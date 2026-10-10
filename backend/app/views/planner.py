from flask import Blueprint, jsonify, request

from app import db
from app.services.planner_manager import PlanConflict, PlannerManager
from app.services.period_planner_manager import PeriodPlannerManager
from app.views.authority import authority_check

planner_bp = Blueprint("planner", __name__)
manager = PlannerManager(db)
period_manager = PeriodPlannerManager(db)


@planner_bp.errorhandler(ValueError)
def invalid_plan(error):
    return jsonify({"error": str(error)}), 400


@planner_bp.errorhandler(PlanConflict)
def stale_plan(error):
    return jsonify({"error": "This plan was changed in another window."}), 409


@planner_bp.get("/api/planner/day/<day>")
@authority_check()
def get_day(day, owner):
    return manager.get_day(owner, day)


@planner_bp.put("/api/planner/day/<day>")
@authority_check()
def save_day(day, owner):
    if request.content_length and request.content_length > 2_000_000:
        return jsonify({"error": "Plan is too large"}), 413
    return manager.save_day(owner, day, request.get_json())


@planner_bp.get("/api/planner/overview")
@authority_check()
def overview(owner):
    return manager.overview(owner, request.args.get("start"), request.args.get("end"))


@planner_bp.get("/api/planner/period/<period>/<day>")
@authority_check()
def get_period(period, day, owner):
    return period_manager.get_plan(owner, period, day)


@planner_bp.put("/api/planner/period/<period>/<day>")
@authority_check()
def save_period(period, day, owner):
    if request.content_length and request.content_length > 2_000_000:
        return jsonify({"error": "Plan is too large"}), 413
    return period_manager.save_plan(owner, period, day, request.get_json())


@planner_bp.get("/api/planner/agenda/<day>")
@authority_check()
def reminder_agenda(day, owner):
    return jsonify([
        manager.get_day(owner, day),
        *[period_manager.get_plan(owner, period, day) for period in ("week", "month", "year")],
    ])
