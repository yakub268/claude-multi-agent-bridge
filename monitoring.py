#!/usr/bin/env python3
"""
Prometheus Monitoring for Claude Multi-Agent Bridge

Exposes metrics:
- Message throughput (messages/sec, messages/min)
- WebSocket connections (active, total, errors)
- Collaboration rooms (active, members, messages)
- Latency (message delivery, room operations)
- Error rates (by type)

Usage:
    python monitoring.py  # Start on port 9090
    # Metrics available at http://localhost:9090/metrics
"""
import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics disabled")
    logger.warning("Install with: pip install prometheus-client")


@dataclass
class MetricsCollector:
    """
    Collects and exposes Prometheus metrics

    Metrics categories:
    - Message metrics: total, rate, errors
    - Connection metrics: active, total, by client
    - Room metrics: active, members, messages
    - Latency metrics: p50, p95, p99
    """

    # Internal state
    _message_count: int = 0
    _connection_count: int = 0
    _error_count: int = 0
    _room_count: int = 0

    # Time windows for rate calculation
    _message_timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    _latencies: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Active tracking
    _active_connections: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _active_rooms: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not PROMETHEUS_AVAILABLE:
            return

        # Define Prometheus metrics
        self.messages_total = Counter(
            'bridge_messages_total',
            'Total messages sent through bridge',
            ['from_client', 'to_client']
        )

        self.messages_errors = Counter(
            'bridge_messages_errors_total',
            'Total message errors',
            ['error_type']
        )

        self.connections_active = Gauge(
            'bridge_connections_active',
            'Currently active WebSocket connections',
            ['client_id']
        )

        self.connections_total = Counter(
            'bridge_connections_total',
            'Total WebSocket connections',
            ['client_id']
        )

        self.rooms_active = Gauge(
            'bridge_rooms_active',
            'Currently active collaboration rooms'
        )

        self.room_members = Gauge(
            'bridge_room_members',
            'Members in collaboration room',
            ['room_id']
        )

        self.room_messages = Counter(
            'bridge_room_messages_total',
            'Total room messages',
            ['room_id', 'channel']
        )

        self.message_latency = Histogram(
            'bridge_message_latency_seconds',
            'Message delivery latency',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )

        self.operation_latency = Summary(
            'bridge_operation_duration_seconds',
            'Operation duration',
            ['operation']
        )

        logger.info("✅ Prometheus metrics initialized")

    # ========================================================================
    # Message Metrics
    # ========================================================================

    def record_message(self, from_client: str, to_client: str, latency_ms: Optional[float] = None):
        """Record a message sent"""
        self._message_count += 1
        self._message_timestamps.append(time.time())

        if PROMETHEUS_AVAILABLE:
            self.messages_total.labels(from_client=from_client, to_client=to_client).inc()

            if latency_ms is not None:
                self.message_latency.observe(latency_ms / 1000.0)
                self._latencies.append(latency_ms)

    def record_message_error(self, error_type: str):
        """Record a message error"""
        self._error_count += 1

        if PROMETHEUS_AVAILABLE:
            self.messages_errors.labels(error_type=error_type).inc()

    def get_message_rate(self, window_seconds: int = 60) -> float:
        """Calculate messages per second over window"""
        cutoff = time.time() - window_seconds
        recent = sum(1 for ts in self._message_timestamps if ts >= cutoff)
        return recent / window_seconds if window_seconds > 0 else 0.0

    # ========================================================================
    # Connection Metrics
    # ========================================================================

    def record_connection_open(self, client_id: str):
        """Record new connection"""
        self._connection_count += 1
        self._active_connections[client_id] += 1

        if PROMETHEUS_AVAILABLE:
            self.connections_total.labels(client_id=client_id).inc()
            self.connections_active.labels(client_id=client_id).set(self._active_connections[client_id])

    def record_connection_close(self, client_id: str):
        """Record connection closed"""
        if client_id in self._active_connections:
            self._active_connections[client_id] -= 1

            if self._active_connections[client_id] <= 0:
                del self._active_connections[client_id]

            if PROMETHEUS_AVAILABLE:
                self.connections_active.labels(client_id=client_id).set(
                    self._active_connections.get(client_id, 0)
                )

    def get_active_connections(self) -> int:
        """Get total active connections"""
        return sum(self._active_connections.values())

    # ========================================================================
    # Room Metrics
    # ========================================================================

    def record_room_created(self, room_id: str):
        """Record new room"""
        self._room_count += 1
        self._active_rooms[room_id] = 0

        if PROMETHEUS_AVAILABLE:
            self.rooms_active.set(len(self._active_rooms))

    def record_room_closed(self, room_id: str):
        """Record room closed"""
        if room_id in self._active_rooms:
            del self._active_rooms[room_id]

            if PROMETHEUS_AVAILABLE:
                self.rooms_active.set(len(self._active_rooms))
                # Set room members to 0 instead of remove (which doesn't exist)
                self.room_members.labels(room_id=room_id).set(0)

    def record_room_member_join(self, room_id: str):
        """Record member joined room"""
        if room_id in self._active_rooms:
            self._active_rooms[room_id] += 1

            if PROMETHEUS_AVAILABLE:
                self.room_members.labels(room_id=room_id).set(self._active_rooms[room_id])

    def record_room_member_leave(self, room_id: str):
        """Record member left room"""
        if room_id in self._active_rooms:
            self._active_rooms[room_id] -= 1

            if PROMETHEUS_AVAILABLE:
                self.room_members.labels(room_id=room_id).set(self._active_rooms[room_id])

    def record_room_message(self, room_id: str, channel: str = "main"):
        """Record room message"""
        if PROMETHEUS_AVAILABLE:
            self.room_messages.labels(room_id=room_id, channel=channel).inc()

    # ========================================================================
    # Latency Metrics
    # ========================================================================

    def get_latency_percentile(self, percentile: float) -> Optional[float]:
        """Get latency percentile (p50, p95, p99)"""
        if not self._latencies:
            return None

        sorted_latencies = sorted(self._latencies)
        index = int(len(sorted_latencies) * percentile)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    # ========================================================================
    # Summary
    # ========================================================================

    def get_summary(self) -> Dict:
        """Get metrics summary"""
        return {
            'messages': {
                'total': self._message_count,
                'rate_per_second': round(self.get_message_rate(60), 2),
                'errors': self._error_count
            },
            'connections': {
                'total': self._connection_count,
                'active': self.get_active_connections(),
                'by_client': dict(self._active_connections)
            },
            'rooms': {
                'total': self._room_count,
                'active': len(self._active_rooms),
                'members_by_room': dict(self._active_rooms)
            },
            'latency': {
                'p50_ms': self.get_latency_percentile(0.50),
                'p95_ms': self.get_latency_percentile(0.95),
                'p99_ms': self.get_latency_percentile(0.99)
            }
        }


# Flask endpoint for /metrics
def create_metrics_endpoint():
    """Create Flask endpoint for Prometheus scraping"""
    from flask import Flask, Response

    app = Flask(__name__)

    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        if not PROMETHEUS_AVAILABLE:
            return Response("Prometheus client not installed", status=500)

        return Response(generate_latest(REGISTRY), mimetype='text/plain')

    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}

    return app


# Standalone monitoring server
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus monitoring server")
    parser.add_argument('--port', type=int, default=9090, help='Metrics port')
    parser.add_argument('--host', default='0.0.0.0', help='Bind host')

    args = parser.parse_args()

    if not PROMETHEUS_AVAILABLE:
        print("ERROR: prometheus-client not installed")
        print("Install with: pip install prometheus-client")
        exit(1)

    print("=" * 80)
    print("📊 PROMETHEUS MONITORING SERVER")
    print("=" * 80)
    print()
    print(f"Metrics endpoint: http://{args.host}:{args.port}/metrics")
    print(f"Health endpoint:  http://{args.host}:{args.port}/health")
    print()
    print("Configure Prometheus to scrape:")
    print("""
scrape_configs:
  - job_name: 'claude-bridge'
    static_configs:
      - targets: ['{args.host}:{args.port}']
""")
    print("=" * 80)
    print()

    app = create_metrics_endpoint()
    app.run(host=args.host, port=args.port)
