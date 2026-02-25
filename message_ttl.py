#!/usr/bin/env python3
"""
Message TTL (Time-To-Live) Management
Auto-expire messages, scheduled cleanup, retention policies
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import heapq
from threading import Thread, Lock


class RetentionPolicy(Enum):
    """Message retention policies"""

    IMMEDIATE = "immediate"  # Delete after delivery
    SHORT = "short"  # 1 hour
    MEDIUM = "medium"  # 24 hours
    LONG = "long"  # 7 days
    PERMANENT = "permanent"  # Never delete


@dataclass
class TTLConfig:
    """
    TTL configuration for message types

    Example:
        # Delete errors after 1 hour
        TTLConfig(
            message_type="error",
            ttl_seconds=3600,
            policy=RetentionPolicy.SHORT,
            on_expire=lambda msg: print(f"Expired: {msg['id']}")
        )
    """

    message_type: str
    ttl_seconds: int
    policy: RetentionPolicy = RetentionPolicy.MEDIUM
    on_expire: Optional[Callable] = None
    archive_before_delete: bool = False


class MessageTTLManager:
    """
    Manage message expiration and cleanup

    Features:
    - Per-message-type TTL policies
    - Scheduled cleanup (efficient heap-based)
    - Archive expired messages before deletion
    - Statistics on expired messages
    - Manual expiration triggers
    """

    # Default TTL policies
    DEFAULT_POLICIES = {
        RetentionPolicy.IMMEDIATE: 0,
        RetentionPolicy.SHORT: 3600,  # 1 hour
        RetentionPolicy.MEDIUM: 86400,  # 24 hours
        RetentionPolicy.LONG: 604800,  # 7 days
        RetentionPolicy.PERMANENT: -1,  # Never expire
    }

    def __init__(self, default_ttl: int = 86400):
        """
        Initialize TTL manager

        Args:
            default_ttl: Default TTL in seconds (24 hours)
        """
        self.default_ttl = default_ttl
        self.ttl_configs: Dict[str, TTLConfig] = {}
        self.expiry_heap = []  # Min-heap of (expiry_time, message_id)
        self.messages: Dict[str, Dict] = {}  # message_id -> message
        self.lock = Lock()
        self.stats = {"total_expired": 0, "total_archived": 0, "by_type": {}}
        self.archived_messages = []
        self._cleanup_running = False

    def register_policy(self, config: TTLConfig):
        """Register TTL policy for message type"""
        self.ttl_configs[config.message_type] = config

    def add_message(self, message: Dict):
        """
        Add message with TTL tracking

        Args:
            message: Message dict with id, type, timestamp
        """
        with self.lock:
            message_id = message["id"]
            message_type = message.get("type", "default")

            # Get TTL for this message type
            config = self.ttl_configs.get(message_type)

            if config:
                ttl = config.ttl_seconds
            else:
                ttl = self.default_ttl

            # Permanent messages don't expire
            if ttl < 0:
                self.messages[message_id] = message
                return

            # Calculate expiry time
            timestamp = datetime.fromisoformat(message["timestamp"])
            expiry_time = timestamp + timedelta(seconds=ttl)
            expiry_unix = expiry_time.timestamp()

            # Add to heap
            heapq.heappush(self.expiry_heap, (expiry_unix, message_id))
            self.messages[message_id] = message

    def remove_message(self, message_id: str) -> bool:
        """
        Manually remove message

        Args:
            message_id: Message ID to remove

        Returns:
            True if removed
        """
        with self.lock:
            if message_id in self.messages:
                del self.messages[message_id]
                return True
            return False

    def get_message(self, message_id: str) -> Optional[Dict]:
        """
        Get message if not expired

        Args:
            message_id: Message ID

        Returns:
            Message dict or None if expired/not found
        """
        with self.lock:
            return self.messages.get(message_id)

    def cleanup_expired(self) -> int:
        """
        Clean up expired messages

        Returns:
            Number of messages expired
        """
        now = time.time()
        expired_count = 0

        with self.lock:
            # Process expired messages from heap
            while self.expiry_heap:
                expiry_time, message_id = self.expiry_heap[0]

                # Not expired yet
                if expiry_time > now:
                    break

                # Remove from heap
                heapq.heappop(self.expiry_heap)

                # Message might have been manually deleted
                if message_id not in self.messages:
                    continue

                # Get message
                message = self.messages[message_id]
                message_type = message.get("type", "default")

                # Get config
                config = self.ttl_configs.get(message_type)

                # Archive if configured
                if config and config.archive_before_delete:
                    self.archived_messages.append(
                        {
                            **message,
                            "expired_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    self.stats["total_archived"] += 1

                    # Keep only last 1000 archived
                    if len(self.archived_messages) > 1000:
                        self.archived_messages = self.archived_messages[-1000:]

                # Call expiry callback
                if config and config.on_expire:
                    try:
                        config.on_expire(message)
                    except Exception as e:
                        print(f"❌ Error in expiry callback: {e}")

                # Remove message
                del self.messages[message_id]

                # Update stats
                expired_count += 1
                self.stats["total_expired"] += 1
                type_key = message_type
                self.stats["by_type"][type_key] = (
                    self.stats["by_type"].get(type_key, 0) + 1
                )

        return expired_count

    def start_cleanup_worker(self, interval: int = 60):
        """
        Start background cleanup worker

        Args:
            interval: Cleanup interval in seconds (default: 60)
        """
        if self._cleanup_running:
            return

        self._cleanup_running = True

        def worker():
            while self._cleanup_running:
                try:
                    expired = self.cleanup_expired()
                    if expired > 0:
                        print(f"🗑️  Expired {expired} messages")
                except Exception as e:
                    print(f"❌ Cleanup error: {e}")

                time.sleep(interval)

        thread = Thread(target=worker, daemon=True)
        thread.start()

    def stop_cleanup_worker(self):
        """Stop background cleanup worker"""
        self._cleanup_running = False

    def get_stats(self) -> Dict:
        """Get TTL statistics"""
        with self.lock:
            return {
                **self.stats,
                "active_messages": len(self.messages),
                "pending_expiry": len(self.expiry_heap),
                "archived_count": len(self.archived_messages),
            }

    def get_expired_messages(self, limit: int = 100) -> List[Dict]:
        """
        Get recently expired messages

        Args:
            limit: Max messages to return

        Returns:
            List of expired messages
        """
        with self.lock:
            return self.archived_messages[-limit:]

    def get_expiring_soon(self, within_seconds: int = 300) -> List[Dict]:
        """
        Get messages expiring soon

        Args:
            within_seconds: Time window (default: 5 minutes)

        Returns:
            List of messages expiring within time window
        """
        cutoff = time.time() + within_seconds
        expiring = []

        with self.lock:
            for expiry_time, message_id in self.expiry_heap:
                if expiry_time > cutoff:
                    break

                if message_id in self.messages:
                    message = self.messages[message_id]
                    expiring.append(
                        {**message, "expires_in": expiry_time - time.time()}
                    )

        return expiring

    def extend_ttl(self, message_id: str, additional_seconds: int) -> bool:
        """
        Extend TTL for a message

        Args:
            message_id: Message ID
            additional_seconds: Seconds to add to TTL

        Returns:
            True if extended
        """
        with self.lock:
            if message_id not in self.messages:
                return False

            message = self.messages[message_id]

            # Remove old expiry entry (mark as stale)
            # New expiry will be added

            # Calculate new expiry
            current_time = time.time()
            new_expiry = current_time + additional_seconds

            # Add new expiry entry
            heapq.heappush(self.expiry_heap, (new_expiry, message_id))

            return True


# ============================================================================
# Pre-configured Policies
# ============================================================================


class StandardPolicies:
    """Standard TTL policies for common message types"""

    @staticmethod
    def get_error_policy() -> TTLConfig:
        """Error messages - keep for 1 hour"""
        return TTLConfig(
            message_type="error",
            ttl_seconds=3600,
            policy=RetentionPolicy.SHORT,
            archive_before_delete=True,
        )

    @staticmethod
    def get_log_policy() -> TTLConfig:
        """Log messages - keep for 24 hours"""
        return TTLConfig(
            message_type="log",
            ttl_seconds=86400,
            policy=RetentionPolicy.MEDIUM,
            archive_before_delete=False,
        )

    @staticmethod
    def get_command_policy() -> TTLConfig:
        """Command messages - keep for 7 days"""
        return TTLConfig(
            message_type="command",
            ttl_seconds=604800,
            policy=RetentionPolicy.LONG,
            archive_before_delete=True,
        )

    @staticmethod
    def get_notification_policy() -> TTLConfig:
        """Notifications - delete after delivery"""
        return TTLConfig(
            message_type="notification",
            ttl_seconds=0,
            policy=RetentionPolicy.IMMEDIATE,
            archive_before_delete=False,
        )

    @staticmethod
    def get_audit_policy() -> TTLConfig:
        """Audit logs - never delete"""
        return TTLConfig(
            message_type="audit",
            ttl_seconds=-1,
            policy=RetentionPolicy.PERMANENT,
            archive_before_delete=False,
        )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("⏱️  Message TTL Test")
    print("=" * 70)

    # Create manager
    ttl_manager = MessageTTLManager(default_ttl=86400)

    # Register policies
    ttl_manager.register_policy(StandardPolicies.get_error_policy())
    ttl_manager.register_policy(StandardPolicies.get_log_policy())
    ttl_manager.register_policy(StandardPolicies.get_command_policy())

    # Add custom policy with callback
    def on_expire(msg):
        print(f"   📬 Custom expiry callback: {msg['id']} expired")

    ttl_manager.register_policy(
        TTLConfig(
            message_type="custom",
            ttl_seconds=5,  # 5 seconds for testing
            on_expire=on_expire,
            archive_before_delete=True,
        )
    )

    # Add messages
    print("\n📝 Adding messages...")

    # Error message (1 hour TTL)
    error_msg = {
        "id": "msg-error-1",
        "type": "error",
        "payload": {"error": "Test error"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ttl_manager.add_message(error_msg)
    print("   Added: error message (1 hour TTL)")

    # Custom message (5 second TTL for testing)
    custom_msg = {
        "id": "msg-custom-1",
        "type": "custom",
        "payload": {"data": "Test"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ttl_manager.add_message(custom_msg)
    print("   Added: custom message (5 second TTL)")

    # Log message (24 hour TTL)
    log_msg = {
        "id": "msg-log-1",
        "type": "log",
        "payload": {"message": "Test log"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ttl_manager.add_message(log_msg)
    print("   Added: log message (24 hour TTL)")

    # Stats before cleanup
    print("\n📊 Stats before cleanup:")
    stats = ttl_manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Check expiring soon
    print("\n⏰ Messages expiring in next 10 seconds:")
    expiring = ttl_manager.get_expiring_soon(within_seconds=10)
    for msg in expiring:
        print(f"   {msg['id']}: expires in {msg['expires_in']:.1f}s")

    # Wait for expiry
    print("\n⏳ Waiting 6 seconds for custom message to expire...")
    time.sleep(6)

    # Cleanup
    print("\n🗑️  Running cleanup...")
    expired = ttl_manager.cleanup_expired()
    print(f"   Expired {expired} messages")

    # Stats after cleanup
    print("\n📊 Stats after cleanup:")
    stats = ttl_manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Get archived
    print("\n📦 Archived messages:")
    archived = ttl_manager.get_expired_messages(limit=10)
    for msg in archived:
        print(f"   {msg['id']} (expired at {msg['expired_at']})")

    # Test extend TTL
    print("\n➕ Extending TTL for error message...")
    extended = ttl_manager.extend_ttl("msg-error-1", 3600)
    print(f"   Extended: {extended}")

    print("\n✅ Test complete")
