from sqlalchemy.orm import Session

from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.models.market_quote_raw import MarketQuoteRaw
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.schemas.quote_fx import FXRateCreate, MarketQuoteCreate


class MarketDataAdminService:
    def __init__(self, db: Session):
        self.db = db
        self.quote_repo = MarketQuoteRepository(db)
        self.fx_repo = FXRateRepository(db)

    def create_quote(self, payload: MarketQuoteCreate) -> MarketQuote:
        normalized = MarketQuote(
            asset_id=payload.asset_id,
            provider_name=payload.provider_name,
            price=payload.price,
            quote_currency=payload.quote_currency.upper(),
            provider_timestamp_utc=payload.provider_timestamp_utc,
            freshness_status="unknown",
            interval_type="spot",
            is_backfill=False,
        )
        raw = MarketQuoteRaw(
            asset_id=payload.asset_id,
            provider_name=payload.provider_name,
            provider_symbol=payload.provider_symbol,
            payload_json={"price": str(payload.price), "quote_currency": payload.quote_currency.upper()},
            provider_timestamp_utc=payload.provider_timestamp_utc,
            status="ok",
        )
        self.quote_repo.add(normalized)
        self.quote_repo.add_raw(raw)
        self.db.commit()
        self.db.refresh(normalized)
        return normalized

    def create_fx_rate(self, payload: FXRateCreate) -> FXRate:
        base = payload.base_currency.upper()
        quote = payload.quote_currency.upper()
        fx = FXRate(
            pair_code=f"{base}/{quote}",
            base_currency=base,
            quote_currency=quote,
            rate=payload.rate,
            provider_name=payload.provider_name,
            provider_timestamp_utc=payload.provider_timestamp_utc,
            interval_type="spot",
        )
        self.fx_repo.add(fx)
        self.db.commit()
        self.db.refresh(fx)
        return fx
