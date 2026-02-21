"""
Multi-Model Consensus Example
==============================

Ask the same question to multiple Claude instances and compare answers.
Useful for:
- Validating important decisions
- Getting diverse perspectives
- Comparing reasoning approaches

Usage:
    python examples/consensus.py "Should I use REST or GraphQL for my API?"
"""
from code_client import CodeClient
import time
import sys

def get_consensus(question: str):
    """Ask multiple Claude instances the same question"""
    c = CodeClient()

    instances = ['browser']  # Can add 'desktop' when available

    print(f"🤔 Question: {question}\n")
    print(f"📊 Asking {len(instances)} Claude instance(s)...\n")

    # Send to all instances
    for instance in instances:
        c.send(instance, 'command', {
            'action': 'run_prompt',
            'text': question
        })

    # Collect responses
    responses = {}
    start = time.time()

    while (time.time() - start) < 30 and len(responses) < len(instances):
        messages = c.poll()

        for msg in messages:
            if msg.get('type') == 'claude_response':
                from_instance = msg.get('from', 'unknown')
                if from_instance not in responses:
                    responses[from_instance] = msg['payload']['response']
                    print(f"✅ Got response from {from_instance}")

        time.sleep(1)

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70 + "\n")

    for instance, response in responses.items():
        print(f"📍 {instance.upper()}:")
        print(f"{response}\n")
        print("-" * 70 + "\n")

    # Simple consensus check
    if len(responses) > 1:
        print("💡 CONSENSUS:")
        # Count similar keywords/phrases
        all_text = ' '.join(responses.values()).lower()

        if 'rest' in all_text and 'graphql' in all_text:
            print("Both approaches mentioned - nuanced answer")
        elif len(set(len(r) for r in responses.values())) < 50:
            print("Responses are similar length - likely agreement")
        else:
            print("Diverse perspectives - review each carefully")

def main():
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
    else:
        question = "What's more important in software: simplicity or performance?"

    get_consensus(question)

if __name__ == '__main__':
    main()
