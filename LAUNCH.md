# 🚀 Launch Materials

## Twitter Thread (Post this!)

**Tweet 1:**
```
I just built something wild 🧵

Claude instances can now talk to each other.

Code → Browser → Code
Real-time. Bidirectional. Actually works.

Here's how it changes AI development:
```

**Tweet 2:**
```
The problem: You're coding in Claude Code while researching in Browser Claude.

You copy-paste between them.

It's 2026.

We can do better.
```

**Tweet 3:**
```
The solution: Direct AI-to-AI communication

Send command from Code → Browser Claude types it → Response comes back automatically

python
c.send('browser', 'command', {'text': 'Research React hooks'})
response = c.poll()  # Done.


5 steps → 1 line of code
```

**Tweet 4:**
```
How it works:

→ HTTP message bus (localhost:5001)
→ Chrome extension (CSP-compliant)
→ DOM manipulation (no eval())
→ Response extraction
→ Back to your code

End-to-end latency: ~3 seconds
```

**Tweet 5:**
```
Real use cases:

1. Parallel research (keep coding while Browser Claude researches)
2. Multi-model consensus (ask multiple instances, compare answers)
3. Extended context (access Browser Claude's artifacts/projects)
4. Automated workflows
```

**Tweet 6:**
```
Technical challenges solved:

✅ Content Security Policy (pure DOM manipulation)
✅ Chrome caching (version bumping)
✅ Response timing (watch "Done", not "Thinking")
✅ Message backlogs (timestamp filtering)
✅ Duplicate sends (deduplication)

War stories in the README.
```

**Tweet 7:**
```
Open sourced for the community:

→ github.com/yakub268/claude-multi-agent-bridge
→ MIT License
→ Working examples included
→ Full documentation

Star if this inspires you ⭐

Let's build multi-agent systems together 🤖↔️🤖
```

---

## Reddit Posts

### r/ClaudeAI
**Title:** I built a system for Claude instances to communicate with each other

**Body:**
```
TL;DR: Send commands from Claude Code → Browser Claude executes them → Response comes back automatically.

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

Feedback welcome!
```

### r/MachineLearning
**Title:** [P] Multi-Agent Claude Communication via HTTP Message Bus

**Body:**
```
Paper/Code: https://github.com/yakub268/claude-multi-agent-bridge

**Abstract:**
Bidirectional communication system enabling Claude Code CLI, Browser Claude, and Desktop Claude to exchange messages in real-time via HTTP message bus.

**Key Contributions:**
1. CSP-compliant browser extension for claude.ai interaction
2. Message bus architecture with timestamp filtering
3. DOM manipulation without eval() or dynamic script injection
4. Response extraction using MutationObserver pattern

**Results:**
- End-to-end latency: ~2-5 seconds
- Success rate: >95% (after deduplication)
- No rate limiting observed

**Applications:**
- Multi-agent consensus systems
- Parallel task delegation
- Extended context windows via UI access
- Automated research workflows

**Implementation:**
- Python 3.8+ (Flask, requests)
- Chrome Extension (Manifest v3)
- DOM manipulation via querySelector

**Limitations:**
- Requires local message bus
- Chrome-only (Firefox/Safari planned)
- No message persistence

**Code:** MIT License, working examples included

Open to collaborations on extending this to other LLMs.
```

### r/Programming
**Title:** Built a multi-agent AI communication system (Claude → Claude)

**Body:**
```
I made a system where Claude AI instances can talk to each other.

GitHub: https://github.com/yakub268/claude-multi-agent-bridge

**The problem:**
I code in Claude Code CLI. I research in Browser Claude. I copy-paste between them manually.

**The solution:**
Direct AI-to-AI communication via HTTP message bus.

**Architecture:**
```
Code → Message Bus → Extension → Browser Claude
                                         ↓
Code ← Message Bus ← Extraction ← Browser Claude
```

**Example:**
```python
c.send('browser', 'command', {'text': 'Research async patterns'})
response = c.poll()  # Response from Browser Claude
```

**Technical highlights:**
- CSP-compliant (no eval, no inline scripts)
- MutationObserver for response detection
- Timestamp filtering (ignore message backlog)
- Deduplication logic

**Use cases:**
- Delegate research while coding
- Multi-model consensus
- Access Browser Claude's full UI (artifacts, projects)

**What I learned:**
- Chrome caches extension files AGGRESSIVELY (15+ reloads to get fixes loaded)
- claude.ai's CSP requires pure DOM manipulation
- "Thinking..." status never leaves DOM (watch "Done" instead)

**Status:** Working, MIT licensed, 3-minute setup

**Feedback welcome!** Especially on:
- Better response detection methods
- Multi-browser support
- Message persistence strategies
```

---

## Hacker News

**Title:** Show HN: Four-way communication between Claude AI instances

**Text:**
```
I built a system where Claude instances can communicate with each other via HTTP message bus.

Demo: https://github.com/yakub268/claude-multi-agent-bridge

**What it does:**

Send commands from Claude Code → Browser Claude executes them → Response returns to your code automatically.

**Why:**

I was constantly context-switching between Claude Code (development) and Browser Claude (research). I'd ask the same question twice, copy responses manually. Inefficient.

**How it works:**

1. HTTP message bus (Flask, port 5001)
2. Chrome extension (injects into claude.ai)
3. Python client API
4. DOM manipulation for prompt submission
5. MutationObserver for response extraction

**Technical challenges:**

- claude.ai's CSP blocks eval/inline scripts → Pure DOM manipulation
- Chrome caches extension files aggressively → Version bumping
- "Thinking..." status never disappears → Watch "Done" instead
- Message backlog on startup → Timestamp filtering
- MutationObserver fires multiple times → Deduplication

**Use cases:**

- Parallel research (delegate tasks while coding)
- Multi-model consensus (compare responses)
- Extended context (access Browser Claude's artifacts/projects)
- Automated workflows

**Current status:**

- Working (tested >50 round-trips)
- MIT licensed
- 3-minute setup
- Working examples included

**Future:**

- Desktop Claude integration (PyAutoGUI)
- Multi-tab routing
- WebSocket support
- Message persistence

**Try it:** Clone repo, run server.py, install extension, run examples/hello_world.py

Questions welcome!
```

---

## Discord (Anthropic Community)

**Channel:** #show-and-tell

**Message:**
```
🎉 Just finished building something I'm excited to share!

**Claude Multi-Agent Bridge** - Real-time communication between Claude instances

GitHub: https://github.com/yakub268/claude-multi-agent-bridge

**What it does:**
→ Send commands from Claude Code
→ Browser Claude executes them
→ Response comes back automatically

**Why:**
I was copy-pasting between Code and Browser constantly. Now they just... talk.

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

Feedback/questions welcome! 🚀
```

---

## Product Hunt (When Ready)

**Name:** Claude Multi-Agent Bridge

**Tagline:** Make Claude instances talk to each other in real-time

**Description:**
```
Send commands from Claude Code to Browser Claude. Get responses back automatically. No more copy-pasting between AI instances.

Perfect for:
→ Developers who use multiple Claude interfaces
→ Researchers delegating parallel tasks
→ Anyone building multi-agent AI systems

Technical innovation:
→ CSP-compliant browser extension
→ Real-time message bus
→ Smart response extraction

Open source (MIT). Working examples. 3-minute setup.
```

**First Comment (as maker):**
```
Hey PH! 👋

I built this because I was constantly switching between Claude Code (for development) and Browser Claude (for research).

The manual workflow:
1. Ask question in Code
2. Switch to Browser
3. Ask again
4. Copy response
5. Paste back to Code

Now it's one line:
```python
c.send('browser', 'command', {'text': 'Research topic'})
```

Took a week of debugging Chrome's aggressive caching, claude.ai's CSP, and response detection timing. But it works!

GitHub: https://github.com/yakub268/claude-multi-agent-bridge

Happy to answer questions!
```

---

## Email Signature / Social Bio

```
Creator of Claude Multi-Agent Bridge - enabling AI instances to communicate
→ github.com/yakub268/claude-multi-agent-bridge
```

---

## Next Steps

**Today:**
- [ ] Post Twitter thread
- [ ] Post to r/ClaudeAI
- [ ] Post in Anthropic Discord #show-and-tell
- [ ] Send to Anthropic team (community@anthropic.com)

**This Week:**
- [ ] Post to r/MachineLearning
- [ ] Post to r/Programming
- [ ] Submit to Hacker News (Tuesday/Wednesday 8-10am PT)
- [ ] Create demo video (Loom, 2-3 minutes)
- [ ] Add GIF to README

**Next Week:**
- [ ] Product Hunt launch (prepare screenshots, logo)
- [ ] Dev.to blog post
- [ ] Medium article
- [ ] Submit to Claude MCP Registry

**Track:**
- GitHub stars
- Reddit upvotes/comments
- Twitter engagement
- Issue reports (features/bugs)

**Respond to ALL comments/questions within 2 hours for first 48 hours!**
