"""
🚀 LAUNCH ASSISTANT - Ultimate Dog-Fooding
===========================================

Uses Browser Claude to help optimize and post launch materials.
This is our tool launching itself!

Usage:
    python LAUNCH_ASSISTANT.py

Interactive mode - Browser Claude helps you with each step.
"""

from code_client import CodeClient
import time

class LaunchAssistant:
    def __init__(self):
        self.client = CodeClient()
        print("="*70)
        print("🚀 CLAUDE MULTI-AGENT BRIDGE - LAUNCH ASSISTANT")
        print("="*70)
        print("\n💡 Using our own tool to launch itself!")
        print("   Browser Claude will help optimize each post.\n")

    def ask_browser_claude(self, prompt: str, wait_time: int = 15) -> str:
        """Ask Browser Claude for help"""
        print("\n📤 Asking Browser Claude...")
        print(f"   {prompt[:80]}...")

        self.client.send('browser', 'command', {
            'action': 'run_prompt',
            'text': prompt
        })

        print("⏳ Waiting for response...")

        start = time.time()
        while (time.time() - start) < wait_time:
            messages = self.client.poll()

            for msg in messages:
                if msg.get('type') == 'claude_response':
                    response = msg['payload']['response']
                    print("✅ Got response!\n")
                    return response

            time.sleep(1)

        print("⏰ Timeout")
        return None

    def optimize_tweet_thread(self):
        """Get Browser Claude to optimize our Twitter thread"""
        print("\n" + "="*70)
        print("🐦 STEP 1: OPTIMIZE TWITTER THREAD")
        print("="*70)

        original_thread = """Tweet 1: I just built something wild 🧵

Claude instances can now talk to each other.

Code → Browser → Code
Real-time. Bidirectional. Actually works.

Here's how it changes AI development:

Tweet 2: The problem: You're coding in Claude Code while researching in Browser Claude.

You copy-paste between them.

It's 2026.

We can do better.

Tweet 3: The solution: Direct AI-to-AI communication

Send command from Code → Browser Claude types it → Response comes back automatically

c.send('browser', 'command', {'text': 'Research React hooks'})
response = c.poll()

5 steps → 1 line of code

Tweet 4-7: [technical details, use cases, challenges solved, CTA]"""

        prompt = """I'm about to launch my multi-agent AI project on Twitter. Here's my draft thread:

{original_thread}

Can you:
1. Optimize for maximum engagement (Twitter algorithm favors certain patterns)
2. Make the hook more compelling
3. Suggest better hashtags
4. Improve the CTA
5. Keep it under 280 chars per tweet

Repository: github.com/yakub268/claude-multi-agent-bridge"""

        response = self.ask_browser_claude(prompt, wait_time=20)

        if response:
            print("="*70)
            print("OPTIMIZED THREAD:")
            print("="*70)
            print(response)
            print("\n" + "="*70)
            print("✅ Copy this optimized version and post to Twitter!")
            print("   Don't forget to tag @AnthropicAI")
        else:
            print("❌ Timeout - use original version from LAUNCH.md")

    def optimize_reddit_post(self):
        """Get Browser Claude to optimize Reddit post"""
        print("\n" + "="*70)
        print("📱 STEP 2: OPTIMIZE REDDIT POST")
        print("="*70)

        prompt = """I'm posting to r/ClaudeAI about my project: Claude Multi-Agent Bridge

github.com/yakub268/claude-multi-agent-bridge

It enables Claude Code and Browser Claude to communicate in real-time.

Can you help me:
1. Write an attention-grabbing title (not clickbait, but compelling)
2. Optimize the first paragraph (Reddit users decide in 3 seconds)
3. Structure for Reddit's format (bullets, code blocks, etc.)
4. Add appropriate tone (Reddit likes genuine, not corporate)
5. Include a tl;dr

Key points to cover:
- Problem: copying between Claude instances
- Solution: direct AI-to-AI communication
- Technical: CSP-compliant extension, message bus
- Status: working, MIT licensed, examples included"""

        response = self.ask_browser_claude(prompt, wait_time=20)

        if response:
            print("="*70)
            print("OPTIMIZED REDDIT POST:")
            print("="*70)
            print(response)
            print("\n" + "="*70)
            print("✅ Copy this and post to r/ClaudeAI")
        else:
            print("❌ Timeout - use original version from LAUNCH.md")

    def get_hn_advice(self):
        """Get Browser Claude's advice for Hacker News"""
        print("\n" + "="*70)
        print("🟠 STEP 3: HACKER NEWS STRATEGY")
        print("="*70)

        prompt = """I'm submitting to Hacker News:

Project: Claude Multi-Agent Bridge
URL: github.com/yakub268/claude-multi-agent-bridge

It's a system for Claude AI instances to communicate with each other.

Can you help me:
1. Write the perfect HN title (format: "Show HN: ...")
2. Craft the first comment (makers should always post context)
3. List potential criticisms and how to address them
4. Suggest best time to post (HN has specific patterns)
5. Warn me about common HN mistakes to avoid

Technical details:
- HTTP message bus
- Chrome extension (CSP-compliant)
- Real-time bidirectional communication
- MIT licensed, working examples"""

        response = self.ask_browser_claude(prompt, wait_time=20)

        if response:
            print("="*70)
            print("HACKER NEWS STRATEGY:")
            print("="*70)
            print(response)
            print("\n" + "="*70)
            print("✅ Follow this advice when posting to HN")
        else:
            print("❌ Timeout - use original version from LAUNCH.md")

    def get_viral_advice(self):
        """Get Browser Claude's advice on going viral"""
        print("\n" + "="*70)
        print("🔥 STEP 4: VIRAL STRATEGY")
        print("="*70)

        prompt = """I just launched an open source project that enables Claude AI instances to communicate with each other:

github.com/yakub268/claude-multi-agent-bridge

I've posted to:
- Twitter (thread with @AnthropicAI tag)
- Reddit r/ClaudeAI
- Hacker News

What else should I do to maximize reach?

Specifically:
1. Other platforms I'm missing?
2. Timing strategy (when to post where)?
3. How to get Anthropic team's attention?
4. Should I reach out to AI influencers? Who?
5. Any creative promo ideas?

The project is genuinely useful - I use it myself. But I want the community to discover it."""

        response = self.ask_browser_claude(prompt, wait_time=20)

        if response:
            print("="*70)
            print("VIRAL STRATEGY:")
            print("="*70)
            print(response)
            print("\n" + "="*70)
            print("✅ Execute these additional tactics")
        else:
            print("❌ Timeout")

def main():
    assistant = LaunchAssistant()

    print("\n🎯 This assistant will help you optimize each launch post")
    print("   using Browser Claude's knowledge of each platform.\n")

    input("Press Enter to start (make sure Browser Claude tab is open)...")

    # Step by step optimization
    assistant.optimize_tweet_thread()
    input("\n\nPress Enter for next step...")

    assistant.optimize_reddit_post()
    input("\n\nPress Enter for next step...")

    assistant.get_hn_advice()
    input("\n\nPress Enter for next step...")

    assistant.get_viral_advice()

    print("\n" + "="*70)
    print("🎉 LAUNCH OPTIMIZATION COMPLETE!")
    print("="*70)
    print("\nYou now have optimized versions of:")
    print("  ✅ Twitter thread")
    print("  ✅ Reddit post")
    print("  ✅ Hacker News strategy")
    print("  ✅ Viral growth tactics")
    print("\n📋 All optimized by Browser Claude using our own tool!")
    print("\n🚀 Now go post them and watch the stars roll in!")

if __name__ == '__main__':
    main()
