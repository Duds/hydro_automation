"""Thread-safe gate for timed device-on operations."""

import threading
from typing import Optional


class TimedOperationBusyError(Exception):
    """Raised when a timed operation is already running."""

    pass


class TimedOperationGate:
    """
    Gate coordinating timed pump-on operations. Ensures only one timed operation
    runs at a time and allows the scheduler to wait before starting cycles.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._off_at_utc_iso: Optional[str] = None
        self._done_event = threading.Event()
        self._done_event.set()  # Initially "done" (no op running)

    def is_running(self) -> bool:
        """Return True if a timed operation is currently running."""
        with self._lock:
            return self._running

    def get_off_at(self) -> Optional[str]:
        """Return UTC ISO 8601 timestamp when pump will turn off, or None."""
        with self._lock:
            return self._off_at_utc_iso

    def start(self, off_at_utc_iso: str) -> None:
        """Mark a timed operation as started."""
        with self._lock:
            self._running = True
            self._off_at_utc_iso = off_at_utc_iso
            self._done_event.clear()

    def finish(self) -> None:
        """Mark a timed operation as finished."""
        with self._lock:
            self._running = False
            self._off_at_utc_iso = None
            self._done_event.set()

    def wait_until_done(self, timeout: Optional[float] = None) -> bool:
        """Block until the timed operation completes. Returns True if done, False if timeout."""
        return self._done_event.wait(timeout=timeout)
