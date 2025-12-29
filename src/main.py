"""Main application entry point."""

import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .logger import setup_logger
from .core.config_validator import load_and_validate_config, ConfigValidationError
from .core.scheduler_interface import IScheduler
from .services.service_factory import (
    create_device_registry,
    create_sensor_registry,
    create_actuator_registry,
    create_environmental_service
)
from .core.scheduler_factory import SchedulerFactory


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
        self.device_registry = None
        self.sensor_registry = None
        self.actuator_registry = None
        self.env_service = None
        self.scheduler: Optional[IScheduler] = None
        self.shutdown_requested = False
        self.web_api = None

        # Load and validate configuration
        self._load_config()

        # Setup logger
        log_config = self.config.get("logging", {})
        log_file = log_config.get("log_file", "logs/hydro_controller.log")
        log_level = log_config.get("log_level", "INFO")
        self.logger = setup_logger(log_file, log_level)

        # Initialize registries and services
        self._init_services()

        # Initialize scheduler
        self._init_scheduler()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self):
        """Load and validate configuration from JSON file."""
        try:
            self.config = load_and_validate_config(str(self.config_path))
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except ConfigValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    def _init_services(self):
        """Initialize device, sensor, actuator registries and environmental service."""
        # Create device registry
        devices_config = self.config.get("devices", {})
        self.device_registry = create_device_registry(devices_config, self.logger)

        # Create sensor registry
        sensors_config = self.config.get("sensors", {})
        self.sensor_registry = create_sensor_registry(sensors_config, self.logger)

        # Create actuator registry
        actuators_config = self.config.get("actuators", {})
        self.actuator_registry = create_actuator_registry(actuators_config, self.logger)

        # Create environmental service
        schedule_config = self.config.get("schedule", {})
        adaptation_config = schedule_config.get("adaptation", {}) or {}
        self.env_service = create_environmental_service(adaptation_config, self.logger)

    def _init_scheduler(self):
        """Initialize scheduler using factory."""
        factory = SchedulerFactory(
            device_registry=self.device_registry,
            sensor_registry=self.sensor_registry,
            actuator_registry=self.actuator_registry,
            env_service=self.env_service,
            logger=self.logger
        )
        self.scheduler = factory.create(self.config)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if self.logger:
            try:
                signal_name = signal.Signals(signum).name
                self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            except (ValueError, AttributeError):
                self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        self.stop()

    def start(self):
        """Start the controller."""
        if self.logger:
            self.logger.info("=" * 60)
            self.logger.info("Hydroponic Controller Starting")
            self.logger.info("=" * 60)

        # Connect to all devices
        growing_system = self.config.get("growing_system", {})
        primary_device_id = growing_system.get("primary_device_id")

        if primary_device_id:
            device = self.device_registry.get_device(primary_device_id)
            if device:
                if not device.connect():
                    if self.logger:
                        self.logger.error(f"Failed to connect to primary device {primary_device_id}. Exiting.")
                    sys.exit(1)
            else:
                if self.logger:
                    self.logger.error(f"Primary device {primary_device_id} not found in registry. Exiting.")
                sys.exit(1)
        else:
            if self.logger:
                self.logger.error("No primary_device_id specified in growing_system configuration. Exiting.")
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
        if not web_config or not web_config.get("enabled", False):
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

        # Close all device connections
        if self.device_registry:
            for device in self.device_registry.get_all_devices():
                try:
                    device.close()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error closing device connection: {e}")

        if self.logger:
            self.logger.info("Controller stopped")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Hydroponic Controller")
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
