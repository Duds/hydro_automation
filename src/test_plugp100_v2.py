#!/usr/bin/env python3
"""Test script for plugp100 library using TapoClient."""

import asyncio
import sys

try:
    from plugp100.api.tapo_client import TapoClient, TapoProtocolType
    from plugp100.common.credentials import AuthCredential
    from plugp100.protocol.klap.klap_protocol import KlapProtocol
    from plugp100.protocol.passthrough_protocol import PassthroughProtocol
    import aiohttp
except ImportError as e:
    print(f"Error importing plugp100: {e}")
    print("Install it with: pip install plugp100")
    sys.exit(1)


async def test_connection(ip_address: str, email: str, password: str):
    """Test connection using plugp100 TapoClient."""
    print(f"\nTesting connection to {ip_address} using plugp100 TapoClient...")
    print(f"Email: {email}")
    print(f"Password: {'*' * len(password)}\n")
    
    auth = AuthCredential(email, password)
    url = f"http://{ip_address}"
    
    # Try KLAP protocol first (newer firmware)
    print("  Attempting connection with KLAP protocol (for newer firmware)...")
    try:
        http_session = aiohttp.ClientSession()
        protocol = KlapProtocol(auth, url, http_session)
        client = TapoClient(auth, url, protocol, http_session)
        
        # Try to get device info
        print("  Getting device info...")
        device_info_result = await client.get_device_info()
        
        if device_info_result.is_success():
            device_info = device_info_result.value
            print("  ✓ Connection successful with KLAP protocol!\n")
            print("Device Information:")
            print("-" * 40)
            print(f"  Device Info: {device_info}")
            
            # Test control
            print("\nTesting device control:")
            print("-" * 40)
            
            # Get current state
            from plugp100.api.requests.set_device_info.set_plug_info_params import SetPlugInfoParams
            current_state = device_info.get("device_on", False)
            print(f"  Current state: {'ON' if current_state else 'OFF'}")
            
            # Turn on
            print("  Turning device ON...")
            set_on = SetPlugInfoParams(device_on=True)
            result = await client.set_device_info(set_on)
            if result.is_success():
                print("  ✓ Device turned ON successfully")
            else:
                print(f"  ✗ Failed to turn ON: {result.error()}")
            
            await asyncio.sleep(2)
            
            # Turn off
            print("  Turning device OFF...")
            set_off = SetPlugInfoParams(device_on=False)
            result = await client.set_device_info(set_off)
            if result.is_success():
                print("  ✓ Device turned OFF successfully")
            else:
                print(f"  ✗ Failed to turn OFF: {result.error()}")
            
            print("\n" + "=" * 40)
            print("✓ All tests passed! plugp100 TapoClient works!")
            print("=" * 40)
            
            await client.close()
            await http_session.close()
            return True
        else:
            print(f"  ✗ KLAP protocol failed: {result.error()}")
            await client.close()
            await http_session.close()
    except Exception as e:
        print(f"  ✗ KLAP protocol error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await http_session.close()
        except:
            pass
    
    # Try Passthrough protocol (older firmware)
    print("\n  Attempting connection with Passthrough protocol (for older firmware)...")
    try:
        http_session = aiohttp.ClientSession()
        protocol = PassthroughProtocol(auth, url, http_session)
        client = TapoClient(auth, url, protocol, http_session)
        
        device_info_result = await client.get_device_info()
        if device_info_result.is_success():
            print("  ✓ Connection successful with Passthrough protocol!")
            await client.close()
            await http_session.close()
            return True
        else:
            print(f"  ✗ Passthrough protocol failed: {device_info_result.error()}")
            await client.close()
            await http_session.close()
    except Exception as e:
        print(f"  ✗ Passthrough protocol error: {e}")
        try:
            await http_session.close()
        except:
            pass
    
    print("\n✗ All connection attempts failed.")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -m src.test_plugp100_v2 <ip> <email> <password>")
        sys.exit(1)
    
    ip = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    result = asyncio.run(test_connection(ip, email, password))
    sys.exit(0 if result else 1)

