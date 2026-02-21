#!/usr/bin/env python3
"""
Stress Test Suite for Multi-Claude Message Bus
Tests reliability, latency, throughput, and edge cases
"""
import time
import threading
import statistics
from datetime import datetime
from code_client import CodeClient
import sys

class StressTest:
    def __init__(self):
        self.client = CodeClient()
        self.results = {
            'total_sent': 0,
            'total_received': 0,
            'timeouts': 0,
            'errors': 0,
            'latencies': [],
            'start_time': None,
            'end_time': None
        }
        self.lock = threading.Lock()

    def test_single_message(self, test_id, expected_response=None):
        """Test a single message round-trip"""
        start = time.time()

        try:
            # Send message
            prompt = f"Test {test_id}: What is 2+2? Reply with ONLY the number."
            self.client.send('browser', 'command', {
                'action': 'run_prompt',
                'text': prompt
            })

            with self.lock:
                self.results['total_sent'] += 1

            # Poll for response (15 second timeout)
            response = None
            for _ in range(15):
                time.sleep(1)
                messages = self.client.poll()

                for msg in messages:
                    if msg.get('type') == 'claude_response':
                        response = msg['payload']['response']
                        break

                if response:
                    break

            latency = time.time() - start

            if response:
                with self.lock:
                    self.results['total_received'] += 1
                    self.results['latencies'].append(latency)

                # Validate response if expected
                if expected_response and expected_response not in response:
                    print(f"  ⚠️  Test {test_id}: Unexpected response: {response[:50]}")
                    return False

                print(f"  ✅ Test {test_id}: Success ({latency:.2f}s)")
                return True
            else:
                with self.lock:
                    self.results['timeouts'] += 1
                print(f"  ❌ Test {test_id}: Timeout ({latency:.2f}s)")
                return False

        except Exception as e:
            with self.lock:
                self.results['errors'] += 1
            print(f"  ❌ Test {test_id}: Error - {e}")
            return False

    def test_sequential_messages(self, count=10):
        """Test sequential message sending"""
        print(f"\n{'='*70}")
        print(f"TEST 1: Sequential Messages ({count} messages)")
        print('='*70)

        success_count = 0
        for i in range(count):
            if self.test_single_message(f"SEQ-{i+1}"):
                success_count += 1
            time.sleep(0.5)  # Small delay between messages

        print(f"\nResults: {success_count}/{count} successful")
        return success_count == count

    def test_rapid_fire(self, count=20):
        """Test rapid message sending"""
        print(f"\n{'='*70}")
        print(f"TEST 2: Rapid Fire ({count} messages, no delay)")
        print('='*70)

        success_count = 0
        for i in range(count):
            if self.test_single_message(f"RAPID-{i+1}"):
                success_count += 1
            # No delay - send as fast as possible

        print(f"\nResults: {success_count}/{count} successful")
        return success_count >= count * 0.8  # 80% success threshold

    def test_concurrent_messages(self, count=10):
        """Test concurrent message sending"""
        print(f"\n{'='*70}")
        print(f"TEST 3: Concurrent Messages ({count} threads)")
        print('='*70)

        threads = []
        results = []

        def worker(test_id):
            result = self.test_single_message(f"CONCURRENT-{test_id}")
            results.append(result)

        # Launch threads
        for i in range(count):
            t = threading.Thread(target=worker, args=(i+1,))
            threads.append(t)
            t.start()

        # Wait for all
        for t in threads:
            t.join()

        success_count = sum(results)
        print(f"\nResults: {success_count}/{count} successful")
        return success_count >= count * 0.7  # 70% success threshold

    def test_large_payload(self):
        """Test with large payloads"""
        print(f"\n{'='*70}")
        print(f"TEST 4: Large Payload")
        print('='*70)

        # Generate large prompt
        large_text = "Repeat this: " + ("A" * 1000)

        start = time.time()
        self.client.send('browser', 'command', {
            'action': 'run_prompt',
            'text': large_text[:500]  # Trim to reasonable size
        })

        with self.lock:
            self.results['total_sent'] += 1

        # Wait for response
        response = None
        for _ in range(20):
            time.sleep(1)
            messages = self.client.poll()
            for msg in messages:
                if msg.get('type') == 'claude_response':
                    response = msg['payload']['response']
                    break
            if response:
                break

        latency = time.time() - start

        if response:
            with self.lock:
                self.results['total_received'] += 1
                self.results['latencies'].append(latency)
            print(f"  ✅ Large payload: Success ({latency:.2f}s, {len(response)} chars)")
            return True
        else:
            with self.lock:
                self.results['timeouts'] += 1
            print(f"  ❌ Large payload: Timeout")
            return False

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print(f"\n{'='*70}")
        print(f"TEST 5: Edge Cases")
        print('='*70)

        passed = 0
        total = 0

        # Test 1: Empty payload
        print("  Testing empty payload...")
        try:
            self.client.send('browser', 'command', {'text': ''})
            print("    ✅ Empty payload handled")
            passed += 1
        except Exception as e:
            print(f"    ❌ Empty payload error: {e}")
        total += 1

        # Test 2: Special characters
        print("  Testing special characters...")
        try:
            self.client.send('browser', 'command', {
                'text': 'Test: <script>alert("xss")</script> & "quotes" \\backslash'
            })
            print("    ✅ Special characters handled")
            passed += 1
        except Exception as e:
            print(f"    ❌ Special characters error: {e}")
        total += 1

        # Test 3: Unicode
        print("  Testing unicode...")
        try:
            self.client.send('browser', 'command', {
                'text': 'Test: 你好 🤖 привет مرحبا'
            })
            print("    ✅ Unicode handled")
            passed += 1
        except Exception as e:
            print(f"    ❌ Unicode error: {e}")
        total += 1

        print(f"\nResults: {passed}/{total} edge cases passed")
        return passed == total

    def test_message_filtering(self):
        """Test message filtering and deduplication"""
        print(f"\n{'='*70}")
        print(f"TEST 6: Message Filtering")
        print('='*70)

        # Send messages to different recipients
        self.client.send('browser', 'command', {'text': 'To browser'})
        self.client.send('desktop', 'command', {'text': 'To desktop'})
        self.client.send('all', 'broadcast', {'text': 'To all'})

        time.sleep(1)

        # Poll as browser
        browser_msgs = self.client.poll(recipient='browser')
        all_msgs = self.client.poll(recipient='all')

        print(f"  Browser-specific messages: {len(browser_msgs)}")
        print(f"  All messages: {len(all_msgs)}")

        # Should have at least 2 messages for browser (browser + all)
        if len(browser_msgs) >= 2:
            print("  ✅ Message filtering works")
            return True
        else:
            print("  ❌ Message filtering failed")
            return False

    def print_summary(self):
        """Print test summary"""
        elapsed = (self.results['end_time'] - self.results['start_time']) if self.results['end_time'] else 0

        print("\n" + "="*70)
        print("STRESS TEST SUMMARY")
        print("="*70)
        print(f"Duration: {elapsed:.2f}s")
        print(f"Messages Sent: {self.results['total_sent']}")
        print(f"Messages Received: {self.results['total_received']}")
        print(f"Timeouts: {self.results['timeouts']}")
        print(f"Errors: {self.results['errors']}")

        if self.results['latencies']:
            print(f"\nLatency Statistics:")
            print(f"  Min: {min(self.results['latencies']):.2f}s")
            print(f"  Max: {max(self.results['latencies']):.2f}s")
            print(f"  Avg: {statistics.mean(self.results['latencies']):.2f}s")
            print(f"  Median: {statistics.median(self.results['latencies']):.2f}s")

        success_rate = (self.results['total_received'] / self.results['total_sent'] * 100) if self.results['total_sent'] > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if success_rate >= 95:
            print("✅ EXCELLENT")
        elif success_rate >= 85:
            print("⚠️  GOOD (some issues)")
        elif success_rate >= 70:
            print("⚠️  FAIR (significant issues)")
        else:
            print("❌ POOR (major issues)")

        print("="*70)

        # Recommendations
        if self.results['timeouts'] > 0:
            print("\n⚠️  Recommendations:")
            print(f"  - {self.results['timeouts']} timeouts detected")
            print("  - Check browser extension is loaded")
            print("  - Verify fresh claude.ai tab is open")
            print("  - Consider increasing timeout thresholds")

        if self.results['errors'] > 0:
            print(f"\n❌ {self.results['errors']} errors detected - check logs")

def main():
    print("="*70)
    print("🧪 MULTI-CLAUDE BRIDGE - STRESS TEST SUITE")
    print("="*70)
    print("\nThis will run 100+ interactions to test:")
    print("  - Sequential messaging")
    print("  - Rapid fire messaging")
    print("  - Concurrent messaging")
    print("  - Large payloads")
    print("  - Edge cases")
    print("  - Message filtering")
    print("\nPrerequisites:")
    print("  ✅ server.py running (or server_v2.py)")
    print("  ✅ Fresh claude.ai tab open")
    print("  ✅ Extension loaded and working")
    print()

    # Check for --auto flag
    if '--auto' not in sys.argv and '-y' not in sys.argv:
        response = input("Ready to start? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    else:
        print("Running in auto mode...")

    test = StressTest()
    test.results['start_time'] = time.time()

    # Run test suite
    try:
        test.test_sequential_messages(10)
        time.sleep(2)

        test.test_rapid_fire(20)
        time.sleep(2)

        test.test_concurrent_messages(10)
        time.sleep(2)

        test.test_large_payload()
        time.sleep(2)

        test.test_edge_cases()
        time.sleep(2)

        test.test_message_filtering()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")

    test.results['end_time'] = time.time()
    test.print_summary()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"stress_test_{timestamp}.txt"

    with open(report_file, 'w') as f:
        f.write(f"Stress Test Report - {timestamp}\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total Sent: {test.results['total_sent']}\n")
        f.write(f"Total Received: {test.results['total_received']}\n")
        f.write(f"Timeouts: {test.results['timeouts']}\n")
        f.write(f"Errors: {test.results['errors']}\n")
        if test.results['latencies']:
            f.write(f"\nLatency (avg): {statistics.mean(test.results['latencies']):.2f}s\n")

    print(f"\n📊 Report saved to: {report_file}")

if __name__ == '__main__':
    main()
