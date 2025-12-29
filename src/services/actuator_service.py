"""Actuator service interface and implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ActuatorInfo:
    """Actuator metadata."""
    actuator_id: str
    name: str
    type: str  # 'dosing_pump', 'valve', etc.
    channel: Optional[int] = None  # For multi-channel pumps


class IActuator(ABC):
    """Interface for actuator devices (dosing pumps, valves, etc.)."""

    @abstractmethod
    def get_actuator_info(self) -> ActuatorInfo:
        """Get actuator information.

        Returns:
            ActuatorInfo object with actuator metadata
        """
        pass

    @abstractmethod
    def activate(self, duration_seconds: float, verify: bool = True) -> bool:
        """Activate actuator for specified duration.

        Args:
            duration_seconds: Duration to activate actuator in seconds
            verify: Whether to verify activation (if supported)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if actuator is connected.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop actuator immediately.

        Returns:
            True if successful, False otherwise
        """
        pass


class DosingPumpService(IActuator):
    """Dosing pump implementation."""

    def __init__(self, actuator_id: str, name: str, config: Dict[str, Any], logger=None):
        """
        Initialize dosing pump service.

        Args:
            actuator_id: Unique actuator identifier
            name: Human-readable actuator name
            config: Actuator-specific configuration
            logger: Optional logger instance
        """
        self.actuator_id = actuator_id
        self.name = name
        self.config = config
        self.logger = logger
        self.channel = config.get("channel")  # For multi-channel pumps
        # TODO: Initialize pump hardware/controller based on config

    def get_actuator_info(self) -> ActuatorInfo:
        """Get actuator information."""
        return ActuatorInfo(
            actuator_id=self.actuator_id,
            name=self.name,
            type="dosing_pump",
            channel=self.channel
        )

    def activate(self, duration_seconds: float, verify: bool = True) -> bool:
        """Activate pump for specified duration.

        Args:
            duration_seconds: Duration to run pump in seconds
            verify: Whether to verify activation (if supported)

        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement actual pump activation
        # Could be PWM control, relay control, serial command, etc.
        if self.logger:
            self.logger.debug(
                f"Dosing pump {self.actuator_id} activate for {duration_seconds}s not yet implemented"
            )
        return False

    def is_connected(self) -> bool:
        """Check if pump is connected."""
        # TODO: Implement actual connection check
        return False

    def stop(self) -> bool:
        """Stop pump immediately."""
        # TODO: Implement actual pump stop
        if self.logger:
            self.logger.debug(f"Dosing pump {self.actuator_id} stop not yet implemented")
        return False


class ActuatorRegistry:
    """Registry for managing actuator devices."""

    def __init__(self):
        """Initialize actuator registry."""
        self._actuators: Dict[str, IActuator] = {}

    def register(self, actuator: IActuator) -> None:
        """Register an actuator.

        Args:
            actuator: Actuator instance to register
        """
        info = actuator.get_actuator_info()
        self._actuators[info.actuator_id] = actuator

    def get_actuator(self, actuator_id: str) -> Optional[IActuator]:
        """Get actuator by ID.

        Args:
            actuator_id: Actuator identifier

        Returns:
            Actuator instance or None if not found
        """
        return self._actuators.get(actuator_id)

    def get_actuators_by_type(self, actuator_type: str) -> List[IActuator]:
        """Get all actuators of a specific type.

        Args:
            actuator_type: Actuator type string

        Returns:
            List of actuators of the specified type
        """
        return [
            a for a in self._actuators.values()
            if a.get_actuator_info().type == actuator_type
        ]

