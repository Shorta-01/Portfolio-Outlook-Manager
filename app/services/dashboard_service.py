from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.dashboard import SummaryCards
from app.services.portfolio_service import PortfolioService


class DashboardService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.portfolio_service = PortfolioService(LotRepository(db))
        self.settings_repo = SettingsRepository(db)

    def _base_currency(self) -> str:
        settings = self.settings_repo.get_first()
        return settings.portfolio_base_currency if settings else "EUR"

    def owned_rows(self, quote_price_by_asset_id: dict[int, Decimal] | None = None, fx_rate_by_currency: dict[str, Decimal] | None = None):
        assets = self.asset_repo.list_by_mode(AssetMode.OWNED)
        base_currency = self._base_currency()
        quote_price_by_asset_id = quote_price_by_asset_id or {}
        fx_rate_by_currency = {k.upper(): v for k, v in (fx_rate_by_currency or {}).items()}
        rows = []
        for asset in assets:
            rows.append(
                self.portfolio_service.aggregate_asset(
                    asset,
                    portfolio_base_currency=base_currency,
                    latest_quote_price=quote_price_by_asset_id.get(asset.id),
                    fx_rate_to_base=fx_rate_by_currency.get(asset.quote_currency.upper()),
                )
            )
        return rows

    def watchlist_rows(self):
        assets = self.asset_repo.list_by_mode(AssetMode.WATCHLIST)
        return assets

    def summary_cards(self, rows: list | None = None) -> SummaryCards:
        rows = rows if rows is not None else self.owned_rows()
        total_invested = sum((row.total_invested_value_including_fees for row in rows), Decimal("0"))
        complete_rows = [row for row in rows if row.valuation.has_base_value]
        total_current_value_base = sum((row.valuation.value_in_base for row in complete_rows), Decimal("0"))
        total_unrealized_pl_base = sum((row.valuation.unrealized_pl_base for row in complete_rows), Decimal("0"))
        missing_fx_asset_count = sum(1 for row in rows if row.valuation.fx_status == "missing")
        missing_quote_asset_count = sum(1 for row in rows if not row.valuation.has_quote)
        totals_complete = (missing_fx_asset_count + missing_quote_asset_count) == 0
        return SummaryCards(
            total_invested=total_invested,
            total_current_value_base=total_current_value_base,
            total_unrealized_pl_base=total_unrealized_pl_base,
            totals_complete=totals_complete,
            missing_fx_asset_count=missing_fx_asset_count,
            missing_quote_asset_count=missing_quote_asset_count,
        )
