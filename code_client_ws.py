#!/usr/bin/env python3
"""
WebSocket Client for Claude Multi-Agent Bridge
Real-time bi-directional communication
"""
import json
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
import websocket
import requests

logger = logging.getLogger(__name__)


class CodeClientWS:
    """
    WebSocket-enabled client for Claude Multi-Agent Bridge

    Features:
    - Real-time message delivery (no polling)
    - Automatic reconnection
    - Message acknowledgment
    - Event handlers
    """

    def __init__(self, client_id: str = "code", bus_url: str = "ws://localhost:5001"):
        self.client_id = client_id
        self.bus_url = bus_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.ws_url = f"{self.bus_url}/ws/{self.client_id}"

        self.ws = None
        self.connected = False
        self.reconnect_interval = 5  # seconds
        self.handlers = {}  # message_type -> callback
        self.received_messages = []
        self.lock = threading.Lock()

        # Auto-connect
        self._connect()

    def _connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )

            # Run in background thread
            wst = threading.Thread(target=self.ws.run_forever, daemon=True)
            wst.start()

            # Wait for connection
            timeout = 5
            start = time.time()
            while not self.connected and time.time() - start < timeout:
                time.sleep(0.1)

            if not self.connected:
                print("⚠️  WebSocket connection timeout. Falling back to polling mode.")

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            print("💡 Make sure server_ws.py is running")

    def _on_open(self, ws):
        """WebSocket connection opened"""
        self.connected = True
        print(f"✅ WebSocket connected: {self.client_id}")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'connection_confirmed':
                print("🔌 Connection confirmed by server")

            elif msg_type == 'message':
                # Actual message from another client
                msg = data['message']

                with self.lock:
                    self.received_messages.append(msg)

                # Auto-acknowledge if required
                if msg.get('requires_ack'):
                    self.acknowledge(msg['id'])

                # Call registered handler
                handler = self.handlers.get(msg['type'])
                if handler:
                    try:
                        handler(msg)
                    except Exception as e:
                        print(f"❌ Handler error: {e}")

            elif msg_type == 'pong':
                # Ping response
                pass

            elif msg_type == 'error':
                print(f"❌ Server error: {data.get('error')}")

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Message handling error: {e}")

    def _on_error(self, ws, error):
        """WebSocket error"""
        print(f"❌ WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        self.connected = False
        print("🔌 WebSocket disconnected")

        # Auto-reconnect
        print(f"🔄 Reconnecting in {self.reconnect_interval} seconds...")
        time.sleep(self.reconnect_interval)
        self._connect()

    def send(self, to: str, msg_type: str, payload: Dict, require_ack: bool = False) -> bool:
        """
        Send message to another client

        Args:
            to: Target client ID
            msg_type: Message type
            payload: Message payload
            require_ack: Require acknowledgment from recipient

        Returns:
            True if sent successfully
        """
        if not self.connected:
            print("⚠️  Not connected, message not sent")
            return False

        try:
            message = {
                'type': 'send',
                'to': to,
                'msg_type': msg_type,
                'payload': payload,
                'require_ack': require_ack
            }

            self.ws.send(json.dumps(message))
            return True

        except Exception as e:
            print(f"❌ Send failed: {e}")
            return False

    def acknowledge(self, message_id: str) -> bool:
        """Acknowledge receipt of a message"""
        if not self.connected:
            return False

        try:
            ack = {
                'type': 'ack',
                'message_id': message_id
            }

            self.ws.send(json.dumps(ack))
            return True

        except Exception as e:
            print(f"❌ Ack failed: {e}")
            return False

    def on(self, msg_type: str, handler: Callable):
        """
        Register handler for message type

        Example:
            def handle_response(msg):
                print(f"Got response: {msg['payload']}")

            client.on('claude_response', handle_response)
        """
        self.handlers[msg_type] = handler

    def get_messages(self, msg_type: Optional[str] = None, clear: bool = False) -> List[Dict]:
        """
        Get received messages

        Args:
            msg_type: Filter by message type (optional)
            clear: Clear messages after retrieving

        Returns:
            List of messages
        """
        with self.lock:
            if msg_type:
                messages = [m for m in self.received_messages if m['type'] == msg_type]
            else:
                messages = self.received_messages.copy()

            if clear:
                self.received_messages.clear()

        return messages

    def wait_for_message(self, msg_type: str, timeout: float = 10.0) -> Optional[Dict]:
        """
        Wait for a specific message type

        Args:
            msg_type: Message type to wait for
            timeout: Max wait time in seconds

        Returns:
            Message if received, None if timeout
        """
        start = time.time()

        while time.time() - start < timeout:
            messages = self.get_messages(msg_type=msg_type, clear=True)
            if messages:
                return messages[0]
            time.sleep(0.1)

        return None

    def ping(self) -> bool:
        """Send ping to server"""
        if not self.connected:
            return False

        try:
            self.ws.send(json.dumps({'type': 'ping'}))
            return True
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.connected = False


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("🧪 WebSocket Client Test")
    print("="*70)

    # Create client
    client = CodeClientWS(client_id="code")

    # Wait for connection
    time.sleep(1)

    if not client.connected:
        print("❌ Not connected. Make sure server_ws.py is running.")
        exit(1)

    # Register handler
    def handle_response(msg):
        print(f"\n📨 Received: {msg['type']}")
        print(f"   From: {msg['from']}")
        print(f"   Payload: {msg['payload']}")

    client.on('claude_response', handle_response)
    client.on('test', handle_response)

    # Send test message
    print("\n📤 Sending test message to browser...")
    success = client.send('browser', 'command', {
        'action': 'run_prompt',
        'text': 'What is 2+2?'
    })

    if success:
        print("✅ Message sent")

        # Wait for response
        print("⏳ Waiting for response (10 seconds)...")
        response = client.wait_for_message('claude_response', timeout=10)

        if response:
            print(f"\n✅ Got response: {response['payload']}")
        else:
            print("\n⚠️  No response received (browser might not be connected)")

    # Keep alive
    print("\n🔄 Client running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Closing...")
        client.close()
