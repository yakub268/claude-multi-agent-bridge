# Quick Start Guide

## 1. Start the Message Bus (✅ Already Running)

```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python server.py
```

Server is running on: **http://localhost:5001**

Status: http://localhost:5001/api/status

## 2. Install Browser Extension

### Chrome/Edge:
1. Open `chrome://extensions/` (or `edge://extensions/`)
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select folder: `C:\Users\yakub\.claude-shared\multi_claude_bus\browser_extension`
5. Extension should appear with "Claude Multi-Agent Bridge" name

### Verify:
- Navigate to https://claude.ai
- Open DevTools (F12) → Console
- Look for: `[Claude Bridge] Content script loaded`
- Look for: `[Claude Bridge] API injected into window.claudeBridge`

## 3. Test Communication

### From Claude Code (this CLI):

```python
from code_client import CodeClient

client = CodeClient()

# Send prompt to browser Claude
client.send("browser", "command", {
    "action": "run_prompt",
    "text": "What's 2+2?"
})

# Listen for responses
client.listen(duration=10.0)
```

### From Browser Console (on claude.ai):

```javascript
// Check if bridge is loaded
console.log(window.claudeBridge);

// Send message to Code
await window.claudeBridge.send('code', 'response', {
    text: 'Hello from browser!'
});

// Control chat input
window.claudeBridge.setInputText('What is Python?');
window.claudeBridge.submitInput();
```

### From Extension Popup:

1. Click extension icon (puzzle piece in toolbar)
2. Click "Claude Multi-Agent Bridge"
3. Click "Send Test Message"
4. Check status and recent messages

## 4. Use Playwright Automation

```python
from playwright_bridge import PlaywrightBridge
from code_client import CodeClient

client = CodeClient()
bridge = PlaywrightBridge(client)

# Send prompt to browser and wait for response
bridge.send_prompt_to_browser("What's the weather in Paris?")
response = bridge.wait_for_response(timeout=30.0)
print(f"Response: {response}")
```

## 5. Run Demo

```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python demo.py
```

## Message Examples

### Command: Run prompt in browser
```json
{
  "from": "code",
  "to": "browser",
  "type": "command",
  "payload": {
    "action": "run_prompt",
    "text": "Analyze this data..."
  }
}
```

### Response: Browser replies
```json
{
  "from": "browser",
  "to": "code",
  "type": "response",
  "payload": {
    "text": "Analysis complete: ..."
  }
}
```

### Broadcast: Status update
```json
{
  "from": "code",
  "to": "all",
  "type": "broadcast",
  "payload": {
    "message": "System started",
    "timestamp": "2026-02-20T12:00:00Z"
  }
}
```

## Troubleshooting

### Extension not loading
- Check manifest.json has no syntax errors
- Reload extension: Extensions page → Reload button
- Check permissions: Must have `https://claude.ai/*`

### No messages received
- Check bus is running: `curl http://localhost:5001/api/status`
- Check browser console for `[Claude Bridge]` logs
- Verify client ID matches `to` field in messages

### CORS errors
- Server should have `CORS(app)` enabled (already done)
- Extension should send `Content-Type: application/json`

### Commands not executing
- Check if on claude.ai page (not login page)
- Verify chat input exists: `document.querySelector('[contenteditable="true"]')`
- Check submit button: `document.querySelector('button[aria-label*="Send"]')`

## API Reference

### Server Endpoints

- `POST /api/send` - Send message
- `GET /api/messages?to=<client>&since=<timestamp>` - Poll messages
- `GET /api/subscribe` - Server-Sent Events stream
- `GET /api/status` - Health check

### Browser Bridge API

Injected into `window.claudeBridge` on claude.ai:

- `send(to, type, payload)` - Send message to bus
- `getInputText()` - Get current input text
- `setInputText(text)` - Set input text
- `submitInput()` - Click submit button
- `getLastResponse()` - Get last assistant message

### Python Client API

```python
client = CodeClient(bus_url="http://localhost:5001")

# Send
client.send(to="browser", msg_type="command", payload={...})
client.broadcast(msg_type="status", payload={...})

# Receive
messages = client.poll()  # One-time poll
client.listen(interval=1.0, duration=10.0)  # Continuous

# Handlers
client.on("response", callback_function)

# Status
status = client.status()
```

## Next Steps

1. ✅ Message bus running
2. ⬜ Install browser extension
3. ⬜ Test browser → code communication
4. ⬜ Try Playwright automation
5. ⬜ Add desktop control (when PyAutoGUI MCP available)

## Use Cases

### Trading Bot Alerts
```python
# From trading bot
client.broadcast("alert", {
    "type": "trade_executed",
    "symbol": "BTC-USD",
    "side": "buy",
    "price": 45000,
    "size": 0.1
})
```

### Research Delegation
```python
# Code sends research task to browser Claude
client.send("browser", "command", {
    "action": "run_prompt",
    "text": "Research the latest React 19 features and summarize in 3 bullet points"
})

# Listen for response
client.listen(duration=60.0)
```

### Multi-Agent Workflows
```python
# Code orchestrates browser + desktop
client.send("browser", "query", {"task": "analyze_code"})
time.sleep(5)
client.send("desktop", "command", {"action": "save_results"})
```
