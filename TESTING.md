# Testing Guide

## Quick Start Testing

### 1. Basic Functionality Test (2 minutes)

```bash
# Terminal 1: Start enhanced server
python server_v2.py

# Terminal 2: Run hello world
python examples/hello_world.py
```

**Expected**: Message sent, response received within 5 seconds

---

## Comprehensive Test Suite

### 2. Stress Test (10 minutes)

Tests 100+ interactions across 6 test categories:

```bash
python stress_test.py
```

**What it tests:**
- Sequential messaging (10 messages)
- Rapid fire (20 messages, no delay)
- Concurrent (10 parallel threads)
- Large payloads
- Edge cases (empty, special chars, unicode)
- Message filtering

**Success criteria:**
- ✅ 95%+ success rate = Excellent
- ⚠️ 85-95% = Good (some issues)
- ⚠️ 70-85% = Fair (significant issues)
- ❌ <70% = Poor (major issues)

**Output:**
- Console summary
- Report saved to `stress_test_YYYYMMDD_HHMMSS.txt`

---

### 3. Desktop Client Test (5 minutes)

**Prerequisites:**
- Claude Desktop app installed and running
- `pip install pyautogui pytesseract pygetwindow`
- Tesseract OCR installed (https://github.com/tesseract-ocr/tesseract)

```bash
# Test 1: Window detection
python desktop_client.py --test

# Test 2: Send single message
python desktop_client.py --send "What is 2+2?"

# Test 3: Daemon mode (continuous)
python desktop_client.py --daemon
```

**Known limitations:**
- OCR accuracy ~80-90% (depends on screen resolution, font)
- Window detection may fail if Claude Desktop title changes
- Response extraction is heuristic-based

---

### 4. Server v2 Features Test

**Test logging:**
```bash
# Start server_v2
python server_v2.py

# Check log file
tail -f message_bus.log  # or: type message_bus.log on Windows
```

**Test persistence:**
```bash
# Send messages
python examples/hello_world.py

# Stop server (Ctrl+C)

# Restart server
python server_v2.py

# Check status - should show database stats
curl http://localhost:5001/api/status
```

**Test metrics:**
```bash
curl http://localhost:5001/api/status | python -m json.tool
```

**Expected output:**
```json
{
  "status": "running",
  "uptime_seconds": 123,
  "queue": {
    "current": 5,
    "max": 500
  },
  "metrics": {
    "total_messages": 10,
    "by_client": {
      "code": 5,
      "browser": 5
    },
    "errors": 0,
    "messages_per_minute": 4.88
  },
  "database": {
    "total": 10,
    "by_client": {
      "code": 5,
      "browser": 5
    }
  }
}
```

**Test error handling:**
```bash
# Empty payload
curl -X POST http://localhost:5001/api/send \
  -H "Content-Type: application/json" \
  -d '{}'

# Invalid JSON
curl -X POST http://localhost:5001/api/send \
  -H "Content-Type: application/json" \
  -d 'invalid'

# Missing fields
curl -X POST http://localhost:5001/api/send \
  -H "Content-Type: application/json" \
  -d '{"from": "test"}'
```

**Expected**: All return proper error responses (400/500), logged in message_bus.log

---

## Performance Benchmarks

### Target Metrics

| Metric | Target | Excellent | Poor |
|--------|--------|-----------|------|
| Latency (avg) | <5s | <3s | >10s |
| Success rate | >95% | >98% | <85% |
| Throughput | 10 msg/min | 20 msg/min | <5 msg/min |
| Concurrent | 10 threads | 20 threads | <5 threads |

### Measuring Performance

```python
# Quick benchmark
from code_client import CodeClient
import time

c = CodeClient()
start = time.time()

for i in range(10):
    c.send('browser', 'command', {'text': f'Test {i}'})

elapsed = time.time() - start
print(f"10 messages in {elapsed:.2f}s = {10/elapsed:.2f} msg/s")
```

---

## Edge Cases to Test

### 1. Message Ordering
```python
# Send 5 messages rapidly
for i in range(5):
    c.send('browser', 'command', {'text': f'Message {i}'})

# Verify responses arrive in order
```

### 2. Large Payloads
```python
# 1KB payload
large_text = "A" * 1000
c.send('browser', 'command', {'text': large_text})

# 10KB payload (may hit limits)
huge_text = "A" * 10000
c.send('browser', 'command', {'text': huge_text})
```

### 3. Special Characters
```python
c.send('browser', 'command', {
    'text': 'Test: <script>alert("xss")</script> & "quotes" \\backslash'
})
```

### 4. Unicode
```python
c.send('browser', 'command', {
    'text': 'Test: 你好 🤖 привет مرحبا'
})
```

### 5. Timeout Handling
```python
# Send to non-existent recipient
c.send('nonexistent', 'command', {'text': 'test'})

# Should timeout gracefully
```

---

## Debugging Failed Tests

### Issue: High timeout rate (>10%)

**Possible causes:**
- Browser extension not loaded
- Claude.ai tab not active/visible
- Extension cached old version
- Browser rate limiting

**Solutions:**
1. Check browser console for extension logs
2. Reload extension (chrome://extensions)
3. Open fresh claude.ai tab
4. Reduce message send rate

---

### Issue: Response extraction fails

**Possible causes:**
- Wrong DOM selectors (claude.ai changed)
- MutationObserver not firing
- Response arrives before observer attached

**Solutions:**
1. Inspect claude.ai DOM structure
2. Update selectors in content_final.js
3. Increase wait time before polling

---

### Issue: Desktop client can't find window

**Possible causes:**
- Claude Desktop not running
- Window title changed
- pygetwindow not compatible with OS

**Solutions:**
1. Verify Desktop app is running
2. Check window title matches
3. Try alternative window finding method

---

### Issue: Server crashes under load

**Possible causes:**
- Memory leak (queue too large)
- Database locking
- Thread deadlock

**Solutions:**
1. Check message_bus.log for errors
2. Reduce MAX_QUEUE_SIZE
3. Disable persistence (set PERSIST_ENABLED=False)
4. Restart server

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Multi-Agent Bridge

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Start message bus
      run: |
        python server_v2.py &
        sleep 5

    - name: Run unit tests
      run: |
        python -m pytest tests/

    - name: Check server status
      run: |
        curl http://localhost:5001/api/status
```

---

## Test Coverage Goals

- ✅ Message send/receive: 100%
- ✅ Error handling: 90%+
- ✅ Edge cases: 80%+
- ⚠️ Desktop client: 60%+ (platform-specific)
- ⚠️ Browser extension: Manual testing only

---

## Reporting Bugs

When filing bug reports, include:

1. **Test output** (from stress_test.py)
2. **Server logs** (message_bus.log)
3. **Browser console** (if extension-related)
4. **Environment**:
   - OS version
   - Python version
   - Browser version
   - Claude Desktop version (if applicable)

---

## Next Steps

After passing all tests:

1. ✅ Run stress test and achieve >95% success rate
2. ✅ Test Desktop client (if using)
3. ✅ Verify persistence works across server restarts
4. ✅ Check logs for errors/warnings
5. ✅ Review metrics in /api/status
6. 🚀 Ready for production use / launch
