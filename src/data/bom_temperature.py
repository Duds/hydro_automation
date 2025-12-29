"""BOM (Bureau of Meteorology) temperature and humidity integration."""

import requests
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Dict, Any, Tuple, List
import json
from collections import deque

from .bom_stations import (
    get_station_name,
    find_nearest_station as find_nearest_station_db,
    get_station_info
)


class BOMTemperature:
    """Fetch temperature data from BOM observation stations."""

    def __init__(self, station_id: Optional[str] = None, logger=None):
        """
        Initialize BOM temperature fetcher.

        Args:
            station_id: BOM observation station ID (e.g., "94768" for Sydney Observatory Hill)
            logger: Optional logger instance
        """
        self.station_id = station_id
        self.station_name: Optional[str] = None
        if station_id:
            self.station_name = get_station_name(station_id)
        self.logger = logger
        self.last_temperature: Optional[float] = None
        self.last_humidity: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.base_url = "http://www.bom.gov.au/fwo/IDN60801/IDN60801"
        
        # Historical data for trend analysis (stores last 24 hours)
        # Format: [(datetime, temperature, humidity), ...]
        self.historical_data: deque = deque(maxlen=24)  # Store hourly data for 24 hours

    def find_nearest_station(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Find nearest BOM observation station to given coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Station ID or None if not found
        """
        result = find_nearest_station_db(latitude, longitude)
        if result:
            station_id, station_name, distance_km = result
            if self.logger:
                self.logger.info(
                    f"Found nearest BOM station: {station_name} ({station_id}) "
                    f"at {distance_km:.1f} km"
                )
            return station_id
        return None

    def fetch_temperature(self) -> Optional[float]:
        """
        Fetch current temperature from BOM observation station.

        Returns:
            Temperature in Celsius, or None if fetch fails
        """
        if not self.station_id:
            if self.logger:
                self.logger.warning("No BOM station ID configured")
            return None

        try:
            url = f"{self.base_url}.{self.station_id}.json"
            
            if self.logger:
                self.logger.debug(f"Fetching temperature from BOM: {url}")

            # BOM requires a User-Agent header
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            
            # Parse BOM observation data
            # Structure: observations.data[0].air_temp
            if "observations" in data and "data" in data["observations"]:
                observations = data["observations"]["data"]
                if observations and len(observations) > 0:
                    latest = observations[0]
                    temperature = latest.get("air_temp")
                    humidity = latest.get("rel_hum")
                    
                    if temperature is not None:
                        self.last_temperature = float(temperature)
                        self.last_update = datetime.now()
                        
                        # Store humidity if available
                        if humidity is not None:
                            self.last_humidity = float(humidity)
                        
                        # Store in historical data
                        self.historical_data.append((
                            self.last_update,
                            self.last_temperature,
                            self.last_humidity
                        ))
                        
                        if self.logger:
                            station_display = f"{self.station_name} ({self.station_id})" if self.station_name else f"station {self.station_id}"
                            temp_msg = f"Fetched from BOM: {self.last_temperature}°C"
                            if self.last_humidity is not None:
                                temp_msg += f", {self.last_humidity}% humidity"
                            temp_msg += f" ({station_display})"
                            self.logger.info(temp_msg)
                        
                        return self.last_temperature
                    else:
                        if self.logger:
                            self.logger.warning(f"No air_temp field in BOM data for station {self.station_id}")
                else:
                    if self.logger:
                        self.logger.warning(f"No observation data available for station {self.station_id}")
            else:
                if self.logger:
                    self.logger.warning(f"Unexpected BOM data structure for station {self.station_id}")

        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.error(f"Error fetching temperature from BOM: {e}")
        except (KeyError, ValueError, TypeError) as e:
            if self.logger:
                self.logger.error(f"Error parsing BOM temperature data: {e}")

        # Return cached temperature if available
        if self.last_temperature is not None:
            if self.logger:
                self.logger.info(f"Using cached temperature: {self.last_temperature}°C")
            return self.last_temperature

        return None

    def get_temperature_adjustment_factor(self, temperature: Optional[float], sensitivity: str = "medium") -> float:
        """
        Calculate adjustment factor for OFF duration based on temperature.

        Args:
            temperature: Temperature in Celsius
            sensitivity: Adjustment sensitivity - "low", "medium", or "high" (default: "medium")

        Returns:
            Adjustment factor (1.0 = no change, <1.0 = reduce OFF duration, >1.0 = increase OFF duration)
        """
        if temperature is None:
            return 1.0  # No adjustment if temperature unknown

        # Base temperature bands and adjustment factors (medium sensitivity)
        if temperature < 15:
            # Cold: reduce frequency by 10-20% (increase OFF duration)
            base_factor = 1.15  # 15% longer OFF duration
        elif temperature <= 25:
            # Normal: no adjustment (include 25°C in normal range)
            base_factor = 1.0
        elif temperature < 30:
            # Warm: increase frequency by 10-20% (reduce OFF duration)
            base_factor = 0.85  # 15% shorter OFF duration
        else:
            # Hot: increase frequency by 20-30% (reduce OFF duration significantly)
            base_factor = 0.70  # 30% shorter OFF duration

        # Apply sensitivity scaling
        # Low: reduce adjustments by ~30% (make closer to 1.0)
        # Medium: no scaling (use base factors)
        # High: increase adjustments by ~30% (make further from 1.0)
        if sensitivity == "low":
            if base_factor == 1.0:
                factor = 1.0  # No adjustment stays no adjustment
            elif base_factor > 1.0:
                # Scale down: 1.0 + (base - 1.0) * 0.7
                factor = 1.0 + (base_factor - 1.0) * 0.7
            else:
                # Scale up: 1.0 - (1.0 - base) * 0.7
                factor = 1.0 - (1.0 - base_factor) * 0.7
        elif sensitivity == "high":
            if base_factor == 1.0:
                factor = 1.0  # No adjustment stays no adjustment
            elif base_factor > 1.0:
                # Scale up: 1.0 + (base - 1.0) * 1.3
                factor = 1.0 + (base_factor - 1.0) * 1.3
            else:
                # Scale down: 1.0 - (1.0 - base) * 1.3
                factor = 1.0 - (1.0 - base_factor) * 1.3
        else:  # medium (default)
            factor = base_factor

        if self.logger:
            self.logger.info(
                f"Temperature adjustment factor: {factor:.2f} "
                f"(temperature: {temperature}°C, sensitivity: {sensitivity})"
            )

        return factor

    def fetch_humidity(self) -> Optional[float]:
        """
        Fetch current humidity from BOM observation station.
        
        Returns:
            Humidity as percentage (0-100), or None if fetch fails
        """
        # Fetch temperature (which also fetches humidity)
        self.fetch_temperature()
        return self.last_humidity

    def get_temperature_at_time(self, target_time: dt_time) -> Optional[float]:
        """
        Estimate temperature for a specific time of day.
        
        Uses current temperature and historical patterns to estimate.
        For future times, uses diurnal patterns (typically cooler in morning, warmer in afternoon).
        
        Args:
            target_time: Time of day to estimate temperature for
            
        Returns:
            Estimated temperature in Celsius, or None if cannot estimate
        """
        if self.last_temperature is None:
            return None
        
        # If we have historical data, use it for better estimation
        if len(self.historical_data) >= 2:
            # Calculate trend from historical data
            recent_temps = [d[1] for d in self.historical_data if d[1] is not None]
            if len(recent_temps) >= 2:
                # Simple linear trend
                temp_trend = (recent_temps[0] - recent_temps[-1]) / len(recent_temps)
                
                # Estimate based on time of day and trend
                current_hour = datetime.now().hour
                target_hour = target_time.hour
                hours_diff = target_hour - current_hour
                
                # Diurnal pattern: typically warmest around 14:00-16:00, coolest around 06:00
                # Simple model: adjust based on hour difference and diurnal pattern
                diurnal_adjustment = 0
                if 6 <= target_hour <= 10:
                    # Morning: typically cooler
                    diurnal_adjustment = -2
                elif 10 < target_hour <= 14:
                    # Late morning to early afternoon: warming
                    diurnal_adjustment = 2
                elif 14 < target_hour <= 18:
                    # Afternoon: warmest
                    diurnal_adjustment = 3
                elif 18 < target_hour <= 22:
                    # Evening: cooling
                    diurnal_adjustment = 1
                else:
                    # Night: coolest
                    diurnal_adjustment = -1
                
                estimated = self.last_temperature + (temp_trend * hours_diff) + diurnal_adjustment
                return max(0, min(50, estimated))  # Clamp to reasonable range
        
        # Fallback: use current temperature with simple diurnal adjustment
        current_hour = datetime.now().hour
        target_hour = target_time.hour
        
        # Simple diurnal pattern
        if 6 <= target_hour <= 10:
            return self.last_temperature - 2
        elif 10 < target_hour <= 14:
            return self.last_temperature + 2
        elif 14 < target_hour <= 18:
            return self.last_temperature + 3
        elif 18 < target_hour <= 22:
            return self.last_temperature + 1
        else:
            return self.last_temperature - 1

    def get_humidity_at_time(self, target_time: dt_time) -> Optional[float]:
        """
        Estimate humidity for a specific time of day.
        
        Humidity typically follows inverse pattern to temperature (higher when cooler).
        
        Args:
            target_time: Time of day to estimate humidity for
            
        Returns:
            Estimated humidity as percentage (0-100), or None if cannot estimate
        """
        if self.last_humidity is None:
            return None
        
        # Humidity typically inversely correlates with temperature
        # Cooler times = higher humidity, warmer times = lower humidity
        current_hour = datetime.now().hour
        target_hour = target_time.hour
        
        # Simple model: adjust based on time of day
        if 6 <= target_hour <= 10:
            # Morning: typically higher humidity
            return min(100, self.last_humidity + 5)
        elif 10 < target_hour <= 14:
            # Late morning to early afternoon: lower humidity
            return max(0, self.last_humidity - 5)
        elif 14 < target_hour <= 18:
            # Afternoon: lowest humidity
            return max(0, self.last_humidity - 10)
        elif 18 < target_hour <= 22:
            # Evening: increasing humidity
            return min(100, self.last_humidity + 3)
        else:
            # Night: highest humidity
            return min(100, self.last_humidity + 8)

    def calculate_temperature_trend(self, hours: int = 3) -> str:
        """
        Calculate temperature trend over the last N hours.
        
        Args:
            hours: Number of hours to analyze (default: 3)
            
        Returns:
            Trend string: "rising", "falling", or "stable"
        """
        if len(self.historical_data) < 2:
            return "stable"
        
        # Get data points within the specified hours
        cutoff_time = datetime.now() - timedelta(hours=hours)
        relevant_data = [
            d for d in self.historical_data
            if d[0] >= cutoff_time and d[1] is not None
        ]
        
        if len(relevant_data) < 2:
            return "stable"
        
        # Calculate trend
        # relevant_data is in chronological order (oldest first) since deque.append() adds to end
        temps = [d[1] for d in relevant_data]
        oldest_temp = temps[0]
        newest_temp = temps[-1]
        change = newest_temp - oldest_temp
        
        # Threshold: 1°C change indicates trend
        if change > 1.0:
            return "rising"
        elif change < -1.0:
            return "falling"
        else:
            return "stable"

    def get_humidity_adjustment_factor(self, humidity: Optional[float]) -> float:
        """
        Calculate adjustment factor for OFF duration based on humidity.
        
        Low humidity increases transpiration (need more frequent flooding).
        High humidity decreases transpiration (need less frequent flooding).
        
        Args:
            humidity: Humidity as percentage (0-100)
            
        Returns:
            Adjustment factor (1.0 = no change, <1.0 = reduce OFF duration, >1.0 = increase OFF duration)
        """
        if humidity is None:
            return 1.0  # No adjustment if humidity unknown
        
        # Humidity bands and adjustment factors
        if humidity < 40:
            # Low humidity: increase frequency (reduce OFF duration)
            return 0.9  # 10% shorter OFF duration
        elif humidity <= 70:
            # Normal humidity: no adjustment
            return 1.0
        else:
            # High humidity: decrease frequency (increase OFF duration)
            return 1.1  # 10% longer OFF duration

