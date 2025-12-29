"""Unified scheduler interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any


class IScheduler(ABC):
    """Unified interface for all scheduler implementations."""

    @abstractmethod
    def start(self) -> None:
        """Start the scheduler."""
        pass

    @abstractmethod
    def stop(self, timeout: float = 10.0) -> None:
        """Stop the scheduler gracefully.

        Args:
            timeout: Maximum time to wait for scheduler to stop (seconds)
        """
        pass

    @abstractmethod
    def get_state(self) -> str:
        """Get current scheduler state.

        Returns:
            Current state string (e.g., 'idle', 'flood', 'drain', 'waiting')
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if scheduler is running, False otherwise
        """
        pass

    @abstractmethod
    def get_next_event_time(self) -> Optional[datetime]:
        """Get the next scheduled event time.

        Returns:
            Datetime of next event, or None if no events scheduled
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status for API.

        Returns:
            Dictionary containing scheduler status information
        """
        pass

