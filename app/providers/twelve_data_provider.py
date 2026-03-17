from datetime import date, datetime, timedelta

import httpx

from app.config import settings
from app.models.asset import Asset
from app.providers.base import MarketDataProvider
from app.providers.normalizers import normalize_currency, parse_provider_timestamp, to_decimal, utc_now_naive
from app.providers.symbol_resolver import SymbolResolver
from app.providers.types import NormalizedFXRate, NormalizedQuote


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"

    def __init__(self):
        self.base_url = "https://api.twelvedata.com"
        self.api_key = settings.twelve_data_api_key
        self.resolver = SymbolResolver()

    def fetch_latest_quote(self, asset: Asset) -> NormalizedQuote | None:
        resolved = self.resolver.resolve(asset)
        if not resolved.lookup_possible or not resolved.provider_symbol:
            return None
        payload = self._get("/price", {"symbol": resolved.provider_symbol})
        if "price" not in payload:
            return None
        return NormalizedQuote(self.name, resolved.provider_symbol, to_decimal(payload["price"]), normalize_currency(asset.quote_currency), utc_now_naive(), "spot", payload)

    def fetch_historical_daily(self, asset: Asset, start_date: date, end_date: date) -> list[NormalizedQuote]:
        resolved = self.resolver.resolve(asset)
        if not resolved.lookup_possible or not resolved.provider_symbol:
            return []
        payload = self._get(
            "/time_series",
            {"symbol": resolved.provider_symbol, "interval": "1day", "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "order": "ASC", "outputsize": 5000},
        )
        values = payload.get("values") or []
        return [
            NormalizedQuote(self.name, resolved.provider_symbol, to_decimal(item["close"]), normalize_currency(asset.quote_currency), parse_provider_timestamp(item["datetime"]), "1day", item)
            for item in values
            if "close" in item and "datetime" in item
        ]

    def fetch_historical_intraday(self, asset: Asset, start_datetime: datetime, end_datetime: datetime) -> list[NormalizedQuote]:
        resolved = self.resolver.resolve(asset)
        if not resolved.lookup_possible or not resolved.provider_symbol:
            return []
        payload = self._get(
            "/time_series",
            {
                "symbol": resolved.provider_symbol,
                "interval": "5min",
                "start_date": start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "order": "ASC",
                "outputsize": 5000,
            },
        )
        return [
            NormalizedQuote(self.name, resolved.provider_symbol, to_decimal(item["close"]), normalize_currency(asset.quote_currency), parse_provider_timestamp(item["datetime"]), "intraday", item)
            for item in payload.get("values") or []
            if "close" in item and "datetime" in item
        ]

    def fetch_latest_fx(self, base_currency: str, quote_currency: str) -> NormalizedFXRate | None:
        symbol = f"{base_currency.upper()}/{quote_currency.upper()}"
        payload = self._get("/price", {"symbol": symbol})
        if "price" not in payload:
            return None
        return NormalizedFXRate(self.name, base_currency.upper(), quote_currency.upper(), to_decimal(payload["price"]), utc_now_naive(), "spot", payload)

    def fetch_historical_fx(self, base_currency: str, quote_currency: str, start_date: date, end_date: date) -> list[NormalizedFXRate]:
        symbol = f"{base_currency.upper()}/{quote_currency.upper()}"
        payload = self._get(
            "/time_series",
            {"symbol": symbol, "interval": "1day", "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "order": "ASC", "outputsize": 5000},
        )
        return [
            NormalizedFXRate(self.name, base_currency.upper(), quote_currency.upper(), to_decimal(item["close"]), parse_provider_timestamp(item["datetime"]), "1day", item)
            for item in payload.get("values") or []
            if "close" in item and "datetime" in item
        ]

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            return {}
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}{path}", params={**params, "apikey": self.api_key})
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
