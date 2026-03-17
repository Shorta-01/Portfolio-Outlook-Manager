from datetime import datetime, timedelta

from app.models.polling_rule import PollingRule


def is_due(rule: PollingRule, now_utc: datetime) -> bool:
    return rule.enabled and (rule.next_due_at_utc is None or rule.next_due_at_utc <= now_utc)


def compute_next_due(rule: PollingRule, now_utc: datetime) -> datetime:
    interval = max(rule.poll_every_minutes, 1)
    return now_utc + timedelta(minutes=interval)
