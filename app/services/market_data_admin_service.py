from sqlalchemy.orm import Session

from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.providers.types import NormalizedFXRate, NormalizedQuote
from app.schemas.quote_fx import FXRateCreate, MarketQuoteCreate
from app.services.market_data_ingestion_service import MarketDataIngestionService


class MarketDataAdminService:
    def __init__(self, db: Session):
        self.db = db
        self.ingestion = MarketDataIngestionService(db)

    def create_quote(self, payload: MarketQuoteCreate) -> MarketQuote:
        normalized = self.ingestion.ingest_quote(
            payload.asset_id,
            NormalizedQuote(
                provider_name=payload.provider_name,
                provider_symbol=payload.provider_symbol,
                price=payload.price,
                quote_currency=payload.quote_currency.upper(),
                provider_timestamp_utc=payload.provider_timestamp_utc,
                interval_type="spot",
                payload={"price": str(payload.price), "quote_currency": payload.quote_currency.upper()},
            ),
            is_backfill=False,
        )
        self.db.commit()
        self.db.refresh(normalized)
        return normalized

    def create_fx_rate(self, payload: FXRateCreate) -> FXRate:
        base = payload.base_currency.upper()
        quote = payload.quote_currency.upper()
        fx = self.ingestion.ingest_fx(
            NormalizedFXRate(
                provider_name=payload.provider_name,
                base_currency=base,
                quote_currency=quote,
                rate=payload.rate,
                provider_timestamp_utc=payload.provider_timestamp_utc,
                interval_type="spot",
                payload={"rate": str(payload.rate)},
            )
        )
        self.db.commit()
        self.db.refresh(fx)
        return fx
