from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.alert_event_repo import AlertEventRepository
from app.repositories.alert_rule_repo import AlertRuleRepository
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.scheduler.engine import scheduler_running
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService
from app.services.maintenance_service import MaintenanceService
from app.services.outlook_evaluation_service import OutlookEvaluationService
from app.services.scheduler_state import scheduler_state
from app.services.valuation_service import ValuationService


class StatusService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.alert_rule_repo = AlertRuleRepository(db)
        self.alert_event_repo = AlertEventRepository(db)
        self.polling_repo = PollingRuleRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.dashboard_service = DashboardService(db)
        self.outlook_repo = OutlookSnapshotRepository(db)
        self.outlook_eval_service = OutlookEvaluationService(db)
        self.export_service = ExportService(db)
        self.valuation_service = ValuationService(LotRepository(db), MarketQuoteRepository(db), FXRateRepository(db))

    def database_reachable(self) -> bool:
        try:
            self.db.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def _runtime_state(self) -> dict:
        jobs = scheduler_state.jobs
        return {
            "app_status": "ok",
            "scheduler_status": "running" if scheduler_running() else "stopped",
            "scheduler_running": scheduler_running(),
            "scheduler_started_at_utc": scheduler_state.startup_utc,
            "scheduler_stopped_at_utc": scheduler_state.shutdown_utc,
            "scheduler_start_error": scheduler_state.last_start_error,
            "last_successful_poll_utc": jobs["polling"].last_success_utc,
            "last_failed_poll_utc": jobs["polling"].last_failure_utc,
            "poll_error_count": jobs["polling"].error_count,
            "poll_last_error_summary": jobs["polling"].last_error_summary,
            "last_successful_backfill_utc": jobs["backfill"].last_success_utc,
            "last_failed_backfill_utc": jobs["backfill"].last_failure_utc,
            "last_successful_outlook_run_utc": jobs["outlook"].last_success_utc,
            "last_failed_outlook_run_utc": jobs["outlook"].last_failure_utc,
            "last_successful_outlook_evaluation_run_utc": jobs["evaluation"].last_success_utc,
            "last_failed_outlook_evaluation_run_utc": jobs["evaluation"].last_failure_utc,
            "last_successful_alert_run_utc": jobs["alerts"].last_success_utc,
            "last_failed_alert_run_utc": jobs["alerts"].last_failure_utc,
            "last_successful_cleanup_run_utc": jobs["cleanup"].last_success_utc,
            "last_failed_cleanup_run_utc": jobs["cleanup"].last_failure_utc,
            "cleanup_error_count": jobs["cleanup"].error_count,
            "cleanup_last_error_summary": jobs["cleanup"].last_error_summary,
            "last_cleanup_summary": scheduler_state.last_cleanup_summary,
            "last_successful_backup_utc": jobs["backup"].last_success_utc,
            "last_failed_backup_utc": jobs["backup"].last_failure_utc,
            "backup_error_count": jobs["backup"].error_count,
        }

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
        all_assets = self.asset_repo.list_all()
        backup_meta = self.export_service.latest_backup_metadata()
        runtime = self._runtime_state()
        maintenance = MaintenanceService(self.db).scan()

        return {
            **runtime,
            "database_reachable": self.database_reachable(),
            "settings_present": settings is not None,
            "asset_counts": self.asset_repo.count_by_mode(),
            "archived_asset_count": maintenance["archived_asset_count"],
            "maintenance_issue_count": maintenance["issue_count"],
            "last_maintenance_scan_utc": maintenance["scanned_at_utc"],
            "polling_rule_count": self.polling_repo.count(),
            "provider_freshness": "active",
            "assets_with_latest_quote": latest_quote_count,
            "assets_stale_or_unknown_prices": stale_or_unknown,
            "stale_assets_count": stale_or_unknown,
            "assets_without_quote_data": without_quote,
            "assets_missing_quote": without_quote,
            "assets_missing_fx_for_base_valuation": sum(1 for row in owned_rows if row.fx_status == "missing"),
            "assets_missing_fx": sum(1 for row in owned_rows if row.fx_status == "missing"),
            "assets_unresolved_for_lookup_count": sum(1 for a in all_assets if (a.provider_symbol_primary in {None, ""} and a.isin in {None, ""})),
            "totals_complete": summary.totals_complete,
            "incomplete_valuation_count": summary.missing_fx_asset_count + summary.missing_quote_asset_count,
            "missing_fx_asset_count": summary.missing_fx_asset_count,
            "missing_quote_asset_count": summary.missing_quote_asset_count,
            "base_currency": base_currency,
            "assets_with_history_count": sum(1 for asset in all_assets if self.quote_repo.has_quote_for_asset(asset.id)),
            "assets_without_history_count": sum(1 for asset in all_assets if not self.quote_repo.has_quote_for_asset(asset.id)),
            "quote_rows_count": self.quote_repo.count_rows(),
            "fx_rows_count": FXRateRepository(self.db).count_rows(),
            "assets_with_outlook_count": sum(1 for asset in all_assets if self.outlook_repo.get_latest_by_asset(asset.id) is not None),
            "assets_without_outlook_count": sum(1 for asset in all_assets if self.outlook_repo.get_latest_by_asset(asset.id) is None),
            "total_outlook_snapshots": eval_scorecard["total_outlook_snapshots"],
            "total_evaluated_outlooks": eval_scorecard["total_evaluated"],
            "global_short_term_hit_rate": eval_scorecard["accuracy"]["short"]["hit_rate"],
            "global_medium_term_hit_rate": eval_scorecard["accuracy"]["medium"]["hit_rate"],
            "global_confidence_bucket_stats": eval_scorecard["confidence"],
            "evaluated_outlook_count": scheduler_state.evaluated_outlook_count,
            "unevaluated_outlook_count": scheduler_state.unevaluated_outlook_count,
            "alerts_enabled": settings.alerts_enabled_global if settings else True,
            "total_alert_rules": self.alert_rule_repo.count(),
            "total_alert_events": self.alert_event_repo.count(),
            "unread_alert_count": self.alert_event_repo.unread_count(),
            "active_alert_count": self.alert_event_repo.active_count(),
            "latest_backup_timestamp_utc": backup_meta["timestamp_utc"],
            "latest_backup_path": backup_meta["path"],
        }
