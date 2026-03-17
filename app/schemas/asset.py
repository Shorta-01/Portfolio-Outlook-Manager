from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.asset import AssetMode, AssetType


class AssetCreate(BaseModel):
    display_name: str = Field(min_length=1)
    asset_type: AssetType
    asset_mode: AssetMode
    quote_currency: str = Field(min_length=1)
    term_deposit_rate: Decimal | None = Field(default=None, ge=0)
    exchange: str | None = None
    isin: str | None = None
    is_manual_asset: bool = True


class AssetRead(BaseModel):
    id: int
    display_name: str
    asset_type: AssetType
    asset_mode: AssetMode
    quote_currency: str

    class Config:
        from_attributes = True
