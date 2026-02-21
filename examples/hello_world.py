"""
Hello World - Simplest Multi-Agent Communication
=================================================

The absolute simplest example of Claude-to-Claude communication.

Usage:
    python examples/hello_world.py
"""
from code_client import CodeClient
import time

def main():
    print("🚀 Claude Multi-Agent Bridge - Hello World\n")

    # Create client
    c = CodeClient()

    # Send message to Browser Claude
    print("📤 Sending: 'What is 2+2? Reply with ONLY the number.'")

    c.send('browser', 'command', {
        'action': 'run_prompt',
        'text': 'What is 2+2? Reply with ONLY the number.'
    })

    # Wait for response
    print("⏳ Waiting for response...\n")

    for _ in range(15):  # Try for 15 seconds
        time.sleep(1)

        messages = c.poll()

        for msg in messages:
            if msg.get('type') == 'claude_response':
                response = msg['payload']['response']
                print(f"📨 Response: {response}")
                print("\n✅ Success! Two Claude instances just communicated.")
                return

    print("⏰ Timeout - Make sure:")
    print("  1. Message bus is running (python server.py)")
    print("  2. Extension is installed and enabled")
    print("  3. You have a claude.ai tab open")

if __name__ == '__main__':
    main()
