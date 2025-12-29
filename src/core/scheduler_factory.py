"""Factory for creating scheduler instances."""

from typing import Dict, Any, TYPE_CHECKING

from .scheduler_interface import IScheduler

if TYPE_CHECKING:
    from ..services.device_service import DeviceRegistry
    from ..services.sensor_service import SensorRegistry
    from ..services.actuator_service import ActuatorRegistry
    from ..services.environmental_service import EnvironmentalService


class SchedulerFactory:
    """Factory for creating scheduler instances."""

    def __init__(
        self,
        device_registry: "DeviceRegistry",
        sensor_registry: "SensorRegistry",
        actuator_registry: "ActuatorRegistry",
        env_service: "EnvironmentalService",
        logger=None
    ):
        """
        Initialize scheduler factory.

        Args:
            device_registry: Device registry instance
            sensor_registry: Sensor registry instance
            actuator_registry: Actuator registry instance
            env_service: Environmental service instance
            logger: Optional logger instance
        """
        self.device_registry = device_registry
        self.sensor_registry = sensor_registry
        self.actuator_registry = actuator_registry
        self.env_service = env_service
        self.logger = logger

    def create(self, config: Dict[str, Any]) -> IScheduler:
        """
        Create scheduler based on configuration.

        Args:
            config: Configuration dictionary (validated AppConfig)

        Returns:
            Scheduler instance implementing IScheduler

        Raises:
            ValueError: If configuration is invalid or scheduler cannot be created
        """
        schedule_config = config.get("schedule", {})
        schedule_type = schedule_config.get("type", "interval")
        growing_system = config.get("growing_system", {}).get("type", "flood_drain")

        # Select scheduler based on growing system and schedule type
        if growing_system == "nft":
            return self._create_nft_scheduler(config, schedule_config)
        elif growing_system == "flood_drain":
            if schedule_type == "interval":
                return self._create_interval_scheduler(config, schedule_config)
            elif schedule_type == "time_based":
                adaptation_config = schedule_config.get("adaptation", {}) or {}
                if adaptation_config.get("enabled", False) and adaptation_config.get("adaptive", {}).get("enabled", False):
                    return self._create_adaptive_scheduler(config, schedule_config, adaptation_config)
                else:
                    return self._create_time_based_scheduler(config, schedule_config)
            else:
                raise ValueError(f"Unknown schedule type: {schedule_type}")
        else:
            raise ValueError(f"Unknown growing system: {growing_system}")

    def _create_interval_scheduler(self, config: Dict[str, Any], schedule_config: Dict[str, Any]) -> IScheduler:
        """Create interval-based scheduler."""
        from ..schedulers.interval_scheduler import IntervalScheduler

        growing_system = config.get("growing_system", {})
        device_id = growing_system.get("primary_device_id")

        if not device_id:
            raise ValueError("primary_device_id is required in growing_system configuration")

        # Get cycle config from schedule (interval type)
        flood_duration = float(schedule_config.get("flood_duration_minutes", 15.0))
        drain_duration = float(schedule_config.get("drain_duration_minutes", 30.0))
        interval = float(schedule_config.get("interval_minutes", 120.0))
        enabled = schedule_config.get("enabled", True)
        active_hours = schedule_config.get("active_hours") or {}

        return IntervalScheduler(
            device_registry=self.device_registry,
            device_id=device_id,
            flood_duration_minutes=flood_duration,
            drain_duration_minutes=drain_duration,
            interval_minutes=interval,
            schedule_enabled=enabled,
            active_hours_start=active_hours.get("start"),
            active_hours_end=active_hours.get("end"),
            logger=self.logger
        )

    def _create_time_based_scheduler(self, config: Dict[str, Any], schedule_config: Dict[str, Any]) -> IScheduler:
        """Create time-based scheduler."""
        from ..schedulers.time_based_scheduler import TimeBasedScheduler

        growing_system = config.get("growing_system", {})
        device_id = growing_system.get("primary_device_id")

        if not device_id:
            raise ValueError("primary_device_id is required in growing_system configuration")

        flood_duration = float(schedule_config.get("flood_duration_minutes", 2.0))
        cycles = schedule_config.get("cycles", [])

        if not cycles:
            raise ValueError("cycles are required for time_based schedule")

        return TimeBasedScheduler(
            device_registry=self.device_registry,
            device_id=device_id,
            cycles=cycles,
            flood_duration_minutes=flood_duration,
            logger=self.logger
        )

    def _create_adaptive_scheduler(self, config: Dict[str, Any], schedule_config: Dict[str, Any], adaptation_config: Dict[str, Any]) -> IScheduler:
        """Create adaptive scheduler."""
        from ..schedulers.adaptive_scheduler import AdaptiveScheduler

        growing_system = config.get("growing_system", {})
        device_id = growing_system.get("primary_device_id")

        if not device_id:
            raise ValueError("primary_device_id is required in growing_system configuration")

        flood_duration = float(schedule_config.get("flood_duration_minutes", 2.0))

        return AdaptiveScheduler(
            device_registry=self.device_registry,
            device_id=device_id,
            flood_duration_minutes=flood_duration,
            adaptation_config=adaptation_config,
            env_service=self.env_service,
            logger=self.logger
        )

    def _create_nft_scheduler(self, config: Dict[str, Any], schedule_config: Dict[str, Any]) -> IScheduler:
        """Create NFT scheduler."""
        from ..schedulers.nft_scheduler import NFTScheduler

        growing_system = config.get("growing_system", {})
        device_id = growing_system.get("primary_device_id")

        if not device_id:
            raise ValueError("primary_device_id is required in growing_system configuration")

        flow_schedule = growing_system.get("config", {})

        return NFTScheduler(
            device_registry=self.device_registry,
            device_id=device_id,
            flow_schedule=flow_schedule,
            logger=self.logger
        )

