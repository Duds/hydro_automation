"""FastAPI application and routes for web UI."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

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
                
                # Calculate next event time and time until next cycle
                next_event_time = None
                time_until_next_cycle = None
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
                        # If we can't calculate next event time, leave it as None
                        pass
                
                # Determine current time period
                current_time_period = None
                try:
                    from datetime import time as dt_time
                    now_time = datetime.now().time()
                    
                    # Check if we have an adaptive scheduler with period detection
                    from ..adaptive_scheduler import AdaptiveScheduler
                    if isinstance(scheduler, AdaptiveScheduler):
                        # Use adaptive scheduler's period detection method
                        sunrise = None
                        sunset = None
                        if hasattr(self.controller, 'daylight_calc') and self.controller.daylight_calc:
                            sunrise, sunset = self.controller.daylight_calc.get_sunrise_sunset()
                        if hasattr(scheduler, '_get_time_period'):
                            current_time_period = scheduler._get_time_period(now_time, sunrise, sunset)
                    else:
                        # Simple period detection based on time of day
                        hour = now_time.hour
                        if 6 <= hour < 9:
                            current_time_period = "morning"
                        elif 9 <= hour < 18:
                            current_time_period = "day"
                        elif 18 <= hour < 20:
                            current_time_period = "evening"
                        else:
                            current_time_period = "night"
                except Exception as e:
                    # If we can't determine period, leave it as None
                    # Log error but don't fail the status endpoint
                    if hasattr(self.controller, 'logger') and self.controller.logger:
                        self.controller.logger.debug(f"Could not determine time period: {e}")
                    pass
                
                return StatusResponse(
                    controller_running=not self.controller.shutdown_requested,
                    scheduler_running=scheduler_running,
                    scheduler_state=scheduler_state,
                    device_connected=device_connected,
                    device_state=device_state,
                    device_ip=device_ip,
                    next_event_time=next_event_time,
                    time_until_next_cycle=time_until_next_cycle,
                    current_time_period=current_time_period
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
                    "humidity": None,
                    "temperature_source": None,
                    "temperature_last_update": None,
                    "sunrise": None,
                    "sunset": None,
                    "adaptation_enabled": adaptation_config.get("enabled", False),
                    "active_adaptive_enabled": adaptation_config.get("active_adaptive", {}).get("enabled", False),
                    "location_configured": False
                }
                
                # Get daylight calculator (from controller or scheduler)
                daylight_calc = None
                if hasattr(self.controller, 'daylight_calc') and self.controller.daylight_calc:
                    daylight_calc = self.controller.daylight_calc
                elif hasattr(self.controller.scheduler, 'daylight_calc') and self.controller.scheduler.daylight_calc:
                    daylight_calc = self.controller.scheduler.daylight_calc
                
                # Get sunrise/sunset
                if daylight_calc:
                    sunrise, sunset = daylight_calc.get_sunrise_sunset()
                    if sunrise:
                        result["sunrise"] = sunrise.strftime("%H:%M")
                    if sunset:
                        result["sunset"] = sunset.strftime("%H:%M")
                    result["location_configured"] = True
                
                # Get temperature fetcher (from controller or scheduler)
                temp_fetcher = None
                if hasattr(self.controller, 'temperature_fetcher') and self.controller.temperature_fetcher:
                    temp_fetcher = self.controller.temperature_fetcher
                elif hasattr(self.controller.scheduler, 'temperature_fetcher') and self.controller.scheduler.temperature_fetcher:
                    temp_fetcher = self.controller.scheduler.temperature_fetcher
                
                # Fetch/update temperature if fetcher is available
                if temp_fetcher:
                    # Check if we need to fetch (if never fetched or stale)
                    temp_config = adaptation_config.get("temperature", {})
                    update_interval = temp_config.get("update_interval_minutes", 60)
                    
                    should_fetch = False
                    if temp_fetcher.last_update is None:
                        should_fetch = True
                    else:
                        from datetime import datetime, timedelta
                        time_since_update = datetime.now() - temp_fetcher.last_update
                        if time_since_update.total_seconds() >= update_interval * 60:
                            should_fetch = True
                    
                    if should_fetch:
                        # Fetch fresh temperature
                        temp_fetcher.fetch_temperature()
                    
                    # Return temperature and humidity data
                    result["temperature"] = temp_fetcher.last_temperature
                    result["humidity"] = temp_fetcher.last_humidity
                    station_display = (
                        f"{temp_fetcher.station_name} ({temp_fetcher.station_id})"
                        if temp_fetcher.station_name
                        else f"Station {temp_fetcher.station_id}"
                    )
                    result["temperature_source"] = f"BOM {station_display}"
                    result["temperature_station_id"] = temp_fetcher.station_id
                    result["temperature_station_name"] = temp_fetcher.station_name
                    result["temperature_last_update"] = (
                        temp_fetcher.last_update.isoformat() if temp_fetcher.last_update else None
                    )
                
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
                schedule_config = self.controller.config.get("schedule", {}).copy()
                
                # Add current environmental data to response
                if hasattr(self.controller, 'daylight_calc') and self.controller.daylight_calc:
                    sunrise, sunset = self.controller.daylight_calc.get_sunrise_sunset()
                    if sunrise:
                        schedule_config["_current_sunrise"] = sunrise.strftime("%H:%M")
                    if sunset:
                        schedule_config["_current_sunset"] = sunset.strftime("%H:%M")
                
                if hasattr(self.controller, 'temperature_fetcher') and self.controller.temperature_fetcher:
                    temp_fetcher = self.controller.temperature_fetcher
                    schedule_config["_current_temperature"] = temp_fetcher.last_temperature
                    schedule_config["_temperature_station_id"] = temp_fetcher.station_id
                    schedule_config["_temperature_station_name"] = temp_fetcher.station_name
                
                return schedule_config
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting schedule config: {str(e)}")

        @self.app.get("/api/config/schedule/adapted")
        async def get_adapted_schedule():
            """Get current adapted schedule cycles when adaptation is enabled."""
            try:
                scheduler = self.controller.scheduler
                
                # Check if scheduler is an ActiveAdaptiveScheduler
                from ..active_adaptive_scheduler import ActiveAdaptiveScheduler
                if isinstance(scheduler, ActiveAdaptiveScheduler):
                    # Get adapted cycles from active adaptive scheduler
                    adapted_cycles = scheduler.get_adapted_cycles()
                    formatted_cycles = []
                    for cycle in adapted_cycles:
                        on_time = cycle.get("on_time")
                        if on_time:
                            if hasattr(on_time, 'strftime'):
                                on_time_str = on_time.strftime("%H:%M")
                            else:
                                on_time_str = str(on_time)
                            
                            formatted_cycles.append({
                                "on_time": on_time_str,
                                "off_duration_minutes": cycle.get("off_duration_minutes", 0),
                                "_period": cycle.get("_period"),
                                "_temp": cycle.get("_temp"),
                                "_humidity": cycle.get("_humidity"),
                                "_temp_factor": cycle.get("_temp_factor"),
                                "_humidity_factor": cycle.get("_humidity_factor")
                            })
                    
                    # Get base cycles for comparison (analytical only)
                    schedule_config = self.controller.config.get("schedule", {})
                    base_cycles = schedule_config.get("cycles", [])
                    
                    return {
                        "adapted": True,
                        "active_adaptive": True,
                        "cycles": formatted_cycles,
                        "base_cycles": base_cycles
                    }
                
                # Check if scheduler is an AdaptiveScheduler (legacy)
                from ..adaptive_scheduler import AdaptiveScheduler
                if isinstance(scheduler, AdaptiveScheduler):
                    # Get adapted cycles from base_scheduler (contains active adapted cycles)
                    base_scheduler = scheduler.base_scheduler
                    if hasattr(base_scheduler, 'cycles') and base_scheduler.cycles:
                        # Format cycles for JSON response
                        adapted_cycles = []
                        for cycle in base_scheduler.cycles:
                            on_time = cycle.get("on_time")
                            if on_time:
                                # Convert time object to string if needed
                                if hasattr(on_time, 'strftime'):
                                    on_time_str = on_time.strftime("%H:%M")
                                else:
                                    on_time_str = str(on_time)
                                
                                adapted_cycles.append({
                                    "on_time": on_time_str,
                                    "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                                })
                        
                        return {
                            "adapted": True,
                            "cycles": adapted_cycles,
                            "base_cycles": scheduler.base_cycles if hasattr(scheduler, 'base_cycles') else []
                        }
                    elif hasattr(scheduler, 'adapted_cycles') and scheduler.adapted_cycles:
                        # Fallback to adapted_cycles if base_scheduler.cycles not available
                        adapted_cycles = []
                        for cycle in scheduler.adapted_cycles:
                            on_time = cycle.get("on_time")
                            if on_time:
                                if hasattr(on_time, 'strftime'):
                                    on_time_str = on_time.strftime("%H:%M")
                                else:
                                    on_time_str = str(on_time)
                                
                                adapted_cycles.append({
                                    "on_time": on_time_str,
                                    "off_duration_minutes": cycle.get("off_duration_minutes", 0)
                                })
                        
                        return {
                            "adapted": True,
                            "active_adaptive": False,
                            "cycles": adapted_cycles,
                            "base_cycles": scheduler.base_cycles if hasattr(scheduler, 'base_cycles') else []
                        }
                
                # Adaptation not enabled or no adapted cycles available
                # Return base cycles
                schedule_config = self.controller.config.get("schedule", {})
                base_cycles = schedule_config.get("cycles", [])
                
                return {
                    "adapted": False,
                    "active_adaptive": False,
                    "cycles": base_cycles,
                    "base_cycles": base_cycles
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting adapted schedule: {str(e)}")

        @self.app.get("/api/config/schedule/active-adaptive")
        async def get_active_adaptive_schedule():
            """Get active adaptive schedule (if enabled)."""
            try:
                scheduler = self.controller.scheduler
                
                from ..active_adaptive_scheduler import ActiveAdaptiveScheduler
                if isinstance(scheduler, ActiveAdaptiveScheduler):
                    adapted_cycles = scheduler.get_adapted_cycles()
                    formatted_cycles = []
                    for cycle in adapted_cycles:
                        on_time = cycle.get("on_time")
                        if on_time:
                            if hasattr(on_time, 'strftime'):
                                on_time_str = on_time.strftime("%H:%M")
                            else:
                                on_time_str = str(on_time)
                            
                            formatted_cycles.append({
                                "on_time": on_time_str,
                                "off_duration_minutes": cycle.get("off_duration_minutes", 0),
                                "period": cycle.get("_period"),
                                "temperature": cycle.get("_temp"),
                                "humidity": cycle.get("_humidity"),
                                "temp_factor": cycle.get("_temp_factor"),
                                "humidity_factor": cycle.get("_humidity_factor")
                            })
                    
                    return {
                        "enabled": True,
                        "cycles": formatted_cycles,
                        "event_count": len(formatted_cycles)
                    }
                
                return {
                    "enabled": False,
                    "cycles": [],
                    "event_count": 0
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting active adaptive schedule: {str(e)}")

        @self.app.get("/api/config/schedule/active-adaptive/validate")
        async def validate_active_adaptive():
            """Compare active adaptive schedule with base schedule (testing only)."""
            try:
                scheduler = self.controller.scheduler
                
                from ..active_adaptive_scheduler import ActiveAdaptiveScheduler
                from ..adaptive_validation import AdaptiveValidator
                
                if not isinstance(scheduler, ActiveAdaptiveScheduler):
                    raise HTTPException(status_code=400, detail="Active adaptive is not enabled")
                
                # Get active adaptive schedule
                active_cycles = scheduler.get_adapted_cycles()
                
                # Get base schedule
                schedule_config = self.controller.config.get("schedule", {})
                base_cycles = schedule_config.get("cycles", [])
                
                if not base_cycles:
                    raise HTTPException(status_code=400, detail="No base schedule available for comparison")
                
                # Validate
                validator = AdaptiveValidator(threshold=0.5)
                comparison = validator.compare_with_base(active_cycles, base_cycles)
                report = validator.generate_validation_report(active_cycles, base_cycles)
                
                return {
                    "comparison": comparison,
                    "report": report,
                    "warnings_count": len(comparison["warnings"]),
                    "deviations_count": len(comparison["deviations"]),
                    "matches_count": len(comparison["matches"])
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error validating active adaptive schedule: {str(e)}")

        @self.app.put("/api/config/schedule", response_model=ControlResponse)
        async def update_schedule_config(request: Request):
            """Update schedule configuration."""
            try:
                # Get raw JSON from request body
                body = await request.json()
                update_dict = body
                
                config = self.controller.config
                schedule_config = config.get("schedule", {})
                adaptation_config = schedule_config.get("adaptation", {})
                adaptation_enabled = adaptation_config.get("enabled", False)
                
                # Check if adaptation is enabled and user is trying to modify schedule (not just adaptation config)
                if adaptation_enabled:
                    # Allow adaptation config updates, but block schedule changes
                    if "cycles" in update_dict or "on_times" in update_dict or "flood_duration_minutes" in update_dict:
                        raise HTTPException(
                            status_code=403,
                            detail="Schedule editing is disabled when adaptation is enabled. "
                                   "Disable adaptation first to modify the schedule manually."
                        )
                
                # Handle cycles if present
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
                
                # Handle adaptation config if present
                if "adaptation" in update_dict:
                    schedule_config["adaptation"] = update_dict["adaptation"]
                    # Remove from update_dict so it doesn't overwrite
                    del update_dict["adaptation"]
                
                # Update other fields
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
                    plist_file = os.path.expanduser(f"~/Library/LaunchAgents/{plist_name}.plist")
                    
                    if action == "start":
                        # Check if plist exists
                        if not os.path.exists(plist_file):
                            return ControlResponse(success=False, message=f"Daemon plist not found at {plist_file}. Please install the daemon first.")
                        
                        # Check if already loaded
                        check_result = subprocess.run(
                            ["launchctl", "list", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        # If not loaded, load it first
                        if check_result.returncode != 0:
                            load_result = subprocess.run(
                                ["launchctl", "load", plist_file],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if load_result.returncode != 0:
                                return ControlResponse(success=False, message=f"Failed to load daemon: {load_result.stderr}")
                        
                        # Start the service
                        result = subprocess.run(
                            ["launchctl", "start", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            return ControlResponse(success=True, message="Daemon started successfully")
                        else:
                            # launchctl start can return 0 even if service is already running
                            # Check if it's actually running
                            check_result = subprocess.run(
                                ["launchctl", "list", plist_name],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if check_result.returncode == 0:
                                return ControlResponse(success=True, message="Daemon is running")
                            return ControlResponse(success=False, message=f"Failed to start daemon: {result.stderr}")
                    
                    elif action == "stop":
                        result = subprocess.run(
                            ["launchctl", "stop", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        # launchctl stop returns 0 even if service is not running
                        # Check if it's actually stopped
                        import time
                        time.sleep(1)
                        check_result = subprocess.run(
                            ["launchctl", "list", plist_name],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if check_result.returncode != 0:
                            return ControlResponse(success=True, message="Daemon stopped successfully")
                        else:
                            # Service might still be listed but stopped
                            return ControlResponse(success=True, message="Daemon stop command executed")
                    
                    elif action == "restart":
                        # Stop first
                        subprocess.run(["launchctl", "stop", plist_name], capture_output=True, timeout=5)
                        import time
                        time.sleep(2)
                        
                        # Check if plist exists and load if needed
                        if os.path.exists(plist_file):
                            check_result = subprocess.run(
                                ["launchctl", "list", plist_name],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if check_result.returncode != 0:
                                # Not loaded, load it
                                subprocess.run(["launchctl", "load", plist_file], capture_output=True, timeout=5)
                        
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

        # BOM Station endpoints
        @self.app.get("/api/bom/stations")
        async def get_bom_stations(q: Optional[str] = None):
            """Get all BOM stations or search by query."""
            try:
                from ..bom_stations import get_all_stations, search_stations
                
                if q:
                    stations = search_stations(q)
                else:
                    stations = get_all_stations()
                
                return {"stations": stations, "total": len(stations)}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting BOM stations: {str(e)}")

        @self.app.get("/api/bom/stations/{station_id}")
        async def get_bom_station(station_id: str):
            """Get BOM station information by ID."""
            try:
                from ..bom_stations import get_station_info
                
                info = get_station_info(station_id)
                if not info:
                    raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
                
                name, lat, lon, state = info
                return {
                    "id": station_id,
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "state": state
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting station info: {str(e)}")

        @self.app.get("/api/bom/nearest-station")
        async def get_nearest_station(postcode: Optional[str] = None):
            """Find nearest BOM station from postcode."""
            try:
                if not postcode:
                    raise HTTPException(status_code=400, detail="Postcode parameter required")
                
                # Convert postcode to lat/long
                import pgeocode
                import pandas as pd
                
                nomi = pgeocode.Nominatim('au')  # 'au' for Australia
                location_data = nomi.query_postal_code(postcode)
                
                if location_data is None or location_data.empty:
                    raise HTTPException(status_code=404, detail=f"Postcode {postcode} not found")
                
                latitude = location_data['latitude']
                longitude = location_data['longitude']
                
                if pd.isna(latitude) or pd.isna(longitude):
                    raise HTTPException(status_code=404, detail=f"Could not get coordinates for postcode {postcode}")
                
                # Find nearest station
                from ..bom_stations import find_nearest_station
                
                result = find_nearest_station(float(latitude), float(longitude))
                if not result:
                    raise HTTPException(status_code=404, detail="No BOM stations found")
                
                station_id, station_name, distance_km = result
                
                return {
                    "station_id": station_id,
                    "station_name": station_name,
                    "distance_km": round(distance_km, 1),
                    "postcode": postcode,
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error finding nearest station: {str(e)}")

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

