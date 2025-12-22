"""BOM (Bureau of Meteorology) temperature integration."""

import requests
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import json

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
        self.last_update: Optional[datetime] = None
        self.base_url = "http://www.bom.gov.au/fwo/IDN60801/IDN60801"

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
                    
                    if temperature is not None:
                        self.last_temperature = float(temperature)
                        self.last_update = datetime.now()
                        
                        if self.logger:
                            station_display = f"{self.station_name} ({self.station_id})" if self.station_name else f"station {self.station_id}"
                            self.logger.info(
                                f"Fetched temperature from BOM: {self.last_temperature}°C "
                                f"({station_display})"
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
        elif temperature < 25:
            # Normal: no adjustment
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

