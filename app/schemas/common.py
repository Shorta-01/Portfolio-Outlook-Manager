from decimal import Decimal


def to_decimal(value: str | Decimal | float | int) -> Decimal:
    return Decimal(str(value))
