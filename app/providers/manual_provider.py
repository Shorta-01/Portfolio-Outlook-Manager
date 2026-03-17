from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.asset import Asset
from app.providers.base import MarketDataProvider
from app.providers.normalizers import utc_now_naive
from app.providers.types import NormalizedFXRate, NormalizedQuote
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.market_quote_repo import MarketQuoteRepository


class ManualProvider(MarketDataProvider):
    name = "manual"

    def __init__(self, quote_repo: MarketQuoteRepository, fx_repo: FXRateRepository):
        self.quote_repo = quote_repo
        self.fx_repo = fx_repo

    def fetch_latest_quote(self, asset: Asset) -> NormalizedQuote | None:
        latest = self.quote_repo.latest_for_asset(asset.id)
        if latest is None:
            return None
        return NormalizedQuote(
            provider_name=self.name,
            provider_symbol=asset.provider_symbol_primary or asset.display_name,
            price=Decimal(latest.price),
            quote_currency=latest.quote_currency,
            provider_timestamp_utc=latest.provider_timestamp_utc,
            interval_type="spot",
            payload={"source": "stored_quote"},
        )

    def fetch_historical_daily(self, asset: Asset, start_date: date, end_date: date) -> list[NormalizedQuote]:
        rows = self.quote_repo.recent_for_asset(asset.id, limit=2000)
        return [
            NormalizedQuote(self.name, asset.provider_symbol_primary or asset.display_name, Decimal(r.price), r.quote_currency, r.provider_timestamp_utc, "1day", {"source": "stored_quote"})
            for r in rows
            if start_date <= r.provider_timestamp_utc.date() <= end_date
        ]

    def fetch_historical_intraday(self, asset: Asset, start_datetime: datetime, end_datetime: datetime) -> list[NormalizedQuote]:
        rows = self.quote_repo.recent_for_asset(asset.id, limit=2000)
        return [
            NormalizedQuote(self.name, asset.provider_symbol_primary or asset.display_name, Decimal(r.price), r.quote_currency, r.provider_timestamp_utc, "intraday", {"source": "stored_quote"})
            for r in rows
            if start_datetime <= r.provider_timestamp_utc <= end_datetime
        ]

    def fetch_latest_fx(self, base_currency: str, quote_currency: str) -> NormalizedFXRate | None:
        pair = f"{base_currency.upper()}/{quote_currency.upper()}"
        latest = self.fx_repo.latest_for_pair(pair)
        if latest is None:
            return None
        return NormalizedFXRate(self.name, latest.base_currency, latest.quote_currency, Decimal(latest.rate), latest.provider_timestamp_utc, "spot", {"source": "stored_fx"})

    def fetch_historical_fx(self, base_currency: str, quote_currency: str, start_date: date, end_date: date) -> list[NormalizedFXRate]:
        latest = self.fetch_latest_fx(base_currency, quote_currency)
        if latest is None:
            return []
        out: list[NormalizedFXRate] = []
        current = start_date
        while current <= end_date:
            out.append(
                NormalizedFXRate(self.name, base_currency.upper(), quote_currency.upper(), latest.rate, datetime.combine(current, datetime.min.time()) + timedelta(hours=16), "1day", {"source": "synthetic_manual"})
            )
            current += timedelta(days=1)
        return out
