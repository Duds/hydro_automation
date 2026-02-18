#!/usr/bin/env python3
"""
MCP Server for Hydroponic Flood & Drain Controller.

A thin monitoring and control interface that talks to the running
HydroController daemon via its FastAPI web API (localhost:8000).

IMPORTANT: This MCP server does NOT own or manage the scheduler.
The daemon (src.main) owns the scheduler and must be running
independently. The MCP server is a supporting interface only —
if it crashes or stops, the scheduler keeps running unaffected.

Environment Variables:
    HYDRO_API_URL: Base URL of the running daemon API (default: http://localhost:8000)
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("HYDRO_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 10.0

# ---------------------------------------------------------------------------
# FastMCP server — stateless HTTP client, no lifespan needed
# ---------------------------------------------------------------------------

mcp = FastMCP("hydro_mcp")

# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------


async def _get(endpoint: str) -> Dict[str, Any]:
    """Make a GET request to the daemon API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def _post(endpoint: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make a POST request to the daemon API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}{endpoint}",
            json=json,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def _put(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make a PUT request to the daemon API."""
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}{endpoint}",
            json=data,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


def _format_next_event_local(iso_utc: Optional[str]) -> Optional[str]:
    """Format ISO 8601 UTC timestamp as local time string (Australia/Sydney).

    Returns e.g. '16:26 today' or '09:15 tomorrow'.
    """
    if not iso_utc:
        return None
    try:
        dt_utc = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        local = dt_utc.astimezone(ZoneInfo("Australia/Sydney"))
        today = datetime.now(ZoneInfo("Australia/Sydney")).date()
        if local.date() == today:
            return local.strftime("%H:%M today")
        elif local.date().toordinal() == today.toordinal() + 1:
            return local.strftime("%H:%M tomorrow")
        else:
            return local.strftime("%H:%M %d/%m/%Y")
    except (ValueError, TypeError):
        return None


def _daemon_error(e: Exception) -> str:
    """Return a clear error message when the daemon is unreachable."""
    if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout)):
        return (
            f"Error: Cannot reach the hydroponic controller daemon at {API_BASE_URL}. "
            "Make sure the daemon is running: python -m src.main"
        )
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: Daemon returned HTTP {e.response.status_code} — {e.response.text}"
    if isinstance(e, httpx.TimeoutException):
        return f"Error: Request timed out after {REQUEST_TIMEOUT}s. The daemon may be busy."
    return f"Error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------


class GetLogsInput(BaseModel):
    """Input for retrieving log entries."""
    model_config = ConfigDict(str_strip_whitespace=True)

    lines: int = Field(
        default=50,
        description="Number of recent log lines to return (1–500)",
        ge=1,
        le=500,
    )


class UpdateScheduleInput(BaseModel):
    """Input for updating the schedule configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)

    type: Optional[str] = Field(
        default=None,
        description="Schedule type: 'interval' or 'time_based'",
    )
    flood_duration_minutes: Optional[float] = Field(
        default=None,
        description="Duration to keep the pump ON per cycle (minutes)",
        gt=0,
    )
    drain_duration_minutes: Optional[float] = Field(
        default=None,
        description="Drain phase duration — interval mode only (minutes)",
        gt=0,
    )
    interval_minutes: Optional[float] = Field(
        default=None,
        description="Time between cycles — interval mode only (minutes)",
        gt=0,
    )
    active_hours_start: Optional[str] = Field(
        default=None,
        description="Start of active hours in HH:MM 24-hour format (e.g. '06:00')",
    )
    active_hours_end: Optional[str] = Field(
        default=None,
        description="End of active hours in HH:MM 24-hour format (e.g. '22:00')",
    )
    cycles: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description=(
            "Cycle definitions for time_based mode. "
            "Each dict has 'on_time' (HH:MM) and 'off_duration_minutes' (float)."
        ),
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("interval", "time_based"):
            raise ValueError("type must be 'interval' or 'time_based'")
        return v


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="hydro_get_status",
    annotations={
        "title": "Get System Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_get_status() -> str:
    """Get the current hydroponic system status.

    Returns a Markdown summary including scheduler state, device connection
    and power state, and the next scheduled event time.

    Returns:
        str: Markdown-formatted status report.
    """
    try:
        data = await _get("/api/status")
    except Exception as e:
        return _daemon_error(e)

    scheduler_running = data.get("scheduler_running", False)
    scheduler_state = data.get("scheduler_state", "unknown")
    scheduler_mode = data.get("scheduler_mode", "unknown")
    device_connected = data.get("device_connected", False)
    device_state = data.get("device_state")
    device_ip = data.get("device_ip", "unknown")
    next_event_iso = data.get("next_event") or data.get("next_event_time")
    next_event_local = _format_next_event_local(next_event_iso)
    time_until = data.get("time_until_next_cycle", "")

    if device_state is True:
        state_str = "ON"
    elif device_state is False:
        state_str = "OFF"
    else:
        state_str = "UNKNOWN"

    lines = [
        "# Hydroponic System Status",
        "",
        f"- **Scheduler**: {'running' if scheduler_running else 'stopped'} ({scheduler_mode} mode, state: {scheduler_state})",
        f"- **Device**: {state_str} — {'connected' if device_connected else 'disconnected'}",
        f"- **Device IP**: {device_ip}",
    ]
    if next_event_local:
        suffix = f" (in {time_until})" if time_until else ""
        lines.append(f"- **Next flood**: {next_event_local}{suffix}")
    else:
        lines.append("- **Next flood**: none scheduled")

    timed_off_iso = data.get("timed_off_at")
    if timed_off_iso:
        timed_off_local = _format_next_event_local(timed_off_iso)
        time_until_timed = data.get("time_until_timed_off", "")
        suffix = f" (in {time_until_timed})" if time_until_timed else ""
        lines.append(f"- **Timed off at**: {timed_off_local}{suffix}")

    return "\n".join(lines)


@mcp.tool(
    name="hydro_get_device_info",
    annotations={
        "title": "Get Device Info",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_get_device_info() -> str:
    """Get information about the primary Tapo P100 device.

    Returns:
        str: JSON with device id, name, ip_address, connected, state.
    """
    try:
        data = await _get("/api/device/info")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_get_logs",
    annotations={
        "title": "Get Recent Logs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_get_logs(params: GetLogsInput) -> str:
    """Retrieve the most recent log entries from the controller.

    Args:
        params (GetLogsInput):
            - lines (int): Number of recent lines to return, 1–500 (default 50).

    Returns:
        str: Log lines or an error message.
    """
    try:
        data = await _get(f"/api/logs?lines={params.lines}")
        logs = data.get("logs", [])
        if not logs:
            return "No log entries found."
        return "\n".join(logs)
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_get_config",
    annotations={
        "title": "Get Configuration",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_get_config() -> str:
    """Get the current controller configuration with passwords redacted.

    Returns:
        str: JSON-formatted configuration.
    """
    try:
        data = await _get("/api/config")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_get_schedule",
    annotations={
        "title": "Get Schedule",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_get_schedule() -> str:
    """Get the current schedule configuration.

    Returns:
        str: JSON-formatted schedule configuration.
    """
    try:
        data = await _get("/api/config/schedule")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _daemon_error(e)


# ---------------------------------------------------------------------------
# Control tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="hydro_device_on",
    annotations={
        "title": "Turn Pump ON",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_device_on() -> str:
    """Manually turn the pump ON via the daemon.

    Returns:
        str: Success or failure message.
    """
    try:
        data = await _post("/api/device/on")
        return data.get("message", "Done.")
    except Exception as e:
        return _daemon_error(e)


class DeviceOnTimedInput(BaseModel):
    """Input for turning pump ON for a specified duration."""
    model_config = ConfigDict(str_strip_whitespace=True)

    duration_minutes: float = Field(
        gt=0,
        le=60,
        description="Duration to keep the pump ON in minutes (1–60)",
    )


@mcp.tool(
    name="hydro_device_on_timed",
    annotations={
        "title": "Turn Pump ON (Timed)",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def hydro_device_on_timed(params: DeviceOnTimedInput) -> str:
    """Turn the pump ON for a specified duration, then automatically turn it OFF.

    Args:
        params (DeviceOnTimedInput): duration_minutes (float, 1–60).

    Returns:
        str: Confirmation message including scheduled off time in Australia/Sydney.
    """
    try:
        data = await _post(
            "/api/device/on-timed",
            json={"duration_minutes": params.duration_minutes},
        )
        msg = data.get("message", "Pump turned ON for specified duration.")
        off_at_iso = data.get("off_at_iso")
        if off_at_iso:
            off_local = _format_next_event_local(off_at_iso)
            return f"{msg} Scheduled off time: {off_local} (Australia/Sydney)."
        return msg
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return "Error: A timed operation is already running. Wait for it to complete."
        return _daemon_error(e)
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_device_off",
    annotations={
        "title": "Turn Pump OFF",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_device_off() -> str:
    """Manually turn the pump OFF via the daemon.

    Returns:
        str: Success or failure message.
    """
    try:
        data = await _post("/api/device/off")
        return data.get("message", "Done.")
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_scheduler_start",
    annotations={
        "title": "Start Scheduler",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_scheduler_start() -> str:
    """Start the flood/drain scheduler on the daemon.

    Returns:
        str: Status message.
    """
    try:
        data = await _post("/api/control/start")
        return data.get("message", "Done.")
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_scheduler_stop",
    annotations={
        "title": "Stop Scheduler",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hydro_scheduler_stop() -> str:
    """Stop the flood/drain scheduler on the daemon.

    Returns:
        str: Status message.
    """
    try:
        data = await _post("/api/control/stop")
        return data.get("message", "Done.")
    except Exception as e:
        return _daemon_error(e)


@mcp.tool(
    name="hydro_update_schedule",
    annotations={
        "title": "Update Schedule",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def hydro_update_schedule(params: UpdateScheduleInput) -> str:
    """Update the schedule configuration on the daemon and save to disk.

    Args:
        params (UpdateScheduleInput): Fields to update (only non-None fields applied).

    Returns:
        str: Confirmation message or error.
    """
    updates = params.model_dump(exclude_none=True)
    if not updates:
        return "No schedule fields provided to update."

    try:
        current = await _get("/api/config/schedule")
        current.update(updates)
        data = await _put("/api/config/schedule", current)
        return data.get("message", "Schedule updated.")
    except Exception as e:
        return _daemon_error(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
