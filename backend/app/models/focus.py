from sqlalchemy import BigInteger, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FocusState(Base):
    __tablename__ = "focus_state"

    owner: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)


class FocusRecord(Base):
    __tablename__ = "focus_record"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    finished_at: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
