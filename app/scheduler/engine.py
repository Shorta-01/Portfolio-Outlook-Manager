import logging
from datetime import datetime

from app.services.scheduler_state import scheduler_state

logger = logging.getLogger(__name__)

_scheduler = None


def _load_scheduler_cls():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        return BackgroundScheduler
    except ModuleNotFoundError:
        return None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    scheduler_cls = _load_scheduler_cls()
    if scheduler_cls is None:
        scheduler_state.running = False
        scheduler_state.last_start_error = "APScheduler missing"
        logger.warning("Scheduler disabled: APScheduler not installed")
        return

    from app.scheduler.jobs import run_polling_cycle_from_new_session

    try:
        _scheduler = scheduler_cls(timezone="UTC")
        _scheduler.add_job(run_polling_cycle_from_new_session, "interval", minutes=1, id="market-poll-coordinator", replace_existing=True)
        _scheduler.start()
        scheduler_state.running = True
        scheduler_state.startup_utc = datetime.utcnow()
        scheduler_state.last_start_error = None
        logger.info("Scheduler started")
    except Exception as exc:
        scheduler_state.running = False
        scheduler_state.last_start_error = str(exc)[:240]
        _scheduler = None
        logger.exception("Scheduler startup failed")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    scheduler_state.running = False
    scheduler_state.shutdown_utc = datetime.utcnow()
    logger.info("Scheduler stopped")


def scheduler_running() -> bool:
    return bool(_scheduler is not None and _scheduler.running)
