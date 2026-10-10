import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import scoped_session, sessionmaker

from app.models.base import Base
from app.models.focus import FocusRecord
from app.services.focus_manager import FocusConflict, FocusManager
from app.services.planner_manager import PlannerManager
from app.services.period_planner_manager import PeriodPlannerManager


class FocusTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = scoped_session(sessionmaker(bind=self.engine))
        self.now = 1791511200000
        self.manager = FocusManager(self.db, lambda: self.now)

    def tearDown(self):
        self.db.remove()
        self.engine.dispose()

    def command(self, action, owner="admin", **extra):
        state = self.manager.state(owner)
        result = self.manager.command(owner, {
            "revision": state["revision"], "id": (state["session"] or {}).get("id"), "action": action, **extra
        })
        self.db.commit()
        return result

    def start(self, mode="pomodoro", duration=1500, **extra):
        return self.command("start", mode=mode, duration=duration, **extra)

    def count(self):
        return self.db.scalar(select(func.count()).select_from(FocusRecord))

    def test_countdown_uses_deadline_and_records_once(self):
        start = self.start()
        self.now += 1600000
        final = self.manager.state("admin")
        self.db.commit()
        self.assertEqual(final["session"]["status"], "completed")
        self.assertEqual(final["session"]["elapsedMs"], 1500000)
        self.assertEqual(final["session"]["finishedAt"], start["serverNow"] + 1500000)
        self.manager.state("admin")
        self.assertEqual(self.count(), 1)
        self.assertEqual(final["revision"], 2)

    def test_pause_refresh_resume_excludes_paused_time(self):
        self.start()
        self.now += 100000
        paused = self.command("pause")
        self.now += 500000
        self.db.remove()
        restored = self.manager.state("admin")
        self.assertEqual(restored["session"], paused["session"])
        self.assertEqual(self.manager.elapsed(restored["session"], self.now), 100000)
        self.command("resume")
        self.now += 200000
        done = self.command("finish")
        self.assertEqual(done["session"]["elapsedMs"], 300000)
        self.assertEqual(self.count(), 1)

    def test_stopwatch_records_actual_time_and_never_goes_negative(self):
        started = self.start("stopwatch", 0)
        self.assertEqual(self.manager.elapsed(started["session"], self.now - 1000), 0)
        self.now += 75000
        result = self.command("finish")
        self.assertEqual(result["session"]["elapsedMs"], 75000)
        self.assertEqual(self.count(), 1)

    def test_break_and_discard_are_not_work_records(self):
        self.start("break", 60)
        self.now += 61000
        self.manager.state("admin")
        self.db.commit()
        self.assertEqual(self.count(), 0)
        self.start("countdown", 60)
        self.now += 10000
        self.assertEqual(self.command("discard")["session"]["status"], "cancelled")
        self.assertEqual(self.count(), 0)

    def test_stale_and_duplicate_commands_cannot_restart_or_double_record(self):
        started = self.start()
        self.now += 40000
        finished = self.command("finish")
        for action in ("pause", "finish", "discard", "start"):
            with self.assertRaises(FocusConflict):
                self.manager.command("admin", {"action": action, "revision": started["revision"],
                                               "id": started["session"]["id"], "mode": "stopwatch", "duration": 0})
        self.assertEqual(self.manager.state("admin")["revision"], finished["revision"])
        self.assertEqual(self.count(), 1)

    def test_running_session_cannot_be_replaced_and_owner_isolation(self):
        original = self.start()
        with self.assertRaises(FocusConflict):
            self.start()
        self.assertIsNone(self.manager.state("other")["session"])
        self.start(owner="other")
        self.assertEqual(self.manager.state("admin")["session"]["id"], original["session"]["id"])

    def test_links_resolve_all_plan_periods_without_mutating_tasks(self):
        for period in ("day", "week", "month", "year"):
            with self.subTest(period=period):
                pm = PlannerManager(self.db) if period == "day" else PeriodPlannerManager(self.db)
                plan = pm.get_day("admin", "2026-10-09") if period == "day" else pm.get_plan("admin", period, "2026-10-09")
                plan["sections"][0]["tasks"] = [{"id": "linked", "title": period, "kind": "task",
                                               "time": "", "notes": "", "done": False}]
                if period == "day":
                    pm.save_day("admin", plan["day"], plan)
                else:
                    pm.save_plan("admin", period, plan["day"], plan)
                self.db.commit()
                value = self.start(link={"period": period, "day": plan["day"], "taskId": "linked", "title": "forged"})
                self.assertEqual(value["session"]["title"], period)
                self.assertEqual(value["session"]["link"]["day"], plan["day"])
                self.now += 1000
                self.command("finish")
                same = pm.get_day("admin", plan["day"]) if period == "day" else pm.get_plan("admin", period, plan["day"])
                self.assertFalse(same["sections"][0]["tasks"][0]["done"])
                with self.assertRaises(ValueError):
                    self.start(owner="other", link={"period": period, "day": plan["day"], "taskId": "linked"})
        self.assertEqual(self.count(), 4)

    def test_validation_rejects_invalid_inputs(self):
        for data in [
            None, {}, {"revision": True}, {"revision": 0, "action": "nope"},
            {"revision": 0, "action": "start", "mode": "bad", "duration": 60},
            {"revision": 0, "action": "start", "mode": "pomodoro", "duration": 1},
            {"revision": 0, "action": "start", "mode": "countdown", "duration": 10801},
            {"revision": 0, "action": "start", "mode": "stopwatch", "duration": 60},
            {"revision": 0, "action": "start", "mode": "break", "duration": 3601},
            {"revision": 0, "action": "start", "mode": "pomodoro", "duration": "60"},
        ]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.manager.command("admin", data)
        self.assertEqual(self.manager.state("admin")["revision"], 0)

    def test_pausing_after_deadline_finishes_at_deadline(self):
        started = self.start("countdown", 60)
        self.now += 65000
        result = self.manager.command("admin", {"action": "pause", "revision": 1, "id": started["session"]["id"]})
        self.db.commit()
        self.assertEqual(result["session"]["status"], "completed")
        self.assertEqual(result["session"]["elapsedMs"], 60000)
        self.assertEqual(self.count(), 1)

    def test_records_local_day_and_owner_filter(self):
        self.start("stopwatch", 0)
        self.now += 65000
        self.command("finish")
        from datetime import datetime, timedelta, timezone
        day = datetime.fromtimestamp(self.now / 1000, timezone(timedelta(hours=8))).date().isoformat()
        report = self.manager.records("admin", day, 480)
        self.assertEqual(report["totalMs"], 65000)
        self.assertEqual(report["count"], 1)
        self.assertEqual(self.manager.records("other", day, 480)["count"], 0)
        self.assertEqual(self.manager.records("admin", "2026-01-01", 480)["count"], 0)
        for offset in ("bad", 9999):
            with self.assertRaises(ValueError):
                self.manager.records("admin", day, offset)


if __name__ == "__main__":
    unittest.main()
