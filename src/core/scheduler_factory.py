"""Factory for creating scheduler instances based on configuration."""

from typing import Dict, Any, Optional

from ..schedulers.base_scheduler import BaseScheduler
from ..schedulers.interval_scheduler import IntervalScheduler
from ..schedulers.time_based_scheduler import TimeBasedScheduler


class SchedulerFactory:
    """Factory class for creating schedulers."""

    @staticmethod
    def create_scheduler(
        config: Dict[str, Any],
        device_registry=None,
        logger=None
    ) -> BaseScheduler:
        """
        Create a scheduler instance from configuration.

        Args:
            config: Full application configuration dictionary
            device_registry: DeviceRegistry instance
            logger: Logger instance

        Returns:
            An instance of a BaseScheduler subclass
        """
        schedule_config = config.get("schedule", {})
        schedule_type = schedule_config.get("type", "interval")
        growing_system = config.get("growing_system", {})
        primary_device_id = growing_system.get("primary_device_id")

        if not primary_device_id:
            raise ValueError("primary_device_id must be specified in growing_system config")

        if schedule_type == "interval":
            return SchedulerFactory._create_interval_scheduler(
                schedule_config, primary_device_id, device_registry, logger
            )
        elif schedule_type == "time_based":
            return SchedulerFactory._create_time_based_scheduler(
                schedule_config, primary_device_id, device_registry, logger
            )
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def _create_interval_scheduler(
        config: Dict[str, Any],
        device_id: str,
        device_registry=None,
        logger=None
    ) -> IntervalScheduler:
        """Create an IntervalScheduler."""
        return IntervalScheduler(
            device_id=device_id,
            flood_duration_minutes=config.get("flood_duration_minutes", 15.0),
            drain_duration_minutes=config.get("drain_duration_minutes", 30.0),
            interval_minutes=config.get("interval_minutes", 120.0),
            active_hours_start=config.get("active_hours_start"),
            active_hours_end=config.get("active_hours_end"),
            device_registry=device_registry,
            logger=logger
        )

    @staticmethod
    def _create_time_based_scheduler(
        config: Dict[str, Any],
        device_id: str,
        device_registry=None,
        logger=None
    ) -> TimeBasedScheduler:
        """Create a TimeBasedScheduler."""
        return TimeBasedScheduler(
            device_id=device_id,
            flood_duration_minutes=config.get("flood_duration_minutes", 15.0),
            cycles=config.get("cycles", []),
            device_registry=device_registry,
            logger=logger
        )
