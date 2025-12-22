"""Active adaptive scheduler that generates schedules independently from environmental factors."""

import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Any, Optional, Tuple

from .time_scheduler import TimeScheduler
from .daylight import DaylightCalculator
from .bom_temperature import BOMTemperature


class ActiveAdaptiveScheduler:
    """
    Active adaptive scheduler that generates flood schedules independently from factors.
    
    This scheduler has NO programmatic relationship with the base schedule.
    It calculates everything from scratch using:
    - Time of Day (ToD) requirements
    - Temperature at time of day
    - Temperature trends
    - Humidity at time of day
    - Day length/seasonal adjustments
    """

    def __init__(
        self,
        controller,
        flood_duration_minutes: float,
        adaptation_config: Dict[str, Any],
        logger=None
    ):
        """
        Initialize active adaptive scheduler.

        Args:
            controller: TapoController instance
            flood_duration_minutes: Flood duration in minutes
            adaptation_config: Adaptation configuration dict
            logger: Optional logger instance
        """
        self.controller = controller
        self.flood_duration_minutes = flood_duration_minutes
        self.adaptation_config = adaptation_config
        self.logger = logger
        self.enabled = adaptation_config.get("active_adaptive", {}).get("enabled", False)
        
        # Get active adaptive config
        active_config = adaptation_config.get("active_adaptive", {})
        self.tod_frequencies = active_config.get("tod_frequencies", {
            "morning": 18.0,
            "day": 28.0,
            "evening": 18.0,
            "night": 118.0
        })
        self.temperature_bands = active_config.get("temperature_bands", {
            "cold": {"max": 15, "factor": 1.15},
            "normal": {"min": 15, "max": 25, "factor": 1.0},
            "warm": {"min": 25, "max": 30, "factor": 0.85},
            "hot": {"min": 30, "factor": 0.70}
        })
        self.humidity_bands = active_config.get("humidity_bands", {
            "low": {"max": 40, "factor": 0.9},
            "normal": {"min": 40, "max": 70, "factor": 1.0},
            "high": {"min": 70, "factor": 1.1}
        })
        self.constraints = active_config.get("constraints", {
            "min_wait_duration": 5,
            "max_wait_duration": 180,
            "min_flood_duration": 2,
            "max_flood_duration": 15
        })
        
        # Initialize environmental data sources
        self.daylight_calc: Optional[DaylightCalculator] = None
        location_config = adaptation_config.get("location", {})
        postcode = location_config.get("postcode")
        timezone = location_config.get("timezone")
        if postcode:
            self.daylight_calc = DaylightCalculator(postcode=postcode, timezone=timezone, logger=logger)
        
        self.temperature_fetcher: Optional[BOMTemperature] = None
        temp_config = adaptation_config.get("temperature", {})
        if temp_config.get("enabled", False):
            station_id = temp_config.get("station_id", "auto")
            if station_id == "auto" and self.daylight_calc and self.daylight_calc.location_info:
                lat = self.daylight_calc.location_info.latitude
                lon = self.daylight_calc.location_info.longitude
                station_id = BOMTemperature(logger=logger).find_nearest_station(lat, lon)
            
            if station_id and station_id != "auto":
                self.temperature_fetcher = BOMTemperature(station_id=station_id, logger=logger)
                # Fetch initial data
                self.temperature_fetcher.fetch_temperature()
        
        # Generate initial schedule
        self.adapted_cycles: List[Dict[str, Any]] = []
        if self.enabled:
            self._generate_schedule()
        
        # Create base scheduler with generated cycles (or empty if not enabled)
        # Format cycles for TimeScheduler
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
        
        self.base_scheduler = TimeScheduler(
            controller=controller,
            cycles=formatted_cycles,
            flood_duration_minutes=flood_duration_minutes,
            logger=logger
        )
        
        # Threading
        self.running = False
        self.shutdown_requested = False

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
        
        # Get sunrise/sunset
        sunrise = None
        sunset = None
        if self.daylight_calc:
            sunrise, sunset = self.daylight_calc.get_sunrise_sunset()
        
        # Generate events for each period
        all_events = []
        
        # Morning period (sunrise or 06:00 to 09:00)
        morning_start = sunrise if sunrise and 5 * 60 <= (sunrise.hour * 60 + sunrise.minute) <= 7 * 60 else dt_time(6, 0)
        morning_end = dt_time(9, 0)
        all_events.extend(self._generate_period_events("morning", morning_start, morning_end, sunrise, sunset))
        
        # Day period (09:00 to sunset or 18:00)
        day_start = dt_time(9, 0)
        day_end = sunset if sunset and 17 * 60 <= (sunset.hour * 60 + sunset.minute) <= 19 * 60 else dt_time(18, 0)
        all_events.extend(self._generate_period_events("day", day_start, day_end, sunrise, sunset))
        
        # Evening period (sunset or 18:00 to 20:00)
        evening_start = sunset if sunset and 17 * 60 <= (sunset.hour * 60 + sunset.minute) <= 19 * 60 else dt_time(18, 0)
        evening_end = dt_time(20, 0)
        all_events.extend(self._generate_period_events("evening", evening_start, evening_end, sunrise, sunset))
        
        # Night period (20:00 to sunrise or 06:00 next day)
        night_start = dt_time(20, 0)
        night_end = sunrise if sunrise and 5 * 60 <= (sunrise.hour * 60 + sunrise.minute) <= 7 * 60 else dt_time(6, 0)
        all_events.extend(self._generate_period_events("night", night_start, night_end, sunrise, sunset))
        
        # Sort by time
        all_events.sort(key=lambda e: self._time_to_minutes(e["on_time"]))
        
        # Apply system constraints
        self.adapted_cycles = self._apply_constraints(all_events)
        
        if self.logger:
            self.logger.info(f"Generated active adaptive schedule with {len(self.adapted_cycles)} events")

    def _generate_period_events(self, period: str, start_time: dt_time, end_time: dt_time, 
                                sunrise: Optional[dt_time], sunset: Optional[dt_time]) -> List[Dict[str, Any]]:
        """
        Generate events for a specific time period.
        
        Args:
            period: Period name ("morning", "day", "evening", "night")
            start_time: Start time of period
            end_time: End time of period
            sunrise: Sunrise time (optional)
            sunset: Sunset time (optional)
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        # Get base frequency for this period
        base_wait = self.calculate_tod_base_frequency(period)
        
        # Calculate period duration
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        # Handle night period wrapping midnight
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        period_duration = end_minutes - start_minutes
        
        # Generate events throughout the period
        current_minutes = start_minutes
        event_time = start_time
        
        while current_minutes < end_minutes:
            # Get environmental conditions for this time
            temp = None
            humidity = None
            if self.temperature_fetcher:
                temp = self.temperature_fetcher.get_temperature_at_time(event_time)
                humidity = self.temperature_fetcher.get_humidity_at_time(event_time)
            
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
        """
        Apply system constraints to events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of events with constraints applied
        """
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
        
        if self.base_scheduler and self.base_scheduler.is_running():
            # Update running scheduler
            formatted_cycles = []
            for cycle in self.adapted_cycles:
                on_time = cycle.get("on_time")
                if isinstance(on_time, str):
                    formatted_cycles.append({
                        "on_time": on_time,
                        "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                    })
                else:
                    # Convert time object to string
                    formatted_cycles.append({
                        "on_time": on_time.strftime("%H:%M") if hasattr(on_time, 'strftime') else str(on_time),
                        "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                    })
            
            self.base_scheduler.update_cycles(formatted_cycles)
            
            if self.logger:
                self.logger.info(
                    f"Updated active adaptive schedule: {old_count} -> {new_count} events"
                )

    def start(self):
        """Start the active adaptive scheduler."""
        try:
            # Update schedule before starting
            if self.enabled:
                self._update_schedule()
            
            # Start base scheduler
            self.base_scheduler.start()
            self.running = True
            
            # Start update thread
            if self.enabled:
                self._start_update_thread()
        except Exception as e:
            if self.logger:
                import traceback
                self.logger.error(f"Error starting active adaptive scheduler: {e}")
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
                    if self.temperature_fetcher:
                        self.temperature_fetcher.fetch_temperature()
                    
                    # Regenerate schedule
                    self._update_schedule()
                    
                    # Wait for next update
                    time.sleep(update_interval * 60)
                except Exception as e:
                    if self.logger:
                        import traceback
                        self.logger.error(f"Error in schedule update: {e}")
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                    time.sleep(60)  # Wait 1 minute before retry
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

    def stop(self, timeout: float = 10.0):
        """Stop the active adaptive scheduler."""
        self.shutdown_requested = True
        self.running = False
        self.base_scheduler.stop(timeout)

    def get_state(self) -> str:
        """Get current scheduler state."""
        return self.base_scheduler.get_state()

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.base_scheduler.is_running()

    def get_adapted_cycles(self) -> List[Dict[str, Any]]:
        """Get current adapted cycles."""
        return self.adapted_cycles.copy()

