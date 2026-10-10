import unittest
from copy import deepcopy

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import scoped_session, sessionmaker

from app.models.base import Base
from app.models.planner import PeriodPlan
from app.services.planner_manager import PlanConflict, PlannerManager
from app.services.period_planner_manager import PeriodPlannerManager, period_bounds


class PeriodPlannerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = scoped_session(sessionmaker(bind=self.engine))
        self.manager = PeriodPlannerManager(self.db)
        self.daily = PlannerManager(self.db)
        self.day = "2026-10-09"

    def tearDown(self):
        self.db.remove()
        self.engine.dispose()

    def save(self, plan, owner="admin"):
        result = self.manager.save_plan(owner, plan["period"], plan["day"], plan)
        self.db.commit()
        return result

    def seed(self, period):
        plan = self.manager.get_plan("admin", period, self.day)
        plan["sections"][0]["tasks"].append({
            "id": "shared-id", "title": period, "kind": "task", "time": "09:50",
            "endTime": "11:00", "scheduledDate": self.day, "done": False, "notes": "Details",
        })
        return self.save(plan)

    def test_calendar_bounds_include_cross_year_week_and_leap_month(self):
        self.assertEqual(period_bounds("week", "2026-10-11"), ("2026-10-05", "2026-10-11"))
        self.assertEqual(period_bounds("week", "2027-01-01"), ("2026-12-28", "2027-01-03"))
        self.assertEqual(period_bounds("month", "2024-02-19"), ("2024-02-01", "2024-02-29"))
        self.assertEqual(period_bounds("month", "2026-02-19"), ("2026-02-01", "2026-02-28"))
        self.assertEqual(period_bounds("year", "2026-10-09"), ("2026-01-01", "2026-12-31"))
        for period, day in [("other", self.day), ("day", self.day), ("week", "2026-02-30"), ("month", None)]:
            with self.subTest(period=period, day=day), self.assertRaises(ValueError):
                period_bounds(period, day)

    def test_period_owner_and_daily_storage_are_independent(self):
        original = self.daily.get_day("admin", self.day)
        for period in ("week", "month", "year"):
            saved = self.seed(period)
            self.assertEqual(self.manager.get_plan("admin", period, self.day), saved)
            self.assertEqual(saved["sections"][0]["tasks"][0]["title"], period)
            self.assertEqual(self.manager.get_plan("other", period, self.day)["revision"], 0)
        self.assertEqual(self.daily.get_day("admin", self.day), original)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(PeriodPlan)), 3)

    def test_same_period_dates_share_one_plan_and_next_period_is_empty(self):
        for period, other, next_day in [
            ("week", "2026-10-11", "2026-10-12"),
            ("month", "2026-10-31", "2026-11-01"),
            ("year", "2026-12-31", "2027-01-01"),
        ]:
            saved = self.seed(period)
            self.assertEqual(self.manager.get_plan("admin", period, other), saved)
            future = self.manager.get_plan("admin", period, next_day)
            self.assertEqual(future["revision"], 0)
            self.assertTrue(all(not section["tasks"] for section in future["sections"]))

    def test_content_edits_completion_move_delete_and_reload(self):
        plan = self.seed("month")
        plan["title"] = "Monthly objectives"
        plan["sections"].append({
            "id": "new", "title": "Personal", "color": "blue", "start": "", "end": "", "tasks": [],
        })
        task = plan["sections"][0]["tasks"].pop()
        task.update(done=True, notes="Updated", endTime="12:00")
        plan["sections"][-1]["tasks"].append(task)
        saved = self.save(plan)
        self.db.remove()
        self.assertEqual(self.manager.get_plan("admin", "month", self.day), saved)
        saved["sections"][-1]["tasks"] = []
        self.save(saved)
        self.assertEqual(self.manager.get_plan("admin", "month", self.day)["sections"][-1]["tasks"], [])

    def test_stale_revisions_cannot_overwrite_existing_plan(self):
        empty = self.manager.get_plan("admin", "week", self.day)
        saved = self.save(empty)
        with self.assertRaises(PlanConflict):
            self.save(empty)
        self.db.commit()
        newer = deepcopy(saved)
        newer["title"] = "New"
        newer = self.save(newer)
        with self.assertRaises(PlanConflict):
            self.save(saved)
        self.db.commit()
        self.assertEqual(self.manager.get_plan("admin", "week", self.day), newer)

    def test_dates_and_daily_repeats_are_validated_without_data_loss(self):
        saved = self.seed("week")
        for change in [
            {"scheduledDate": "2026-10-04"}, {"scheduledDate": "2026-10-12"},
            {"scheduledDate": "2026-02-30"}, {"scheduledDate": None},
            {"scheduledDate": ""}, {"daily": True}, {"endTime": "09:00"},
        ]:
            with self.subTest(change=change):
                bad = deepcopy(saved)
                bad["sections"][0]["tasks"][0].update(change)
                with self.assertRaises(ValueError):
                    self.save(bad)
                self.db.commit()
                self.assertEqual(self.manager.get_plan("admin", "week", self.day), saved)

    def test_unscheduled_and_all_day_tasks_are_supported(self):
        plan = self.seed("year")
        task = plan["sections"][0]["tasks"][0]
        task.update(time="", endTime="", scheduledDate="")
        saved = self.save(plan)
        self.assertEqual(saved["sections"][0]["tasks"][0]["scheduledDate"], "")
        saved["sections"][0]["tasks"][0]["scheduledDate"] = "2026-12-31"
        self.assertEqual(self.save(saved)["sections"][0]["tasks"][0]["scheduledDate"], "2026-12-31")

    def test_invalid_revisions_and_payloads_do_not_create_rows(self):
        for revision in [True, -1, "0", None]:
            plan = self.manager.get_plan("admin", "year", self.day)
            plan["revision"] = revision
            with self.assertRaises(ValueError):
                self.save(plan)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(PeriodPlan)), 0)


if __name__ == "__main__":
    unittest.main()
