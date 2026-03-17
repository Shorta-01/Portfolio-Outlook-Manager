from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PollingRule(Base):
    __tablename__ = "polling_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), unique=True)
    poll_every_minutes: Mapped[int] = mapped_column(Integer)
    market_hours_only: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_polled_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_due_at_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = relationship("Asset", back_populates="polling_rule")
