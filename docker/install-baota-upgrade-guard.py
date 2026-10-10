"""Install a narrowly scoped compatibility guard for SmartTodo panel upgrades."""
import argparse
import ast
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import tempfile
import textwrap


MARKER = "# SMARTTODO_COMPOSE_UPGRADE_GUARD_V1"
DEFAULT_PANEL_FILE = Path("/www/server/panel/class/btdockerModel/containerModel.py")
GUARD = """
# SMARTTODO_COMPOSE_UPGRADE_GUARD_V1
if (get.get("upgrade") == "1"
        and old_container_config.get("name", "").lstrip("/") == "smarttodo"
        and (old_container_config.get("labels") or {}).get("com.docker.compose.project") == "smarttodo"):
    import os as _st_os
    import re as _st_re
    import subprocess as _st_subprocess
    from pathlib import Path as _st_Path
    _st_root = _st_Path("/www/wwwroot/smarttodo")
    _st_image = get.new_container_config.get("image", "")
    if not _st_re.fullmatch(r"ghcr\\.io/tompulsen/smarttodo:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", _st_image):
        return public.returnMsg(False, "SmartTodo: select a published SmartTodo image tag.")
    if not ((_st_root / ".smarttodo-deployment").is_file()
            and (_st_root / "update.sh").is_file() and (_st_root / ".env").is_file()):
        return public.returnMsg(False, "SmartTodo deployment files are missing; no container was changed.")
    try:
        _st_result = _st_subprocess.run(
            ["sh", "update.sh", "image"], cwd=str(_st_root),
            env=dict(_st_os.environ, SMARTTODO_IMAGE=_st_image),
            stdout=_st_subprocess.PIPE, stderr=_st_subprocess.STDOUT,
            text=True, timeout=300,
        )
    except _st_subprocess.TimeoutExpired:
        return public.returnMsg(False, "SmartTodo update timed out; check its deployment log before retrying.")
    if _st_result.returncode:
        return public.returnMsg(False, "SmartTodo update failed; check container health and deployment logs.")
    return public.returnMsg(True, "SmartTodo updated and healthy; deployment settings preserved.")
"""


def patch_source(source):
    tree = ast.parse(source)
    if MARKER in source:
        return source
    methods = [node for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and node.name == "upgrade_container"]
    if len(methods) != 1:
        raise ValueError("Expected exactly one panel upgrade method; no changes made.")
    method = methods[0]
    matches = [node for node in ast.walk(method) if isinstance(node, ast.Assign)
               and len(node.targets) == 1 and ast.unparse(node.targets[0]) == "get.new_container_config"
               and isinstance(node.value, ast.Name) and node.value.id == "new_container_config"]
    if len(matches) != 1:
        raise ValueError("Panel upgrade layout has changed; no changes made.")
    insertion = matches[0]
    lines = source.splitlines(keepends=True)
    patched = "".join(lines[:insertion.end_lineno]) + textwrap.indent(
        GUARD.lstrip("\n"), " " * insertion.col_offset) + "".join(lines[insertion.end_lineno:])
    ast.parse(patched)
    return patched


def install(path):
    if path.resolve() != DEFAULT_PANEL_FILE:
        raise ValueError("Only the known panel module may be patched.")
    source = path.read_text(encoding="utf-8")
    patched = patch_source(source)
    if patched == source:
        return {"installed": True, "changed": False}
    backup = path.with_name(path.name + ".smarttodo-backup-" +
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    shutil.copy2(path, backup)
    metadata = path.stat()
    descriptor, temporary = tempfile.mkstemp(prefix=".smarttodo-", suffix=".py", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(patched)
        os.chmod(temporary, metadata.st_mode)
        if hasattr(os, "chown"):
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"installed": True, "changed": True, "backup": str(backup)}


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        source = DEFAULT_PANEL_FILE.read_text(encoding="utf-8")
        patch_source(source)
        print(json.dumps({"compatible": True, "installed": MARKER in source}))
    else:
        print(json.dumps(install(DEFAULT_PANEL_FILE)))
