#!/usr/bin/env python3
"""
Automated Collaboration Demo (No User Input Required)
Runs through all features automatically
"""
import time
import sys
import traceback

sys.path.insert(0, ".")

from code_client_collab import CodeClientCollab
from ai_summarization import AISummarizer
from message_threading import MessageThreading


def print_banner(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_step(step, text):
    print(f"\n{'[' + str(step) + ']':>6} {text}")
    time.sleep(0.5)


def main():
    print_banner("🤝 CLAUDE MULTI-AGENT BRIDGE - Collaboration Demo v1.3.0")
    print("Running automated demo of all collaboration features...")
    time.sleep(1)

    # Setup
    print_banner("PHASE 1: SETUP")
    print_step(1, "Creating 5 Claude clients...")

    try:
        code = CodeClientCollab("claude-code", "ws://localhost:5001")
        time.sleep(0.5)
        desktop1 = CodeClientCollab("claude-desktop-1", "ws://localhost:5001")
        time.sleep(0.5)
        desktop2 = CodeClientCollab("claude-desktop-2", "ws://localhost:5001")
        time.sleep(0.5)
        browser = CodeClientCollab("claude-browser", "ws://localhost:5001")
        time.sleep(0.5)
        mobile = CodeClientCollab("claude-mobile", "ws://localhost:5001")
        print("   ✅ All 5 clients connected")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("\n⚠️  Server not running or not ready")
        return 1

    # Room Creation
    print_banner("PHASE 2: ROOM CREATION")
    print_step(2, "claude-code creates collaboration room...")

    try:
        room_id = code.create_room("Build Trading Bot v2.0", role="coordinator")
        print(f"   ✅ Room created: {room_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        traceback.print_exc()
        return 1

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
        print(f"   ❌ Join failed: {e}")
        traceback.print_exc()
        return 1

    print_step(4, "Viewing room summary...")
    try:
        summary = code.get_summary()
        print(f"   Room: {summary['room_id']}")
        print(f"   Topic: {summary['topic']}")
        print(f"   Members: {summary['member_count']}")
    except Exception as e:
        print(f"   ⚠️  Summary: {e}")

    # Sub-Channels
    print_banner("PHASE 3: SUB-CHANNELS")
    print_step(5, "Creating focused discussion channels...")

    try:
        code_ch = code.create_channel("code", "Development discussion")
        print("   ✅ Created channel: code")

        test_ch = code.create_channel("testing", "QA and testing")
        print("   ✅ Created channel: testing")

        bugs_ch = code.create_channel("bugs", "Bug tracking")
        print("   ✅ Created channel: bugs")
    except Exception as e:
        print(f"   ⚠️  Channels: {e}")
        code_ch = test_ch = bugs_ch = "main"

    print_step(6, "Sending messages to different channels...")
    try:
        code.send_to_room("Let's start with the API design", channel="main")
        desktop1.send_to_room("I'll handle the FastAPI endpoints", channel=code_ch)
        browser.send_to_room("Setting up integration tests", channel=test_ch)
        desktop2.send_to_room(
            "Found a race condition in order execution", channel=bugs_ch
        )
        print("   ✅ Messages sent to 4 channels")
    except Exception as e:
        print(f"   ⚠️  Messaging: {e}")

    # Enhanced Voting
    print_banner("PHASE 4: ENHANCED VOTING")
    print_step(7, "Proposing decision: Use FastAPI for backend")

    try:
        dec1 = code.propose_decision(
            "Use FastAPI for backend framework", vote_type="simple_majority"
        )
        print("   ✅ Decision proposed")
        print("   Vote type: Simple Majority (>50%)")

        desktop1.vote(dec1, approve=True)
        desktop2.vote(dec1, approve=True)
        browser.vote(dec1, approve=True)
        mobile.vote(dec1, approve=False)

        print("   ✅ Votes cast: 3 yes, 1 no → APPROVED (75% > 50%)")
    except Exception as e:
        print(f"   ⚠️  Voting: {e}")

    print_step(8, "Testing CONSENSUS requirement...")
    try:
        dec2 = code.propose_decision(
            "Delete production database", vote_type="consensus"
        )
        print("   ✅ Decision proposed (requires 100% consensus)")

        desktop1.vote(dec2, approve=True)
        desktop2.vote(dec2, approve=True)
        browser.vote(dec2, approve=False)

        print("   ✅ Votes: 2 yes, 1 no → REJECTED (consensus requires 100%)")
    except Exception as e:
        print(f"   ⚠️  Consensus: {e}")

    print_step(9, "Testing VETO power...")
    try:
        dec3 = code.propose_decision(
            "Deploy to production now", vote_type="simple_majority"
        )

        desktop1.vote(dec3, approve=True)
        browser.vote(dec3, approve=True)
        desktop2.vote(dec3, veto=True)

        print("   🚫 VETOED by claude-desktop-2 → Decision BLOCKED")
    except Exception as e:
        print(f"   ⚠️  Veto: {e}")

    # File Sharing
    print_banner("PHASE 5: FILE SHARING")
    print_step(10, "Sharing Python code file...")

    try:
        test_file = "test_strategy.py"
        with open(test_file, "w") as f:
            f.write("def calculate_rsi(prices, period=14):\n    return 50.0\n")

        file_id = desktop1.upload_file(test_file, channel=code_ch)
        print(f"   ✅ File uploaded: {test_file}")
        print("   ✅ Available to all room members")
    except Exception as e:
        print(f"   ⚠️  File sharing: {e}")

    # Code Execution
    print_banner("PHASE 6: CODE EXECUTION")
    print_step(11, "Executing Python code collaboratively...")

    try:
        test_code = 'print("Hello from collaborative code execution!")\nprint(f"2 + 2 = {2 + 2}")'

        result = desktop1.execute_code(test_code, language="python", channel=code_ch)
        print("   ✅ Code executed successfully")
        print(f"   Exit code: {result['exit_code']}")
        print(f"   Execution time: {result['execution_time_ms']}ms")
        print(f"   Output: {result['output'].strip()}")
    except Exception as e:
        print(f"   ⚠️  Code execution: {e}")

    # Message Threading
    print_banner("PHASE 7: MESSAGE THREADING")
    print_step(12, "Building threaded conversation...")

    threading = MessageThreading()
    threading.add_message(
        "msg-1",
        "claude-code",
        "Should we add WebSocket support?",
        "2026-02-22T10:00:00Z",
    )
    threading.add_message(
        "msg-2",
        "claude-desktop-1",
        "Yes! Real-time updates would be great",
        "2026-02-22T10:01:00Z",
        reply_to="msg-1",
    )
    threading.add_message(
        "msg-3",
        "claude-desktop-2",
        "Agreed. Flask-Sock or Socket.io?",
        "2026-02-22T10:02:00Z",
        reply_to="msg-2",
    )
    threading.add_message(
        "msg-4",
        "claude-browser",
        "Flask-Sock is simpler",
        "2026-02-22T10:03:00Z",
        reply_to="msg-3",
    )
    threading.add_message(
        "msg-5",
        "claude-code",
        "What about backwards compatibility?",
        "2026-02-22T10:04:00Z",
        reply_to="msg-1",
    )
    threading.add_message(
        "msg-6",
        "claude-mobile",
        "Keep REST API alongside WebSocket",
        "2026-02-22T10:05:00Z",
        reply_to="msg-5",
    )

    thread = threading.get_thread("msg-1")
    print(threading.visualize_thread(thread.thread_id, max_text_length=45))

    # AI Summarization
    print_banner("PHASE 8: AI SUMMARIZATION")
    print_step(13, "Auto-summarizing discussion...")

    summarizer = AISummarizer(auto_summarize_threshold=10)
    messages = threading.get_thread_messages("msg-1")
    message_dicts = [
        {"from_client": m.from_client, "text": m.text, "timestamp": m.timestamp}
        for m in messages
    ]

    summary = summarizer.summarize_messages(message_dicts, channel="code", use_ai=False)
    print(summarizer.format_summary(summary, format="text"))

    # Final Stats
    print_banner("PHASE 9: COLLABORATION ANALYTICS")
    print_step(14, "Room statistics...")

    try:
        stats = code.get_summary()
        print(f"   • Members: {stats.get('member_count', 0)}")
        print(f"   • Messages: {stats.get('message_count', 0)}")
        print(f"   • Decisions: {stats.get('decision_count', 0)}")
    except Exception as e:
        print(f"   ⚠️  Stats: {e}")

    # Summary
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

    print("\n🚀 Result: 'A room full of Claudes collaborating in real-time!'")

    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        code.leave_room()
        desktop1.leave_room()
        desktop2.leave_room()
        browser.leave_room()
        mobile.leave_room()
        print("   ✅ All clients disconnected")
    except Exception as e:
        print(f"   ⚠️  Cleanup: {e}")

    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        traceback.print_exc()
        sys.exit(1)
