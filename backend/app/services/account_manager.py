from datetime import datetime, timedelta
import hashlib
import re
import secrets

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.account import Account, AuthThrottle
from app.models.base import Base


class AccountError(ValueError):
    def __init__(self, message, status=400):
        self.status = status
        super().__init__(message)


def username_value(value):
    if not isinstance(value, str):
        raise AccountError("请输入账号。")
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]{3,14}", value):
        raise AccountError("账号需为 4–15 位小写字母、数字或下划线，且以字母开头。")
    return value


def password_value(value):
    if not isinstance(value, str) or not 10 <= len(value) <= 128:
        raise AccountError("密码长度需为 10–128 位。")
    if value.isspace():
        raise AccountError("密码不能全部为空格。")
    return value


def profile_name(value, username):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 40:
        raise AccountError("昵称需为 1–40 个字符。")
    return value.strip() or username


class AccountManager:
    def __init__(self, db):
        self.db = db
        self._dummy_hash = generate_password_hash(secrets.token_urlsafe(32))

    def get(self, username):
        return self.db.get(Account, username) if isinstance(username, str) else None

    def public(self, account):
        return {
            "username": account.username,
            "displayName": account.display_name,
            "isAdmin": account.is_admin,
            "preferences": {"defaultPeriod": (account.preferences or {}).get("defaultPeriod", "day")},
        }

    def create(self, data, *, admin=False):
        username = username_value(data.get("username"))
        password = password_value(data.get("password"))
        name = profile_name(data.get("displayName", username), username)
        if self.get(username):
            raise AccountError("这个账号已被注册，请更换账号。", 409)
        if not admin:
            # Existing local owners must be migrated by the operator, never claimed by signup.
            for table in Base.metadata.sorted_tables:
                if "owner" in table.c and self.db.scalar(
                    select(table.c.owner).where(table.c.owner == username).limit(1)
                ) is not None:
                    raise AccountError("这个账号已有历史数据，请联系管理员迁移或更换账号。", 409)
        account = Account(username=username, display_name=name,
                          password_hash=generate_password_hash(password), is_admin=admin,
                          active=True, session_version=1, preferences={"defaultPeriod": "day"})
        try:
            with self.db.begin_nested():
                self.db.add(account)
                self.db.flush()
        except IntegrityError:
            raise AccountError("这个账号已被注册，请更换账号。", 409) from None
        return account

    def authenticate(self, username, password):
        username = username.strip().lower() if isinstance(username, str) else ""
        password = password if isinstance(password, str) and len(password) <= 128 else ""
        account = self.get(username)
        valid = check_password_hash(account.password_hash if account else self._dummy_hash, password)
        if not valid or not account or not account.active:
            raise AccountError("账号或密码错误。", 401)
        return account

    def update_profile(self, account, data):
        name = profile_name(data.get("displayName"), account.username)
        period = data.get("defaultPeriod")
        if period not in ("day", "week", "month", "year"):
            raise AccountError("请选择有效的默认计划。")
        account.display_name = name
        account.preferences = {"defaultPeriod": period}
        self.db.flush()
        return account

    def change_password(self, account, data):
        current = data.get("currentPassword")
        if not isinstance(current, str) or len(current) > 128 or not check_password_hash(account.password_hash, current):
            raise AccountError("当前密码不正确。", 400)
        password = password_value(data.get("newPassword"))
        if secrets.compare_digest(current.encode(), password.encode()):
            raise AccountError("新密码不能与当前密码相同。")
        # A conditional update also invalidates other sessions if two requests race.
        changed = self.db.execute(update(Account).where(Account.username == account.username,
            Account.session_version == account.session_version).values(
                password_hash=generate_password_hash(password), session_version=Account.session_version + 1))
        if changed.rowcount != 1:
            raise AccountError("账号已在其他窗口更新，请重新登录。", 409)
        self.db.flush()

    def throttle(self, category, identity, limit, seconds=900):
        now = datetime.utcnow()
        key = hashlib.sha256(f"{category}:{identity}".encode()).hexdigest()
        self.db.execute(delete(AuthThrottle).where(AuthThrottle.expires_at <= now))
        try:
            with self.db.begin_nested():
                row = self.db.get(AuthThrottle, key)
                if row is None:
                    self.db.add(AuthThrottle(key=key, count=0, expires_at=now + timedelta(seconds=seconds)))
                    self.db.flush()
        except IntegrityError:
            pass
        result = self.db.execute(update(AuthThrottle).where(AuthThrottle.key == key,
            AuthThrottle.count < limit).values(count=AuthThrottle.count + 1))
        self.db.commit()
        if result.rowcount != 1:
            raise AccountError("尝试次数过多，请稍后再试。", 429)

    def bootstrap(self, username, password):
        if not username and not password:
            return
        if not username or not password:
            raise RuntimeError("Both bootstrap username and password are required")
        if not self.get(username_value(username)):
            self.create({"username": username, "password": password}, admin=True)
            self.db.commit()
