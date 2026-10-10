from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import math
import secrets
from threading import Lock
import time

import requests
from sqlalchemy import select

from app.models.account import Account
from app.models.location import SharedLocation
from app.services.account_manager import AccountError


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def number(value, minimum, maximum):
    if isinstance(value, bool):
        raise AccountError("请输入有效的数值。")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise AccountError("请输入有效的数值。") from None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise AccountError("数值超出有效范围。")
    return result


def token_matches(expected, provided):
    return (isinstance(provided, str) and provided.isascii() and 1 <= len(provided) <= 64
            and secrets.compare_digest(expected, provided))


class LocationManager:
    def __init__(self, db):
        self.db = db

    def locked(self, username, version):
        # Serialize consent changes and samples on the account row, including
        # the first sample, so a delayed request cannot undo a revocation.
        account = self.db.scalar(select(Account).where(Account.username == username).with_for_update()
                                 .execution_options(populate_existing=True))
        if not account or not account.active or account.session_version != version:
            raise AccountError("账号状态已变化，请重新登录。", 401)
        row = self.db.get(SharedLocation, username)
        if row is None:
            row = SharedLocation(owner=username, enabled=False, token="")
            self.db.add(row)
        return row

    def owner_state(self, username):
        row = self.db.get(SharedLocation, username)
        return {"enabled": bool(row and row.enabled), "token": row.token if row and row.enabled else None,
                "consentAt": iso(row.consent_at) if row else None,
                "receivedAt": iso(row.received_at) if row and row.enabled else None}

    def consent(self, username, version, data):
        if set(data) != {"enabled"} or type(data["enabled"]) is not bool:
            raise AccountError("定位授权无效。")
        row = self.locked(username, version)
        row.enabled = data["enabled"]
        row.token = secrets.token_urlsafe(32) if row.enabled else ""
        row.session_version = version
        row.consent_at = utcnow() if row.enabled else None
        self.clear_sample(row)
        self.db.flush()
        return self.owner_state(username)

    @staticmethod
    def clear_sample(row):
        row.latitude = row.longitude = row.accuracy = row.captured_at = row.received_at = None

    def stop(self, username, version, data):
        if set(data) != {"token"} or not isinstance(data["token"], str):
            raise AccountError("定位会话无效。")
        row = self.locked(username, version)
        # Closing an older tab must not revoke a newer tab's location session.
        if row.enabled and token_matches(row.token, data["token"]):
            row.enabled = False
            row.token = ""
            row.consent_at = None
            self.clear_sample(row)
        self.db.flush()
        return {"stopped": True}

    def sample(self, username, version, data):
        if set(data) != {"token", "latitude", "longitude", "accuracy", "capturedAt"}:
            raise AccountError("定位数据不完整。")
        latitude = number(data["latitude"], -90, 90)
        longitude = number(data["longitude"], -180, 180)
        accuracy = number(data["accuracy"], 0, 100000)
        timestamp = number(data["capturedAt"], 0, 4102444800000)
        captured = datetime.fromtimestamp(timestamp / 1000, timezone.utc).replace(tzinfo=None)
        now = utcnow()
        if captured < now - timedelta(minutes=2) or captured > now + timedelta(seconds=30):
            raise AccountError("定位结果已过期，请重新定位。")
        row = self.locked(username, version)
        if not row.enabled or row.session_version != version or not token_matches(row.token, data["token"]):
            raise AccountError("位置共享已关闭或授权已更新。", 409)
        if row.captured_at and captured <= row.captured_at:
            return {"receivedAt": iso(row.received_at)}
        row.latitude, row.longitude, row.accuracy = latitude, longitude, accuracy
        row.captured_at, row.received_at = captured, now
        self.db.flush()
        return {"receivedAt": iso(row.received_at)}

    def admin_locations(self, usernames):
        if not usernames or len(usernames) > 25 or any(
                not isinstance(name, str) or not 1 <= len(name) <= 15 for name in usernames):
            raise AccountError("每次最多查询 25 位用户。")
        accounts = self.db.scalars(select(Account).where(Account.username.in_(usernames))).all()
        rows = {row.owner: row for row in self.db.scalars(
            select(SharedLocation).where(SharedLocation.owner.in_(usernames))).all()}
        now = utcnow()
        result = []
        for account in accounts:
            row = rows.get(account.username)
            item = {"username": account.username, "status": "not_shared", "position": None}
            if not account.active:
                item["status"] = "disabled"
            elif row and row.enabled and row.session_version == account.session_version:
                item["status"] = "waiting"
                if row.captured_at and row.received_at:
                    age = max((now - row.captured_at).total_seconds(), (now - row.received_at).total_seconds())
                    item["status"] = "live" if age <= 90 else "stale" if age <= 1800 else "expired"
                    if age <= 1800:
                        item["position"] = {"latitude": row.latitude, "longitude": row.longitude,
                                            "accuracy": row.accuracy, "capturedAt": iso(row.captured_at),
                                            "receivedAt": iso(row.received_at)}
            result.append(item)
        return {"locations": result, "serverTime": iso(now)}

    def weather_position(self, username):
        row = self.db.get(SharedLocation, username)
        account = self.db.get(Account, username)
        if (not row or not account or not row.enabled or row.session_version != account.session_version
                or not row.captured_at or utcnow() - row.captured_at > timedelta(minutes=2)):
            raise AccountError("请先同意定位并取得当前位置，再使用环境舒适度。", 409)
        return {"latitude": row.latitude, "longitude": row.longitude}


class WeatherService:
    """Bounded, coarse-coordinate cache; precise fixes never leave this service."""

    def __init__(self):
        self.cache = OrderedDict()
        self.lock = Lock()

    def fetch(self, kind, key, url, params, ttl):
        cache_key = (kind, key)
        with self.lock:
            cached = self.cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < ttl:
                self.cache.move_to_end(cache_key)
                return cached[1]
        try:
            with requests.Session() as client:
                client.trust_env = False
                response = client.get(url, params=params, timeout=(3, 8), allow_redirects=False)
                response.raise_for_status()
                data = response.json()
            if not isinstance(data, dict) or data.get("error"):
                raise ValueError("Invalid weather response")
        except (requests.RequestException, ValueError):
            raise AccountError("天气服务暂时不可用，请稍后重试。", 503) from None
        with self.lock:
            self.cache[cache_key] = (time.monotonic(), data)
            self.cache.move_to_end(cache_key)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
        return data

    def weather(self, data):
        if set(data) != {"latitude", "longitude"}:
            raise AccountError("请先取得当前位置。")
        lat, lon = round(number(data["latitude"], -90, 90), 2), round(number(data["longitude"], -180, 180), 2)
        current_fields = ("temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day",
                          "precipitation", "weather_code", "wind_speed_10m")
        hourly_fields = ("temperature_2m", "apparent_temperature", "relative_humidity_2m",
                         "precipitation_probability", "weather_code", "wind_speed_10m", "uv_index")
        daily_fields = ("temperature_2m_max", "temperature_2m_min", "sunrise", "sunset",
                        "precipitation_probability_max", "uv_index_max")
        raw = self.fetch("weather", (lat, lon), "https://api.open-meteo.com/v1/forecast", {
            "latitude": lat, "longitude": lon, "current": ",".join(current_fields),
            "hourly": ",".join(hourly_fields), "daily": ",".join(daily_fields),
            "timezone": "auto", "timeformat": "unixtime", "wind_speed_unit": "ms", "forecast_days": 1,
        }, 300)

        def finite(value):
            return value if type(value) in (int, float) and math.isfinite(value) else None

        try:
            current = {field: finite(raw["current"].get(field)) for field in ("time", *current_fields)}
            times = raw["hourly"]["time"]
            hourly = [{field: finite(raw["hourly"].get(field, [None] * len(times))[index])
                       for field in ("time", *hourly_fields)} for index in range(min(len(times), 25))]
            daily = {field: finite(raw["daily"].get(field, [None])[0]) for field in ("time", *daily_fields)}
            if current["time"] is None or not hourly or any(hour["time"] is None for hour in hourly):
                raise ValueError("Weather times missing")
            return {"timezone": raw["timezone"], "current": current, "hourly": hourly, "daily": daily,
                    "provider": "Open-Meteo", "coordinatePrecision": 0.01}
        except (KeyError, TypeError, IndexError, ValueError, AttributeError):
            raise AccountError("天气数据不完整，请稍后刷新。", 503) from None
