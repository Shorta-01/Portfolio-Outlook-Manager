from datetime import datetime

from sqlalchemy.orm import Session

from app.forecasting import QuotePoint, run_ensemble
from app.models.action_snapshot import ActionSnapshot
from app.models.asset import AssetMode, AssetType
from app.models.outlook_snapshot import OutlookSnapshot
from app.repositories.action_snapshot_repo import ActionSnapshotRepository
from app.repositories.asset_repo import AssetRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.services.action_service import ActionService
from app.services.scheduler_state import scheduler_state


class OutlookService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.outlook_repo = OutlookSnapshotRepository(db)
        self.action_repo = ActionSnapshotRepository(db)
        self.action_service = ActionService()

    def eligible_asset(self, asset) -> bool:
        if asset.asset_mode in {AssetMode.CASH, AssetMode.TERM_DEPOSIT}:
            return False
        if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
            return False
        return True

    def run_for_asset(self, asset_id: int):
        asset = self.asset_repo.get(asset_id)
        if asset is None or not self.eligible_asset(asset):
            return None
        quotes = list(reversed(self.quote_repo.recent_for_asset(asset.id, limit=60)))
        points = [QuotePoint(timestamp_utc=q.provider_timestamp_utc, price=float(q.price)) for q in quotes]
        result = run_ensemble(points, datetime.utcnow())
        action_label, invalidation_note = self.action_service.map_action(
            action_score=result.action_score,
            key_level_up=result.key_level_up,
            key_level_down=result.key_level_down,
            medium_term_outlook=result.medium_term_outlook,
        )
        ts = datetime.utcnow()
        outlook = OutlookSnapshot(
            asset_id=asset.id,
            timestamp_utc=ts,
            short_term_outlook=result.short_term_outlook,
            medium_term_outlook=result.medium_term_outlook,
            confidence=result.confidence,
            urgency=result.urgency,
            reason_summary=result.reason_summary,
            risk_note=result.risk_note,
            short_term_score=result.short_term_score,
            medium_term_score=result.medium_term_score,
            model_version=result.model_version,
        )
        action = ActionSnapshot(
            asset_id=asset.id,
            timestamp_utc=ts,
            action_label=action_label,
            action_score=result.action_score,
            invalidation_note=invalidation_note,
            key_level_up=result.key_level_up,
            key_level_down=result.key_level_down,
            model_version=result.model_version,
        )
        self.outlook_repo.insert_snapshot(outlook)
        self.action_repo.insert_snapshot(action)
        return outlook, action

    def run_once_for_eligible_assets(self) -> dict:
        processed = 0
        skipped = 0
        for asset in self.asset_repo.list_all():
            if not self.eligible_asset(asset):
                skipped += 1
                continue
            if not self.quote_repo.has_quote_for_asset(asset.id):
                skipped += 1
                continue
            self.run_for_asset(asset.id)
            processed += 1
        self.db.commit()
        scheduler_state.last_successful_outlook_run_utc = datetime.utcnow()
        return {"ok": True, "processed": processed, "skipped": skipped}

    def latest_for_asset(self, asset_id: int):
        return self.outlook_repo.get_latest_by_asset(asset_id), self.action_repo.get_latest_by_asset(asset_id)

    def recent_history_for_asset(self, asset_id: int, limit: int = 10):
        return self.outlook_repo.get_recent_history_by_asset(asset_id, limit=limit)
