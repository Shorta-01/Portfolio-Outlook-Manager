from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule


class AlertRuleRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, rule: AlertRule) -> AlertRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def get(self, rule_id: int) -> AlertRule | None:
        return self.db.get(AlertRule, rule_id)

    def list_all(self) -> list[AlertRule]:
        return list(self.db.execute(select(AlertRule).order_by(AlertRule.id.desc())).scalars().all())

    def list_enabled(self) -> list[AlertRule]:
        stmt = select(AlertRule).where(AlertRule.enabled.is_(True)).order_by(AlertRule.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        return len(self.db.execute(select(AlertRule.id)).scalars().all())
