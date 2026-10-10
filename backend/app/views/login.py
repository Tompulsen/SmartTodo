import secrets

from flask import Blueprint, current_app, jsonify, request, session

from app import account_manager, config_manager, db
from app.security import current_account
from app.services.account_manager import AccountError

login_bp = Blueprint("login", __name__)


def payload():
    if request.content_length and request.content_length > 16384:
        raise AccountError("提交内容过大。", 413)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AccountError("请提交有效的表单。")
    return data


def establish(account):
    session.clear()
    session.permanent = True
    session["username"] = account.username
    session["auth_version"] = account.session_version
    session["csrf_token"] = secrets.token_urlsafe(32)
    return {"user": account_manager.public(account), "csrfToken": session["csrf_token"], "localMode": False}


def required():
    account = current_account(db)
    if not account:
        raise AccountError("请先登录。", 401)
    return account


@login_bp.errorhandler(AccountError)
def account_error(error):
    db.rollback()
    response = jsonify({"error": str(error)})
    if error.status == 429:
        response.headers["Retry-After"] = "900"
    return response, error.status


@login_bp.get("/api/auth/session")
def auth_session():
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    if current_app.config["LOCAL_MODE"]:
        owner = session.get("username")
        return {"localMode": True, "csrfToken": session["csrf_token"], "registrationEnabled": False,
                "user": {"username": owner, "displayName": owner, "isAdmin": config_manager.is_admin_user(owner),
                         "preferences": {"defaultPeriod": "day"}} if owner else None}
    account = current_account(db)
    return {"user": account_manager.public(account) if account else None,
            "localMode": False, "csrfToken": session["csrf_token"],
            "registrationEnabled": current_app.config["REGISTRATION_ENABLED"]}


@login_bp.post("/api/auth/register")
def register():
    if current_app.config["LOCAL_MODE"] or not current_app.config["REGISTRATION_ENABLED"]:
        raise AccountError("当前站点未开放注册。", 403)
    account_manager.throttle("register", request.remote_addr or "", 10, 3600)
    account = account_manager.create(payload())
    db.commit()
    return establish(account), 201


@login_bp.post("/api/login")
def login():
    data = payload()
    account_manager.throttle("login-ip", request.remote_addr or "", 50)
    name = str(data.get("username", "")).strip().lower()[:100]
    account_manager.throttle("login-account", name, 15)
    account = account_manager.authenticate(data.get("username"), data.get("password"))
    return establish(account)


@login_bp.post("/api/logout")
def logout():
    session.clear()
    session["csrf_token"] = secrets.token_urlsafe(32)
    return {"user": None, "csrfToken": session["csrf_token"], "localMode": False}


@login_bp.patch("/api/account/profile")
def profile():
    account = account_manager.update_profile(required(), payload())
    db.commit()
    return {"user": account_manager.public(account)}


@login_bp.post("/api/account/password")
def change_password():
    owner = required().username
    account_manager.throttle("password", owner, 10)
    account_manager.change_password(account_manager.get(owner), payload())
    db.commit()
    session.clear()
    return {"message": "密码已修改，请重新登录。"}
