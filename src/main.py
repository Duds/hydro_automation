"""Main application entry point."""

import json
import signal
import sys
from pathlib import Path
from typing import Dict, Any

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

        # Load configuration
        self._load_config()

        # Setup logger
        log_config = self.config.get("logging", {})
        log_file = log_config.get("log_file", "logs/hydro_controller.log")
        log_level = log_config.get("log_level", "INFO")
        self.logger = setup_logger(log_file, log_level)

        # Initialise device controller
        self._init_controller()

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

    def _init_scheduler(self):
        """Initialise the scheduler (time-based or interval-based)."""
        schedule_config = self.config.get("schedule", {})
        schedule_type = schedule_config.get("type", "interval")  # "interval" or "time_based"

        if schedule_type == "time_based":
            # Use time-based scheduler with explicit ON times
            on_times = schedule_config.get("on_times", [])
            flood_duration_minutes = float(schedule_config.get("flood_duration_minutes", 2.0))
            
            if not on_times:
                raise ValueError("time_based schedule requires 'on_times' list in schedule configuration")
            
            self.scheduler = TimeScheduler(
                controller=self.controller,
                on_times=on_times,
                flood_duration_minutes=flood_duration_minutes,
                logger=self.logger
            )
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
        self.scheduler.start()

        if self.logger:
            self.logger.info("Controller started successfully")
            self.logger.info("Press Ctrl+C to stop")

        # Main loop - keep application running
        try:
            while not self.shutdown_requested:
                signal.pause()  # Wait for signals
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Keyboard interrupt received")
            self.shutdown_requested = True
            self.stop()

    def stop(self):
        """Stop the controller gracefully."""
        if self.logger:
            self.logger.info("Stopping controller...")

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

    args = parser.parse_args()

    try:
        app = HydroController(args.config)
        app.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

