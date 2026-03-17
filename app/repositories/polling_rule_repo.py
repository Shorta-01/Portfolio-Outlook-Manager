from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.polling_rule import PollingRule


class PollingRuleRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, rule: PollingRule) -> PollingRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def list_all(self) -> list[PollingRule]:
        return list(self.db.execute(select(PollingRule)).scalars().all())

    def count(self) -> int:
        return len(self.list_all())

    def list_due(self, now_utc: datetime) -> list[PollingRule]:
        stmt = select(PollingRule).where(
            PollingRule.enabled.is_(True),
            (PollingRule.next_due_at_utc.is_(None)) | (PollingRule.next_due_at_utc <= now_utc),
        )
        return list(self.db.execute(stmt).scalars().all())
