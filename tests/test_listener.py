#!/usr/bin/env python3
"""
Test script to verify the HTTP listener functionality works.
"""

import json
import requests
import time
import threading

# Test data
test_data = [
    {
        "name": ["John", "Doe"],
        "found": True,
        "headshotImgString": "media/images/johndoe.jpg",
        "pCardName": "john-doe-1234"
    },
    {
        "name": ["Jane", "Smith"],
        "found": False,
        "headshotImgString": None,
        "pCardName": None
    }
]

def test_listener():
    """Test sending data to the listener."""
    time.sleep(1)  # Give server time to start
    
    try:
        response = requests.post(
            'http://localhost:8888/people-card-data',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"✅ Test request sent, response: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Test request failed: {e}")

if __name__ == "__main__":
    # Start test in background
    test_thread = threading.Thread(target=test_listener, daemon=True)
    test_thread.start()
    
    # Import and test the server
    try:
        from commands.scan import start_listener_server, received_data
        print("🧪 Starting test server...")
        start_listener_server()
        
        if received_data:
            print("✅ Test successful! Data received:")
            print(json.dumps(received_data, indent=2))
        else:
            print("❌ Test failed: No data received")
            
    except Exception as e:
        print(f"❌ Test error: {e}")