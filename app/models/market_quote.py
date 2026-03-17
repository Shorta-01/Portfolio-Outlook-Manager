from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MarketQuote(Base):
    __tablename__ = "market_quotes"
    __table_args__ = (
        Index("ix_market_quotes_asset_provider_ts", "asset_id", "provider_timestamp_utc"),
        Index("ix_market_quotes_asset_ingested", "asset_id", "ingested_at_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    provider_name: Mapped[str] = mapped_column(String(64))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    quote_currency: Mapped[str] = mapped_column(String(8))
    provider_timestamp_utc: Mapped[datetime] = mapped_column(DateTime)
    ingested_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_backfill: Mapped[bool] = mapped_column(Boolean, default=False)
    interval_type: Mapped[str] = mapped_column(String(32), default="spot")
    freshness_status: Mapped[str] = mapped_column(String(32), default="unknown")

    asset = relationship("Asset", back_populates="market_quotes")
