from flask import Blueprint, jsonify, request

from app import db
from app.services.focus_manager import FocusConflict, FocusManager
from app.views.authority import authority_check

focus_bp = Blueprint("focus", __name__)
manager = FocusManager(db)


@focus_bp.errorhandler(ValueError)
def invalid_focus(error):
    return jsonify({"error": str(error)}), 400


@focus_bp.errorhandler(FocusConflict)
def focus_conflict(error):
    return jsonify({"error": "Focus session changed. Reload and try again."}), 409


@focus_bp.get("/api/focus/state")
@authority_check()
def focus_state(owner):
    return manager.state(owner)


@focus_bp.post("/api/focus/state")
@authority_check()
def focus_command(owner):
    if request.content_length and request.content_length > 8000:
        return jsonify({"error": "Request is too large"}), 413
    return manager.command(owner, request.get_json())


@focus_bp.get("/api/focus/records")
@authority_check()
def focus_records(owner):
    return manager.records(owner, request.args.get("day"), request.args.get("offset", "0"))
