from dataclasses import dataclass
from decimal import Decimal


@dataclass
class OwnedAssetRow:
    asset_id: int
    asset_name: str
    asset_type: str
    quantity: Decimal
    weighted_avg_buy_price: Decimal
    total_invested_value: Decimal
    lot_count: int


@dataclass
class SummaryCards:
    total_invested: Decimal
