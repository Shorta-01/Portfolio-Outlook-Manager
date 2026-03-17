from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.dashboard_service import DashboardService
from app.services.valuation_service import ValuationService
from app.repositories.lot_repo import LotRepository
from app.repositories.fx_rate_repo import FXRateRepository


class StatusService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.polling_repo = PollingRuleRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.dashboard_service = DashboardService(db)
        self.valuation_service = ValuationService(LotRepository(db), MarketQuoteRepository(db), FXRateRepository(db))

    def database_reachable(self) -> bool:
        try:
            self.db.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def build(self) -> dict:
        owned_assets = self.asset_repo.list_by_mode(AssetMode.OWNED)
        latest_quote_count = 0
        stale_or_unknown = 0
        without_quote = 0
        for asset in owned_assets:
            latest = self.quote_repo.latest_for_asset(asset.id)
            if latest is None:
                without_quote += 1
                stale_or_unknown += 1
                continue
            latest_quote_count += 1
            freshness = self.valuation_service._freshness_from_timestamp(latest.provider_timestamp_utc)
            if freshness in {"stale", "unknown"}:
                stale_or_unknown += 1

        settings = self.settings_repo.get_first()
        base_currency = settings.portfolio_base_currency if settings else "EUR"
        summary = self.dashboard_service.summary_cards()
        owned_rows = self.dashboard_service.owned_rows()
        return {
            "app_status": "ok",
            "database_reachable": self.database_reachable(),
            "settings_present": settings is not None,
            "asset_counts": self.asset_repo.count_by_mode(),
            "polling_rule_count": self.polling_repo.count(),
            "scheduler_status": "placeholder",
            "provider_freshness": "active",
            "assets_with_latest_quote": latest_quote_count,
            "assets_stale_or_unknown_prices": stale_or_unknown,
            "assets_without_quote_data": without_quote,
            "assets_missing_fx_for_base_valuation": sum(1 for row in owned_rows if row.fx_status == "missing"),
            "totals_complete": summary.totals_complete,
            "missing_fx_asset_count": summary.missing_fx_asset_count,
            "missing_quote_asset_count": summary.missing_quote_asset_count,
            "base_currency": base_currency,
        }
