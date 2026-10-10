import app as application
from app.models.connection import ConnectionMessage
from app.tests.services import account_test
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import unittest
import uuid


class ConnectionTests(unittest.TestCase):
    setUp = account_test.AccountTests.setUp
    tearDown = account_test.AccountTests.tearDown
    token = account_test.AccountTests.token
    send = account_test.AccountTests.send
    register = account_test.AccountTests.register

    def setUp_users(self):
        self.register("alice")
        self.bob = self.app.test_client()
        self.register("bobbie", self.bob, displayName="Bob")

    def connect(self):
        response = self.send("/api/connections/invitations", {"username": "bobbie"})
        self.assertEqual(response.status_code, 201)
        connection_id = response.json["id"]
        self.assertEqual(self.bob.get("/api/connections").json["incoming"][0]["id"], connection_id)
        accepted = self.send(f"/api/connections/{connection_id}/invitation", {"action": "accept"},
                             method="PATCH", client=self.bob)
        self.assertEqual(accepted.status_code, 200)
        return connection_id

    @staticmethod
    def today():
        return datetime.now(timezone(timedelta(hours=8))).date().isoformat()

    def test_login_and_mutual_acceptance_are_required(self):
        self.assertEqual(self.client.get("/api/connections").status_code, 401)
        self.setUp_users()
        self.assertEqual(self.send("/api/connections/invitations", {"username": "missing"}).status_code, 404)
        self.assertEqual(self.send("/api/connections/invitations", {"username": "alice"}).status_code, 400)
        request = self.send("/api/connections/invitations", {"username": "bobbie"})
        connection_id = request.json["id"]
        self.assertEqual(self.client.get(f"/api/connections/{connection_id}/messages").status_code, 404)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/invitation",
                                   {"action": "accept"}, method="PATCH").status_code, 409)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/invitation",
                                   {"action": "reject"}, method="PATCH", client=self.bob).status_code, 200)
        self.assertEqual(self.bob.get(f"/api/connections/{connection_id}/today").status_code, 404)

    def test_today_is_private_until_explicitly_shared_and_revocation_is_immediate(self):
        self.setUp_users()
        connection_id = self.connect()
        day = self.today()
        plan = self.client.get(f"/api/planner/day/{day}").json
        plan["title"] = "Alice Today"
        plan["sections"][0]["tasks"] = [{
            "id": "task-secret", "title": "Private task", "notes": "Private note",
            "kind": "task", "time": "09:00", "done": False,
        }]
        self.assertEqual(self.send(f"/api/planner/day/{day}", plan, "PUT").status_code, 200)
        self.assertEqual(self.bob.get(f"/api/connections/{connection_id}/today").status_code, 403)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/sharing", {"enabled": True},
                                   "PATCH").status_code, 200)
        shared = self.bob.get(f"/api/connections/{connection_id}/today")
        self.assertEqual(shared.status_code, 200)
        self.assertEqual(shared.json["title"], "Alice Today")
        self.assertNotIn("Private note", str(shared.json))
        self.assertEqual(shared.json["taskCount"], 1)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/sharing", {"enabled": False},
                                   "PATCH").status_code, 200)
        self.assertEqual(self.bob.get(f"/api/connections/{connection_id}/today").status_code, 403)

    def test_shared_plan_snapshot_omits_notes_by_default_and_can_be_revoked(self):
        self.setUp_users()
        connection_id = self.connect()
        day = self.today()
        plan = self.client.get(f"/api/planner/day/{day}").json
        plan["sections"][0]["tasks"] = [{
            "id": "task-one", "title": "Prepare notes", "notes": "Private detail",
            "kind": "task", "time": "09:00", "done": False,
        }]
        self.send(f"/api/planner/day/{day}", plan, "PUT")
        message = self.send(f"/api/connections/{connection_id}/share-today",
                            {"clientId": str(uuid.uuid4())}).json
        task = message["plan"]["sections"][0]["tasks"][0]
        self.assertEqual(task["title"], "Prepare notes")
        self.assertNotIn("notes", task)
        self.assertEqual(message["plan"]["includesNotes"], False)
        received = self.bob.get(f"/api/connections/{connection_id}/messages").json["messages"][0]
        self.assertNotIn("Private detail", str(received))
        revoked = self.send(f"/api/connections/{connection_id}/messages/{message['id']}",
                            method="DELETE")
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNone(self.bob.get(
            f"/api/connections/{connection_id}/messages"
        ).json["messages"][0].get("plan"))
        update = self.bob.get(
            f"/api/connections/{connection_id}/messages?after={message['id']}&visibleFrom={message['id']}"
        ).json
        self.assertEqual(update["messages"], [])
        self.assertEqual(update["revokedIds"], [message["id"]])

    def test_chat_isolation_validation_idempotency_and_unread_read_cursor(self):
        self.setUp_users()
        connection_id = self.connect()
        client_id = str(uuid.uuid4())
        data = {"clientId": client_id, "body": "今天一起复盘吗？"}
        sent = self.send(f"/api/connections/{connection_id}/messages", data)
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/messages", data).json["id"], sent.json["id"])
        self.assertEqual(self.bob.get("/api/connections").json["contacts"][0]["unread"], 1)
        page = self.bob.get(f"/api/connections/{connection_id}/messages")
        self.assertEqual(page.json["messages"][0]["body"], data["body"])
        marked = self.send(f"/api/connections/{connection_id}/read",
                           {"messageId": str(sent.json["id"])}, client=self.bob)
        self.assertEqual(marked.status_code, 200)
        self.assertEqual(self.bob.get("/api/connections").json["contacts"][0]["unread"], 0)
        self.assertEqual(self.bob.get(f"/api/connections/{connection_id}/messages?after=broken").status_code, 400)
        outsider = self.app.test_client()
        self.register("charlie", outsider)
        self.assertEqual(outsider.get(f"/api/connections/{connection_id}/messages").status_code, 404)
        self.assertEqual(self.send(f"/api/connections/{connection_id}/messages", {
            "clientId": str(uuid.uuid4()), "body": "x" * 2001,
        }).status_code, 400)
        for endpoint, method in (("messages", "POST"), ("sharing", "PATCH"), ("read", "POST")):
            invalid = self.client.open(
                f"/api/connections/{connection_id}/{endpoint}", method=method, json=["invalid"],
                headers={"X-CSRF-Token": self.token()},
            )
            self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.bob.get(
            f"/api/connections/{connection_id}/messages?visibleFrom=broken"
        ).status_code, 400)
        with self.app.app_context():
            self.assertEqual(application.db.scalar(select(ConnectionMessage.id).where(
                ConnectionMessage.connection_id == connection_id
            )), sent.json["id"])

    def test_removal_deletes_conversation_and_revokes_shared_access(self):
        self.setUp_users()
        connection_id = self.connect()
        self.send(f"/api/connections/{connection_id}/sharing", {"enabled": True}, "PATCH")
        self.send(f"/api/connections/{connection_id}/messages", {
            "clientId": str(uuid.uuid4()), "body": "Hello",
        })
        self.assertEqual(self.send(f"/api/connections/{connection_id}", method="DELETE").status_code, 200)
        self.assertEqual(self.bob.get(f"/api/connections/{connection_id}/messages").status_code, 404)
        with self.app.app_context():
            self.assertIsNone(application.db.get(ConnectionMessage, 1))

    def test_local_mode_disables_connections(self):
        self.app.config["LOCAL_MODE"] = True
        self.assertEqual(self.client.get("/api/connections").status_code, 403)
