# Multi-Claude Communication Bus

Three-way communication system between Claude Code (CLI), Browser Claude (claude.ai), and Desktop Claude.

## Architecture

```
┌─────────────────┐
│  Claude Code    │ ← HTTP server on :5001
│  (CLI Agent)    │ ← code_client.py
└────────┬────────┘
         │
         ├── HTTP ──────────→ ┌──────────────────┐
         │                    │ Browser Extension│
         │                    │  (Chrome/Edge)   │
         │                    └────────┬─────────┘
         │                             │
         ├── Playwright ──────→ ┌─────┴────────────┐
         │                      │   claude.ai      │
         │                      │  (Browser Chat)  │
         │                      └──────────────────┘
         │
         └── PyAutoGUI ───────→ ┌──────────────────┐
                                │  Desktop Claude  │
                                │   (Native App)   │
                                └──────────────────┘
```

## Components

### 1. Message Bus (`server.py`)
- Flask HTTP server on port 5001
- Message queue (last 100 messages)
- REST API + Server-Sent Events
- CORS enabled for browser extension

**Endpoints:**
- `POST /api/send` - Send message
- `GET /api/messages` - Poll messages
- `GET /api/subscribe` - SSE stream
- `GET /api/status` - Health check

### 2. Code Client (`code_client.py`)
- Python client for Claude Code
- Send/receive messages
- Poll or listen mode
- Message handlers

### 3. Browser Extension (`browser_extension/`)
- Chrome/Edge/Firefox extension
- Content script injected into claude.ai
- Bridges page → extension → bus
- Can read/write chat input, submit messages

### 4. Playwright Bridge (`playwright_bridge.py`)
- Control browser Claude via Playwright MCP
- Inject message bus polling script
- Programmatic prompt submission
- Wait for responses

## Setup

### Step 1: Start Message Bus
```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python server.py
```

Server starts on http://localhost:5001

### Step 2: Install Browser Extension
1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `C:\Users\yakub\.claude-shared\multi_claude_bus\browser_extension`
5. Navigate to https://claude.ai
6. Extension auto-injects bridge script

### Step 3: Use from Claude Code

```python
from code_client import CodeClient

client = CodeClient()

# Send message to browser Claude
client.send(
    to="browser",
    msg_type="command",
    payload={"action": "run_prompt", "text": "What's 2+2?"}
)

# Listen for responses
client.listen(duration=10.0)
```

## Message Format

```json
{
  "id": "msg-1708445678123",
  "timestamp": "2026-02-20T12:34:56Z",
  "from": "code",
  "to": "browser",
  "type": "command",
  "payload": {
    "action": "run_prompt",
    "text": "What's 2+2?"
  }
}
```

**Clients:** `code`, `browser`, `desktop`, `extension`, `all`

**Types:** `command`, `query`, `response`, `broadcast`

## Common Use Cases

### Code → Browser: Run prompt
```python
client.send("browser", "command", {
    "action": "run_prompt",
    "text": "Analyze this code: ..."
})
```

### Browser → Code: Send result
```javascript
// In browser extension content script
window.claudeBridge.send("code", "response", {
    "text": "Analysis complete: ..."
});
```

### Code → Desktop: Control app
```python
# Requires PyAutoGUI MCP (not yet available)
client.send("desktop", "command", {
    "action": "click",
    "x": 100,
    "y": 200
})
```

### Broadcast to all
```python
client.broadcast("status", {
    "message": "Trading bot started"
})
```

## Extension API

Injected into `window.claudeBridge` on claude.ai:

```javascript
// Send message to bus
await window.claudeBridge.send('code', 'response', {text: '...'});

// Get text from input
const text = window.claudeBridge.getInputText();

// Set input text
window.claudeBridge.setInputText('What is 2+2?');

// Submit input
window.claudeBridge.submitInput();

// Get last response
const response = window.claudeBridge.getLastResponse();
```

## Playwright Integration

Use Playwright MCP to control browser:

```python
from playwright_bridge import PlaywrightBridge

bridge = PlaywrightBridge(client)
bridge.send_prompt_to_browser("What's the weather?")
response = bridge.wait_for_response(timeout=30.0)
```

## Desktop Control (PyAutoGUI)

**Status:** PyAutoGUI MCP not currently available in tool list.

When available, can control desktop Claude app:
- Click coordinates
- Type text
- Press keyboard shortcuts
- Take screenshots
- OCR text extraction

## Troubleshooting

**Bus not starting:**
```bash
pip install flask flask-cors
python server.py
```

**Extension not working:**
- Check if injected: Open DevTools → Console → look for `[Claude Bridge]` logs
- Check permissions: Extension needs `https://claude.ai/*` access
- CORS errors: Make sure server.py has `CORS(app)` enabled

**No messages received:**
- Check bus status: `curl http://localhost:5001/api/status`
- Verify polling: Browser DevTools → Network → filter `messages`
- Check client ID: Make sure `to` field matches recipient

## Security Notes

- **Local only**: Server binds to 0.0.0.0 but should only be used on localhost
- **No auth**: Anyone on localhost can send/receive messages
- **CORS enabled**: Browser extension can POST from any origin
- **Message persistence**: Only last 100 messages kept in memory

For production use:
1. Add authentication (API keys)
2. Add message encryption
3. Add rate limiting
4. Use persistent storage (Redis/SQLite)
5. Add message TTL/expiry

## Files

```
multi_claude_bus/
├── server.py                    # Message bus server
├── code_client.py               # Python client for Code
├── playwright_bridge.py         # Playwright automation
├── browser_extension/
│   ├── manifest.json           # Extension config
│   ├── content.js              # Injected script
│   ├── background.js           # Service worker
│   ├── popup.html              # Extension popup
│   ├── popup.js                # Popup logic
│   └── icons/                  # Extension icons (TODO)
└── README.md                   # This file
```

## TODO

- [ ] Add extension icons (16x16, 48x48, 128x128)
- [ ] PyAutoGUI integration when MCP available
- [ ] Message persistence (SQLite)
- [ ] Authentication/API keys
- [ ] Rate limiting
- [ ] WebSocket support (replace polling)
- [ ] Message acknowledgments
- [ ] Retry logic for failed sends
- [ ] Desktop app bridge (native messaging)
- [ ] Multi-device sync
