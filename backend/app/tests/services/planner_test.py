import unittest
from copy import deepcopy

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import scoped_session, sessionmaker

from app.models.base import Base
from app.models.planner import DailyPlan, DailyTaskRule, PlannerState
from app.services.planner_manager import PlanConflict, PlannerManager, validate_content


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = scoped_session(sessionmaker(bind=self.engine))
        self.manager = PlannerManager(self.db)
        self.day = "2026-10-08"

    def tearDown(self):
        self.db.remove()
        self.engine.dispose()

    def save(self, board, owner="admin"):
        saved = self.manager.save_day(owner, board["day"], board)
        self.db.commit()
        return saved

    @staticmethod
    def tasks(board):
        return [task for section in board["sections"] for task in section["tasks"]]

    def seed_daily(self, custom=False, day=None):
        board = self.manager.get_day("admin", day or self.day)
        if custom:
            board["sections"].append({
                "id": "morning", "title": "Morning", "color": "teal",
                "start": "08:00", "end": "12:00", "tasks": [],
            })
        board["sections"][-1 if custom else 0]["tasks"].append({
            "id": "routine", "title": "Read", "notes": "Chapter 1", "time": "09:30",
            "kind": "task", "done": False, "daily": True,
        })
        return self.save(board)

    def test_default_day_is_independent_and_has_four_sections(self):
        first = self.manager.get_day("admin", self.day)
        self.assertEqual(len(first["sections"]), 4)
        first["sections"][0]["title"] = "Changed"
        second = self.manager.get_day("admin", self.day)
        self.assertNotEqual(first["sections"][0]["title"], second["sections"][0]["title"])
        self.assertEqual(second["revision"], 0)

    def test_save_reload_date_and_owner_isolation(self):
        board = self.manager.get_day("admin", self.day)
        board["sections"][0]["tasks"].append({
            "id": "task-1", "title": "Read", "kind": "task", "time": "09:30", "done": False, "notes": "Chapter 1",
        })
        saved = self.manager.save_day("admin", self.day, board)
        self.db.commit()
        self.assertEqual(self.manager.get_day("admin", self.day), saved)
        self.assertEqual(self.manager.get_day("user", self.day)["revision"], 0)
        self.assertEqual(self.manager.get_day("admin", "2026-10-09")["revision"], 0)
        self.assertEqual(self.manager.overview("admin", self.day, self.day)[self.day], {"total": 1, "done": 0})

    def test_revisions_prevent_overwrites(self):
        original = self.manager.get_day("admin", self.day)
        saved = self.manager.save_day("admin", self.day, original)
        self.db.commit()
        with self.assertRaises(PlanConflict):
            self.manager.save_day("admin", self.day, original)
        updated = self.manager.save_day("admin", self.day, saved)
        self.db.commit()
        self.assertEqual(updated["revision"], 2)
        with self.assertRaises(PlanConflict):
            self.manager.save_day("admin", self.day, saved)

    def test_sections_order_content_and_done_are_preserved(self):
        board = self.manager.get_day("admin", self.day)
        board["sections"].append({"id": "evening", "title": "Evening", "color": "teal", "start": "19:00", "end": "21:00", "tasks": [
            {"id": "b", "title": "Call", "kind": "event", "time": "19:30", "done": True, "notes": ""},
            {"id": "a", "title": "Read", "kind": "task", "time": "", "done": False, "notes": ""},
        ]})
        self.manager.save_day("admin", self.day, board)
        self.db.commit()
        self.assertEqual(self.manager.get_day("admin", self.day)["sections"], board["sections"])
        self.assertEqual(self.manager.overview("admin", self.day, self.day)[self.day], {"total": 2, "done": 1})

    def test_invalid_payloads_are_rejected(self):
        board = self.manager.get_day("admin", self.day)
        for invalid in [None, {}, {"title": "x", "sections": []}]:
            with self.assertRaises(ValueError):
                validate_content(invalid)
        for field, value in [("color", "invalid"), ("color", []), ("title", ""), ("start", "25:61")]:
            bad = deepcopy(board)
            bad["sections"][0][field] = value
            with self.assertRaises(ValueError):
                validate_content(bad)
        duplicate = deepcopy(board)
        duplicate["sections"].append(deepcopy(duplicate["sections"][0]))
        with self.assertRaises(ValueError):
            validate_content(duplicate)
        with self.assertRaises(ValueError):
            self.manager.get_day("admin", "2026-02-30")

    def test_duplicate_tasks_and_invalid_revision_are_rejected(self):
        board = self.manager.get_day("admin", self.day)
        task = {"id": "a", "title": "Read", "kind": "task", "done": False, "time": "", "notes": ""}
        board["sections"][0]["tasks"].append(task)
        board["sections"][1]["tasks"].append(deepcopy(task))
        with self.assertRaises(ValueError):
            validate_content(board)
        board["sections"][1]["tasks"] = []
        for revision in [True, -1, "0", None]:
            board["revision"] = revision
            with self.assertRaises(ValueError):
                self.manager.save_day("admin", self.day, board)

    def test_invalid_time_window_and_overview_range_are_rejected(self):
        board = self.manager.get_day("admin", self.day)
        board["sections"][0].update(start="18:00", end="09:00")
        with self.assertRaises(ValueError):
            validate_content(board)
        with self.assertRaises(ValueError):
            self.manager.overview("admin", "2026-10-09", "2026-10-08")
        with self.assertRaises(ValueError):
            self.manager.overview("admin", "2026-01-01", "2026-12-31")

    def test_existing_task_can_be_enabled_without_changing_identity(self):
        board = self.manager.get_day("admin", self.day)
        board["sections"][0]["tasks"].append({
            "id": "existing", "title": "Cook", "kind": "task", "done": True, "notes": "", "time": "",
        })
        board = self.save(board)
        board["sections"][0]["tasks"][0]["daily"] = True
        self.save(board)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.assertEqual(self.tasks(tomorrow)[0]["id"], "existing")
        self.assertFalse(self.tasks(tomorrow)[0]["done"])
        self.assertTrue(self.tasks(self.manager.get_day("admin", self.day))[0]["done"])

    def test_task_ranges_persist_for_tasks_and_events_alongside_legacy_times(self):
        board = self.manager.get_day("admin", self.day)
        for index, (kind, start, end) in enumerate([
            ("task", "09:50", "11:00"), ("event", "14:00", "15:30"),
            ("task", "00:00", "00:30"), ("task", "23:00", "23:59"),
            ("task", "08:00", ""), ("task", "", ""),
        ]):
            board["sections"][0]["tasks"].append({
                "id": str(index), "title": "Time test", "kind": kind, "time": start,
                "endTime": end, "done": False, "notes": "",
            })
        board["sections"][0]["tasks"].append({
            "id": "legacy", "title": "Legacy", "kind": "task", "time": "08:00",
            "done": False, "notes": "",
        })
        saved = self.save(board)
        self.db.remove()
        self.assertEqual(self.manager.get_day("admin", self.day), saved)
        self.assertEqual(saved["sections"], board["sections"])
        self.assertNotIn("endTime", self.tasks(saved)[-1])

    def test_invalid_task_ranges_are_rejected_without_changing_saved_data(self):
        board = self.seed_daily()
        for start, end in [
            ("09:50", "09:50"), ("09:50", "09:49"), ("", "11:00"),
            ("23:00", "01:00"), ("09:50", "24:00"), ("09:50", "11:60"),
            ("09:50", "11"), ("09:50", None), ("09:50", 1100),
        ]:
            with self.subTest(start=start, end=end):
                bad = deepcopy(board)
                self.tasks(bad)[0].update(time=start, endTime=end)
                with self.assertRaises(ValueError):
                    self.save(bad)
                self.db.commit()
                self.assertEqual(self.manager.get_day("admin", self.day), board)

    def test_recurring_ranges_apply_forward_preserve_done_and_can_be_cleared(self):
        board = self.seed_daily(custom=True)
        self.tasks(board)[0].update(time="09:50", endTime="11:00")
        self.save(board)
        future = self.manager.get_day("admin", "2026-10-11")
        self.assertEqual(self.tasks(future)[0]["endTime"], "11:00")
        self.tasks(future)[0]["done"] = True
        self.save(future)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        moved = tomorrow["sections"][-1]["tasks"].pop()
        moved["endTime"] = "11:30"
        tomorrow["sections"][1]["tasks"].append(moved)
        self.save(tomorrow)
        self.assertEqual(self.tasks(self.manager.get_day("admin", self.day))[0]["endTime"], "11:00")
        future = self.manager.get_day("admin", "2026-10-11")
        self.assertEqual(future["sections"][1]["tasks"][0]["endTime"], "11:30")
        self.assertTrue(future["sections"][1]["tasks"][0]["done"])
        next_day = self.manager.get_day("admin", "2026-10-10")
        self.tasks(next_day)[0]["endTime"] = ""
        self.save(next_day)
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-10-11"))[0]["endTime"], "")
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-10-09"))[0]["endTime"], "11:30")

    def test_repeat_carries_custom_section_but_not_to_past_or_other_owner(self):
        original = self.seed_daily(custom=True)
        for day in ["2026-10-09", "2026-11-01", "2027-01-01"]:
            board = self.manager.get_day("admin", day)
            self.assertEqual(board["sections"][-1], original["sections"][-1])
            self.assertEqual(len(self.tasks(board)), 1)
            self.assertEqual(board["revision"], 0)
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-10-07")), [])
        self.assertEqual(self.tasks(self.manager.get_day("other", "2026-10-09")), [])

    def test_done_is_independent_and_reads_do_not_create_duplicate_rows(self):
        self.seed_daily()
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0]["done"] = True
        self.save(tomorrow)
        self.db.remove()
        for _ in range(3):
            self.assertTrue(self.tasks(self.manager.get_day("admin", "2026-10-09"))[0]["done"])
            self.assertFalse(self.tasks(self.manager.get_day("admin", "2026-10-08"))[0]["done"])
            self.assertFalse(self.tasks(self.manager.get_day("admin", "2026-10-10"))[0]["done"])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(DailyPlan)), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(DailyTaskRule)), 1)

    def test_calendar_includes_unsaved_repeats_and_independent_completion(self):
        self.seed_daily()
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0]["done"] = True
        self.save(tomorrow)
        counts = self.manager.overview("admin", "2026-10-07", "2026-10-11")
        self.assertEqual(counts["2026-10-07"], {"total": 0, "done": 0})
        self.assertEqual(counts["2026-10-08"], {"total": 1, "done": 0})
        self.assertEqual(counts["2026-10-09"], {"total": 1, "done": 1})
        self.assertEqual(counts["2026-10-11"], {"total": 1, "done": 0})

    def test_repeat_merges_into_previously_saved_day(self):
        future = self.manager.get_day("admin", "2026-10-09")
        future["title"] = "Already planned"
        future["sections"][1]["tasks"].append({
            "id": "one-off", "title": "Meeting", "kind": "event", "time": "15:00", "done": True, "notes": "",
        })
        self.save(future)
        self.seed_daily(custom=True)
        future = self.manager.get_day("admin", "2026-10-09")
        self.assertEqual(future["title"], "Already planned")
        self.assertEqual([task["id"] for task in self.tasks(future)], ["one-off", "routine"])
        self.assertTrue(self.tasks(future)[0]["done"])
        self.save(future)
        self.assertEqual(len(self.tasks(self.manager.get_day("admin", "2026-10-09"))), 2)

    def test_edits_apply_forward_while_history_and_future_completion_survive(self):
        self.seed_daily()
        future = self.manager.get_day("admin", "2026-10-11")
        self.tasks(future)[0]["done"] = True
        self.save(future)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0].update(title="Read more", time="10:00", notes="Chapter 2", kind="event")
        self.save(tomorrow)
        self.assertEqual(self.tasks(self.manager.get_day("admin", self.day))[0]["title"], "Read")
        for day in ["2026-10-09", "2026-10-10", "2026-10-11"]:
            task = self.tasks(self.manager.get_day("admin", day))[0]
            self.assertEqual((task["title"], task["time"], task["notes"], task["kind"]),
                             ("Read more", "10:00", "Chapter 2", "event"))
            self.assertEqual(task["done"], day == "2026-10-11")

    def test_turning_off_keeps_selected_occurrence_and_stops_saved_future_ones(self):
        self.seed_daily(custom=True)
        self.save(self.manager.get_day("admin", "2026-10-10"))
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0].update(daily=False, done=True)
        self.save(tomorrow)
        self.assertTrue(self.tasks(self.manager.get_day("admin", self.day))[0]["daily"])
        task = self.tasks(self.manager.get_day("admin", "2026-10-09"))[0]
        self.assertFalse(task["daily"])
        self.assertTrue(task["done"])
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-10-10")), [])
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-11-01")), [])

    def test_deleting_repeat_stops_future_and_preserves_previous_days(self):
        self.seed_daily()
        later = self.manager.get_day("admin", "2026-10-11")
        self.tasks(later)[0]["title"] = "Later revision"
        self.save(later)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        tomorrow["sections"][0]["tasks"] = []
        self.save(tomorrow)
        self.assertEqual(len(self.tasks(self.manager.get_day("admin", self.day))), 1)
        for day in ["2026-10-09", "2026-10-10", "2026-10-11", "2026-11-01"]:
            self.assertEqual(self.tasks(self.manager.get_day("admin", day)), [])

    def test_reenabling_repeat_is_deduplicated(self):
        self.seed_daily()
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0]["daily"] = False
        tomorrow = self.save(tomorrow)
        self.tasks(tomorrow)[0]["daily"] = True
        self.save(tomorrow)
        for day in ["2026-10-09", "2026-10-10"]:
            self.assertEqual(len(self.tasks(self.manager.get_day("admin", day))), 1)
            self.assertTrue(self.tasks(self.manager.get_day("admin", day))[0]["daily"])

    def test_moving_and_renaming_recurring_section_applies_forward(self):
        self.seed_daily(custom=True)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        task = tomorrow["sections"][-1]["tasks"].pop()
        tomorrow["sections"][1]["tasks"].append(task)
        tomorrow["sections"][1].update(title="Reading", start="09:00", end="11:00")
        self.save(tomorrow)
        next_day = self.manager.get_day("admin", "2026-10-10")
        self.assertEqual(next_day["sections"][1]["title"], "Reading")
        self.assertEqual(next_day["sections"][1]["tasks"][0]["id"], "routine")
        self.assertEqual(self.manager.get_day("admin", self.day)["sections"][-1]["tasks"][0]["id"], "routine")

    def test_multiple_daily_tasks_share_custom_section_without_duplicates(self):
        board = self.seed_daily(custom=True)
        another = deepcopy(self.tasks(board)[0])
        another.update(id="second", title="Exercise")
        board["sections"][-1]["tasks"].append(another)
        self.save(board)
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.assertEqual(len(tomorrow["sections"]), 5)
        self.assertEqual([task["id"] for task in tomorrow["sections"][-1]["tasks"]], ["routine", "second"])
        self.save(tomorrow)
        self.assertEqual(len(self.tasks(self.manager.get_day("admin", "2026-10-09"))), 2)

    def test_cross_date_conflicts_do_not_resurrect_disabled_series(self):
        self.seed_daily()
        stale = self.manager.get_day("admin", "2026-10-10")
        tomorrow = self.manager.get_day("admin", "2026-10-09")
        self.tasks(tomorrow)[0]["daily"] = False
        self.save(tomorrow)
        with self.assertRaises(PlanConflict):
            self.save(stale)
        self.db.commit()
        self.assertEqual(self.tasks(self.manager.get_day("admin", "2026-10-10")), [])
        self.assertEqual(self.manager.get_day("admin", "2026-10-10")["revision"], 0)

    def test_stale_day_revision_rolls_back_shared_guard_and_rule_changes(self):
        board = self.seed_daily()
        stale = deepcopy(board)
        board["title"] = "Updated"
        saved = self.save(board)
        stale["schedule_revision"] = saved["schedule_revision"]
        self.tasks(stale)[0]["daily"] = False
        with self.assertRaises(PlanConflict):
            self.save(stale)
        self.db.commit()
        self.assertEqual(self.manager.get_day("admin", self.day), saved)
        self.assertEqual(len(self.tasks(self.manager.get_day("admin", "2026-10-09"))), 1)

    def test_invalid_repeat_payload_rolls_back_guard(self):
        board = self.manager.get_day("admin", self.day)
        board["sections"][0]["tasks"].append({
            "id": "a", "title": "Read", "kind": "task", "done": False, "daily": "yes",
        })
        with self.assertRaises(ValueError):
            self.save(board)
        self.db.commit()
        self.assertIsNone(self.db.scalar(select(PlannerState)))
        board["sections"][0]["tasks"][0]["daily"] = True
        for invalid in [True, -1, "0", None]:
            board["schedule_revision"] = invalid
            with self.assertRaises(ValueError):
                self.save(board)

    def test_generated_section_does_not_make_full_saved_day_uneditable(self):
        future = self.manager.get_day("admin", "2026-10-09")
        for index in range(20):
            future["sections"].append({
                "id": f"custom-{index}", "title": "Custom", "color": "blue", "start": "", "end": "", "tasks": [],
            })
        self.save(future)
        self.seed_daily(custom=True)
        future = self.manager.get_day("admin", "2026-10-09")
        self.assertEqual(len(future["sections"]), 25)
        self.tasks(future)[0]["done"] = True
        self.save(future)
        self.assertTrue(self.tasks(self.manager.get_day("admin", "2026-10-09"))[0]["done"])


if __name__ == "__main__":
    unittest.main()
