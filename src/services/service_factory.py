"""Factory functions for creating services from configuration."""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .device_service import DeviceRegistry

# Import here to avoid circular dependencies
from .device_service import DeviceRegistry, TapoDeviceService


def create_device_registry(devices_config: Dict[str, Any], logger=None) -> DeviceRegistry:
    """
    Create device registry from configuration.

    Args:
        devices_config: Devices configuration dictionary
        logger: Optional logger instance

    Returns:
        DeviceRegistry with all devices registered
    """
    registry = DeviceRegistry()
    devices = devices_config.get("devices", [])

    for device_config in devices:
        device_id = device_config.get("device_id")
        name = device_config.get("name")
        brand = device_config.get("brand", "tapo")
        ip_address = device_config.get("ip_address")
        email = device_config.get("email")
        password = device_config.get("password")
        auto_discovery = device_config.get("auto_discovery", True)

        if not device_id or not name:
            if logger:
                logger.warning(f"Skipping device config missing device_id or name: {device_config}")
            continue

        # Create device service based on brand
        if brand == "tapo":
            from ..device.tapo_controller import TapoController
            controller = TapoController(
                ip_address=ip_address,
                email=email or "",
                password=password or "",
                logger=logger,
                enable_auto_discovery=auto_discovery
            )
            device_service = TapoDeviceService(
                device_id=device_id,
                name=name,
                tapo_controller=controller
            )
            registry.register(device_id, device_service)
            if logger:
                logger.info(f"Registered Tapo device: {name} ({device_id})")
        else:
            if logger:
                logger.warning(f"Unknown device brand: {brand}, skipping device {device_id}")

    return registry
