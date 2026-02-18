from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union


class DeviceConfig(BaseModel):
    """Configuration for a single device."""
    device_id: str
    name: str
    brand: str = "tapo"  # 'tapo'
    type: str = "power_controller"  # 'power_controller'
    ip_address: str
    email: Optional[str] = None
    password: Optional[str] = None
    auto_discovery: bool = True
    config: Optional[Dict[str, Any]] = None


class DevicesConfig(BaseModel):
    """Configuration for multiple devices."""
    devices: List[DeviceConfig]


class CycleDefinition(BaseModel):
    """Single cycle definition for time-based scheduling."""
    on_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    off_duration_minutes: float


class TimeBasedScheduleConfig(BaseModel):
    """Time-based schedule configuration."""
    type: str = "time_based"
    flood_duration_minutes: float
    cycles: List[CycleDefinition]


class IntervalScheduleConfig(BaseModel):
    """Interval-based schedule configuration."""
    type: str = "interval"
    enabled: bool = True
    flood_duration_minutes: float
    drain_duration_minutes: float
    interval_minutes: float
    active_hours: Optional[Dict[str, str]] = None


# Union type for schedule config
ScheduleConfig = Union[TimeBasedScheduleConfig, IntervalScheduleConfig]


class GrowingSystemConfig(BaseModel):
    """Growing system configuration."""
    type: str = "flood_drain"  # 'flood_drain'
    primary_device_id: str  # Main power controller device ID
    config: Optional[Dict[str, Any]] = None


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
    growing_system: GrowingSystemConfig
    schedule: Dict[str, Any]  # Schedule config (validated separately based on type)
    logging: LoggingConfig
    web: Optional[WebConfig] = None


