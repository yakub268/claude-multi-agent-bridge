# Claude Multi-Agent Bridge

> Real-time communication between Claude instances — **no API key required**

Connect Claude Code (CLI), Browser Claude (claude.ai), and Claude Desktop into a single coordinated system. Use claude.ai's web features — **real-time web search, artifacts, projects** — directly from your Python scripts and Claude Code sessions.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## Why this exists

Every other multi-agent Claude tool requires API keys or paid subscriptions. The API doesn't expose claude.ai's web features: real-time search, artifacts, projects, file uploads, or thinking mode on free tier.

This bridge gives you programmatic access to all of it — free.

```
Claude Code CLI  ←──────────────────────→  Browser Claude (claude.ai)
                         │
                    Flask server
                    SQLite (persistent)
                    SSE push (instant)
                    MCP server (any client)
```

---

## What's new (Phase 1)

- **True SSE push** — messages arrive instantly, no polling. Browser extension reconnects automatically.
- **SQLite persistence** — messages survive server restarts. Full audit trail (append-only event sourcing).
- **FTS5 full-text search** — `GET /api/search?q=your+query` searches all agent history instantly.
- **MCP server** — any MCP-compatible client (Claude Desktop, Cursor, VS Code) can use the bridge with zero code.

---

## Quickstart

### 1. Start the server
```bash
pip install flask flask-cors requests mcp
python server.py
# → http://localhost:5001
```

### 2. Install the Chrome extension
1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select the `browser_extension/` folder
4. Open [claude.ai](https://claude.ai) — the extension connects automatically via SSE

### 3. Use from Python (Claude Code)
```python
from code_client import CodeClient

client = CodeClient()

# Send a task to Browser Claude (uses claude.ai's web search — free)
client.send("browser", "command", {
    "action": "run_prompt",
    "text": "Search the web for the latest news on MCP protocol adoption and summarize in 3 bullets"
})

# Wait for the response
messages = client.wait_for_response(from_client="browser", timeout=60)
print(messages[0]["payload"]["text"])
```

### 4. Use via MCP (Claude Desktop / Cursor / VS Code)

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "claude-bridge": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": { "BRIDGE_URL": "http://localhost:5001" }
    }
  }
}
```

Then in Claude Desktop, you can say:
> "Use bridge_ask to ask Browser Claude to search for recent AI agent frameworks and report back"

---

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/send` | POST | Send a message to any client |
| `/api/subscribe?client=code&since_seq=0` | GET | **SSE push stream** (real-time) |
| `/api/messages?to=code&since=<ts>` | GET | Polling fallback |
| `/api/search?q=<query>&limit=10` | GET | FTS5 full-text search |
| `/api/status` | GET | Health check + subscriber count |
| `/api/clear` | POST | Wipe message history (dev) |

### Send message format
```json
{
  "from": "code",
  "to": "browser",
  "type": "command",
  "payload": {
    "action": "run_prompt",
    "text": "your prompt here"
  }
}
```

### MCP tools
| Tool | Description |
|---|---|
| `bridge_send` | Send fire-and-forget message |
| `bridge_ask` | Send and wait for reply (request/response) |
| `bridge_broadcast` | Send to all connected instances |
| `bridge_messages` | Retrieve recent messages |
| `bridge_search` | Full-text search message history |
| `bridge_status` | Check connected clients |

---

## Architecture

```
┌──────────────────┐     SSE push    ┌─────────────────────────────┐
│  Chrome Extension │◄───────────────│                             │
│  (claude.ai tab)  │─── POST send ──►   Flask server :5001        │
└──────────────────┘                 │   SQLite: bridge_messages.db │
                                     │   FTS5 full-text search      │
┌──────────────────┐     SSE push    │   Append-only event log      │
│  Claude Code CLI  │◄───────────────│                             │
│  code_client.py   │─── POST send ──►                             │
└──────────────────┘                 └─────────────────────────────┘
                                                   ▲
┌──────────────────┐     MCP stdio                 │
│  Claude Desktop   │───────────────── mcp_server.py ┘
│  Cursor / VS Code │
└──────────────────┘
```

---

## Use cases

**Web search without API costs**
```python
client.send("browser", "command", {"action": "run_prompt",
    "text": "Search: latest Claude API pricing changes 2026"})
```

**Parallel research agents**
```python
topics = ["market size", "competitors", "regulations"]
for topic in topics:
    client.send("browser", "command", {"action": "run_prompt",
        "text": f"Research: {topic} in AI agent market"})
```

**CLI orchestrates Browser for artifacts**
```python
client.send("browser", "command", {"action": "run_prompt",
    "text": "Create a React component for a dashboard and return the code"})
```

---

## Contributing

PRs welcome. Key areas:
- Better DOM selectors for claude.ai response extraction
- Desktop client improvements
- Additional MCP tool coverage
- Demo GIF / video

---

## License

MIT — use freely, attribution appreciated.
