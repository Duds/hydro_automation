"""Sensor service interface and implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class SensorReading:
    """Sensor reading with timestamp."""
    value: float
    unit: str
    timestamp: datetime
    sensor_id: str


class ISensor(ABC):
    """Interface for sensor devices."""

    @abstractmethod
    def get_sensor_id(self) -> str:
        """Get unique sensor identifier.

        Returns:
            Sensor ID string
        """
        pass

    @abstractmethod
    def get_sensor_type(self) -> str:
        """Get sensor type.

        Returns:
            Sensor type string (e.g., 'reservoir_level', 'ec', 'ph')
        """
        pass

    @abstractmethod
    def read(self) -> Optional[SensorReading]:
        """Read current sensor value.

        Returns:
            SensorReading object or None if reading failed
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if sensor is available/connected.

        Returns:
            True if sensor is available, False otherwise
        """
        pass


class ReservoirLevelSensor(ISensor):
    """Reservoir water level sensor."""

    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any], logger=None):
        """
        Initialize reservoir level sensor.

        Args:
            sensor_id: Unique sensor identifier
            name: Human-readable sensor name
            config: Sensor-specific configuration
            logger: Optional logger instance
        """
        self.sensor_id = sensor_id
        self.name = name
        self.config = config
        self.logger = logger
        # TODO: Initialize sensor hardware/API based on config

    def get_sensor_id(self) -> str:
        """Get sensor ID."""
        return self.sensor_id

    def get_sensor_type(self) -> str:
        """Get sensor type."""
        return "reservoir_level"

    def read(self) -> Optional[SensorReading]:
        """Read current sensor value.

        Returns:
            SensorReading with level percentage (0-100)
        """
        # TODO: Implement actual sensor reading
        # For now, return None to indicate not implemented
        if self.logger:
            self.logger.debug(f"Reservoir level sensor {self.sensor_id} read not yet implemented")
        return None

    def is_available(self) -> bool:
        """Check if sensor is available."""
        # TODO: Implement actual availability check
        return False


class ECSensor(ISensor):
    """Electrical conductivity sensor (nutrient concentration)."""

    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any], logger=None):
        """
        Initialize EC sensor.

        Args:
            sensor_id: Unique sensor identifier
            name: Human-readable sensor name
            config: Sensor-specific configuration
            logger: Optional logger instance
        """
        self.sensor_id = sensor_id
        self.name = name
        self.config = config
        self.logger = logger
        # TODO: Initialize sensor hardware/API based on config

    def get_sensor_id(self) -> str:
        """Get sensor ID."""
        return self.sensor_id

    def get_sensor_type(self) -> str:
        """Get sensor type."""
        return "ec"

    def read(self) -> Optional[SensorReading]:
        """Read current sensor value.

        Returns:
            SensorReading with EC value in mS/cm
        """
        # TODO: Implement actual sensor reading
        if self.logger:
            self.logger.debug(f"EC sensor {self.sensor_id} read not yet implemented")
        return None

    def is_available(self) -> bool:
        """Check if sensor is available."""
        # TODO: Implement actual availability check
        return False


class PHSensor(ISensor):
    """pH sensor (acidity/alkalinity)."""

    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any], logger=None):
        """
        Initialize pH sensor.

        Args:
            sensor_id: Unique sensor identifier
            name: Human-readable sensor name
            config: Sensor-specific configuration
            logger: Optional logger instance
        """
        self.sensor_id = sensor_id
        self.name = name
        self.config = config
        self.logger = logger
        # TODO: Initialize sensor hardware/API based on config

    def get_sensor_id(self) -> str:
        """Get sensor ID."""
        return self.sensor_id

    def get_sensor_type(self) -> str:
        """Get sensor type."""
        return "ph"

    def read(self) -> Optional[SensorReading]:
        """Read current sensor value.

        Returns:
            SensorReading with pH value (0-14)
        """
        # TODO: Implement actual sensor reading
        if self.logger:
            self.logger.debug(f"pH sensor {self.sensor_id} read not yet implemented")
        return None

    def is_available(self) -> bool:
        """Check if sensor is available."""
        # TODO: Implement actual availability check
        return False


class SensorRegistry:
    """Registry for managing sensor devices."""

    def __init__(self):
        """Initialize sensor registry."""
        self._sensors: Dict[str, ISensor] = {}

    def register(self, sensor: ISensor) -> None:
        """Register a sensor.

        Args:
            sensor: Sensor instance to register
        """
        self._sensors[sensor.get_sensor_id()] = sensor

    def get_sensor(self, sensor_id: str) -> Optional[ISensor]:
        """Get sensor by ID.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Sensor instance or None if not found
        """
        return self._sensors.get(sensor_id)

    def get_sensors_by_type(self, sensor_type: str) -> List[ISensor]:
        """Get all sensors of a specific type.

        Args:
            sensor_type: Sensor type string

        Returns:
            List of sensors of the specified type
        """
        return [s for s in self._sensors.values() if s.get_sensor_type() == sensor_type]

    def get_latest_reading(self, sensor_id: str) -> Optional[SensorReading]:
        """Get latest reading from a sensor.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Latest SensorReading or None if sensor not found or reading failed
        """
        sensor = self.get_sensor(sensor_id)
        return sensor.read() if sensor else None

