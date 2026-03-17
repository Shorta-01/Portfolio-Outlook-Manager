from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.asset import AssetMode, AssetType


class AssetCreate(BaseModel):
    display_name: str = Field(min_length=1)
    asset_type: AssetType
    asset_mode: AssetMode
    quote_currency: str = Field(min_length=1)
    exchange: str | None = None
    isin: str | None = None
    is_manual_asset: bool = True
    current_amount: Decimal | None = Field(default=None, ge=0)
    principal_amount: Decimal | None = Field(default=None, gt=0)
    interest_rate_annual: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    maturity_date: date | None = None
    accrual_method: str | None = None
    payout_type: str | None = None
    bank_name: str | None = None

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.asset_type == AssetType.CASH or self.asset_mode == AssetMode.CASH:
            if self.current_amount is None:
                raise ValueError("cash amount is required for cash assets")
        if self.asset_type == AssetType.TERM_DEPOSIT or self.asset_mode == AssetMode.TERM_DEPOSIT:
            if self.principal_amount is None or self.interest_rate_annual is None or self.start_date is None or self.maturity_date is None:
                raise ValueError("term deposit requires principal, annual rate, start date, and maturity date")
            if self.maturity_date < self.start_date:
                raise ValueError("maturity_date must be on or after start_date")
        return self


class AssetRead(BaseModel):
    id: int
    display_name: str
    asset_type: AssetType
    asset_mode: AssetMode
    quote_currency: str

    class Config:
        from_attributes = True
