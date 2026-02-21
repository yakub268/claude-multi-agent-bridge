#!/usr/bin/env python3
"""
Automated demo recorder - captures browser + terminal interaction
"""
from code_client import CodeClient
import time
import subprocess
import sys
from pathlib import Path

def record_demo():
    """Record a clean demo showing the full communication loop"""

    print("="*70)
    print("🎬 DEMO RECORDER - Multi-Agent Bridge")
    print("="*70)
    print()
    print("This will demonstrate:")
    print("  1. Code sending: 'What is 2+2?'")
    print("  2. Browser Claude receiving and processing")
    print("  3. Response: '4' coming back")
    print()
    print("SETUP:")
    print("  ✅ Server running (python server.py in separate terminal)")
    print("  ✅ Fresh claude.ai tab open")
    print("  ✅ Extension loaded")
    print()
    print("RECORDING TIP:")
    print("  Use Windows Game Bar (Win+G) or OBS to record your screen")
    print("  Position terminal and browser side-by-side")
    print()

    input("Press Enter to start demo...")
    print()

    # Countdown
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    print("\n" + "="*70)
    print("🚀 DEMO STARTING")
    print("="*70)
    print()

    # Initialize client
    print("Initializing Multi-Agent Bridge...")
    c = CodeClient()
    print("✅ Connected to message bus\n")
    time.sleep(1)

    # Show the prompt
    prompt = "What is 2+2? Reply with ONLY the number."
    print(f"📤 Sending to Browser Claude:")
    print(f'   "{prompt}"')
    print()
    time.sleep(1)

    # Send message
    c.send('browser', 'command', {
        'action': 'run_prompt',
        'text': prompt
    })

    print("⏳ Message sent! Waiting for Browser Claude to respond...")
    print()
    time.sleep(2)

    # Poll for response
    response_received = False
    for i in range(15):
        time.sleep(1)
        print(f"   Polling... ({i+1}s)")

        messages = c.poll()
        for msg in messages:
            if msg.get('type') == 'claude_response':
                response = msg['payload']['response']
                print()
                print("="*70)
                print("📥 RESPONSE RECEIVED FROM BROWSER CLAUDE")
                print("="*70)
                print()
                print(f'   Answer: {response}')
                print()
                print("="*70)
                print("✅ MULTI-AGENT COMMUNICATION SUCCESSFUL!")
                print("="*70)
                print()
                print("Code → Browser → Code in ~3 seconds")
                print("No copy-paste. No tab switching. Just works.")
                response_received = True
                break

        if response_received:
            break

    if not response_received:
        print()
        print("⏰ Timeout - check that:")
        print("   1. Server is running")
        print("   2. Browser tab is open on claude.ai")
        print("   3. Extension is loaded")

    print()
    print("="*70)
    print("Demo complete! Record this and convert to GIF.")
    print("="*70)

if __name__ == '__main__':
    record_demo()
