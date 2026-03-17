from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutlookSnapshot(Base):
    __tablename__ = "outlook_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    short_term_outlook: Mapped[str] = mapped_column(String(32), nullable=False)
    medium_term_outlook: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_summary: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_note: Mapped[str] = mapped_column(String(512), nullable=False)
    short_term_score: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    medium_term_score: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    asset = relationship("Asset", back_populates="outlook_snapshots")


Index("ix_outlook_snapshots_asset_id", OutlookSnapshot.asset_id)
Index("ix_outlook_snapshots_timestamp_utc", OutlookSnapshot.timestamp_utc)
