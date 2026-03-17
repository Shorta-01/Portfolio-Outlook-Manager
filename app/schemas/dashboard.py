from dataclasses import dataclass
from decimal import Decimal


@dataclass
class AssetValuation:
    quote_currency: str
    base_currency: str
    quote_price: Decimal | None
    fx_rate_to_base: Decimal | None
    value_in_quote: Decimal | None
    value_in_base: Decimal | None
    unrealized_pl_base: Decimal | None
    has_quote: bool
    has_base_value: bool
    fx_status: str
    source_status: str
    freshness_status: str
    valuation_warning: str | None


@dataclass
class OwnedAssetRow:
    asset_id: int
    asset_name: str
    asset_type: str
    total_quantity: Decimal
    weighted_avg_buy_price_ex_fees: Decimal
    total_fees: Decimal
    total_invested_value_including_fees: Decimal
    cost_basis_per_unit_including_fees: Decimal
    lot_count: int
    valuation: AssetValuation


@dataclass
class SummaryCards:
    total_invested: Decimal
    total_current_value_base: Decimal
    total_unrealized_pl_base: Decimal
    totals_complete: bool
    missing_fx_asset_count: int
    missing_quote_asset_count: int
