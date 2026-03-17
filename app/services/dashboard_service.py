from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.dashboard import SummaryCards
from app.services.valuation_service import ValuationService


class DashboardService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.valuation_service = ValuationService(LotRepository(db), MarketQuoteRepository(db), FXRateRepository(db))

    def _base_currency(self) -> str:
        settings = self.settings_repo.get_first()
        return settings.portfolio_base_currency if settings else "EUR"

    def owned_rows(self):
        assets = self.asset_repo.list_by_mode(AssetMode.OWNED)
        base_currency = self._base_currency()
        return [self.valuation_service.aggregate_owned_asset(asset, base_currency) for asset in assets]

    def watchlist_rows(self):
        return self.asset_repo.list_by_mode(AssetMode.WATCHLIST)

    def summary_cards(self) -> SummaryCards:
        rows = self.owned_rows()
        total_invested = sum((row.total_invested_value_including_fees for row in rows), Decimal("0"))
        rows_with_base = [row for row in rows if row.has_base_value and row.value_now is not None]
        total_current = sum((row.value_now for row in rows_with_base), Decimal("0"))
        pl_amount = total_current - total_invested
        pl_percent = (pl_amount / total_invested * Decimal("100")) if total_invested > 0 else None
        missing_fx_asset_count = sum(1 for row in rows if row.fx_status == "missing")
        missing_quote_asset_count = sum(1 for row in rows if not row.has_quote)
        omitted_from_totals_count = sum(1 for row in rows if not row.has_base_value)
        return SummaryCards(
            total_invested=total_invested,
            total_current_value=total_current,
            total_unrealized_pl_amount=pl_amount,
            total_unrealized_pl_percent=pl_percent,
            totals_complete=omitted_from_totals_count == 0,
            missing_fx_asset_count=missing_fx_asset_count,
            missing_quote_asset_count=missing_quote_asset_count,
            omitted_from_totals_count=omitted_from_totals_count,
        )
