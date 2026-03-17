from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.action_snapshot import ActionSnapshot


class ActionSnapshotRepository:
    def __init__(self, db: Session):
        self.db = db

    def insert_snapshot(self, snapshot: ActionSnapshot) -> ActionSnapshot:
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def get_latest_by_asset(self, asset_id: int) -> ActionSnapshot | None:
        stmt = (
            select(ActionSnapshot)
            .where(ActionSnapshot.asset_id == asset_id)
            .order_by(ActionSnapshot.timestamp_utc.desc(), ActionSnapshot.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_recent_history_by_asset(self, asset_id: int, limit: int = 20) -> list[ActionSnapshot]:
        stmt = (
            select(ActionSnapshot)
            .where(ActionSnapshot.asset_id == asset_id)
            .order_by(ActionSnapshot.timestamp_utc.desc(), ActionSnapshot.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
