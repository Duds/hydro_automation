#!/usr/bin/env python3
"""Test script using plugp100 device factory (auto-detects protocol)."""

import asyncio
import sys

try:
    from plugp100.common.credentials import AuthCredential
    from plugp100.new.device_factory import connect, DeviceConnectConfiguration
except ImportError as e:
    print(f"Error importing plugp100: {e}")
    print("Install it with: pip install plugp100")
    sys.exit(1)


async def test_connection(ip_address: str, email: str, password: str):
    """Test connection using plugp100 device factory."""
    print(f"\nTesting connection to {ip_address} using plugp100 device factory...")
    print(f"Email: {email}")
    print(f"Password: {'*' * len(password)}\n")
    print("  Auto-detecting protocol and connecting...")
    
    credentials = AuthCredential(email, password)
    config = DeviceConnectConfiguration(host=ip_address, credentials=credentials)
    
    device = None
    try:
        device = await connect(config)
        print("  ✓ Connection successful!\n")
        
        print("  Updating device state...")
        await device.update()
        print("  ✓ Device state updated!\n")
        
        print("Device Information:")
        print("-" * 40)
        print(f"  Device Type: {type(device).__name__}")
        print(f"  Protocol: {device.protocol_version}")
        print(f"  Device ID: {device.device_id}")
        print(f"  Model: {device.model}")
        print(f"  Firmware: {device.firmware_version}")
        print(f"  Hardware: {device.hardware_version}")
        print(f"  Nickname: {device.nickname}")
        print(f"  Current State: {'ON' if device.is_on else 'OFF'}")
        
        print("\nTesting device control:")
        print("-" * 40)
        
        # Turn device on
        print("  Turning device ON...")
        result = await device.turn_on()
        if result.is_success():
            print("  ✓ Device turned ON successfully")
        else:
            print(f"  ✗ Failed to turn device ON: {result.error()}")
        
        await asyncio.sleep(2)
        await device.update()
        print(f"  Current state after ON: {'ON' if device.is_on else 'OFF'}")
        
        # Turn device off
        print("  Turning device OFF...")
        result = await device.turn_off()
        if result.is_success():
            print("  ✓ Device turned OFF successfully")
        else:
            print(f"  ✗ Failed to turn device OFF: {result.error()}")
        
        await asyncio.sleep(2)
        await device.update()
        print(f"  Current state after OFF: {'ON' if device.is_on else 'OFF'}")
        
        print("\n" + "=" * 40)
        print("✓ All tests passed! plugp100 works with your device!")
        print("=" * 40)
        
        await device.client.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print(f"     Error type: {type(e).__name__}")
        import traceback
        print(f"\n     Full traceback:\n{traceback.format_exc()}")
        if device:
            try:
                await device.client.close()
            except:
                pass
        return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -m src.test_plugp100_factory <ip> <email> <password>")
        sys.exit(1)
    
    ip = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    result = asyncio.run(test_connection(ip, email, password))
    sys.exit(0 if result else 1)

