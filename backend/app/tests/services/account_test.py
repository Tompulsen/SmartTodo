import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable
from werkzeug.security import check_password_hash

import app as application
from app.models.account import Account, AuthThrottle
from app.models.base import Base
from app.models.item import Item


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.old_engine = application.engine
        application.db.remove()
        self.engine = create_engine("sqlite://")
        application.db.configure(bind=self.engine)
        self.env = patch.dict(os.environ, {
            "SMARTTODO_LOCAL_MODE": "0", "SMARTTODO_SCHEDULER": "0",
            "SMARTTODO_ADMIN_USER": "", "SMARTTODO_ADMIN_PASSWORD": "",
            "SMARTTODO_REGISTRATION": "1", "SMARTTODO_SECURE_COOKIE": "0",
        })
        self.env.start()
        self.engine_patch = patch.object(application, "engine", self.engine)
        self.engine_patch.start()
        with patch.object(application, "get_or_create_secret_key", return_value="isolated-test-session-secret"):
            self.app = application.create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        application.db.remove()
        application.db.configure(bind=self.old_engine)
        self.engine.dispose()
        self.engine_patch.stop()
        self.env.stop()

    def token(self, client=None):
        return (client or self.client).get("/api/auth/session").json["csrfToken"]

    def send(self, path, data=None, method="POST", client=None):
        client = client or self.client
        return client.open(path, method=method, json=data or {},
                           headers={"X-CSRF-Token": self.token(client)})

    def register(self, username="alice", client=None, **extra):
        return self.send("/api/auth/register", {
            "username": username, "password": "a-secure-test-password", **extra,
        }, client=client)

    def test_registration_hashes_password_and_never_grants_admin(self):
        response = self.register("ALICE", displayName="Alice", isAdmin=True, role=["ROLE_ADMIN"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["username"], "alice")
        self.assertFalse(response.json["user"]["isAdmin"])
        with self.app.app_context():
            account = application.db.get(Account, "alice")
            self.assertNotEqual(account.password_hash, "a-secure-test-password")
            self.assertTrue(check_password_hash(account.password_hash, "a-secure-test-password"))
        self.assertNotIn("password", str(response.json))
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", response.headers["Set-Cookie"])
        self.assertEqual(self.register("Alice").status_code, 409)

    def test_csrf_session_and_logout_protect_data(self):
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/register", json={}).status_code, 403)
        old_token = self.token()
        self.register()
        self.assertNotEqual(old_token, self.token())
        self.assertEqual(self.client.post("/api/logout", headers={"X-CSRF-Token": old_token}).status_code, 403)
        self.assertEqual(self.client.get("/api/focus/state").status_code, 200)
        self.assertEqual(self.client.get("/api/log/log").status_code, 403)
        self.assertEqual(self.send("/api/logout").status_code, 200)
        self.assertIsNone(self.client.get("/api/auth/session").json["user"])
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)

    def test_login_rejects_bad_password_and_accepts_case_normalization(self):
        self.register()
        self.send("/api/logout")
        response = self.send("/api/login", {"username": "alice", "password": "incorrect-password"})
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.client.get("/api/auth/session").json["user"])
        response = self.send("/api/login", {"username": " ALICE ", "password": "a-secure-test-password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["username"], "alice")

    def test_profile_persists_and_password_change_revokes_other_sessions(self):
        self.register()
        second = self.app.test_client()
        self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"}, client=second)
        response = self.send("/api/account/profile", {"displayName": "New Name", "defaultPeriod": "month"}, method="PATCH")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(second.get("/api/auth/session").json["user"]["preferences"]["defaultPeriod"], "month")
        self.assertEqual(self.send("/api/account/password", {"currentPassword": "wrong", "newPassword": "new-password-123"}).status_code, 400)
        self.assertEqual(self.send("/api/account/password", {"currentPassword": "a-secure-test-password", "newPassword": "new-password-123"}).status_code, 200)
        self.assertEqual(second.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"}).status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "new-password-123"}).status_code, 200)

    def test_plan_and_focus_are_isolated_between_registered_accounts(self):
        self.register()
        board = self.client.get("/api/planner/day/2026-10-10").json
        board["title"] = "Alice private plan"
        self.assertEqual(self.send("/api/planner/day/2026-10-10", board, method="PUT").status_code, 200)
        other = self.app.test_client()
        self.register("bobbie", other)
        self.assertNotEqual(other.get("/api/planner/day/2026-10-10").json["title"], board["title"])
        self.assertEqual(self.client.get("/api/planner/day/2026-10-10").json["title"], board["title"])
        self.assertEqual(self.send("/api/focus/state", {"action": "start", "revision": 0,
                         "mode": "pomodoro", "duration": 1500}).status_code, 200)
        self.assertIsNotNone(self.client.get("/api/focus/state").json["session"])
        self.assertIsNone(other.get("/api/focus/state").json["session"])

    def test_signup_cannot_claim_a_local_owners_existing_data(self):
        with self.app.app_context():
            application.db.add(Item(name="Private local task", owner="legacy"))
        self.assertEqual(self.register("legacy").status_code, 409)
        self.assertEqual(self.client.get("/api/planner/day/2026-10-10").status_code, 401)

    def test_legacy_items_cannot_reference_another_owners_note(self):
        self.register()
        self.assertEqual(self.send("/api/item/create", {"name": "Private note", "itemType": "note"}).status_code, 200)
        with self.app.app_context():
            note = application.db.scalar(select(Item))
            identifier = note.id
        other = self.app.test_client()
        self.register("bobbie", other)
        response = self.send("/api/item/create", {"name": "Bad parent", "itemType": "single", "parent": identifier}, client=other)
        self.assertEqual(response.status_code, 403)
        response = self.send("/api/item/recentNote", client=other)
        self.assertEqual(response.json, [])

    def test_registration_disabled_and_invalid_inputs(self):
        for name, password in [("../root", "long-password"), ("root", "short"), ("1root", "long-password")]:
            self.assertEqual(self.register(name, password=password).status_code, 400)
        self.app.config["REGISTRATION_ENABLED"] = False
        self.assertFalse(self.client.get("/api/auth/session").json["registrationEnabled"])
        self.assertEqual(self.register().status_code, 403)

    def test_rate_limit_is_persistent_across_new_sessions(self):
        with self.app.app_context():
            application.account_manager.throttle("test", "identity", 1)
        with self.app.app_context():
            with self.assertRaisesRegex(ValueError, "尝试次数"):
                application.account_manager.throttle("test", "identity", 1)
            self.assertEqual(application.db.scalar(select(AuthThrottle.count)), 1)
        self.register()
        for _ in range(15):
            self.assertEqual(self.send("/api/login", {"username": "alice", "password": "wrong"}).status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "wrong"}).status_code, 429)

    def test_file_upload_uses_safe_names_and_requires_ownership(self):
        self.register()
        with tempfile.TemporaryDirectory() as temp:
            with patch("app.tools.file.FILE_FOLDER", temp), patch("app.views.file.FILE_FOLDER", temp):
                response = self.client.post("/api/file/upload",
                    data={"myFile": (io.BytesIO(b"private attachment"), "../outside.txt")},
                    headers={"X-CSRF-Token": self.token()})
                self.assertEqual(response.status_code, 200)
                with self.app.app_context():
                    item = application.db.scalar(select(Item))
                    path = item.url
                self.assertEqual(len(list(Path(temp).iterdir())), 1)
                attachment = self.client.get(path)
                self.assertEqual(attachment.data, b"private attachment")
                self.assertIn("attachment;", attachment.headers["Content-Disposition"])
                attachment.close()
                second = self.app.test_client()
                self.assertEqual(second.get(path).status_code, 401)
                self.register("bobbie", second)
                self.assertEqual(second.get(path).status_code, 404)

    def test_all_tables_compile_for_mysql_and_secure_cookie_setting(self):
        for table in Base.metadata.sorted_tables:
            self.assertIn("CREATE TABLE", str(CreateTable(table).compile(dialect=mysql.dialect())))
        self.app.config["SESSION_COOKIE_SECURE"] = True
        response = self.client.get("/api/auth/session", base_url="https://localhost")
        self.assertIn("Secure;", response.headers["Set-Cookie"])

    def test_local_mode_remains_explicit_and_has_no_registration(self):
        self.app.config["LOCAL_MODE"] = True
        with self.client.session_transaction() as session:
            session["username"] = "admin"
            session["role"] = ["ROLE_USER", "ROLE_ADMIN"]
        response = self.client.get("/api/auth/session")
        self.assertTrue(response.json["localMode"])
        self.assertFalse(response.json["registrationEnabled"])
        self.assertEqual(self.client.get("/api/planner/day/2026-10-10").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/register", json={}).status_code, 403)
