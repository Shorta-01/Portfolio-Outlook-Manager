from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class ResolvedInstrument:
    provider_name: str | None
    provider_symbol: str | None
    lookup_possible: bool
    lookup_reason: str
    pricing_classification: str


@dataclass
class NormalizedQuote:
    provider_name: str
    provider_symbol: str
    price: Decimal
    quote_currency: str
    provider_timestamp_utc: datetime
    interval_type: str = "spot"
    payload: dict | None = None


@dataclass
class NormalizedFXRate:
    provider_name: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    provider_timestamp_utc: datetime
    interval_type: str = "spot"
    payload: dict | None = None


@dataclass
class HistoricalWindow:
    start_date: date
    end_date: date
