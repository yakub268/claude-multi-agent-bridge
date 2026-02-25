#!/usr/bin/env python3
"""
Multi-Agent Trading Bot Diagnostic Orchestrator
Uses Claude Multi-Agent Bridge to coordinate 5 specialized agents

Agents:
1. Manual Trade Analyzer - Reconstructs 6 winning manual trades
2. Bot Signal Inspector - Pulls bot signals at same timestamps
3. Execution Tracer - Reviews logs for timing/slippage issues
4. Position Sizing Auditor - Compares manual vs bot position sizing
5. Shadow P&L Synthesizer - Analyzes filtered/blocked signals

Orchestrator - Coordinates agents, identifies divergence points
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List

BASE_URL = "http://localhost:5001/api"
TRADING_BOT_PATH = "C:\\Users\\yakub\\Desktop\\trading_bot"

# Agent channels
AGENTS = {
    "orchestrator": "diagnostic_orchestrator",
    "manual_analyzer": "agent_manual_trades",
    "bot_inspector": "agent_bot_signals",
    "execution_tracer": "agent_execution_logs",
    "sizing_auditor": "agent_position_sizing",
    "shadow_synthesizer": "agent_shadow_pnl"
}

class BridgeClient:
    """Simple client for Claude Multi-Agent Bridge"""

    def __init__(self, channel: str):
        self.channel = channel

    def send(self, content: str, to_channel: str = None) -> bool:
        """Send message to bridge"""
        try:
            payload = {
                "channel": to_channel or self.channel,
                "sender": self.channel,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(f"{BASE_URL}/send", json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Send failed: {e}")
            return False

    def poll(self, since: str = None) -> List[Dict]:
        """Poll messages for this channel"""
        try:
            params = {"channel": self.channel}
            if since:
                params["since"] = since
            response = requests.get(f"{BASE_URL}/messages", params=params, timeout=5)
            if response.status_code == 200:
                return response.json().get("messages", [])
            return []
        except Exception as e:
            print(f"❌ Poll failed: {e}")
            return []

def create_task_assignments() -> Dict[str, str]:
    """Define tasks for each agent"""
    return {
        "manual_analyzer": """
**TASK: Manual Trade Reconstruction**

You are analyzing the 6 winning manual trades from the trading bot.

**Your mission:**
1. Find records of the 6 manual trades that went 6-for-6 (+$407)
2. For each trade, extract:
   - Entry timestamp
   - Symbol/ticker
   - Entry price
   - Position size
   - Exit price
   - Reasoning (if logged)
   - P&L
3. Identify what signals/indicators led to manual entry

**Data sources:**
- `{TRADING_BOT_PATH}\\data\\live\\event_trading.db` (SQLite)
- `{TRADING_BOT_PATH}\\logs\\` (application logs)
- Manual trade records in DB or logs

**Output format:**
```json
{{
  "manual_trades": [
    {{
      "timestamp": "2026-XX-XX HH:MM:SS",
      "ticker": "KXHIGH...",
      "entry_price": 0.XX,
      "size": X,
      "exit_price": 0.XX,
      "pnl": X.XX,
      "reasoning": "...",
      "signals_present": ["..."]
    }}
  ]
}}
```

Send results to `diagnostic_orchestrator` channel when complete.
""",

        "bot_inspector": """
**TASK: Bot Signal Analysis**

You will receive manual trade timestamps from the orchestrator.

**Your mission:**
1. For each manual trade timestamp, find what signals the bots generated
2. Compare bot signals to manual entry decisions
3. Identify if bots:
   - Generated same signal (but filtered out)
   - Generated opposite signal
   - Generated no signal
   - Generated signal at different time

**Data sources:**
- `{TRADING_BOT_PATH}\\data\\fleet\\fleet_trades.db` (fleet signals table)
- `{TRADING_BOT_PATH}\\data\\live\\event_trading.db` (event trading signals)
- `{TRADING_BOT_PATH}\\logs\\` (bot execution logs)

**Output format:**
```json
{{
  "signal_comparison": [
    {{
      "manual_timestamp": "...",
      "manual_ticker": "...",
      "bot_signals": [
        {{
          "bot_name": "...",
          "signal_timestamp": "...",
          "action": "buy/sell/none",
          "confidence": 0.XX,
          "executed": true/false,
          "block_reason": "..."
        }}
      ],
      "divergence": "same_signal_filtered | opposite | no_signal | timing_mismatch"
    }}
  ]
}}
```

Wait for manual trade data from orchestrator, then analyze.
""",

        "execution_tracer": """
**TASK: Execution Log Analysis**

You will receive trade timestamps from the orchestrator.

**Your mission:**
1. For each bot trade, trace the execution path:
   - Signal generation time
   - Risk check time
   - Order submission time
   - Fill time
   - Fill price vs intended price
2. Calculate slippage and delays
3. Identify execution bottlenecks

**Data sources:**
- `{TRADING_BOT_PATH}\\logs\\trading_bot.log` (main log)
- `{TRADING_BOT_PATH}\\logs\\master_orchestrator.log` (orchestrator)
- DB trade records with timestamps

**Output format:**
```json
{{
  "execution_analysis": [
    {{
      "trade_id": "...",
      "signal_time": "...",
      "risk_check_time": "...",
      "order_submit_time": "...",
      "fill_time": "...",
      "total_latency_seconds": X.XX,
      "intended_price": 0.XX,
      "fill_price": 0.XX,
      "slippage_percent": X.XX,
      "bottleneck": "signal_generation | risk_check | order_routing | market_fill"
    }}
  ]
}}
```

Wait for trade list from orchestrator.
""",

        "sizing_auditor": """
**TASK: Position Sizing Comparison**

You will receive manual vs bot trade data from orchestrator.

**Your mission:**
1. Compare position sizes:
   - Manual trade: how much was risked?
   - Bot trade (same opportunity): how much would bot risk?
2. Check Kelly criterion calculations
3. Identify if sizing is:
   - Too small (leaving money on table)
   - Too large (excessive risk)
   - Asymmetric (small winners, big losers)

**Data sources:**
- Manual trade data (from orchestrator)
- Bot configuration files (`{TRADING_BOT_PATH}\\config\\*.py`)
- Risk management logs

**Output format:**
```json
{{
  "sizing_comparison": [
    {{
      "opportunity": "...",
      "manual_size": X.XX,
      "manual_kelly": 0.XX,
      "bot_size": X.XX,
      "bot_kelly": 0.XX,
      "size_ratio": X.XX,
      "assessment": "optimal | too_small | too_large",
      "recommendation": "..."
    }}
  ],
  "asymmetry_check": {{
    "avg_winner_size": X.XX,
    "avg_loser_size": X.XX,
    "win_loss_ratio": X.XX,
    "verdict": "..."
  }}
}}
```

Wait for trade data from orchestrator.
""",

        "shadow_synthesizer": """
**TASK: Shadow P&L Analysis**

Analyze the shadow P&L data from the Fleet system.

**Your mission:**
1. Query `{TRADING_BOT_PATH}\\data\\fleet\\fleet_trades.db` fleet_signals table
2. For signals with outcome='filtered' or outcome='risk_blocked':
   - Check if shadow_pnl exists
   - Calculate total money left on table
   - Group by block_reason to find which filters are costly
3. Identify systematic filtering errors

**Data sources:**
- `{TRADING_BOT_PATH}\\data\\fleet\\fleet_trades.db` (fleet_signals table)
- Shadow tracker logs

**SQL example:**
```sql
SELECT
  block_reason,
  COUNT(*) as blocked_count,
  AVG(shadow_pnl) as avg_pnl,
  SUM(shadow_pnl) as total_pnl
FROM fleet_signals
WHERE outcome IN ('filtered', 'risk_blocked')
  AND shadow_pnl IS NOT NULL
GROUP BY block_reason
ORDER BY total_pnl DESC;
```

**Output format:**
```json
{{
  "shadow_analysis": [
    {{
      "block_reason": "...",
      "count": X,
      "avg_shadow_pnl": X.XX,
      "total_opportunity_cost": X.XX,
      "verdict": "filter_is_helping | filter_is_hurting"
    }}
  ],
  "total_missed_profit": X.XX,
  "costliest_filter": "...",
  "recommendations": ["..."]
}}
```

Start analysis immediately (no dependencies).
""",
    }

def run_orchestrator():
    """Main orchestrator loop"""
    orchestrator = BridgeClient(AGENTS["orchestrator"])

    print("🎯 CLAUDE MULTI-AGENT BOT DIAGNOSTIC")
    print("=" * 60)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌉 Bridge: {BASE_URL}")
    print(f"📁 Trading Bot: {TRADING_BOT_PATH}")
    print("=" * 60)

    # Step 1: Assign tasks to all agents
    tasks = create_task_assignments()
    print("\n📋 PHASE 1: Assigning Tasks")
    print("-" * 60)

    for agent_key, task in tasks.items():
        channel = AGENTS[agent_key]
        print(f"📨 Sending task to {agent_key} ({channel})...")
        orchestrator.send(task, to_channel=channel)
        time.sleep(0.5)

    print("\n✅ All tasks assigned!")
    print("\n" + "=" * 60)
    print("📊 PHASE 2: Coordination Instructions")
    print("=" * 60)
    print("""
🎭 MANUAL SETUP REQUIRED:

1. Open 5 NEW Claude Code windows (or Browser/Desktop instances)

2. In EACH Claude instance, run this code to join the diagnostic:

   ```python
   import requests, json, time

   # Pick ONE agent role per window:
   AGENT = "agent_manual_trades"  # or agent_bot_signals, agent_execution_logs, etc

   def poll_tasks():
       r = requests.get(f"http://localhost:5001/api/messages?channel={AGENT}")
       if r.status_code == 200:
           msgs = r.json().get("messages", [])
           if msgs:
               print(f"📬 Task received:\\n{msgs[0]['content']}")
               return msgs[0]['content']
       return None

   def send_result(result):
       requests.post("http://localhost:5001/api/send", json={
           "channel": "diagnostic_orchestrator",
           "sender": AGENT,
           "content": result
       })

   # 1. Poll for your task
   task = poll_tasks()

   # 2. Do the analysis (read files, query DB, etc)

   # 3. Send results back
   send_result(json.dumps(your_results))
   ```

3. Each agent will:
   - Poll for their task (already sent above)
   - Perform analysis (read files, query DBs)
   - Send results to orchestrator channel

4. THIS orchestrator will:
   - Collect all 5 agent results
   - Synthesize findings
   - Identify root cause divergence

🚀 READY TO COORDINATE!

Once agents start reporting, results will appear below...
""")

    # Step 3: Wait for agent responses
    print("\n" + "=" * 60)
    print("⏳ PHASE 3: Collecting Agent Results")
    print("=" * 60)

    results = {}
    timeout = 600  # 10 minutes
    start_time = time.time()
    last_poll = None

    while len(results) < 5 and (time.time() - start_time) < timeout:
        messages = orchestrator.poll(since=last_poll)

        for msg in messages:
            sender = msg.get("sender", "")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            if sender in AGENTS.values() and sender != AGENTS["orchestrator"]:
                agent_name = [k for k, v in AGENTS.items() if v == sender][0]
                if agent_name not in results:
                    print(f"\n✅ {agent_name} completed!")
                    print(f"   📝 {content[:200]}...")
                    results[agent_name] = content
                    last_poll = timestamp

        if len(results) < 5:
            print(f"\r⏳ Waiting for agents... ({len(results)}/5 complete)", end="", flush=True)
            time.sleep(5)

    print(f"\n\n{'='*60}")
    if len(results) == 5:
        print("🎉 All agents reported!")
    else:
        print(f"⚠️  Timeout - only {len(results)}/5 agents completed")
    print(f"{'='*60}")

    # Step 4: Synthesize findings
    print("\n📊 PHASE 4: Synthesis")
    print("-" * 60)

    synthesis_report = {
        "diagnostic_summary": {
            "timestamp": datetime.now().isoformat(),
            "agents_completed": len(results),
            "agent_results": results
        },
        "divergence_analysis": "Orchestrator will analyze agent results to identify root cause",
        "root_cause_hypothesis": [],
        "recommended_fixes": []
    }

    # Save full report
    report_path = f"{TRADING_BOT_PATH}\\diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path.replace("\\", "/"), "w") as f:
        json.dump(synthesis_report, f, indent=2)

    print(f"\n💾 Full report saved: {report_path}")
    print(f"\n📊 Agent completion: {len(results)}/5")
    for agent_name in results.keys():
        print(f"   ✅ {agent_name}")

    print("\n" + "=" * 60)
    print("🎯 NEXT STEP: Human Claude (you) should:")
    print("   1. Read the diagnostic report JSON")
    print("   2. Analyze agent findings for patterns")
    print("   3. Identify root cause divergence")
    print("   4. Propose specific fixes")
    print("=" * 60)

    return synthesis_report

if __name__ == "__main__":
    run_orchestrator()
