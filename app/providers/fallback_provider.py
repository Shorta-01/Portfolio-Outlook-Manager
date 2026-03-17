from datetime import date, datetime

from app.models.asset import Asset
from app.providers.base import MarketDataProvider
from app.providers.types import NormalizedFXRate, NormalizedQuote


class FallbackProvider(MarketDataProvider):
    def __init__(self, providers: list[MarketDataProvider]):
        self.providers = providers
        self.name = "fallback"

    def fetch_latest_quote(self, asset: Asset) -> NormalizedQuote | None:
        for provider in self.providers:
            quote = provider.fetch_latest_quote(asset)
            if quote is not None:
                return quote
        return None

    def fetch_historical_daily(self, asset: Asset, start_date: date, end_date: date) -> list[NormalizedQuote]:
        for provider in self.providers:
            rows = provider.fetch_historical_daily(asset, start_date, end_date)
            if rows:
                return rows
        return []

    def fetch_historical_intraday(self, asset: Asset, start_datetime: datetime, end_datetime: datetime) -> list[NormalizedQuote]:
        for provider in self.providers:
            rows = provider.fetch_historical_intraday(asset, start_datetime, end_datetime)
            if rows:
                return rows
        return []

    def fetch_latest_fx(self, base_currency: str, quote_currency: str) -> NormalizedFXRate | None:
        for provider in self.providers:
            row = provider.fetch_latest_fx(base_currency, quote_currency)
            if row is not None:
                return row
        return None

    def fetch_historical_fx(self, base_currency: str, quote_currency: str, start_date: date, end_date: date) -> list[NormalizedFXRate]:
        for provider in self.providers:
            rows = provider.fetch_historical_fx(base_currency, quote_currency, start_date, end_date)
            if rows:
                return rows
        return []
