"""Adaptive scheduler wrapper that adjusts cycles based on environmental factors."""

import threading
import time
from datetime import datetime, time as dt_time
from typing import List, Dict, Any, Optional, Tuple

from .time_scheduler import TimeScheduler
from .daylight import DaylightCalculator
from .bom_temperature import BOMTemperature


class AdaptiveScheduler:
    """Wrapper around TimeScheduler that applies environmental adaptations."""

    def __init__(
        self,
        base_cycles: List[Dict[str, Any]],
        controller,
        flood_duration_minutes: float,
        adaptation_config: Dict[str, Any],
        logger=None
    ):
        """
        Initialize adaptive scheduler.

        Args:
            base_cycles: Base cycle definitions
            controller: TapoController instance
            flood_duration_minutes: Flood duration
            adaptation_config: Adaptation configuration dict
            logger: Optional logger instance
        """
        self.base_cycles = base_cycles
        # Ensure adaptation_config is a dict, not a list
        if not isinstance(adaptation_config, dict):
            adaptation_config = {}
        self.adaptation_config = adaptation_config
        self.logger = logger
        self.enabled = adaptation_config.get("enabled", False)
        
        # Initialize tracking attributes BEFORE calling _apply_all_adaptations
        # (which may access these attributes)
        self.last_sunrise_update: Optional[datetime] = None
        self.last_temperature_update: Optional[datetime] = None
        self.last_temperature_value: Optional[float] = None
        self.last_sunrise_time: Optional[dt_time] = None
        self.adapted_cycles: Optional[List[Dict[str, Any]]] = None
        
        # Initialize daylight calculator
        self.daylight_calc: Optional[DaylightCalculator] = None
        daylight_config = adaptation_config.get("daylight", {})
        # Ensure daylight_config is a dict, not a list
        if not isinstance(daylight_config, dict):
            daylight_config = {}
        if self.enabled and daylight_config.get("enabled", False):
            location_config = adaptation_config.get("location", {})
            # Ensure location_config is a dict
            if not isinstance(location_config, dict):
                location_config = {}
            postcode = location_config.get("postcode")
            timezone = location_config.get("timezone")
            if postcode:
                self.daylight_calc = DaylightCalculator(postcode=postcode, timezone=timezone, logger=logger)
        
        # Initialize temperature fetcher
        self.temperature_fetcher: Optional[BOMTemperature] = None
        temp_config = adaptation_config.get("temperature", {})
        # Ensure temp_config is a dict, not a list
        if not isinstance(temp_config, dict):
            temp_config = {}
        if self.enabled and temp_config.get("enabled", False):
            station_id = temp_config.get("station_id", "auto")
            if station_id == "auto" and self.daylight_calc and self.daylight_calc.location_info:
                # Auto-detect station from location
                lat = self.daylight_calc.location_info.latitude
                lon = self.daylight_calc.location_info.longitude
                station_id = BOMTemperature(logger=logger).find_nearest_station(lat, lon)
            
            if station_id and station_id != "auto":
                self.temperature_fetcher = BOMTemperature(station_id=station_id, logger=logger)
        
        # Apply adaptations and create base scheduler
        adapted_cycles, _ = self._apply_all_adaptations(base_cycles.copy())
        # Ensure adapted_cycles is a flat list of dicts
        if adapted_cycles:
            # Flatten if nested
            flattened = []
            for item in adapted_cycles:
                if isinstance(item, list):
                    flattened.extend(item)
                elif isinstance(item, dict):
                    flattened.append(item)
                else:
                    if logger:
                        logger.warning(f"Skipping invalid cycle item (not dict or list): {item}")
            adapted_cycles = flattened if flattened else adapted_cycles
        self.base_scheduler = TimeScheduler(
            controller=controller,
            cycles=adapted_cycles,
            flood_duration_minutes=flood_duration_minutes,
            logger=logger
        )

    def _apply_daylight_shift(self, base_cycles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Apply daylight-based schedule shifting.
        
        Returns:
            Tuple of (shifted_cycles, sunrise_changed)
        """
        if not self.daylight_calc:
            return base_cycles, False
        
        daylight_config = self.adaptation_config.get("daylight", {})
        # Ensure daylight_config is a dict, not a list
        if not isinstance(daylight_config, dict):
            daylight_config = {}
        if not daylight_config.get("shift_schedule", False):
            return base_cycles, False
        
        # Ensure last_sunrise_time is initialized (safety check)
        if not hasattr(self, 'last_sunrise_time'):
            self.last_sunrise_time = None
        
        sunrise, sunset = self.daylight_calc.get_sunrise_sunset()
        sunrise_changed = False
        if sunrise:
            # Check if sunrise time changed
            if self.last_sunrise_time is None or self.last_sunrise_time != sunrise:
                sunrise_changed = True
                if self.logger and self.last_sunrise_time is not None:
                    self.logger.info(
                        f"Sunrise time changed: {self.last_sunrise_time.strftime('%H:%M')} -> {sunrise.strftime('%H:%M')}"
                    )
                self.last_sunrise_time = sunrise
            
            shifted = self.daylight_calc.shift_schedule_to_sunrise(base_cycles, sunrise)
            # Ensure shifted is a list of dicts, not nested lists
            if shifted and isinstance(shifted[0], list):
                # Flatten if nested
                flattened = []
                for item in shifted:
                    if isinstance(item, list):
                        flattened.extend(item)
                    else:
                        flattened.append(item)
                shifted = flattened
            if self.logger:
                self.logger.info(f"Applied daylight shift: sunrise at {sunrise.strftime('%H:%M')}")
            return shifted, sunrise_changed
        
        return base_cycles, False

    def _get_time_period(self, cycle_time: dt_time, sunrise: Optional[dt_time] = None, sunset: Optional[dt_time] = None) -> str:
        """
        Determine which time period a cycle belongs to.
        
        Periods:
        - morning: 06:00-09:00 (or sunrise to 09:00 if sunrise shift enabled)
        - day: 09:00-18:00 (or 09:00 to sunset if daylight shift enabled)
        - evening: 18:00-20:00 (or sunset to 20:00)
        - night: 20:00-06:00 next day (or 20:00 to sunrise)
        
        Args:
            cycle_time: Time of the cycle
            sunrise: Sunrise time (optional, for dynamic morning start)
            sunset: Sunset time (optional, for dynamic day/evening boundaries)
            
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
        
        # Adjust boundaries if sunrise/sunset are provided and within reasonable range
        if sunrise:
            sunrise_minutes = sunrise.hour * 60 + sunrise.minute
            # Use sunrise as morning start if it's between 5:00 and 7:00
            if 5 * 60 <= sunrise_minutes <= 7 * 60:
                morning_start = sunrise_minutes
        
        if sunset:
            sunset_minutes = sunset.hour * 60 + sunset.minute
            # Use sunset for day/evening boundary if it's between 17:00 and 19:00
            if 17 * 60 <= sunset_minutes <= 19 * 60:
                evening_start = sunset_minutes
        
        # Determine period
        # Night period spans midnight (20:00 to 06:00 next day)
        if cycle_minutes >= night_start or cycle_minutes < morning_start:
            return "night"
        elif morning_start <= cycle_minutes < day_start:
            return "morning"
        elif day_start <= cycle_minutes < evening_start:
            return "day"
        else:  # evening_start <= cycle_minutes < night_start
            return "evening"
    
    def _apply_daylight_boost_reduction(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply time-of-day period-based factors to cycle OFF durations.
        
        Uses period-based factors (morning, day, evening, night) if configured,
        otherwise falls back to binary daylight_boost/night_reduction for backward compatibility.
        
        If preserve_base_durations is enabled, this function returns cycles unchanged,
        preserving the base schedule's already-optimized OFF durations.
        """
        if not self.daylight_calc:
            return cycles
        
        daylight_config = self.adaptation_config.get("daylight", {})
        # Ensure daylight_config is a dict, not a list
        if not isinstance(daylight_config, dict):
            daylight_config = {}
        if not daylight_config.get("enabled", False):
            return cycles
        
        # Check if base durations should be preserved (schedule already optimized)
        preserve_base_durations = daylight_config.get("preserve_base_durations", False)
        if preserve_base_durations:
            if self.logger:
                self.logger.info("Preserving base OFF durations (schedule already optimized for plant growth)")
            return cycles
        
        sunrise, sunset = self.daylight_calc.get_sunrise_sunset()
        if not sunrise or not sunset:
            return cycles
        
        # Check if period-based factors are configured
        period_factors = daylight_config.get("period_factors", {})
        # Ensure period_factors is a dict, not a list
        if not isinstance(period_factors, dict):
            period_factors = {}
        use_periods = bool(period_factors)
        
        if use_periods:
            # Use period-based factors
            morning_factor = period_factors.get("morning", 1.0)
            day_factor = period_factors.get("day", 1.0)
            evening_factor = period_factors.get("evening", 1.0)
            night_factor = period_factors.get("night", 1.0)
            
            # Convert boost factors to OFF duration multipliers
            # Factor > 1.0 means more frequent = shorter OFF = multiply by 1/factor
            # Factor < 1.0 means less frequent = longer OFF = divide by factor
            def convert_factor(factor: float) -> float:
                if factor > 1.0:
                    return 1.0 / factor  # Shorter OFF (more frequent)
                elif factor < 1.0:
                    return 1.0 / factor  # Longer OFF (less frequent) - same formula
                else:
                    return 1.0
            
            morning_off_factor = convert_factor(morning_factor)
            day_off_factor = convert_factor(day_factor)
            evening_off_factor = convert_factor(evening_factor)
            night_off_factor = convert_factor(night_factor)
        else:
            # Backward compatibility: use binary daylight_boost/night_reduction
            daylight_boost = daylight_config.get("daylight_boost", 1.2)
            night_reduction = daylight_config.get("night_reduction", 0.8)
            
            # Convert factors to OFF duration multipliers
            daylight_factor = 1.0 / daylight_boost if daylight_boost != 0 else 1.0
            night_factor = night_reduction
            
            # Map to periods for logging
            morning_off_factor = daylight_factor
            day_off_factor = daylight_factor
            evening_off_factor = daylight_factor
            night_off_factor = night_factor
        
        adjusted_cycles = []
        period_counts = {"morning": 0, "day": 0, "evening": 0, "night": 0}
        
        for cycle in cycles:
            adjusted_cycle = cycle.copy()
            on_time_str = cycle.get("on_time")
            
            if on_time_str:
                # Parse time string
                if isinstance(on_time_str, str):
                    parts = on_time_str.split(":")
                    cycle_time = dt_time(int(parts[0]), int(parts[1]))
                else:
                    cycle_time = on_time_str
                
                # Determine period
                period = self._get_time_period(cycle_time, sunrise, sunset)
                
                # Get appropriate factor for this period
                if period == "morning":
                    adjustment_factor = morning_off_factor
                elif period == "day":
                    adjustment_factor = day_off_factor
                elif period == "evening":
                    adjustment_factor = evening_off_factor
                else:  # night
                    adjustment_factor = night_off_factor
                
                period_counts[period] += 1
                
                # Apply adjustment
                off_duration = cycle.get("off_duration_minutes", 0)
                adjusted_off = off_duration * adjustment_factor
                
                # Apply safety limits
                min_off = 5  # Minimum 5 minutes
                max_off = 180  # Maximum 180 minutes
                
                adjusted_off = max(min_off, min(max_off, adjusted_off))
                adjusted_cycle["off_duration_minutes"] = adjusted_off
            else:
                adjusted_cycle = cycle.copy()
            
            adjusted_cycles.append(adjusted_cycle)
        
        if self.logger and any(count > 0 for count in period_counts.values()):
            if use_periods:
                self.logger.info(
                    f"Applied period-based factors: "
                    f"morning={period_factors.get('morning', 1.0):.2f} ({period_counts['morning']} cycles), "
                    f"day={period_factors.get('day', 1.0):.2f} ({period_counts['day']} cycles), "
                    f"evening={period_factors.get('evening', 1.0):.2f} ({period_counts['evening']} cycles), "
                    f"night={period_factors.get('night', 1.0):.2f} ({period_counts['night']} cycles)"
                )
            else:
                # Backward compatibility logging
                daylight_boost = daylight_config.get("daylight_boost", 1.2)
                night_reduction = daylight_config.get("night_reduction", 0.8)
                daylight_count = period_counts["morning"] + period_counts["day"] + period_counts["evening"]
                self.logger.info(
                    f"Applied daylight boost/reduction: "
                    f"daylight_boost={daylight_boost:.2f} ({daylight_count} cycles), "
                    f"night_reduction={night_reduction:.2f} ({period_counts['night']} cycles)"
                )
        
        return adjusted_cycles

    def _apply_temperature_adjustment(self, cycles: List[Dict[str, Any]], force_update: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Apply temperature-based OFF duration adjustments.
        
        Args:
            cycles: List of cycles to adjust
            force_update: Force temperature fetch even if within update interval
            
        Returns:
            Tuple of (adjusted_cycles, temperature_changed)
        """
        if not self.temperature_fetcher:
            return cycles, False
        
        # Ensure last_temperature_update is initialized
        if not hasattr(self, 'last_temperature_update'):
            self.last_temperature_update = None
        if not hasattr(self, 'last_temperature_value'):
            self.last_temperature_value = None
        
        temp_config = self.adaptation_config.get("temperature", {})
        # Ensure temp_config is a dict, not a list
        if not isinstance(temp_config, dict):
            temp_config = {}
        update_interval = temp_config.get("update_interval_minutes", 60)
        
        # Check if we need to update temperature
        now = datetime.now()
        should_update = force_update or (
            self.last_temperature_update is None or
            (now - self.last_temperature_update).total_seconds() >= update_interval * 60
        )
        
        temperature_changed = False
        if should_update:
            temperature = self.temperature_fetcher.fetch_temperature()
            if temperature is not None:
                # Check if temperature actually changed (more than 0.5°C difference)
                if self.last_temperature_value is None or abs(temperature - self.last_temperature_value) >= 0.5:
                    temperature_changed = True
                    if self.logger:
                        self.logger.info(
                            f"Temperature changed: {self.last_temperature_value}°C -> {temperature}°C"
                        )
                self.last_temperature_value = temperature
                self.last_temperature_update = now
        
        # Get adjustment factor with sensitivity
        sensitivity = temp_config.get("adjustment_sensitivity", "medium")
        adjustment_factor = self.temperature_fetcher.get_temperature_adjustment_factor(
            self.temperature_fetcher.last_temperature,
            sensitivity=sensitivity
        )
        
        if adjustment_factor == 1.0:
            return cycles, temperature_changed  # No adjustment needed
        
        # Apply adjustment to OFF durations
        adjusted_cycles = []
        for cycle in cycles:
            adjusted_cycle = cycle.copy()
            off_duration = cycle.get("off_duration_minutes", 0)
            
            # Apply adjustment with safety limits
            adjusted_off = off_duration * adjustment_factor
            min_off = 5  # Minimum 5 minutes
            max_off = 180  # Maximum 180 minutes
            
            adjusted_off = max(min_off, min(max_off, adjusted_off))
            adjusted_cycle["off_duration_minutes"] = adjusted_off
            
            adjusted_cycles.append(adjusted_cycle)
        
        if self.logger:
            self.logger.info(
                f"Applied temperature adjustment: factor {adjustment_factor:.2f}, "
                f"temperature {self.temperature_fetcher.last_temperature}°C"
            )
        
        return adjusted_cycles, temperature_changed

    def _apply_all_adaptations(self, cycles: List[Dict[str, Any]], force_temperature_update: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Apply all adaptations to cycles.
        
        Args:
            cycles: Base cycles to adapt
            force_temperature_update: Force temperature fetch even if within interval
            
        Returns:
            Tuple of (adapted_cycles, changes_detected)
        """
        if not self.enabled:
            return cycles, False
        
        changes_detected = False
        
        # Apply daylight shift (daily)
        cycles, sunrise_changed = self._apply_daylight_shift(cycles)
        if sunrise_changed:
            changes_detected = True
        self.last_sunrise_update = datetime.now()
        
        # Apply daylight boost/reduction (daily)
        cycles = self._apply_daylight_boost_reduction(cycles)
        
        # Apply temperature adjustment (hourly or when temperature changes)
        cycles, temp_changed = self._apply_temperature_adjustment(cycles, force_update=force_temperature_update)
        if temp_changed:
            changes_detected = True
        if force_temperature_update or temp_changed:
            self.last_temperature_update = datetime.now()
        
        self.adapted_cycles = cycles
        return cycles, changes_detected

    def _update_adaptations(self, force_temperature_update: bool = False):
        """
        Update schedule adaptations based on environmental factors and apply to running scheduler.
        
        Args:
            force_temperature_update: Force temperature fetch even if within update interval
        """
        if not self.enabled:
            return
        
        # Re-apply adaptations to base cycles
        adapted, changes_detected = self._apply_all_adaptations(
            self.base_cycles.copy(),
            force_temperature_update=force_temperature_update
        )
        self.adapted_cycles = adapted
        
        # If changes were detected or forced update, apply to running scheduler
        if changes_detected or force_temperature_update:
            if self.base_scheduler.is_running():
                # Convert adapted cycles to format expected by TimeScheduler
                formatted_cycles = []
                for cycle in adapted:
                    on_time = cycle.get("on_time")
                    if isinstance(on_time, dt_time):
                        on_time_str = on_time.strftime("%H:%M")
                    else:
                        on_time_str = str(on_time)
                    
                    formatted_cycles.append({
                        "on_time": on_time_str,
                        "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                    })
                
                self.base_scheduler.update_cycles(formatted_cycles)
                if self.logger:
                    self.logger.info("Schedule updated and applied to running scheduler")
            else:
                if self.logger:
                    self.logger.info("Adaptations updated (scheduler not running)")
        else:
            if self.logger:
                self.logger.debug("Adaptations checked - no changes detected")

    def start(self):
        """Start the adaptive scheduler."""
        try:
            # Update adaptations before starting
            if self.enabled:
                self._update_adaptations()
            
            # Start base scheduler
            self.base_scheduler.start()
            
            # Start adaptation update thread (after scheduler is running)
            if self.enabled:
                self._start_adaptation_thread()
        except Exception as e:
            if self.logger:
                import traceback
                self.logger.error(f"Error starting adaptive scheduler: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _start_adaptation_thread(self):
        """Start background thread for periodic adaptation updates."""
        def adaptation_loop():
            # Check temperature more frequently (every 5 minutes) to catch changes
            temp_config = self.adaptation_config.get("temperature", {})
            # Ensure temp_config is a dict, not a list
            if not isinstance(temp_config, dict):
                temp_config = {}
            temp_check_interval = temp_config.get("check_interval_minutes", 5)  # Check every 5 min
            temp_update_interval = temp_config.get("update_interval_minutes", 60)  # Fetch every 60 min
            
            last_temp_check = datetime.now()
            last_daylight_check = datetime.now()
            
            while self.base_scheduler.running:
                try:
                    now = datetime.now()
                    
                    # Check temperature more frequently (every 5 minutes by default)
                    if (now - last_temp_check).total_seconds() >= temp_check_interval * 60:
                        # Force temperature update if it's been long enough since last fetch
                        force_update = (
                            self.last_temperature_update is None or
                            (now - self.last_temperature_update).total_seconds() >= temp_update_interval * 60
                        )
                        self._update_adaptations(force_temperature_update=force_update)
                        last_temp_check = now
                    
                    # Check daylight changes daily (once per day)
                    if (now - last_daylight_check).total_seconds() >= 24 * 60 * 60:
                        self._update_adaptations(force_temperature_update=False)
                        last_daylight_check = now
                    
                    # Sleep for shorter intervals to be more responsive
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    if self.logger:
                        import traceback
                        self.logger.error(f"Error in adaptation update: {e}")
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        import traceback
                        print(f"Error in adaptation update: {e}")
                        traceback.print_exc()
                    time.sleep(60)  # Wait 1 minute before retry
        
        thread = threading.Thread(target=adaptation_loop, daemon=True)
        thread.start()

    def stop(self, timeout: float = 10.0):
        """Stop the adaptive scheduler."""
        self.base_scheduler.stop(timeout)

    def get_state(self) -> str:
        """Get current scheduler state."""
        return self.base_scheduler.get_state()

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.base_scheduler.is_running()

