from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta

import sqlalchemy as sal
from sqlalchemy.exc import IntegrityError

from app.models.planner import PeriodPlan
from app.services.planner_manager import PlanConflict, default_content, validate_content, validate_day
from app.tools.time import now


def period_bounds(period, day):
    current = date.fromisoformat(validate_day(day))
    if period == "week":
        start = current - timedelta(days=current.weekday())
        try:
            end = start + timedelta(days=6)
        except OverflowError as exc:
            raise ValueError("Invalid week") from exc
    elif period == "month":
        start = current.replace(day=1)
        end = current.replace(day=monthrange(current.year, current.month)[1])
    elif period == "year":
        start, end = current.replace(month=1, day=1), current.replace(month=12, day=31)
    else:
        raise ValueError("Invalid plan period")
    return start.isoformat(), end.isoformat()


def period_default(period):
    content = default_content()
    content["title"] = {
        "week": "\u4e00\u5468\u8ba1\u5212",
        "month": "\u4e00\u6708\u8ba1\u5212",
        "year": "\u4e00\u5e74\u8ba1\u5212",
    }[period]
    return content


class PeriodPlannerManager:
    def __init__(self, db):
        self.db = db

    def get_plan(self, owner, period, day):
        start, end = period_bounds(period, day)
        row = self.db.scalar(
            sal.select(PeriodPlan).where(
                PeriodPlan.owner == owner, PeriodPlan.period == period, PeriodPlan.start == start
            ).execution_options(populate_existing=True)
        )
        return {
            "period": period, "day": start, "endDay": end,
            "revision": row.revision if row else 0, "schedule_revision": 0,
            **(deepcopy(row.content) if row else period_default(period)),
        }

    def save_plan(self, owner, period, day, data):
        start, end = period_bounds(period, day)
        if not isinstance(data, dict):
            raise ValueError("Invalid plan")
        revision = data.get("revision")
        if type(revision) is not int or revision < 0:
            raise ValueError("Invalid revision")
        content = validate_content(data)
        for section in content["sections"]:
            for task in section["tasks"]:
                scheduled = task.get("scheduledDate", "")
                if scheduled and not start <= scheduled <= end:
                    raise ValueError("Task date must be within this plan period")
                if task["time"] and not scheduled:
                    raise ValueError("Timed period tasks need an execution date")
                if task.get("daily"):
                    raise ValueError("Daily repeat belongs to daily plans")
        try:
            with self.db.begin_nested():
                if revision == 0:
                    self.db.add(PeriodPlan(owner=owner, period=period, start=start,
                                           revision=1, content=content))
                else:
                    result = self.db.execute(
                        sal.update(PeriodPlan).where(
                            PeriodPlan.owner == owner, PeriodPlan.period == period,
                            PeriodPlan.start == start, PeriodPlan.revision == revision,
                        ).values(content=content, revision=revision + 1, updated_at=now())
                        .execution_options(synchronize_session=False)
                    )
                    if result.rowcount != 1:
                        raise PlanConflict()
                self.db.flush()
        except IntegrityError as exc:
            raise PlanConflict() from exc
        return {
            "period": period, "day": start, "endDay": end,
            "revision": revision + 1, "schedule_revision": 0, **content,
        }
