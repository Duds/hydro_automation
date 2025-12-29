"""Centralised service for environmental data sources."""

from typing import Optional, Dict, Any

from ..data.daylight import DaylightCalculator
from ..data.bom_temperature import BOMTemperature


class EnvironmentalService:
    """Centralised service for environmental data sources."""

    def __init__(self, location_config: Dict[str, Any], temp_config: Dict[str, Any], logger=None):
        """
        Initialize environmental service.

        Args:
            location_config: Location configuration dictionary with 'postcode' and optional 'timezone'
            temp_config: Temperature configuration dictionary with 'enabled', 'source', 'station_id', etc.
            logger: Optional logger instance
        """
        self.logger = logger
        self.daylight_calc: Optional[DaylightCalculator] = None
        self.temperature_service: Optional[BOMTemperature] = None

        # Initialize daylight calculator
        postcode = location_config.get("postcode") if location_config else None
        if postcode:
            timezone = location_config.get("timezone", "Australia/Sydney")
            try:
                self.daylight_calc = DaylightCalculator(
                    postcode=postcode,
                    timezone=timezone,
                    logger=logger
                )
                if self.logger:
                    self.logger.info(f"Daylight calculator initialised for postcode {postcode}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to initialise daylight calculator: {e}")

        # Initialize temperature service
        if temp_config and temp_config.get("enabled", False):
            source = temp_config.get("source", "bom")
            if source == "bom":
                station_id = temp_config.get("station_id", "auto")
                if station_id == "auto" and self.daylight_calc and self.daylight_calc.location_info:
                    # Auto-detect station from location
                    lat = self.daylight_calc.location_info.latitude
                    lon = self.daylight_calc.location_info.longitude
                    temp_fetcher_temp = BOMTemperature(logger=logger)
                    station_id = temp_fetcher_temp.find_nearest_station(lat, lon)
                    if not station_id:
                        # Fallback to default Sydney station
                        station_id = "94768"
                        if self.logger:
                            self.logger.info("Using default BOM station (Sydney) - configure postcode for nearest station")
                elif not station_id or station_id == "auto":
                    # No location configured, use default
                    station_id = "94768"
                    if self.logger:
                        self.logger.info("Using default BOM station (Sydney) - configure postcode for nearest station")

                if station_id and station_id != "auto":
                    try:
                        self.temperature_service = BOMTemperature(station_id=station_id, logger=logger)
                        station_name = self.temperature_service.station_name or station_id
                        if self.logger:
                            self.logger.info(
                                f"BOM temperature service initialised for {station_name} ({station_id})"
                            )
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Failed to initialise temperature service: {e}")

