"""
Research Assistant Example
==========================

Delegate research tasks to Browser Claude while you continue coding.
Browser Claude can access web search, read articles, analyze images.

Usage:
    python examples/research_assistant.py
"""
from code_client import CodeClient
import time

def main():
    c = CodeClient()

    # Define research tasks
    tasks = [
        "What are the key differences between React Server Components and traditional React?",
        "Find the most popular Python async frameworks in 2026",
        "Summarize the latest TypeScript 5.x features"
    ]

    print("🔬 Research Assistant - Delegating to Browser Claude\n")

    for i, task in enumerate(tasks, 1):
        print(f"📋 Task {i}/{len(tasks)}: {task}")

        # Send to Browser Claude
        c.send('browser', 'command', {
            'action': 'run_prompt',
            'text': task
        })

        print("   ⏳ Waiting for response...")

        # Wait for response
        start = time.time()
        while (time.time() - start) < 30:
            messages = c.poll()

            for msg in messages:
                if msg.get('type') == 'claude_response':
                    response = msg['payload']['response']
                    print(f"   ✅ Response received ({len(response)} chars)")
                    print(f"\n{response}\n")
                    print("-" * 70)
                    break
            else:
                time.sleep(1)
                continue
            break
        else:
            print("   ⏰ Timeout - no response\n")

        # Small delay between tasks
        time.sleep(2)

    print("\n✨ Research complete! All tasks delegated and responses collected.")

if __name__ == '__main__':
    main()
