from datetime import datetime, timezone
from decimal import Decimal


def parse_provider_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def to_decimal(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def normalize_currency(code: str) -> str:
    return code.strip().upper()


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
