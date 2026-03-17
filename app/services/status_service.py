from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.scheduler.engine import scheduler_running
from app.services.dashboard_service import DashboardService
from app.services.outlook_evaluation_service import OutlookEvaluationService
from app.services.scheduler_state import scheduler_state
from app.services.valuation_service import ValuationService


class StatusService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.polling_repo = PollingRuleRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.dashboard_service = DashboardService(db)
        self.outlook_repo = OutlookSnapshotRepository(db)
        self.outlook_eval_service = OutlookEvaluationService(db)
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
        eval_scorecard = self.outlook_eval_service.global_scorecard()
        return {
            "app_status": "ok",
            "database_reachable": self.database_reachable(),
            "settings_present": settings is not None,
            "asset_counts": self.asset_repo.count_by_mode(),
            "polling_rule_count": self.polling_repo.count(),
            "scheduler_status": "running" if scheduler_running() else "stopped",
            "scheduler_running": scheduler_running(),
            "provider_freshness": "active",
            "assets_with_latest_quote": latest_quote_count,
            "assets_stale_or_unknown_prices": stale_or_unknown,
            "assets_without_quote_data": without_quote,
            "assets_missing_fx_for_base_valuation": sum(1 for row in owned_rows if row.fx_status == "missing"),
            "totals_complete": summary.totals_complete,
            "missing_fx_asset_count": summary.missing_fx_asset_count,
            "missing_quote_asset_count": summary.missing_quote_asset_count,
            "base_currency": base_currency,
            "last_successful_poll_utc": scheduler_state.last_successful_poll_utc,
            "last_successful_backfill_utc": scheduler_state.last_successful_backfill_utc,
            "assets_with_history_count": sum(1 for asset in self.asset_repo.list_all() if self.quote_repo.has_quote_for_asset(asset.id)),
            "assets_without_history_count": sum(1 for asset in self.asset_repo.list_all() if not self.quote_repo.has_quote_for_asset(asset.id)),
            "quote_rows_count": self.quote_repo.count_rows(),
            "fx_rows_count": FXRateRepository(self.db).count_rows(),
            "assets_with_outlook_count": sum(1 for asset in self.asset_repo.list_all() if self.outlook_repo.get_latest_by_asset(asset.id) is not None),
            "assets_without_outlook_count": sum(1 for asset in self.asset_repo.list_all() if self.outlook_repo.get_latest_by_asset(asset.id) is None),
            "last_successful_outlook_run_utc": scheduler_state.last_successful_outlook_run_utc,
            "total_outlook_snapshots": eval_scorecard["total_outlook_snapshots"],
            "total_evaluated_outlooks": eval_scorecard["total_evaluated"],
            "global_short_term_hit_rate": eval_scorecard["accuracy"]["short"]["hit_rate"],
            "global_medium_term_hit_rate": eval_scorecard["accuracy"]["medium"]["hit_rate"],
            "global_confidence_bucket_stats": eval_scorecard["confidence"],
            "last_successful_outlook_evaluation_run_utc": scheduler_state.last_successful_outlook_evaluation_run_utc,
            "evaluated_outlook_count": scheduler_state.evaluated_outlook_count,
            "unevaluated_outlook_count": scheduler_state.unevaluated_outlook_count,
        }
