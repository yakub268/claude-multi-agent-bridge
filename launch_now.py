#!/usr/bin/env python3
"""
🚀 AUTOMATED LAUNCH - NO INTERACTION REQUIRED
==============================================

Runs all optimization steps automatically.
Uses Browser Claude to optimize launch materials.

Usage:
    python launch_now.py
"""

from code_client import CodeClient
import time
import sys

class AutoLauncher:
    def __init__(self):
        self.client = CodeClient()
        self.wait_time = 20  # seconds to wait for each response

    def send_and_collect(self, prompt: str, label: str):
        """Send prompt and collect response"""
        print(f"\n{'='*70}")
        print(f"📤 {label}")
        print('='*70)
        print("Sending to Browser Claude...")

        # Send the prompt
        self.client.send('browser', 'command', {
            'action': 'run_prompt',
            'text': prompt
        })

        # Wait for response
        print(f"⏳ Waiting {self.wait_time} seconds...")
        time.sleep(self.wait_time)

        # Collect response
        messages = self.client.poll()

        for msg in messages:
            if msg.get('type') == 'claude_response':
                response = msg['payload']['response']
                print(f"\n✅ Response received ({len(response)} chars)\n")
                print('='*70)
                print('RESULT:')
                print('='*70)
                print(response)
                print('='*70)
                return response

        print("❌ No response received")
        return None

    def optimize_twitter(self):
        """Optimize Twitter thread"""
        prompt = """I'm launching a project on Twitter. Here's my thread:

Tweet 1: I just built something wild 🧵
Claude instances can now talk to each other.
Code → Browser → Code. Real-time. Bidirectional.
Here's how it changes AI development:

Tweet 2: The problem: You're coding in Claude Code while researching in Browser Claude. You copy-paste between them. It's 2026. We can do better.

Tweet 3: The solution: Direct AI-to-AI communication
c.send('browser', 'command', {'text': 'Research React'})
response = c.poll()
5 steps → 1 line of code

Tweet 4: How it works:
→ HTTP message bus
→ Chrome extension (CSP-compliant)
→ DOM manipulation
→ Response extraction
End-to-end: ~3 seconds

Tweet 5: Use cases:
1. Parallel research
2. Multi-model consensus
3. Extended context
4. Automated workflows

Tweet 6: The meta part: I USED THIS TOOL TO LAUNCH ITSELF 🤯
Browser Claude helped optimize these tweets.
Multi-agent AI in action.

Tweet 7: Open sourced:
→ github.com/yakub268/claude-multi-agent-bridge
→ MIT License
→ Working examples
Star if inspired ⭐
@AnthropicAI

Optimize this for MAXIMUM viral potential. Make it punchy, add perfect hashtags, improve hooks. Keep under 280 chars per tweet."""

        return self.send_and_collect(prompt, "TWITTER THREAD OPTIMIZATION")

    def optimize_reddit(self):
        """Optimize Reddit post"""
        prompt = """I'm posting to r/ClaudeAI. Optimize this for Reddit:

Title: I built a system for Claude instances to communicate with each other

I was switching between Claude Code (dev) and Browser Claude (research), copy-pasting constantly.

So I built a bridge. Now they talk directly.

Example:
```python
c.send('browser', 'command', {'text': 'Research React hooks'})
response = c.poll()  # Response from Browser Claude
```

Tech: HTTP message bus, Chrome extension (CSP-compliant), Python client

Status: Working, MIT licensed, examples included
github.com/yakub268/claude-multi-agent-bridge

Optimize this for r/ClaudeAI:
1. Better title (engaging but not clickbait)
2. Perfect opening (Reddit users decide in 3 sec)
3. Better structure (bullets, code formatting)
4. Add tl;dr
5. Reddit tone (genuine, not corporate)"""

        return self.send_and_collect(prompt, "REDDIT POST OPTIMIZATION")

    def get_hn_strategy(self):
        """Get Hacker News strategy"""
        prompt = """I'm submitting to Hacker News:

Project: Claude Multi-Agent Bridge (AI instances talking to each other)
URL: github.com/yakub268/claude-multi-agent-bridge

Give me:
1. Perfect "Show HN:" title (what works on HN)
2. First comment as maker (provide context)
3. Potential criticisms + how to address
4. Best posting time
5. Common HN mistakes to avoid

Tech: HTTP message bus, Chrome extension, real-time bidirectional communication"""

        return self.send_and_collect(prompt, "HACKER NEWS STRATEGY")

    def get_viral_tactics(self):
        """Get viral growth tactics"""
        prompt = """My open source project: Claude Multi-Agent Bridge (AI instances communicating)
github.com/yakub268/claude-multi-agent-bridge

Posted to: Twitter, Reddit r/ClaudeAI, planning Hacker News

Give me viral growth tactics:
1. Other platforms I'm missing
2. Timing strategy for each platform
3. How to get Anthropic team's attention
4. AI influencers to reach out to (who?)
5. Creative promo ideas

The project is genuinely useful and working. I want maximum reach."""

        return self.send_and_collect(prompt, "VIRAL GROWTH TACTICS")

def main():
    print("="*70)
    print("🚀 AUTOMATED LAUNCH - USING OUR OWN TOOL!")
    print("="*70)
    print("\nThis script uses Browser Claude to optimize launch materials.")
    print("Make sure you have a FRESH claude.ai tab open!\n")

    # Give user 5 seconds to prepare
    for i in range(5, 0, -1):
        print(f"Starting in {i}...", end='\r')
        time.sleep(1)
    print("Starting NOW!     \n")

    launcher = AutoLauncher()

    # Run all optimizations
    results = {}

    print("\n🐦 PHASE 1: Twitter Optimization")
    results['twitter'] = launcher.optimize_twitter()
    time.sleep(3)

    print("\n\n📱 PHASE 2: Reddit Optimization")
    results['reddit'] = launcher.optimize_reddit()
    time.sleep(3)

    print("\n\n🟠 PHASE 3: Hacker News Strategy")
    results['hn'] = launcher.get_hn_strategy()
    time.sleep(3)

    print("\n\n🔥 PHASE 4: Viral Growth Tactics")
    results['viral'] = launcher.get_viral_tactics()

    # Summary
    print("\n\n" + "="*70)
    print("🎉 LAUNCH OPTIMIZATION COMPLETE!")
    print("="*70)

    successful = sum(1 for v in results.values() if v is not None)
    print(f"\n✅ Successfully optimized: {successful}/4 steps")

    if successful == 4:
        print("\n🚀 ALL OPTIMIZATIONS COMPLETE!")
        print("\nYou now have:")
        print("  ✅ Viral-optimized Twitter thread")
        print("  ✅ Reddit post tailored for r/ClaudeAI")
        print("  ✅ Hacker News strategy and timing")
        print("  ✅ Additional viral growth tactics")
        print("\n📋 All created using Browser Claude via our own tool!")
        print("\n🎯 Now go post them and watch the stars roll in!")
    else:
        print("\n⚠️  Some optimizations failed")
        print("   Make sure:")
        print("   1. Browser Claude tab is open on claude.ai")
        print("   2. Extension is enabled")
        print("   3. Message bus is running")
        print("\n💡 You can still use the templates in LAUNCH.md")

    print("\n" + "="*70)
    print("Repository: https://github.com/yakub268/claude-multi-agent-bridge")
    print("="*70)

if __name__ == '__main__':
    main()
