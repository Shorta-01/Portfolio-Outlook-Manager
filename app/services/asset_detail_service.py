from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.portfolio_service import PortfolioService


class AssetDetailService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.portfolio_service = PortfolioService(self.lot_repo)

    def build(self, asset_id: int) -> dict:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")
        lots = self.lot_repo.list_for_asset(asset.id) if asset.asset_mode == AssetMode.OWNED else []
        settings = self.settings_repo.get_first()
        base_currency = settings.portfolio_base_currency if settings else "EUR"
        aggregate = self.portfolio_service.aggregate_asset(asset, portfolio_base_currency=base_currency) if asset.asset_mode == AssetMode.OWNED else None
        return {"asset": asset, "lots": lots, "aggregate": aggregate, "is_owned": asset.asset_mode == AssetMode.OWNED}
