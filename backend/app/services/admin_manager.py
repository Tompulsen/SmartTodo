from datetime import timezone

from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

from app.models.account import Account
from app.services.account_manager import AccountError, password_value, profile_name, username_value


class AdminManager:
    def __init__(self, db, accounts):
        self.db = db
        self.accounts = accounts

    def public(self, account):
        return {
            **self.accounts.public(account),
            "active": account.active,
            "revision": account.session_version,
            "createdAt": account.created_at.replace(tzinfo=timezone.utc).isoformat(),
        }

    def list_users(self, query):
        try:
            page = int(query.get("page", "1"))
        except (ValueError, TypeError):
            raise AccountError("页码不正确。") from None
        if not 1 <= page <= 100000:
            raise AccountError("页码不正确。")
        search = query.get("q", "").strip()
        status = query.get("status", "all")
        role = query.get("role", "all")
        if len(search) > 40 or status not in ("all", "active", "disabled") or role not in ("all", "admin", "user"):
            raise AccountError("筛选条件不正确。")
        filters = []
        if search:
            pattern = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            filters.append(Account.username.like(pattern, escape="\\") |
                           Account.display_name.like(pattern, escape="\\"))
        if status != "all":
            filters.append(Account.active.is_(status == "active"))
        if role != "all":
            filters.append(Account.is_admin.is_(role == "admin"))
        total = self.db.scalar(select(func.count()).select_from(Account).where(*filters))
        rows = self.db.scalars(select(Account).where(*filters).order_by(Account.created_at.desc(), Account.username)
                               .offset((page - 1) * 25).limit(25)).all()
        return {"users": [self.public(row) for row in rows], "total": total, "page": page, "pageSize": 25}

    def locked_target(self, actor_name, actor_version, username, revision):
        username = username_value(username)
        if type(revision) is not int or revision < 1:
            raise AccountError("请重新加载用户资料后再编辑。", 409)
        # Lock in a stable order and re-check the actor after waiting: concurrent
        # administrators cannot deactivate each other using stale permissions.
        rows = self.db.scalars(select(Account).where(Account.username.in_([actor_name, username]))
                               .order_by(Account.username).with_for_update()
                               .execution_options(populate_existing=True)).all()
        accounts = {row.username: row for row in rows}
        actor = accounts.get(actor_name)
        if not actor or not actor.active or not actor.is_admin or actor.session_version != actor_version:
            raise AccountError("管理员权限已失效，请重新登录。", 403)
        if username == actor_name:
            raise AccountError("不能在管理控制台修改自己的账号，请前往个人设置。")
        target = accounts.get(username)
        if not target:
            raise AccountError("账号不存在。", 404)
        if target.session_version != revision:
            raise AccountError("账号已被其他管理员更新，请刷新后重试。", 409)
        return target

    def update(self, actor_name, actor_version, username, data):
        if set(data) - {"revision", "displayName", "defaultPeriod", "active", "isAdmin"}:
            raise AccountError("包含不支持的账号字段。")
        if len(data) < 2:
            raise AccountError("请提交需要修改的资料。")
        for key in ("active", "isAdmin"):
            if key in data and type(data[key]) is not bool:
                raise AccountError("角色和账号状态必须为有效的开关值。")
        if "defaultPeriod" in data and data["defaultPeriod"] not in ("day", "week", "month", "year"):
            raise AccountError("请选择有效的默认计划。")
        name = profile_name(data["displayName"], username) if "displayName" in data else None
        target = self.locked_target(actor_name, actor_version, username, data.get("revision"))
        if name is not None:
            target.display_name = name
        if "defaultPeriod" in data:
            target.preferences = {**(target.preferences or {}), "defaultPeriod": data["defaultPeriod"]}
        if "active" in data:
            target.active = data["active"]
        if "isAdmin" in data:
            target.is_admin = data["isAdmin"]
        target.session_version += 1
        self.db.flush()
        return self.public(target)

    def reset_password(self, actor_name, actor_version, username, data):
        if set(data) != {"revision", "newPassword"}:
            raise AccountError("请提交新密码和用户版本。")
        hashed = generate_password_hash(password_value(data.get("newPassword")))
        target = self.locked_target(actor_name, actor_version, username, data.get("revision"))
        target.password_hash = hashed
        target.session_version += 1
        self.db.flush()
        return self.public(target)
