#!/usr/bin/env python3
"""Test script for plugp100 library."""

import asyncio
import sys

try:
    from plugp100 import TapoApiClient, TapoDeviceState
except ImportError:
    print("Error: plugp100 library not installed.")
    print("Install it with: pip install plugp100")
    sys.exit(1)


async def test_connection(ip_address: str, email: str, password: str):
    """Test connection using plugp100 library."""
    print(f"\nTesting connection to {ip_address} using plugp100 library...")
    print(f"Email: {email}")
    print(f"Password: {'*' * len(password)}\n")
    
    client = TapoApiClient(ip_address, email, password)
    
    try:
        print("  Attempting login...")
        await client.login()
        print("  ✓ Login successful!\n")
        
        print("  Getting device info...")
        state = await client.get_state()
        print("  ✓ Device info retrieved!\n")
        
        print("Device Information:")
        print("-" * 40)
        print(f"  Device ID: {state.device_id}")
        print(f"  Model: {state.model}")
        print(f"  Firmware: {state.firmware_version}")
        print(f"  Device Name: {state.nickname}")
        print(f"  Current State: {'ON' if state.device_on else 'OFF'}")
        print(f"  Hardware Version: {state.hardware_version}")
        
        print("\nTesting device control:")
        print("-" * 40)
        
        # Turn device on
        print("  Turning device ON...")
        await client.on()
        await asyncio.sleep(2)
        state = await client.get_state()
        if state.device_on:
            print("  ✓ Device turned ON successfully")
        else:
            print("  ✗ Device ON command may have failed")
        
        # Turn device off
        print("  Turning device OFF...")
        await client.off()
        await asyncio.sleep(2)
        state = await client.get_state()
        if not state.device_on:
            print("  ✓ Device turned OFF successfully")
        else:
            print("  ✗ Device OFF command may have failed")
        
        print("\n" + "=" * 40)
        print("✓ All tests passed! plugp100 library works with your device!")
        print("=" * 40)
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print(f"     Error type: {type(e).__name__}")
        import traceback
        print(f"\n     Full traceback:\n{traceback.format_exc()}")
        try:
            await client.close()
        except:
            pass
        return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -m src.test_plugp100 <ip> <email> <password>")
        sys.exit(1)
    
    ip = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    result = asyncio.run(test_connection(ip, email, password))
    sys.exit(0 if result else 1)

