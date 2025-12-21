"""BOM (Bureau of Meteorology) temperature integration."""

import requests
import time
from datetime import datetime
from typing import Optional, Dict, Any
import json


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
        self.logger = logger
        self.last_temperature: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.base_url = "http://www.bom.gov.au/fwo/IDN60801/IDN60801"

    def find_nearest_station(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Find nearest BOM observation station to given coordinates.

        Note: This is a simplified implementation. In production, you'd want to
        use a BOM station list or API to find the nearest station.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Station ID or None if not found
        """
        # Common BOM station IDs for major Australian cities
        # This is a simplified lookup - in production, use a full station database
        station_map = {
            # Sydney area
            (-33.8688, 151.2093): "94768",  # Sydney Observatory Hill
            # Melbourne area
            (-37.8136, 144.9631): "95936",  # Melbourne
            # Brisbane area
            (-27.4698, 153.0251): "94578",  # Brisbane
            # Perth area
            (-31.9505, 115.8605): "94610",  # Perth
            # Adelaide area
            (-34.9285, 138.6007): "94672",  # Adelaide
        }

        # Find closest station (simplified - use distance calculation in production)
        min_distance = float('inf')
        closest_station = None

        for (lat, lon), station_id in station_map.items():
            distance = ((latitude - lat) ** 2 + (longitude - lon) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_station = station_id

        if self.logger and closest_station:
            self.logger.info(f"Found nearest BOM station: {closest_station} (distance: {min_distance:.3f} degrees)")

        return closest_station

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

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            
            # Parse BOM observation data
            # Structure: observations.data[0].air_temp
            if "observations" in data and "data" in data["observations"]:
                observations = data["observations"]["data"]
                if observations and len(observations) > 0:
                    latest = observations[0]
                    temperature = latest.get("air_temp")
                    
                    if temperature is not None:
                        self.last_temperature = float(temperature)
                        self.last_update = datetime.now()
                        
                        if self.logger:
                            self.logger.info(
                                f"Fetched temperature from BOM: {self.last_temperature}°C "
                                f"(station {self.station_id})"
                            )
                        
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

    def get_temperature_adjustment_factor(self, temperature: Optional[float]) -> float:
        """
        Calculate adjustment factor for OFF duration based on temperature.

        Args:
            temperature: Temperature in Celsius

        Returns:
            Adjustment factor (1.0 = no change, <1.0 = reduce OFF duration, >1.0 = increase OFF duration)
        """
        if temperature is None:
            return 1.0  # No adjustment if temperature unknown

        # Temperature bands and adjustment factors
        if temperature < 15:
            # Cold: reduce frequency by 10-20% (increase OFF duration)
            factor = 1.15  # 15% longer OFF duration
        elif temperature < 25:
            # Normal: no adjustment
            factor = 1.0
        elif temperature < 30:
            # Warm: increase frequency by 10-20% (reduce OFF duration)
            factor = 0.85  # 15% shorter OFF duration
        else:
            # Hot: increase frequency by 20-30% (reduce OFF duration significantly)
            factor = 0.70  # 30% shorter OFF duration

        if self.logger:
            self.logger.info(
                f"Temperature adjustment factor: {factor:.2f} "
                f"(temperature: {temperature}°C)"
            )

        return factor

