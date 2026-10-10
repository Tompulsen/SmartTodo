import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask


class ProductionFrontendTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "index.html").write_text("<html>SmartTodo test</html>")
        (root / "assets").mkdir()
        (root / "assets" / "app.js").write_text("console.log('test');")
        self.environment = patch.dict(os.environ, {"SMARTTODO_WEB_ROOT": str(root)})
        self.environment.start()
        sys.modules.pop("wsgi", None)
        with patch("app.create_app", side_effect=lambda: Flask("production-test")):
            self.client = importlib.import_module("wsgi").app.test_client()

    def tearDown(self):
        sys.modules.pop("wsgi", None)
        self.environment.stop()
        self.directory.cleanup()

    def test_client_routes_and_static_assets(self):
        for path in ("/", "/login", "/register", "/settings", "/tools/admin"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"SmartTodo test", response.data)
                self.assertEqual(response.headers["Cache-Control"], "no-cache")
        with self.client.get("/assets/app.js") as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"console.log", response.data)

    def test_private_and_missing_asset_routes_do_not_serve_frontend(self):
        for path in ("/api/missing", "/admin/config", "/file/private", "/_local/health",
                     "/.env", "/assets/../../config/secret.txt", "/assets/missing.js"):
            self.assertEqual(self.client.get(path).status_code, 404, path)


if __name__ == "__main__":
    unittest.main()
