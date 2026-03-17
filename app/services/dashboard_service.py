from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.schemas.dashboard import SummaryCards
from app.services.portfolio_service import PortfolioService


class DashboardService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.portfolio_service = PortfolioService(LotRepository(db))

    def owned_rows(self):
        assets = self.asset_repo.list_by_mode(AssetMode.OWNED)
        return [self.portfolio_service.aggregate_asset(asset) for asset in assets]

    def watchlist_rows(self):
        assets = self.asset_repo.list_by_mode(AssetMode.WATCHLIST)
        return assets

    def summary_cards(self) -> SummaryCards:
        total_invested = sum((row.total_invested_value_including_fees for row in self.owned_rows()), Decimal("0"))
        return SummaryCards(total_invested=total_invested)
