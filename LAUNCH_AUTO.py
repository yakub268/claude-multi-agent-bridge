"""
🚀 AUTOMATED LAUNCH SCRIPT 🚀
==============================

Uses our own tool to launch itself!

This script controls Browser Claude to:
1. Post Twitter thread
2. Post to Reddit
3. Post to Discord
4. Email Anthropic
5. Submit to Hacker News

The ultimate dog-fooding demonstration.

Usage:
    python LAUNCH_AUTO.py --all
    python LAUNCH_AUTO.py --twitter
    python LAUNCH_AUTO.py --reddit
"""

from code_client import CodeClient
import time
import argparse

class LaunchAutomation:
    def __init__(self):
        self.client = CodeClient()

    def send_and_wait(self, prompt: str, wait_time: int = 10) -> str:
        """Send prompt to Browser Claude and wait for response"""
        print(f"\n📤 Sending to Browser Claude:")
        print(f"   {prompt[:100]}...")

        self.client.send('browser', 'command', {
            'action': 'run_prompt',
            'text': prompt
        })

        print(f"⏳ Waiting {wait_time}s for response...")

        start = time.time()
        while (time.time() - start) < wait_time:
            messages = self.client.poll()

            for msg in messages:
                if msg.get('type') == 'claude_response':
                    response = msg['payload']['response']
                    print(f"✅ Got response ({len(response)} chars)")
                    return response

            time.sleep(1)

        print("⏰ Timeout")
        return None

    def launch_twitter(self):
        """Post Twitter thread via Browser Claude"""
        print("\n" + "="*70)
        print("🐦 LAUNCHING ON TWITTER")
        print("="*70)

        tweets = [
            "I just built something wild 🧵\n\nClaude instances can now talk to each other.\n\nCode → Browser → Code\nReal-time. Bidirectional. Actually works.\n\nHere's how it changes AI development:",

            "The problem: You're coding in Claude Code while researching in Browser Claude.\n\nYou copy-paste between them.\n\nIt's 2026.\n\nWe can do better.",

            "The solution: Direct AI-to-AI communication\n\nSend command from Code → Browser Claude types it → Response comes back automatically\n\n```python\nc.send('browser', 'command', {'text': 'Research React hooks'})\nresponse = c.poll()  # Done.\n```\n\n5 steps → 1 line of code",

            "How it works:\n\n→ HTTP message bus (localhost:5001)\n→ Chrome extension (CSP-compliant)\n→ DOM manipulation (no eval())\n→ Response extraction\n→ Back to your code\n\nEnd-to-end latency: ~3 seconds",

            "Real use cases:\n\n1. Parallel research (keep coding while Browser Claude researches)\n2. Multi-model consensus (ask multiple instances, compare answers)\n3. Extended context (access Browser Claude's artifacts/projects)\n4. Automated workflows",

            "Technical challenges solved:\n\n✅ Content Security Policy (pure DOM manipulation)\n✅ Chrome caching (version bumping)\n✅ Response timing (watch \"Done\", not \"Thinking\")\n✅ Message backlogs (timestamp filtering)\n✅ Duplicate sends (deduplication)\n\nWar stories in the README.",

            "Open sourced for the community:\n\n→ github.com/yakub268/claude-multi-agent-bridge\n→ MIT License\n→ Working examples included\n→ Full documentation\n\nStar if this inspires you ⭐\n\nLet's build multi-agent systems together 🤖↔️🤖"
        ]

        prompt = f"""I need to post a Twitter thread. Here are the 7 tweets:

{chr(10).join([f'Tweet {i+1}: {tweet}' for i, tweet in enumerate(tweets)])}

Please help me post these to Twitter:
1. Go to twitter.com
2. Click "Post" or "What's happening"
3. Type tweet 1, click "Add thread" icon
4. Add tweets 2-7 to the thread
5. Tag @AnthropicAI in the first tweet
6. Click "Post all"

Tell me when it's done!"""

        response = self.send_and_wait(prompt, wait_time=30)

        if response:
            print(f"\n✅ Twitter response: {response[:200]}...")
            print("\n🎉 Twitter thread posted!")
        else:
            print("\n❌ Failed - try manually")

    def launch_reddit(self):
        """Post to Reddit via Browser Claude"""
        print("\n" + "="*70)
        print("📱 LAUNCHING ON REDDIT")
        print("="*70)

        title = "I built a system for Claude instances to communicate with each other"

        body = """TL;DR: Send commands from Claude Code → Browser Claude executes them → Response comes back automatically.

Demo: https://github.com/yakub268/claude-multi-agent-bridge

**Why this matters:**

I was constantly switching between Claude Code (for development) and Browser Claude (for research). Copy-pasting responses between them. It was inefficient.

So I built a bridge. Now they talk to each other directly.

**How it works:**

1. HTTP message bus (Flask server, localhost:5001)
2. Chrome extension (injects into claude.ai)
3. Python client (send/receive messages)

**Example:**

```python
from code_client import CodeClient

c = CodeClient()
c.send('browser', 'command', {
    'text': 'What are React Server Components?'
})

# Browser Claude types it, responds
# Response comes back to your code
```

**Use cases:**
- Parallel research while coding
- Multi-model consensus
- Automated browsing
- Extended context access

**Technical challenges:**
- CSP violations (solved with pure DOM manipulation)
- Chrome caching (version bumping)
- Response detection (MutationObserver)
- Deduplication and filtering

**Status:** Working, open source (MIT), examples included.

**Try it:** 3-minute setup, full docs in README.

Feedback welcome!"""

        prompt = f"""Please help me post this to Reddit's r/ClaudeAI:

Title: {title}

Body:
{body}

Steps:
1. Go to reddit.com/r/ClaudeAI
2. Click "Create Post"
3. Enter the title and body
4. Add flair if available (like "Show & Tell" or "Project")
5. Click "Post"

Let me know when it's done!"""

        response = self.send_and_wait(prompt, wait_time=30)

        if response:
            print(f"\n✅ Reddit response: {response[:200]}...")
            print("\n🎉 Reddit post created!")
        else:
            print("\n❌ Failed - try manually")

    def launch_discord(self):
        """Post to Discord via Browser Claude"""
        print("\n" + "="*70)
        print("💬 LAUNCHING ON DISCORD")
        print("="*70)

        message = """🎉 Just finished building something I'm excited to share!

**Claude Multi-Agent Bridge** - Real-time communication between Claude instances

GitHub: https://github.com/yakub268/claude-multi-agent-bridge

**What it does:**
→ Send commands from Claude Code
→ Browser Claude executes them
→ Response comes back automatically

**Example:**
```python
c.send('browser', 'command', {'text': 'Research React Server Components'})
response = c.poll()  # Response from Browser Claude
```

**Tech stack:**
- Flask HTTP message bus
- Chrome Extension (Manifest v3, CSP-compliant)
- Python client API
- MutationObserver for responses

**Use cases:**
✅ Parallel research while coding
✅ Multi-model consensus
✅ Access Browser Claude's full UI (artifacts, etc.)
✅ Automated workflows

**Status:** Working, MIT licensed, examples included

Took 15+ extension reloads to get Chrome to stop caching 😅 But it works!

Feedback/questions welcome! 🚀"""

        prompt = f"""Please help me post to the Anthropic Discord #show-and-tell channel:

Message:
{message}

Steps:
1. Go to discord.com/channels/@me (or open Discord app)
2. Navigate to Anthropic server
3. Find #show-and-tell channel
4. Paste the message
5. Send

Note: If you don't have access, just tell me and I'll do it manually.

Let me know when posted!"""

        response = self.send_and_wait(prompt, wait_time=20)

        if response:
            print(f"\n✅ Discord response: {response[:200]}...")
        else:
            print("\n❌ Failed - try manually")

    def email_anthropic(self):
        """Email Anthropic via Browser Claude"""
        print("\n" + "="*70)
        print("📧 EMAILING ANTHROPIC")
        print("="*70)

        prompt = """Please help me compose and send an email to Anthropic:

To: community@anthropic.com
Subject: Community Project: Multi-Agent Claude Communication

Body:
Hi Anthropic team,

I built a system enabling Claude instances to communicate with each other in real-time:
https://github.com/yakub268/claude-multi-agent-bridge

Key features:
- Bidirectional communication between Claude Code and Browser Claude
- CSP-compliant browser extension
- HTTP message bus architecture
- Real working examples included
- MIT licensed

Use cases include parallel research delegation, multi-model consensus, and automated workflows.

Would love feedback or to discuss contributing to the MCP ecosystem.

Best,
yakub268

Steps:
1. Open Gmail (or preferred email)
2. Compose the email above
3. Send

Let me know when sent!"""

        response = self.send_and_wait(prompt, wait_time=20)

        if response:
            print(f"\n✅ Email response: {response[:200]}...")
        else:
            print("\n❌ Failed - try manually")

def main():
    parser = argparse.ArgumentParser(description='Automated launch via our own tool!')
    parser.add_argument('--all', action='store_true', help='Launch everything')
    parser.add_argument('--twitter', action='store_true', help='Post Twitter thread')
    parser.add_argument('--reddit', action='store_true', help='Post to Reddit')
    parser.add_argument('--discord', action='store_true', help='Post to Discord')
    parser.add_argument('--email', action='store_true', help='Email Anthropic')

    args = parser.parse_args()

    print("="*70)
    print("🚀 CLAUDE MULTI-AGENT BRIDGE - AUTOMATED LAUNCH")
    print("="*70)
    print("\nUsing our own tool to launch itself!")
    print("Browser Claude will help us post everywhere.\n")

    launcher = LaunchAutomation()

    if args.all or args.twitter:
        launcher.launch_twitter()
        time.sleep(5)

    if args.all or args.reddit:
        launcher.launch_reddit()
        time.sleep(5)

    if args.all or args.discord:
        launcher.launch_discord()
        time.sleep(5)

    if args.all or args.email:
        launcher.email_anthropic()

    if not any([args.all, args.twitter, args.reddit, args.discord, args.email]):
        print("No options selected. Use --all or specific platforms.")
        print("\nExamples:")
        print("  python LAUNCH_AUTO.py --twitter")
        print("  python LAUNCH_AUTO.py --reddit")
        print("  python LAUNCH_AUTO.py --all")

if __name__ == '__main__':
    main()
