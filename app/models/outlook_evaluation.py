from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutlookEvaluation(Base):
    __tablename__ = "outlook_evaluations"
    __table_args__ = (UniqueConstraint("outlook_snapshot_id", "horizon_type", name="uq_outlook_eval_snapshot_horizon"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    outlook_snapshot_id: Mapped[int] = mapped_column(ForeignKey("outlook_snapshots.id"), nullable=False)
    evaluation_timestamp_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    horizon_type: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon_end_timestamp_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(32), nullable=False)
    realized_return: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    realized_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    was_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence_at_prediction: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_bucket: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_note: Mapped[str] = mapped_column(String(512), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    asset = relationship("Asset", back_populates="outlook_evaluations")
    outlook_snapshot = relationship("OutlookSnapshot", back_populates="evaluations")


Index("ix_outlook_evaluations_asset_id", OutlookEvaluation.asset_id)
Index("ix_outlook_evaluations_outlook_snapshot_id", OutlookEvaluation.outlook_snapshot_id)
Index("ix_outlook_evaluations_horizon_type", OutlookEvaluation.horizon_type)
Index("ix_outlook_evaluations_evaluation_timestamp_utc", OutlookEvaluation.evaluation_timestamp_utc)
