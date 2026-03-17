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
