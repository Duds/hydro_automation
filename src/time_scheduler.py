"""Time-based scheduler for scheduled flood/drain cycles."""

import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Optional

from .tapo_controller import TapoController


class TimeScheduler:
    """Scheduler that executes ON/OFF cycles at specific times."""

    def __init__(
        self,
        controller: TapoController,
        on_times: List[str],
        flood_duration_minutes: float = 2.0,
        logger=None
    ):
        """
        Initialise the time-based scheduler.

        Args:
            controller: TapoController instance
            on_times: List of times in HH:MM format when device should turn ON (e.g., ["06:00", "06:20"])
            flood_duration_minutes: Duration to keep device ON in minutes (default: 2.0)
            logger: Optional logger instance
        """
        self.controller = controller
        self.on_times = [self._parse_time(t) for t in on_times if self._parse_time(t) is not None]
        self.flood_duration_minutes = flood_duration_minutes
        self.logger = logger

        if not self.on_times:
            raise ValueError("At least one valid ON time must be provided")

        # Sort times
        self.on_times.sort()

        self.running = False
        self.shutdown_requested = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.current_state = "idle"

    @staticmethod
    def _parse_time(time_str: str) -> Optional[dt_time]:
        """
        Parse time string in HH:MM format to time object.

        Args:
            time_str: Time string in HH:MM format (24-hour) or HH:MM am/pm

        Returns:
            time object or None if parsing fails
        """
        try:
            time_str = time_str.strip()
            # Handle 12-hour format with am/pm
            is_pm = "pm" in time_str.lower()
            is_am = "am" in time_str.lower()
            
            # Remove am/pm for parsing
            clean_time = time_str.replace("am", "").replace("AM", "").replace("pm", "").replace("PM", "").strip()
            parts = clean_time.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            
            # Convert to 24-hour format
            if is_pm and hour != 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0
            
            return dt_time(hour, minute)
        except (ValueError, AttributeError, IndexError):
            return None

    def _get_next_on_time(self, current_time: dt_time) -> Optional[dt_time]:
        """
        Get the next scheduled ON time from the current time.

        Args:
            current_time: Current time

        Returns:
            Next ON time, or first ON time tomorrow if past last scheduled time
        """
        for on_time in self.on_times:
            if on_time > current_time:
                return on_time
        
        # Past last scheduled time, return first time tomorrow
        return self.on_times[0]

    def _time_until_next_event(self, target_time: dt_time) -> float:
        """
        Calculate seconds until target time.

        Args:
            target_time: Target time

        Returns:
            Seconds until target time (can be negative if target is in the past)
        """
        now = datetime.now()
        target_datetime = datetime.combine(now.date(), target_time)
        
        # If target time has passed today, it's tomorrow
        if target_datetime <= now:
            target_datetime += timedelta(days=1)
        
        delta = target_datetime - now
        return delta.total_seconds()

    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread."""
        if self.logger:
            self.logger.info("Time-based scheduler started")
            self.logger.info(f"Flood duration: {self.flood_duration_minutes} minutes")
            self.logger.info(f"Scheduled ON times: {[t.strftime('%H:%M') for t in self.on_times]}")
            self.logger.info(f"Total cycles per day: {len(self.on_times)}")

        while self.running and not self.shutdown_requested:
            now_time = datetime.now().time()
            next_on_time = self._get_next_on_time(now_time)
            
            if next_on_time is None:
                if self.logger:
                    self.logger.error("No next ON time found, stopping scheduler")
                break

            seconds_until_next = self._time_until_next_event(next_on_time)
            
            if self.logger:
                self.logger.info(
                    f"Next ON time: {next_on_time.strftime('%H:%M')} "
                    f"(in {seconds_until_next / 60:.1f} minutes)"
                )

            # Wait until it's time to turn ON
            wait_start = time.time()
            while time.time() - wait_start < seconds_until_next and not self.shutdown_requested:
                time.sleep(1)

            if self.shutdown_requested:
                break

            # Turn ON
            with self.lock:
                self.current_state = "flood"
            
            if self.logger:
                self.logger.info("=" * 60)
                self.logger.info(
                    f"FLOOD: Turning device ON at {datetime.now().strftime('%H:%M:%S')} "
                    f"for {self.flood_duration_minutes} minutes"
                )

            if self.controller.turn_on(verify=True):
                flood_duration_seconds = self.flood_duration_minutes * 60
                flood_start = time.time()
                while time.time() - flood_start < flood_duration_seconds and not self.shutdown_requested:
                    time.sleep(1)
            else:
                if self.logger:
                    self.logger.error("Failed to turn device on for flood phase")

            if self.shutdown_requested:
                break

            # Turn OFF
            with self.lock:
                self.current_state = "drain"
            
            if self.logger:
                self.logger.info(
                    f"DRAIN: Turning device OFF at {datetime.now().strftime('%H:%M:%S')}"
                )

            self.controller.turn_off(verify=True)
            
            with self.lock:
                self.current_state = "waiting"
            
            if self.logger:
                self.logger.info("Cycle completed, waiting for next scheduled time")

        if self.logger:
            self.logger.info("Time-based scheduler stopped")

    def start(self):
        """Start the scheduler in a separate thread."""
        if self.running:
            if self.logger:
                self.logger.warning("Scheduler is already running")
            return

        self.running = True
        self.shutdown_requested = False
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.info("Time-based scheduler thread started")

    def stop(self, timeout: float = 10.0):
        """
        Stop the scheduler gracefully.

        Args:
            timeout: Maximum time to wait for scheduler to stop (seconds)
        """
        if not self.running:
            return

        if self.logger:
            self.logger.info("Stopping time-based scheduler...")

        self.shutdown_requested = True
        self.running = False

        # Ensure device is turned off
        if self.controller.is_connected():
            if self.logger:
                self.logger.info("Ensuring device is turned off before shutdown")
            self.controller.ensure_off()

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                if self.logger:
                    self.logger.warning("Scheduler thread did not stop within timeout")
            else:
                if self.logger:
                    self.logger.info("Time-based scheduler stopped successfully")

        with self.lock:
            self.current_state = "idle"

    def get_state(self) -> str:
        """
        Get current scheduler state.

        Returns:
            Current state string
        """
        with self.lock:
            return self.current_state

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running

