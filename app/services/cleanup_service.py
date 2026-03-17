import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.action_snapshot import ActionSnapshot
from app.models.alert_event import AlertEvent
from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.models.market_quote_raw import MarketQuoteRaw
from app.models.outlook_evaluation import OutlookEvaluation
from app.models.outlook_snapshot import OutlookSnapshot
from app.services.scheduler_state import scheduler_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanupResult:
    run_at_utc: datetime
    removed: dict[str, int]


class CleanupService:
    def __init__(self, db: Session):
        self.db = db

    def run_once(self) -> CleanupResult:
        now = datetime.utcnow()
        removed = {
            "market_quotes_raw": 0,
            "market_quotes": 0,
            "fx_rates": 0,
            "outlook_evaluations": 0,
            "outlook_snapshots": 0,
            "action_snapshots": 0,
            "alert_events": 0,
        }
        try:
            removed["market_quotes_raw"] = self._delete_market_quote_raw(now - timedelta(days=settings.retention_raw_quotes_days))
            removed["market_quotes"] = self._delete_market_quotes(now - timedelta(days=settings.retention_normalized_quotes_days))
            removed["fx_rates"] = self._delete_fx_rates(now - timedelta(days=settings.retention_fx_days))
            removed["outlook_evaluations"] = self._delete_outlook_evaluations(now - timedelta(days=settings.retention_outlook_evaluations_days))
            removed["outlook_snapshots"] = self._delete_outlook_snapshots(now - timedelta(days=settings.retention_outlook_snapshots_days))
            removed["action_snapshots"] = self._delete_action_snapshots(now - timedelta(days=settings.retention_action_snapshots_days))
            removed["alert_events"] = self._delete_alert_events(now - timedelta(days=settings.retention_alert_events_days))
            self.db.commit()
            scheduler_state.mark_job_success("cleanup")
            scheduler_state.last_cleanup_summary = removed
            logger.info("Cleanup run completed removed=%s", removed)
            return CleanupResult(run_at_utc=now, removed=removed)
        except Exception as exc:
            self.db.rollback()
            scheduler_state.mark_job_failure("cleanup", str(exc))
            logger.exception("Cleanup run failed")
            raise

    def _delete_market_quote_raw(self, cutoff: datetime) -> int:
        stmt = delete(MarketQuoteRaw).where(MarketQuoteRaw.ingested_at_utc < cutoff)
        return self.db.execute(stmt).rowcount or 0

    def _delete_market_quotes(self, cutoff: datetime) -> int:
        protected = select(func.max(MarketQuote.id)).group_by(MarketQuote.asset_id)
        stmt = delete(MarketQuote).where(MarketQuote.provider_timestamp_utc < cutoff, MarketQuote.id.not_in(protected))
        return self.db.execute(stmt).rowcount or 0

    def _delete_fx_rates(self, cutoff: datetime) -> int:
        protected = select(func.max(FXRate.id)).group_by(FXRate.pair_code)
        stmt = delete(FXRate).where(FXRate.provider_timestamp_utc < cutoff, FXRate.id.not_in(protected))
        return self.db.execute(stmt).rowcount or 0

    def _delete_outlook_evaluations(self, cutoff: datetime) -> int:
        stmt = delete(OutlookEvaluation).where(OutlookEvaluation.evaluation_timestamp_utc < cutoff)
        return self.db.execute(stmt).rowcount or 0

    def _delete_outlook_snapshots(self, cutoff: datetime) -> int:
        protected = select(func.max(OutlookSnapshot.id)).group_by(OutlookSnapshot.asset_id)
        stmt = delete(OutlookSnapshot).where(OutlookSnapshot.timestamp_utc < cutoff, OutlookSnapshot.id.not_in(protected))
        return self.db.execute(stmt).rowcount or 0

    def _delete_action_snapshots(self, cutoff: datetime) -> int:
        protected = select(func.max(ActionSnapshot.id)).group_by(ActionSnapshot.asset_id)
        stmt = delete(ActionSnapshot).where(ActionSnapshot.timestamp_utc < cutoff, ActionSnapshot.id.not_in(protected))
        return self.db.execute(stmt).rowcount or 0

    def _delete_alert_events(self, cutoff: datetime) -> int:
        stmt = delete(AlertEvent).where(
            AlertEvent.timestamp_utc < cutoff,
            AlertEvent.is_read.is_(True),
            AlertEvent.is_active.is_(False),
            or_(AlertEvent.resolved_at_utc.is_(None), AlertEvent.resolved_at_utc < cutoff),
        )
        return self.db.execute(stmt).rowcount or 0
