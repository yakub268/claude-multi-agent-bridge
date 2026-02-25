#!/usr/bin/env python3
"""
Intelligent Load Balancer
Distribute messages across multiple clients for optimal throughput
"""
import time
from typing import Dict, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import random


class LoadStrategy(Enum):
    """Load balancing strategies"""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FASTEST_RESPONSE = "fastest_response"
    RANDOM = "random"
    WEIGHTED = "weighted"
    STICKY_SESSION = "sticky_session"


@dataclass
class ClientMetrics:
    """Metrics for a client"""

    client_id: str
    total_messages: int = 0
    pending_messages: int = 0
    avg_latency_ms: float = 0
    last_latency_ms: float = 0
    success_rate: float = 1.0
    failures: int = 0
    weight: float = 1.0
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    healthy: bool = True


class LoadBalancer:
    """
    Intelligent load balancer for message distribution

    Features:
    - Multiple balancing strategies
    - Client health tracking
    - Automatic failover
    - Weighted distribution
    - Sticky sessions
    - Circuit breaker integration
    """

    def __init__(self, strategy: LoadStrategy = LoadStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.clients: Dict[str, ClientMetrics] = {}
        self.round_robin_index = 0
        self.sessions: Dict[str, str] = {}  # session_id -> client_id
        self.latency_window = deque(maxlen=100)  # Rolling window
        self.stats = {"total_routed": 0, "failovers": 0, "strategy_changes": 0}

    def register_client(self, client_id: str, weight: float = 1.0):
        """
        Register a client for load balancing

        Args:
            client_id: Client identifier
            weight: Weight for weighted strategies (higher = more traffic)
        """
        if client_id not in self.clients:
            self.clients[client_id] = ClientMetrics(client_id=client_id, weight=weight)

    def unregister_client(self, client_id: str):
        """Unregister a client"""
        if client_id in self.clients:
            del self.clients[client_id]

    def mark_unhealthy(self, client_id: str):
        """Mark client as unhealthy"""
        if client_id in self.clients:
            self.clients[client_id].healthy = False

    def mark_healthy(self, client_id: str):
        """Mark client as healthy"""
        if client_id in self.clients:
            self.clients[client_id].healthy = True

    def get_healthy_clients(self) -> List[str]:
        """Get list of healthy clients"""
        return [cid for cid, metrics in self.clients.items() if metrics.healthy]

    def select_client(
        self, session_id: Optional[str] = None, excluded: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select best client for message

        Args:
            session_id: Optional session ID for sticky sessions
            excluded: Clients to exclude (for failover)

        Returns:
            Selected client ID or None
        """
        excluded = excluded or []
        available = [cid for cid in self.get_healthy_clients() if cid not in excluded]

        if not available:
            return None

        self.stats["total_routed"] += 1

        # Sticky session
        if session_id and self.strategy == LoadStrategy.STICKY_SESSION:
            if session_id in self.sessions:
                client = self.sessions[session_id]
                if client in available:
                    return client

            # Assign new sticky client
            client = self._select_by_strategy(available)
            self.sessions[session_id] = client
            return client

        return self._select_by_strategy(available)

    def _select_by_strategy(self, available: List[str]) -> str:
        """
        Select client using configured strategy

        Args:
            available: List of available clients

        Returns:
            Selected client ID
        """
        if self.strategy == LoadStrategy.ROUND_ROBIN:
            return self._round_robin(available)

        elif self.strategy == LoadStrategy.LEAST_LOADED:
            return self._least_loaded(available)

        elif self.strategy == LoadStrategy.FASTEST_RESPONSE:
            return self._fastest_response(available)

        elif self.strategy == LoadStrategy.RANDOM:
            return random.choice(available)

        elif self.strategy == LoadStrategy.WEIGHTED:
            return self._weighted_random(available)

        else:
            return available[0]

    def _round_robin(self, available: List[str]) -> str:
        """Round-robin selection"""
        client = available[self.round_robin_index % len(available)]
        self.round_robin_index += 1
        return client

    def _least_loaded(self, available: List[str]) -> str:
        """Select client with fewest pending messages"""
        return min(available, key=lambda cid: self.clients[cid].pending_messages)

    def _fastest_response(self, available: List[str]) -> str:
        """Select client with lowest average latency"""
        return min(available, key=lambda cid: self.clients[cid].avg_latency_ms)

    def _weighted_random(self, available: List[str]) -> str:
        """Weighted random selection"""
        weights = [self.clients[cid].weight for cid in available]
        return random.choices(available, weights=weights)[0]

    def record_latency(self, client_id: str, latency_ms: float):
        """
        Record latency for client

        Args:
            client_id: Client ID
            latency_ms: Latency in milliseconds
        """
        if client_id not in self.clients:
            return

        metrics = self.clients[client_id]

        # Update last latency
        metrics.last_latency_ms = latency_ms

        # Update average (exponential moving average)
        alpha = 0.3  # Smoothing factor
        if metrics.avg_latency_ms == 0:
            metrics.avg_latency_ms = latency_ms
        else:
            metrics.avg_latency_ms = (
                alpha * latency_ms + (1 - alpha) * metrics.avg_latency_ms
            )

    def record_success(self, client_id: str):
        """Record successful message delivery"""
        if client_id not in self.clients:
            return

        metrics = self.clients[client_id]
        metrics.total_messages += 1

        # Update success rate (exponential moving average)
        alpha = 0.1
        metrics.success_rate = alpha * 1.0 + (1 - alpha) * metrics.success_rate

    def record_failure(self, client_id: str):
        """Record failed message delivery"""
        if client_id not in self.clients:
            return

        metrics = self.clients[client_id]
        metrics.failures += 1

        # Update success rate
        alpha = 0.1
        metrics.success_rate = alpha * 0.0 + (1 - alpha) * metrics.success_rate

        # Mark unhealthy if too many failures
        if metrics.success_rate < 0.5:
            self.mark_unhealthy(client_id)

    def increment_pending(self, client_id: str):
        """Increment pending message count"""
        if client_id in self.clients:
            self.clients[client_id].pending_messages += 1

    def decrement_pending(self, client_id: str):
        """Decrement pending message count"""
        if client_id in self.clients:
            metrics = self.clients[client_id]
            metrics.pending_messages = max(0, metrics.pending_messages - 1)

    def failover(
        self, failed_client: str, session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Failover to another client

        Args:
            failed_client: Failed client ID
            session_id: Optional session ID

        Returns:
            Fallback client ID or None
        """
        self.stats["failovers"] += 1
        self.mark_unhealthy(failed_client)

        # Select new client (excluding failed)
        new_client = self.select_client(session_id=session_id, excluded=[failed_client])

        # Update sticky session
        if session_id and new_client:
            self.sessions[session_id] = new_client

        return new_client

    def change_strategy(self, strategy: LoadStrategy):
        """
        Change load balancing strategy

        Args:
            strategy: New strategy
        """
        self.strategy = strategy
        self.stats["strategy_changes"] += 1

    def get_client_stats(self, client_id: str) -> Optional[Dict]:
        """Get statistics for specific client"""
        if client_id not in self.clients:
            return None

        metrics = self.clients[client_id]

        return {
            "client_id": metrics.client_id,
            "total_messages": metrics.total_messages,
            "pending_messages": metrics.pending_messages,
            "avg_latency_ms": metrics.avg_latency_ms,
            "last_latency_ms": metrics.last_latency_ms,
            "success_rate": metrics.success_rate,
            "failures": metrics.failures,
            "weight": metrics.weight,
            "healthy": metrics.healthy,
            "last_used": metrics.last_used.isoformat(),
        }

    def get_stats(self) -> Dict:
        """Get load balancer statistics"""
        return {
            **self.stats,
            "strategy": self.strategy.value,
            "registered_clients": len(self.clients),
            "healthy_clients": len(self.get_healthy_clients()),
            "total_pending": sum(c.pending_messages for c in self.clients.values()),
            "avg_success_rate": (
                sum(c.success_rate for c in self.clients.values()) / len(self.clients)
                if self.clients
                else 0
            ),
        }

    def get_distribution(self) -> Dict:
        """Get message distribution across clients"""
        return {
            client_id: metrics.total_messages
            for client_id, metrics in self.clients.items()
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("⚖️  Load Balancer Test")
    print("=" * 70)

    # Create load balancer
    lb = LoadBalancer(strategy=LoadStrategy.LEAST_LOADED)

    # Register clients
    print("\n1️⃣ Registering clients...")
    lb.register_client("browser-1", weight=1.0)
    lb.register_client("browser-2", weight=1.5)
    lb.register_client("browser-3", weight=0.8)

    # Simulate traffic
    print("\n2️⃣ Simulating traffic...")
    for i in range(30):
        client = lb.select_client()
        print(f"   Message {i+1} → {client}")

        # Simulate varying latencies
        import random

        latency = random.uniform(10, 100)
        lb.record_latency(client, latency)

        # Simulate success/failure
        if random.random() < 0.95:
            lb.record_success(client)
        else:
            lb.record_failure(client)

    # Stats
    print("\n3️⃣ Load balancer stats:")
    stats = lb.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Distribution
    print("\n4️⃣ Message distribution:")
    dist = lb.get_distribution()
    for client_id, count in dist.items():
        print(f"   {client_id}: {count} messages")

    # Client metrics
    print("\n5️⃣ Client metrics:")
    for client_id in lb.clients.keys():
        metrics = lb.get_client_stats(client_id)
        print(f"\n   📊 {client_id}:")
        print(f"      Total: {metrics['total_messages']}")
        print(f"      Latency: {metrics['avg_latency_ms']:.1f}ms")
        print(f"      Success Rate: {metrics['success_rate']:.1%}")
        print(f"      Health: {'🟢 Healthy' if metrics['healthy'] else '🔴 Unhealthy'}")

    # Test failover
    print("\n6️⃣ Testing failover...")
    failed = "browser-1"
    fallback = lb.failover(failed)
    print(f"   {failed} failed → fallback to {fallback}")

    print("\n✅ Test complete")
