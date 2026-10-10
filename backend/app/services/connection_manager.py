import re
from datetime import datetime, timedelta, timezone

import sqlalchemy as sal
from sqlalchemy.exc import IntegrityError

from app.models.account import Account
from app.models.base import Database
from app.models.connection import ConnectionMessage, UserConnection
from app.services.account_manager import AccountError, username_value
from app.services.planner_manager import PlannerManager
from app.tools.time import now

MESSAGE_LIMIT = 50
CHINA_TIME = timezone(timedelta(hours=8))


class ConnectionManager:
    def __init__(self, db: Database):
        self.db = db
        self.planner = PlannerManager(db)

    def _relation(self, owner, connection_id, *, accepted=True):
        relation = self.db.get(UserConnection, connection_id)
        if not relation or owner not in (relation.user_low, relation.user_high):
            raise AccountError("没有权限访问这段关联。", 404)
        peer = self.db.get(Account, self._other(relation, owner))
        if not peer or not peer.active:
            raise AccountError("该联系人暂不可用。", 404)
        if accepted and relation.status != "accepted":
            raise AccountError("这段关联尚未建立。", 404)
        return relation

    @staticmethod
    def _other(relation, owner):
        return relation.user_high if relation.user_low == owner else relation.user_low

    @staticmethod
    def _read_marker(relation, owner):
        return relation.low_read_message_id if relation.user_low == owner else relation.high_read_message_id

    @staticmethod
    def _share_marker(relation, owner):
        return "low_shares_today" if relation.user_low == owner else "high_shares_today"

    def _unread(self, relation, owner):
        return self.db.scalar(sal.select(sal.func.count(ConnectionMessage.id)).where(
            ConnectionMessage.connection_id == relation.id,
            ConnectionMessage.sender != owner,
            ConnectionMessage.id > self._read_marker(relation, owner),
            ConnectionMessage.revoked.is_(False),
        )) or 0

    def _message(self, message, viewer):
        result = {
            "id": message.id, "sender": message.sender, "kind": message.kind,
            "body": "[消息已撤回]" if message.revoked else message.body,
            "revoked": message.revoked, "createdAt": message.created_at.isoformat(timespec="seconds"),
            "clientId": message.client_id,
        }
        if message.kind == "plan" and not message.revoked:
            result["plan"] = message.plan_snapshot
            result["canRevoke"] = message.sender == viewer
        return result

    def _contact(self, relation, owner):
        peer_name = self._other(relation, owner)
        peer = self.db.get(Account, peer_name)
        if not peer or not peer.active:
            return None
        latest = self.db.scalar(
            sal.select(ConnectionMessage)
            .where(ConnectionMessage.connection_id == relation.id)
            .order_by(ConnectionMessage.id.desc()).limit(1)
        )
        return {
            "id": relation.id, "username": peer.username, "displayName": peer.display_name,
            "sharesToday": bool(getattr(relation, self._share_marker(relation, owner))),
            "peerSharesToday": bool(getattr(relation, self._share_marker(relation, peer_name))),
            "unread": self._unread(relation, owner),
            "lastMessage": self._message(latest, owner) if latest else None,
            "updatedAt": (latest.created_at if latest else relation.updated_at).isoformat(timespec="seconds"),
        }

    def overview(self, owner):
        relations = self.db.scalars(sal.select(UserConnection).where(
            sal.or_(UserConnection.user_low == owner, UserConnection.user_high == owner),
        ).order_by(UserConnection.updated_at.desc(), UserConnection.id.desc())).all()
        contacts, incoming, outgoing = [], [], []
        for relation in relations:
            if relation.status == "accepted":
                contact = self._contact(relation, owner)
                if contact:
                    contacts.append(contact)
            elif relation.status == "pending":
                peer_name = self._other(relation, owner)
                peer = self.db.get(Account, peer_name)
                if not peer or not peer.active:
                    continue
                request = {"id": relation.id, "username": peer.username, "displayName": peer.display_name}
                (incoming if relation.requester != owner else outgoing).append(request)
        return {"contacts": contacts, "incoming": incoming, "outgoing": outgoing}

    def invite(self, owner, raw_username):
        peer_name = username_value(raw_username)
        if peer_name == owner:
            raise AccountError("不能添加自己的账号。")
        peer = self.db.get(Account, peer_name)
        if not peer or not peer.active:
            raise AccountError("没有找到可用的账号。", 404)
        low, high = sorted((owner, peer_name))
        relation = self.db.scalar(sal.select(UserConnection).where(
            UserConnection.user_low == low, UserConnection.user_high == high,
        ))
        if relation and relation.status in ("pending", "accepted"):
            raise AccountError("该账号已有待处理邀请或已在联系人中。", 409)
        if relation:
            relation.requester = owner
            relation.status = "pending"
            relation.low_shares_today = False
            relation.high_shares_today = False
            relation.low_read_message_id = 0
            relation.high_read_message_id = 0
            relation.updated_at = now()
        else:
            relation = UserConnection(user_low=low, user_high=high, requester=owner,
                                      status="pending", created_at=now(), updated_at=now())
            self.db.add(relation)
        self.db.flush()
        return {"id": relation.id, "username": peer.username, "displayName": peer.display_name}

    def respond(self, owner, connection_id, action):
        relation = self._relation(owner, connection_id, accepted=False)
        if relation.status != "pending" or relation.requester == owner:
            raise AccountError("该邀请已处理，或不是发给你的邀请。", 409)
        if action not in ("accept", "reject"):
            raise AccountError("请选择接受或拒绝邀请。")
        relation.status = "accepted" if action == "accept" else "rejected"
        relation.updated_at = now()
        return {"status": relation.status}

    def remove(self, owner, connection_id):
        relation = self._relation(owner, connection_id)
        self.db.execute(sal.delete(ConnectionMessage).where(ConnectionMessage.connection_id == relation.id))
        self.db.delete(relation)
        return {"removed": True}

    def set_sharing(self, owner, connection_id, enabled):
        if type(enabled) is not bool:
            raise AccountError("共享状态无效。")
        relation = self._relation(owner, connection_id)
        setattr(relation, self._share_marker(relation, owner), enabled)
        relation.updated_at = now()
        return {"sharesToday": enabled}

    def today_plan(self, owner, connection_id):
        relation = self._relation(owner, connection_id)
        peer = self._other(relation, owner)
        if not getattr(relation, self._share_marker(relation, peer)):
            raise AccountError("对方尚未开放今日计划。", 403)
        return {"owner": peer, **self._shared_plan(peer)}

    def _shared_plan(self, owner, include_notes=False):
        day = datetime.now(CHINA_TIME).date().isoformat()
        plan = self.planner.get_day(owner, day)
        sections = []
        task_count = done_count = 0
        for section in plan["sections"]:
            tasks = []
            for task in section["tasks"]:
                task_count += 1
                done_count += int(task["done"])
                tasks.append({key: value for key, value in task.items() if include_notes or key != "notes"})
            sections.append({**{key: value for key, value in section.items() if key != "tasks"}, "tasks": tasks})
        return {
            "day": day, "title": plan["title"], "sections": sections,
            "taskCount": task_count, "doneCount": done_count, "includesNotes": include_notes,
        }

    def _save_message(self, relation, message, owner):
        try:
            with self.db.begin_nested():
                relation.updated_at = now()
                self.db.add(message)
                self.db.flush()
        except IntegrityError:
            existing = self.db.scalar(sal.select(ConnectionMessage).where(
                ConnectionMessage.connection_id == message.connection_id,
                ConnectionMessage.sender == owner,
                ConnectionMessage.client_id == message.client_id,
            ))
            if existing:
                return self._message(existing, owner)
            raise
        return self._message(message, owner)

    def messages(self, owner, connection_id, *, after=None, before=None, visible_from=None):
        relation = self._relation(owner, connection_id)
        if after is not None and before is not None:
            raise AccountError("不能同时指定前后消息位置。")
        visible_from = self._cursor(visible_from) if visible_from is not None else None
        query = sal.select(ConnectionMessage).where(ConnectionMessage.connection_id == relation.id)
        if after is not None:
            query = query.where(ConnectionMessage.id > self._cursor(after))
        elif before is not None:
            query = query.where(ConnectionMessage.id < self._cursor(before))
        if before is not None or after is None:
            rows = self.db.scalars(query.order_by(ConnectionMessage.id.desc()).limit(MESSAGE_LIMIT + 1)).all()
            has_more = len(rows) > MESSAGE_LIMIT
            rows = list(reversed(rows[:MESSAGE_LIMIT]))
        else:
            rows = self.db.scalars(query.order_by(ConnectionMessage.id.asc()).limit(MESSAGE_LIMIT + 1)).all()
            has_more = len(rows) > MESSAGE_LIMIT
            rows = rows[:MESSAGE_LIMIT]
        return {
            "messages": [self._message(row, owner) for row in rows],
            "hasMore": has_more,
            "readThrough": self._read_marker(relation, owner),
            "revokedIds": list(self.db.scalars(sal.select(ConnectionMessage.id).where(
                ConnectionMessage.connection_id == relation.id,
                ConnectionMessage.id >= visible_from,
                ConnectionMessage.revoked.is_(True),
            )).all()) if visible_from is not None else [],
        }

    @staticmethod
    def _cursor(value):
        if not isinstance(value, str) or not re.fullmatch(r"[1-9]\d{0,9}", value):
            raise AccountError("消息位置无效。")
        return int(value)

    def send(self, owner, connection_id, data):
        relation = self._relation(owner, connection_id)
        if not isinstance(data, dict):
            raise AccountError("消息格式无效。")
        body, client_id = data.get("body"), data.get("clientId")
        if not isinstance(body, str) or not body.strip() or len(body) > 2000:
            raise AccountError("消息需为 1–2000 个字符。")
        if not isinstance(client_id, str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
            client_id,
        ):
            raise AccountError("消息标识无效。")
        existing = self.db.scalar(sal.select(ConnectionMessage).where(
            ConnectionMessage.connection_id == relation.id,
            ConnectionMessage.sender == owner,
            ConnectionMessage.client_id == client_id,
        ))
        if existing:
            return self._message(existing, owner)
        message = ConnectionMessage(connection_id=relation.id, sender=owner, client_id=client_id,
                                    kind="text", body=body.strip())
        return self._save_message(relation, message, owner)

    def share_today(self, owner, connection_id, data):
        relation = self._relation(owner, connection_id)
        client_id = data.get("clientId") if isinstance(data, dict) else None
        if not isinstance(client_id, str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
            client_id,
        ):
            raise AccountError("消息标识无效。")
        existing = self.db.scalar(sal.select(ConnectionMessage).where(
            ConnectionMessage.connection_id == relation.id,
            ConnectionMessage.sender == owner,
            ConnectionMessage.client_id == client_id,
        ))
        if existing:
            return self._message(existing, owner)
        include_notes = data.get("includeNotes", False)
        if type(include_notes) is not bool:
            raise AccountError("备注共享选项无效。")
        message = ConnectionMessage(connection_id=relation.id, sender=owner, client_id=client_id,
                                    kind="plan", body="", plan_snapshot=self._shared_plan(owner, include_notes))
        return self._save_message(relation, message, owner)

    def revoke_plan(self, owner, connection_id, message_id):
        relation = self._relation(owner, connection_id)
        message = self.db.get(ConnectionMessage, message_id)
        if not message or message.connection_id != relation.id or message.sender != owner or message.kind != "plan":
            raise AccountError("不能撤回这条计划分享。", 404)
        message.revoked = True
        message.plan_snapshot = None
        return {"revoked": True}

    def mark_read(self, owner, connection_id, message_id):
        relation = self._relation(owner, connection_id)
        message_id = self._cursor(message_id)
        message = self.db.get(ConnectionMessage, message_id)
        if not message or message.connection_id != relation.id:
            raise AccountError("消息不存在。", 404)
        marker = "low_read_message_id" if relation.user_low == owner else "high_read_message_id"
        setattr(relation, marker, max(getattr(relation, marker), message_id))
        return {"readThrough": getattr(relation, marker)}
