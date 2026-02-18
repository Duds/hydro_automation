"""Pydantic models for API requests and responses."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StatusResponse(BaseModel):
    """System status response."""
    controller_running: bool
    scheduler_running: bool
    scheduler_state: str
    scheduler_mode: Optional[str]  # "adaptive" or "scheduled"
    device_connected: bool
    device_state: Optional[bool]  # True = ON, False = OFF, None = unknown
    device_ip: Optional[str]
    next_event: Optional[str]  # ISO 8601 UTC timestamp of next scheduled flood cycle, or null
    next_event_time: Optional[str]  # Deprecated: use next_event
    time_until_next_cycle: Optional[str]  # Human-readable format like "2h 15m" or "45m 30s"
    timed_off_at: Optional[str]  # ISO 8601 UTC timestamp when timed pump-on turns off, or null
    time_until_timed_off: Optional[str]  # Human-readable e.g. "1m 45s" when timed op running
    current_time_period: Optional[str]  # "morning", "day", "evening", or "night"


class DeviceInfoResponse(BaseModel):
    """Device information response."""
    ip_address: str
    connected: bool
    state: Optional[bool]


class LogResponse(BaseModel):
    """Log entries response."""
    logs: List[str]
    total_lines: int


class ConfigResponse(BaseModel):
    """Configuration response (sanitised)."""
    cycle: Dict[str, Any]
    schedule: Dict[str, Any]
    web: Optional[Dict[str, Any]] = None


class CycleConfigUpdate(BaseModel):
    """Cycle configuration update request."""
    flood_duration_minutes: Optional[float] = None
    drain_duration_minutes: Optional[float] = None
    interval_minutes: Optional[float] = None


class Cycle(BaseModel):
    """Single cycle definition."""
    on_time: str
    off_duration_minutes: float


class ScheduleConfigUpdate(BaseModel):
    """Schedule configuration update request."""
    type: Optional[str] = None  # "interval" or "time_based"
    enabled: Optional[bool] = None
    active_hours: Optional[Dict[str, str]] = None
    on_times: Optional[List[str]] = None  # Legacy format
    cycles: Optional[List[Cycle]] = None  # New format with variable OFF durations
    flood_duration_minutes: Optional[float] = None


class ControlResponse(BaseModel):
    """Control action response."""
    success: bool
    message: str
    off_at_iso: Optional[str] = None  # For timed on: UTC ISO 8601 when pump turns off

