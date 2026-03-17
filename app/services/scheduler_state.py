from dataclasses import dataclass
from datetime import datetime


@dataclass
class SchedulerState:
    running: bool = False
    last_successful_poll_utc: datetime | None = None
    last_successful_backfill_utc: datetime | None = None
    last_successful_outlook_run_utc: datetime | None = None
    last_successful_outlook_evaluation_run_utc: datetime | None = None
    evaluated_outlook_count: int = 0
    unevaluated_outlook_count: int = 0


scheduler_state = SchedulerState()
