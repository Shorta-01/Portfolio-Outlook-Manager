from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_quote import MarketQuote
from app.models.market_quote_raw import MarketQuoteRaw


class MarketQuoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, quote: MarketQuote) -> MarketQuote:
        self.db.add(quote)
        self.db.flush()
        return quote

    def add_raw(self, quote_raw: MarketQuoteRaw) -> MarketQuoteRaw:
        self.db.add(quote_raw)
        self.db.flush()
        return quote_raw

    def latest_for_asset(self, asset_id: int) -> MarketQuote | None:
        stmt = (
            select(MarketQuote)
            .where(MarketQuote.asset_id == asset_id)
            .order_by(MarketQuote.provider_timestamp_utc.desc(), MarketQuote.ingested_at_utc.desc(), MarketQuote.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def recent_for_asset(self, asset_id: int, limit: int = 50) -> list[MarketQuote]:
        stmt = (
            select(MarketQuote)
            .where(MarketQuote.asset_id == asset_id)
            .order_by(MarketQuote.provider_timestamp_utc.desc(), MarketQuote.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def has_quote_for_asset(self, asset_id: int) -> bool:
        return self.latest_for_asset(asset_id) is not None

    def latest_at_or_before(self, asset_id: int, at_utc: datetime) -> MarketQuote | None:
        stmt = (
            select(MarketQuote)
            .where(MarketQuote.asset_id == asset_id, MarketQuote.provider_timestamp_utc <= at_utc)
            .order_by(MarketQuote.provider_timestamp_utc.desc(), MarketQuote.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def earliest_at_or_after(self, asset_id: int, at_utc: datetime) -> MarketQuote | None:
        stmt = (
            select(MarketQuote)
            .where(MarketQuote.asset_id == asset_id, MarketQuote.provider_timestamp_utc >= at_utc)
            .order_by(MarketQuote.provider_timestamp_utc.asc(), MarketQuote.id.asc())
        )
        return self.db.execute(stmt).scalars().first()

    def find_duplicate_normalized(
        self,
        *,
        asset_id: int,
        provider_name: str,
        provider_timestamp_utc: datetime,
        price: Decimal,
        quote_currency: str,
        interval_type: str,
    ) -> MarketQuote | None:
        stmt = select(MarketQuote).where(
            MarketQuote.asset_id == asset_id,
            MarketQuote.provider_name == provider_name,
            MarketQuote.provider_timestamp_utc == provider_timestamp_utc,
            MarketQuote.price == price,
            MarketQuote.quote_currency == quote_currency,
            MarketQuote.interval_type == interval_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def find_duplicate_raw(
        self,
        *,
        asset_id: int,
        provider_name: str,
        provider_symbol: str,
        provider_timestamp_utc: datetime,
    ) -> MarketQuoteRaw | None:
        stmt = select(MarketQuoteRaw).where(
            MarketQuoteRaw.asset_id == asset_id,
            MarketQuoteRaw.provider_name == provider_name,
            MarketQuoteRaw.provider_symbol == provider_symbol,
            MarketQuoteRaw.provider_timestamp_utc == provider_timestamp_utc,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_rows(self) -> int:
        return len(self.db.execute(select(MarketQuote.id)).scalars().all())
