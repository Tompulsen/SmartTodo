from flask import Blueprint, current_app, jsonify, request, session

from app import account_manager, db
from app.services.account_manager import AccountError
from app.services.environment_manager import LocationManager, WeatherService
from app.views.admin import required_admin
from app.views.login import payload, required

environment_bp = Blueprint("environment", __name__)
locations = LocationManager(db)
weather = WeatherService()


@environment_bp.errorhandler(AccountError)
def environment_error(error):
    db.rollback()
    return jsonify({"error": str(error)}), error.status


def weather_access():
    if not current_app.config["LOCAL_MODE"]:
        owner = required().username
        account_manager.throttle("weather", owner, 60, 300)


def location_access():
    if current_app.config["LOCAL_MODE"]:
        raise AccountError("本地模式不向管理员共享位置。", 403)
    return required().username, session["auth_version"]


@environment_bp.post("/api/environment/weather")
def forecast():
    weather_access()
    data = payload() if current_app.config["LOCAL_MODE"] else locations.weather_position(required().username)
    return weather.weather(data)


@environment_bp.get("/api/environment/location")
def own_location():
    owner, _ = location_access()
    return locations.owner_state(owner)


@environment_bp.patch("/api/environment/location")
def location_consent():
    owner, version = location_access()
    result = locations.consent(owner, version, payload())
    db.commit()
    return result


@environment_bp.post("/api/environment/location")
def location_sample():
    owner, version = location_access()
    result = locations.sample(owner, version, payload())
    db.commit()
    return result


@environment_bp.get("/api/admin/locations")
def admin_locations():
    required_admin()
    return locations.admin_locations(request.args.get("users", "").split(","))


@environment_bp.post("/api/environment/location/stop")
def stop_location():
    owner, version = location_access()
    result = locations.stop(owner, version, payload())
    db.commit()
    return result
