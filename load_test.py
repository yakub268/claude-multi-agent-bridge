#!/usr/bin/env python3
"""
Load Testing for Claude Multi-Agent Bridge

Tests:
1. Message throughput (100+ concurrent clients)
2. WebSocket connection handling
3. Room creation/joining under load
4. Message latency under stress
5. Error rate monitoring

Usage:
    python load_test.py --clients 100 --duration 60
"""
import time
import json
import asyncio
import logging
import statistics
from datetime import datetime, timezone
from typing import List, Dict
from collections import defaultdict
from dataclasses import dataclass, field

import requests
import websocket

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestResults:
    """Results from load test"""

    total_clients: int
    duration_seconds: float
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    connection_errors: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def get_summary(self) -> Dict:
        """Get test summary"""
        throughput = (
            self.messages_sent / self.duration_seconds
            if self.duration_seconds > 0
            else 0
        )

        latency_stats = {}
        if self.latencies_ms:
            latency_stats = {
                "min_ms": round(min(self.latencies_ms), 2),
                "max_ms": round(max(self.latencies_ms), 2),
                "mean_ms": round(statistics.mean(self.latencies_ms), 2),
                "p50_ms": round(statistics.median(self.latencies_ms), 2),
                "p95_ms": (
                    round(statistics.quantiles(self.latencies_ms, n=20)[18], 2)
                    if len(self.latencies_ms) > 20
                    else None
                ),
                "p99_ms": (
                    round(statistics.quantiles(self.latencies_ms, n=100)[98], 2)
                    if len(self.latencies_ms) > 100
                    else None
                ),
            }

        return {
            "test_config": {
                "total_clients": self.total_clients,
                "duration_seconds": self.duration_seconds,
            },
            "throughput": {
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "messages_per_second": round(throughput, 2),
            },
            "errors": {
                "total": self.errors,
                "connection_errors": self.connection_errors,
                "by_type": dict(self.errors_by_type),
            },
            "latency": latency_stats,
            "success_rate": round(
                (1 - self.errors / max(self.messages_sent, 1)) * 100, 2
            ),
        }


class LoadTestClient:
    """Single client for load testing"""

    def __init__(self, client_id: str, server_url: str, ws_url: str):
        self.client_id = client_id
        self.server_url = server_url
        self.ws_url = ws_url
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = 0
        self.latencies = []
        self.ws = None

    def connect_ws(self) -> bool:
        """Connect WebSocket"""
        try:
            ws_url = f"{self.ws_url}/ws/{self.client_id}"
            self.ws = websocket.create_connection(ws_url, timeout=10)
            return True
        except Exception as e:
            logger.error(f"[{self.client_id}] WS connection failed: {e}")
            self.errors += 1
            return False

    def send_message(self, to: str, text: str) -> bool:
        """Send message via REST"""
        try:
            start = time.time()

            response = requests.post(
                f"{self.server_url}/message",
                json={
                    "from": self.client_id,
                    "to": to,
                    "text": text,
                    "timestamp": int(time.time() * 1000),
                },
                timeout=5,
            )

            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                self.messages_sent += 1
                self.latencies.append(latency)
                return True
            else:
                self.errors += 1
                return False

        except Exception as e:
            self.errors += 1
            return False

    def receive_ws_messages(self, timeout: float = 1.0) -> int:
        """Receive messages via WebSocket"""
        if not self.ws:
            return 0

        count = 0
        deadline = time.time() + timeout

        try:
            while time.time() < deadline:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break

                self.ws.settimeout(remaining)
                msg = self.ws.recv()

                if msg:
                    count += 1
                    self.messages_received += 1

        except websocket.WebSocketTimeoutException:
            pass
        except Exception as e:
            logger.error(f"[{self.client_id}] Receive error: {e}")
            self.errors += 1

        return count

    def close(self):
        """Close connection"""
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}, continuing anyway")
                pass


class LoadTester:
    """Load testing coordinator"""

    def __init__(
        self,
        server_url: str = "http://localhost:5001",
        ws_url: str = "ws://localhost:5001",
    ):
        self.server_url = server_url
        self.ws_url = ws_url

    def run_throughput_test(
        self, num_clients: int = 100, duration_seconds: int = 60, message_rate: int = 10
    ) -> LoadTestResults:
        """
        Test message throughput

        Args:
            num_clients: Number of concurrent clients
            duration_seconds: Test duration
            message_rate: Messages per second per client

        Returns:
            LoadTestResults with metrics
        """
        logger.info("=" * 80)
        logger.info("🚀 THROUGHPUT TEST")
        logger.info("=" * 80)
        logger.info(f"Clients: {num_clients}")
        logger.info(f"Duration: {duration_seconds}s")
        logger.info(f"Rate: {message_rate} msg/s per client")
        logger.info(
            f"Expected total: {num_clients * message_rate * duration_seconds} messages"
        )
        logger.info("=" * 80)

        # Create clients
        clients = [
            LoadTestClient(f"load-test-{i}", self.server_url, self.ws_url)
            for i in range(num_clients)
        ]

        # Connect all clients
        logger.info("Connecting clients...")
        connected = 0
        for client in clients:
            if client.connect_ws():
                connected += 1

        logger.info(f"✅ Connected: {connected}/{num_clients}")

        # Run test
        logger.info("Starting message flood...")
        start_time = time.time()
        message_interval = 1.0 / message_rate

        while time.time() - start_time < duration_seconds:
            cycle_start = time.time()

            # Each client sends one message
            for i, client in enumerate(clients):
                target = clients[(i + 1) % len(clients)].client_id
                client.send_message(target, f"Load test message {client.messages_sent}")

            # Wait for next cycle
            elapsed = time.time() - cycle_start
            if elapsed < message_interval:
                time.sleep(message_interval - elapsed)

        actual_duration = time.time() - start_time
        logger.info(f"✅ Test complete ({actual_duration:.1f}s)")

        # Collect results
        results = LoadTestResults(
            total_clients=num_clients, duration_seconds=actual_duration
        )

        for client in clients:
            results.messages_sent += client.messages_sent
            results.messages_received += client.messages_received
            results.errors += client.errors
            results.latencies_ms.extend(client.latencies)

            # Close client
            client.close()

        return results

    def run_connection_test(self, num_clients: int = 500) -> LoadTestResults:
        """
        Test WebSocket connection handling

        Args:
            num_clients: Number of simultaneous connections

        Returns:
            LoadTestResults with metrics
        """
        logger.info("=" * 80)
        logger.info("🔌 CONNECTION TEST")
        logger.info("=" * 80)
        logger.info(f"Connections: {num_clients}")
        logger.info("=" * 80)

        clients = [
            LoadTestClient(f"conn-test-{i}", self.server_url, self.ws_url)
            for i in range(num_clients)
        ]

        start = time.time()
        connected = 0
        errors = 0

        for client in clients:
            if client.connect_ws():
                connected += 1
            else:
                errors += 1

        duration = time.time() - start

        logger.info(f"✅ Connected: {connected}/{num_clients}")
        logger.info(f"❌ Errors: {errors}")
        logger.info(f"⏱️  Duration: {duration:.2f}s")

        # Close all
        for client in clients:
            client.close()

        results = LoadTestResults(
            total_clients=num_clients,
            duration_seconds=duration,
            connection_errors=errors,
        )

        return results

    def run_room_test(
        self, num_rooms: int = 50, members_per_room: int = 5
    ) -> LoadTestResults:
        """
        Test collaboration room handling

        Args:
            num_rooms: Number of rooms to create
            members_per_room: Members in each room

        Returns:
            LoadTestResults with metrics
        """
        logger.info("=" * 80)
        logger.info("🏢 ROOM TEST")
        logger.info("=" * 80)
        logger.info(f"Rooms: {num_rooms}")
        logger.info(f"Members per room: {members_per_room}")
        logger.info(f"Total operations: {num_rooms * (1 + members_per_room)}")
        logger.info("=" * 80)

        start = time.time()
        successes = 0
        errors = 0

        for room_i in range(num_rooms):
            room_id = f"load-test-room-{room_i}"

            # Create room
            try:
                response = requests.post(
                    f"{self.server_url}/collab/room",
                    json={"room_id": room_id, "topic": f"Load test room {room_i}"},
                    timeout=5,
                )

                if response.status_code == 200:
                    successes += 1
                else:
                    errors += 1

                # Join members
                for member_i in range(members_per_room):
                    client_id = f"room-{room_i}-member-{member_i}"

                    response = requests.post(
                        f"{self.server_url}/collab/room/{room_id}/join",
                        json={"client_id": client_id, "role": "member"},
                        timeout=5,
                    )

                    if response.status_code == 200:
                        successes += 1
                    else:
                        errors += 1

            except Exception as e:
                logger.error(f"Room {room_i} failed: {e}")
                errors += 1

        duration = time.time() - start

        logger.info(f"✅ Successes: {successes}")
        logger.info(f"❌ Errors: {errors}")
        logger.info(f"⏱️  Duration: {duration:.2f}s")

        results = LoadTestResults(
            total_clients=num_rooms * members_per_room,
            duration_seconds=duration,
            messages_sent=successes,
            errors=errors,
        )

        return results


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load testing for Claude Bridge")
    parser.add_argument("--url", default="http://localhost:5001", help="Server URL")
    parser.add_argument("--ws-url", default="ws://localhost:5001", help="WebSocket URL")
    parser.add_argument(
        "--test", choices=["throughput", "connections", "rooms", "all"], default="all"
    )
    parser.add_argument("--clients", type=int, default=100, help="Number of clients")
    parser.add_argument(
        "--duration", type=int, default=60, help="Test duration (seconds)"
    )
    parser.add_argument(
        "--rate", type=int, default=10, help="Messages per second per client"
    )
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    tester = LoadTester(args.url, args.ws_url)
    all_results = {}

    print()
    print("=" * 80)
    print("🧪 CLAUDE BRIDGE LOAD TESTING")
    print("=" * 80)
    print(f"Server: {args.url}")
    print("=" * 80)
    print()

    if args.test in ["throughput", "all"]:
        results = tester.run_throughput_test(args.clients, args.duration, args.rate)
        all_results["throughput"] = results.get_summary()
        print()
        print("📊 THROUGHPUT RESULTS:")
        print(json.dumps(results.get_summary(), indent=2))
        print()

    if args.test in ["connections", "all"]:
        results = tester.run_connection_test(args.clients)
        all_results["connections"] = results.get_summary()
        print()
        print("📊 CONNECTION RESULTS:")
        print(json.dumps(results.get_summary(), indent=2))
        print()

    if args.test in ["rooms", "all"]:
        results = tester.run_room_test(num_rooms=20, members_per_room=5)
        all_results["rooms"] = results.get_summary()
        print()
        print("📊 ROOM RESULTS:")
        print(json.dumps(results.get_summary(), indent=2))
        print()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"✅ Results saved to {args.output}")

    print("=" * 80)
    print("✅ LOAD TESTING COMPLETE")
    print("=" * 80)
