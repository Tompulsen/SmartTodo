import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SHELL = shutil.which("sh")
if SHELL is None and os.name == "nt":
    candidates = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"]
    git = shutil.which("git")
    if git:
        candidates.append(Path(git).resolve().parents[1] / "bin/bash.exe")
    SHELL = next((str(candidate) for candidate in candidates if candidate.is_file()), None)


@unittest.skipUnless(SHELL, "A POSIX shell is required for deployment script tests")
class DeploymentUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        source = Path(__file__).resolve().parents[4] / "docker/update.sh"
        shutil.copyfile(source, self.root / "update.sh")
        (self.root / ".env").write_text("", encoding="utf-8")
        (self.root / "docker").write_text(
            """#!/bin/sh
set -eu
printf '%s\\t%s\\n' "${SMARTTODO_IMAGE:-}" "$*" >> "$DOCKER_TEST_LOG"
case "$1" in
    inspect) printf 'sha256:previous\\n' ;;
    compose)
        if [ "$2" = pull ] && [ "${MOCK_PULL_FAIL:-0}" = 1 ]; then exit 1; fi
        if [ "$2" = up ] && [ "${MOCK_UP_FAIL:-0}" = 1 ] &&
           [ "${SMARTTODO_IMAGE:-}" != sha256:previous ]; then exit 1; fi
        ;;
esac
""", encoding="utf-8", newline="\n")
        (self.root / "docker").chmod(0o755)
        self.log = self.root / "commands.log"
        self.environment = dict(os.environ, DOCKER_TEST_LOG=self.log.as_posix(), SMARTTODO_IMAGE="")

    def tearDown(self):
        self.directory.cleanup()

    def run_update(self, **flags):
        result = subprocess.run(
            [SHELL, "-c", 'export PATH="$PWD:$PATH"; exec sh update.sh'],
            cwd=self.root, env=dict(self.environment, **flags),
            capture_output=True, text=True, timeout=15)
        commands = [line.split("\t", 1) for line in self.log.read_text().splitlines()]
        return result, commands

    def test_update_recreates_container_even_if_the_image_has_not_changed(self):
        result, commands = self.run_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        updates = [args for _, args in commands if args.startswith("compose up")]
        self.assertEqual(updates, ["compose up -d --force-recreate --wait --wait-timeout 120 smarttodo"])
        self.assertIn("SmartTodo is healthy.", result.stdout)

    def test_failed_health_check_recreates_the_previous_image(self):
        result, commands = self.run_update(MOCK_UP_FAIL="1")
        self.assertEqual(result.returncode, 1)
        updates = [(image, args) for image, args in commands if args.startswith("compose up")]
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[1][0], "sha256:previous")
        self.assertTrue(all("--force-recreate" in args and "--wait" in args for _, args in updates))
        self.assertIn("restoring the previous image", result.stdout)

    def test_failed_pull_does_not_replace_the_running_container(self):
        result, commands = self.run_update(MOCK_PULL_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(args.startswith("compose up") for _, args in commands))
