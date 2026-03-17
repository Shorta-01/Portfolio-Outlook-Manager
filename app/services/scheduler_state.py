from dataclasses import dataclass
from datetime import datetime


@dataclass
class SchedulerState:
    running: bool = False
    last_successful_poll_utc: datetime | None = None
    last_successful_backfill_utc: datetime | None = None


scheduler_state = SchedulerState()
