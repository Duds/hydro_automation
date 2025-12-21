"""Tapo P100 device controller using plugp100 library."""

import asyncio
import time
from typing import Optional

try:
    from plugp100.common.credentials import AuthCredential
    from plugp100.new.device_factory import connect, DeviceConnectConfiguration
    from plugp100.new.tapoplug import TapoPlug
    from plugp100.discovery.tapo_discovery import TapoDiscovery
except ImportError:
    raise ImportError(
        "plugp100 library not installed. Install it with: pip install plugp100"
    )


class TapoController:
    """Controller for TP-Link Tapo P100 smart plug using plugp100 library."""

    def __init__(self, ip_address: str, email: str, password: str, logger=None, enable_auto_discovery: bool = True):
        """
        Initialise the Tapo controller.

        Args:
            ip_address: IP address of the Tapo P100 device (used as initial/default)
            email: Tapo account email
            password: Tapo account password
            logger: Optional logger instance
            enable_auto_discovery: If True, attempt to discover device if IP connection fails
        """
        self.ip_address = ip_address
        self.email = email
        self.password = password
        self.logger = logger
        self.enable_auto_discovery = enable_auto_discovery
        self.device: Optional[TapoPlug] = None
        self.connected = False
        self._loop = None
        self._loop_thread = None

    def _get_or_create_loop(self):
        """Get or create and start event loop in a background thread."""
        if self._loop is not None and not self._loop.is_closed():
            return self._loop
        
        # Create new event loop
        self._loop = asyncio.new_event_loop()
        
        # Start loop in background thread
        import threading
        def run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
        
        return self._loop

    def _run_async(self, coro):
        """Run async coroutine in the persistent event loop."""
        loop = self._get_or_create_loop()
        
        # Schedule coroutine and wait for result
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30)  # 30 second timeout

    def discover_device(self, timeout: int = 10) -> Optional[str]:
        """
        Discover Tapo P100 device on the network.

        Args:
            timeout: Timeout in seconds for discovery

        Returns:
            IP address of discovered device, or None if not found
        """
        async def _discover_async():
            try:
                if self.logger:
                    self.logger.info(f"Scanning network for Tapo P100 device (timeout: {timeout}s)...")
                
                discovered_devices = await TapoDiscovery.scan(timeout=timeout)
                
                if not discovered_devices:
                    if self.logger:
                        self.logger.warning("No Tapo devices found on network")
                    return None
                
                # Try to connect to each discovered device to verify it's the right one
                credentials = AuthCredential(self.email, self.password)
                for discovered_device in discovered_devices:
                    try:
                        if self.logger:
                            self.logger.info(f"Trying discovered device at {discovered_device.ip}")
                        
                        device = await discovered_device.get_tapo_device(credentials)
                        await device.update()
                        
                        # Check if it's a P100 plug
                        if isinstance(device, TapoPlug):
                            if self.logger:
                                self.logger.info(
                                    f"Found Tapo P100 at {discovered_device.ip} "
                                    f"(Device ID: {device.device_id})"
                                )
                            await device.client.close()
                            return discovered_device.ip
                        else:
                            await device.client.close()
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"Failed to connect to {discovered_device.ip}: {e}")
                        continue
                
                if self.logger:
                    self.logger.warning("Found Tapo devices but none are P100 plugs")
                return None
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error during device discovery: {e}")
                return None

        try:
            # Use thread-safe async execution
            return self._run_async(_discover_async())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during discovery: {e}")
            return None

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Establish connection to the Tapo device.

        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Delay in seconds between retries

        Returns:
            True if connection successful, False otherwise
        """
        async def _connect_async(ip_addr: str):
            credentials = AuthCredential(self.email, self.password)
            config = DeviceConnectConfiguration(host=ip_addr, credentials=credentials)

            for attempt in range(1, max_retries + 1):
                try:
                    if self.logger:
                        self.logger.info(
                            f"Connecting to Tapo P100 at {ip_addr} (attempt {attempt}/{max_retries})"
                        )

                    device = await connect(config)
                    await device.update()
                    
                    self.device = device
                    self.connected = True
                    self.ip_address = ip_addr  # Update IP if it changed

                    if self.logger:
                        self.logger.info(
                            f"Successfully connected to Tapo P100 at {ip_addr} using {device.protocol_version} protocol"
                        )
                    return True

                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Connection attempt {attempt} to {ip_addr} failed: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                    else:
                        return False

            return False

        # Ensure we have a loop before connecting
        loop = self._get_or_create_loop()
        
        try:
            # Use thread-safe async execution
            # Try configured IP first
            if self._run_async(_connect_async(self.ip_address)):
                return True

            # If that fails and auto-discovery is enabled, try to discover the device
            if self.enable_auto_discovery:
                if self.logger:
                    self.logger.info(
                        f"Connection to configured IP {self.ip_address} failed. "
                        "Attempting to discover device on network..."
                    )
                
                discovered_ip = self.discover_device(timeout=10)
                if discovered_ip:
                    if self.logger:
                        self.logger.info(
                            f"Device discovered at {discovered_ip}. "
                            f"Consider updating config.json with new IP address."
                        )
                    # Try connecting to discovered IP
                    if self._run_async(_connect_async(discovered_ip)):
                        return True
                else:
                    if self.logger:
                        self.logger.error("Device discovery failed. Could not find Tapo P100 on network.")

            if self.logger:
                self.logger.error(
                    "Failed to connect to Tapo P100 after all retry attempts and discovery"
                )
            self.connected = False
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during connection: {e}")
            self.connected = False
            return False

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.connected and self.device is not None

    def turn_on(self, verify: bool = True, max_retries: int = 3) -> bool:
        """
        Turn on the device.

        Args:
            verify: Whether to verify the device state after command
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if self.logger:
                self.logger.error("Cannot turn on device: not connected")
            return False

        async def _turn_on_async():
            for attempt in range(1, max_retries + 1):
                try:
                    result = await self.device.turn_on()
                    if result.is_success():
                        if self.logger:
                            self.logger.info("Device turned ON")

                        if verify:
                            await asyncio.sleep(1.0)
                            await self.device.update()
                            if self.device.is_on:
                                return True
                            else:
                                if self.logger:
                                    self.logger.warning(
                                        f"Device ON command sent but verification failed (attempt {attempt})"
                                    )
                                if attempt < max_retries:
                                    await asyncio.sleep(1.0)
                                continue

                        return True
                    else:
                        error = result.error()
                        if self.logger:
                            self.logger.warning(f"Failed to turn on device (attempt {attempt}): {error}")
                        if attempt < max_retries:
                            await asyncio.sleep(1.0)
                        else:
                            if self.logger:
                                self.logger.error("Failed to turn on device after all retry attempts")
                            return False

                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to turn on device (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(1.0)
                    else:
                        if self.logger:
                            self.logger.error("Failed to turn on device after all retry attempts")
                        return False

            return False

        try:
            # Use thread-safe async execution
            return self._run_async(_turn_on_async())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error turning device on: {e}")
            return False

    def turn_off(self, verify: bool = True, max_retries: int = 3) -> bool:
        """
        Turn off the device.

        Args:
            verify: Whether to verify the device state after command
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if self.logger:
                self.logger.error("Cannot turn off device: not connected")
            return False

        async def _turn_off_async():
            for attempt in range(1, max_retries + 1):
                try:
                    result = await self.device.turn_off()
                    if result.is_success():
                        if self.logger:
                            self.logger.info("Device turned OFF")

                        if verify:
                            await asyncio.sleep(1.0)
                            await self.device.update()
                            if not self.device.is_on:
                                return True
                            else:
                                if self.logger:
                                    self.logger.warning(
                                        f"Device OFF command sent but verification failed (attempt {attempt})"
                                    )
                                if attempt < max_retries:
                                    await asyncio.sleep(1.0)
                                continue

                        return True
                    else:
                        error = result.error()
                        if self.logger:
                            self.logger.warning(f"Failed to turn off device (attempt {attempt}): {error}")
                        if attempt < max_retries:
                            await asyncio.sleep(1.0)
                        else:
                            if self.logger:
                                self.logger.error("Failed to turn off device after all retry attempts")
                            return False

                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to turn off device (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(1.0)
                    else:
                        if self.logger:
                            self.logger.error("Failed to turn off device after all retry attempts")
                        return False

            return False

        try:
            # Use thread-safe async execution
            return self._run_async(_turn_off_async())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error turning device off: {e}")
            return False

    def is_device_on(self) -> Optional[bool]:
        """
        Check if device is currently on.

        Returns:
            True if on, False if off, None if unable to determine
        """
        if not self.is_connected():
            return None

        async def _check_state_async():
            try:
                await self.device.update()
                return self.device.is_on
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to get device state: {e}")
                return None

        try:
            # Use thread-safe async execution
            return self._run_async(_check_state_async())
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error checking device state: {e}")
            return None

    def ensure_off(self) -> bool:
        """
        Ensure device is turned off (useful for graceful shutdown).

        Returns:
            True if device is confirmed off, False otherwise
        """
        if not self.is_connected():
            return False

        async def _ensure_off_async():
            try:
                await self.device.update()
                if self.device.is_on:
                    result = await self.device.turn_off()
                    if result.is_success():
                        await asyncio.sleep(1.0)
                        await self.device.update()
                        return not self.device.is_on
                    return False
                else:
                    return True
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error ensuring device is off: {e}")
                return False

        try:
            # Use thread-safe async execution
            return self._run_async(_ensure_off_async())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error ensuring device is off: {e}")
            return False

    def close(self):
        """Close the device connection."""
        if self.device and self.connected:
            async def _close_async():
                try:
                    await self.device.client.close()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error closing device connection: {e}")

            try:
                # Use thread-safe async execution
                self._run_async(_close_async())
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error closing connection: {e}")
            finally:
                self.connected = False
                self.device = None
