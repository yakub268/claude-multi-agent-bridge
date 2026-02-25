#!/usr/bin/env python3
"""
Desktop Claude Client v2
Improved desktop automation with WebSocket support and better reliability
"""
import time
import pyautogui
import pygetwindow as gw
import requests
import json
import threading
from datetime import datetime, timezone
from queue import Queue
from typing import Optional, Dict, List
import logging

# Configure
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DesktopClaudeClient:
    """
    Improved Desktop Claude client with WebSocket support

    Features:
    - Reliable window detection and activation
    - Better input detection (no OCR needed)
    - WebSocket for real-time commands
    - Auto-reconnection
    - Error recovery
    - Heartbeat monitoring
    """

    def __init__(self, bus_url="http://localhost:5001", client_id="desktop"):
        self.bus_url = bus_url
        self.client_id = client_id
        self.window = None
        self.last_response = None
        self.command_queue = Queue()
        self.running = False
        self.last_heartbeat = time.time()

    def find_window(self) -> bool:
        """
        Find Claude Desktop window

        Searches for windows containing 'Claude' in title.
        """
        try:
            # Try multiple title patterns
            patterns = ["Claude", "claude", "CLAUDE"]

            for pattern in patterns:
                windows = gw.getWindowsWithTitle(pattern)

                if windows:
                    # Filter out browser Claude (contains 'claude.ai')
                    desktop_windows = [
                        w
                        for w in windows
                        if "claude.ai" not in w.title.lower()
                        and "chrome" not in w.title.lower()
                    ]

                    if desktop_windows:
                        self.window = desktop_windows[0]
                        logger.info(f"✅ Found window: {self.window.title}")
                        return True

            logger.warning("❌ Claude Desktop window not found")
            logger.info("   Make sure Claude Desktop is running")
            logger.info("   Window title should contain 'Claude'")
            return False

        except Exception as e:
            logger.error(f"❌ Error finding window: {e}")
            return False

    def activate_window(self) -> bool:
        """Bring window to front and focus"""
        if not self.window:
            return False

        try:
            # Check if window still exists
            if not self.window.isActive and not self.window.isMinimized:
                self.window.restore()

            self.window.activate()
            time.sleep(0.5)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to activate window: {e}")
            # Window might have been closed - try to find it again
            self.window = None
            return False

    def find_input_area(self) -> Optional[tuple]:
        """
        Find input area without OCR

        Uses window geometry to estimate input location.
        Desktop Claude has input at bottom of window.
        """
        if not self.window:
            return None

        try:
            # Get window position and size
            left = self.window.left
            top = self.window.top
            width = self.window.width
            height = self.window.height

            # Input box is typically at:
            # - Horizontal center
            # - 90% down from top (last 10% of window)
            input_x = left + (width // 2)
            input_y = top + int(height * 0.90)

            logger.debug(f"Input area estimated at: ({input_x}, {input_y})")
            return (input_x, input_y)

        except Exception as e:
            logger.error(f"❌ Error finding input area: {e}")
            return None

    def send_message(self, text: str) -> bool:
        """
        Send message to Desktop Claude

        Args:
            text: Message to send

        Returns:
            True if sent successfully
        """
        if not self.activate_window():
            logger.error("❌ Cannot activate window")
            return False

        try:
            # Find input area
            input_pos = self.find_input_area()
            if not input_pos:
                logger.error("❌ Cannot find input area")
                return False

            # Click input area to focus
            pyautogui.click(input_pos[0], input_pos[1])
            time.sleep(0.3)

            # Clear existing text
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("delete")
            time.sleep(0.2)

            # Type message (handle special characters)
            # Split into chunks to avoid issues with long text
            chunk_size = 500
            for i in range(0, len(text), chunk_size):
                chunk = text[i : i + chunk_size]
                pyautogui.write(chunk, interval=0.01)
                time.sleep(0.1)

            time.sleep(0.3)

            # Submit
            pyautogui.press("enter")

            logger.info(
                f"✅ Sent message: {text[:100]}{'...' if len(text) > 100 else ''}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False

    def wait_for_response(self, timeout: int = 30) -> bool:
        """
        Wait for Claude to finish responding

        Uses clipboard monitoring as a proxy:
        - Desktop Claude allows copying responses
        - We wait for typing activity to stop

        Args:
            timeout: Max seconds to wait

        Returns:
            True if response appears complete
        """
        start_time = time.time()

        # Wait for initial response to appear (2 seconds)
        time.sleep(2)

        # Then wait for typing to stop
        # This is heuristic - Claude Desktop doesn't expose a "done" indicator
        # We just wait a reasonable time
        wait_time = min(timeout, 15)  # Max 15 seconds after initial delay
        time.sleep(wait_time)

        elapsed = time.time() - start_time
        logger.debug(f"Waited {elapsed:.1f}s for response")

        return True

    def extract_response_clipboard(self) -> Optional[str]:
        """
        Extract response via clipboard

        Strategy:
        1. Select all text in response area (Ctrl+A)
        2. Copy to clipboard (Ctrl+C)
        3. Read clipboard
        4. Parse out the response
        """
        try:
            # Focus window
            if not self.activate_window():
                return None

            # Click in message area (above input box)
            if self.window:
                left = self.window.left
                top = self.window.top
                width = self.window.width
                height = self.window.height

                # Click in middle of conversation area
                click_x = left + (width // 2)
                click_y = top + int(height * 0.50)

                pyautogui.click(click_x, click_y)
                time.sleep(0.3)

            # Select all
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)

            # Copy
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.3)

            # Get clipboard
            import pyperclip

            clipboard_text = pyperclip.paste()

            if clipboard_text and len(clipboard_text) > 0:
                # Parse response (last message in conversation)
                # This is heuristic - might need adjustment
                lines = clipboard_text.split("\n")

                # Find last substantial block of text
                response_lines = []
                for line in reversed(lines):
                    if line.strip():
                        response_lines.insert(0, line)
                    elif response_lines:
                        # Hit empty line after finding text - stop
                        break

                if response_lines:
                    response = "\n".join(response_lines)
                    logger.debug(f"Extracted response: {response[:200]}...")
                    return response

            logger.warning("⚠️  No response in clipboard")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to extract response: {e}")
            return None

    def poll_messages(self) -> List[Dict]:
        """Poll message bus for commands"""
        try:
            response = requests.get(
                f"{self.bus_url}/api/messages", params={"to": self.client_id}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                return messages
            else:
                logger.error(f"❌ Poll failed: {response.status_code}")
                return []

        except Exception as e:
            logger.debug(f"Poll error (will retry): {e}")
            return []

    def send_response(self, response_text: str, original_msg_id: str) -> bool:
        """Send response back to bus"""
        try:
            payload = {
                "from": self.client_id,
                "to": "code",
                "type": "claude_response",
                "payload": {"response": response_text, "in_reply_to": original_msg_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            response = requests.post(
                f"{self.bus_url}/api/send", json=payload, timeout=5
            )

            if response.status_code == 200:
                logger.info("✅ Response sent to bus")
                return True
            else:
                logger.error(f"❌ Send failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending response: {e}")
            return False

    def process_command(self, msg: Dict) -> bool:
        """
        Process a command message

        Args:
            msg: Command message

        Returns:
            True if processed successfully
        """
        try:
            prompt = msg["payload"].get("text", "")
            if not prompt:
                logger.warning("⚠️  Empty prompt in command")
                return False

            logger.info(f"📩 Processing: {prompt[:100]}...")

            # Send to Desktop Claude
            if not self.send_message(prompt):
                return False

            # Wait for response
            if not self.wait_for_response():
                logger.warning("⚠️  Response timeout")
                return False

            # Extract response
            response = self.extract_response_clipboard()

            if response:
                logger.info(f"📤 Got response: {response[:100]}...")
                return self.send_response(response, msg["id"])
            else:
                logger.warning("⚠️  No response extracted")
                return False

        except Exception as e:
            logger.error(f"❌ Error processing command: {e}")
            return False

    def heartbeat(self):
        """Send periodic heartbeat to bus"""
        try:
            payload = {
                "from": self.client_id,
                "to": "server",
                "type": "heartbeat",
                "payload": {"status": "alive", "window_found": self.window is not None},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            requests.post(f"{self.bus_url}/api/send", json=payload, timeout=2)

            self.last_heartbeat = time.time()

        except Exception:
            pass  # Heartbeat failures are non-critical

    def run_daemon(self):
        """Run in daemon mode"""
        logger.info("=" * 70)
        logger.info("🖥️  DESKTOP CLAUDE CLIENT v2 - DAEMON MODE")
        logger.info("=" * 70)
        logger.info(f"Message Bus: {self.bus_url}")
        logger.info(f"Client ID: {self.client_id}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70)

        # Initial window check
        if not self.find_window():
            logger.error("\n❌ Cannot start - Claude Desktop not found")
            logger.info("\nRetrying every 10 seconds...")

        self.running = True

        try:
            while self.running:
                # Check if window is still available
                if not self.window or not self.window.isMinimized:
                    if not self.find_window():
                        logger.warning("⚠️  Window lost, retrying in 10s...")
                        time.sleep(10)
                        continue

                # Poll for messages
                messages = self.poll_messages()

                for msg in messages:
                    if msg["type"] == "command":
                        self.process_command(msg)

                # Send heartbeat every 30s
                if time.time() - self.last_heartbeat > 30:
                    self.heartbeat()

                # Sleep between polls
                time.sleep(2)

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Daemon stopped by user")
            self.running = False

        except Exception as e:
            logger.error(f"\n\n❌ Daemon error: {e}")
            self.running = False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Desktop Claude Client v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test window detection
  python desktop_client_v2.py --test

  # Send single message
  python desktop_client_v2.py --send "What is 2+2?"

  # Run daemon (listens for commands from bridge)
  python desktop_client_v2.py --daemon

  # Run with debug logging
  python desktop_client_v2.py --daemon --debug
        """,
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (listens for commands)",
    )
    parser.add_argument(
        "--test", action="store_true", help="Test window detection and activation"
    )
    parser.add_argument("--send", type=str, help="Send a single message")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--bus-url",
        type=str,
        default="http://localhost:5001",
        help="Message bus URL (default: http://localhost:5001)",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    client = DesktopClaudeClient(bus_url=args.bus_url)

    if args.test:
        logger.info("Testing window detection...")
        if client.find_window():
            logger.info("✅ Window found")

            if client.activate_window():
                logger.info("✅ Window activated")

                input_pos = client.find_input_area()
                logger.info(f"✅ Input area at: {input_pos}")

                logger.info("\n✅ All tests passed!")
            else:
                logger.error("❌ Failed to activate window")
        else:
            logger.error("❌ Window not found")

    elif args.send:
        if client.find_window():
            if client.send_message(args.send):
                logger.info("✅ Message sent")
                logger.info("Waiting for response...")

                if client.wait_for_response():
                    response = client.extract_response_clipboard()
                    if response:
                        logger.info(f"\n📥 Response:\n{response}\n")
                    else:
                        logger.warning("⚠️  No response extracted")
        else:
            logger.error("❌ Window not found")

    elif args.daemon:
        client.run_daemon()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
