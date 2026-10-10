from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.tools.time import now


class UserConnection(Base):
    __tablename__ = "user_connection"
    __table_args__ = (UniqueConstraint("user_low", "user_high", name="uq_user_connection_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_low: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    user_high: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    requester: Mapped[str] = mapped_column(String(15), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending", index=True)
    low_shares_today: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    high_shares_today: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    low_read_message_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_read_message_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now, onupdate=now)


class ConnectionMessage(Base):
    __tablename__ = "connection_message"
    __table_args__ = (
        UniqueConstraint("connection_id", "sender", "client_id", name="uq_connection_message_client"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False, default="text")
    body: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    plan_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now, index=True)
