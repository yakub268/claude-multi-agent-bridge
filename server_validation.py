#!/usr/bin/env python3
"""
Server-Only Validation Test
Tests server performance and reliability without requiring browser clients
"""
import time
import threading
import requests
import statistics
from datetime import datetime, timezone

class ServerValidator:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.results = {
            'total_sent': 0,
            'total_received': 0,
            'errors': 0,
            'latencies': [],
        }
        self.lock = threading.Lock()

    def test_send_receive(self, from_client, to_client, test_id):
        """Test sending from one client and receiving by another"""
        try:
            start = time.time()

            # Send message
            response = requests.post(f"{self.base_url}/api/send", json={
                'from': from_client,
                'to': to_client,
                'type': 'test',
                'payload': {'id': test_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
            }, timeout=5)

            if response.status_code == 200:
                with self.lock:
                    self.results['total_sent'] += 1

                # Try to retrieve the message
                response = requests.get(f"{self.base_url}/api/messages", params={
                    'to': to_client
                }, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    messages = data.get('messages', [])
                    found = any(msg['payload'].get('id') == test_id for msg in messages)

                    latency = time.time() - start

                    if found:
                        with self.lock:
                            self.results['total_received'] += 1
                            self.results['latencies'].append(latency)
                        return True

            with self.lock:
                self.results['errors'] += 1
            return False

        except Exception as e:
            with self.lock:
                self.results['errors'] += 1
            print(f"  ❌ Error: {e}")
            return False

    def test_sequential(self, count=50):
        """Test sequential message sending"""
        print(f"\n{'='*70}")
        print(f"TEST 1: Sequential Send/Receive ({count} messages)")
        print('='*70)

        success = 0
        for i in range(count):
            if self.test_send_receive('code', 'browser', f'SEQ-{i}'):
                success += 1
            time.sleep(0.1)

        print(f"✅ Sent: {self.results['total_sent']}/{count}")
        print(f"✅ Received: {self.results['total_received']}/{count}")
        print(f"❌ Errors: {self.results['errors']}")

        return success >= count * 0.95  # 95% success

    def test_rapid_fire(self, count=100):
        """Test rapid message sending without delays"""
        print(f"\n{'='*70}")
        print(f"TEST 2: Rapid Fire ({count} messages, no delay)")
        print('='*70)

        start_sent = self.results['total_sent']
        start_received = self.results['total_received']

        success = 0
        for i in range(count):
            if self.test_send_receive('code', 'browser', f'RAPID-{i}'):
                success += 1

        sent = self.results['total_sent'] - start_sent
        received = self.results['total_received'] - start_received

        print(f"✅ Sent: {sent}/{count}")
        print(f"✅ Received: {received}/{count}")
        print(f"❌ Errors: {self.results['errors']}")

        return success >= count * 0.90  # 90% success for rapid fire

    def test_concurrent(self, thread_count=30):
        """Test concurrent message sending from multiple threads"""
        print(f"\n{'='*70}")
        print(f"TEST 3: Concurrent Threads ({thread_count} threads, 10 messages each)")
        print('='*70)

        start_sent = self.results['total_sent']
        start_received = self.results['total_received']

        threads = []

        def worker(thread_id):
            for i in range(10):
                self.test_send_receive('code', 'browser', f'THREAD-{thread_id}-{i}')
                time.sleep(0.05)

        # Launch threads
        for i in range(thread_count):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        sent = self.results['total_sent'] - start_sent
        received = self.results['total_received'] - start_received
        expected = thread_count * 10

        print(f"✅ Sent: {sent}/{expected}")
        print(f"✅ Received: {received}/{expected}")
        print(f"❌ Errors: {self.results['errors']}")

        return received >= expected * 0.90  # 90% success

    def test_channel_isolation(self):
        """Test that messages are properly routed to correct recipients"""
        print(f"\n{'='*70}")
        print(f"TEST 4: Channel Isolation")
        print('='*70)

        # Send to browser
        requests.post(f"{self.base_url}/api/send", json={
            'from': 'code',
            'to': 'browser',
            'type': 'test',
            'payload': {'target': 'browser'}
        })

        # Send to desktop
        requests.post(f"{self.base_url}/api/send", json={
            'from': 'code',
            'to': 'desktop',
            'type': 'test',
            'payload': {'target': 'desktop'}
        })

        time.sleep(0.5)

        # Check browser messages
        browser_data = requests.get(f"{self.base_url}/api/messages", params={'to': 'browser'}).json()
        browser_msgs = browser_data.get('messages', [])
        browser_has_desktop_msg = any(msg['payload'].get('target') == 'desktop' for msg in browser_msgs)

        # Check desktop messages
        desktop_data = requests.get(f"{self.base_url}/api/messages", params={'to': 'desktop'}).json()
        desktop_msgs = desktop_data.get('messages', [])
        desktop_has_browser_msg = any(msg['payload'].get('target') == 'browser' for msg in desktop_msgs)

        if not browser_has_desktop_msg and not desktop_has_browser_msg:
            print("✅ Channel isolation working correctly")
            return True
        else:
            print("❌ Channel isolation FAILED - messages leaked between channels")
            return False

    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        print(f"\n{'='*70}")
        print(f"TEST 5: Status Endpoint")
        print('='*70)

        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Status: {status['status']}")
                print(f"✅ Uptime: {status['uptime_seconds']:.0f}s")
                print(f"✅ Total Messages: {status['metrics']['total_messages']}")
                print(f"✅ Messages/min: {status['metrics']['messages_per_minute']:.2f}")
                print(f"✅ Errors: {status['metrics']['errors']}")
                return True
            return False
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print("📊 VALIDATION SUMMARY")
        print('='*70)

        print(f"Total Sent: {self.results['total_sent']}")
        print(f"Total Received: {self.results['total_received']}")
        print(f"Errors: {self.results['errors']}")

        if self.results['latencies']:
            print(f"\nLatency Stats:")
            print(f"  Min: {min(self.results['latencies'])*1000:.1f}ms")
            print(f"  Max: {max(self.results['latencies'])*1000:.1f}ms")
            print(f"  Avg: {statistics.mean(self.results['latencies'])*1000:.1f}ms")
            print(f"  p50: {statistics.median(self.results['latencies'])*1000:.1f}ms")
            if len(self.results['latencies']) > 1:
                print(f"  p95: {statistics.quantiles(self.results['latencies'], n=20)[18]*1000:.1f}ms")

        success_rate = (self.results['total_received'] / self.results['total_sent'] * 100) if self.results['total_sent'] > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if success_rate >= 95 and self.results['errors'] < 10:
            print("\n✅ SERVER VALIDATION PASSED")
            return True
        else:
            print("\n❌ SERVER VALIDATION FAILED")
            return False


def main():
    print("="*70)
    print("🧪 MULTI-CLAUDE BRIDGE - SERVER VALIDATION")
    print("="*70)
    print("\nThis validates server functionality without requiring browser clients.")
    print("For full end-to-end testing, use stress_test.py with browser extension.")
    print()

    validator = ServerValidator()

    # Run tests
    results = []

    results.append(("Status Check", validator.test_status_endpoint()))
    time.sleep(1)

    results.append(("Sequential", validator.test_sequential(50)))
    time.sleep(1)

    results.append(("Rapid Fire", validator.test_rapid_fire(100)))
    time.sleep(1)

    results.append(("Concurrent", validator.test_concurrent(30)))
    time.sleep(1)

    results.append(("Channel Isolation", validator.test_channel_isolation()))

    # Summary
    validator.print_summary()

    print(f"\n{'='*70}")
    print("TEST RESULTS:")
    print('='*70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20s} {status}")

    overall = all(result[1] for result in results)
    print(f"\n{'='*70}")
    if overall:
        print("✅ ALL TESTS PASSED - Server ready for production")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
    print('='*70)


if __name__ == '__main__':
    main()
