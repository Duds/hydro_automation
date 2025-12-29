"""Device service interface and implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List

from ..device.tapo_controller import TapoController


@dataclass
class DeviceInfo:
    """Device metadata."""
    device_id: str
    name: str
    brand: str
    model: str
    ip_address: Optional[str] = None


class IDeviceService(ABC):
    """Interface for device control services (supports multiple brands)."""

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Get device information.

        Returns:
            DeviceInfo object with device metadata
        """
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Connect to device.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def turn_on(self, verify: bool = True) -> bool:
        """Turn device on.

        Args:
            verify: Whether to verify device state after command

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def turn_off(self, verify: bool = True) -> bool:
        """Turn device off.

        Args:
            verify: Whether to verify device state after command

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def is_device_on(self) -> Optional[bool]:
        """Get device state.

        Returns:
            True if device is on, False if off, None if unknown
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection to device."""
        pass

    @abstractmethod
    def ensure_off(self) -> bool:
        """Ensure device is turned off (used for graceful shutdown).

        Returns:
            True if device is off, False otherwise
        """
        pass


class TapoDeviceService(IDeviceService):
    """Tapo P100 device implementation."""

    def __init__(self, device_id: str, name: str, tapo_controller: TapoController):
        """
        Initialize Tapo device service.

        Args:
            device_id: Unique identifier for this device
            name: Human-readable name for the device
            tapo_controller: TapoController instance to delegate to
        """
        self.device_id = device_id
        self.name = name
        self.controller = tapo_controller
        self._device_info: Optional[DeviceInfo] = None

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        if self._device_info is None:
            self._device_info = DeviceInfo(
                device_id=self.device_id,
                name=self.name,
                brand="tapo",
                model="P100",
                ip_address=self.controller.ip_address
            )
        return self._device_info

    def connect(self) -> bool:
        """Connect to device."""
        return self.controller.connect()

    def turn_on(self, verify: bool = True) -> bool:
        """Turn device on."""
        return self.controller.turn_on(verify=verify)

    def turn_off(self, verify: bool = True) -> bool:
        """Turn device off."""
        return self.controller.turn_off(verify=verify)

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.controller.is_connected()

    def is_device_on(self) -> Optional[bool]:
        """Get device state."""
        return self.controller.is_device_on()

    def close(self) -> None:
        """Close connection to device."""
        self.controller.close()

    def ensure_off(self) -> bool:
        """Ensure device is turned off."""
        return self.controller.ensure_off()


class DeviceRegistry:
    """Registry for managing multiple device services."""

    def __init__(self):
        """Initialize device registry."""
        self._devices: Dict[str, IDeviceService] = {}

    def register(self, device_id: str, device_service: IDeviceService) -> None:
        """Register a device service.

        Args:
            device_id: Unique identifier for the device
            device_service: Device service instance to register
        """
        self._devices[device_id] = device_service

    def get_device(self, device_id: str) -> Optional[IDeviceService]:
        """Get device service by ID.

        Args:
            device_id: Device identifier

        Returns:
            Device service instance or None if not found
        """
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[IDeviceService]:
        """Get all registered devices.

        Returns:
            List of all device service instances
        """
        return list(self._devices.values())

    def get_device_by_name(self, name: str) -> Optional[IDeviceService]:
        """Get device service by name.

        Args:
            name: Device name

        Returns:
            Device service instance or None if not found
        """
        for device in self._devices.values():
            if device.get_device_info().name == name:
                return device
        return None

    def connect_all(self) -> Dict[str, bool]:
        """Connect to all devices.

        Returns:
            Dictionary mapping device_id -> connection success status
        """
        results = {}
        for device_id, device in self._devices.items():
            results[device_id] = device.connect()
        return results

