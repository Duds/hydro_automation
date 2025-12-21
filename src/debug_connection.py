#!/usr/bin/env python3
"""Debug script to inspect Tapo P100 device responses."""

import json
import requests
import sys

def test_raw_handshake(ip_address: str):
    """Test raw handshake request to see actual response."""
    url = f"http://{ip_address}/app"
    
    # Payload that PyP100 uses for handshake
    payload = {
        "method": "handshake",
        "params": {
            "key": ""
        },
        "requestTimeMils": 0
    }
    
    print(f"Testing raw handshake to {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    try:
        # Use a fresh session
        session = requests.Session()
        response = session.post(url, json=payload, timeout=5)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nRaw Response Text:")
        print(response.text)
        
        print(f"\nResponse as JSON:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
            
            # Check what keys are actually present
            if isinstance(response_json, dict):
                print(f"\nResponse keys: {list(response_json.keys())}")
                if "error_code" in response_json:
                    print(f"Error code: {response_json['error_code']}")
                if "msg" in response_json:
                    print(f"Message: {response_json['msg']}")
        except json.JSONDecodeError as e:
            print(f"Could not parse as JSON: {e}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.debug_connection <ip_address>")
        sys.exit(1)
    
    ip = sys.argv[1]
    test_raw_handshake(ip)

