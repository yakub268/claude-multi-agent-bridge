#!/usr/bin/env python3
"""Simple test to verify server collaboration is working"""
import requests
import time

print("Testing server collaboration features...")

# Check server status
print("\n1. Checking server status...")
try:
    resp = requests.get("http://localhost:5001/api/status")
    data = resp.json()
    print(f"   Server version: {data['version']}")
    print(f"   Collaboration enabled: {data['features']['collaboration']}")
    if data["features"]["collaboration"]:
        print("   ✅ Collaboration features available")
    else:
        print("   ❌ Collaboration features disabled")
        exit(1)
except Exception as e:
    print(f"   ❌ Server not responding: {e}")
    exit(1)

# List rooms (should be empty initially)
print("\n2. Listing collaboration rooms...")
try:
    resp = requests.get("http://localhost:5001/api/collab/rooms")
    data = resp.json()
    print(f"   Status: {data['status']}")
    print(f"   Total rooms: {data['total']}")
    print("   ✅ REST API working")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

print("\n✅ Server collaboration features are accessible!")
print("   - Server running: ✅")
print("   - Collaboration enabled: ✅")
print("   - REST API working: ✅")
print("\n❌ WebSocket integration test requires fix in client response handling")
