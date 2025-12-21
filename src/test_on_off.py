#!/usr/bin/env python3
"""Test script to turn device ON for 2 minutes, then OFF."""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tapo_controller import TapoController
from src.logger import setup_logger


def main():
    """Run the on/off test."""
    # Load config
    import json
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    
    with open(config_path) as f:
        config = json.load(f)
    
    device_config = config["device"]
    logging_config = config.get("logging", {})
    
    # Setup logger
    logger = setup_logger(
        log_file=logging_config.get("log_file", "logs/test.log"),
        log_level=logging_config.get("log_level", "INFO")
    )
    
    # Create controller
    controller = TapoController(
        ip_address=device_config["ip_address"],
        email=device_config["email"],
        password=device_config["password"],
        logger=logger,
        enable_auto_discovery=device_config.get("auto_discovery", True)
    )
    
    logger.info("=" * 60)
    logger.info("Testing Device ON/OFF - 2 minutes ON, then OFF")
    logger.info("=" * 60)
    
    # Connect
    logger.info("Connecting to device...")
    if not controller.connect():
        logger.error("Failed to connect to device. Exiting.")
        sys.exit(1)
    
    logger.info("✓ Connected successfully")
    
    # Turn ON
    logger.info("\n" + "=" * 60)
    logger.info("Turning device ON...")
    logger.info("=" * 60)
    
    if controller.turn_on(verify=True):
        logger.info("✓ Device is ON")
        logger.info(f"Keeping device ON for 2 minutes (120 seconds)...")
        
        # Wait for 2 minutes
        for remaining in range(120, 0, -10):
            logger.info(f"  {remaining} seconds remaining...")
            time.sleep(10)
        
        logger.info("  2 minutes elapsed")
    else:
        logger.error("✗ Failed to turn device ON")
        controller.close()
        sys.exit(1)
    
    # Turn OFF
    logger.info("\n" + "=" * 60)
    logger.info("Turning device OFF...")
    logger.info("=" * 60)
    
    if controller.turn_off(verify=True):
        logger.info("✓ Device is OFF")
    else:
        logger.error("✗ Failed to turn device OFF")
    
    # Close connection
    controller.close()
    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

