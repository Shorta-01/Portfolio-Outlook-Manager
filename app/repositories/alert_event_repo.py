from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.alert_event import AlertEvent


class AlertEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: AlertEvent) -> AlertEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def get(self, alert_id: int) -> AlertEvent | None:
        return self.db.get(AlertEvent, alert_id)

    def latest_by_rule_asset(self, rule_id: int, asset_id: int | None) -> AlertEvent | None:
        stmt = (
            select(AlertEvent)
            .where(AlertEvent.alert_rule_id == rule_id, AlertEvent.asset_id == asset_id)
            .order_by(AlertEvent.timestamp_utc.desc(), AlertEvent.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def latest_active_by_rule_asset(self, rule_id: int, asset_id: int | None) -> AlertEvent | None:
        stmt = (
            select(AlertEvent)
            .where(AlertEvent.alert_rule_id == rule_id, AlertEvent.asset_id == asset_id, AlertEvent.is_active.is_(True))
            .order_by(AlertEvent.timestamp_utc.desc(), AlertEvent.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def list_recent(self, limit: int = 200) -> list[AlertEvent]:
        stmt = select(AlertEvent).options(joinedload(AlertEvent.asset)).order_by(AlertEvent.timestamp_utc.desc(), AlertEvent.id.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_filtered(self, *, unread_only: bool = False, severity: str = "", asset_id: int | None = None, active_only: bool = False, resolved_only: bool = False, limit: int = 300) -> list[AlertEvent]:
        stmt = select(AlertEvent).options(joinedload(AlertEvent.asset))
        if unread_only:
            stmt = stmt.where(AlertEvent.is_read.is_(False))
        if severity:
            stmt = stmt.where(AlertEvent.severity == severity)
        if asset_id is not None:
            stmt = stmt.where(AlertEvent.asset_id == asset_id)
        if active_only:
            stmt = stmt.where(AlertEvent.is_active.is_(True))
        if resolved_only:
            stmt = stmt.where(AlertEvent.is_active.is_(False))
        stmt = stmt.order_by(AlertEvent.timestamp_utc.desc(), AlertEvent.id.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def mark_read(self, alert_id: int) -> None:
        event = self.get(alert_id)
        if event:
            event.is_read = True
            self.db.flush()

    def mark_all_read(self) -> int:
        count = 0
        for event in self.list_filtered(limit=20000):
            if not event.is_read:
                event.is_read = True
                count += 1
        self.db.flush()
        return count

    def resolve(self, alert_id: int) -> None:
        event = self.get(alert_id)
        if event and event.is_active:
            event.is_active = False
            event.resolved_at_utc = datetime.utcnow()
            self.db.flush()

    def count(self) -> int:
        return len(self.db.execute(select(AlertEvent.id)).scalars().all())

    def unread_count(self) -> int:
        return len(self.db.execute(select(AlertEvent.id).where(AlertEvent.is_read.is_(False))).scalars().all())

    def active_count(self) -> int:
        return len(self.db.execute(select(AlertEvent.id).where(AlertEvent.is_active.is_(True))).scalars().all())
