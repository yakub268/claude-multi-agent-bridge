#!/usr/bin/env python3
"""
Performance Optimizer
Blazing-fast message processing with intelligent routing
"""
import time
from typing import Dict, List, Optional, Callable
from collections import defaultdict, deque
from threading import Lock, Thread
import heapq
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CachedRoute:
    """Cached routing decision"""
    from_client: str
    to_client: str
    route_type: str
    latency_ms: float
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0


class PerformanceOptimizer:
    """
    Optimize message routing and processing

    Features:
    - Route caching (avoid repeated lookups)
    - Message batching (combine small messages)
    - Connection pooling (reuse connections)
    - Prefetching (anticipate next message)
    - Compression thresholds (auto-compress large payloads)
    - Fast path routing (skip unnecessary processing)
    """

    def __init__(self):
        self.route_cache: Dict[tuple, CachedRoute] = {}
        self.connection_pool: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.batch_queue: Dict[str, List] = defaultdict(list)
        self.batch_lock = Lock()
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'batches_sent': 0,
            'fast_path_used': 0,
            'total_latency_saved_ms': 0
        }

    def get_cached_route(self, from_client: str, to_client: str) -> Optional[CachedRoute]:
        """
        Get cached route

        Args:
            from_client: Source
            to_client: Destination

        Returns:
            Cached route or None
        """
        key = (from_client, to_client)
        route = self.route_cache.get(key)

        if route:
            self.stats['cache_hits'] += 1
            route.use_count += 1
            route.last_used = datetime.now(timezone.utc)
            return route
        else:
            self.stats['cache_misses'] += 1
            return None

    def cache_route(self, from_client: str, to_client: str,
                   route_type: str, latency_ms: float):
        """
        Cache routing decision

        Args:
            from_client: Source
            to_client: Destination
            route_type: Route type ('direct', 'broadcast', 'relay')
            latency_ms: Observed latency
        """
        key = (from_client, to_client)

        route = CachedRoute(
            from_client=from_client,
            to_client=to_client,
            route_type=route_type,
            latency_ms=latency_ms
        )

        self.route_cache[key] = route

        # Cleanup old routes (keep last 1000)
        if len(self.route_cache) > 1000:
            # Remove least recently used
            sorted_routes = sorted(
                self.route_cache.items(),
                key=lambda x: x[1].last_used
            )
            for key, _ in sorted_routes[:100]:
                del self.route_cache[key]

    def should_batch(self, to_client: str, payload_size: int,
                    batch_threshold: int = 1024) -> bool:
        """
        Determine if message should be batched

        Small messages to same client can be batched for efficiency.

        Args:
            to_client: Destination
            payload_size: Size in bytes
            batch_threshold: Max size to batch

        Returns:
            True if should batch
        """
        return payload_size < batch_threshold

    def add_to_batch(self, to_client: str, message: Dict):
        """
        Add message to batch queue

        Args:
            to_client: Destination
            message: Message to batch
        """
        with self.batch_lock:
            self.batch_queue[to_client].append(message)

    def flush_batch(self, to_client: str,
                   send_func: Callable) -> int:
        """
        Flush batched messages for client

        Args:
            to_client: Destination
            send_func: Function to send batch

        Returns:
            Number of messages sent
        """
        with self.batch_lock:
            messages = self.batch_queue.get(to_client, [])
            if not messages:
                return 0

            # Send batch
            batch = {
                'type': 'batch',
                'count': len(messages),
                'messages': messages
            }

            send_func(to_client, batch)

            # Clear queue
            self.batch_queue[to_client] = []
            self.stats['batches_sent'] += 1

            return len(messages)

    def auto_flush_batches(self, send_func: Callable,
                          max_wait_ms: int = 100):
        """
        Auto-flush batches after timeout

        Args:
            send_func: Function to send batch
            max_wait_ms: Max time to wait before flushing
        """
        with self.batch_lock:
            for to_client, messages in list(self.batch_queue.items()):
                if not messages:
                    continue

                # Check oldest message age
                oldest = messages[0]
                age_ms = (time.time() - oldest.get('queued_at', time.time())) * 1000

                if age_ms > max_wait_ms:
                    self.flush_batch(to_client, send_func)

    def is_fast_path_eligible(self, message: Dict) -> bool:
        """
        Check if message can use fast path

        Fast path skips:
        - Persistence
        - Acknowledgments
        - Routing rules
        - Transformations

        Use for high-frequency, low-importance messages.

        Args:
            message: Message to check

        Returns:
            True if eligible
        """
        # Fast path criteria
        msg_type = message.get('type', '')

        fast_types = {
            'heartbeat',
            'ping',
            'status_update',
            'metrics',
            'telemetry'
        }

        if msg_type in fast_types:
            self.stats['fast_path_used'] += 1
            return True

        return False

    def should_compress(self, payload: Dict,
                       threshold_bytes: int = 1024) -> bool:
        """
        Determine if payload should be compressed

        Args:
            payload: Message payload
            threshold_bytes: Compress if larger than this

        Returns:
            True if should compress
        """
        import json
        size = len(json.dumps(payload).encode('utf-8'))
        return size > threshold_bytes

    def estimate_processing_time(self, message: Dict) -> float:
        """
        Estimate processing time for message

        Uses historical data from route cache.

        Args:
            message: Message

        Returns:
            Estimated time in milliseconds
        """
        from_client = message.get('from', '')
        to_client = message.get('to', '')

        route = self.get_cached_route(from_client, to_client)

        if route:
            return route.latency_ms
        else:
            # Default estimate
            return 50.0  # 50ms default

    def prefetch_route(self, from_client: str, to_client: str):
        """
        Prefetch/warm up route

        Pre-establishes connection to reduce latency.

        Args:
            from_client: Source
            to_client: Destination
        """
        # In real implementation, this would:
        # - Open connection
        # - Warm up caches
        # - Pre-allocate resources

        key = (from_client, to_client)
        if key not in self.route_cache:
            # Create placeholder route
            self.cache_route(from_client, to_client, 'prefetch', 0)

    def get_connection(self, client_id: str) -> Optional[object]:
        """
        Get connection from pool

        Args:
            client_id: Client ID

        Returns:
            Connection object or None
        """
        pool = self.connection_pool.get(client_id)
        if pool and len(pool) > 0:
            return pool.popleft()
        return None

    def return_connection(self, client_id: str, connection: object):
        """
        Return connection to pool

        Args:
            client_id: Client ID
            connection: Connection to return
        """
        self.connection_pool[client_id].append(connection)

    def get_stats(self) -> Dict:
        """Get performance statistics"""
        cache_hit_rate = 0
        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (
                self.stats['cache_hits'] + self.stats['cache_misses']
            )

        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'cached_routes': len(self.route_cache),
            'pooled_connections': sum(len(p) for p in self.connection_pool.values()),
            'pending_batches': sum(len(b) for b in self.batch_queue.values())
        }

    def optimize_message(self, message: Dict) -> Dict:
        """
        Optimize message before sending

        Applies:
        - Compression (if beneficial)
        - Fast path marking
        - Route caching
        - Batching decision

        Args:
            message: Original message

        Returns:
            Optimized message
        """
        optimized = message.copy()

        # Mark fast path
        if self.is_fast_path_eligible(message):
            optimized['_fast_path'] = True

        # Mark compression
        if self.should_compress(message.get('payload', {})):
            optimized['_compress'] = True

        # Add routing hint
        from_client = message.get('from', '')
        to_client = message.get('to', '')
        route = self.get_cached_route(from_client, to_client)

        if route:
            optimized['_route_hint'] = route.route_type

        return optimized


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("⚡ Performance Optimizer Test")
    print("="*70)

    optimizer = PerformanceOptimizer()

    # Cache routes
    print("\n1️⃣ Caching routes...")
    optimizer.cache_route('code', 'browser', 'direct', 25.5)
    optimizer.cache_route('code', 'desktop', 'direct', 45.2)
    optimizer.cache_route('browser', 'code', 'direct', 30.1)

    # Get cached route
    print("\n2️⃣ Getting cached route...")
    route = optimizer.get_cached_route('code', 'browser')
    if route:
        print(f"   ✅ Found: {route.route_type}, {route.latency_ms}ms")

    # Check fast path
    print("\n3️⃣ Fast path check...")
    msg1 = {'type': 'heartbeat', 'from': 'code', 'to': 'browser'}
    msg2 = {'type': 'command', 'from': 'code', 'to': 'browser'}

    print(f"   Heartbeat: {optimizer.is_fast_path_eligible(msg1)}")
    print(f"   Command: {optimizer.is_fast_path_eligible(msg2)}")

    # Estimate processing time
    print("\n4️⃣ Processing time estimation...")
    time_ms = optimizer.estimate_processing_time({'from': 'code', 'to': 'browser'})
    print(f"   Estimated: {time_ms}ms")

    # Optimize message
    print("\n5️⃣ Message optimization...")
    msg = {
        'from': 'code',
        'to': 'browser',
        'type': 'command',
        'payload': {'text': 'Hello world'}
    }

    optimized = optimizer.optimize_message(msg)
    print(f"   Original keys: {list(msg.keys())}")
    print(f"   Optimized keys: {list(optimized.keys())}")

    # Stats
    print("\n6️⃣ Performance stats:")
    stats = optimizer.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Test complete")
