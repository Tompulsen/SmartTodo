import re
from copy import deepcopy
from datetime import date, timedelta

import sqlalchemy as sal
from sqlalchemy.exc import IntegrityError

from app.models.base import Database
from app.models.planner import DailyPlan, DailyTaskRule, PlannerState
from app.tools.time import now

COLORS = {"rose", "gold", "sage", "blue", "lilac", "teal"}
DEFAULT_SECTIONS = [
    ("urgent-important", "\u91cd\u8981\u4e14\u7d27\u6025", "rose"),
    ("important", "\u91cd\u8981\u4e0d\u7d27\u6025", "gold"),
    ("urgent", "\u7d27\u6025\u4e0d\u91cd\u8981", "sage"),
    ("someday", "\u4e0d\u91cd\u8981\u4e0d\u7d27\u6025", "blue"),
]


class PlanConflict(Exception):
    pass


def validate_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid date")
    date.fromisoformat(value)
    return value


def validate_time(value):
    if not isinstance(value, str) or (value and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)):
        raise ValueError("Invalid time")
    return value


def text(value, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError("Invalid text")
    return value.strip()


def default_content():
    return {
        "title": "\u4e00\u65e5\u8ba1\u5212",
        "sections": [
            {"id": key, "title": title, "color": color, "start": "", "end": "", "tasks": []}
            for key, title, color in DEFAULT_SECTIONS
        ],
    }


def validate_content(data, section_limit=24, task_limit=1000):
    if not isinstance(data, dict):
        raise ValueError("Invalid plan")
    title = text(data.get("title"), 60, True)
    sections = data.get("sections")
    if not isinstance(sections, list) or not 1 <= len(sections) <= section_limit:
        raise ValueError("Invalid number of sections")

    section_ids, task_ids = set(), set()
    clean_sections = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("Invalid section")
        sid = text(section.get("id"), 80, True)
        if sid in section_ids:
            raise ValueError("Duplicate section")
        section_ids.add(sid)
        color = section.get("color")
        if not isinstance(color, str) or color not in COLORS:
            raise ValueError("Invalid section color")
        start, end = validate_time(section.get("start", "")), validate_time(section.get("end", ""))
        if start and end and start >= end:
            raise ValueError("Section end must be after start")
        tasks = section.get("tasks")
        if not isinstance(tasks, list):
            raise ValueError("Invalid task list")
        clean_tasks = []
        for task in tasks:
            if not isinstance(task, dict):
                raise ValueError("Invalid task")
            tid = text(task.get("id"), 80, True)
            if tid in task_ids:
                raise ValueError("Duplicate task")
            task_ids.add(tid)
            if len(task_ids) > task_limit:
                raise ValueError("Too many tasks")
            if task.get("kind") not in {"task", "event"} or type(task.get("done")) is not bool:
                raise ValueError("Invalid task state")
            if "daily" in task and type(task["daily"]) is not bool:
                raise ValueError("Invalid daily repeat state")
            task_start = validate_time(task.get("time", ""))
            task_end = validate_time(task.get("endTime", ""))
            if task_end and (not task_start or task_end <= task_start):
                raise ValueError("Task end must be after start on the same day")
            scheduled = task.get("scheduledDate", "")
            if scheduled != "":
                validate_day(scheduled)
            clean_tasks.append({
                "id": tid,
                "title": text(task.get("title"), 200, True),
                "notes": text(task.get("notes", ""), 5000),
                "kind": task["kind"],
                "time": task_start,
                **({"endTime": task_end} if "endTime" in task else {}),
                **({"scheduledDate": scheduled} if "scheduledDate" in task else {}),
                "done": task["done"],
                **({"daily": task["daily"]} if "daily" in task else {}),
            })
        clean_sections.append({
            "id": sid, "title": text(section.get("title"), 40, True),
            "color": color, "start": start, "end": end, "tasks": clean_tasks,
        })
    return {"title": title, "sections": clean_sections}


class PlannerManager:
    def __init__(self, db: Database):
        self.db = db

    def get_day(self, owner, day):
        day = validate_day(day)
        schedule_revision = self.db.scalar(
            sal.select(PlannerState.revision).where(PlannerState.owner == owner)
        ) or 0
        row = self.db.scalar(
            sal.select(DailyPlan).where(DailyPlan.owner == owner, DailyPlan.day == day)
            .execution_options(populate_existing=True)
        )
        return {
            "day": day, "revision": row.revision if row else 0,
            "schedule_revision": schedule_revision,
            **self._materialize(day, row, self._rules(owner, day)),
        }

    def _rules(self, owner, through):
        return self.db.scalars(
            sal.select(DailyTaskRule)
            .where(DailyTaskRule.owner == owner, DailyTaskRule.day <= through)
            .order_by(DailyTaskRule.day, DailyTaskRule.id)
        ).all()

    @staticmethod
    def _materialize(day, row, rules):
        content = deepcopy(row.content) if row else default_content()
        latest = {}
        for rule in rules:
            if rule.day <= day:
                latest[rule.task_id] = rule
        sections = {section["id"]: section for section in content["sections"]}
        tasks = {
            task["id"]: (section, task)
            for section in content["sections"] for task in section["tasks"]
        }
        for rule in sorted(latest.values(), key=lambda item: (item.day, item.id)):
            source, existing = tasks.get(rule.task_id, (None, None))
            if not rule.content:
                if existing and existing.get("daily"):
                    source["tasks"].remove(existing)
                continue
            # A saved one-off occurrence is independent of the repeating series.
            if existing and not existing.get("daily"):
                continue
            template = rule.content
            sid = template["section"]["id"]
            target = sections.get(sid)
            if target is None:
                target = {**deepcopy(template["section"]), "tasks": []}
                content["sections"].append(target)
                sections[sid] = target
            elif row is None:
                target.update(deepcopy(template["section"]))
            task = {**deepcopy(template["task"]), "done": existing["done"] if existing else False}
            if source is target:
                target["tasks"][target["tasks"].index(existing)] = task
            else:
                if source is not None:
                    source["tasks"].remove(existing)
                target["tasks"].append(task)
        return content

    @staticmethod
    def _templates(content):
        return {
            task["id"]: {
                "section": {key: value for key, value in section.items() if key != "tasks"},
                "task": {key: value for key, value in task.items() if key != "done"},
            }
            for section in content["sections"] for task in section["tasks"] if task.get("daily")
        }

    def _save_rules(self, owner, day, before, after):
        previous, current = self._templates(before), self._templates(after)
        for tid in dict.fromkeys([*previous, *current]):
            if previous.get(tid) == current.get(tid):
                continue
            self.db.execute(sal.delete(DailyTaskRule).where(
                DailyTaskRule.owner == owner, DailyTaskRule.task_id == tid, DailyTaskRule.day >= day,
            ))
            self.db.add(DailyTaskRule(owner=owner, task_id=tid, day=day, content=current.get(tid, {})))

    def save_day(self, owner, day, data):
        day = validate_day(day)
        if not isinstance(data, dict):
            raise ValueError("Invalid plan")
        revision = data.get("revision")
        schedule_revision = data.get("schedule_revision", 0)
        if any(type(value) is not int or value < 0 for value in (revision, schedule_revision)):
            raise ValueError("Invalid revision")

        try:
            # Guard all dates together: a series edit must invalidate stale future-day forms.
            # The savepoint also rolls back handled conflicts, including rule changes.
            with self.db.begin_nested():
                guard = self.db.execute(
                    sal.update(PlannerState)
                    .where(PlannerState.owner == owner, PlannerState.revision == schedule_revision)
                    .values(revision=schedule_revision + 1)
                    .execution_options(synchronize_session=False)
                )
                if guard.rowcount != 1:
                    if schedule_revision != 0:
                        raise PlanConflict()
                    self.db.add(PlannerState(owner=owner, revision=1))
                    self.db.flush()

                previous = self.get_day(owner, day)
                # Generated sections must stay editable even if a full saved day already existed.
                content = validate_content(
                    data, max(24, len(previous["sections"])),
                    max(1000, sum(len(section["tasks"]) for section in previous["sections"])),
                )
                if revision == 0:
                    self.db.add(DailyPlan(owner=owner, day=day, content=content, revision=1))
                else:
                    result = self.db.execute(
                        sal.update(DailyPlan)
                        .where(DailyPlan.owner == owner, DailyPlan.day == day, DailyPlan.revision == revision)
                        .values(content=content, revision=revision + 1, updated_at=now())
                        .execution_options(synchronize_session=False)
                    )
                    if result.rowcount != 1:
                        raise PlanConflict()
                self._save_rules(owner, day, previous, content)
                self.db.flush()
        except IntegrityError as exc:
            raise PlanConflict() from exc
        return {"day": day, "revision": revision + 1, "schedule_revision": schedule_revision + 1, **content}

    def overview(self, owner, start, end):
        start, end = validate_day(start), validate_day(end)
        if not 0 <= (date.fromisoformat(end) - date.fromisoformat(start)).days <= 42:
            raise ValueError("Invalid calendar range")
        rows = {row.day: row for row in self.db.scalars(
            sal.select(DailyPlan).where(DailyPlan.owner == owner, DailyPlan.day >= start, DailyPlan.day <= end)
            .execution_options(populate_existing=True)
        ).all()}
        rules = self._rules(owner, end)
        result = {}
        for offset in range((date.fromisoformat(end) - date.fromisoformat(start)).days + 1):
            day = (date.fromisoformat(start) + timedelta(days=offset)).isoformat()
            content = self._materialize(day, rows.get(day), rules)
            tasks = [task for section in content["sections"] for task in section["tasks"]]
            result[day] = {"total": len(tasks), "done": sum(task["done"] for task in tasks)}
        return result
