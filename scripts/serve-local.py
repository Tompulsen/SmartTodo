"""Serve the existing application and built frontend on a loopback address."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "dist"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if not (WEB_ROOT / "index.html").is_file():
        parser.error("Build the frontend first: cd web && pnpm run build")

    os.chdir(ROOT)
    os.environ["ENV"] = "DEV"
    (ROOT / "data").mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT / "backend"))

    from flask import abort, jsonify, redirect, request, send_from_directory, session
    from app import config_manager
    from run import app

    local_user = next(
        (user for user in config_manager.get_all_users() if config_manager.is_admin_user(user)),
        None,
    )
    if local_user is None:
        parser.error("Local mode requires a configured administrator to own the existing data.")

    @app.before_request
    def local_access():
        if request.remote_addr not in {"127.0.0.1", "::1"}:
            abort(403)

        # Reuse the existing owner's data without requiring a browser login cookie.
        session["username"] = local_user
        session["role"] = config_manager.get_roles(local_user)
        if request.path.rstrip("/") == "/login":
            return redirect("/index")
        if request.method == "POST":
            if request.path == "/api/login":
                return "True"
            if request.path == "/api/logout":
                return jsonify(True)

    @app.get("/_local/health")
    def local_health():
        return {"application": "SmartTodo", "mode": "local", "authentication_required": False}

    @app.get("/file/<path:filename>")
    def local_download(filename):
        return send_from_directory(ROOT / "data" / "filebase", filename)

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def local_frontend(path):
        if path.split("/", 1)[0] in {"api", "admin", "file", "_local"}:
            abort(404)
        if path and (WEB_ROOT / path).is_file():
            return send_from_directory(WEB_ROOT, path)
        return send_from_directory(WEB_ROOT, "index.html")

    app.run(host="127.0.0.1", port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
