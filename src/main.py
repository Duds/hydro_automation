import os
import signal
import sys
import time
import logging
from typing import Optional, Dict, Any

from .core.config_validator import load_and_validate_config
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

            # 4. Initialize scheduler
            self.scheduler = SchedulerFactory.create_scheduler(
                self.config,
                self.device_registry,
                self.logger
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
