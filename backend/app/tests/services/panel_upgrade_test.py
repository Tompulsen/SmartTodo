import ast
import importlib.util
from pathlib import Path
import subprocess
import types
import unittest
from unittest.mock import patch


module_path = Path(__file__).resolve().parents[4] / "docker/install-baota-upgrade-guard.py"
spec = importlib.util.spec_from_file_location("panel_upgrade_guard", module_path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class Arguments(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


SOURCE = """
class Panel:
    def upgrade_container(self, get):
        old_container_config = get.old_container_config
        new_container_config = get.proposed
        get.new_container_config = new_container_config
        return "original-upgrade"
"""


class PanelUpgradeTests(unittest.TestCase):
    def invoke(self, name="/smarttodo", project="smarttodo", upgrade="1",
               image="ghcr.io/tompulsen/smarttodo:latest", exists=True, returncode=0):
        namespace = {"public": types.SimpleNamespace(returnMsg=lambda ok, message: (ok, message))}
        exec(compile(guard.patch_source(SOURCE), "<panel-test>", "exec"), namespace)
        arguments = Arguments(
            upgrade=upgrade, old_container_config={"name": name, "labels": {"com.docker.compose.project": project}},
            proposed={"image": image},
        )
        with patch.object(Path, "is_file", return_value=exists), patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], returncode, "")) as runner:
            result = namespace["Panel"]().upgrade_container(arguments)
        return result, runner

    def test_smarttodo_upgrade_uses_the_health_checked_project_script(self):
        result, runner = self.invoke()
        self.assertTrue(result[0])
        self.assertEqual(runner.call_args.args[0], ["sh", "update.sh", "image"])
        self.assertEqual(Path(runner.call_args.kwargs["cwd"]), Path("/www/wwwroot/smarttodo"))
        self.assertEqual(runner.call_args.kwargs["env"]["SMARTTODO_IMAGE"],
                         "ghcr.io/tompulsen/smarttodo:latest")

    def test_other_containers_and_editing_keep_the_original_panel_behavior(self):
        for overrides in ({"name": "/another"}, {"project": "another"}, {"upgrade": "0"}):
            result, runner = self.invoke(**overrides)
            self.assertEqual(result, "original-upgrade")
            runner.assert_not_called()

    def test_missing_files_and_invalid_images_fail_before_any_mutation(self):
        for overrides in ({"exists": False}, {"image": "other:latest"}, {"image": "bad; command"}):
            result, runner = self.invoke(**overrides)
            self.assertFalse(result[0])
            runner.assert_not_called()

    def test_failed_update_is_reported_as_failure(self):
        result, _ = self.invoke(returncode=1)
        self.assertFalse(result[0])

    def test_patching_is_idempotent_and_rejects_unrecognized_panel_versions(self):
        patched = guard.patch_source(SOURCE)
        ast.parse(patched)
        self.assertEqual(guard.patch_source(patched), patched)
        with self.assertRaises(ValueError):
            guard.patch_source("class AnotherPanel: pass")
