from decimal import Decimal

from app.models.asset import Asset
from app.repositories.lot_repo import LotRepository
from app.schemas.dashboard import OwnedAssetRow


class PortfolioService:
    def __init__(self, lot_repo: LotRepository):
        self.lot_repo = lot_repo

    def aggregate_asset(self, asset: Asset) -> OwnedAssetRow:
        lots = self.lot_repo.list_for_asset(asset.id)
        total_qty = sum((lot.quantity for lot in lots), Decimal("0"))
        total_invested = sum((lot.quantity * lot.buy_price + lot.fees for lot in lots), Decimal("0"))
        avg_price = (total_invested / total_qty) if total_qty > 0 else Decimal("0")
        return OwnedAssetRow(
            asset_id=asset.id,
            asset_name=asset.display_name,
            asset_type=asset.asset_type.value,
            quantity=total_qty,
            weighted_avg_buy_price=avg_price,
            total_invested_value=total_invested,
            lot_count=len(lots),
        )
