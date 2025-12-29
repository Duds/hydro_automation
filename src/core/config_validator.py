"""Configuration validation and loading."""

import json
from pathlib import Path
from typing import Dict, Any

from .config_schema import (
    AppConfig, TimeBasedScheduleConfig, IntervalScheduleConfig,
    ScheduleConfig, GrowingSystemConfig, LoggingConfig, WebConfig
)


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


def load_and_validate_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate configuration from JSON file.

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Validated configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If configuration is invalid
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in configuration file: {e}")

    # Validate main config structure
    try:
        # Validate schedule separately (union type needs special handling)
        schedule_data = config_data.get("schedule", {})
        schedule_type = schedule_data.get("type", "interval")

        if schedule_type == "time_based":
            validated_schedule = TimeBasedScheduleConfig(**schedule_data)
        elif schedule_type == "interval":
            validated_schedule = IntervalScheduleConfig(**schedule_data)
        else:
            raise ConfigValidationError(
                f"Unknown schedule type: {schedule_type}. Must be 'interval' or 'time_based'"
            )

        # Replace schedule in config_data with validated version (as dict for AppConfig)
            config_data["schedule"] = validated_schedule.model_dump()

        # Validate remaining config
        validated_config = AppConfig(**config_data)

        # Return as dict for easier usage
        result = validated_config.model_dump()
        # Convert schedule back to validated object for proper typing
        result["schedule"] = validated_schedule.model_dump()
        return result

    except Exception as e:
        if isinstance(e, ConfigValidationError):
            raise
        # Re-raise Pydantic validation errors with clearer messages
        if hasattr(e, 'errors'):
            error_msgs = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise ConfigValidationError(f"Configuration validation failed:\n" + "\n".join(error_msgs))
        raise ConfigValidationError(f"Configuration validation failed: {e}")

