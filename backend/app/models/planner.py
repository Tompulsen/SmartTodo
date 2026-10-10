from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class DailyPlan(Base):
    __tablename__ = "daily_plan"
    __table_args__ = (UniqueConstraint("owner", "day", name="uq_daily_plan_owner_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    day: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class PlannerState(Base):
    __tablename__ = "planner_state"

    owner: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DailyTaskRule(Base):
    __tablename__ = "daily_task_rule"
    __table_args__ = (UniqueConstraint("owner", "task_id", "day", name="uq_daily_task_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(80), nullable=False)
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    # Empty content stops the series from this date; older versions remain intact.
    content: Mapped[dict] = mapped_column(JSON, nullable=False)


class PeriodPlan(Base):
    __tablename__ = "period_plan"
    __table_args__ = (UniqueConstraint("owner", "period", "start", name="uq_period_plan_owner_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False)
    start: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
