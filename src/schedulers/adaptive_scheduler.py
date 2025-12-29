"""Adaptive scheduler that generates schedules independently from environmental factors."""

import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Any, Optional, Tuple

from ..core.scheduler_interface import IScheduler
from ..services.device_service import DeviceRegistry, IDeviceService
from ..services.environmental_service import EnvironmentalService
from ..schedulers.time_based_scheduler import TimeBasedScheduler


class AdaptiveScheduler(IScheduler):
    """
    Adaptive scheduler that generates flood schedules independently from factors.
    
    This scheduler generates schedules from scratch using:
    - Time of Day (ToD) requirements
    - Temperature at time of day
    - Temperature trends
    - Humidity at time of day
    - Day length/seasonal adjustments
    """

    def __init__(
        self,
        device_registry: DeviceRegistry,
        device_id: str,
        flood_duration_minutes: float,
        adaptation_config: Dict[str, Any],
        env_service: EnvironmentalService,
        logger=None
    ):
        """
        Initialize adaptive scheduler.

        Args:
            device_registry: Device registry containing devices
            device_id: ID of the device to control
            flood_duration_minutes: Flood duration in minutes
            adaptation_config: Adaptation configuration dict
            env_service: Environmental service instance
            logger: Optional logger instance
        """
        self.device_registry = device_registry
        self.device_id = device_id
        self.flood_duration_minutes = flood_duration_minutes
        self.adaptation_config = adaptation_config
        self.env_service = env_service
        self.logger = logger
        self.enabled = adaptation_config.get("enabled", False)

        # Get adaptive config (previously "active_adaptive")
        adaptive_config = adaptation_config.get("adaptive", {})
        self.tod_frequencies = adaptive_config.get("tod_frequencies", {
            "morning": 18.0,
            "day": 28.0,
            "evening": 18.0,
            "night": 118.0
        })
        self.temperature_bands = adaptive_config.get("temperature_bands", {
            "cold": {"max": 15, "factor": 1.15},
            "normal": {"min": 15, "max": 25, "factor": 1.0},
            "warm": {"min": 25, "max": 30, "factor": 0.85},
            "hot": {"min": 30, "factor": 0.70}
        })
        self.humidity_bands = adaptive_config.get("humidity_bands", {
            "low": {"max": 40, "factor": 0.9},
            "normal": {"min": 40, "max": 70, "factor": 1.0},
            "high": {"min": 70, "factor": 1.1}
        })
        self.constraints = adaptive_config.get("constraints", {
            "min_wait_duration": 5,
            "max_wait_duration": 180,
            "min_flood_duration": 2,
            "max_flood_duration": 15
        })

        # Generate initial schedule
        self.adapted_cycles: List[Dict[str, Any]] = []
        if self.enabled:
            self._generate_schedule()

        # Create internal TimeBasedScheduler with generated cycles
        formatted_cycles = []
        for cycle in self.adapted_cycles:
            on_time = cycle.get("on_time")
            if isinstance(on_time, str):
                formatted_cycles.append({
                    "on_time": on_time,
                    "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                })
            else:
                formatted_cycles.append({
                    "on_time": on_time.strftime("%H:%M") if hasattr(on_time, 'strftime') else str(on_time),
                    "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                })

        # If no cycles, create a dummy cycle to prevent initialization error
        if not formatted_cycles:
            formatted_cycles = [{"on_time": "00:00", "off_duration_minutes": 60}]

        self.base_scheduler = TimeBasedScheduler(
            device_registry=device_registry,
            device_id=device_id,
            cycles=formatted_cycles,
            flood_duration_minutes=flood_duration_minutes,
            logger=logger
        )

        # Threading
        self.running = False
        self.shutdown_requested = False
        self.update_thread: Optional[threading.Thread] = None

    def _get_device(self) -> Optional[IDeviceService]:
        """Get the device service instance."""
        return self.device_registry.get_device(self.device_id)

    def _get_time_period(self, cycle_time: dt_time, sunrise: Optional[dt_time] = None, sunset: Optional[dt_time] = None) -> str:
        """
        Determine which time period a cycle belongs to.

        Args:
            cycle_time: Time of the cycle
            sunrise: Sunrise time (optional)
            sunset: Sunset time (optional)

        Returns:
            Period name: "morning", "day", "evening", or "night"
        """
        hour = cycle_time.hour
        minute = cycle_time.minute
        cycle_minutes = hour * 60 + minute

        # Define period boundaries (in minutes from midnight)
        morning_start = 6 * 60  # 06:00
        day_start = 9 * 60  # 09:00
        evening_start = 18 * 60  # 18:00
        night_start = 20 * 60  # 20:00

        # Adjust boundaries if sunrise/sunset are provided
        if sunrise:
            sunrise_minutes = sunrise.hour * 60 + sunrise.minute
            if 5 * 60 <= sunrise_minutes <= 7 * 60:
                morning_start = sunrise_minutes

        if sunset:
            sunset_minutes = sunset.hour * 60 + sunset.minute
            if 17 * 60 <= sunset_minutes <= 19 * 60:
                evening_start = sunset_minutes

        # Determine period
        if cycle_minutes >= night_start or cycle_minutes < morning_start:
            return "night"
        elif morning_start <= cycle_minutes < day_start:
            return "morning"
        elif day_start <= cycle_minutes < evening_start:
            return "day"
        else:  # evening_start <= cycle_minutes < night_start
            return "evening"

    def calculate_tod_base_frequency(self, period: str) -> float:
        """
        Calculate base wait duration from Time of Day requirements.

        Args:
            period: Time period ("morning", "day", "evening", "night")

        Returns:
            Base wait duration in minutes
        """
        return self.tod_frequencies.get(period, 28.0)

    def get_temperature_factor(self, temperature: Optional[float]) -> float:
        """
        Calculate temperature adjustment factor.

        Args:
            temperature: Temperature in Celsius

        Returns:
            Adjustment factor
        """
        if temperature is None:
            return 1.0

        # Find matching temperature band
        for band_name, band_config in self.temperature_bands.items():
            min_temp = band_config.get("min")
            max_temp = band_config.get("max")
            factor = band_config.get("factor", 1.0)

            if min_temp is not None and max_temp is not None:
                if min_temp <= temperature < max_temp:
                    return factor
            elif min_temp is not None:
                if temperature >= min_temp:
                    return factor
            elif max_temp is not None:
                if temperature < max_temp:
                    return factor

        return 1.0

    def get_humidity_factor(self, humidity: Optional[float]) -> float:
        """
        Calculate humidity adjustment factor.

        Args:
            humidity: Humidity as percentage (0-100)

        Returns:
            Adjustment factor
        """
        if humidity is None:
            return 1.0

        # Find matching humidity band
        for band_name, band_config in self.humidity_bands.items():
            min_humidity = band_config.get("min")
            max_humidity = band_config.get("max")
            factor = band_config.get("factor", 1.0)

            if min_humidity is not None and max_humidity is not None:
                if min_humidity <= humidity < max_humidity:
                    return factor
            elif min_humidity is not None:
                if humidity >= min_humidity:
                    return factor
            elif max_humidity is not None:
                if humidity < max_humidity:
                    return factor

        return 1.0

    def _generate_schedule(self):
        """Generate adaptive schedule for the full day."""
        if not self.enabled:
            self.adapted_cycles = []
            return

        # Get sunrise/sunset from environmental service
        sunrise = None
        sunset = None
        if self.env_service and self.env_service.daylight_calc:
            sunrise, sunset = self.env_service.daylight_calc.get_sunrise_sunset()

        # Generate events for each period
        all_events = []
        last_event_next_time = None

        # Morning period (sunrise or 06:00 to 09:00)
        morning_start = sunrise if sunrise and 5 * 60 <= (sunrise.hour * 60 + sunrise.minute) <= 7 * 60 else dt_time(6, 0)
        morning_end = dt_time(9, 0)
        morning_events = self._generate_period_events("morning", morning_start, morning_end, sunrise, sunset, last_event_next_time)
        all_events.extend(morning_events)
        if morning_events:
            last_morning = morning_events[-1]
            last_morning_time = self._time_to_minutes(last_morning["on_time"])
            last_morning_wait = last_morning["off_duration_minutes"]
            next_time_minutes = last_morning_time + last_morning_wait + self.flood_duration_minutes
            next_time_hour = int((next_time_minutes % (24 * 60)) // 60)
            next_time_minute = int((next_time_minutes % (24 * 60)) % 60)
            last_event_next_time = dt_time(next_time_hour, next_time_minute)

        # Day period (09:00 to sunset or 18:00)
        day_start = dt_time(9, 0)
        day_end = sunset if sunset and 17 * 60 <= (sunset.hour * 60 + sunset.minute) <= 19 * 60 else dt_time(18, 0)
        day_actual_start = day_start
        if last_event_next_time:
            day_start_minutes = day_start.hour * 60 + day_start.minute
            last_next_minutes = last_event_next_time.hour * 60 + last_event_next_time.minute
            diff = abs(last_next_minutes - day_start_minutes)
            if diff <= 10 or (last_next_minutes > day_start_minutes and last_next_minutes < day_end.hour * 60 + day_end.minute):
                day_actual_start = last_event_next_time
        day_events = self._generate_period_events("day", day_start, day_end, sunrise, sunset, day_actual_start if day_actual_start != day_start else None)
        all_events.extend(day_events)
        if day_events:
            last_day = day_events[-1]
            last_day_time = self._time_to_minutes(last_day["on_time"])
            last_day_wait = last_day["off_duration_minutes"]
            next_time_minutes = last_day_time + last_day_wait + self.flood_duration_minutes
            next_time_hour = int((next_time_minutes % (24 * 60)) // 60)
            next_time_minute = int((next_time_minutes % (24 * 60)) % 60)
            last_event_next_time = dt_time(next_time_hour, next_time_minute)

        # Evening period (sunset or 18:00 to 20:00)
        evening_start = sunset if sunset and 17 * 60 <= (sunset.hour * 60 + sunset.minute) <= 19 * 60 else dt_time(18, 0)
        evening_end = dt_time(20, 0)
        evening_actual_start = evening_start
        if last_event_next_time:
            evening_start_minutes = evening_start.hour * 60 + evening_start.minute
            last_next_minutes = last_event_next_time.hour * 60 + last_event_next_time.minute
            if last_next_minutes < 12 * 60:
                last_next_minutes += 24 * 60
            diff = abs(last_next_minutes - evening_start_minutes)
            if diff <= 10 or (last_next_minutes > evening_start_minutes and last_next_minutes < evening_end.hour * 60 + evening_end.minute):
                evening_actual_start = last_event_next_time
        evening_events = self._generate_period_events("evening", evening_start, evening_end, sunrise, sunset, evening_actual_start if evening_actual_start != evening_start else None)
        all_events.extend(evening_events)
        if evening_events:
            last_evening = evening_events[-1]
            last_evening_time = self._time_to_minutes(last_evening["on_time"])
            last_evening_wait = last_evening["off_duration_minutes"]
            next_time_minutes = last_evening_time + last_evening_wait + self.flood_duration_minutes
            next_time_hour = int((next_time_minutes % (24 * 60)) // 60)
            next_time_minute = int((next_time_minutes % (24 * 60)) % 60)
            last_event_next_time = dt_time(next_time_hour, next_time_minute)

        # Night period (20:00 to sunrise or 06:00 next day)
        night_start = dt_time(20, 0)
        night_end = sunrise if sunrise and 5 * 60 <= (sunrise.hour * 60 + sunrise.minute) <= 7 * 60 else dt_time(6, 0)
        night_actual_start = night_start
        if last_event_next_time:
            night_start_minutes = night_start.hour * 60 + night_start.minute
            last_next_minutes = last_event_next_time.hour * 60 + last_event_next_time.minute
            diff = abs(last_next_minutes - night_start_minutes)
            if diff <= 10 or (last_next_minutes > night_start_minutes):
                night_actual_start = last_event_next_time
        night_events = self._generate_period_events("night", night_start, night_end, sunrise, sunset, night_actual_start if night_actual_start != night_start else None)
        all_events.extend(night_events)

        # Sort by time
        all_events.sort(key=lambda e: self._time_to_minutes(e["on_time"]))

        # Apply system constraints
        self.adapted_cycles = self._apply_constraints(all_events)

        if self.logger:
            self.logger.info(f"Generated adaptive schedule with {len(self.adapted_cycles)} events")

    def _generate_period_events(self, period: str, start_time: dt_time, end_time: dt_time,
                                sunrise: Optional[dt_time], sunset: Optional[dt_time],
                                start_from_time: Optional[dt_time] = None) -> List[Dict[str, Any]]:
        """Generate events for a specific time period."""
        events = []

        base_wait = self.calculate_tod_base_frequency(period)
        actual_start_time = start_from_time if start_from_time else start_time

        start_minutes = actual_start_time.hour * 60 + actual_start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute

        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        period_duration = end_minutes - start_minutes
        current_minutes = start_minutes
        event_time = actual_start_time

        while current_minutes < end_minutes:
            # Get environmental conditions
            temp = None
            humidity = None
            if self.env_service and self.env_service.temperature_service:
                temp_service = self.env_service.temperature_service
                temp = temp_service.get_temperature_at_time(event_time) if hasattr(temp_service, 'get_temperature_at_time') else temp_service.last_temperature
                humidity = temp_service.get_humidity_at_time(event_time) if hasattr(temp_service, 'get_humidity_at_time') else temp_service.last_humidity

            # Calculate adjustment factors
            temp_factor = self.get_temperature_factor(temp)
            humidity_factor = self.get_humidity_factor(humidity)

            # Calculate adjusted wait duration
            adjusted_wait = base_wait * temp_factor * humidity_factor

            # Create event
            event = {
                "on_time": event_time.strftime("%H:%M"),
                "off_duration_minutes": adjusted_wait,
                "_period": period,
                "_temp": temp,
                "_humidity": humidity,
                "_temp_factor": temp_factor,
                "_humidity_factor": humidity_factor
            }
            events.append(event)

            # Move to next event time
            current_minutes += adjusted_wait + self.flood_duration_minutes
            event_hour = int((current_minutes % (24 * 60)) // 60)
            event_minute = int((current_minutes % (24 * 60)) % 60)
            event_time = dt_time(event_hour, event_minute)

        return events

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string to minutes from midnight."""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _apply_constraints(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply system constraints to events."""
        min_wait = self.constraints.get("min_wait_duration", 5)
        max_wait = self.constraints.get("max_wait_duration", 180)

        constrained_events = []
        for event in events:
            constrained_event = event.copy()
            wait = event.get("off_duration_minutes", 0)
            constrained_wait = max(min_wait, min(max_wait, wait))
            constrained_event["off_duration_minutes"] = constrained_wait
            constrained_events.append(constrained_event)

        return constrained_events

    def _update_schedule(self):
        """Update the adaptive schedule based on current conditions."""
        if not self.enabled:
            return

        old_count = len(self.adapted_cycles)
        self._generate_schedule()
        new_count = len(self.adapted_cycles)

        # TODO: Implement cycle update for running scheduler
        # For now, we regenerate the schedule but don't update the running scheduler
        # The schedule will be updated on the next restart
        if self.logger:
            self.logger.info(
                f"Regenerated adaptive schedule: {old_count} -> {new_count} events (requires restart to apply)"
            )

    def start(self) -> None:
        """Start the adaptive scheduler."""
        try:
            if self.enabled:
                self._update_schedule()

            self.base_scheduler.start()
            self.running = True

            if self.enabled:
                self._start_update_thread()
        except Exception as e:
            if self.logger:
                import traceback
                self.logger.error(f"Error starting adaptive scheduler: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _start_update_thread(self):
        """Start background thread for periodic schedule updates."""
        def update_loop():
            temp_config = self.adaptation_config.get("temperature", {})
            update_interval = temp_config.get("update_interval_minutes", 60)

            while self.running and not self.shutdown_requested:
                try:
                    # Update temperature/humidity data
                    if self.env_service and self.env_service.temperature_service:
                        self.env_service.temperature_service.fetch_temperature()

                    # Regenerate schedule
                    self._update_schedule()

                    time.sleep(update_interval * 60)
                except Exception as e:
                    if self.logger:
                        import traceback
                        self.logger.error(f"Error in schedule update: {e}")
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(60)

        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the adaptive scheduler gracefully."""
        self.shutdown_requested = True
        self.running = False
        if self.base_scheduler:
            self.base_scheduler.stop(timeout)

    def get_state(self) -> str:
        """Get current scheduler state."""
        return self.base_scheduler.get_state() if self.base_scheduler else "idle"

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.base_scheduler.is_running() if self.base_scheduler else False

    def get_next_event_time(self) -> Optional[datetime]:
        """Get the next scheduled event time."""
        return self.base_scheduler.get_next_event_time() if self.base_scheduler else None

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status for API."""
        device = self._get_device()
        device_info = device.get_device_info() if device else None
        next_event = self.get_next_event_time()

        status = {
            "scheduler_type": "adaptive",
            "running": self.is_running(),
            "state": self.get_state(),
            "device_id": self.device_id,
            "device_name": device_info.name if device_info else None,
            "device_connected": device.is_connected() if device else False,
            "device_state": device.is_device_on() if device else None,
            "flood_duration_minutes": self.flood_duration_minutes,
            "enabled": self.enabled,
            "total_cycles": len(self.adapted_cycles),
            "next_event_time": next_event.isoformat() if next_event else None
        }

        # Add cycle information
        status["cycles"] = [
            {
                "on_time": c.get("on_time", ""),
                "off_duration_minutes": c.get("off_duration_minutes", 0),
                "period": c.get("_period"),
                "temperature": c.get("_temp"),
                "humidity": c.get("_humidity"),
                "temp_factor": c.get("_temp_factor"),
                "humidity_factor": c.get("_humidity_factor")
            }
            for c in self.adapted_cycles
        ]

        return status

    def get_adapted_cycles(self) -> List[Dict[str, Any]]:
        """Get current adapted cycles."""
        return self.adapted_cycles.copy()

