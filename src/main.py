import os
import signal
import sys
import threading
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from .core.config_validator import load_and_validate_config
from .core.timed_operation import TimedOperationBusyError, TimedOperationGate
from .services.service_factory import create_device_registry
from .core.scheduler_factory import SchedulerFactory
from .web.api import WebAPI


class HydroController:
    """Main controller class for hydroponic automation."""

    def __init__(self, config_path: str):
        """
        Initialise the controller.

        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.logger: Optional[logging.Logger] = None
        self.device_registry = None
        self.scheduler = None
        self.web_api = None
        self.shutdown_requested = False
        self.timed_operation_gate = TimedOperationGate()

    @property
    def next_cycle_time(self) -> Optional[str]:
        """Next scheduled flood cycle start time (UTC ISO 8601) or None if stopped."""
        if self.scheduler and hasattr(self.scheduler, "next_cycle_time"):
            return self.scheduler.next_cycle_time
        return None

    def setup(self) -> bool:
        """
        Setup the controller, services and components.

        Returns:
            True if setup was successful
        """
        try:
            # 1. Load and validate configuration
            self.config = load_and_validate_config(self.config_path)

            # 2. Setup logging
            log_config = self.config.get("logging", {})
            self._setup_logging(log_config)
            self.logger.info("Hydroponic Controller starting...")

            # 3. Initialize device registry
            devices_config = self.config.get("devices", {})
            self.device_registry = create_device_registry(devices_config, self.logger)

            # Connect to primary device to ensure it's accessible
            primary_id = self.config.get("growing_system", {}).get("primary_device_id")
            if primary_id:
                device = self.device_registry.get_device(primary_id)
                if device:
                    self.logger.info(f"Connecting to primary device: {primary_id}")
                    if not device.connect():
                        self.logger.warning(f"Initial connection to primary device {primary_id} failed")
                else:
                    self.logger.error(f"Primary device {primary_id} not found in registry")
                    return False

            # 4. Initialize scheduler (pass gate so scheduler waits for timed ops)
            self.scheduler = SchedulerFactory.create_scheduler(
                self.config,
                self.device_registry,
                self.logger,
                self.timed_operation_gate,
            )

            # 5. Initialize web API (if enabled)
            web_config = self.config.get("web", {})
            if web_config and web_config.get("enabled", False):
                self.web_api = WebAPI(
                    self,
                    host=web_config.get("host", "0.0.0.0"),
                    port=web_config.get("port", 8000)
                )

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Setup failed: {str(e)}")
            else:
                print(f"Setup failed: {str(e)}")
            return False

    def _setup_logging(self, config: Dict[str, Any]):
        """Setup logging based on configuration."""
        log_file = config.get("log_file", "logs/hydro_controller.log")
        log_level_str = config.get("log_level", "INFO").upper()
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        level = getattr(logging, log_level_str, logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("HydroController")

    def device_on_timed(self, duration_minutes: float) -> str:
        """
        Turn the pump on for a specified duration, then turn it off automatically.
        Runs in a background thread. Only one timed operation can run at a time.

        Args:
            duration_minutes: Duration in minutes (must be > 0)

        Returns:
            UTC ISO 8601 timestamp of when the pump will turn off.

        Raises:
            TimedOperationBusyError: If a timed operation is already running (from
                src.core.timed_operation).
        """
        if self.timed_operation_gate.is_running():
            raise TimedOperationBusyError(
                "A timed operation is already running. Wait for it to complete."
            )

        primary_id = self.config.get("growing_system", {}).get("primary_device_id")
        if not primary_id or not self.device_registry:
            raise ValueError("Primary device not configured")

        device = self.device_registry.get_device(primary_id)
        if not device:
            raise ValueError("Primary device not found in registry")

        off_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        off_at_iso = off_at.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        self.timed_operation_gate.start(off_at_iso)

        def run_timed():
            try:
                if self.logger:
                    self.logger.info(
                        f"Timed operation: turning pump ON for {duration_minutes} minutes "
                        f"(off at {off_at_iso})"
                    )
                if device.turn_on(verify=True):
                    duration_seconds = duration_minutes * 60
                    start = time.time()
                    while time.time() - start < duration_seconds and not self.shutdown_requested:
                        time.sleep(1)
                device.turn_off(verify=True)
                if self.logger:
                    self.logger.info("Timed operation: pump turned OFF")
            finally:
                self.timed_operation_gate.finish()

        t = threading.Thread(target=run_timed, daemon=True)
        t.start()

        return off_at_iso

    def run(self):
        """Main execution loop."""
        if not self.setup():
            return

        # Start web API if enabled
        if self.web_api:
            self.logger.info(f"Starting Web API on {self.web_api.host}:{self.web_api.port}")
            self.web_api.start()

        # Start scheduler
        self.logger.info("Starting scheduler...")
        self.scheduler.start()

        # Handle signals for graceful shutdown
        def signal_handler(sig, frame):
            self.logger.info("Shutdown requested...")
            self.shutdown_requested = True
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep main thread alive
        try:
            while not self.shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop all services and components."""
        self.logger.info("Stopping services...")
        
        if self.scheduler:
            self.scheduler.stop()
        
        if self.web_api:
            self.web_api.stop()

        # 3. Close all device connections
        if self.device_registry:
            self.logger.info("Closing device connections...")
            for device in self.device_registry.get_all_devices():
                try:
                    device.close()
                except Exception as e:
                    self.logger.debug(f"Error closing device: {e}")
            
        self.logger.info("Hydroponic Controller stopped.")


def main():
    """Main entry point."""
    # Default config path
    config_path = os.environ.get("HYDRO_CONFIG", "config/config.json")
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        print("Please create a config file or set HYDRO_CONFIG environment variable.")
        sys.exit(1)

    controller = HydroController(config_path)
    controller.run()


if __name__ == "__main__":
    main()
