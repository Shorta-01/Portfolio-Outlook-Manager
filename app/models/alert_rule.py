from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_asset_id", "asset_id"),
        Index("ix_alert_rules_enabled", "enabled"),
        Index("ix_alert_rules_rule_type", "rule_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
    asset_mode_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_type_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    threshold_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = relationship("Asset", back_populates="alert_rules")
    alert_events = relationship("AlertEvent", back_populates="alert_rule")
