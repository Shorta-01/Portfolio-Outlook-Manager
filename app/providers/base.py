from abc import ABC, abstractmethod
from datetime import date, datetime

from app.models.asset import Asset
from app.providers.types import NormalizedFXRate, NormalizedQuote


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def fetch_latest_quote(self, asset: Asset) -> NormalizedQuote | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_historical_daily(self, asset: Asset, start_date: date, end_date: date) -> list[NormalizedQuote]:
        raise NotImplementedError

    @abstractmethod
    def fetch_historical_intraday(self, asset: Asset, start_datetime: datetime, end_datetime: datetime) -> list[NormalizedQuote]:
        raise NotImplementedError

    @abstractmethod
    def fetch_latest_fx(self, base_currency: str, quote_currency: str) -> NormalizedFXRate | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_historical_fx(self, base_currency: str, quote_currency: str, start_date: date, end_date: date) -> list[NormalizedFXRate]:
        raise NotImplementedError
