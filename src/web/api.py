"""FastAPI application and routes for web UI."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
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
                device = self.controller.controller
                
                # Handle adaptive scheduler wrapper
                base_scheduler = scheduler
                if hasattr(scheduler, 'base_scheduler'):
                    base_scheduler = scheduler.base_scheduler
                
                scheduler_running = scheduler.is_running() if scheduler else False
                scheduler_state = scheduler.get_state() if scheduler else "idle"
                device_connected = device.is_connected() if device else False
                device_state = device.is_device_on() if device_connected else None
                device_ip = device.ip_address if device else None
                
                # Calculate next event time (simplified - would need scheduler-specific logic)
                next_event_time = None
                if scheduler_running and base_scheduler:
                    # Try to get next event time for TimeScheduler
                    try:
                        from datetime import time as dt_time
                        if hasattr(base_scheduler, '_get_next_on_time') and hasattr(base_scheduler, '_time_until_next_event'):
                            now_time = datetime.now().time()
                            next_time = base_scheduler._get_next_on_time(now_time)
                            if next_time:
                                seconds_until = base_scheduler._time_until_next_event(next_time)
                                next_dt = datetime.now().timestamp() + seconds_until
                                next_event_time = datetime.fromtimestamp(next_dt).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        # If we can't calculate next event time, leave it as None
                        pass
                
                return StatusResponse(
                    controller_running=not self.controller.shutdown_requested,
                    scheduler_running=scheduler_running,
                    scheduler_state=scheduler_state,
                    device_connected=device_connected,
                    device_state=device_state,
                    device_ip=device_ip,
                    next_event_time=next_event_time
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

        @self.app.get("/api/environment")
        async def get_environment():
            """Get environmental data (temperature, sunrise/sunset)."""
            try:
                schedule_config = self.controller.config.get("schedule", {})
                adaptation_config = schedule_config.get("adaptation", {})
                
                result = {
                    "temperature": None,
                    "temperature_source": None,
                    "sunrise": None,
                    "sunset": None,
                    "adaptation_enabled": adaptation_config.get("enabled", False)
                }
                
                # Get temperature if adaptation is enabled
                if adaptation_config.get("enabled", False):
                    temp_config = adaptation_config.get("temperature", {})
                    if temp_config.get("enabled", False):
                        # Try to get temperature from adaptive scheduler
                        if hasattr(self.controller.scheduler, 'temperature_fetcher'):
                            temp_fetcher = self.controller.scheduler.temperature_fetcher
                            if temp_fetcher:
                                result["temperature"] = temp_fetcher.last_temperature
                                result["temperature_source"] = f"BOM Station {temp_fetcher.station_id}"
                                result["temperature_last_update"] = (
                                    temp_fetcher.last_update.isoformat() if temp_fetcher.last_update else None
                                )
                    
                    # Get sunrise/sunset if daylight adaptation is enabled
                    daylight_config = adaptation_config.get("daylight", {})
                    if daylight_config.get("enabled", False):
                        if hasattr(self.controller.scheduler, 'daylight_calc'):
                            daylight_calc = self.controller.scheduler.daylight_calc
                            if daylight_calc:
                                sunrise, sunset = daylight_calc.get_sunrise_sunset()
                                if sunrise:
                                    result["sunrise"] = sunrise.strftime("%H:%M")
                                if sunset:
                                    result["sunset"] = sunset.strftime("%H:%M")
                
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting environment data: {str(e)}")

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
                
                # Sanitise - remove passwords
                if "device" in config:
                    device_config = config["device"].copy()
                    if "password" in device_config:
                        device_config["password"] = "***"
                    config["device"] = device_config
                
                return ConfigResponse(
                    cycle=config.get("cycle", {}),
                    schedule=config.get("schedule", {}),
                    web=config.get("web", {})
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")

        @self.app.get("/api/device/info", response_model=DeviceInfoResponse)
        async def get_device_info():
            """Get device information."""
            try:
                device = self.controller.controller
                if not device:
                    raise HTTPException(status_code=404, detail="Device controller not initialised")
                
                return DeviceInfoResponse(
                    ip_address=device.ip_address,
                    connected=device.is_connected(),
                    state=device.is_device_on()
                )
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
                device = self.controller.controller
                if not device:
                    raise HTTPException(status_code=404, detail="Device controller not initialised")
                
                if not device.is_connected():
                    raise HTTPException(status_code=503, detail="Device not connected")
                
                success = device.turn_on(verify=True)
                if success:
                    return ControlResponse(success=True, message="Device turned ON")
                else:
                    return ControlResponse(success=False, message="Failed to turn device ON")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error turning device on: {str(e)}")

        @self.app.post("/api/device/off", response_model=ControlResponse)
        async def turn_device_off():
            """Manually turn device OFF."""
            try:
                device = self.controller.controller
                if not device:
                    raise HTTPException(status_code=404, detail="Device controller not initialised")
                
                if not device.is_connected():
                    raise HTTPException(status_code=503, detail="Device not connected")
                
                success = device.turn_off(verify=True)
                if success:
                    return ControlResponse(success=True, message="Device turned OFF")
                else:
                    return ControlResponse(success=False, message="Failed to turn device OFF")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error turning device off: {str(e)}")

        @self.app.get("/api/device/state")
        async def get_device_state():
            """Get current device state."""
            try:
                device = self.controller.controller
                if not device:
                    raise HTTPException(status_code=404, detail="Device controller not initialised")
                
                if not device.is_connected():
                    return {"connected": False, "state": None}
                
                state = device.is_device_on()
                return {"connected": True, "state": state}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting device state: {str(e)}")

        # Configuration endpoints
        @self.app.get("/api/config/schedule")
        async def get_schedule_config():
            """Get schedule configuration."""
            try:
                return self.controller.config.get("schedule", {})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting schedule config: {str(e)}")

        @self.app.put("/api/config/schedule", response_model=ControlResponse)
        async def update_schedule_config(update: ScheduleConfigUpdate):
            """Update schedule configuration."""
            try:
                config = self.controller.config
                schedule_config = config.get("schedule", {})
                
                # Update fields
                update_dict = update.dict(exclude_none=True)
                
                # Handle cycles - convert Pydantic models to dicts
                if "cycles" in update_dict and update_dict["cycles"]:
                    cycles_list = []
                    for cycle in update_dict["cycles"]:
                        if isinstance(cycle, dict):
                            cycles_list.append({
                                "on_time": cycle.get("on_time"),
                                "off_duration_minutes": float(cycle.get("off_duration_minutes", 0))
                            })
                        else:
                            # Pydantic model
                            cycles_list.append({
                                "on_time": cycle.on_time,
                                "off_duration_minutes": float(cycle.off_duration_minutes)
                            })
                    
                    # Validate cycles
                    for cycle in cycles_list:
                        if not cycle["on_time"]:
                            raise ValueError("Each cycle must have an on_time")
                        if cycle["off_duration_minutes"] < 0:
                            raise ValueError("off_duration_minutes must be >= 0")
                    
                    # Sort cycles by on_time
                    def parse_time_for_sort(time_str):
                        parts = time_str.split(":")
                        return int(parts[0]) * 60 + int(parts[1])
                    
                    cycles_list.sort(key=lambda c: parse_time_for_sort(c["on_time"]))
                    update_dict["cycles"] = cycles_list
                
                schedule_config.update(update_dict)
                config["schedule"] = schedule_config
                
                # Save to file
                with open(self.controller.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                
                # Reload config
                self.controller.config = config
                
                return ControlResponse(
                    success=True,
                    message="Schedule configuration updated. Restart required for changes to take effect."
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid schedule configuration: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error updating schedule config: {str(e)}")

        @self.app.get("/api/config/cycle")
        async def get_cycle_config():
            """Get cycle configuration."""
            try:
                return self.controller.config.get("cycle", {})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting cycle config: {str(e)}")

        @self.app.put("/api/config/cycle", response_model=ControlResponse)
        async def update_cycle_config(update: CycleConfigUpdate):
            """Update cycle configuration."""
            try:
                config = self.controller.config
                cycle_config = config.get("cycle", {})
                
                # Update fields
                update_dict = update.dict(exclude_none=True)
                cycle_config.update(update_dict)
                config["cycle"] = cycle_config
                
                # Save to file
                with open(self.controller.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                
                # Reload config
                self.controller.config = config
                
                return ControlResponse(
                    success=True,
                    message="Cycle configuration updated. Restart required for changes to take effect."
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error updating cycle config: {str(e)}")

        # Service management endpoints
        @self.app.get("/api/service/status")
        async def get_service_status():
            """Get daemon and webapp service status."""
            try:
                import subprocess
                
                # Check daemon status
                daemon_running = False
                try:
                    result = subprocess.run(
                        ["launchctl", "list", "com.hydro.controller"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    daemon_running = result.returncode == 0 and "com.hydro.controller" in result.stdout
                except Exception:
                    pass
                
                # Webapp is running if we can respond to this request
                webapp_running = True
                
                return {
                    "daemon_running": daemon_running,
                    "webapp_running": webapp_running
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")

        @self.app.post("/api/service/{service}/{action}", response_model=ControlResponse)
        async def control_service(service: str, action: str):
            """Control daemon or webapp service (start/stop/restart)."""
            try:
                import subprocess
                import os
                
                if service not in ["daemon", "webapp"]:
                    raise HTTPException(status_code=400, detail="Invalid service. Must be 'daemon' or 'webapp'")
                
                if action not in ["start", "stop", "restart"]:
                    raise HTTPException(status_code=400, detail="Invalid action. Must be 'start', 'stop', or 'restart'")
                
                if service == "daemon":
                    # Control launchd daemon
                    plist_name = "com.hydro.controller"
                    
                    if action == "start":
                        result = subprocess.run(
                            ["launchctl", "start", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            return ControlResponse(success=True, message="Daemon started successfully")
                        else:
                            return ControlResponse(success=False, message=f"Failed to start daemon: {result.stderr}")
                    
                    elif action == "stop":
                        result = subprocess.run(
                            ["launchctl", "stop", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            return ControlResponse(success=True, message="Daemon stopped successfully")
                        else:
                            return ControlResponse(success=False, message=f"Failed to stop daemon: {result.stderr}")
                    
                    elif action == "restart":
                        # Stop first
                        subprocess.run(["launchctl", "stop", plist_name], capture_output=True, timeout=5)
                        import time
                        time.sleep(2)
                        # Then start
                        result = subprocess.run(
                            ["launchctl", "start", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            return ControlResponse(success=True, message="Daemon restarted successfully")
                        else:
                            return ControlResponse(success=False, message=f"Failed to restart daemon: {result.stderr}")
                
                elif service == "webapp":
                    # For webapp, we can only stop (graceful shutdown)
                    # Start/restart would require external process management
                    if action == "stop":
                        # Signal the controller to stop web server
                        if hasattr(self.controller, 'web_api'):
                            self.controller.web_api.stop()
                            return ControlResponse(success=True, message="Web app stopped. Restart daemon to start it again.")
                        else:
                            return ControlResponse(success=False, message="Web app not running")
                    elif action == "start":
                        return ControlResponse(success=False, message="Web app start requires daemon restart. Please restart the daemon.")
                    elif action == "restart":
                        return ControlResponse(success=False, message="Web app restart requires daemon restart. Please restart the daemon.")
                
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=500, detail="Service control operation timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error controlling service: {str(e)}")

    def start(self):
        """Start the web server in a background thread."""
        import uvicorn
        
        def run_server():
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning"  # Reduce uvicorn logging
            )
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the web server."""
        # Uvicorn doesn't have a clean shutdown API when run in thread
        # The daemon thread will exit when main process exits
        pass

