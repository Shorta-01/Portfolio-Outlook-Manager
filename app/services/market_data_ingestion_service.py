from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.models.market_quote_raw import MarketQuoteRaw
from app.providers.types import NormalizedFXRate, NormalizedQuote
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.services.valuation_service import DELAYED_SECS, FRESH_SECS


class MarketDataIngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.quote_repo = MarketQuoteRepository(db)
        self.fx_repo = FXRateRepository(db)

    def ingest_quote(self, asset_id: int, quote: NormalizedQuote, is_backfill: bool) -> MarketQuote:
        existing = self.quote_repo.find_duplicate_raw(
            asset_id=asset_id,
            provider_name=quote.provider_name,
            provider_symbol=quote.provider_symbol,
            provider_timestamp_utc=quote.provider_timestamp_utc,
        )
        if existing is None:
            self.quote_repo.add_raw(
                MarketQuoteRaw(
                    asset_id=asset_id,
                    provider_name=quote.provider_name,
                    provider_symbol=quote.provider_symbol,
                    payload_json=quote.payload or {},
                    provider_timestamp_utc=quote.provider_timestamp_utc,
                    status="ok",
                )
            )

        duplicate = self.quote_repo.find_duplicate_normalized(
            asset_id=asset_id,
            provider_name=quote.provider_name,
            provider_timestamp_utc=quote.provider_timestamp_utc,
            price=quote.price,
            quote_currency=quote.quote_currency.upper(),
            interval_type=quote.interval_type,
        )
        if duplicate is not None:
            return duplicate

        row = MarketQuote(
            asset_id=asset_id,
            provider_name=quote.provider_name,
            price=quote.price,
            quote_currency=quote.quote_currency.upper(),
            provider_timestamp_utc=quote.provider_timestamp_utc,
            is_backfill=is_backfill,
            interval_type=quote.interval_type,
            freshness_status=self._freshness_from_timestamp(quote.provider_timestamp_utc),
        )
        self.quote_repo.add(row)
        return row

    def ingest_fx(self, fx: NormalizedFXRate) -> FXRate:
        pair_code = f"{fx.base_currency.upper()}/{fx.quote_currency.upper()}"
        duplicate = self.fx_repo.find_duplicate(
            pair_code=pair_code,
            provider_name=fx.provider_name,
            provider_timestamp_utc=fx.provider_timestamp_utc,
            rate=fx.rate,
            interval_type=fx.interval_type,
        )
        if duplicate is not None:
            return duplicate

        row = FXRate(
            pair_code=pair_code,
            base_currency=fx.base_currency.upper(),
            quote_currency=fx.quote_currency.upper(),
            rate=fx.rate,
            provider_name=fx.provider_name,
            provider_timestamp_utc=fx.provider_timestamp_utc,
            interval_type=fx.interval_type,
        )
        self.fx_repo.add(row)
        return row

    def _freshness_from_timestamp(self, provider_timestamp_utc: datetime) -> str:
        now = datetime.now(timezone.utc)
        ts = provider_timestamp_utc.replace(tzinfo=timezone.utc) if provider_timestamp_utc.tzinfo is None else provider_timestamp_utc
        age_seconds = (now - ts).total_seconds()
        if age_seconds <= FRESH_SECS:
            return "fresh"
        if age_seconds <= DELAYED_SECS:
            return "delayed"
        return "stale"
