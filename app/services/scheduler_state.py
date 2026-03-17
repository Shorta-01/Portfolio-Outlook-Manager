from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class JobRuntimeState:
    last_success_utc: datetime | None = None
    last_failure_utc: datetime | None = None
    error_count: int = 0
    last_error_summary: str | None = None


@dataclass
class SchedulerState:
    running: bool = False
    startup_utc: datetime | None = None
    shutdown_utc: datetime | None = None
    last_start_error: str | None = None
    jobs: dict[str, JobRuntimeState] = field(
        default_factory=lambda: {
            "polling": JobRuntimeState(),
            "backfill": JobRuntimeState(),
            "outlook": JobRuntimeState(),
            "evaluation": JobRuntimeState(),
            "alerts": JobRuntimeState(),
            "cleanup": JobRuntimeState(),
            "backup": JobRuntimeState(),
        }
    )
    evaluated_outlook_count: int = 0
    unevaluated_outlook_count: int = 0
    last_cleanup_summary: dict[str, int] = field(default_factory=dict)
    last_backup_path: str | None = None

    def mark_job_success(self, job_name: str) -> None:
        job = self.jobs.setdefault(job_name, JobRuntimeState())
        job.last_success_utc = datetime.utcnow()

    def mark_job_failure(self, job_name: str, error_summary: str) -> None:
        job = self.jobs.setdefault(job_name, JobRuntimeState())
        job.last_failure_utc = datetime.utcnow()
        job.error_count += 1
        job.last_error_summary = error_summary[:240]


scheduler_state = SchedulerState()
