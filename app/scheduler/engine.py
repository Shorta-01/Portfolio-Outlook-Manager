from app.services.scheduler_state import scheduler_state

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
        return

    from app.scheduler.jobs import run_polling_cycle_from_new_session

    _scheduler = scheduler_cls(timezone="UTC")
    _scheduler.add_job(run_polling_cycle_from_new_session, "interval", minutes=1, id="market-poll-coordinator", replace_existing=True)
    _scheduler.start()
    scheduler_state.running = True


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    scheduler_state.running = False


def scheduler_running() -> bool:
    return bool(_scheduler is not None and _scheduler.running)
