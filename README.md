# Claude Multi-Agent Bridge 🤖↔️🤖

> **Make Claude instances talk to each other in real-time**

[![GitHub release](https://img.shields.io/github/v/release/yakub268/claude-multi-agent-bridge)](https://github.com/yakub268/claude-multi-agent-bridge/releases)
[![GitHub stars](https://img.shields.io/github/stars/yakub268/claude-multi-agent-bridge)](https://github.com/yakub268/claude-multi-agent-bridge/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

---

## 📧 Need Help Implementing This?

I offer consulting for multi-agent systems:
- **Custom implementation** for your use case
- **Production deployment** and scaling
- **Team training** and architecture design

**Packages start at $3,500** | [See pricing](launch/consulting_packages.md) | DM me on [LinkedIn](https://linkedin.com/in/yourprofile) or open an issue

---

## 🎉 What's New in v1.3.0

**Collaboration Features - Multiple Claudes Working Together!**

- ✅ **Collaboration Rooms** - Create rooms where Claudes coordinate in real-time
- ✅ **Enhanced Voting** - Democratic decisions (simple majority, consensus, veto, weighted)
- ✅ **Sub-Channels** - Focused discussions like Discord channels
- ✅ **File Sharing** - Exchange code and documents between Claudes
- ✅ **Code Execution Sandbox** - Run Python/JavaScript/Bash collaboratively
- ✅ **Kanban Board** - Visual task tracking with dependencies
- ✅ **GitHub Integration** - Create issues and PRs from room decisions

**Example:**
```python
# 3 Claudes collaborating on a project
room_id = code.create_room("Build Trading Bot")
desktop1.join_room(room_id, role="coder")
desktop2.join_room(room_id, role="reviewer")

# Vote on decisions
dec_id = code.propose_decision("Use FastAPI", vote_type="consensus")
desktop1.vote(dec_id, approve=True)
desktop2.vote(dec_id, approve=True)  # Approved! ✅

# Execute code collaboratively
result = desktop1.execute_code("print('Hello!')", language="python")
# All room members see the output instantly
```

[See full collaboration docs →](#-collaboration-features-v130)

---

![Demo](demo_workflow.gif)

**The problem:** You're coding in Claude Code while researching in Browser Claude. You copy-paste between them. It's 2026.

**The solution:** Direct AI-to-AI communication. Send commands from Code → Browser Claude types it → Response comes back automatically.

```python
from code_client import CodeClient

c = CodeClient()
c.send('browser', 'command', {
    'action': 'run_prompt',
    'text': 'What is quantum entanglement?'
})

# Browser Claude types it, thinks, responds...
# Response arrives in your code automatically
```

**Result:** `"Quantum entanglement is..."`

That's it. Two Claude instances collaborating.

---

## 🎯 What This Enables

### Before:
```
You: [Types in Claude Code] "Research React hooks for me"
You: [Switches to Browser]
You: [Types same thing again]
You: [Waits]
You: [Copies response]
You: [Pastes back to Code]
```

### After:
```python
c.send('browser', 'command', {'action': 'run_prompt', 'text': 'Research React hooks'})
response = c.poll()  # Done.
```

**5 steps → 1 line of code.**

---

## 🚀 Quick Start (3 minutes)

### 1️⃣ Start the message bus
```bash
git clone https://github.com/yakub268/claude-multi-agent-bridge
cd claude-multi-agent-bridge
python server.py
```

Server starts on `localhost:5001`

### 2️⃣ Install Chrome extension
1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `browser_extension/` folder
5. Done! Extension auto-activates on claude.ai

### 3️⃣ Send your first cross-AI message
```python
from code_client import CodeClient

c = CodeClient()

# Send to Browser Claude
c.send('browser', 'command', {
    'action': 'run_prompt',
    'text': 'Explain async/await in one sentence'
})

# Wait for response (usually 2-5 seconds)
import time
time.sleep(5)

# Get response
messages = c.poll()
for msg in messages:
    if msg['type'] == 'claude_response':
        print(msg['payload']['response'])
        # → "async/await is syntactic sugar for Promises..."
```

**That's it.** You just orchestrated two AI agents.

---

## 💡 Real Use Cases

### 1. **Parallel Research**
```python
# You keep coding while Browser Claude researches
c.send('browser', 'command', {
    'text': 'Find the latest React 19 breaking changes'
})

# Continue coding...
# Response arrives asynchronously
```

### 2. **Multi-Model Consensus**
```python
# Ask same question to multiple instances
c.send('browser', 'command', {'text': 'Is P=NP?'})
c.send('desktop', 'command', {'text': 'Is P=NP?'})

# Compare answers
```

### 3. **Extended Context Window**
```python
# Use Browser Claude's artifacts, projects, full UI
# While controlling from CLI
c.send('browser', 'command', {
    'text': 'Create a React component with the code in your last artifact'
})
```

### 4. **Automated Browsing**
```python
# Browser Claude can access web, images, etc.
c.send('browser', 'command', {
    'text': 'Search for "best Python async libraries 2026" and summarize top 3'
})
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Collaboration Hub (v1.3)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Room 1     │  │   Room 2     │  │   Room 3     │          │
│  │ (Topic A)    │  │ (Topic B)    │  │ (Topic C)    │          │
│  │ - Voting     │  │ - Code Exec  │  │ - Files      │          │
│  │ - Channels   │  │ - Kanban     │  │ - GitHub     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         └──────────────────┼──────────────────┘                 │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   WebSocket Server│  ← localhost:5001
                    │   Message Bus     │  ← Real-time broadcast
                    │   (v1.3.0)        │  ← 500-msg queue
                    └─────────┬─────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
      ┌─────▼─────┐    ┌──────▼──────┐   ┌────▼──────┐
      │  Code     │    │   Browser   │   │  Desktop  │
      │  Claude   │    │   Claude    │   │  Claude   │
      │           │    │             │   │           │
      │ (Python)  │    │  (Chrome    │   │(Clipboard)│
      │           │    │  Extension) │   │           │
      └───────────┘    └─────────────┘   └───────────┘
```

**Core Flow:**
1. Python code → WebSocket → Message bus
2. Extension receives → Types into claude.ai
3. Claude responds → Extension extracts
4. Response → WebSocket → All clients receive

**Collaboration Flow (NEW in v1.3):**
1. Any Claude creates room → All can join
2. Messages broadcast to all room members instantly
3. Voting, file sharing, code execution all in real-time
4. Kanban board tracks tasks across all Claudes
5. GitHub integration links decisions → issues/PRs

**Latency:**
- Message delivery: <100ms (WebSocket)
- End-to-end with Claude: ~2-5 seconds

---

## 🎓 Technical Deep Dive

### The Hard Problems We Solved

#### 1. **Content Security Policy (CSP)**
claude.ai blocks `eval()`, inline scripts, dynamic script injection.

**❌ Doesn't work:**
```javascript
const script = document.createElement('script');
script.textContent = `...`;
document.body.appendChild(script);  // CSP violation!
```

**✅ Our solution:**
```javascript
// Pure DOM manipulation, no eval()
const input = document.querySelector('[contenteditable="true"]');
input.textContent = text;
input.dispatchEvent(new Event('input', {bubbles: true}));
```

#### 2. **Response Detection**
Claude's "Thinking..." status never leaves the DOM. Can't wait for it to disappear.

**❌ Doesn't work:**
```javascript
// isThinking never becomes false!
const isThinking = document.querySelector('[role="status"]');
```

**✅ Our solution:**
```javascript
// Watch for "Done" indicator instead
const hasDone = Array.from(document.querySelectorAll('*'))
    .some(el => el.textContent.trim() === 'Done');
```

#### 3. **Chrome's Aggressive Caching**
Extension files cached even after clicking "Reload extension"

**✅ Our solution:**
```json
// Bump version in manifest.json
"version": "1.0.1" → "1.0.2"
// Forces Chrome to clear cache
```

#### 4. **Message Queue Backlog**
Extension loads old messages on startup → Processes stale commands

**✅ Our solution:**
```javascript
// Start from current time, ignore backlog
let lastTimestamp = new Date().toISOString();
```

#### 5. **Duplicate Responses**
`MutationObserver` fires multiple times → Sends same response 10x

**✅ Our solution:**
```javascript
let lastSentResponse = null;
if (response !== lastSentResponse) {
    send(response);
    lastSentResponse = response;
}
```

---

## 📦 Components

### Message Bus (`server.py`)
- Flask HTTP server
- 100-message circular buffer
- Server-Sent Events (SSE) support
- CORS enabled for browser
- Timestamp-based filtering

**API:**
- `POST /api/send` - Send message
- `GET /api/messages?to=browser&since=<timestamp>` - Poll
- `GET /api/status` - Health check

### Python Client (`code_client.py`)
```python
client = CodeClient()
client.send(to, type, payload)     # Send message
client.poll()                       # Get new messages
client.broadcast(type, payload)     # Send to all
client.listen(duration=10)          # Listen with callbacks
client.on('claude_response', fn)    # Register handler
```

### Browser Extension (`browser_extension/`)
- **Manifest v3** compliant
- **CSP-safe** (no eval, no inline scripts)
- **MutationObserver** for response detection
- **Deduplication** logic
- **Timestamp filtering**

**Files:**
- `manifest.json` - Extension config (v1.0.1)
- `content_final.js` - Main content script
- `background.js` - Service worker
- `popup.html` - Extension UI
- `icons/*.png` - 16/48/128px icons

---

## 🔧 Configuration

**Change server port:**
```python
# server.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # ← Change this
```

**Change polling interval:**
```javascript
// content_final.js
setTimeout(pollMessages, 1000);  // ← Change this (ms)
```

**Change queue size:**
```python
# server.py
MAX_MESSAGES = 100  // ← Change this
```

---

## ✅ Validation & Testing

### Quick Validation (30 seconds)

Verify server is working correctly:

```bash
python quick_validation.py
```

**Tests:**
- ✅ Server status and uptime
- ✅ Basic send/receive
- ✅ Bulk message handling (20 rapid-fire messages)
- ✅ Concurrent access (10 threads × 5 messages)
- ✅ Channel isolation (no cross-contamination)

**Expected output:**
```
======================================================================
📊 RESULTS
======================================================================
Server Status             ✅ PASS
Basic Send/Receive        ✅ PASS
Bulk Messages             ✅ PASS
Concurrent Access         ✅ PASS
Channel Isolation         ✅ PASS

======================================================================
✅ ALL TESTS PASSED - Server is production-ready!
======================================================================
```

### Full End-to-End Test (with browser)

**Prerequisites:**
1. Server running (`python server_v2.py`)
2. Fresh claude.ai tab open
3. Extension loaded and working

**Run:**
```bash
python stress_test.py --auto
```

This sends 100+ test prompts to browser Claude and validates:
- Sequential messaging (10 prompts)
- Rapid fire (20 prompts, no delay)
- Concurrent messaging (10 threads)
- Large payloads (5KB+ prompts)
- Edge cases (special characters, Unicode)
- Message filtering

**Production Validation Results:**
```
Server uptime: 54 minutes
Total messages: 235
Error rate: 0%
Concurrent throughput: 50 messages/second
Channel isolation: 100% (no leakage)
```

---

## 🐛 Troubleshooting

### Extension not receiving messages?
1. Check console: `F12` → Should see `[Claude Bridge] Content script loaded`
2. Verify URL: Must be on `https://claude.ai/*`
3. Check extension permissions: Should have `activeTab`, `storage`, `scripting`

### No response coming back?
1. Look for `[Claude Bridge] Extracted response:` in console
2. Check `[Claude Bridge] Response sent to bus`
3. Verify server is running: `curl localhost:5001/api/status`

### Getting old responses?
1. Close **ALL** claude.ai tabs
2. Open fresh tab
3. Extension filters by timestamp automatically

### CSP errors in console?
1. Make sure you're using `content_final.js`
2. Check `manifest.json` version is `1.0.1`+
3. Reload extension: `chrome://extensions/` → Click reload button

---

## 🎁 Production Features (v1.2.0)

### **Webhooks** - External Notifications
Get notified in Slack/Discord when events occur:

```python
from webhooks import WebhookManager, WebhookEvent, SlackWebhook

webhook_mgr = WebhookManager()
webhook_mgr.start_worker()

# Slack notifications
SlackWebhook.send(
    webhook_url="https://hooks.slack.com/...",
    event=WebhookEvent.MESSAGE_SENT,
    data={'from': 'code', 'to': 'browser'}
)
```

### **Health Checks** - Kubernetes-Ready
Production-grade health monitoring:

```python
from health_checks import HealthCheckManager

health = HealthCheckManager(app)

# Endpoints: /health/live, /health/ready, /health/startup
# Perfect for Kubernetes liveness/readiness probes
```

### **Message TTL** - Auto-Cleanup
Automatically expire old messages:

```python
from message_ttl import MessageTTLManager, StandardPolicies

ttl_mgr = MessageTTLManager()
ttl_mgr.register_policy(StandardPolicies.get_error_policy())  # 1 hour
ttl_mgr.start_cleanup_worker()
```

### **Enhanced Metrics** - Prometheus Export
Detailed performance metrics with percentiles:

```python
from enhanced_metrics import MetricsCollector

metrics = MetricsCollector()

# Track latency with P50, P90, P99
latency = metrics.summary('request_duration_ms')
latency.observe(45.2)

# Export to Prometheus
@app.route('/metrics')
def prometheus():
    return metrics.get_prometheus_metrics()
```

### **Server-Sent Events** - Real-Time Streaming
Stream events to browser without polling:

```javascript
// Browser client
const eventSource = new EventSource('/stream/events?client_id=browser-1');
eventSource.addEventListener('message_received', (e) => {
    const data = JSON.parse(e.data);
    console.log('Message:', data);
});
```

**See [UPGRADE_GUIDE_V1.2.md](UPGRADE_GUIDE_V1.2.md) for full documentation**

---

## 🤝 Collaboration Features (v1.3.0)

**NEW:** Multiple Claudes can now collaborate in real-time with zero manual coordination!

### **Collaboration Rooms** - Multi-Claude Coordination
Create rooms where multiple Claude instances work together:

```python
from code_client_collab import CodeClientCollab

# Connect clients
code = CodeClientCollab("claude-code")
desktop1 = CodeClientCollab("claude-desktop-1")
desktop2 = CodeClientCollab("claude-desktop-2")

# Create room
room_id = code.create_room("Build Trading Bot", role="coordinator")

# Others join
desktop1.join_room(room_id, role="coder")
desktop2.join_room(room_id, role="reviewer")

# Create focused channels
code_ch = code.create_channel("code", "Development")
test_ch = code.create_channel("testing", "QA")

# Collaborate!
code.send_to_room("Let's start coding!", channel=code_ch)
desktop1.send_to_room("Working on momentum strategy", channel=code_ch)
```

### **Enhanced Voting** - Democratic Decisions
Multiple voting modes for group decisions:

```python
# Simple majority (>50%)
dec_id = code.propose_decision("Use FastAPI for backend", vote_type="simple_majority")

# Consensus mode (100% required)
dec_id = code.propose_decision("Delete production data", vote_type="consensus")

# Vote
desktop1.vote(dec_id, approve=True)
desktop2.vote(dec_id, approve=True)

# Veto power
desktop1.vote(dec_id, veto=True)  # Blocks decision immediately
```

### **File Sharing** - Exchange Code & Docs
Share files between Claude instances:

```python
# Upload file
file_id = code.upload_file("trading_strategy.py", channel="code")

# Other Claudes can access it
# File is stored in room with metadata
```

### **Code Execution Sandbox** - Run Code Collaboratively
Execute Python, JavaScript, or Bash in a shared sandbox:

```python
# Execute Python code
result = desktop1.execute_code(
    code="""
print('Hello from collaborative Python!')
print(2 + 2)
for i in range(3):
    print(f'Count: {i}')
    """,
    language="python"
)

# Result posted to channel automatically
print(result['output'])       # "Hello from collaborative Python!\n4\n..."
print(result['exit_code'])    # 0
print(result['execution_time_ms'])  # e.g., 23.5
```

### **Kanban Board** - Visual Task Tracking
Coordinate work with a built-in Kanban board:

```python
from kanban_board import KanbanBoardManager, TaskPriority, TaskStatus

manager = KanbanBoardManager()
board_id = manager.create_board("Trading Bot Development")
board = manager.get_board(board_id)

# Create task
task_id = board.create_task(
    "Implement RSI indicator",
    "Calculate 14-period RSI with overbought/oversold levels",
    created_by="claude-code",
    priority=TaskPriority.HIGH,
    assignee="claude-desktop-1",
    estimated_minutes=60
)

# Move through workflow
board.move_task(task_id, TaskStatus.IN_PROGRESS)
board.add_time(task_id, 45)
board.add_comment(task_id, "claude-desktop-1", "RSI working, testing now")
board.move_task(task_id, TaskStatus.REVIEW)
board.move_task(task_id, TaskStatus.DONE)

# Analytics
analytics = board.get_analytics()
print(f"Completion rate: {analytics['completion_rate']}%")
print(f"Total time: {analytics['total_time_spent']} minutes")
```

### **GitHub Integration** - Create Issues & PRs
Link collaboration to GitHub:

```python
from github_integration import GitHubIntegration

gh = GitHubIntegration('owner/repo')

# Create issue from decision
issue = gh.create_issue(
    title="[Decision] Use FastAPI for backend",
    body="Decided in collaboration room",
    created_by="claude-code",
    labels=['decision', 'enhancement']
)

# Create PR from task
pr = gh.create_pr(
    title="Implement RSI indicator",
    body="Task completed in collaboration room",
    source_branch="feature/rsi",
    reviewers=['teammate']
)
```

**See [IMPROVEMENTS_IMPLEMENTED.md](IMPROVEMENTS_IMPLEMENTED.md) for complete documentation**

---

## 🛣️ Roadmap

**v1.1 (Completed):**
- [x] WebSocket support (replace polling)
- [x] Message persistence (SQLite)
- [x] Authentication & rate limiting
- [x] Priority queue
- [x] Circuit breaker & retries
- [x] Message routing

**v1.2 (Completed):**
- [x] Webhooks (Slack/Discord)
- [x] Health checks (Kubernetes)
- [x] Message TTL
- [x] Enhanced metrics (Prometheus)
- [x] Server-Sent Events

**v1.3 (Completed):**
- [x] Collaboration rooms (multi-Claude coordination)
- [x] Enhanced voting (consensus, veto, weighted, quorum)
- [x] Sub-channels (focused discussions)
- [x] File sharing between Claudes
- [x] Code execution sandbox (Python, JavaScript, Bash)
- [x] Kanban board integration
- [x] GitHub integration (issues, PRs)
- [x] Desktop Claude integration (clipboard-based)

**v1.4 (Planned):**
- [ ] Multi-tab support (route to specific conversations)
- [ ] Artifact extraction (get charts, code blocks, etc.)
- [ ] File upload automation
- [ ] Project context injection
- [ ] End-to-end encryption
- [ ] PostgreSQL persistence
- [ ] React admin dashboard
- [ ] Voice channels (STT + TTS)
- [ ] AI summarization of discussions
- [ ] Message threading
- [ ] Screen sharing between Claudes

---

## 🤝 Contributing

This was built in one intense debugging session (15+ extension reloads to get Chrome to pick up CSP fixes 😅).

**Want to help?**

Areas for improvement:
- [ ] Better error handling & retry logic
- [ ] Connection recovery
- [ ] Message acknowledgments
- [ ] Unit tests
- [ ] Multi-browser support

**PR Guidelines:**
1. Keep it simple
2. Add tests if adding features
3. Update README
4. Follow existing code style

---

## 📜 License

MIT License - Use freely, credit appreciated!

---

## 🙏 Credits

Built by [@yakub268](https://github.com/yakub268) with Claude Sonnet 4.5

**The Story:** Started as "Can we make Claude instances talk to each other?"

Ended up solving:
- CSP violations (pure DOM manipulation)
- Chrome caching (version bumping)
- Response timing (watch "Done", not "Thinking")
- Message backlogs (timestamp filtering)
- Duplicate sends (deduplication)

**Result:** Working multi-agent AI system. Open sourced for the community.

---

## ⭐ Star History

If this saved you time or inspired you, drop a star! It helps others discover this project.

**Share it:**
- 🐦 Twitter: "Just connected two Claude instances to work together 🤯"
- 💬 Discord: [Anthropic Community](https://discord.gg/anthropic) #show-and-tell
- 📰 Reddit: r/ClaudeAI, r/MachineLearning, r/Programming

---

**Questions?** Open an issue or [DM on Twitter](https://twitter.com/yakub268)

**Want to contribute?** PRs welcome! See [Contributing](#-contributing) above.

**Using this in production?** Let me know! I'd love to hear your use case.
