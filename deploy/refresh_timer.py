"""
Auto-refresh timer for automatic tag refresh at configurable intervals.
"""

import threading
import time
from typing import Callable


class RefreshTimer:
    """Manages automatic refresh of tags at configurable intervals."""

    def __init__(self, interval_seconds: int, on_refresh: Callable):
        """
        Initialize RefreshTimer.

        Args:
            interval_seconds: Interval in seconds between automatic refreshes.
            on_refresh: Callback function to call when refresh timer fires.
        """
        self.interval_seconds = interval_seconds
        self.on_refresh_callback = on_refresh
        self._thread: threading.Thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Start the automatic refresh timer."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the automatic refresh timer."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    def _run(self):
        """Internal method to run the refresh loop."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval_seconds)
            if not self._stop_event.is_set():
                try:
                    self.on_refresh_callback()
                except Exception as e:
                    print(f"Error during auto-refresh: {e}")
