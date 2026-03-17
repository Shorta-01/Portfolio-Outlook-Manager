from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_base_currency: Mapped[str] = mapped_column(String(8), default="EUR")
    default_poll_every_minutes: Mapped[int] = mapped_column(Integer, default=5)
    use_market_hours_default: Mapped[bool] = mapped_column(Boolean, default=False)
    backfill_daily_years_default: Mapped[int] = mapped_column(Integer, default=5)
    backfill_intraday_days_default: Mapped[int] = mapped_column(Integer, default=30)
    ui_theme_preference: Mapped[str] = mapped_column(String(32), default="dark")
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
