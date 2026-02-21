"""
Four-way conversation test between all Claude instances
"""
from code_client import CodeClient
import time
import json

def main():
    client = CodeClient()

    print("=" * 70)
    print("🔗 FOUR-WAY CLAUDE CONVERSATION TEST")
    print("=" * 70)
    print()

    # Test 1: Check who's online
    print("1️⃣  Checking who's connected to the message bus...\n")

    status = client.status()
    print(f"   Message Bus: {status.get('status')}")
    print(f"   Messages in queue: {status.get('message_count')}")
    print()

    # Test 2: Send broadcast to all
    print("2️⃣  Broadcasting to all Claude instances...\n")

    client.broadcast("roll_call", {
        "from": "Code CLI (main session)",
        "message": "Sound off! Who's here?",
        "timestamp": time.time()
    })

    print("   ✅ Broadcast sent\n")

    # Test 3: Send prompt to browser
    print("3️⃣  Sending test prompt to Browser Claude...\n")

    test_question = "What is 144 divided by 12? Reply with JUST the number."

    client.send("browser", "command", {
        "action": "run_prompt",
        "text": test_question
    })

    print(f"   📤 Sent: {test_question}")
    print()

    # Test 4: Listen for responses
    print("4️⃣  Listening for responses (15 seconds)...\n")

    seen_messages = set()
    start_time = time.time()

    while (time.time() - start_time) < 15:
        messages = client.poll()

        for msg in messages:
            msg_id = msg.get('id')
            if msg_id in seen_messages:
                continue

            seen_messages.add(msg_id)

            from_client = msg.get('from')
            msg_type = msg.get('type')

            # Skip our own messages
            if from_client == 'code':
                continue

            print(f"   📨 [{from_client}] {msg_type}")

            # Show payload for interesting messages
            if msg_type == 'claude_response':
                payload = msg.get('payload', {})
                response = payload.get('response', 'N/A')
                print(f"      Response: {response[:100]}")
            elif msg_type == 'browser_ready':
                payload = msg.get('payload', {})
                print(f"      URL: {payload.get('url', 'N/A')}")

            print()

        time.sleep(1)

    print()
    print("=" * 70)
    print("Test complete!")
    print("=" * 70)
    print()
    print("📊 Summary:")
    print(f"   Total messages seen: {len(seen_messages)}")
    print()
    print("💡 Next steps:")
    print("   - If you saw 'browser_ready': Extension is loaded ✅")
    print("   - If you saw 'claude_response': Full loop working ✅")
    print("   - If no responses: Check extension is on claude.ai tab")
    print()


if __name__ == "__main__":
    main()
