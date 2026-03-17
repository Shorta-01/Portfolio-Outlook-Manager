from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssetMode(str, Enum):
    OWNED = "owned"
    WATCHLIST = "watchlist"
    CASH = "cash"
    TERM_DEPOSIT = "term_deposit"


class AssetType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    FUND = "fund"
    GOLD = "gold"
    OIL = "oil"
    BOND = "bond"
    FOREX = "forex"
    CRYPTO = "crypto"
    CASH = "cash"
    TERM_DEPOSIT = "term_deposit"
    OTHER = "other"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol_internal: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType))
    asset_mode: Mapped[AssetMode] = mapped_column(SAEnum(AssetMode))
    quote_currency: Mapped[str] = mapped_column(String(8))
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_primary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_symbol_primary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_symbol_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_manual_asset: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lots = relationship("Lot", back_populates="asset", cascade="all, delete-orphan")
    polling_rule = relationship("PollingRule", back_populates="asset", uselist=False, cascade="all, delete-orphan")
