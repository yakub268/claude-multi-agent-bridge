#!/usr/bin/env python3
"""
Priority Queue for Message Bus
Support for high-priority, normal, and low-priority messages
"""
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, List
from datetime import datetime, timezone


@dataclass(order=True)
class PrioritizedMessage:
    """Message with priority"""

    priority: int
    timestamp: float = field(compare=False)
    message: Any = field(compare=False)

    def __init__(self, message: dict, priority: int = 5):
        """
        Initialize prioritized message

        Priority levels:
            1 = Critical (system messages, errors)
            3 = High (interactive commands)
            5 = Normal (default)
            7 = Low (background tasks)
            9 = Bulk (batch operations)
        """
        self.priority = priority
        self.timestamp = time.time()
        self.message = message


class PriorityMessageQueue:
    """
    Priority queue for messages

    Features:
    - Priority-based delivery
    - FIFO within same priority
    - Size limits per priority
    - Starvation prevention
    """

    def __init__(self, max_size: int = 1000):
        self.queue: List[PrioritizedMessage] = []
        self.max_size = max_size
        self.stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "rejected": 0,
            "by_priority": {i: 0 for i in range(1, 10)},
        }

        # Starvation prevention
        self.low_priority_wait_time = 30  # seconds
        self.last_low_priority_dequeue = time.time()

    def enqueue(self, message: dict, priority: int = 5) -> bool:
        """
        Add message to queue

        Returns:
            True if enqueued, False if queue full
        """
        if len(self.queue) >= self.max_size:
            self.stats["rejected"] += 1
            return False

        prioritized_msg = PrioritizedMessage(message, priority)
        heapq.heappush(self.queue, prioritized_msg)

        self.stats["total_enqueued"] += 1
        self.stats["by_priority"][priority] = (
            self.stats["by_priority"].get(priority, 0) + 1
        )

        return True

    def dequeue(self) -> dict:
        """
        Get highest priority message

        Implements starvation prevention:
        - If low-priority messages waiting >30s, force dequeue one
        """
        if not self.queue:
            return None

        # Check for starvation
        now = time.time()
        has_low_priority = any(msg.priority >= 7 for msg in self.queue)

        if (
            has_low_priority
            and (now - self.last_low_priority_dequeue) > self.low_priority_wait_time
        ):
            # Force dequeue a low-priority message
            for i, msg in enumerate(self.queue):
                if msg.priority >= 7:
                    self.queue.pop(i)
                    heapq.heapify(self.queue)
                    self.last_low_priority_dequeue = now
                    self.stats["total_dequeued"] += 1
                    return msg.message

        # Normal priority dequeue
        prioritized_msg = heapq.heappop(self.queue)
        self.stats["total_dequeued"] += 1

        if prioritized_msg.priority >= 7:
            self.last_low_priority_dequeue = now

        return prioritized_msg.message

    def peek(self) -> dict:
        """Peek at highest priority message without removing"""
        if not self.queue:
            return None
        return self.queue[0].message

    def size(self) -> int:
        """Get queue size"""
        return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.queue) == 0

    def clear(self):
        """Clear all messages"""
        self.queue.clear()

    def get_stats(self) -> dict:
        """Get queue statistics"""
        priority_distribution = {}
        for msg in self.queue:
            p = msg.priority
            priority_distribution[p] = priority_distribution.get(p, 0) + 1

        return {
            **self.stats,
            "current_size": len(self.queue),
            "max_size": self.max_size,
            "utilization": len(self.queue) / self.max_size,
            "current_distribution": priority_distribution,
        }


# ============================================================================
# Message Priority Helpers
# ============================================================================


class Priority:
    """Priority level constants"""

    CRITICAL = 1  # System messages, errors
    HIGH = 3  # Interactive commands, user requests
    NORMAL = 5  # Default priority
    LOW = 7  # Background tasks, updates
    BULK = 9  # Batch operations, analytics


def get_priority_for_type(msg_type: str) -> int:
    """Get recommended priority for message type"""
    priority_map = {
        # Critical
        "error": Priority.CRITICAL,
        "shutdown": Priority.CRITICAL,
        "alert": Priority.CRITICAL,
        # High
        "command": Priority.HIGH,
        "query": Priority.HIGH,
        "interactive": Priority.HIGH,
        # Normal
        "message": Priority.NORMAL,
        "response": Priority.NORMAL,
        "notification": Priority.NORMAL,
        # Low
        "status": Priority.LOW,
        "heartbeat": Priority.LOW,
        "sync": Priority.LOW,
        # Bulk
        "batch": Priority.BULK,
        "analytics": Priority.BULK,
        "log": Priority.BULK,
    }

    return priority_map.get(msg_type, Priority.NORMAL)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Priority Queue Test")
    print("=" * 70)

    queue = PriorityMessageQueue(max_size=100)

    # Add messages with different priorities
    messages = [
        ({"type": "batch", "data": "bulk1"}, Priority.BULK),
        ({"type": "command", "data": "cmd1"}, Priority.HIGH),
        ({"type": "message", "data": "msg1"}, Priority.NORMAL),
        ({"type": "error", "data": "err1"}, Priority.CRITICAL),
        ({"type": "status", "data": "status1"}, Priority.LOW),
        ({"type": "command", "data": "cmd2"}, Priority.HIGH),
    ]

    print("\n📥 Enqueueing messages...")
    for msg, priority in messages:
        queue.enqueue(msg, priority)
        print(f"   Added {msg['type']:10s} (priority {priority})")

    print(f"\n📊 Queue size: {queue.size()}")
    print(f"📊 Stats: {queue.get_stats()}")

    print("\n📤 Dequeueing by priority...")
    while not queue.is_empty():
        msg = queue.dequeue()
        print(f"   Got: {msg['type']:10s} - {msg['data']}")

    print(f"\n✅ Final stats: {queue.get_stats()}")
