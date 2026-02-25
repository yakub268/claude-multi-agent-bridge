#!/usr/bin/env python3
"""
Diagnostic Agent Client - Run this in separate Claude instances

Each Claude instance picks ONE role and executes the assigned task.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5001/api"

# Pick ONE role (change this in each Claude window):
AVAILABLE_ROLES = {
    "1": "agent_manual_trades",      # Manual Trade Analyzer
    "2": "agent_bot_signals",        # Bot Signal Inspector
    "3": "agent_execution_logs",     # Execution Tracer
    "4": "agent_position_sizing",    # Position Sizing Auditor
    "5": "agent_shadow_pnl"          # Shadow P&L Synthesizer
}

def select_role():
    """Interactive role selection"""
    print("🎭 DIAGNOSTIC AGENT CLIENT")
    print("=" * 60)
    print("Select your agent role:")
    print()
    print("1 - Manual Trade Analyzer")
    print("2 - Bot Signal Inspector")
    print("3 - Execution Tracer")
    print("4 - Position Sizing Auditor")
    print("5 - Shadow P&L Synthesizer")
    print()

    choice = input("Enter role number (1-5): ").strip()
    if choice not in AVAILABLE_ROLES:
        print("❌ Invalid choice")
        sys.exit(1)

    return AVAILABLE_ROLES[choice]

def poll_task(channel):
    """Poll for assigned task"""
    print(f"\n📬 Polling for task on channel: {channel}")
    print("⏳ Waiting for orchestrator...")

    while True:
        try:
            response = requests.get(f"{BASE_URL}/messages", params={"channel": channel}, timeout=5)
            if response.status_code == 200:
                messages = response.json().get("messages", [])
                if messages:
                    task = messages[0]["content"]
                    print("\n" + "=" * 60)
                    print("📋 TASK RECEIVED:")
                    print("=" * 60)
                    print(task)
                    print("=" * 60)
                    return task
        except Exception as e:
            print(f"⚠️  Poll error: {e}")

        time.sleep(3)

def send_result(channel, result):
    """Send analysis result to orchestrator"""
    try:
        payload = {
            "channel": "diagnostic_orchestrator",
            "sender": channel,
            "content": result
        }
        response = requests.post(f"{BASE_URL}/send", json=payload, timeout=5)
        if response.status_code == 200:
            print("\n✅ Results sent to orchestrator!")
            return True
        else:
            print(f"\n❌ Failed to send results: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Send error: {e}")
        return False

def main():
    """Main agent loop"""
    agent_channel = select_role()

    print(f"\n✅ You are: {agent_channel}")
    print(f"🌉 Bridge: {BASE_URL}")
    print()
    print("=" * 60)
    print("🚀 READY TO WORK")
    print("=" * 60)

    # Step 1: Get task
    task = poll_task(agent_channel)

    # Step 2: Pause for human Claude to do the analysis
    print("\n" + "=" * 60)
    print("👤 HUMAN CLAUDE: Perform the analysis described above")
    print("=" * 60)
    print("""
Instructions:
1. Read the task description carefully
2. Use Claude Code tools (Read, Bash, Grep, etc) to gather data
3. Analyze the data according to task requirements
4. Format results as JSON (as specified in task)
5. Come back here and run send_result()

When ready to send results, run:

    result = '''
    {
      "your_key": "your_value",
      ...
    }
    '''

    send_result(AGENT_CHANNEL, result)

""")

    print(f"💡 Your channel: {agent_channel}")
    print("💡 Send results to: diagnostic_orchestrator")
    print()

    # Make channel available for interactive use
    global AGENT_CHANNEL
    AGENT_CHANNEL = agent_channel

    # Drop into interactive mode
    print("📝 Ready for interactive analysis. Use tools to complete your task.")
    print("   Then call: send_result(AGENT_CHANNEL, your_json_result)")

if __name__ == "__main__":
    main()
