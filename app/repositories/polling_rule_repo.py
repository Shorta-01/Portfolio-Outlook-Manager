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
