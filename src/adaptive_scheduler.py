"""Adaptive scheduler wrapper that adjusts cycles based on environmental factors."""

import threading
import time
from datetime import datetime, time as dt_time
from typing import List, Dict, Any, Optional

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
        self.adaptation_config = adaptation_config
        self.logger = logger
        self.enabled = adaptation_config.get("enabled", False)
        
        # Initialize daylight calculator
        self.daylight_calc: Optional[DaylightCalculator] = None
        if self.enabled and adaptation_config.get("daylight", {}).get("enabled", False):
            location_config = adaptation_config.get("location", {})
            postcode = location_config.get("postcode")
            timezone = location_config.get("timezone")
            if postcode:
                self.daylight_calc = DaylightCalculator(postcode=postcode, timezone=timezone, logger=logger)
        
        # Initialize temperature fetcher
        self.temperature_fetcher: Optional[BOMTemperature] = None
        if self.enabled and adaptation_config.get("temperature", {}).get("enabled", False):
            temp_config = adaptation_config.get("temperature", {})
            station_id = temp_config.get("station_id", "auto")
            if station_id == "auto" and self.daylight_calc and self.daylight_calc.location_info:
                # Auto-detect station from location
                lat = self.daylight_calc.location_info.latitude
                lon = self.daylight_calc.location_info.longitude
                station_id = BOMTemperature(logger=logger).find_nearest_station(lat, lon)
            
            if station_id and station_id != "auto":
                self.temperature_fetcher = BOMTemperature(station_id=station_id, logger=logger)
        
        # Apply adaptations and create base scheduler
        adapted_cycles = self._apply_all_adaptations(base_cycles.copy())
        self.base_scheduler = TimeScheduler(
            controller=controller,
            cycles=adapted_cycles,
            flood_duration_minutes=flood_duration_minutes,
            logger=logger
        )
        
        # Track last adaptation time
        self.last_sunrise_update: Optional[datetime] = None
        self.last_temperature_update: Optional[datetime] = None
        self.adapted_cycles: Optional[List[Dict[str, Any]]] = None

    def _apply_daylight_shift(self, base_cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply daylight-based schedule shifting."""
        if not self.daylight_calc:
            return base_cycles
        
        daylight_config = self.adaptation_config.get("daylight", {})
        if not daylight_config.get("shift_schedule", False):
            return base_cycles
        
        sunrise, sunset = self.daylight_calc.get_sunrise_sunset()
        if sunrise:
            shifted = self.daylight_calc.shift_schedule_to_sunrise(base_cycles, sunrise)
            if self.logger:
                self.logger.info(f"Applied daylight shift: sunrise at {sunrise.strftime('%H:%M')}")
            return shifted
        
        return base_cycles

    def _apply_temperature_adjustment(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply temperature-based OFF duration adjustments."""
        if not self.temperature_fetcher:
            return cycles
        
        temp_config = self.adaptation_config.get("temperature", {})
        update_interval = temp_config.get("update_interval_minutes", 60)
        
        # Check if we need to update temperature
        now = datetime.now()
        should_update = (
            self.last_temperature_update is None or
            (now - self.last_temperature_update).total_seconds() >= update_interval * 60
        )
        
        if should_update:
            temperature = self.temperature_fetcher.fetch_temperature()
            if temperature is not None:
                self.last_temperature_update = now
        
        # Get adjustment factor
        adjustment_factor = self.temperature_fetcher.get_temperature_adjustment_factor(
            self.temperature_fetcher.last_temperature
        )
        
        if adjustment_factor == 1.0:
            return cycles  # No adjustment needed
        
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
        
        return adjusted_cycles

    def _apply_all_adaptations(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all adaptations to cycles."""
        if not self.enabled:
            return cycles
        
        # Apply daylight shift (daily)
        cycles = self._apply_daylight_shift(cycles)
        self.last_sunrise_update = datetime.now()
        
        # Apply temperature adjustment (hourly)
        cycles = self._apply_temperature_adjustment(cycles)
        self.last_temperature_update = datetime.now()
        
        self.adapted_cycles = cycles
        return cycles

    def _update_adaptations(self):
        """Update schedule adaptations based on environmental factors (for periodic updates)."""
        if not self.enabled:
            return
        
        # Re-apply adaptations to base cycles
        adapted = self._apply_all_adaptations(self.base_cycles.copy())
        self.adapted_cycles = adapted
        
        if self.logger:
            self.logger.info("Adaptations updated - restart scheduler to apply changes")

    def start(self):
        """Start the adaptive scheduler."""
        # Update adaptations before starting
        if self.enabled:
            self._update_adaptations()
        
        # Start adaptation update thread
        if self.enabled:
            self._start_adaptation_thread()
        
        # Start base scheduler
        self.base_scheduler.start()

    def _start_adaptation_thread(self):
        """Start background thread for periodic adaptation updates."""
        def adaptation_loop():
            while self.base_scheduler.running:
                try:
                    self._update_adaptations()
                    # Check every 30 minutes
                    time.sleep(30 * 60)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in adaptation update: {e}")
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

