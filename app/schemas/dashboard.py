from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


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
    current_price: Decimal | None = None
    value_now: Decimal | None = None
    value_now_quote_currency: Decimal | None = None
    unrealized_pl_amount: Decimal | None = None
    unrealized_pl_percent: Decimal | None = None
    has_quote: bool = False
    has_base_value: bool = False
    fx_status: str = "not_applicable"
    freshness_status: str = "unknown"
    source_label: str = "Unknown"
    valuation_warning: str | None = None
    outlook: str | None = None
    suggested_action: str | None = None
    confidence: str | None = None
    urgency: str | None = None
    last_update_utc: datetime | None = None
    quote_currency: str | None = None
    isin: str | None = None
    provider_symbol: str | None = None


@dataclass
class SummaryCards:
    total_invested: Decimal
    total_current_value: Decimal | None
    total_unrealized_pl_amount: Decimal | None
    total_unrealized_pl_percent: Decimal | None
    totals_complete: bool
    missing_fx_asset_count: int
    missing_quote_asset_count: int
    omitted_from_totals_count: int
