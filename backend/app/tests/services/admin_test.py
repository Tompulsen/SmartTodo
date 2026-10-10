import app as application
from app.models.account import Account
from app.services.admin_manager import AdminManager
from app.tests.services import account_test
from werkzeug.security import check_password_hash
import unittest


class AdminTests(unittest.TestCase):
    setUp = account_test.AccountTests.setUp
    tearDown = account_test.AccountTests.tearDown
    token = account_test.AccountTests.token
    send = account_test.AccountTests.send
    register = account_test.AccountTests.register

    def login_admin(self, username="admin"):
        with self.app.app_context():
            application.account_manager.create({"username": username, "password": "admin-test-password"}, admin=True)
        client = self.app.test_client()
        result = self.send("/api/login", {"username": username, "password": "admin-test-password"}, client=client)
        self.assertEqual(result.status_code, 200)
        return client

    def record(self, client, username="alice"):
        response = client.get("/api/admin/users")
        self.assertEqual(response.status_code, 200)
        return next(user for user in response.json["users"] if user["username"] == username)

    def edit(self, client, username="alice", **data):
        revision = self.record(client, username)["revision"]
        return self.send("/api/admin/users/" + username, {"revision": revision, **data}, method="PATCH", client=client)

    def test_anonymous_regular_and_forged_session_cannot_manage_users(self):
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)
        self.register()
        for path, method in [("/api/admin/users", "GET"), ("/api/admin/users/alice", "PATCH"),
                             ("/api/admin/users/alice/password", "POST")]:
            self.assertEqual(self.send(path, {"revision": 1, "isAdmin": True}, method, self.client).status_code, 403)
        with self.client.session_transaction() as session:
            session["role"] = ["ROLE_ADMIN"]
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)

    def test_listing_has_filters_and_no_passwords_or_private_plans(self):
        self.register("alice", displayName="Alice")
        self.register("bobbie", displayName="Bob")
        client = self.login_admin()
        response = client.get("/api/admin/users?q=Alice&status=active&role=user").json
        self.assertEqual(response["total"], 1)
        user = response["users"][0]
        self.assertEqual(user["username"], "alice")
        self.assertIn("createdAt", user)
        self.assertEqual(set(user), {"username", "displayName", "isAdmin", "preferences", "active", "revision", "createdAt"})
        self.assertEqual(client.get("/api/admin/users?role=admin").json["total"], 1)
        self.assertEqual(client.get("/api/admin/users?q=%").json["total"], 0)
        for query in ("page=0", "page=no", "role=root", "status=unknown", "q=" + "a" * 41):
            self.assertEqual(client.get("/api/admin/users?" + query).status_code, 400)

    def test_edit_revokes_sessions_and_persists_profile(self):
        self.register()
        client = self.login_admin()
        response = self.edit(client, displayName="Edited", defaultPeriod="year")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["preferences"]["defaultPeriod"], "year")
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/session").json["user"]["displayName"], "Edited")

    def test_disable_enable_and_role_changes_are_effective(self):
        self.register()
        client = self.login_admin()
        self.assertEqual(self.edit(client, active=False).status_code, 200)
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"}).status_code, 401)
        self.assertEqual(self.edit(client, active=True, isAdmin=True).status_code, 200)
        self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"})
        self.assertEqual(self.client.get("/api/admin/users").status_code, 200)
        self.assertEqual(self.edit(client, isAdmin=False).status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)
        self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"})
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)

    def test_self_changes_are_blocked_and_last_administrator_is_preserved(self):
        client = self.login_admin()
        for data in ({"active": False}, {"isAdmin": False}, {"displayName": "Changed"}):
            self.assertEqual(self.edit(client, username="admin", **data).status_code, 400)
        self.assertEqual(self.send("/api/admin/users/admin/password",
            {"revision": 1, "newPassword": "new-test-password"}, client=client).status_code, 400)
        self.assertEqual(client.get("/api/auth/session").json["user"]["isAdmin"], True)

    def test_password_reset_hashes_password_and_revokes_sessions(self):
        self.register()
        client = self.login_admin()
        response = self.send("/api/admin/users/alice/password",
            {"revision": 1, "newPassword": "replacement-password"}, client=client)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("replacement-password", str(response.json))
        self.assertEqual(self.client.get("/api/focus/state").status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "a-secure-test-password"}).status_code, 401)
        self.assertEqual(self.send("/api/login", {"username": "alice", "password": "replacement-password"}).status_code, 200)
        with self.app.app_context():
            self.assertTrue(check_password_hash(application.db.get(Account, "alice").password_hash, "replacement-password"))

    def test_stale_revisions_do_not_overwrite_profile_or_password(self):
        self.register()
        client = self.login_admin()
        self.edit(client, displayName="New")
        for path, method, data in [
            ("/api/admin/users/alice", "PATCH", {"revision": 1, "displayName": "Stale"}),
            ("/api/admin/users/alice/password", "POST", {"revision": 1, "newPassword": "new-test-password"}),
        ]:
            self.assertEqual(self.send(path, data, method=method, client=client).status_code, 409)
        self.assertEqual(self.record(client)["displayName"], "New")

    def test_invalid_fields_and_csrf_do_not_change_user(self):
        self.register()
        client = self.login_admin()
        for data in ({"active": "false"}, {"isAdmin": 1}, {"defaultPeriod": "other"},
                     {"displayName": ""}, {"username": "changed"}, {"password_hash": "bad"}):
            self.assertEqual(self.send("/api/admin/users/alice", {"revision": 1, **data},
                method="PATCH", client=client).status_code, 400)
        self.assertEqual(client.patch("/api/admin/users/alice", json={"revision": 1, "isAdmin": True}).status_code, 403)
        self.assertEqual(self.record(client)["revision"], 1)
        self.assertEqual(self.send("/api/admin/users/alice/password",
            {"revision": 1, "newPassword": "short"}, client=client).status_code, 400)
        self.assertEqual(self.send("/api/admin/users/missing", {"revision": 1, "active": False},
            method="PATCH", client=client).status_code, 404)

    def test_revoked_actor_is_rechecked_before_mutation(self):
        self.register()
        self.login_admin()
        with self.app.app_context():
            actor = application.db.get(Account, "admin")
            actor.is_admin = False
            application.db.flush()
            manager = AdminManager(application.db, application.account_manager)
            with self.assertRaisesRegex(ValueError, "权限已失效"):
                manager.update("admin", 1, "alice", {"revision": 1, "isAdmin": True})
            self.assertFalse(application.db.get(Account, "alice").is_admin)

    def test_revoked_actor_session_is_rechecked_before_mutation(self):
        self.register()
        self.login_admin()
        with self.app.app_context():
            actor = application.db.get(Account, "admin")
            actor.session_version += 1
            application.db.flush()
            manager = AdminManager(application.db, application.account_manager)
            with self.assertRaisesRegex(ValueError, "权限已失效"):
                manager.update("admin", 1, "alice", {"revision": 1, "active": False})
            self.assertTrue(application.db.get(Account, "alice").active)

    def test_local_mode_never_exposes_platform_user_management(self):
        self.app.config["LOCAL_MODE"] = True
        with self.client.session_transaction() as session:
            session["username"] = "admin"
            session["role"] = ["ROLE_USER", "ROLE_ADMIN"]
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)

    def test_pagination_and_stable_sort(self):
        client = self.login_admin()
        with self.app.app_context():
            template = application.db.get(Account, "admin").password_hash
            for i in range(30):
                application.db.add(Account(username=f"user{i:04}", display_name="User",
                    password_hash=template, is_admin=False, active=True, session_version=1,
                    preferences={"defaultPeriod": "day"}))
        first = client.get("/api/admin/users?page=1").json
        second = client.get("/api/admin/users?page=2").json
        self.assertEqual((first["total"], len(first["users"]), len(second["users"])), (31, 25, 6))
        self.assertFalse(set(user["username"] for user in first["users"]) &
                         set(user["username"] for user in second["users"]))
