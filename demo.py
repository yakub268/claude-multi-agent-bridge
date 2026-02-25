"""
Demo: Three-way communication between Code, Browser, and Desktop
"""

import time
from code_client import CodeClient


def main():
    print("🚀 Multi-Claude Communication Demo\n")

    # Initialize client
    client = CodeClient()

    # Check bus status
    print("📡 Checking message bus...")
    status = client.status()

    if status.get("status") != "running":
        print("❌ Message bus not running!")
        print("   Start with: python server.py")
        return

    print(f"✅ Bus running: {status.get('message_count', 0)} messages in queue\n")

    # Demo 1: Send command to browser
    print("=" * 50)
    print("DEMO 1: Code → Browser")
    print("=" * 50)
    print("Sending prompt to browser Claude...")

    success = client.send(
        to="browser",
        msg_type="command",
        payload={
            "action": "run_prompt",
            "text": "What's the cube root of 27? Reply with just the number.",
        },
    )

    if success:
        print("✅ Command sent to browser")
        print("   (Check browser Claude for the prompt)\n")
    else:
        print("❌ Failed to send command\n")

    time.sleep(2)

    # Demo 2: Broadcast status
    print("=" * 50)
    print("DEMO 2: Broadcast to All")
    print("=" * 50)
    print("Broadcasting status to all clients...")

    client.broadcast(
        "status",
        {
            "source": "code",
            "message": "Trading bot started",
            "balance": 1250.50,
            "active_positions": 3,
        },
    )

    print("✅ Broadcast sent\n")
    time.sleep(1)

    # Demo 3: Listen for responses
    print("=" * 50)
    print("DEMO 3: Listen for Messages")
    print("=" * 50)
    print("Listening for 10 seconds...")
    print("(Try using the browser extension popup to send a test message)\n")

    # Register handlers
    def on_response(msg):
        print(f"\n📨 RESPONSE from {msg['from']}:")
        print(f"   {msg['payload']}\n")

    def on_test(msg):
        print(f"\n🧪 TEST MESSAGE from {msg['from']}:")
        print(f"   {msg['payload']}\n")

    def on_status(msg):
        print(f"\n📊 STATUS from {msg['from']}:")
        print(f"   {msg['payload']}\n")

    client.on("response", on_response)
    client.on("test", on_test)
    client.on("status", on_status)

    # Listen for 10 seconds
    try:
        client.listen(interval=1.0, duration=10.0)
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted")
        return

    # Demo 4: Check message queue
    print("\n" + "=" * 50)
    print("DEMO 4: Recent Messages")
    print("=" * 50)

    messages = client.poll()
    if messages:
        print(f"Found {len(messages)} messages:\n")
        for msg in messages[-5:]:  # Last 5
            print(f"  [{msg['from']}→{msg['to']}] {msg['type']}")
    else:
        print("No messages in queue")

    print("\n✅ Demo complete!")
    print("\nNext steps:")
    print("  1. Install browser extension")
    print("  2. Open claude.ai in browser")
    print("  3. Check extension popup")
    print("  4. Try sending messages between clients")
    print("  5. Use Playwright bridge for automation")


if __name__ == "__main__":
    main()
