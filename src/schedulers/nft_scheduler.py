"""NFT (Nutrient Film Technique) scheduler for continuous flow systems."""

import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.scheduler_interface import IScheduler
from ..services.device_service import DeviceRegistry, IDeviceService


class NFTScheduler(IScheduler):
    """Scheduler for NFT (Nutrient Film Technique) systems.
    
    NFT systems require continuous flow, not flood/drain cycles.
    This scheduler manages flow rates and timing.
    """

    def __init__(
        self,
        device_registry: DeviceRegistry,
        device_id: str,
        flow_schedule: Dict[str, Any],
        logger=None
    ):
        """
        Initialize NFT scheduler.

        Args:
            device_registry: Device registry containing devices
            device_id: ID of the device to control (pump)
            flow_schedule: Flow rate schedule configuration
            logger: Optional logger instance
        """
        self.device_registry = device_registry
        self.device_id = device_id
        self.flow_schedule = flow_schedule
        self.logger = logger

        self.state = "idle"
        self.running = False
        self.shutdown_requested = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def _get_device(self) -> Optional[IDeviceService]:
        """Get the device service instance.

        Returns:
            Device service or None if not found
        """
        return self.device_registry.get_device(self.device_id)

    def _scheduler_loop(self):
        """Main scheduler loop for NFT continuous flow management."""
        device = self._get_device()
        if not device:
            if self.logger:
                self.logger.error(f"Device {self.device_id} not found in registry")
            return

        if self.logger:
            self.logger.info("NFT scheduler started - continuous flow mode")
            self.logger.warning("NFT scheduler implementation is not yet complete")

        # TODO: Implement NFT-specific scheduling logic
        # NFT systems typically require:
        # - Continuous pump operation during active hours
        # - Flow rate adjustments based on time of day
        # - Different flow rates for different growth stages
        # - Potentially intermittent flow (pump on for X minutes, off for Y minutes)

        while self.running and not self.shutdown_requested:
            # Placeholder: Keep pump running during active hours
            # This is a simplified implementation - actual NFT systems may need
            # more sophisticated flow management
            with self.lock:
                self.state = "flowing"

            if device.turn_on(verify=True):
                # Run continuously during active period
                # TODO: Implement proper flow schedule management
                time.sleep(60)  # Check every minute
            else:
                if self.logger:
                    self.logger.error("Failed to turn device on for NFT flow")
                time.sleep(10)

            if self.shutdown_requested:
                break

        if self.logger:
            self.logger.info("NFT scheduler stopped")

    def start(self) -> None:
        """Start the scheduler in a separate thread."""
        if self.running:
            if self.logger:
                self.logger.warning("Scheduler is already running")
            return

        self.running = True
        self.shutdown_requested = False
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.info("NFT scheduler thread started")

    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop the scheduler gracefully.

        Args:
            timeout: Maximum time to wait for scheduler to stop (seconds)
        """
        if not self.running:
            return

        if self.logger:
            self.logger.info("Stopping NFT scheduler...")

        self.shutdown_requested = True
        self.running = False

        # Ensure device is turned off
        device = self._get_device()
        if device and device.is_connected():
            if self.logger:
                self.logger.info("Ensuring device is turned off before shutdown")
            device.ensure_off()

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                if self.logger:
                    self.logger.warning("Scheduler thread did not stop within timeout")
            else:
                if self.logger:
                    self.logger.info("NFT scheduler stopped successfully")

        with self.lock:
            self.state = "idle"

    def get_state(self) -> str:
        """
        Get current scheduler state.

        Returns:
            Current state string
        """
        with self.lock:
            return self.state

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running

    def get_next_event_time(self) -> Optional[datetime]:
        """
        Get the next scheduled event time.

        For NFT scheduler, this is typically the next flow rate change time.

        Returns:
            Datetime of next event, or None if scheduler not running
        """
        # TODO: Implement next event calculation based on flow schedule
        return None

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status for API.

        Returns:
            Dictionary containing scheduler status information
        """
        device = self._get_device()
        device_info = device.get_device_info() if device else None

        return {
            "scheduler_type": "nft",
            "running": self.running,
            "state": self.get_state(),
            "device_id": self.device_id,
            "device_name": device_info.name if device_info else None,
            "device_connected": device.is_connected() if device else False,
            "device_state": device.is_device_on() if device else None,
            "flow_schedule": self.flow_schedule,
            "next_event_time": self.get_next_event_time().isoformat() if self.get_next_event_time() else None
        }

