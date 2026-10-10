import os
from pathlib import Path

from flask import abort, send_from_directory

from app import create_app


def production_app():
    app = create_app()
    web_root = Path(os.environ.get("SMARTTODO_WEB_ROOT", "/app/web")).resolve()

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path):
        if path.split("/", 1)[0] in {"api", "admin", "file", "_local"}:
            abort(404)
        if any(part.startswith(".") for part in Path(path).parts):
            abort(404)
        if path and (web_root / path).is_file():
            return send_from_directory(web_root, path)
        if path.startswith(("assets/", "art/", "sounds/")):
            abort(404)
        response = send_from_directory(web_root, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    return app


app = production_app()
