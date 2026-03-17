from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActionSnapshot(Base):
    __tablename__ = "action_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    action_label: Mapped[str] = mapped_column(String(32), nullable=False)
    action_score: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    invalidation_note: Mapped[str] = mapped_column(String(512), nullable=False)
    key_level_up: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    key_level_down: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    asset = relationship("Asset", back_populates="action_snapshots")


Index("ix_action_snapshots_asset_id", ActionSnapshot.asset_id)
Index("ix_action_snapshots_timestamp_utc", ActionSnapshot.timestamp_utc)
