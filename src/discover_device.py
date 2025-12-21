#!/usr/bin/env python3
"""Device discovery and connection testing script for Tapo P100."""

import argparse
import socket
import sys
import time
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PyP100 import PyP100
except ImportError:
    print("Error: PyP100 library not installed.")
    print("Install it with: pip install PyP100")
    sys.exit(1)


def scan_local_network(base_ip: str = "192.168.1") -> list:
    """
    Scan local network for potential Tapo devices.

    Note: This is a simple port scan and may not find all devices.
    For more reliable discovery, check your router's device list or
    use the Tapo app to find the IP address.

    Args:
        base_ip: Base IP address (e.g., "192.168.1")

    Returns:
        List of IP addresses with port 80 open
    """
    found_ips = []
    print(f"Scanning {base_ip}.0-255:80 for devices...")
    print("This may take a few minutes...\n")

    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((ip, 80))
            if result == 0:
                found_ips.append(ip)
                print(f"  Found device at {ip}")
            sock.close()
        except Exception:
            pass

    return found_ips


def test_connection(ip_address: str, email: str, password: str) -> bool:
    """
    Test connection to Tapo P100 device.

    Args:
        ip_address: IP address of the device
        email: Tapo account email
        password: Tapo account password

    Returns:
        True if connection successful, False otherwise
    """
    print(f"\nTesting connection to {ip_address}...")
    print(f"Email: {email}")
    print(f"Password: {'*' * len(password)}\n")

    try:
        device = PyP100.P100(ip_address, email, password)
        print("  Establishing handshake...")
        try:
            device.handshake()
            print("  ✓ Handshake successful")
        except Exception as e:
            print(f"  ✗ Handshake failed: {e}")
            print(f"     Error type: {type(e).__name__}")
            print(f"     Full traceback:\n{traceback.format_exc()}")
            return False
        
        print("  Logging in...")
        try:
            device.login()
            print("  ✓ Login successful")
        except Exception as e:
            print(f"  ✗ Login failed: {e}")
            print(f"     Error type: {type(e).__name__}")
            print(f"     Full traceback:\n{traceback.format_exc()}")
            return False
        
        print("\n  ✓ Connection successful!\n")

        # Get device info
        print("Device Information:")
        print("-" * 40)
        try:
            device_info = device.getDeviceInfo()
            if device_info and "result" in device_info:
                result = device_info["result"]
                print(f"  Device ID: {result.get('device_id', 'N/A')}")
                print(f"  Model: {result.get('model', 'N/A')}")
                print(f"  Firmware: {result.get('fw_ver', 'N/A')}")
                print(f"  Device Name: {result.get('nickname', 'N/A')}")
                print(f"  Current State: {'ON' if result.get('device_on', False) else 'OFF'}")
        except Exception as e:
            print(f"  Could not retrieve device info: {e}")

        # Test turning device on
        print("\nTesting device control:")
        print("-" * 40)
        try:
            print("  Turning device ON...")
            device.turnOn()
            time.sleep(2)
            info = device.getDeviceInfo()
            if info and info.get("result", {}).get("device_on", False):
                print("  ✓ Device turned ON successfully")
            else:
                print("  ✗ Device ON command may have failed")

            print("  Turning device OFF...")
            device.turnOff()
            time.sleep(2)
            info = device.getDeviceInfo()
            if info and info.get("result", {}).get("device_on", False):
                print("  ✗ Device OFF command may have failed")
            else:
                print("  ✓ Device turned OFF successfully")
        except Exception as e:
            print(f"  ✗ Device control test failed: {e}")
            return False

        print("\n" + "=" * 40)
        print("✓ All tests passed! Device is ready to use.")
        print("=" * 40)
        return True

    except KeyError as e:
        print(f"  ✗ Connection failed - KeyError: {e}")
        print("     This usually means the device response format is unexpected.")
        print("     The device might be using a newer firmware version.")
        print(f"\n     Full traceback:\n{traceback.format_exc()}")
        print("\nTroubleshooting tips:")
        print("  - Try updating PyP100: pip install --upgrade PyP100")
        print("  - Verify the IP address is correct")
        print("  - Ensure device is on the same network")
        print("  - Check email and password are correct")
        print("  - Try unplugging and replugging the device")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print(f"     Error type: {type(e).__name__}")
        print(f"\n     Full traceback:\n{traceback.format_exc()}")
        print("\nTroubleshooting tips:")
        print("  - Verify the IP address is correct")
        print("  - Ensure device is on the same network")
        print("  - Check email and password are correct")
        print("  - Try unplugging and replugging the device")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover and test Tapo P100 device connection"
    )
    parser.add_argument(
        "--ip",
        type=str,
        help="IP address of the Tapo P100 device"
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Tapo account email"
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Tapo account password"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan local network for devices (slow)"
    )
    parser.add_argument(
        "--scan-base",
        type=str,
        default="192.168.1",
        help="Base IP for network scan (default: 192.168.1)"
    )

    args = parser.parse_args()

    # Network scan
    if args.scan:
        found_ips = scan_local_network(args.scan_base)
        if not found_ips:
            print("\nNo devices found on the network.")
            print("You may need to:")
            print("  1. Check your router's device list")
            print("  2. Use the Tapo app to find the IP address")
            print("  3. Check if your network uses a different IP range")
            return

        if args.ip:
            # Test specified IP
            if args.ip in found_ips:
                test_connection(args.ip, args.email, args.password)
            else:
                print(f"\nWarning: {args.ip} was not found in scan results")
                print("Found devices:")
                for ip in found_ips:
                    print(f"  - {ip}")
        else:
            # Test all found IPs
            print("\nTesting found devices:")
            for ip in found_ips:
                if test_connection(ip, args.email, args.password):
                    print(f"\n✓ Successfully connected to {ip}")
                    break
    else:
        # Direct connection test
        if not args.ip:
            print("Error: --ip is required (or use --scan to find devices)")
            sys.exit(1)

        success = test_connection(args.ip, args.email, args.password)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

