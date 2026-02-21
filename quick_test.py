"""
Quick test - send prompt and wait for correct response
"""
from code_client import CodeClient
import time

client = CodeClient()

print("🧪 Testing fixed response extraction...\n")

# Clear old messages
print("📭 Clearing old messages...")
client.poll()  # drain queue
time.sleep(1)

# Send simple math question
question = "What is 9 + 3? Reply with JUST the number."
print(f"📤 Sending: {question}")

client.send("browser", "command", {
    "action": "run_prompt",
    "text": question
})

print("⏳ Waiting for response (20 seconds)...\n")

seen = set()
start = time.time()
response_found = False

while (time.time() - start) < 20:
    messages = client.poll()

    for msg in messages:
        msg_id = msg.get('id')
        if msg_id in seen:
            continue
        seen.add(msg_id)

        if msg.get('from') == 'browser' and msg.get('type') == 'claude_response':
            payload = msg.get('payload', {})
            response = payload.get('response', '')

            print(f"✅ Got response: {response}\n")

            # Check if it's the correct answer (12) not the prompt
            if '12' in response and question not in response:
                print("🎉 SUCCESS! Extension is extracting Claude's responses correctly!")
                response_found = True
                break
            elif question in response:
                print("❌ FAIL: Still extracting the prompt, not the response")
                print("   Did you reload the extension?")
                response_found = True
                break

    if response_found:
        break

    time.sleep(1)

if not response_found:
    print("⏰ Timeout - no response received")
    print("   Check that:")
    print("   1. Extension is reloaded")
    print("   2. Browser is on claude.ai tab")
    print("   3. Message bus is running")
