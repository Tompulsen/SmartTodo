from flask import Blueprint, current_app, jsonify, request

from app import account_manager, db
from app.security import current_account
from app.services.account_manager import AccountError
from app.services.connection_manager import ConnectionManager

connections_bp = Blueprint("connections", __name__)
manager = ConnectionManager(db)


def required_user():
    if current_app.config["LOCAL_MODE"]:
        raise AccountError("待办关联仅在账号模式下可用。", 403)
    if not current_account(db):
        raise AccountError("请先登录。", 401)
    return current_account(db).username


def request_data():
    if request.content_length and request.content_length > 16384:
        raise AccountError("提交内容过大。", 413)
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        raise AccountError("请提交有效的数据。")
    return data


@connections_bp.errorhandler(AccountError)
def connection_error(error):
    db.rollback()
    return jsonify({"error": str(error)}), error.status


@connections_bp.get("/api/connections")
def overview():
    return manager.overview(required_user())


@connections_bp.post("/api/connections/invitations")
def invite():
    owner = required_user()
    account_manager.throttle("connection-invite", owner, 30)
    data = request_data()
    return manager.invite(owner, data.get("username")), 201


@connections_bp.patch("/api/connections/<int:connection_id>/invitation")
def respond(connection_id):
    owner = required_user()
    data = request_data()
    return manager.respond(owner, connection_id, data.get("action"))


@connections_bp.delete("/api/connections/<int:connection_id>")
def remove(connection_id):
    result = manager.remove(required_user(), connection_id)
    db.commit()
    return result


@connections_bp.patch("/api/connections/<int:connection_id>/sharing")
def sharing(connection_id):
    owner = required_user()
    data = request_data()
    return manager.set_sharing(owner, connection_id, data.get("enabled"))


@connections_bp.get("/api/connections/<int:connection_id>/today")
def today_plan(connection_id):
    return manager.today_plan(required_user(), connection_id)


@connections_bp.get("/api/connections/<int:connection_id>/messages")
def messages(connection_id):
    return manager.messages(
        required_user(), connection_id,
        after=request.args.get("after"), before=request.args.get("before"),
        visible_from=request.args.get("visibleFrom"),
    )


@connections_bp.post("/api/connections/<int:connection_id>/messages")
def send_message(connection_id):
    owner = required_user()
    account_manager.throttle("connection-message", owner, 120, seconds=60)
    return manager.send(owner, connection_id, request_data()), 201


@connections_bp.post("/api/connections/<int:connection_id>/share-today")
def share_today(connection_id):
    owner = required_user()
    account_manager.throttle("connection-message", owner, 120, seconds=60)
    return manager.share_today(owner, connection_id, request_data()), 201


@connections_bp.delete("/api/connections/<int:connection_id>/messages/<int:message_id>")
def revoke_plan(connection_id, message_id):
    return manager.revoke_plan(required_user(), connection_id, message_id)


@connections_bp.post("/api/connections/<int:connection_id>/read")
def mark_read(connection_id):
    owner = required_user()
    data = request_data()
    return manager.mark_read(owner, connection_id, data.get("messageId"))
