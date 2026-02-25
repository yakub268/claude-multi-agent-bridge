#!/usr/bin/env python3
"""
Webhook System for Multi-Agent Bridge
External notifications for events (message sent, error occurred, etc.)
"""
import requests
import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
import hashlib
import hmac
from threading import Thread
from queue import Queue


class WebhookEvent(Enum):
    """Webhook event types"""

    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_FAILED = "message.failed"
    CLIENT_CONNECTED = "client.connected"
    CLIENT_DISCONNECTED = "client.disconnected"
    ERROR_OCCURRED = "error.occurred"
    RATE_LIMIT_HIT = "rate_limit.hit"
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"


@dataclass
class WebhookEndpoint:
    """
    Webhook endpoint configuration

    Example:
        endpoint = WebhookEndpoint(
            url="https://api.example.com/webhooks/messages",
            events={WebhookEvent.MESSAGE_SENT, WebhookEvent.MESSAGE_RECEIVED},
            secret="webhook_secret_key_123",
            headers={"Authorization": "Bearer token123"}
        )
    """

    url: str
    events: set  # Set of WebhookEvent
    secret: Optional[str] = None
    headers: Optional[Dict] = None
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 10


class WebhookManager:
    """
    Manage webhook endpoints and delivery

    Features:
    - Multiple endpoints per event type
    - HMAC signature verification
    - Retry with exponential backoff
    - Async delivery (non-blocking)
    - Delivery statistics
    - Failed webhook queue
    """

    def __init__(self, max_queue_size: int = 1000):
        self.endpoints: List[WebhookEndpoint] = []
        self.delivery_queue = Queue(maxsize=max_queue_size)
        self.stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "by_event": {},
        }
        self.failed_webhooks = []
        self._worker_running = False

    def register(self, endpoint: WebhookEndpoint):
        """Register a webhook endpoint"""
        self.endpoints.append(endpoint)

    def unregister(self, url: str) -> bool:
        """Unregister endpoint by URL"""
        for i, ep in enumerate(self.endpoints):
            if ep.url == url:
                del self.endpoints[i]
                return True
        return False

    def trigger(self, event: WebhookEvent, payload: Dict):
        """
        Trigger webhook for an event

        Args:
            event: Event type
            payload: Event data
        """
        matching_endpoints = [
            ep for ep in self.endpoints if event in ep.events and ep.enabled
        ]

        if not matching_endpoints:
            return

        # Update stats
        self.stats["total_sent"] += len(matching_endpoints)
        event_key = event.value
        self.stats["by_event"][event_key] = self.stats["by_event"].get(event_key, 0) + 1

        # Create webhook payload
        webhook_payload = {
            "event": event.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }

        # Queue deliveries (async)
        for endpoint in matching_endpoints:
            self.delivery_queue.put((endpoint, webhook_payload))

    def start_worker(self):
        """Start background worker for webhook delivery"""
        if self._worker_running:
            return

        self._worker_running = True
        worker = Thread(target=self._delivery_worker, daemon=True)
        worker.start()

    def stop_worker(self):
        """Stop background worker"""
        self._worker_running = False

    def _delivery_worker(self):
        """Background worker that delivers webhooks"""
        while self._worker_running:
            try:
                if self.delivery_queue.empty():
                    time.sleep(0.1)
                    continue

                endpoint, payload = self.delivery_queue.get(timeout=1)
                self._deliver_webhook(endpoint, payload)

            except Exception as e:
                print(f"❌ Webhook worker error: {e}")
                time.sleep(1)

    def _deliver_webhook(self, endpoint: WebhookEndpoint, payload: Dict):
        """
        Deliver webhook with retries

        Args:
            endpoint: Target endpoint
            payload: Webhook payload
        """
        for attempt in range(endpoint.max_retries):
            try:
                # Sign payload if secret provided
                headers = endpoint.headers.copy() if endpoint.headers else {}

                if endpoint.secret:
                    signature = self._sign_payload(payload, endpoint.secret)
                    headers["X-Webhook-Signature"] = signature

                headers["Content-Type"] = "application/json"
                headers["User-Agent"] = "MultiAgentBridge-Webhook/1.0"

                # Send webhook
                response = requests.post(
                    endpoint.url,
                    json=payload,
                    headers=headers,
                    timeout=endpoint.timeout,
                )

                if response.status_code < 300:
                    # Success
                    self.stats["total_delivered"] += 1
                    return

                else:
                    # HTTP error, will retry
                    if attempt == endpoint.max_retries - 1:
                        self._handle_failed_webhook(
                            endpoint, payload, f"HTTP {response.status_code}"
                        )
                    else:
                        time.sleep(2**attempt)  # Exponential backoff

            except requests.exceptions.Timeout:
                if attempt == endpoint.max_retries - 1:
                    self._handle_failed_webhook(endpoint, payload, "Timeout")
                else:
                    time.sleep(2**attempt)

            except Exception as e:
                if attempt == endpoint.max_retries - 1:
                    self._handle_failed_webhook(endpoint, payload, str(e))
                else:
                    time.sleep(2**attempt)

    def _sign_payload(self, payload: Dict, secret: str) -> str:
        """Generate HMAC signature for payload"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        return signature

    def _handle_failed_webhook(
        self, endpoint: WebhookEndpoint, payload: Dict, error: str
    ):
        """Handle failed webhook delivery"""
        self.stats["total_failed"] += 1

        self.failed_webhooks.append(
            {
                "url": endpoint.url,
                "payload": payload,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Keep only last 100 failed webhooks
        if len(self.failed_webhooks) > 100:
            self.failed_webhooks = self.failed_webhooks[-100:]

        print(f"❌ Webhook failed: {endpoint.url} - {error}")

    def verify_signature(self, payload: Dict, signature: str, secret: str) -> bool:
        """
        Verify webhook signature (for incoming webhooks)

        Args:
            payload: Received payload
            signature: Received signature
            secret: Shared secret

        Returns:
            True if signature is valid
        """
        expected = self._sign_payload(payload, secret)
        return hmac.compare_digest(signature, expected)

    def get_stats(self) -> Dict:
        """Get webhook delivery statistics"""
        success_rate = 0
        if self.stats["total_sent"] > 0:
            success_rate = self.stats["total_delivered"] / self.stats["total_sent"]

        return {
            **self.stats,
            "success_rate": success_rate,
            "queue_size": self.delivery_queue.qsize(),
            "failed_recent": len(self.failed_webhooks),
            "endpoints_registered": len(self.endpoints),
        }

    def get_failed_webhooks(self, limit: int = 50) -> List[Dict]:
        """Get recent failed webhooks"""
        return self.failed_webhooks[-limit:]

    def retry_failed(self, url: str):
        """Retry all failed webhooks for a specific URL"""
        endpoint = next((ep for ep in self.endpoints if ep.url == url), None)
        if not endpoint:
            return

        # Find failed webhooks for this URL
        failed_for_url = [w for w in self.failed_webhooks if w["url"] == url]

        for failed in failed_for_url:
            self.delivery_queue.put((endpoint, failed["payload"]))

        # Remove from failed list
        self.failed_webhooks = [w for w in self.failed_webhooks if w["url"] != url]


# ============================================================================
# Pre-built Webhook Integrations
# ============================================================================


class SlackWebhook:
    """Slack webhook integration"""

    @staticmethod
    def format_message(event: WebhookEvent, data: Dict) -> Dict:
        """Format message for Slack"""
        emoji_map = {
            WebhookEvent.MESSAGE_SENT: "📤",
            WebhookEvent.MESSAGE_RECEIVED: "📥",
            WebhookEvent.MESSAGE_FAILED: "❌",
            WebhookEvent.CLIENT_CONNECTED: "🟢",
            WebhookEvent.CLIENT_DISCONNECTED: "🔴",
            WebhookEvent.ERROR_OCCURRED: "⚠️",
        }

        emoji = emoji_map.get(event, "📣")

        return {
            "text": f"{emoji} *{event.value}*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{event.value}*\n```{json.dumps(data, indent=2)}```",
                    },
                }
            ],
        }

    @staticmethod
    def send(webhook_url: str, event: WebhookEvent, data: Dict):
        """Send notification to Slack"""
        payload = SlackWebhook.format_message(event, data)
        requests.post(webhook_url, json=payload)


class DiscordWebhook:
    """Discord webhook integration"""

    @staticmethod
    def format_message(event: WebhookEvent, data: Dict) -> Dict:
        """Format message for Discord"""
        color_map = {
            WebhookEvent.MESSAGE_SENT: 0x00FF00,
            WebhookEvent.MESSAGE_FAILED: 0xFF0000,
            WebhookEvent.ERROR_OCCURRED: 0xFFA500,
        }

        return {
            "embeds": [
                {
                    "title": event.value,
                    "description": f"```json\n{json.dumps(data, indent=2)}\n```",
                    "color": color_map.get(event, 0x0099FF),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

    @staticmethod
    def send(webhook_url: str, event: WebhookEvent, data: Dict):
        """Send notification to Discord"""
        payload = DiscordWebhook.format_message(event, data)
        requests.post(webhook_url, json=payload)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🪝 Webhook System Test")
    print("=" * 70)

    # Create manager
    manager = WebhookManager()

    # Register endpoints
    endpoint1 = WebhookEndpoint(
        url="https://webhook.site/test-endpoint-1",
        events={WebhookEvent.MESSAGE_SENT, WebhookEvent.MESSAGE_RECEIVED},
        secret="secret123",
    )

    endpoint2 = WebhookEndpoint(
        url="https://webhook.site/test-endpoint-2",
        events={WebhookEvent.ERROR_OCCURRED},
        headers={"Authorization": "Bearer token123"},
    )

    manager.register(endpoint1)
    manager.register(endpoint2)

    # Start worker
    manager.start_worker()

    # Trigger events
    print("\n📤 Triggering MESSAGE_SENT event...")
    manager.trigger(
        WebhookEvent.MESSAGE_SENT,
        {
            "from": "code",
            "to": "browser",
            "type": "command",
            "payload": {"text": "Hello"},
        },
    )

    print("\n⚠️ Triggering ERROR_OCCURRED event...")
    manager.trigger(
        WebhookEvent.ERROR_OCCURRED,
        {"error": "Connection timeout", "details": "Client browser timed out"},
    )

    # Wait for delivery
    time.sleep(2)

    # Stats
    print("\n📊 Webhook stats:")
    for key, value in manager.get_stats().items():
        print(f"   {key}: {value}")

    # Test signature verification
    print("\n🔐 Testing signature verification...")
    test_payload = {"test": "data"}
    signature = manager._sign_payload(test_payload, "secret123")

    valid = manager.verify_signature(test_payload, signature, "secret123")
    invalid = manager.verify_signature(test_payload, "wrong_signature", "secret123")

    print(f"   Valid signature: {valid}")
    print(f"   Invalid signature: {invalid}")

    # Slack example
    print("\n📱 Slack integration example:")
    slack_msg = SlackWebhook.format_message(
        WebhookEvent.MESSAGE_SENT, {"from": "code", "to": "browser"}
    )
    print(f"   {slack_msg['text']}")

    manager.stop_worker()
    print("\n✅ Test complete")
