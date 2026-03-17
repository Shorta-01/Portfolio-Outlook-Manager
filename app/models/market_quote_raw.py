from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MarketQuoteRaw(Base):
    __tablename__ = "market_quotes_raw"
    __table_args__ = (
        Index("ix_market_quotes_raw_asset_ingested", "asset_id", "ingested_at_utc"),
        Index("ix_market_quotes_raw_asset_provider_ts", "asset_id", "provider_timestamp_utc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    provider_name: Mapped[str] = mapped_column(String(64))
    provider_symbol: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict] = mapped_column(JSON)
    provider_timestamp_utc: Mapped[datetime] = mapped_column(DateTime)
    ingested_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset = relationship("Asset", back_populates="market_quotes_raw")
