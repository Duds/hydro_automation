"""Configuration schema definitions using Pydantic."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union


class DeviceConfig(BaseModel):
    """Configuration for a single device."""
    device_id: str
    name: str
    brand: str = "tapo"  # 'tapo', 'tplink', 'sonoff', etc.
    type: str = "power_controller"  # 'power_controller', 'dosing_pump', etc.
    ip_address: str
    email: Optional[str] = None  # Brand-specific auth
    password: Optional[str] = None  # Brand-specific auth
    auto_discovery: bool = True
    config: Optional[Dict[str, Any]] = None  # Brand-specific config


class DevicesConfig(BaseModel):
    """Configuration for multiple devices."""
    devices: List[DeviceConfig]


class SensorConfig(BaseModel):
    """Configuration for a sensor."""
    sensor_id: str
    name: str
    type: str  # 'reservoir_level', 'ec', 'ph'
    config: Dict[str, Any]  # Sensor-specific configuration


class SensorsConfig(BaseModel):
    """Configuration for multiple sensors."""
    sensors: List[SensorConfig] = []


class ActuatorConfig(BaseModel):
    """Configuration for an actuator (dosing pump, valve, etc.)."""
    actuator_id: str
    name: str
    type: str  # 'dosing_pump', 'valve'
    config: Dict[str, Any]  # Actuator-specific configuration


class ActuatorsConfig(BaseModel):
    """Configuration for multiple actuators."""
    actuators: List[ActuatorConfig] = []


class CycleDefinition(BaseModel):
    """Single cycle definition for time-based scheduling."""
    on_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    off_duration_minutes: float


class LocationConfig(BaseModel):
    """Location configuration for environmental data."""
    postcode: str
    timezone: str = "Australia/Sydney"


class TemperatureConfig(BaseModel):
    """Temperature configuration."""
    enabled: bool = False
    source: str = "bom"
    station_id: Optional[str] = "auto"
    update_interval_minutes: int = 60


class DaylightConfig(BaseModel):
    """Daylight adaptation configuration."""
    enabled: bool = False
    shift_schedule: bool = False
    period_factors: Optional[Dict[str, float]] = None
    daylight_boost: float = 1.2
    night_reduction: float = 0.8
    update_frequency: str = "daily"


class AdaptiveConfig(BaseModel):
    """Adaptive scheduling configuration."""
    enabled: bool = False
    tod_frequencies: Dict[str, float] = Field(
        default_factory=lambda: {
            "morning": 18.0,
            "day": 28.0,
            "evening": 18.0,
            "night": 118.0
        }
    )
    temperature_bands: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "cold": {"max": 15, "factor": 1.15},
        "normal": {"min": 15, "max": 25, "factor": 1.0},
        "warm": {"min": 25, "max": 30, "factor": 0.85},
        "hot": {"min": 30, "factor": 0.70}
    })
    humidity_bands: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "low": {"max": 40, "factor": 0.9},
        "normal": {"min": 40, "max": 70, "factor": 1.0},
        "high": {"min": 70, "factor": 1.1}
    })
    constraints: Dict[str, float] = Field(default_factory=lambda: {
        "min_wait_duration": 5,
        "max_wait_duration": 180,
        "min_flood_duration": 2,
        "max_flood_duration": 15
    })


class AdaptationConfig(BaseModel):
    """Adaptation configuration."""
    enabled: bool = False
    location: Optional[LocationConfig] = None
    temperature: Optional[TemperatureConfig] = None
    daylight: Optional[DaylightConfig] = None
    adaptive: Optional[AdaptiveConfig] = None


class TimeBasedScheduleConfig(BaseModel):
    """Time-based schedule configuration."""
    type: str = "time_based"
    flood_duration_minutes: float
    cycles: List[CycleDefinition]
    adaptation: Optional[AdaptationConfig] = None


class IntervalScheduleConfig(BaseModel):
    """Interval-based schedule configuration."""
    type: str = "interval"
    enabled: bool = True
    flood_duration_minutes: float
    drain_duration_minutes: float
    interval_minutes: float
    active_hours: Optional[Dict[str, str]] = None


# Union type for schedule config (handled manually in config validator)
ScheduleConfig = Union[TimeBasedScheduleConfig, IntervalScheduleConfig]


class GrowingSystemConfig(BaseModel):
    """Growing system configuration."""
    type: str = "flood_drain"  # 'flood_drain', 'nft', 'dwc', 'aeroponics'
    primary_device_id: str  # Main power controller device ID
    config: Optional[Dict[str, Any]] = None  # System-specific config


class LoggingConfig(BaseModel):
    """Logging configuration."""
    log_file: str = "logs/hydro_controller.log"
    log_level: str = "INFO"


class WebConfig(BaseModel):
    """Web interface configuration."""
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    """Main application configuration."""
    devices: DevicesConfig
    sensors: SensorsConfig = SensorsConfig(sensors=[])
    actuators: ActuatorsConfig = ActuatorsConfig(actuators=[])
    growing_system: GrowingSystemConfig
    schedule: Dict[str, Any]  # Schedule config (validated separately based on type)
    logging: LoggingConfig
    web: Optional[WebConfig] = None

