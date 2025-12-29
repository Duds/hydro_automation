"""Time-based scheduler for scheduled flood/drain cycles."""

import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Optional, Dict, Any

from ..core.scheduler_interface import IScheduler
from ..services.device_service import DeviceRegistry, IDeviceService


class TimeBasedScheduler(IScheduler):
    """Scheduler that executes ON/OFF cycles at specific times with variable OFF durations."""

    def __init__(
        self,
        device_registry: DeviceRegistry,
        device_id: str,
        cycles: List[Dict[str, Any]],
        flood_duration_minutes: float = 2.0,
        logger=None
    ):
        """
        Initialise the time-based scheduler.

        Args:
            device_registry: Device registry containing devices
            device_id: ID of the device to control
            cycles: List of cycle dicts with 'on_time' and 'off_duration_minutes'
            flood_duration_minutes: Duration to keep device ON in minutes (default: 2.0)
            logger: Optional logger instance
        """
        self.device_registry = device_registry
        self.device_id = device_id
        self.flood_duration_minutes = flood_duration_minutes
        self.logger = logger

        # Parse and validate cycles
        self.cycles = []
        for cycle in cycles:
            if not isinstance(cycle, dict):
                if self.logger:
                    self.logger.warning(f"Skipping invalid cycle (not a dict): {cycle}")
                continue
            on_time_str = cycle.get("on_time")
            off_duration = float(cycle.get("off_duration_minutes", 0))
            parsed_time = self._parse_time(on_time_str) if on_time_str else None
            if parsed_time is not None:
                self.cycles.append({
                    "on_time": parsed_time,
                    "off_duration_minutes": off_duration
                })

        if not self.cycles:
            raise ValueError("At least one valid cycle must be provided")

        # Sort cycles by on_time
        self.cycles.sort(key=lambda c: c["on_time"])

        self.running = False
        self.shutdown_requested = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.current_state = "idle"
        self.current_cycle_index = 0  # Track current cycle for cascading behavior
        self.use_cascading = True  # Enable cascading OFF duration behavior
        self.just_completed_cycle = False  # Flag to track if we just completed a cycle in cascading mode

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
            time_str: Time string in HH:MM format (24-hour)

        Returns:
            time object or None if parsing fails
        """
        try:
            time_str = time_str.strip()
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            return dt_time(hour, minute)
        except (ValueError, AttributeError, IndexError):
            return None

    def _get_next_cycle(self, current_time: dt_time) -> Optional[Dict[str, Any]]:
        """
        Get the next scheduled cycle from the current time.

        Args:
            current_time: Current time

        Returns:
            Next cycle dict, or first cycle tomorrow if past last scheduled time
        """
        for cycle in self.cycles:
            if cycle["on_time"] > current_time:
                return cycle
        # Past last scheduled time, return first cycle tomorrow
        return self.cycles[0] if self.cycles else None

    def _get_next_on_time(self, current_time: dt_time) -> Optional[dt_time]:
        """
        Get the next scheduled ON time from the current time.

        Args:
            current_time: Current time

        Returns:
            Next ON time, or first ON time tomorrow if past last scheduled time
        """
        cycle = self._get_next_cycle(current_time)
        return cycle["on_time"] if cycle else None

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
        device = self._get_device()
        if not device:
            if self.logger:
                self.logger.error(f"Device {self.device_id} not found in registry")
            return

        if self.logger:
            self.logger.info("Time-based scheduler started")
            self.logger.info(f"Flood duration: {self.flood_duration_minutes} minutes")
            cycle_info = ", ".join([
                f"{c['on_time'].strftime('%H:%M')}({c['off_duration_minutes']}min OFF)"
                for c in self.cycles[:5]
            ])
            if len(self.cycles) > 5:
                cycle_info += f" ... ({len(self.cycles)} total)"
            self.logger.info(f"Scheduled cycles: {cycle_info}")
            self.logger.info(f"Total cycles per day: {len(self.cycles)}")
            self.logger.info(f"Cascading behavior: {'enabled' if self.use_cascading else 'disabled'}")

        # Initialize: find the first cycle to run
        now_time = datetime.now().time()
        for i, cycle in enumerate(self.cycles):
            if cycle["on_time"] > now_time:
                self.current_cycle_index = i
                break
        else:
            # Past last cycle, start from beginning (next day)
            self.current_cycle_index = 0

        while self.running and not self.shutdown_requested:
            # Cascading behavior: get current cycle and execute it
            current_cycle = self.cycles[self.current_cycle_index]
            next_on_time = current_cycle["on_time"]
            off_duration_minutes = current_cycle.get("off_duration_minutes", 0)

            # Calculate time until this cycle's ON time
            seconds_until_next = self._time_until_next_event(next_on_time)

            if self.logger:
                off_info = f" ({off_duration_minutes}min OFF)" if off_duration_minutes is not None else ""
                if self.just_completed_cycle and self.use_cascading:
                    self.logger.info(
                        f"Next cycle: {next_on_time.strftime('%H:%M')}{off_info} "
                        "(starting immediately - cascading mode)"
                    )
                else:
                    self.logger.info(
                        f"Next cycle: {next_on_time.strftime('%H:%M')}{off_info} "
                        f"(in {seconds_until_next / 60:.1f} minutes)"
                    )

            # Wait until it's time to turn ON (only if we're waiting for scheduled time)
            # In cascading mode, if we just completed a cycle, skip the wait and proceed immediately
            if not (self.just_completed_cycle and self.use_cascading) and seconds_until_next > 0:
                wait_start = time.time()
                while time.time() - wait_start < seconds_until_next and not self.shutdown_requested:
                    time.sleep(1)

            # Reset the flag after checking it
            self.just_completed_cycle = False

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

            if device.turn_on(verify=True):
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

            device.turn_off(verify=True)

            # Wait for OFF duration (cascading: next cycle starts immediately after OFF duration)
            if off_duration_minutes is not None and off_duration_minutes > 0:
                off_duration_seconds = off_duration_minutes * 60
                if self.logger:
                    self.logger.info(
                        f"Waiting {off_duration_minutes} minutes "
                        "(cascading: next cycle starts immediately after)"
                    )

                off_start = time.time()
                while time.time() - off_start < off_duration_seconds and not self.shutdown_requested:
                    time.sleep(1)

            with self.lock:
                self.current_state = "waiting"

            if self.logger:
                self.logger.info("Cycle completed, proceeding to next cycle")

            # Cascading: move to next cycle immediately (no waiting for scheduled time)
            if self.use_cascading and self.cycles:
                self.current_cycle_index = (self.current_cycle_index + 1) % len(self.cycles)
                # Set flag so next iteration knows to skip waiting for scheduled time
                self.just_completed_cycle = True
                # After OFF duration, next cycle starts immediately (no wait)
                # The loop will continue and execute the next cycle

        if self.logger:
            self.logger.info("Time-based scheduler stopped")

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
            self.logger.info("Time-based scheduler thread started")

    def stop(self, timeout: float = 10.0) -> None:
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
        device = self._get_device()
        if device and device.is_connected():
            if self.logger:
                self.logger.info("Ensuring device is turned off before shutdown")
            device.ensure_off()

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

    def get_next_event_time(self) -> Optional[datetime]:
        """
        Get the next scheduled event time.

        Returns:
            Datetime of next event, or None if scheduler not running
        """
        if not self.running:
            return None

        now_time = datetime.now().time()
        next_time = self._get_next_on_time(now_time)
        if not next_time:
            return None

        now = datetime.now()
        target_datetime = datetime.combine(now.date(), next_time)
        if target_datetime <= now:
            target_datetime += timedelta(days=1)
        return target_datetime

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status for API.

        Returns:
            Dictionary containing scheduler status information
        """
        device = self._get_device()
        device_info = device.get_device_info() if device else None
        next_event = self.get_next_event_time()

        return {
            "scheduler_type": "time_based",
            "running": self.running,
            "state": self.get_state(),
            "device_id": self.device_id,
            "device_name": device_info.name if device_info else None,
            "device_connected": device.is_connected() if device else False,
            "device_state": device.is_device_on() if device else None,
            "flood_duration_minutes": self.flood_duration_minutes,
            "total_cycles": len(self.cycles),
            "current_cycle_index": self.current_cycle_index,
            "next_event_time": next_event.isoformat() if next_event else None,
            "cycles": [
                {
                    "on_time": c["on_time"].strftime("%H:%M"),
                    "off_duration_minutes": c["off_duration_minutes"]
                }
                for c in self.cycles
            ]
        }

