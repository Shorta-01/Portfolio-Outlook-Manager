from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FXRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        Index("ix_fx_rates_pair_provider_ts", "pair_code", "provider_timestamp_utc"),
        Index("ix_fx_rates_pair_ingested", "pair_code", "ingested_at_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pair_code: Mapped[str] = mapped_column(String(16), index=True)
    base_currency: Mapped[str] = mapped_column(String(8))
    quote_currency: Mapped[str] = mapped_column(String(8))
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    provider_name: Mapped[str] = mapped_column(String(64))
    provider_timestamp_utc: Mapped[datetime] = mapped_column(DateTime)
    ingested_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    interval_type: Mapped[str] = mapped_column(String(32), default="spot")
