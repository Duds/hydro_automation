"""Main application entry point."""

import json
import signal
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from .logger import setup_logger
from .scheduler import CycleScheduler
from .time_scheduler import TimeScheduler
from .tapo_controller import TapoController


class HydroController:
    """Main application controller."""

    def __init__(self, config_path: str):
        """
        Initialise the hydroponic controller.

        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.logger = None
        self.controller: TapoController = None
        self.scheduler: CycleScheduler = None
        self.shutdown_requested = False
        self.web_api = None
        self.daylight_calc = None  # Daylight calculator instance
        self.temperature_fetcher = None  # BOM temperature fetcher instance

        # Load configuration
        self._load_config()

        # Setup logger
        log_config = self.config.get("logging", {})
        log_file = log_config.get("log_file", "logs/hydro_controller.log")
        log_level = log_config.get("log_level", "INFO")
        self.logger = setup_logger(log_file, log_level)

        # Initialise device controller
        self._init_controller()

        # Initialise environmental data sources (for API access)
        self._init_environmental_sources()

        # Initialise scheduler
        self._init_scheduler()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        # Validate required configuration sections
        required_sections = ["device", "cycle"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate device configuration
        device_config = self.config["device"]
        required_device_keys = ["ip_address", "email", "password"]
        for key in required_device_keys:
            if key not in device_config:
                raise ValueError(f"Missing required device configuration: {key}")

        # Validate cycle configuration
        cycle_config = self.config["cycle"]
        required_cycle_keys = ["flood_duration_minutes", "drain_duration_minutes", "interval_minutes"]
        for key in required_cycle_keys:
            if key not in cycle_config:
                raise ValueError(f"Missing required cycle configuration: {key}")

    def _init_controller(self):
        """Initialise the Tapo device controller."""
        device_config = self.config["device"]
        auto_discovery = device_config.get("auto_discovery", True)
        self.controller = TapoController(
            ip_address=device_config["ip_address"],
            email=device_config["email"],
            password=device_config["password"],
            logger=self.logger,
            enable_auto_discovery=auto_discovery
        )

    def _init_environmental_sources(self):
        """Initialize environmental data sources (daylight, temperature) for API access."""
        schedule_config = self.config.get("schedule", {})
        adaptation_config = schedule_config.get("adaptation", {})
        
        # Initialize daylight calculator if location is configured (even if adaptation disabled)
        location_config = adaptation_config.get("location", {})
        postcode = location_config.get("postcode")
        timezone = location_config.get("timezone")
        
        if postcode:
            try:
                from .daylight import DaylightCalculator
                self.daylight_calc = DaylightCalculator(
                    postcode=postcode,
                    timezone=timezone,
                    logger=self.logger
                )
                if self.logger:
                    self.logger.info(f"Daylight calculator initialized for postcode {postcode}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to initialize daylight calculator: {e}")
        
        # Initialize temperature fetcher if temperature source is configured (even if adaptation disabled)
        temp_config = adaptation_config.get("temperature", {})
        source = temp_config.get("source", "bom")
        
        if source == "bom":
            try:
                from .bom_temperature import BOMTemperature
                station_id = temp_config.get("station_id", "auto")
                
                # Auto-detect station if needed
                if station_id == "auto":
                    if self.daylight_calc and self.daylight_calc.location_info:
                        lat = self.daylight_calc.location_info.latitude
                        lon = self.daylight_calc.location_info.longitude
                        temp_fetcher_temp = BOMTemperature(logger=self.logger)
                        station_id = temp_fetcher_temp.find_nearest_station(lat, lon)
                    else:
                        # Try to use a default station if no location configured
                        # Use Sydney Observatory Hill as default
                        station_id = "94768"
                        if self.logger:
                            self.logger.info("Using default BOM station (Sydney) - configure postcode for nearest station")
                
                if station_id and station_id != "auto":
                    self.temperature_fetcher = BOMTemperature(station_id=station_id, logger=self.logger)
                    station_name = self.temperature_fetcher.station_name or station_id
                    if self.logger:
                        self.logger.info(f"BOM temperature fetcher initialized for {station_name} ({station_id})")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to initialize temperature fetcher: {e}")

    def _init_scheduler(self):
        """Initialise the scheduler (time-based or interval-based)."""
        schedule_config = self.config.get("schedule", {})
        schedule_type = schedule_config.get("type", "interval")  # "interval" or "time_based"

        if schedule_type == "time_based":
            # Use time-based scheduler with cycles (new format) or on_times (backward compatibility)
            flood_duration_minutes = float(schedule_config.get("flood_duration_minutes", 2.0))
            cycles = schedule_config.get("cycles", [])
            on_times = schedule_config.get("on_times", [])
            
            # Prefer cycles format if available, otherwise fall back to on_times
            base_scheduler = None
            if cycles:
                base_scheduler = TimeScheduler(
                    controller=self.controller,
                    cycles=cycles,
                    flood_duration_minutes=flood_duration_minutes,
                    logger=self.logger
                )
            elif on_times:
                base_scheduler = TimeScheduler(
                    controller=self.controller,
                    on_times=on_times,
                    flood_duration_minutes=flood_duration_minutes,
                    logger=self.logger
                )
            else:
                raise ValueError("time_based schedule requires either 'cycles' or 'on_times' in schedule configuration")
            
            # Check if adaptive scheduling is enabled
            adaptation_config = schedule_config.get("adaptation", {})
            if adaptation_config.get("enabled", False):
                # Check if active adaptive is enabled
                active_adaptive_config = adaptation_config.get("active_adaptive", {})
                if active_adaptive_config.get("enabled", False):
                    # Use active adaptive scheduler (completely independent)
                    from .active_adaptive_scheduler import ActiveAdaptiveScheduler
                    self.scheduler = ActiveAdaptiveScheduler(
                        controller=self.controller,
                        flood_duration_minutes=flood_duration_minutes,
                        adaptation_config=adaptation_config,
                        logger=self.logger
                    )
                else:
                    # Use legacy adaptive scheduler
                    from .adaptive_scheduler import AdaptiveScheduler
                    # Get base cycles for adaptive scheduler
                    base_cycles = cycles if cycles else [
                        {"on_time": t.strftime("%H:%M"), "off_duration_minutes": 0}
                        for t in base_scheduler.on_times
                    ]
                    self.scheduler = AdaptiveScheduler(
                        base_cycles=base_cycles,
                        controller=self.controller,
                        flood_duration_minutes=flood_duration_minutes,
                        adaptation_config=adaptation_config,
                        logger=self.logger
                    )
            else:
                self.scheduler = base_scheduler
        else:
            # Use interval-based scheduler (original)
            cycle_config = self.config["cycle"]
            active_hours = schedule_config.get("active_hours", {})
            active_hours_start = active_hours.get("start")
            active_hours_end = active_hours.get("end")

            self.scheduler = CycleScheduler(
                controller=self.controller,
                flood_duration_minutes=float(cycle_config["flood_duration_minutes"]),
                drain_duration_minutes=float(cycle_config["drain_duration_minutes"]),
                interval_minutes=float(cycle_config["interval_minutes"]),
                schedule_enabled=schedule_config.get("enabled", True),
                active_hours_start=active_hours_start,
                active_hours_end=active_hours_end,
                logger=self.logger
            )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if self.logger:
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.shutdown_requested = True
        self.stop()

    def start(self):
        """Start the controller."""
        if self.logger:
            self.logger.info("=" * 60)
            self.logger.info("Hydroponic Controller Starting")
            self.logger.info("=" * 60)

        # Connect to device
        if not self.controller.connect():
            if self.logger:
                self.logger.error("Failed to connect to device. Exiting.")
            sys.exit(1)

        # Start scheduler
        try:
            self.scheduler.start()
        except Exception as e:
            if self.logger:
                import traceback
                self.logger.error(f"Error starting scheduler: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        if self.logger:
            self.logger.info("Controller started successfully")
            self.logger.info("Press Ctrl+C to stop")
        
        # Start web server if enabled
        self._start_web_server()

        # Main loop - keep application running
        try:
            while not self.shutdown_requested:
                signal.pause()  # Wait for signals
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Keyboard interrupt received")
            self.shutdown_requested = True
            self.stop()

    def _start_web_server(self):
        """Start web server if enabled in configuration."""
        web_config = self.config.get("web", {})
        if not web_config.get("enabled", False):
            return
        
        try:
            from .web.api import WebAPI
            
            host = web_config.get("host", "0.0.0.0")
            port = web_config.get("port", 8000)
            
            self.web_api = WebAPI(self, host=host, port=port)
            self.web_api.start()
            
            if self.logger:
                self.logger.info(f"Web UI started at http://{host}:{port}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start web server: {e}")
            else:
                print(f"Warning: Failed to start web server: {e}", file=sys.stderr)

    def stop(self):
        """Stop the controller gracefully."""
        if self.logger:
            self.logger.info("Stopping controller...")

        # Stop web server
        if self.web_api:
            self.web_api.stop()

        # Stop scheduler (this will also ensure device is turned off)
        if self.scheduler:
            self.scheduler.stop()

        if self.logger:
            self.logger.info("Controller stopped")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Tapo P100 Hydroponic Flood & Drain Controller")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="Path to configuration file (default: config/config.json)"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Enable web UI (overrides config file setting)"
    )

    args = parser.parse_args()

    try:
        app = HydroController(args.config)
        
        # Override web config if --web flag is set
        if args.web:
            if "web" not in app.config:
                app.config["web"] = {}
            app.config["web"]["enabled"] = True
        
        app.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"Error: {e}", file=sys.stderr)
        print(f"Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

