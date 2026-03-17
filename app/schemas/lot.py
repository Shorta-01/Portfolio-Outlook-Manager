from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LotCreate(BaseModel):
    asset_id: int
    quantity: Decimal = Field(gt=0)
    buy_price: Decimal = Field(gt=0)
    buy_currency: str = Field(min_length=1)
    buy_date: date
    fees: Decimal = Field(default=Decimal("0"))
    notes: str | None = None


class LotUpdate(BaseModel):
    quantity: Decimal = Field(gt=0)
    buy_price: Decimal = Field(gt=0)
    buy_currency: str = Field(min_length=1)
    buy_date: date
    fees: Decimal = Field(default=Decimal("0"))
    notes: str | None = None
