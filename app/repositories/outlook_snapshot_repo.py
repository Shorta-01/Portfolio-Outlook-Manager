from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outlook_snapshot import OutlookSnapshot


class OutlookSnapshotRepository:
    def __init__(self, db: Session):
        self.db = db

    def insert_snapshot(self, snapshot: OutlookSnapshot) -> OutlookSnapshot:
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def get_latest_by_asset(self, asset_id: int) -> OutlookSnapshot | None:
        stmt = (
            select(OutlookSnapshot)
            .where(OutlookSnapshot.asset_id == asset_id)
            .order_by(OutlookSnapshot.timestamp_utc.desc(), OutlookSnapshot.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_recent_history_by_asset(self, asset_id: int, limit: int = 20) -> list[OutlookSnapshot]:
        stmt = (
            select(OutlookSnapshot)
            .where(OutlookSnapshot.asset_id == asset_id)
            .order_by(OutlookSnapshot.timestamp_utc.desc(), OutlookSnapshot.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
