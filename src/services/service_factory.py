"""Factory functions for creating services from configuration."""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .device_service import DeviceRegistry, IDeviceService
    from .sensor_service import SensorRegistry, ISensor
    from .actuator_service import ActuatorRegistry, IActuator
    from .environmental_service import EnvironmentalService

# Import here to avoid circular dependencies
from .device_service import DeviceRegistry, TapoDeviceService
from .sensor_service import SensorRegistry, ReservoirLevelSensor, ECSensor, PHSensor
from .actuator_service import ActuatorRegistry, DosingPumpService
from .environmental_service import EnvironmentalService


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
            # TODO: Add support for other brands (TPLink, Sonoff, etc.)

    return registry


def create_sensor_registry(sensors_config: Dict[str, Any], logger=None) -> SensorRegistry:
    """
    Create sensor registry from configuration.

    Args:
        sensors_config: Sensors configuration dictionary
        logger: Optional logger instance

    Returns:
        SensorRegistry with all sensors registered
    """
    registry = SensorRegistry()
    sensors = sensors_config.get("sensors", [])

    for sensor_config in sensors:
        sensor_id = sensor_config.get("sensor_id")
        name = sensor_config.get("name")
        sensor_type = sensor_config.get("type")
        config = sensor_config.get("config", {})

        if not sensor_id or not name or not sensor_type:
            if logger:
                logger.warning(f"Skipping sensor config missing required fields: {sensor_config}")
            continue

        # Create sensor based on type
        if sensor_type == "reservoir_level":
            sensor = ReservoirLevelSensor(sensor_id, name, config, logger)
            registry.register(sensor)
            if logger:
                logger.info(f"Registered reservoir level sensor: {name} ({sensor_id})")
        elif sensor_type == "ec":
            sensor = ECSensor(sensor_id, name, config, logger)
            registry.register(sensor)
            if logger:
                logger.info(f"Registered EC sensor: {name} ({sensor_id})")
        elif sensor_type == "ph":
            sensor = PHSensor(sensor_id, name, config, logger)
            registry.register(sensor)
            if logger:
                logger.info(f"Registered pH sensor: {name} ({sensor_id})")
        else:
            if logger:
                logger.warning(f"Unknown sensor type: {sensor_type}, skipping sensor {sensor_id}")

    return registry


def create_actuator_registry(actuators_config: Dict[str, Any], logger=None) -> ActuatorRegistry:
    """
    Create actuator registry from configuration.

    Args:
        actuators_config: Actuators configuration dictionary
        logger: Optional logger instance

    Returns:
        ActuatorRegistry with all actuators registered
    """
    registry = ActuatorRegistry()
    actuators = actuators_config.get("actuators", [])

    for actuator_config in actuators:
        actuator_id = actuator_config.get("actuator_id")
        name = actuator_config.get("name")
        actuator_type = actuator_config.get("type")
        config = actuator_config.get("config", {})

        if not actuator_id or not name or not actuator_type:
            if logger:
                logger.warning(f"Skipping actuator config missing required fields: {actuator_config}")
            continue

        # Create actuator based on type
        if actuator_type == "dosing_pump":
            actuator = DosingPumpService(actuator_id, name, config, logger)
            registry.register(actuator)
            if logger:
                logger.info(f"Registered dosing pump: {name} ({actuator_id})")
        else:
            if logger:
                logger.warning(f"Unknown actuator type: {actuator_type}, skipping actuator {actuator_id}")

    return registry


def create_environmental_service(
    adaptation_config: Dict[str, Any],
    logger=None
) -> EnvironmentalService:
    """
    Create environmental service from adaptation configuration.

    Args:
        adaptation_config: Adaptation configuration dictionary
        logger: Optional logger instance

    Returns:
        EnvironmentalService instance
    """
    location_config = adaptation_config.get("location", {}) or {}
    temp_config = adaptation_config.get("temperature", {}) or {}

    return EnvironmentalService(
        location_config=location_config,
        temp_config=temp_config,
        logger=logger
    )

