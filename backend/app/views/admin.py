from flask import Blueprint, current_app, jsonify, request, session

from app import account_manager, db
from app.security import current_account
from app.services.account_manager import AccountError
from app.services.admin_manager import AdminManager
from app.views.login import payload

admin_bp = Blueprint("admin_accounts", __name__)
manager = AdminManager(db, account_manager)


def required_admin():
    if current_app.config["LOCAL_MODE"]:
        raise AccountError("本地模式不开放平台账号管理。", 403)
    account = current_account(db)
    if not account:
        raise AccountError("请先登录。", 401)
    if not account.is_admin:
        raise AccountError("仅管理员可访问用户管理。", 403)
    return account.username, session["auth_version"]


@admin_bp.errorhandler(AccountError)
def admin_error(error):
    db.rollback()
    return jsonify({"error": str(error)}), error.status


@admin_bp.get("/api/admin/users")
def users():
    required_admin()
    return manager.list_users(request.args)


@admin_bp.patch("/api/admin/users/<username>")
def update_user(username):
    actor, version = required_admin()
    user = manager.update(actor, version, username, payload())
    db.commit()
    current_app.logger.info("Account updated by administrator %s: %s", actor, user["username"])
    return {"user": user}


@admin_bp.post("/api/admin/users/<username>/password")
def reset_password(username):
    actor, version = required_admin()
    account_manager.throttle("admin-password", actor, 15)
    user = manager.reset_password(actor, version, username, payload())
    db.commit()
    current_app.logger.info("Account password reset by administrator %s: %s", actor, user["username"])
    return {"user": user, "message": "密码已重置，该用户需要重新登录。"}
