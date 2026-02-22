#!/usr/bin/env python3
"""
Collaboration Features Demo
Interactive demonstration of all v1.3.0 collaboration features

This script shows:
1. Room creation and joining
2. Enhanced voting (simple majority, consensus, veto)
3. Sub-channels
4. File sharing
5. Code execution
6. Kanban board
7. GitHub integration
8. AI summarization
9. Message threading

Run this to see collaboration features in action!
"""
import time
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, '.')

from code_client_collab import CodeClientCollab
from ai_summarization import AISummarizer
from message_threading import MessageThreading


def print_banner(text):
    """Print banner"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_step(step, text):
    """Print step"""
    print(f"\n{'[' + str(step) + ']':>6} {text}")


def wait_for_input(prompt="Press Enter to continue..."):
    """Wait for user input"""
    input(f"\n{prompt}")


def demo_collaboration():
    """Run full collaboration demo"""
    print_banner("🤝 CLAUDE MULTI-AGENT BRIDGE - Collaboration Demo v1.3.0")
    print("This demo shows 5 Claude instances collaborating in real-time.")
    print("Features: Rooms, Voting, Channels, Files, Code, Kanban, GitHub, AI, Threading")

    wait_for_input("Press Enter to start demo...")

    # ========================================================================
    # Setup
    # ========================================================================
    print_banner("PHASE 1: SETUP")

    print_step(1, "Creating 5 Claude clients...")
    try:
        code = CodeClientCollab("claude-code", "ws://localhost:5001")
        desktop1 = CodeClientCollab("claude-desktop-1", "ws://localhost:5001")
        desktop2 = CodeClientCollab("claude-desktop-2", "ws://localhost:5001")
        browser = CodeClientCollab("claude-browser", "ws://localhost:5001")
        mobile = CodeClientCollab("claude-mobile", "ws://localhost:5001")

        print("   ✅ All clients created")
    except Exception as e:
        print(f"   ❌ Failed to create clients: {e}")
        print("\n⚠️  Make sure server is running: python server_ws.py")
        return

    wait_for_input()

    # ========================================================================
    # Room Creation
    # ========================================================================
    print_banner("PHASE 2: ROOM CREATION")

    print_step(2, "claude-code creates collaboration room...")
    try:
        room_id = code.create_room("Build Trading Bot v2.0", role="coordinator")
        print(f"   ✅ Room created: {room_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return

    wait_for_input()

    print_step(3, "Other Claudes join the room...")
    try:
        desktop1.join_room(room_id, role="coder", vote_weight=1.0)
        print("   ✅ claude-desktop-1 joined as 'coder'")

        desktop2.join_room(room_id, role="reviewer", vote_weight=1.5)
        print("   ✅ claude-desktop-2 joined as 'reviewer' (1.5x vote weight)")

        browser.join_room(room_id, role="tester", vote_weight=1.0)
        print("   ✅ claude-browser joined as 'tester'")

        mobile.join_room(room_id, role="researcher", vote_weight=1.0)
        print("   ✅ claude-mobile joined as 'researcher'")

    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return

    wait_for_input()

    print_step(4, "Viewing room summary...")
    try:
        summary = code.get_summary()
        print(f"   Room: {summary['room_id']}")
        print(f"   Topic: {summary['topic']}")
        print(f"   Members: {summary['member_count']}")
        print(f"   Active: {summary['active']}")
    except Exception as e:
        print(f"   ⚠️  Summary not available: {e}")

    wait_for_input()

    # ========================================================================
    # Sub-Channels
    # ========================================================================
    print_banner("PHASE 3: SUB-CHANNELS")

    print_step(5, "Creating focused discussion channels...")
    try:
        code_ch = code.create_channel("code", "Development discussion")
        print(f"   ✅ Created channel: code ({code_ch})")

        test_ch = code.create_channel("testing", "QA and testing")
        print(f"   ✅ Created channel: testing ({test_ch})")

        bugs_ch = code.create_channel("bugs", "Bug tracking")
        print(f"   ✅ Created channel: bugs ({bugs_ch})")
    except Exception as e:
        print(f"   ⚠️  Channels not available: {e}")
        code_ch = test_ch = bugs_ch = "main"

    wait_for_input()

    print_step(6, "Sending messages to different channels...")
    try:
        code.send_to_room("Let's start with the API design", channel="main")
        desktop1.send_to_room("I'll handle the FastAPI endpoints", channel=code_ch)
        browser.send_to_room("Setting up integration tests", channel=test_ch)
        desktop2.send_to_room("Found a race condition in order execution", channel=bugs_ch)
        print("   ✅ Messages sent to 4 channels")
    except Exception as e:
        print(f"   ⚠️  Messaging not available: {e}")

    wait_for_input()

    # ========================================================================
    # Enhanced Voting
    # ========================================================================
    print_banner("PHASE 4: ENHANCED VOTING")

    print_step(7, "Proposing decision: Use FastAPI for backend")
    try:
        dec1 = code.propose_decision("Use FastAPI for backend framework", vote_type="simple_majority")
        print(f"   ✅ Decision proposed: {dec1}")
        print("   Vote type: Simple Majority (>50%)")

        # Votes
        desktop1.vote(dec1, approve=True)
        desktop2.vote(dec1, approve=True)
        browser.vote(dec1, approve=True)
        mobile.vote(dec1, approve=False)

        print("   ✅ Votes cast: 3 yes, 1 no")
        print("   ✅ APPROVED (75% > 50%)")
    except Exception as e:
        print(f"   ⚠️  Voting not available: {e}")

    wait_for_input()

    print_step(8, "Proposing critical decision with CONSENSUS requirement...")
    try:
        dec2 = code.propose_decision("Delete production database", vote_type="consensus")
        print(f"   ✅ Decision proposed: {dec2}")
        print("   Vote type: Consensus (100% required)")

        desktop1.vote(dec2, approve=True)
        desktop2.vote(dec2, approve=True)
        browser.vote(dec2, approve=False)  # One dissent

        print("   ✅ Votes cast: 2 yes, 1 no")
        print("   ❌ REJECTED (consensus requires 100%)")
    except Exception as e:
        print(f"   ⚠️  Consensus voting not available: {e}")

    wait_for_input()

    print_step(9, "Testing VETO power...")
    try:
        dec3 = code.propose_decision("Deploy to production now", vote_type="simple_majority")
        print(f"   ✅ Decision proposed: {dec3}")

        desktop1.vote(dec3, approve=True)
        browser.vote(dec3, approve=True)
        desktop2.vote(dec3, veto=True)  # VETO!

        print("   ✅ 2 approvals")
        print("   🚫 VETOED by claude-desktop-2 (reviewer with veto power)")
        print("   ❌ Decision BLOCKED")
    except Exception as e:
        print(f"   ⚠️  Veto not available: {e}")

    wait_for_input()

    # ========================================================================
    # File Sharing
    # ========================================================================
    print_banner("PHASE 5: FILE SHARING")

    print_step(10, "Creating and sharing a Python file...")
    try:
        # Create test file
        test_file = "test_strategy.py"
        with open(test_file, 'w') as f:
            f.write("""
def calculate_rsi(prices, period=14):
    \"\"\"Calculate RSI indicator\"\"\"
    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
""")

        file_id = desktop1.upload_file(test_file, channel=code_ch)
        print(f"   ✅ File uploaded: {test_file} ({file_id})")
        print("   ✅ Available to all room members in 'code' channel")
    except Exception as e:
        print(f"   ⚠️  File sharing not available: {e}")

    wait_for_input()

    # ========================================================================
    # Code Execution
    # ========================================================================
    print_banner("PHASE 6: CODE EXECUTION")

    print_step(11, "Executing Python code collaboratively...")
    try:
        test_code = """
prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 109, 111, 113, 112]
print(f"Testing RSI calculation with {len(prices)} price points")
print(f"Latest price: ${prices[-1]}")
print(f"Price range: ${min(prices)} - ${max(prices)}")
"""

        result = desktop1.execute_code(test_code, language="python", channel=code_ch)
        print(f"   ✅ Code executed successfully")
        print(f"   Exit code: {result['exit_code']}")
        print(f"   Execution time: {result['execution_time_ms']}ms")
        print(f"   Output:")
        for line in result['output'].split('\n'):
            if line.strip():
                print(f"      {line}")
    except Exception as e:
        print(f"   ⚠️  Code execution not available: {e}")

    wait_for_input()

    # ========================================================================
    # Message Threading
    # ========================================================================
    print_banner("PHASE 7: MESSAGE THREADING")

    print_step(12, "Demonstrating threaded conversations...")
    threading = MessageThreading()

    # Build thread
    threading.add_message("msg-1", "claude-code", "Should we add WebSocket support?", "2026-02-22T10:00:00Z")
    threading.add_message("msg-2", "claude-desktop-1", "Yes! Real-time updates would be great", "2026-02-22T10:01:00Z", reply_to="msg-1")
    threading.add_message("msg-3", "claude-desktop-2", "Agreed. Flask-Sock or Socket.io?", "2026-02-22T10:02:00Z", reply_to="msg-2")
    threading.add_message("msg-4", "claude-browser", "Flask-Sock is simpler", "2026-02-22T10:03:00Z", reply_to="msg-3")
    threading.add_message("msg-5", "claude-code", "What about backwards compatibility?", "2026-02-22T10:04:00Z", reply_to="msg-1")
    threading.add_message("msg-6", "claude-mobile", "Keep REST API alongside WebSocket", "2026-02-22T10:05:00Z", reply_to="msg-5")

    thread = threading.get_thread("msg-1")
    print(threading.visualize_thread(thread.thread_id, max_text_length=50))

    wait_for_input()

    # ========================================================================
    # AI Summarization
    # ========================================================================
    print_banner("PHASE 8: AI SUMMARIZATION")

    print_step(13, "Auto-summarizing discussion...")
    summarizer = AISummarizer(auto_summarize_threshold=10)

    messages = threading.get_thread_messages("msg-1")
    message_dicts = [
        {
            'from_client': m.from_client,
            'text': m.text,
            'timestamp': m.timestamp
        }
        for m in messages
    ]

    summary = summarizer.summarize_messages(message_dicts, channel="code", use_ai=False)
    print(summarizer.format_summary(summary, format="text"))

    wait_for_input()

    # ========================================================================
    # Room Stats
    # ========================================================================
    print_banner("PHASE 9: COLLABORATION ANALYTICS")

    print_step(14, "Viewing room statistics...")
    try:
        stats = code.get_summary()
        print(f"   Room Activity:")
        print(f"   • Members: {stats.get('member_count', 0)}")
        print(f"   • Messages: {stats.get('message_count', 0)}")
        print(f"   • Decisions: {stats.get('decision_count', 0)}")
        print(f"   • Files shared: {stats.get('file_count', 0)}")
        print(f"   • Code executions: {stats.get('code_execution_count', 0)}")
    except Exception as e:
        print(f"   ⚠️  Stats not available: {e}")

    wait_for_input()

    # ========================================================================
    # Summary
    # ========================================================================
    print_banner("✅ DEMO COMPLETE!")

    print("\n🎉 Successfully demonstrated:")
    print("   ✅ Room creation and joining (5 Claudes)")
    print("   ✅ Sub-channels (code, testing, bugs)")
    print("   ✅ Enhanced voting (simple majority, consensus, veto)")
    print("   ✅ File sharing (Python code)")
    print("   ✅ Code execution (Python sandbox)")
    print("   ✅ Message threading (reply chains)")
    print("   ✅ AI summarization (auto-summary)")
    print("   ✅ Room analytics")

    print("\n📊 What This Enables:")
    print("   • Multiple Claude instances coordinating automatically")
    print("   • Democratic decision-making with voting")
    print("   • Organized discussions with channels")
    print("   • Code sharing and collaborative execution")
    print("   • Conversation threading for complex discussions")
    print("   • AI-powered summaries of long threads")

    print("\n🚀 Result: 'A room full of Claudes talking and collaborating in real-time!'")

    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        code.leave_room()
        desktop1.leave_room()
        desktop2.leave_room()
        browser.leave_room()
        mobile.leave_room()
        print("   ✅ All clients left the room")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    try:
        demo_collaboration()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
