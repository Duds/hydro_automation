"""FastAPI application and routes for web UI."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .models import (
    StatusResponse,
    DeviceInfoResponse,
    LogResponse,
    ConfigResponse,
    CycleConfigUpdate,
    ScheduleConfigUpdate,
    ControlResponse
)


class WebAPI:
    """Web API server for hydroponic controller."""

    def __init__(self, controller, host: str = "0.0.0.0", port: int = 8000):
        """
        Initialise the web API.

        Args:
            controller: HydroController instance
            host: Host to bind to
            port: Port to listen on
        """
        self.controller = controller
        self.host = host
        self.port = port
        self.app = FastAPI(title="Hydroponic Controller API")
        self.server = None
        self.thread: Optional[threading.Thread] = None
        
        self._setup_routes()

    def _setup_routes(self):
        """Set up all API routes."""
        
        # Static files
        static_path = Path(__file__).parent / "static"
        if static_path.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # Root - serve index.html
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            index_path = Path(__file__).parent / "static" / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return HTMLResponse("<h1>Hydroponic Controller API</h1><p>Web UI not found</p>")

        # Status & Monitoring
        @self.app.get("/api/status", response_model=StatusResponse)
        async def get_status():
            """Get current system status."""
            try:
                scheduler = self.controller.scheduler
                if not scheduler:
                    raise HTTPException(status_code=404, detail="Scheduler not initialised")

                # Use unified scheduler interface
                scheduler_status = scheduler.get_status()
                scheduler_running = scheduler.is_running()
                scheduler_state = scheduler.get_state()

                # Get primary device from device registry
                growing_system = self.controller.config.get("growing_system", {})
                primary_device_id = growing_system.get("primary_device_id")
                device = None
                device_connected = False
                device_state = None
                device_ip = None

                if primary_device_id and self.controller.device_registry:
                    device = self.controller.device_registry.get_device(primary_device_id)
                    if device:
                        device_connected = device.is_connected()
                        device_state = device.is_device_on()
                        device_info = device.get_device_info()
                        device_ip = device_info.ip_address

                # Get next event time from scheduler status (next_event or next_event_time)
                next_event = scheduler_status.get("next_event") or scheduler_status.get(
                    "next_event_time"
                )
                time_until_next_cycle = None
                if next_event:
                    try:
                        next_dt = datetime.fromisoformat(next_event.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)
                        delta = next_dt - now
                        seconds_until = delta.total_seconds()
                        
                        # Format time until next cycle in human-readable format
                        hours = int(seconds_until // 3600)
                        minutes = int((seconds_until % 3600) // 60)
                        seconds = int(seconds_until % 60)
                        
                        if hours > 0:
                            time_until_next_cycle = f"{hours}h {minutes}m"
                        elif minutes > 0:
                            time_until_next_cycle = f"{minutes}m {seconds}s"
                        else:
                            time_until_next_cycle = f"{seconds}s"
                    except Exception:
                        pass

                # Timed operation (pump on for N minutes then auto-off)
                timed_off_at = None
                time_until_timed_off = None
                gate = getattr(self.controller, "timed_operation_gate", None)
                if gate and gate.is_running():
                    timed_off_at = gate.get_off_at()
                    if timed_off_at:
                        try:
                            off_dt = datetime.fromisoformat(
                                timed_off_at.replace("Z", "+00:00")
                            )
                            now = datetime.now(timezone.utc)
                            if off_dt.tzinfo is None:
                                off_dt = off_dt.replace(tzinfo=timezone.utc)
                            delta = off_dt - now
                            secs = int(max(0, delta.total_seconds()))
                            mins, secs = divmod(secs, 60)
                            if mins > 0:
                                time_until_timed_off = f"{mins}m {secs}s"
                            else:
                                time_until_timed_off = f"{secs}s"
                        except Exception:
                            pass

                return StatusResponse(
                    controller_running=not self.controller.shutdown_requested,
                    scheduler_running=scheduler_running,
                    scheduler_state=scheduler_state,
                    scheduler_mode=scheduler_status.get("scheduler_type", "interval"),
                    device_connected=device_connected,
                    device_state=device_state,
                    device_ip=device_ip,
                    next_event=next_event,
                    next_event_time=next_event,
                    time_until_next_cycle=time_until_next_cycle,
                    timed_off_at=timed_off_at,
                    time_until_timed_off=time_until_timed_off,
                    current_time_period=None
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

        @self.app.get("/api/logs", response_model=LogResponse)
        async def get_logs(lines: int = 100):
            """Get recent log entries."""
            try:
                log_config = self.controller.config.get("logging", {})
                log_file = log_config.get("log_file", "logs/hydro_controller.log")
                log_path = Path(log_file)
                
                if not log_path.exists():
                    return LogResponse(logs=[], total_lines=0)
                
                # Read last N lines
                with open(log_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                return LogResponse(
                    logs=[line.rstrip() for line in recent_lines],
                    total_lines=len(all_lines)
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

        @self.app.get("/api/config", response_model=ConfigResponse)
        async def get_config():
            """Get current configuration (sanitised)."""
            try:
                config = self.controller.config.copy()
                
                # Sanitise - remove passwords from devices
                if "devices" in config and "devices" in config["devices"]:
                    devices_list = config["devices"]["devices"]
                    for device_config in devices_list:
                        if "password" in device_config:
                            device_config["password"] = "***"
                
                return ConfigResponse(
                    cycle={},
                    schedule=config.get("schedule", {}),
                    web=config.get("web", {})
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")

        @self.app.get("/api/device/info", response_model=DeviceInfoResponse)
        async def get_device_info():
            """Get device information."""
            try:
                growing_system = self.controller.config.get("growing_system", {})
                primary_device_id = growing_system.get("primary_device_id")

                if not primary_device_id or not self.controller.device_registry:
                    raise HTTPException(status_code=404, detail="Device not found")

                device = self.controller.device_registry.get_device(primary_device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found in registry")

                device_info = device.get_device_info()
                return DeviceInfoResponse(
                    ip_address=device_info.ip_address or "",
                    connected=device.is_connected(),
                    state=device.is_device_on()
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting device info: {str(e)}")

        # Control endpoints
        @self.app.post("/api/control/start", response_model=ControlResponse)
        async def start_scheduler():
            """Start the scheduler."""
            try:
                scheduler = self.controller.scheduler
                if not scheduler:
                    raise HTTPException(status_code=404, detail="Scheduler not initialised")
                
                if scheduler.is_running():
                    return ControlResponse(success=False, message="Scheduler is already running")
                
                scheduler.start()
                return ControlResponse(success=True, message="Scheduler started")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error starting scheduler: {str(e)}")

        @self.app.post("/api/control/stop", response_model=ControlResponse)
        async def stop_scheduler():
            """Stop the scheduler."""
            try:
                scheduler = self.controller.scheduler
                if not scheduler:
                    raise HTTPException(status_code=404, detail="Scheduler not initialised")
                
                if not scheduler.is_running():
                    return ControlResponse(success=False, message="Scheduler is not running")
                
                scheduler.stop()
                return ControlResponse(success=True, message="Scheduler stopped")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error stopping scheduler: {str(e)}")

        @self.app.post("/api/device/on", response_model=ControlResponse)
        async def turn_device_on():
            """Manually turn device ON."""
            try:
                growing_system = self.controller.config.get("growing_system", {})
                primary_device_id = growing_system.get("primary_device_id")

                if not primary_device_id or not self.controller.device_registry:
                    raise HTTPException(status_code=404, detail="Device not found")

                device = self.controller.device_registry.get_device(primary_device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found in registry")

                success = device.turn_on(verify=True)
                if success:
                    return ControlResponse(success=True, message="Device turned ON")
                else:
                    return ControlResponse(success=False, message="Failed to turn device ON")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error turning device on: {str(e)}")

        @self.app.post("/api/device/on-timed", response_model=ControlResponse)
        async def turn_device_on_timed(request: Request):
            """Turn pump ON for a specified duration, then automatically turn OFF."""
            try:
                from ..core.timed_operation import TimedOperationBusyError

                body = await request.json()
                duration_minutes = float(body.get("duration_minutes", 0))

                if duration_minutes <= 0 or duration_minutes > 60:
                    raise HTTPException(
                        status_code=400,
                        detail="duration_minutes must be > 0 and <= 60",
                    )

                off_at_iso = self.controller.device_on_timed(duration_minutes)
                return ControlResponse(
                    success=True,
                    message=f"Pump turned ON for {duration_minutes} minutes. "
                    f"Will turn OFF at {off_at_iso} UTC.",
                    off_at_iso=off_at_iso,
                )
            except TimedOperationBusyError as e:
                raise HTTPException(status_code=409, detail=str(e))
            except (ValueError, KeyError) as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Error starting timed operation: {str(e)}"
                )

        @self.app.post("/api/device/off", response_model=ControlResponse)
        async def turn_device_off():
            """Manually turn device OFF."""
            try:
                growing_system = self.controller.config.get("growing_system", {})
                primary_device_id = growing_system.get("primary_device_id")

                if not primary_device_id or not self.controller.device_registry:
                    raise HTTPException(status_code=404, detail="Device not found")

                device = self.controller.device_registry.get_device(primary_device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found in registry")

                success = device.turn_off(verify=True)
                if success:
                    return ControlResponse(success=True, message="Device turned OFF")
                else:
                    return ControlResponse(success=False, message="Failed to turn device OFF")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error turning device off: {str(e)}")

        # Configuration endpoints
        @self.app.get("/api/config/schedule")
        async def get_schedule_config():
            """Get schedule configuration."""
            try:
                return self.controller.config.get("schedule", {}).copy()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting schedule config: {str(e)}")

        @self.app.put("/api/config/schedule", response_model=ControlResponse)
        async def update_schedule_config(request: Request):
            """Update schedule configuration."""
            try:
                body = await request.json()
                update_dict = body
                
                config = self.controller.config
                schedule_config = config.get("schedule", {}).copy()
                
                # Handle cycles if present
                if "cycles" in update_dict:
                    cycles_list = []
                    for cycle in update_dict["cycles"]:
                        cycles_list.append({
                            "on_time": cycle.get("on_time"),
                            "off_duration_minutes": float(cycle.get("off_duration_minutes", 0))
                        })
                    
                    # Sort cycles by on_time
                    def parse_time_for_sort(time_str):
                        parts = time_str.split(":")
                        return int(parts[0]) * 60 + int(parts[1])
                    
                    cycles_list.sort(key=lambda c: parse_time_for_sort(c["on_time"]))
                    update_dict["cycles"] = cycles_list
                
                # Replace instead of update to avoid merging keys when switching types
                config["schedule"] = update_dict

                # Apply interval change to running interval scheduler immediately
                scheduler = self.controller.scheduler
                if (
                    scheduler
                    and scheduler.is_running()
                    and "interval_minutes" in update_dict
                ):
                    from ..schedulers.interval_scheduler import IntervalScheduler

                    if isinstance(scheduler, IntervalScheduler):
                        scheduler.update_interval_minutes(
                            float(update_dict["interval_minutes"])
                        )

                # Save to file
                with open(self.controller.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)

                return ControlResponse(
                    success=True,
                    message="Schedule configuration updated. Restart required for changes to take effect."
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error updating schedule config: {str(e)}")

    def start(self):
        """Start the web server in a background thread."""
        import uvicorn
        
        def run_server():
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning"
            )
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the web server."""
        pass
