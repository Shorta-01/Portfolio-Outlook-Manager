from threading import Lock


class RunLock:
    def __init__(self):
        self._lock = Lock()

    def acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        if self._lock.locked():
            self._lock.release()


poll_lock = RunLock()
