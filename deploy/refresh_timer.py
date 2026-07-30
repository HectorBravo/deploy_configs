"""
Auto-refresh timer module for periodic tag refresh.
"""

import threading
import time
from typing import Callable, Optional


class RefreshTimer:
    """Periodic timer for auto-refreshing tags."""

    def __init__(self, interval_minutes: float = 5.0,
                 refresh_callback: Optional[Callable] = None):
        """
        Initialize RefreshTimer.

        Args:
            interval_minutes: Interval in minutes between refreshes.
            refresh_callback: Callback function to call on refresh.
        """
        self.interval_seconds = interval_minutes * 60
        self.refresh_callback = refresh_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_refresh = None

    def _refresh_loop(self):
        """Internal refresh loop."""
        while self._running:
            time.sleep(self.interval_seconds)
            if self._running and self.refresh_callback:
                self._last_refresh = time.time()
                self.refresh_callback()

    def start(self):
        """Start the refresh timer."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the refresh timer."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def is_running(self) -> bool:
        """Check if the timer is running."""
        return self._running

    def get_last_refresh(self) -> Optional[float]:
        """Get the timestamp of the last refresh."""
        return self._last_refresh

    def set_interval(self, minutes: float):
        """
        Set a new refresh interval.

        Args:
            minutes: New interval in minutes.
        """
        self.interval_seconds = minutes * 60
