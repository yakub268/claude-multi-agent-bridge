#!/usr/bin/env python3
"""
Demo script for GIF creation - shows clean multi-agent communication
"""
from code_client import CodeClient
import time
import sys

def typewriter_print(text, delay=0.03):
    """Print with typewriter effect"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def main():
    print("="*70)
    typewriter_print("🤖 CLAUDE MULTI-AGENT BRIDGE DEMO", delay=0.02)
    print("="*70)
    print()

    typewriter_print("Initializing client...", delay=0.02)
    c = CodeClient()
    print("✅ Connected to message bus")
    print()

    typewriter_print("Sending prompt to Browser Claude:", delay=0.02)
    prompt = "What is the capital of France? Reply with just the city name."
    print(f'  "{prompt}"')
    print()

    c.send('browser', 'command', {
        'action': 'run_prompt',
        'text': prompt
    })

    typewriter_print("📤 Message sent! Waiting for Browser Claude...", delay=0.02)
    print()

    # Poll for response
    for i in range(20):
        time.sleep(1)
        messages = c.poll()

        for msg in messages:
            if msg.get('type') == 'claude_response':
                response = msg['payload']['response']
                print()
                typewriter_print("📥 Response received from Browser Claude:", delay=0.02)
                print()
                print(f'  "{response}"')
                print()
                print("="*70)
                typewriter_print("✅ COMMUNICATION SUCCESSFUL!", delay=0.02)
                print("="*70)
                return

    print("\n⏰ Timeout - no response received")

if __name__ == '__main__':
    main()
