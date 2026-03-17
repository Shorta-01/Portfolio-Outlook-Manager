from dataclasses import dataclass
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


@dataclass
class SummaryCards:
    total_invested: Decimal
