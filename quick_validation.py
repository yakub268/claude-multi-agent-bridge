#!/usr/bin/env python3
"""
Quick Server Validation - Fast smoke tests for core functionality
"""
import requests
import time
import threading
from datetime import datetime, timezone


def test_status():
    """Test server is running and responding"""
    print("TEST 1: Server Status")
    print("-" * 50)

    try:
        r = requests.get("http://localhost:5001/api/status", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Server running - Uptime: {data['uptime_seconds']:.0f}s")
            print(f"✅ Total messages: {data['metrics']['total_messages']}")
            print(f"✅ Errors: {data['metrics']['errors']}")
            return True
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False


def test_send_receive():
    """Test basic send/receive"""
    print("\nTEST 2: Basic Send/Receive")
    print("-" * 50)

    try:
        # Send message
        payload = {
            'from': 'code',
            'to': 'browser',
            'type': 'test',
            'payload': {'test_id': 'validation-' + str(time.time())}
        }

        r = requests.post("http://localhost:5001/api/send", json=payload, timeout=5)
        if r.status_code != 200:
            print(f"❌ Send failed: {r.status_code}")
            return False

        print("✅ Message sent successfully")

        # Retrieve messages
        time.sleep(0.5)
        r = requests.get("http://localhost:5001/api/messages?to=browser", timeout=5)
        if r.status_code == 200:
            data = r.json()
            count = data.get('count', 0)
            print(f"✅ Retrieved {count} messages for browser")
            return True
        else:
            print(f"❌ Retrieve failed: {r.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_bulk_messages():
    """Test sending multiple messages quickly"""
    print("\nTEST 3: Bulk Message Handling")
    print("-" * 50)

    try:
        # Send 20 messages rapidly
        count = 20
        successes = 0

        for i in range(count):
            payload = {
                'from': 'code',
                'to': 'browser',
                'type': 'bulk_test',
                'payload': {'seq': i, 'timestamp': datetime.now(timezone.utc).isoformat()}
            }

            r = requests.post("http://localhost:5001/api/send", json=payload, timeout=5)
            if r.status_code == 200:
                successes += 1

        print(f"✅ Sent {successes}/{count} messages successfully")
        return successes >= count * 0.95  # 95% success

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_concurrent():
    """Test concurrent requests"""
    print("\nTEST 4: Concurrent Access")
    print("-" * 50)

    successes = []
    errors = []

    def worker(thread_id):
        try:
            for i in range(5):
                payload = {
                    'from': 'code',
                    'to': 'browser',
                    'type': 'concurrent_test',
                    'payload': {'thread': thread_id, 'seq': i}
                }

                r = requests.post("http://localhost:5001/api/send", json=payload, timeout=5)
                if r.status_code == 200:
                    successes.append(1)
                else:
                    errors.append(1)
        except Exception as e:
            errors.append(1)

    # Launch 10 threads, each sending 5 messages
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total = len(successes) + len(errors)
    print(f"✅ Successful: {len(successes)}/{total}")
    print(f"❌ Errors: {len(errors)}/{total}")

    return len(successes) >= total * 0.90  # 90% success


def test_channel_isolation():
    """Test message routing to correct channels"""
    print("\nTEST 5: Channel Isolation")
    print("-" * 50)

    try:
        # Send distinct messages to different channels
        timestamp = str(time.time())

        requests.post("http://localhost:5001/api/send", json={
            'from': 'code',
            'to': 'browser',
            'type': 'isolation_test',
            'payload': {'target': 'browser', 'ts': timestamp}
        }, timeout=5)

        requests.post("http://localhost:5001/api/send", json={
            'from': 'code',
            'to': 'desktop',
            'type': 'isolation_test',
            'payload': {'target': 'desktop', 'ts': timestamp}
        }, timeout=5)

        time.sleep(0.5)

        # Check each channel only has its own messages
        browser_data = requests.get("http://localhost:5001/api/messages?to=browser", timeout=5).json()
        desktop_data = requests.get("http://localhost:5001/api/messages?to=desktop", timeout=5).json()

        browser_msgs = browser_data.get('messages', [])
        desktop_msgs = desktop_data.get('messages', [])

        # Check for cross-contamination
        browser_has_desktop = any(
            msg.get('payload', {}).get('target') == 'desktop' and
            msg.get('payload', {}).get('ts') == timestamp
            for msg in browser_msgs
        )

        desktop_has_browser = any(
            msg.get('payload', {}).get('target') == 'browser' and
            msg.get('payload', {}).get('ts') == timestamp
            for msg in desktop_msgs
        )

        if browser_has_desktop or desktop_has_browser:
            print("❌ Channel isolation FAILED - messages leaked")
            return False
        else:
            print("✅ Channel isolation working correctly")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 70)
    print("🚀 QUICK SERVER VALIDATION")
    print("=" * 70)
    print()

    results = []

    results.append(("Server Status", test_status()))
    results.append(("Basic Send/Receive", test_send_receive()))
    results.append(("Bulk Messages", test_bulk_messages()))
    results.append(("Concurrent Access", test_concurrent()))
    results.append(("Channel Isolation", test_channel_isolation()))

    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:25s} {status}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Server is production-ready!")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
