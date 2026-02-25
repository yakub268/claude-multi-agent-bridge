#!/usr/bin/env python3
"""
Desktop Claude Client - Clipboard-Based Integration
Simpler and more reliable than PyAutoGUI screen automation

Uses clipboard monitoring to:
1. Detect when Claude Desktop copies responses
2. Send messages to bridge
3. Monitor for new messages from bridge
4. Copy them to clipboard for pasting into Claude

This is a passive integration that works alongside manual Claude Desktop usage.
"""
import time
import json
import logging
import requests
import pyperclip
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ClipboardDesktopClient:
    """
    Desktop Claude client using clipboard monitoring

    Workflow:
    1. User asks question in Claude Desktop
    2. Claude responds
    3. User copies Claude's response (Ctrl+C)
    4. This client detects clipboard change
    5. Sends to message bus with [DESKTOP] tag
    6. Other Claudes can respond
    7. Client polls for responses
    8. When response found, copies to clipboard
    9. User pastes into Claude Desktop
    """

    def __init__(
        self,
        client_id: str = "claude-desktop-1",
        message_bus_url: str = "http://localhost:5001",
    ):
        self.client_id = client_id
        self.bus_url = message_bus_url
        self.last_clipboard = ""
        self.last_check_time = time.time()
        self.message_history: List[Dict] = []

        logger.info(f"🖥️  Desktop client initialized: {client_id}")
        logger.info("📋 Clipboard monitoring active")
        logger.info(f"🌉 Connected to bridge: {message_bus_url}")

    def get_clipboard(self) -> str:
        """Get current clipboard content"""
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to read clipboard: {e}")
            return ""

    def set_clipboard(self, text: str):
        """Set clipboard content"""
        try:
            pyperclip.copy(text)
            logger.info(f"📋 Copied to clipboard ({len(text)} chars)")
        except Exception as e:
            logger.error(f"Failed to write clipboard: {e}")

    def send_to_bridge(self, text: str, msg_type: str = "message") -> bool:
        """Send message to bridge"""
        try:
            response = requests.post(
                f"{self.bus_url}/message",
                json={
                    "from": self.client_id,
                    "to": "all",
                    "text": text,
                    "type": msg_type,
                    "priority": 1,
                },
                timeout=5,
            )

            if response.status_code == 200:
                logger.info(f"✅ Sent to bridge: {text[:60]}...")
                return True
            else:
                logger.error(f"Failed to send: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Bridge connection failed: {e}")
            return False

    def check_for_messages(self) -> List[Dict]:
        """Check bridge for new messages"""
        try:
            response = requests.get(
                f"{self.bus_url}/messages",
                params={
                    "to": self.client_id,
                    "since": int(self.last_check_time * 1000),
                },
                timeout=5,
            )

            if response.status_code == 200:
                messages = response.json().get("messages", [])
                if messages:
                    self.last_check_time = time.time()
                    return messages

        except Exception as e:
            logger.error(f"Failed to check messages: {e}")

        return []

    def monitor_clipboard(self, interval: float = 2.0):
        """
        Monitor clipboard for changes

        When clipboard changes:
        1. Check if it looks like a Claude response
        2. Send to bridge if different from last sent
        3. Check for new messages from bridge
        4. Copy responses to clipboard if found
        """
        logger.info("=" * 80)
        logger.info("🚀 CLIPBOARD MONITOR STARTED")
        logger.info("=" * 80)
        logger.info("")
        logger.info("How to use:")
        logger.info("  1. Copy Claude Desktop responses (Ctrl+C)")
        logger.info("  2. They'll be sent to the bridge automatically")
        logger.info("  3. Responses from other Claudes will be copied to clipboard")
        logger.info("  4. Paste them into Claude Desktop (Ctrl+V)")
        logger.info("")
        logger.info(f"Client ID: {self.client_id}")
        logger.info(f"Check interval: {interval}s")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        logger.info("")

        try:
            while True:
                # Check clipboard
                current_clipboard = self.get_clipboard()

                # Detect change
                if current_clipboard and current_clipboard != self.last_clipboard:
                    # Filter out very short clips (likely not responses)
                    if len(current_clipboard) > 20:
                        logger.info(
                            f"📋 Clipboard changed ({len(current_clipboard)} chars)"
                        )

                        # Send to bridge
                        self.send_to_bridge(current_clipboard)
                        self.last_clipboard = current_clipboard

                # Check for new messages
                new_messages = self.check_for_messages()

                if new_messages:
                    logger.info(f"📨 Received {len(new_messages)} new message(s)")

                    for msg in new_messages:
                        from_client = msg.get("from", "unknown")
                        text = msg.get("text", "")

                        logger.info(f"  [{from_client}]: {text[:80]}...")

                        # Copy to clipboard for user to paste
                        self.set_clipboard(text)

                        # Store in history
                        self.message_history.append(msg)

                # Wait before next check
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\n" + "=" * 80)
            logger.info("🛑 Clipboard monitor stopped")
            logger.info(f"📊 Total messages sent: {len(self.message_history)}")
            logger.info("=" * 80)

    def send_manual(self, text: str):
        """Manually send a message to bridge"""
        logger.info("📤 Sending manual message...")
        success = self.send_to_bridge(text)

        if success:
            logger.info("✅ Message sent successfully")
        else:
            logger.error("❌ Failed to send message")


class DesktopCollaborationClient:
    """
    Enhanced desktop client with collaboration room support

    Integrates clipboard monitoring with collaboration rooms for
    multi-Claude coordination via Claude Desktop
    """

    def __init__(
        self,
        client_id: str = "claude-desktop-1",
        message_bus_url: str = "http://localhost:5001",
        room_id: Optional[str] = None,
    ):
        self.client_id = client_id
        self.bus_url = message_bus_url
        self.room_id = room_id
        self.clipboard_client = ClipboardDesktopClient(client_id, message_bus_url)

        logger.info("🏢 Desktop collaboration client initialized")
        if room_id:
            logger.info(f"   Room: {room_id}")

    def join_room(self, room_id: str, role: str = "member") -> bool:
        """Join a collaboration room"""
        try:
            response = requests.post(
                f"{self.bus_url}/collab/room/{room_id}/join",
                json={"client_id": self.client_id, "role": role},
                timeout=5,
            )

            if response.status_code == 200:
                self.room_id = room_id
                logger.info(f"✅ Joined room: {room_id} as {role}")
                return True
            else:
                logger.error(f"Failed to join room: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Room join failed: {e}")
            return False

    def send_to_room(self, text: str, channel: str = "main") -> bool:
        """Send message to collaboration room"""
        if not self.room_id:
            logger.error("Not in a room")
            return False

        try:
            response = requests.post(
                f"{self.bus_url}/collab/room/{self.room_id}/message",
                json={"from_client": self.client_id, "text": text, "channel": channel},
                timeout=5,
            )

            if response.status_code == 200:
                logger.info(f"✅ Sent to room #{channel}: {text[:60]}...")
                return True
            else:
                logger.error(f"Failed to send: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Room send failed: {e}")
            return False

    def start_monitoring(self, interval: float = 2.0):
        """Start clipboard monitoring with room integration"""
        if self.room_id:
            logger.info(f"🏢 Monitoring clipboard for room: {self.room_id}")

        self.clipboard_client.monitor_clipboard(interval)


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Desktop Claude clipboard integration")
    parser.add_argument("--client-id", default="claude-desktop-1", help="Client ID")
    parser.add_argument(
        "--url", default="http://localhost:5001", help="Message bus URL"
    )
    parser.add_argument("--room", help="Collaboration room ID to join")
    parser.add_argument(
        "--role", default="member", help="Room role (member, coder, reviewer, etc.)"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, help="Clipboard check interval (seconds)"
    )
    parser.add_argument("--send", help="Send a single message and exit")

    args = parser.parse_args()

    if args.room:
        # Collaboration mode
        client = DesktopCollaborationClient(
            client_id=args.client_id, message_bus_url=args.url, room_id=args.room
        )

        # Join room
        client.join_room(args.room, args.role)

        # Start monitoring
        client.start_monitoring(args.interval)
    else:
        # Simple clipboard mode
        client = ClipboardDesktopClient(
            client_id=args.client_id, message_bus_url=args.url
        )

        if args.send:
            # Single send mode
            client.send_manual(args.send)
        else:
            # Monitor mode
            client.monitor_clipboard(args.interval)
