"""Interval-based scheduler for flood and drain cycles."""

import threading
import time
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any

from ..core.scheduler_interface import IScheduler
from ..services.device_service import DeviceRegistry, IDeviceService


# State constants (replacing CycleState enum)
STATE_IDLE = "idle"
STATE_FLOOD = "flood"
STATE_DRAIN = "drain"
STATE_WAITING = "waiting"


class IntervalScheduler(IScheduler):
    """Scheduler for managing flood and drain cycles with fixed intervals."""

    def __init__(
        self,
        device_registry: DeviceRegistry,
        device_id: str,
        flood_duration_minutes: float,
        drain_duration_minutes: float,
        interval_minutes: float,
        schedule_enabled: bool = True,
        active_hours_start: Optional[str] = None,
        active_hours_end: Optional[str] = None,
        logger=None
    ):
        """
        Initialise the interval scheduler.

        Args:
            device_registry: Device registry containing devices
            device_id: ID of the device to control
            flood_duration_minutes: Duration of flood cycle in minutes
            drain_duration_minutes: Duration of drain cycle in minutes
            interval_minutes: Interval between cycles in minutes
            schedule_enabled: Whether to respect active hours
            active_hours_start: Start time in HH:MM format (e.g., "06:00")
            active_hours_end: End time in HH:MM format (e.g., "22:00")
            logger: Optional logger instance
        """
        self.device_registry = device_registry
        self.device_id = device_id
        self.flood_duration_minutes = flood_duration_minutes
        self.drain_duration_minutes = drain_duration_minutes
        self.interval_minutes = interval_minutes
        self.schedule_enabled = schedule_enabled
        self.active_hours_start = self._parse_time(active_hours_start) if active_hours_start else None
        self.active_hours_end = self._parse_time(active_hours_end) if active_hours_end else None
        self.logger = logger

        self.state = STATE_IDLE
        self.running = False
        self.shutdown_requested = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def _get_device(self) -> Optional[IDeviceService]:
        """Get the device service instance.

        Returns:
            Device service or None if not found
        """
        return self.device_registry.get_device(self.device_id)

    @staticmethod
    def _parse_time(time_str: str) -> Optional[dt_time]:
        """
        Parse time string in HH:MM format to time object.

        Args:
            time_str: Time string in HH:MM format

        Returns:
            time object or None if parsing fails
        """
        try:
            hour, minute = map(int, time_str.split(":"))
            return dt_time(hour, minute)
        except (ValueError, AttributeError):
            return None

    def _is_within_active_hours(self) -> bool:
        """
        Check if current time is within active hours.

        Returns:
            True if within active hours or scheduling disabled, False otherwise
        """
        if not self.schedule_enabled:
            return True

        if not self.active_hours_start or not self.active_hours_end:
            return True

        now = datetime.now().time()

        # Handle case where active hours span midnight
        if self.active_hours_start <= self.active_hours_end:
            return self.active_hours_start <= now <= self.active_hours_end
        else:
            return now >= self.active_hours_start or now <= self.active_hours_end

    def _run_cycle(self):
        """Execute a single flood and drain cycle."""
        device = self._get_device()
        if not device:
            if self.logger:
                self.logger.error(f"Device {self.device_id} not found in registry")
            return

        if self.logger:
            self.logger.info("=" * 60)
            self.logger.info("Starting new flood/drain cycle")

        # Flood phase
        with self.lock:
            self.state = STATE_FLOOD
        if self.logger:
            self.logger.info(f"FLOOD phase: Turning device ON for {self.flood_duration_minutes} minutes")

        if device.turn_on(verify=True):
            flood_duration_seconds = self.flood_duration_minutes * 60
            start_time = time.time()
            while time.time() - start_time < flood_duration_seconds and not self.shutdown_requested:
                time.sleep(1)
        else:
            if self.logger:
                self.logger.error("Failed to turn device on for flood phase")

        # Drain phase
        with self.lock:
            self.state = STATE_DRAIN
        if self.logger:
            self.logger.info(f"DRAIN phase: Turning device OFF for {self.drain_duration_minutes} minutes")

        if device.turn_off(verify=True):
            drain_duration_seconds = self.drain_duration_minutes * 60
            start_time = time.time()
            while time.time() - start_time < drain_duration_seconds and not self.shutdown_requested:
                time.sleep(1)
        else:
            if self.logger:
                self.logger.error("Failed to turn device off for drain phase")

        with self.lock:
            self.state = STATE_WAITING
        if self.logger:
            self.logger.info("Cycle completed, entering wait phase")

    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread."""
        if self.logger:
            self.logger.info("Interval scheduler started")
            self.logger.info(
                f"Cycle configuration: Flood={self.flood_duration_minutes}min, "
                f"Drain={self.drain_duration_minutes}min, Interval={self.interval_minutes}min"
            )
            if self.schedule_enabled and self.active_hours_start and self.active_hours_end:
                self.logger.info(
                    f"Active hours: {self.active_hours_start.strftime('%H:%M')} - "
                    f"{self.active_hours_end.strftime('%H:%M')}"
                )

        cycle_count = 0

        while self.running and not self.shutdown_requested:
            # Check if within active hours
            if not self._is_within_active_hours():
                if self.logger:
                    self.logger.debug("Outside active hours, waiting...")
                time.sleep(60)  # Check every minute
                continue

            # Execute cycle
            cycle_count += 1
            if self.logger:
                self.logger.info(f"Executing cycle #{cycle_count}")

            self._run_cycle()

            if self.shutdown_requested:
                break

            # Wait for next cycle interval
            if self.logger:
                self.logger.info(f"Waiting {self.interval_minutes} minutes until next cycle")
            interval_seconds = self.interval_minutes * 60
            start_time = time.time()
            while time.time() - start_time < interval_seconds and not self.shutdown_requested:
                time.sleep(1)

        if self.logger:
            self.logger.info("Interval scheduler stopped")

    def start(self) -> None:
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
            self.logger.info("Interval scheduler thread started")

    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop the scheduler gracefully.

        Args:
            timeout: Maximum time to wait for scheduler to stop (seconds)
        """
        if not self.running:
            return

        if self.logger:
            self.logger.info("Stopping interval scheduler...")

        self.shutdown_requested = True
        self.running = False

        # Ensure device is turned off
        device = self._get_device()
        if device and device.is_connected():
            if self.logger:
                self.logger.info("Ensuring device is turned off before shutdown")
            device.ensure_off()
            device.close()

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                if self.logger:
                    self.logger.warning("Scheduler thread did not stop within timeout")
            else:
                if self.logger:
                    self.logger.info("Interval scheduler stopped successfully")

        with self.lock:
            self.state = STATE_IDLE

    def get_state(self) -> str:
        """
        Get current cycle state.

        Returns:
            Current state string
        """
        with self.lock:
            return self.state

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running

    def get_next_event_time(self) -> Optional[datetime]:
        """
        Get the next scheduled event time.

        For interval scheduler, this is the next cycle start time.

        Returns:
            Datetime of next event, or None if scheduler not running
        """
        if not self.running:
            return None

        # For interval scheduler, next event is after current interval
        # This is a simplified calculation - actual next time depends on current state
        # For now, return None as it's complex to calculate accurately
        # TODO: Implement proper next event calculation based on current state
        return None

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status for API.

        Returns:
            Dictionary containing scheduler status information
        """
        device = self._get_device()
        device_info = device.get_device_info() if device else None

        return {
            "scheduler_type": "interval",
            "running": self.running,
            "state": self.get_state(),
            "device_id": self.device_id,
            "device_name": device_info.name if device_info else None,
            "device_connected": device.is_connected() if device else False,
            "device_state": device.is_device_on() if device else None,
            "flood_duration_minutes": self.flood_duration_minutes,
            "drain_duration_minutes": self.drain_duration_minutes,
            "interval_minutes": self.interval_minutes,
            "schedule_enabled": self.schedule_enabled,
            "active_hours_start": self.active_hours_start.strftime("%H:%M") if self.active_hours_start else None,
            "active_hours_end": self.active_hours_end.strftime("%H:%M") if self.active_hours_end else None,
            "next_event_time": self.get_next_event_time().isoformat() if self.get_next_event_time() else None
        }

