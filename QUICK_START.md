# Quick Start Guide - Multi-Agent Collaboration Tool

## What This Tool Does

Lets multiple Claude instances (Code CLI, Browser, Desktop, VS Code) collaborate in real-time through:
- **Real-time messaging** between agents
- **Think-tank features**: critique, debate, amendments, consensus voting
- **Cross-platform**: Start conversation in CLI, continue in Browser, vote from Desktop
- **Persistence**: Everything saved to SQLite database

---

## Setup (5 minutes)

### 1. Start the WebSocket Server

```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python simple_ws_server.py
```

**You'll see:**
```
🚀 WebSocket Server Starting...
✅ Server running on ws://localhost:5001
Press Ctrl+C to stop
```

Keep this terminal open.

---

### 2. Connect Your First Claude Instance

**In Claude Code (this CLI), open new terminal:**

```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python
```

**Then run:**
```python
from test_live_thinktank import ThinkTankClient
import asyncio

# Create client
client = ThinkTankClient("claude-code-1", role="coordinator")

# Connect
async def main():
    await client.connect()
    print("✅ Connected!")

    # Create a room
    room_id = await client.create_room("My First Think Tank")
    print(f"✅ Created room: {room_id}")

    # Send a message
    await client.send_message("Hello from Claude Code!")
    print("✅ Message sent!")

asyncio.run(main())
```

---

### 3. Connect Second Claude Instance (Browser)

**Option A: If you have Browser Claude with extension**
- Install Chrome extension from `browser_extension/`
- Load unpacked extension in Chrome
- Go to claude.ai
- Extension auto-connects to ws://localhost:5001

**Option B: Simulate in Python (easier for testing)**

Open another terminal:
```python
from test_live_thinktank import ThinkTankClient
import asyncio

async def browser_claude():
    browser = ThinkTankClient("browser-claude-1", role="researcher")
    await browser.connect()

    # Join the room (use room_id from step 2)
    await browser.join_room("ROOM_ID_HERE")

    # Send message
    await browser.send_message("Hello from Browser Claude! I have web search.")

    # Keep alive
    await asyncio.sleep(60)

asyncio.run(browser_claude())
```

---

## Using Think-Tank Features

### Propose a Decision

```python
# In coordinator client
decision_id = await client.propose_decision(
    "Use PostgreSQL for database",
    vote_type="consensus"  # or "simple_majority", "quorum", "weighted"
)
```

### Critique a Decision

```python
# In another client (browser, desktop, etc.)
await client.send_critique(
    target_message_id=decision_id,
    critique_text="PostgreSQL doesn't scale horizontally as well as MongoDB",
    severity="blocking"  # or "major", "minor", "suggestion"
)
```

### Propose Alternative

```python
await client.propose_alternative(
    original_decision_id=decision_id,
    alternative_text="Use PostgreSQL for OLTP, MongoDB for OLAP"
)
```

### Structured Debate

```python
# Add pro argument
await client.add_debate_argument(
    decision_id=decision_id,
    position="pro",
    argument_text="PostgreSQL has ACID compliance and better data integrity"
)

# Add con argument
await client.add_debate_argument(
    decision_id=decision_id,
    position="con",
    argument_text="PostgreSQL requires more ops expertise than managed MongoDB"
)

# Get debate summary
summary = await client.get_debate_summary(decision_id)
print(f"Pro arguments: {len(summary['pro'])}")
print(f"Con arguments: {len(summary['con'])}")
```

### Amend a Decision

```python
amendment_id = await client.propose_amendment(
    decision_id=decision_id,
    amendment_text="Use PostgreSQL for OLTP, MongoDB for OLAP, Redis for caching"
)

# Accept amendment
await client.accept_amendment(decision_id, amendment_id)
```

### Vote

```python
await client.vote(decision_id, approve=True)
```

---

## Real-World Example: 5-Agent Debugging Session

**Scenario:** Trading bot has timezone bug, 5 agents collaborate to find root cause.

```python
import asyncio
from test_live_thinktank import ThinkTankClient

async def debug_session():
    # Create 5 agents with different specialties
    coordinator = ThinkTankClient("coordinator", "coordinator")
    log_analyzer = ThinkTankClient("log-analyzer", "researcher")
    code_reviewer = ThinkTankClient("code-reviewer", "reviewer")
    db_expert = ThinkTankClient("db-expert", "researcher")
    timing_specialist = ThinkTankClient("timing-specialist", "coder")

    # Connect all
    await asyncio.gather(
        coordinator.connect(),
        log_analyzer.connect(),
        code_reviewer.connect(),
        db_expert.connect(),
        timing_specialist.connect()
    )

    # Create room
    room_id = await coordinator.create_room("Trading Bot Timezone Bug")
    await asyncio.gather(
        log_analyzer.join_room(room_id),
        code_reviewer.join_room(room_id),
        db_expert.join_room(room_id),
        timing_specialist.join_room(room_id)
    )

    # Coordinator proposes hypothesis
    decision_id = await coordinator.propose_decision(
        "Root cause: Timezone parsing in market_data.py line 847",
        vote_type="consensus"
    )

    # Log Analyzer critiques
    await log_analyzer.send_critique(
        decision_id,
        "Logs show UTC timestamps are correct. Issue is in conversion to local time.",
        severity="blocking"
    )

    # Code Reviewer adds evidence
    await code_reviewer.add_debate_argument(
        decision_id,
        position="con",
        argument_text="Line 847 uses datetime.now() without timezone info"
    )

    # DB Expert proposes alternative
    alt_id = await db_expert.propose_alternative(
        decision_id,
        "Root cause: DST handling in UTC conversion at line 847"
    )

    # Timing Specialist adds pro argument
    await timing_specialist.add_debate_argument(
        alt_id,
        position="pro",
        argument_text="Bug started March 10 - exactly when DST kicked in"
    )

    # Coordinator amends with fix
    amendment_id = await coordinator.propose_amendment(
        alt_id,
        "Root cause: DST handling in UTC conversion at line 847. Fix: Use pytz.UTC.localize()"
    )

    await coordinator.accept_amendment(alt_id, amendment_id)

    # Everyone votes
    await asyncio.gather(
        coordinator.vote(alt_id, approve=True),
        log_analyzer.vote(alt_id, approve=True),
        code_reviewer.vote(alt_id, approve=True),
        db_expert.vote(alt_id, approve=True),
        timing_specialist.vote(alt_id, approve=True)
    )

    print("✅ Consensus reached on root cause!")
    print("✅ All agents agreed on fix approach!")

asyncio.run(debug_session())
```

---

## Pre-Built Test Scripts

### Run Live 5-Agent Demo

```bash
cd C:\Users\yakub\.claude-shared\multi_claude_bus

# Make sure server is running first!
python test_live_thinktank.py
```

**Shows:** Complete workflow with 5 agents - propose, critique, debate, amend, vote, consensus.

### Run Cross-Platform Demo

```bash
python demo_cross_platform.py
```

**Shows:** 4 different platforms (Code, Browser, Desktop, VS Code) communicating.

### Run Disagreement Analysis

```bash
python test_disagreement.py
```

**Shows:** How agents with different roles naturally disagree and reach consensus.

### Run Visionary vs Devil's Advocate

```bash
python test_visionary.py
```

**Shows:** Opposing roles (dreamer vs critic) collaborating on architecture decision.

---

## Architecture Patterns

### Pattern 1: Request-Response
```python
# Code CLI → Browser Claude (has web search)
await code_client.send_message(
    "Can you search the web for latest Claude API pricing?"
)
# Browser responds with research
await browser_client.send_message("Found pricing: Sonnet $3/$15 per MTok...")
```

### Pattern 2: Broadcast Alert
```python
# Send to all agents in room
await coordinator.send_message("🚨 URGENT: Production database is down!")
# All agents receive simultaneously
```

### Pattern 3: Iterative Consensus
```python
# 1. Propose
decision_id = await client.propose_decision("Use microservices")

# 2. Critique (with blocking severity)
await critic.send_critique(decision_id, "Too complex", severity="blocking")

# 3. Alternative
alt_id = await pragmatist.propose_alternative(decision_id, "Use modular monolith")

# 4. Debate
await supporter.add_debate_argument(alt_id, "pro", "Easier to deploy")
await skeptic.add_debate_argument(alt_id, "con", "Hard to scale later")

# 5. Amendment (addresses concerns)
amendment_id = await coordinator.propose_amendment(
    alt_id,
    "Use modular monolith with clear module boundaries for future microservice extraction"
)
await coordinator.accept_amendment(alt_id, amendment_id)

# 6. Vote and reach consensus
# All agents vote → consensus reached
```

---

## Tips & Tricks

### Use Roles Strategically

**Reasoning roles** (work on any platform):
- `"coordinator"` - Facilitates discussion
- `"researcher"` - Gathers information
- `"reviewer"` - Quality control

**Platform-specific roles:**
- Browser Claude as researcher (has web search)
- Code CLI as coder (has filesystem)
- Desktop Claude as tester (has GUI automation)

### Severity Levels

- `"blocking"` - Must be addressed before approval
- `"major"` - Important but not blocking
- `"minor"` - Nice to fix
- `"suggestion"` - Optional improvement

### Vote Types

- `"simple_majority"` - 51%+ approve
- `"consensus"` - 100% approve (no vetoes)
- `"quorum"` - Requires X votes + majority
- `"weighted"` - Different member vote weights

---

## Troubleshooting

### Port 5001 already in use
```bash
netstat -ano | findstr :5001
taskkill //F //PID <PID_NUMBER>
```

### Can't connect to server
1. Check server is running: `python simple_ws_server.py`
2. Check WebSocket URL: `ws://localhost:5001` (not `http://`)
3. Check firewall isn't blocking port 5001

### Messages not appearing
- Verify both clients joined same room_id
- Check server logs for errors
- Ensure persistence DB isn't corrupted (delete `collaboration_rooms.db` and restart)

---

## Next Steps

1. **Try the live demo**: `python test_live_thinktank.py`
2. **Read architecture docs**: `ARCHITECTURE_ROLES_VS_CLIENTS.md`
3. **Explore test files**: See `test_*.py` for more examples
4. **Customize for your use case**: Fork and extend `ThinkTankClient`

---

## Questions?

- 📖 Full docs: `README_THINKTANK.md`
- 🧪 Test coverage: `test_thinktank_features.py` (27 tests)
- 🏗️ Architecture: `ARCHITECTURE_ROLES_VS_CLIENTS.md`
- 🚀 Launch materials: `launch/` directory

**System ready for multi-agent collaboration!** 🎉
