from decimal import Decimal

from app.models.asset import Asset
from app.repositories.lot_repo import LotRepository
from app.schemas.dashboard import OwnedAssetRow


class PortfolioService:
    def __init__(self, lot_repo: LotRepository):
        self.lot_repo = lot_repo

    def aggregate_asset(self, asset: Asset) -> OwnedAssetRow:
        lots = self.lot_repo.list_for_asset(asset.id)
        total_quantity = sum((lot.quantity for lot in lots), Decimal("0"))
        total_fees = sum((lot.fees for lot in lots), Decimal("0"))
        total_buy_value_ex_fees = sum((lot.quantity * lot.buy_price for lot in lots), Decimal("0"))
        total_invested_value_including_fees = total_buy_value_ex_fees + total_fees
        weighted_avg_buy_price_ex_fees = (total_buy_value_ex_fees / total_quantity) if total_quantity > 0 else Decimal("0")
        cost_basis_per_unit_including_fees = (total_invested_value_including_fees / total_quantity) if total_quantity > 0 else Decimal("0")

        return OwnedAssetRow(
            asset_id=asset.id,
            asset_name=asset.display_name,
            asset_type=asset.asset_type.value,
            total_quantity=total_quantity,
            weighted_avg_buy_price_ex_fees=weighted_avg_buy_price_ex_fees,
            total_fees=total_fees,
            total_invested_value_including_fees=total_invested_value_including_fees,
            cost_basis_per_unit_including_fees=cost_basis_per_unit_including_fees,
            lot_count=len(lots),
        )
