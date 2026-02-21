"""
Claude Code Client
Allows Claude Code (CLI) to send/receive messages from browser/desktop
"""
import requests
import time
import json
from datetime import datetime
from typing import Optional, Dict, List, Callable


class CodeClient:
    def __init__(self, bus_url="http://localhost:5001"):
        self.bus_url = bus_url
        self.client_id = "code"
        self.last_timestamp = None
        self.handlers = {}  # message_type -> callback

    def send(self, to: str, msg_type: str, payload: Dict) -> bool:
        """Send message to another Claude instance"""
        try:
            response = requests.post(
                f"{self.bus_url}/api/send",
                json={
                    "from": self.client_id,
                    "to": to,
                    "type": msg_type,
                    "payload": payload
                },
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False

    def broadcast(self, msg_type: str, payload: Dict) -> bool:
        """Broadcast to all clients"""
        return self.send("all", msg_type, payload)

    def poll(self) -> List[Dict]:
        """Poll for new messages"""
        try:
            params = {"to": self.client_id}
            if self.last_timestamp:
                params["since"] = self.last_timestamp

            response = requests.get(
                f"{self.bus_url}/api/messages",
                params=params,
                timeout=2
            )

            if response.status_code == 200:
                messages = response.json().get("messages", [])
                if messages:
                    self.last_timestamp = messages[-1]["timestamp"]
                return messages
        except Exception as e:
            print(f"❌ Failed to poll: {e}")

        return []

    def listen(self, interval: float = 1.0, duration: Optional[float] = None):
        """Listen for messages and dispatch to handlers"""
        start_time = time.time()
        print(f"👂 Listening for messages (interval={interval}s)...")

        try:
            while True:
                messages = self.poll()

                for msg in messages:
                    msg_type = msg.get("type")
                    from_client = msg.get("from")
                    payload = msg.get("payload", {})

                    print(f"📨 [{from_client}] {msg_type}: {json.dumps(payload, indent=2)}")

                    # Dispatch to handler
                    if msg_type in self.handlers:
                        try:
                            self.handlers[msg_type](msg)
                        except Exception as e:
                            print(f"❌ Handler error: {e}")

                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n👋 Stopped listening")

    def on(self, msg_type: str, handler: Callable):
        """Register message handler"""
        self.handlers[msg_type] = handler

    def status(self) -> Dict:
        """Get bus status"""
        try:
            response = requests.get(f"{self.bus_url}/api/status", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"❌ Failed to get status: {e}")

        return {"status": "unreachable"}


# ============= Example Usage =============

if __name__ == "__main__":
    client = CodeClient()

    # Check if bus is running
    status = client.status()
    print(f"🚦 Bus status: {status}")

    if status.get("status") != "running":
        print("⚠️  Message bus not running. Start with: python server.py")
        exit(1)

    # Send test message to browser
    print("\n📤 Sending test message to browser...")
    client.send(
        to="browser",
        msg_type="command",
        payload={"action": "run_prompt", "text": "What's 2+2?"}
    )

    # Register handlers
    def on_response(msg):
        print(f"✅ Got response: {msg['payload']}")

    client.on("response", on_response)

    # Listen for 10 seconds
    print("\n👂 Listening for responses...")
    client.listen(interval=1.0, duration=10.0)
