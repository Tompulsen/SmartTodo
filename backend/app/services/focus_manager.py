from copy import deepcopy
from datetime import datetime, timedelta, timezone
import time
from uuid import uuid4

import sqlalchemy as sal
from sqlalchemy.exc import IntegrityError

from app.models.focus import FocusRecord, FocusState
from app.services.planner_manager import PlannerManager, validate_day
from app.services.period_planner_manager import PeriodPlannerManager


class FocusConflict(Exception):
    pass


class FocusManager:
    def __init__(self, db, clock=None):
        self.db = db
        self.clock = clock or (lambda: int(time.time() * 1000))

    def _load(self, owner):
        row = self.db.scalar(sal.select(FocusState).where(FocusState.owner == owner)
                             .execution_options(populate_existing=True))
        return (row.revision, deepcopy(row.content)) if row else (0, None)

    @staticmethod
    def elapsed(state, now):
        extra = max(0, now - state["resumedAt"]) if state["status"] == "running" else 0
        value = state["elapsedMs"] + extra
        return min(value, state["duration"] * 1000) if state["duration"] else min(value, 86400000)

    def _store(self, owner, revision, state, record=None):
        try:
            with self.db.begin_nested():
                if revision == 0:
                    self.db.add(FocusState(owner=owner, revision=1, content=state))
                else:
                    result = self.db.execute(sal.update(FocusState).where(
                        FocusState.owner == owner, FocusState.revision == revision
                    ).values(revision=revision + 1, content=state).execution_options(synchronize_session=False))
                    if result.rowcount != 1:
                        raise FocusConflict()
                if record:
                    self.db.add(FocusRecord(id=record["id"], owner=owner,
                                            finished_at=record["finishedAt"], content=record))
                self.db.flush()
        except IntegrityError as exc:
            raise FocusConflict() from exc

    def _finish(self, state, now, automatic=False):
        elapsed = self.elapsed(state, now)
        if automatic:
            finished_at = state["resumedAt"] + elapsed - state["elapsedMs"]
        else:
            finished_at = now
        state.update(status="completed", elapsedMs=elapsed, resumedAt=None, finishedAt=finished_at)
        if state["mode"] == "break" or elapsed < 1000:
            return None
        return {key: deepcopy(state[key]) for key in
                ("id", "mode", "title", "link", "startedAt", "finishedAt", "elapsedMs", "duration")}

    def state(self, owner):
        revision, state = self._load(owner)
        now = self.clock()
        if state and state["status"] == "running":
            limit = (state["duration"] or 86400) * 1000
            if self.elapsed(state, now) >= limit:
                record = self._finish(state, now, automatic=True)
                self._store(owner, revision, state, record)
                revision += 1
        return {"revision": revision, "session": state, "serverNow": now}

    def _link(self, owner, link):
        if link is None:
            return None, ""
        if not isinstance(link, dict) or link.get("period") not in ("day", "week", "month", "year"):
            raise ValueError("Invalid plan link")
        day = validate_day(link.get("day"))
        period = link["period"]
        plan = (PlannerManager(self.db).get_day(owner, day) if period == "day" else
                PeriodPlannerManager(self.db).get_plan(owner, period, day))
        for section in plan["sections"]:
            for task in section["tasks"]:
                if task["id"] == link.get("taskId"):
                    return {"period": period, "day": plan["day"], "taskId": task["id"],
                            "title": task["title"], "section": section["title"]}, task["title"]
        raise ValueError("The selected task no longer exists")

    def command(self, owner, data):
        if not isinstance(data, dict) or type(data.get("revision")) is not int or data["revision"] < 0:
            raise ValueError("Invalid revision")
        revision, current = self._load(owner)
        if data["revision"] != revision:
            raise FocusConflict()
        state = deepcopy(current)
        now = self.clock()
        action = data.get("action")
        active = state and state["status"] in ("running", "paused")
        record = None
        if action == "start":
            if active:
                raise FocusConflict()
            mode = data.get("mode")
            duration = data.get("duration")
            if mode not in ("pomodoro", "countdown", "stopwatch", "break"):
                raise ValueError("Invalid timer mode")
            if type(duration) is not int or (mode == "stopwatch" and duration != 0) or (
                mode != "stopwatch" and not 60 <= duration <= (3600 if mode == "break" else 10800)
            ):
                raise ValueError("Invalid timer duration")
            link, title = self._link(owner, data.get("link"))
            state = {"id": str(uuid4()), "mode": mode, "duration": duration, "title": title,
                     "link": link, "status": "running", "elapsedMs": 0, "startedAt": now,
                     "resumedAt": now, "finishedAt": None}
        elif action in ("pause", "resume", "finish", "discard"):
            if not active or data.get("id") != state["id"]:
                raise FocusConflict()
            if state["status"] == "running" and self.elapsed(state, now) >= (state["duration"] or 86400) * 1000:
                record = self._finish(state, now, automatic=True)
            elif action == "pause" and state["status"] == "running":
                state.update(elapsedMs=self.elapsed(state, now), resumedAt=None, status="paused")
            elif action == "resume" and state["status"] == "paused":
                state.update(resumedAt=now, status="running")
            elif action == "finish":
                record = self._finish(state, now)
            elif action == "discard":
                state.update(elapsedMs=self.elapsed(state, now), resumedAt=None, status="cancelled")
            else:
                raise FocusConflict()
        else:
            raise ValueError("Invalid action")
        self._store(owner, revision, state, record)
        return {"revision": revision + 1, "session": state, "serverNow": now}

    def records(self, owner, day, offset):
        day = validate_day(day)
        try:
            offset = int(offset)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid timezone") from exc
        if not -840 <= offset <= 840:
            raise ValueError("Invalid timezone")
        start = datetime.fromisoformat(day).replace(tzinfo=timezone(timedelta(minutes=offset)))
        start_ms = int(start.timestamp() * 1000)
        rows = self.db.scalars(sal.select(FocusRecord).where(
            FocusRecord.owner == owner, FocusRecord.finished_at >= start_ms,
            FocusRecord.finished_at < start_ms + 86400000
        ).order_by(FocusRecord.finished_at.desc())).all()
        records = [deepcopy(row.content) for row in rows]
        return {"records": records, "totalMs": sum(record["elapsedMs"] for record in records),
                "count": len(records)}
