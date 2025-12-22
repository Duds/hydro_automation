"""Time-based scheduler for scheduled flood/drain cycles."""

import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Optional, Dict, Any

from .tapo_controller import TapoController


class TimeScheduler:
    """Scheduler that executes ON/OFF cycles at specific times with variable OFF durations."""

    def __init__(
        self,
        controller: TapoController,
        on_times: Optional[List[str]] = None,
        cycles: Optional[List[Dict[str, Any]]] = None,
        flood_duration_minutes: float = 2.0,
        logger=None
    ):
        """
        Initialise the time-based scheduler.

        Args:
            controller: TapoController instance
            on_times: List of times in HH:MM format when device should turn ON (backward compatibility)
            cycles: List of cycle dicts with 'on_time' and 'off_duration_minutes' (new format)
            flood_duration_minutes: Duration to keep device ON in minutes (default: 2.0)
            logger: Optional logger instance
        """
        self.controller = controller
        self.flood_duration_minutes = flood_duration_minutes
        self.logger = logger

        # Support new cycles format or backward-compatible on_times
        if cycles:
            # New format: cycles with variable OFF durations
            self.cycles = []
            for cycle in cycles:
                # Ensure cycle is a dict, not a list
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
            self.on_times = [c["on_time"] for c in self.cycles]
            self.use_cycles = True
        elif on_times:
            # Backward compatibility: simple on_times list
            self.on_times = [self._parse_time(t) for t in on_times if self._parse_time(t) is not None]
            if not self.on_times:
                raise ValueError("At least one valid ON time must be provided")
            self.on_times.sort()
            self.cycles = None
            self.use_cycles = False
        else:
            raise ValueError("Either 'on_times' or 'cycles' must be provided")

        self.running = False
        self.shutdown_requested = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.current_state = "idle"
        self.current_cycle_index = 0  # Track current cycle for cascading behavior
        self.use_cascading = True  # Enable cascading OFF duration behavior

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

    def _get_next_cycle(self, current_time: dt_time) -> Optional[Dict[str, Any]]:
        """
        Get the next scheduled cycle from the current time.

        Args:
            current_time: Current time

        Returns:
            Next cycle dict, or first cycle tomorrow if past last scheduled time
        """
        if self.use_cycles:
            for cycle in self.cycles:
                if cycle["on_time"] > current_time:
                    return cycle
            # Past last scheduled time, return first cycle tomorrow
            return self.cycles[0] if self.cycles else None
        else:
            # Backward compatibility
            for on_time in self.on_times:
                if on_time > current_time:
                    return {"on_time": on_time, "off_duration_minutes": None}
            return {"on_time": self.on_times[0], "off_duration_minutes": None} if self.on_times else None

    def _get_next_on_time(self, current_time: dt_time) -> Optional[dt_time]:
        """
        Get the next scheduled ON time from the current time (backward compatibility).

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
        if self.logger:
            self.logger.info("Time-based scheduler started")
            self.logger.info(f"Flood duration: {self.flood_duration_minutes} minutes")
            if self.use_cycles:
                cycle_info = ", ".join([
                    f"{c['on_time'].strftime('%H:%M')}({c['off_duration_minutes']}min OFF)"
                    for c in self.cycles[:5]
                ])
                if len(self.cycles) > 5:
                    cycle_info += f" ... ({len(self.cycles)} total)"
                self.logger.info(f"Scheduled cycles: {cycle_info}")
            else:
                self.logger.info(f"Scheduled ON times: {[t.strftime('%H:%M') for t in self.on_times]}")
            self.logger.info(f"Total cycles per day: {len(self.on_times)}")
            self.logger.info(f"Cascading behavior: {'enabled' if self.use_cascading else 'disabled'}")

        # Initialize: find the first cycle to run
        if self.use_cycles and self.cycles:
            now_time = datetime.now().time()
            # Find the next cycle from current time
            for i, cycle in enumerate(self.cycles):
                if cycle["on_time"] > now_time:
                    self.current_cycle_index = i
                    break
            else:
                # Past last cycle, start from beginning (next day)
                self.current_cycle_index = 0
        else:
            self.current_cycle_index = 0

        while self.running and not self.shutdown_requested:
            if self.use_cycles and self.cycles:
                # Cascading behavior: get current cycle and execute it
                current_cycle = self.cycles[self.current_cycle_index]
                next_on_time = current_cycle["on_time"]
                off_duration_minutes = current_cycle.get("off_duration_minutes", 0)
                
                # Calculate time until this cycle's ON time
                seconds_until_next = self._time_until_next_event(next_on_time)
                
                if self.logger:
                    off_info = f" ({off_duration_minutes}min OFF)" if off_duration_minutes is not None else ""
                    self.logger.info(
                        f"Next cycle: {next_on_time.strftime('%H:%M')}{off_info} "
                        f"(in {seconds_until_next / 60:.1f} minutes)"
                    )

                # Wait until it's time to turn ON (only if we're waiting for scheduled time)
                if seconds_until_next > 0:
                    wait_start = time.time()
                    while time.time() - wait_start < seconds_until_next and not self.shutdown_requested:
                        time.sleep(1)

                if self.shutdown_requested:
                    break
            else:
                # Backward compatibility: original behavior
                now_time = datetime.now().time()
                next_cycle = self._get_next_cycle(now_time)
                
                if next_cycle is None:
                    if self.logger:
                        self.logger.error("No next cycle found, stopping scheduler")
                    break

                next_on_time = next_cycle["on_time"]
                off_duration_minutes = next_cycle.get("off_duration_minutes")

                seconds_until_next = self._time_until_next_event(next_on_time)
                
                if self.logger:
                    off_info = f" ({off_duration_minutes}min OFF)" if off_duration_minutes is not None else ""
                    self.logger.info(
                        f"Next ON time: {next_on_time.strftime('%H:%M')}{off_info} "
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
            
            # Wait for OFF duration (cascading: next cycle starts immediately after OFF duration)
            if off_duration_minutes is not None and off_duration_minutes > 0:
                off_duration_seconds = off_duration_minutes * 60
                if self.logger:
                    self.logger.info(f"Waiting {off_duration_minutes} minutes (cascading: next cycle starts immediately after)")
                
                off_start = time.time()
                while time.time() - off_start < off_duration_seconds and not self.shutdown_requested:
                    time.sleep(1)
            
            with self.lock:
                self.current_state = "waiting"
            
            if self.logger:
                self.logger.info("Cycle completed, proceeding to next cycle")
            
            # Cascading: move to next cycle immediately (no waiting for scheduled time)
            if self.use_cascading and self.use_cycles and self.cycles:
                self.current_cycle_index = (self.current_cycle_index + 1) % len(self.cycles)
                # After OFF duration, next cycle starts immediately (no wait)
                # The loop will continue and execute the next cycle

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

    def update_cycles(self, new_cycles: List[Dict[str, Any]]):
        """
        Update cycles dynamically while scheduler is running.
        
        Args:
            new_cycles: List of cycle dicts with 'on_time' and 'off_duration_minutes'
        """
        with self.lock:
            # Parse and validate new cycles
            updated_cycles = []
            for cycle in new_cycles:
                on_time_str = cycle.get("on_time")
                off_duration = float(cycle.get("off_duration_minutes", 0))
                parsed_time = self._parse_time(on_time_str) if on_time_str else None
                if parsed_time is not None:
                    updated_cycles.append({
                        "on_time": parsed_time,
                        "off_duration_minutes": off_duration
                    })
            
            if not updated_cycles:
                if self.logger:
                    self.logger.warning("No valid cycles in update, keeping existing cycles")
                return
            
            # Sort cycles by on_time
            updated_cycles.sort(key=lambda c: c["on_time"])
            
            # Update cycles
            self.cycles = updated_cycles
            self.on_times = [c["on_time"] for c in self.cycles]
            self.use_cycles = True
            
            # Reset current cycle index to find the next appropriate cycle
            now_time = datetime.now().time()
            self.current_cycle_index = 0
            for i, cycle in enumerate(self.cycles):
                if cycle["on_time"] > now_time:
                    self.current_cycle_index = i
                    break
            
            if self.logger:
                self.logger.info(
                    f"Updated schedule with {len(updated_cycles)} cycles. "
                    f"Next cycle: {self.cycles[self.current_cycle_index]['on_time'].strftime('%H:%M')}"
                )

