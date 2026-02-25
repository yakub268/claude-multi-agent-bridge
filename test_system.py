"""
Quick system test - verify all components working
"""

from code_client import CodeClient
import json
import time


def test_system():
    print("🧪 Multi-Claude Communication System Test\n")
    print("=" * 60)

    # Test 1: Server connection
    print("\n1️⃣  Testing server connection...")
    client = CodeClient()
    status = client.status()

    if status.get("status") == "running":
        print(
            f"   ✅ Server running ({status.get('message_count', 0)} messages in queue)"
        )
    else:
        print("   ❌ Server not responding")
        return False

    # Test 2: Send messages
    print("\n2️⃣  Testing message sending...")

    # To browser
    success = client.send(
        "browser",
        "command",
        {"action": "run_prompt", "text": "Test message from Code CLI"},
    )
    print(f"   {'✅' if success else '❌'} Send to browser")

    # To extension
    success = client.send("extension", "ping", {"timestamp": time.time()})
    print(f"   {'✅' if success else '❌'} Send to extension")

    # Broadcast
    success = client.broadcast(
        "test", {"source": "test_system.py", "message": "System test in progress"}
    )
    print(f"   {'✅' if success else '❌'} Broadcast to all")

    # Test 3: Receive messages
    print("\n3️⃣  Testing message retrieval...")
    time.sleep(0.5)
    messages = client.poll()
    print(f"   ✅ Retrieved {len(messages)} messages")

    if messages:
        print("\n   Recent messages:")
        for msg in messages[-3:]:
            print(f"   • [{msg['from']}→{msg['to']}] {msg['type']}")

    # Test 4: Check endpoints
    print("\n4️⃣  Testing API endpoints...")

    import requests

    endpoints = {
        "Status": "http://localhost:5001/api/status",
        "Messages": "http://localhost:5001/api/messages",
    }

    for name, url in endpoints.items():
        try:
            r = requests.get(url, timeout=2)
            print(f"   {'✅' if r.status_code == 200 else '❌'} {name} endpoint")
        except Exception as e:
            print(f"   ❌ {name} endpoint: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("✅ System test complete!")
    print("\nNext steps:")
    print("  1. Install browser extension (see QUICKSTART.md)")
    print("  2. Open claude.ai and check DevTools console")
    print("  3. Run: python demo.py")
    print("  4. Try: python playwright_bridge.py")

    return True


if __name__ == "__main__":
    try:
        test_system()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
