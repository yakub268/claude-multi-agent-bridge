#!/usr/bin/env python3
"""
Desktop Claude Client
Controls Claude Desktop app via PyAutoGUI for automation
"""
import time
import pyautogui
import pytesseract
from PIL import Image
import requests
import json
from pathlib import Path

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5  # Default pause between actions


class DesktopClaudeClient:
    """
    Client for interacting with Claude Desktop app
    Uses screen automation + OCR to send/receive messages
    """

    def __init__(self, message_bus_url="http://localhost:5001"):
        self.bus_url = message_bus_url
        self.app_window = None
        self.last_check_time = time.time()

    def find_window(self):
        """Find Claude Desktop window"""
        print("Looking for Claude Desktop window...")

        # Try to find the window by title
        # This is platform-specific - may need adjustment
        try:
            # On Windows, use pygetwindow
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle('Claude')

            if windows:
                self.app_window = windows[0]
                print(f"✅ Found window: {self.app_window.title}")
                return True
            else:
                print("❌ Claude Desktop window not found")
                print("   Make sure Claude Desktop is running")
                return False

        except ImportError:
            print("⚠️  pygetwindow not installed")
            print("   Install with: pip install pygetwindow")
            return False

    def activate_window(self):
        """Bring Claude window to front"""
        if self.app_window:
            try:
                self.app_window.activate()
                time.sleep(0.5)
                return True
            except Exception as e:
                print(f"❌ Failed to activate window: {e}")
                return False
        return False

    def find_input_box(self):
        """
        Find the text input box location
        Uses template matching or OCR
        """
        # Take screenshot
        screenshot = pyautogui.screenshot()

        # Look for common input box indicators
        # This is a heuristic - may need tuning
        try:
            # Convert to grayscale
            gray = screenshot.convert('L')

            # Look for input placeholder text
            # "How can Claude help you today?" or similar
            text = pytesseract.image_to_string(gray)

            if "help" in text.lower() or "message" in text.lower():
                # Found likely input area
                # Get coordinates (simplified - real impl would be more precise)
                return (pyautogui.size()[0] // 2, pyautogui.size()[1] - 200)

        except Exception as e:
            print(f"⚠️  OCR failed: {e}")

        # Fallback: assume input is at bottom center
        return (pyautogui.size()[0] // 2, pyautogui.size()[1] - 150)

    def send_message(self, text):
        """Send a message to Claude Desktop"""
        if not self.activate_window():
            print("❌ Cannot activate window")
            return False

        try:
            # Find input box
            input_pos = self.find_input_box()

            # Click input box
            pyautogui.click(input_pos[0], input_pos[1])
            time.sleep(0.3)

            # Clear existing text (Ctrl+A, Delete)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            time.sleep(0.1)

            # Type message
            pyautogui.write(text, interval=0.02)
            time.sleep(0.3)

            # Submit (Enter)
            pyautogui.press('enter')

            print(f"✅ Sent: {text[:50]}...")
            return True

        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False

    def extract_response(self):
        """
        Extract Claude's response from the screen
        Uses OCR to read the latest response
        """
        time.sleep(2)  # Wait for response to appear

        try:
            # Take screenshot of response area (top 70% of window)
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size

            # Crop to likely response area
            response_area = screenshot.crop((0, 100, width, height - 200))

            # OCR
            text = pytesseract.image_to_string(response_area)

            # Clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Return last few non-empty lines (likely the response)
            if lines:
                # Heuristic: last response is probably the last paragraph
                response = '\n'.join(lines[-5:])  # Last 5 lines
                return response
            else:
                return None

        except Exception as e:
            print(f"❌ Failed to extract response: {e}")
            return None

    def poll_messages(self):
        """Poll message bus for commands directed to desktop"""
        try:
            response = requests.get(
                f"{self.bus_url}/api/messages",
                params={
                    'to': 'desktop',
                    'since': self.last_check_time
                },
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])

                if messages:
                    self.last_check_time = messages[-1]['timestamp']

                return messages
            else:
                print(f"❌ Failed to poll messages: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error polling messages: {e}")
            return []

    def send_response(self, response_text, original_msg_id):
        """Send response back to message bus"""
        try:
            payload = {
                'from': 'desktop',
                'to': 'code',
                'type': 'claude_response',
                'payload': {
                    'response': response_text,
                    'in_reply_to': original_msg_id
                }
            }

            response = requests.post(
                f"{self.bus_url}/api/send",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                print("✅ Response sent to bus")
                return True
            else:
                print(f"❌ Failed to send response: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error sending response: {e}")
            return False

    def run_daemon(self):
        """Run in daemon mode - continuously poll and respond"""
        print("="*70)
        print("🖥️  DESKTOP CLAUDE CLIENT - DAEMON MODE")
        print("="*70)
        print(f"Message Bus: {self.bus_url}")
        print("Polling for messages directed to 'desktop'...")
        print("Press Ctrl+C to stop")
        print("="*70)

        if not self.find_window():
            print("\n❌ Cannot start - Claude Desktop window not found")
            return

        try:
            while True:
                # Poll for new messages
                messages = self.poll_messages()

                for msg in messages:
                    if msg['type'] == 'command':
                        prompt = msg['payload'].get('text', '')
                        if prompt:
                            print(f"\n📩 Received: {prompt[:50]}...")

                            # Send to Desktop Claude
                            if self.send_message(prompt):
                                # Extract response
                                response = self.extract_response()

                                if response:
                                    print(f"📤 Response: {response[:100]}...")
                                    self.send_response(response, msg['id'])
                                else:
                                    print("⚠️  No response extracted")

                # Sleep between polls
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n\n⚠️  Daemon stopped by user")
        except Exception as e:
            print(f"\n\n❌ Daemon error: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Desktop Claude Client')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--test', action='store_true', help='Test window detection')
    parser.add_argument('--send', type=str, help='Send a single message')

    args = parser.parse_args()

    client = DesktopClaudeClient()

    if args.test:
        print("Testing window detection...")
        if client.find_window():
            client.activate_window()
            input_pos = client.find_input_box()
            print(f"Input box estimated at: {input_pos}")
            print("Test complete")
        else:
            print("Test failed - window not found")

    elif args.send:
        if client.find_window():
            client.send_message(args.send)
            response = client.extract_response()
            if response:
                print(f"\nResponse:\n{response}")
        else:
            print("Cannot send - window not found")

    elif args.daemon:
        client.run_daemon()

    else:
        print("Desktop Claude Client")
        print("\nUsage:")
        print("  python desktop_client.py --test              # Test window detection")
        print("  python desktop_client.py --send 'message'    # Send single message")
        print("  python desktop_client.py --daemon            # Run in daemon mode")
        print("\nDaemon mode polls message bus and responds to 'desktop' commands")


if __name__ == '__main__':
    main()
