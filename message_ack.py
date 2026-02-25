#!/usr/bin/env python3
"""
Message Acknowledgment System
Ensures reliable message delivery with retry logic
"""
import time
import threading
from typing import Dict, Optional, Callable, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import uuid


class MessageStatus(Enum):
    """Message delivery status"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AckMessage:
    """
    Message with acknowledgment tracking

    Attributes:
        id: Unique message ID
        from_client: Sender
        to_client: Recipient
        type: Message type
        payload: Message data
        status: Current status
        sent_at: Time sent
        delivered_at: Time delivered
        acked_at: Time acknowledged
        retries: Number of retry attempts
        timeout: Timeout in seconds
    """

    id: str
    from_client: str
    to_client: str
    type: str
    payload: Dict
    status: MessageStatus = MessageStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    retries: int = 0
    timeout: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AckManager:
    """
    Manage message acknowledgments and retries

    Features:
    - Track message delivery status
    - Automatic retries for undelivered messages
    - Timeout detection
    - Callback on status changes
    - Statistics tracking
    """

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize acknowledgment manager

        Args:
            max_retries: Max retry attempts
            retry_delay: Seconds between retries
        """
        self.messages: Dict[str, AckMessage] = {}
        self.pending_acks: Set[str] = set()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.callbacks = {
            "on_delivered": [],
            "on_acked": [],
            "on_failed": [],
            "on_timeout": [],
        }
        self.stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_acked": 0,
            "total_failed": 0,
            "total_timeout": 0,
        }
        self._running = False
        self._retry_thread = None

    def send_message(
        self,
        from_client: str,
        to_client: str,
        msg_type: str,
        payload: Dict,
        timeout: int = 30,
    ) -> str:
        """
        Send message with acknowledgment tracking

        Args:
            from_client: Sender ID
            to_client: Recipient ID
            msg_type: Message type
            payload: Message data
            timeout: Timeout in seconds

        Returns:
            Message ID
        """
        msg_id = str(uuid.uuid4())

        message = AckMessage(
            id=msg_id,
            from_client=from_client,
            to_client=to_client,
            type=msg_type,
            payload=payload,
            timeout=timeout,
            sent_at=datetime.now(timezone.utc),
        )

        message.status = MessageStatus.SENT

        self.messages[msg_id] = message
        self.pending_acks.add(msg_id)
        self.stats["total_sent"] += 1

        return msg_id

    def mark_delivered(self, msg_id: str) -> bool:
        """
        Mark message as delivered

        Args:
            msg_id: Message ID

        Returns:
            True if marked successfully
        """
        if msg_id not in self.messages:
            return False

        message = self.messages[msg_id]
        message.status = MessageStatus.DELIVERED
        message.delivered_at = datetime.now(timezone.utc)

        self.stats["total_delivered"] += 1

        # Trigger callbacks
        self._trigger_callbacks("on_delivered", message)

        return True

    def mark_acknowledged(self, msg_id: str) -> bool:
        """
        Mark message as acknowledged

        Args:
            msg_id: Message ID

        Returns:
            True if marked successfully
        """
        if msg_id not in self.messages:
            return False

        message = self.messages[msg_id]
        message.status = MessageStatus.ACKNOWLEDGED
        message.acked_at = datetime.now(timezone.utc)

        # Remove from pending
        self.pending_acks.discard(msg_id)

        self.stats["total_acked"] += 1

        # Trigger callbacks
        self._trigger_callbacks("on_acked", message)

        return True

    def mark_failed(self, msg_id: str) -> bool:
        """
        Mark message as failed

        Args:
            msg_id: Message ID

        Returns:
            True if marked successfully
        """
        if msg_id not in self.messages:
            return False

        message = self.messages[msg_id]
        message.status = MessageStatus.FAILED

        # Remove from pending
        self.pending_acks.discard(msg_id)

        self.stats["total_failed"] += 1

        # Trigger callbacks
        self._trigger_callbacks("on_failed", message)

        return True

    def get_message(self, msg_id: str) -> Optional[AckMessage]:
        """Get message by ID"""
        return self.messages.get(msg_id)

    def get_pending_messages(self) -> list:
        """Get all pending messages"""
        return [
            msg
            for msg in self.messages.values()
            if msg.status in [MessageStatus.SENT, MessageStatus.DELIVERED]
        ]

    def register_callback(self, event: str, callback: Callable):
        """
        Register callback for events

        Args:
            event: Event type ('on_delivered', 'on_acked', 'on_failed', 'on_timeout')
            callback: Function to call (receives AckMessage)
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, message: AckMessage):
        """Trigger callbacks for event"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(message)
            except Exception as e:
                print(f"❌ Callback error: {e}")

    def start_retry_worker(self):
        """Start background worker for retries and timeouts"""
        if self._running:
            return

        self._running = True

        def worker():
            while self._running:
                try:
                    self._check_timeouts()
                    self._retry_pending()
                except Exception as e:
                    print(f"❌ Retry worker error: {e}")

                time.sleep(self.retry_delay)

        self._retry_thread = threading.Thread(target=worker, daemon=True)
        self._retry_thread.start()

    def stop_retry_worker(self):
        """Stop retry worker"""
        self._running = False

    def _check_timeouts(self):
        """Check for timed-out messages"""
        now = datetime.now(timezone.utc)

        for msg_id in list(self.pending_acks):
            message = self.messages.get(msg_id)
            if not message:
                continue

            # Check timeout
            if message.sent_at:
                elapsed = (now - message.sent_at).total_seconds()

                if elapsed > message.timeout:
                    # Timeout
                    message.status = MessageStatus.TIMEOUT
                    self.pending_acks.discard(msg_id)
                    self.stats["total_timeout"] += 1

                    # Trigger callbacks
                    self._trigger_callbacks("on_timeout", message)

    def _retry_pending(self):
        """Retry pending messages"""
        for msg_id in list(self.pending_acks):
            message = self.messages.get(msg_id)
            if not message:
                continue

            # Check if needs retry
            if message.status == MessageStatus.SENT:
                if message.retries < self.max_retries:
                    # Retry
                    message.retries += 1
                    print(
                        f"🔄 Retrying message {msg_id} (attempt {message.retries}/{self.max_retries})"
                    )

                    # Mark for resend (implementation would trigger actual send)
                    # For now, just track the retry

                else:
                    # Max retries exceeded
                    self.mark_failed(msg_id)

    def get_stats(self) -> Dict:
        """Get acknowledgment statistics"""
        pending_count = len(self.pending_acks)
        ack_rate = 0
        if self.stats["total_sent"] > 0:
            ack_rate = self.stats["total_acked"] / self.stats["total_sent"]

        return {
            **self.stats,
            "pending": pending_count,
            "ack_rate": ack_rate,
            "active_messages": len(self.messages),
        }

    def cleanup_old(self, max_age_seconds: int = 3600):
        """
        Clean up old acknowledged messages

        Args:
            max_age_seconds: Max age to keep (default: 1 hour)
        """
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - max_age_seconds

        to_remove = []

        for msg_id, message in self.messages.items():
            # Only clean up completed messages
            if message.status in [
                MessageStatus.ACKNOWLEDGED,
                MessageStatus.FAILED,
                MessageStatus.TIMEOUT,
            ]:
                if message.created_at.timestamp() < cutoff:
                    to_remove.append(msg_id)

        for msg_id in to_remove:
            del self.messages[msg_id]

        return len(to_remove)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("✅ Message Acknowledgment System Test")
    print("=" * 70)

    # Create manager
    ack_mgr = AckManager(max_retries=3, retry_delay=2)

    # Register callbacks
    def on_delivered(msg):
        print(f"   📬 Delivered: {msg.id}")

    def on_acked(msg):
        print(f"   ✅ Acknowledged: {msg.id}")

    def on_failed(msg):
        print(f"   ❌ Failed: {msg.id}")

    def on_timeout(msg):
        print(f"   ⏰ Timeout: {msg.id}")

    ack_mgr.register_callback("on_delivered", on_delivered)
    ack_mgr.register_callback("on_acked", on_acked)
    ack_mgr.register_callback("on_failed", on_failed)
    ack_mgr.register_callback("on_timeout", on_timeout)

    # Send messages
    print("\n1️⃣ Sending messages...")
    msg1 = ack_mgr.send_message("code", "browser", "command", {"text": "Hello"})
    msg2 = ack_mgr.send_message("code", "desktop", "command", {"text": "World"})

    print(f"   Sent: {msg1[:8]}...")
    print(f"   Sent: {msg2[:8]}...")

    # Mark delivered
    print("\n2️⃣ Marking as delivered...")
    ack_mgr.mark_delivered(msg1)

    # Mark acknowledged
    print("\n3️⃣ Marking as acknowledged...")
    ack_mgr.mark_acknowledged(msg1)

    # Stats
    print("\n4️⃣ Statistics:")
    stats = ack_mgr.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Pending messages
    print("\n5️⃣ Pending messages:")
    pending = ack_mgr.get_pending_messages()
    for msg in pending:
        print(f"   {msg.id}: {msg.status.value} → {msg.to_client}")

    # Start retry worker
    print("\n6️⃣ Starting retry worker...")
    ack_mgr.start_retry_worker()

    # Wait
    print("   Waiting 10 seconds for timeout...")
    time.sleep(10)

    # Final stats
    print("\n7️⃣ Final statistics:")
    stats = ack_mgr.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    ack_mgr.stop_retry_worker()

    print("\n✅ Test complete")
