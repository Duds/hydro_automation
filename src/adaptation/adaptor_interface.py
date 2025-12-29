"""Adaptation strategy interfaces."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.environmental_service import EnvironmentalService
    from ..services.sensor_service import SensorRegistry


class IAdaptor(ABC):
    """Interface for schedule adaptation strategies."""

    @abstractmethod
    def adapt(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt cycles based on environmental factors.

        Args:
            cycles: List of cycle dictionaries to adapt

        Returns:
            List of adapted cycle dictionaries
        """
        pass

    @abstractmethod
    def should_update(self) -> bool:
        """Check if adaptation should be recalculated.

        Returns:
            True if adaptation should be updated, False otherwise
        """
        pass


class DaylightAdaptor(IAdaptor):
    """Daylight-based adaptation."""

    def __init__(
        self,
        env_service: "EnvironmentalService",
        config: Dict[str, Any]
    ):
        """
        Initialize daylight adaptor.

        Args:
            env_service: Environmental service instance
            config: Adaptation configuration dictionary
        """
        self.env_service = env_service
        self.config = config

    def adapt(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt cycles based on daylight patterns."""
        # TODO: Implement daylight-based adaptation
        # This will be implemented when refactoring AdaptiveScheduler
        return cycles

    def should_update(self) -> bool:
        """Check if daylight adaptation should be updated (daily)."""
        # TODO: Implement update check (e.g., check if sunrise time changed)
        return False


class TemperatureAdaptor(IAdaptor):
    """Temperature-based adaptation."""

    def __init__(
        self,
        env_service: "EnvironmentalService",
        config: Dict[str, Any]
    ):
        """
        Initialize temperature adaptor.

        Args:
            env_service: Environmental service instance
            config: Adaptation configuration dictionary
        """
        self.env_service = env_service
        self.config = config

    def adapt(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt cycles based on temperature."""
        # TODO: Implement temperature-based adaptation
        # This will be implemented when refactoring AdaptiveScheduler
        return cycles

    def should_update(self) -> bool:
        """Check if temperature adaptation should be updated (hourly or when temp changes)."""
        # TODO: Implement update check
        return False


class SensorAdaptor(IAdaptor):
    """Sensor-based adaptation (reservoir level, EC, pH)."""

    def __init__(
        self,
        sensor_registry: "SensorRegistry",
        config: Dict[str, Any]
    ):
        """
        Initialize sensor adaptor.

        Args:
            sensor_registry: Sensor registry instance
            config: Adaptation configuration dictionary
        """
        self.sensor_registry = sensor_registry
        self.config = config

    def adapt(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt cycles based on sensor readings.

        Examples:
            - If reservoir level low, reduce cycle frequency
            - If EC high, reduce nutrient dosing frequency
            - If pH out of range, trigger pH adjustment
        """
        # TODO: Implement sensor-based adaptation
        # This will be implemented when sensors are added
        return cycles

    def should_update(self) -> bool:
        """Check if sensor adaptation should be updated."""
        # TODO: Implement update check (e.g., when sensor readings change significantly)
        return False


class CompositeAdaptor(IAdaptor):
    """Composes multiple adaptors."""

    def __init__(self, adaptors: List[IAdaptor]):
        """
        Initialize composite adaptor.

        Args:
            adaptors: List of adaptor instances to compose
        """
        self.adaptors = adaptors

    def adapt(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all adaptors in sequence.

        Args:
            cycles: List of cycle dictionaries to adapt

        Returns:
            List of cycles after applying all adaptors
        """
        result = cycles
        for adaptor in self.adaptors:
            result = adaptor.adapt(result)
        return result

    def should_update(self) -> bool:
        """Check if any adaptor needs updating."""
        return any(adaptor.should_update() for adaptor in self.adaptors)

