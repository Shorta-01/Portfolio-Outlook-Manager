from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MarketQuoteCreate(BaseModel):
    asset_id: int
    provider_name: str = Field(min_length=1)
    provider_symbol: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    quote_currency: str = Field(min_length=1)
    provider_timestamp_utc: datetime


class FXRateCreate(BaseModel):
    base_currency: str = Field(min_length=1)
    quote_currency: str = Field(min_length=1)
    rate: Decimal = Field(gt=0)
    provider_name: str = Field(min_length=1)
    provider_timestamp_utc: datetime
