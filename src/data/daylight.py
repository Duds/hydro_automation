"""Daylight calculations for sunrise/sunset and schedule shifting."""

from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Tuple
import pytz
from astral import LocationInfo
from astral.sun import sun
import pgeocode
import pandas as pd


class DaylightCalculator:
    """Calculate sunrise/sunset times and shift schedules based on daylight hours."""

    def __init__(self, postcode: Optional[str] = None, timezone: Optional[str] = None, logger=None):
        """
        Initialize daylight calculator.

        Args:
            postcode: Australian postcode
            timezone: Timezone string (e.g., "Australia/Sydney")
            logger: Optional logger instance
        """
        self.postcode = postcode
        self.logger = logger
        self.location_info: Optional[LocationInfo] = None
        self.timezone_str = timezone or "Australia/Sydney"
        self.timezone = pytz.timezone(self.timezone_str)
        
        if postcode:
            self._setup_location_from_postcode(postcode)

    def _setup_location_from_postcode(self, postcode: str):
        """Convert postcode to lat/long and setup location."""
        try:
            # Use pgeocode for Australian postcodes
            nomi = pgeocode.Nominatim('au')  # 'au' for Australia
            location_data = nomi.query_postal_code(postcode)
            
            if location_data is not None and not location_data.empty:
                latitude = location_data['latitude']
                longitude = location_data['longitude']
                
                if pd.notna(latitude) and pd.notna(longitude):
                    # Get city name if available
                    city_name = location_data.get('place_name', f'Postcode {postcode}')
                    
                    self.location_info = LocationInfo(
                        name=city_name,
                        region="Australia",
                        timezone=self.timezone_str,
                        latitude=float(latitude),
                        longitude=float(longitude)
                    )
                    
                    if self.logger:
                        self.logger.info(
                            f"Location set from postcode {postcode}: "
                            f"{city_name} ({latitude}, {longitude})"
                        )
                else:
                    if self.logger:
                        self.logger.warning(f"Could not find location for postcode {postcode}")
            else:
                if self.logger:
                    self.logger.warning(f"Postcode {postcode} not found in database")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error setting up location from postcode: {e}")

    def get_sunrise_sunset(self, date: Optional[datetime] = None) -> Tuple[Optional[dt_time], Optional[dt_time]]:
        """
        Get sunrise and sunset times for a given date.

        Args:
            date: Date to calculate for (default: today)

        Returns:
            Tuple of (sunrise_time, sunset_time) or (None, None) if calculation fails
        """
        if not self.location_info:
            if self.logger:
                self.logger.warning("Location not set, cannot calculate sunrise/sunset")
            return None, None

        try:
            if date is None:
                date = datetime.now(self.timezone)
            else:
                # Ensure date is timezone-aware
                if date.tzinfo is None:
                    date = self.timezone.localize(date)
                else:
                    date = date.astimezone(self.timezone)

            s = sun(self.location_info.observer, date=date.date(), tzinfo=self.timezone)
            
            sunrise = s["sunrise"].time()
            sunset = s["sunset"].time()
            
            return sunrise, sunset
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating sunrise/sunset: {e}")
            return None, None

    def shift_schedule_to_sunrise(self, base_cycles: list, sunrise_time: dt_time) -> list:
        """
        Shift base schedule cycles to align with sunrise.

        Args:
            base_cycles: List of cycle dicts with 'on_time' and 'off_duration_minutes'
            sunrise_time: Target sunrise time

        Returns:
            List of shifted cycles
        """
        if not base_cycles:
            return base_cycles

        # Find the earliest cycle time
        earliest_time = None
        for cycle in base_cycles:
            on_time_str = cycle.get("on_time")
            if on_time_str:
                # Parse time string
                if isinstance(on_time_str, str):
                    parts = on_time_str.split(":")
                    cycle_time = dt_time(int(parts[0]), int(parts[1]))
                else:
                    cycle_time = on_time_str
                
                if earliest_time is None or cycle_time < earliest_time:
                    earliest_time = cycle_time

        if earliest_time is None:
            return base_cycles

        # Calculate time difference between earliest cycle and sunrise
        earliest_minutes = earliest_time.hour * 60 + earliest_time.minute
        sunrise_minutes = sunrise_time.hour * 60 + sunrise_time.minute
        shift_minutes = sunrise_minutes - earliest_minutes

        # Shift all cycles
        shifted_cycles = []
        for cycle in base_cycles:
            on_time_str = cycle.get("on_time")
            if on_time_str:
                if isinstance(on_time_str, str):
                    parts = on_time_str.split(":")
                    cycle_time = dt_time(int(parts[0]), int(parts[1]))
                else:
                    cycle_time = on_time_str
                
                # Add shift
                total_minutes = (cycle_time.hour * 60 + cycle_time.minute + shift_minutes) % (24 * 60)
                new_hour = total_minutes // 60
                new_minute = total_minutes % 60
                new_time = dt_time(new_hour, new_minute)
                
                shifted_cycle = cycle.copy()
                shifted_cycle["on_time"] = new_time.strftime("%H:%M")
                shifted_cycles.append(shifted_cycle)
            else:
                shifted_cycles.append(cycle)

        if self.logger:
            self.logger.info(
                f"Shifted schedule by {shift_minutes} minutes to align with sunrise at {sunrise_time.strftime('%H:%M')}"
            )

        return shifted_cycles

