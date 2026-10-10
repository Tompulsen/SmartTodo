from datetime import timedelta, timezone
import unittest
from unittest.mock import patch

import requests
from sqlalchemy import select, func

import app as application
from app.models.account import Account
from app.models.location import SharedLocation
from app.services.account_manager import AccountError
from app.services.environment_manager import WeatherService, utcnow
from app.tests.services import account_test, admin_test


class EnvironmentTests(unittest.TestCase):
    setUp = account_test.AccountTests.setUp
    tearDown = account_test.AccountTests.tearDown
    token = account_test.AccountTests.token
    send = account_test.AccountTests.send
    register = account_test.AccountTests.register
    login_admin = admin_test.AdminTests.login_admin

    def enable(self):
        result = self.send("/api/environment/location", {"enabled": True}, "PATCH")
        self.assertEqual(result.status_code, 200)
        return result.json["token"]

    def sample(self, token, **extra):
        return self.send("/api/environment/location", {
            "token": token, "latitude": 31.230416, "longitude": 121.473701, "accuracy": 15,
            "capturedAt": utcnow().replace(tzinfo=timezone.utc).timestamp() * 1000, **extra
        })

    def admin_location(self, admin):
        response = admin.get("/api/admin/locations?users=alice")
        self.assertEqual(response.status_code, 200)
        return response.json["locations"][0]

    def test_anonymous_member_and_csrf_protection(self):
        self.assertEqual(self.client.get("/api/admin/locations?users=alice").status_code, 401)
        self.assertEqual(self.send("/api/environment/weather", {"latitude": 0, "longitude": 0}).status_code, 401)
        self.register()
        self.assertEqual(self.client.get("/api/admin/locations?users=alice").status_code, 403)
        with self.client.session_transaction() as session:
            session["role"] = ["ROLE_ADMIN"]
        self.assertEqual(self.client.get("/api/admin/locations?users=alice").status_code, 403)
        self.assertEqual(self.client.patch("/api/environment/location", json={"enabled": True}).status_code, 403)
        self.assertEqual(self.sample("forged-token").status_code, 409)
        admin = self.login_admin()
        self.assertEqual(self.admin_location(admin)["position"], None)

    def test_use_requires_fresh_location_and_stop_clears_it(self):
        self.register()
        admin = self.login_admin()
        self.assertEqual(self.send("/api/environment/weather", {}).status_code, 409)
        token = self.enable()
        self.assertEqual(self.send("/api/environment/weather", {}).status_code, 409)
        self.assertEqual(self.sample(token).status_code, 200)
        position = self.admin_location(admin)
        self.assertEqual(position["status"], "live")
        self.assertEqual(position["position"]["latitude"], 31.230416)
        self.assertNotIn(token, str(position))
        with patch("app.views.environment.weather.weather", return_value={"ok": True}) as weather:
            self.assertEqual(self.send("/api/environment/weather", {"latitude": 0, "longitude": 0}).status_code, 200)
            weather.assert_called_once_with({"latitude": 31.230416, "longitude": 121.473701})
        self.assertEqual(self.send("/api/environment/location/stop", {"token": token}).status_code, 200)
        self.assertEqual(self.admin_location(admin)["status"], "not_shared")
        self.assertEqual(self.sample(token).status_code, 409)
        self.assertEqual(self.send("/api/environment/weather", {}).status_code, 409)
        with self.app.app_context():
            row = application.db.get(SharedLocation, "alice")
            self.assertIsNone(row.latitude)
            self.assertIsNone(row.received_at)
            self.assertEqual(row.token, "")

    def test_tab_tokens_and_user_isolation(self):
        self.register()
        old_token = self.enable()
        token = self.enable()
        self.assertEqual(self.sample(old_token).status_code, 409)
        self.assertEqual(self.sample(token).status_code, 200)
        self.send("/api/environment/location/stop", {"token": old_token})
        self.assertTrue(self.client.get("/api/environment/location").json["enabled"])
        other = self.app.test_client()
        self.register("bobbie", other)
        self.assertIsNone(other.get("/api/environment/location").json["token"])
        self.send("/api/environment/location/stop", {"token": token}, client=other)
        self.assertTrue(self.client.get("/api/environment/location").json["enabled"])
        self.assertEqual(self.sample(token, owner="bobbie").status_code, 400)

    def test_invalid_stale_and_out_of_order_samples(self):
        self.register()
        token = self.enable()
        self.assertEqual(self.sample("非有效令牌").status_code, 409)
        self.assertEqual(self.send("/api/environment/location/stop", {"token": "无效令牌"}).status_code, 200)
        for extra in [{"latitude": 91}, {"longitude": -181}, {"latitude": True}, {"accuracy": -1},
                      {"latitude": "NaN"}, {"capturedAt": 0}, {"accuracy": "Infinity"}, {"latitude": 10 ** 500}]:
            self.assertEqual(self.sample(token, **extra).status_code, 400)
        timestamp = (utcnow() - timedelta(seconds=10)).replace(tzinfo=timezone.utc).timestamp() * 1000
        self.assertEqual(self.sample(token, capturedAt=timestamp).status_code, 200)
        self.assertEqual(self.sample(token, latitude=0, capturedAt=timestamp - 1000).status_code, 200)
        with self.app.app_context():
            self.assertEqual(application.db.get(SharedLocation, "alice").latitude, 31.230416)
            self.assertEqual(application.db.scalar(select(func.count()).select_from(SharedLocation)), 1)

    def test_stale_expired_disabled_and_revoked_sessions(self):
        self.register()
        admin = self.login_admin()
        token = self.enable()
        self.sample(token)
        with self.app.app_context():
            row = application.db.get(SharedLocation, "alice")
            row.captured_at = row.received_at = utcnow() - timedelta(minutes=3)
            application.db.commit()
        self.assertEqual(self.admin_location(admin)["status"], "stale")
        self.assertEqual(self.send("/api/environment/weather", {}).status_code, 409)
        with self.app.app_context():
            row = application.db.get(SharedLocation, "alice")
            row.captured_at = row.received_at = utcnow() - timedelta(minutes=31)
            application.db.commit()
        self.assertEqual(self.admin_location(admin)["status"], "expired")
        self.assertIsNone(self.admin_location(admin)["position"])
        self.sample(token)
        with self.app.app_context():
            application.db.get(Account, "alice").session_version += 1
            application.db.commit()
        self.assertEqual(self.admin_location(admin)["status"], "not_shared")
        self.assertEqual(self.sample(token).status_code, 401)
        with self.app.app_context():
            application.db.get(Account, "alice").active = False
            application.db.commit()
        self.assertEqual(self.admin_location(admin)["status"], "disabled")

    def test_local_mode_has_weather_but_no_admin_location_upload(self):
        self.app.config["LOCAL_MODE"] = True
        self.assertEqual(self.send("/api/environment/location", {"enabled": True}, "PATCH").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/locations?users=alice").status_code, 403)
        with patch("app.views.environment.weather.weather", return_value={"ok": True}) as weather:
            self.assertEqual(self.send("/api/environment/weather", {"latitude": 0, "longitude": 0}).status_code, 200)
            weather.assert_called_once_with({"latitude": 0, "longitude": 0})


class WeatherServiceTests(unittest.TestCase):
    def forecast(self):
        return {
            "timezone": "Asia/Shanghai", "current": {"time": 1791600000, "temperature_2m": 0, "wind_speed_10m": 0},
            "hourly": {"time": [1791600000, 1791603600], "temperature_2m": [0, 2]},
            "daily": {"time": [1791600000], "sunrise": [1791583000], "sunset": [1791625000]}
        }

    def test_rounded_request_cache_units_and_null_values(self):
        service = WeatherService()
        with patch("app.services.environment_manager.requests.Session") as session:
            client = session.return_value.__enter__.return_value
            client.get.return_value.json.return_value = self.forecast()
            result = service.weather({"latitude": 31.230416, "longitude": 121.473701})
            args, kwargs = client.get.call_args
            self.assertEqual(args[0], "https://api.open-meteo.com/v1/forecast")
            self.assertEqual(kwargs["params"]["latitude"], 31.23)
            self.assertEqual(kwargs["params"]["longitude"], 121.47)
            self.assertEqual(kwargs["params"]["timeformat"], "unixtime")
            self.assertEqual(kwargs["params"]["wind_speed_unit"], "ms")
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(result["current"]["temperature_2m"], 0)
            self.assertIsNone(result["current"]["relative_humidity_2m"])
            service.weather({"latitude": 31.23042, "longitude": 121.47371})
            self.assertEqual(client.get.call_count, 1)

    def test_upstream_timeout_and_incomplete_response(self):
        service = WeatherService()
        with patch("app.services.environment_manager.requests.Session") as session:
            session.return_value.__enter__.return_value.get.side_effect = requests.Timeout("private upstream details")
            with self.assertRaises(AccountError) as error:
                service.weather({"latitude": 0, "longitude": 0})
            self.assertEqual(error.exception.status, 503)
            self.assertNotIn("private", str(error.exception))
        with patch.object(service, "fetch", return_value={"current": {}}):
            with self.assertRaises(AccountError):
                service.weather({"latitude": 0, "longitude": 0})
        for bad in [{"latitude": 180, "longitude": 0}, {"latitude": "inf", "longitude": 0}, {"url": "http://localhost"}]:
            with self.assertRaises(AccountError):
                service.weather(bad)


if __name__ == "__main__":
    unittest.main()
