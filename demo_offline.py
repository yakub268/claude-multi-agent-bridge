#!/usr/bin/env python3
"""
Offline Collaboration Demo
Demonstrates all v1.3.0 features without requiring server
"""
import json
import time
from datetime import datetime, timezone

# Import modules
from collaboration_enhanced import (
    EnhancedCollaborationRoom, RoomMember, VoteType,
    CodeLanguage
)
from ai_summarization import AISummarizer
from message_threading import MessageThreading


def print_banner(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_step(step, text):
    print(f"\n{'[' + str(step) + ']':>6} {text}")
    time.sleep(0.3)


def main():
    print_banner("🤝 CLAUDE MULTI-AGENT BRIDGE v1.3.0 - Offline Demo")
    print("Demonstrating all collaboration features (no server required)")
    time.sleep(1)

    # ========================================================================
    # PHASE 1: Room Creation
    # ========================================================================
    print_banner("PHASE 1: ROOM CREATION & MEMBERSHIP")

    print_step(1, "Creating collaboration room...")
    room = EnhancedCollaborationRoom("room-123", "Build Trading Bot v2.0")
    print(f"   ✅ Room created: {room.room_id}")
    print(f"   Topic: {room.topic}")

    print_step(2, "Adding 5 Claude members...")
    from collaboration_enhanced import MemberRole

    room.join("claude-code", role=MemberRole.COORDINATOR, vote_weight=2.0)
    print("   ✅ claude-code joined as coordinator (2.0x vote weight)")

    room.join("claude-desktop-1", role=MemberRole.CODER)
    print("   ✅ claude-desktop-1 joined as coder")

    room.join("claude-desktop-2", role=MemberRole.REVIEWER, vote_weight=1.5)
    print("   ✅ claude-desktop-2 joined as reviewer (1.5x vote weight)")

    room.join("claude-browser", role=MemberRole.TESTER)
    print("   ✅ claude-browser joined as tester")

    room.join("claude-mobile", role=MemberRole.RESEARCHER)
    print("   ✅ claude-mobile joined as researcher")

    print(f"\n   📊 Room has {len(room.members)} members")

    # ========================================================================
    # PHASE 2: Sub-Channels
    # ========================================================================
    print_banner("PHASE 2: SUB-CHANNELS")

    print_step(3, "Creating focused discussion channels...")
    code_ch = room.create_channel("code", "Development discussion", "claude-code")
    print(f"   ✅ Created channel: code ({code_ch})")

    test_ch = room.create_channel("testing", "QA and testing", "claude-browser")
    print(f"   ✅ Created channel: testing ({test_ch})")

    bugs_ch = room.create_channel("bugs", "Bug tracking", "claude-desktop-2")
    print(f"   ✅ Created channel: bugs ({bugs_ch})")

    print(f"\n   📺 Room has {len(room.channels)} channels")

    print_step(4, "Sending messages to different channels...")
    room.send_message("claude-code", "Let's start with the API design", channel="main")
    room.send_message("claude-desktop-1", "I'll handle the FastAPI endpoints", channel=code_ch)
    room.send_message("claude-browser", "Setting up integration tests", channel=test_ch)
    room.send_message("claude-desktop-2", "Found a race condition", channel=bugs_ch)
    print("   ✅ 4 messages sent across different channels")

    # ========================================================================
    # PHASE 3: Enhanced Voting
    # ========================================================================
    print_banner("PHASE 3: ENHANCED VOTING")

    print_step(5, "Simple Majority Vote: Use FastAPI for backend")
    dec1_id = room.propose_decision(
        "claude-code",
        "Use FastAPI for backend framework",
        vote_type=VoteType.SIMPLE_MAJORITY
    )
    print(f"   ✅ Decision proposed: {dec1_id}")
    print("   Vote type: simple_majority")

    room.vote(dec1_id, "claude-desktop-1", approve=True)
    room.vote(dec1_id, "claude-desktop-2", approve=True)
    room.vote(dec1_id, "claude-browser", approve=True)
    room.vote(dec1_id, "claude-mobile", approve=False)

    dec1 = [d for d in room.decisions if d.id == dec1_id][0]
    print("   ✅ Votes: 3 yes, 1 no")
    print(f"   Result: {'✅ APPROVED' if dec1.approved else '❌ REJECTED'}")

    print_step(6, "Consensus Vote: Delete production database")
    dec2_id = room.propose_decision(
        "claude-code",
        "Delete production database",
        vote_type=VoteType.CONSENSUS
    )
    print(f"   ✅ Decision proposed: {dec2_id}")
    print("   Vote type: consensus (requires 100%)")

    room.vote(dec2_id, "claude-desktop-1", approve=True)
    room.vote(dec2_id, "claude-desktop-2", approve=True)
    room.vote(dec2_id, "claude-browser", approve=False)

    dec2 = [d for d in room.decisions if d.id == dec2_id][0]
    print("   ✅ Votes: 2 yes, 1 no")
    print(f"   Result: {'✅ APPROVED' if dec2.approved else '❌ REJECTED (consensus requires 100%)'}")

    print_step(7, "Veto Power: Deploy to production now")
    dec3_id = room.propose_decision(
        "claude-code",
        "Deploy to production now",
        vote_type=VoteType.SIMPLE_MAJORITY
    )

    room.vote(dec3_id, "claude-desktop-1", approve=True)
    room.vote(dec3_id, "claude-browser", approve=True)
    room.vote(dec3_id, "claude-desktop-2", veto=True)

    dec3 = [d for d in room.decisions if d.id == dec3_id][0]
    print("   ✅ 2 approvals")
    print("   🚫 VETOED by claude-desktop-2")
    print(f"   Result: {'✅ APPROVED' if dec3.approved else '❌ BLOCKED BY VETO'}")

    # ========================================================================
    # PHASE 4: File Sharing
    # ========================================================================
    print_banner("PHASE 4: FILE SHARING")

    print_step(8, "Uploading Python strategy file...")
    test_code = b'def calculate_rsi(prices, period=14):\n    return 50.0\n'

    file_id = room.upload_file(
        "claude-desktop-1",
        "strategy.py",
        test_code,
        "text/x-python",
        channel=code_ch
    )
    print(f"   ✅ File uploaded: strategy.py ({file_id})")
    print(f"   Size: {len(test_code)} bytes")
    print("   Channel: code")
    print("   Available to all room members")

    # ========================================================================
    # PHASE 5: Code Execution
    # ========================================================================
    print_banner("PHASE 5: CODE EXECUTION")

    print_step(9, "Executing Python code collaboratively...")
    code = '''
prices = [100, 102, 101, 103, 105, 104, 106, 108]
print(f"Testing RSI with {len(prices)} prices")
print(f"Latest: ${prices[-1]}")
print(f"Range: ${min(prices)}-${max(prices)}")
'''

    result = room.execute_code(
        "claude-desktop-1",
        code,
        CodeLanguage.PYTHON,
        channel=code_ch
    )
    print("   ✅ Code executed successfully")
    print(f"   Exit code: {result.exit_code}")
    print(f"   Execution time: {result.execution_time_ms:.1f}ms")
    print("   Output:")
    for line in result.output.strip().split('\n'):
        print(f"      {line}")

    # ========================================================================
    # PHASE 6: Message Threading
    # ========================================================================
    print_banner("PHASE 6: MESSAGE THREADING")

    print_step(10, "Building threaded conversation...")
    threading = MessageThreading()

    threading.add_message("msg-1", "claude-code", "Should we add WebSocket support?", "2026-02-22T10:00:00Z")
    threading.add_message("msg-2", "claude-desktop-1", "Yes! Real-time updates", "2026-02-22T10:01:00Z", reply_to="msg-1")
    threading.add_message("msg-3", "claude-desktop-2", "Agreed. Flask-Sock?", "2026-02-22T10:02:00Z", reply_to="msg-2")
    threading.add_message("msg-4", "claude-browser", "Flask-Sock is simpler", "2026-02-22T10:03:00Z", reply_to="msg-3")
    threading.add_message("msg-5", "claude-code", "Backwards compatibility?", "2026-02-22T10:04:00Z", reply_to="msg-1")
    threading.add_message("msg-6", "claude-mobile", "Keep REST alongside WebSocket", "2026-02-22T10:05:00Z", reply_to="msg-5")

    thread = threading.get_thread("msg-1")
    print(threading.visualize_thread(thread.thread_id, max_text_length=35))

    stats = threading.get_thread_stats(thread.thread_id)
    print("\n   📊 Thread Stats:")
    print(f"      Messages: {stats['message_count']}")
    print(f"      Max depth: {stats['max_depth']}")
    print(f"      Participants: {stats['participants']}")

    # ========================================================================
    # PHASE 7: AI Summarization
    # ========================================================================
    print_banner("PHASE 7: AI SUMMARIZATION")

    print_step(11, "Auto-summarizing discussion...")
    summarizer = AISummarizer(auto_summarize_threshold=5)

    messages = threading.get_thread_messages("msg-1")
    message_dicts = [
        {'from_client': m.from_client, 'text': m.text, 'timestamp': m.timestamp}
        for m in messages
    ]

    summary = summarizer.summarize_messages(message_dicts, channel="main", use_ai=False)
    print(summarizer.format_summary(summary, format="text"))

    # ========================================================================
    # PHASE 8: Room Statistics
    # ========================================================================
    print_banner("PHASE 8: COLLABORATION ANALYTICS")

    print_step(12, "Room statistics...")
    room_summary = room.get_summary()

    print("   📊 Room Activity:")
    print(f"      • Members: {room_summary['total_members']}")
    print(f"      • Messages: {room_summary['total_messages']}")
    print(f"      • Channels: {room_summary['channels']}")
    print(f"      • Decisions: {room_summary['total_decisions']}")
    print(f"      • Approved: {room_summary['approved_decisions']}")
    print(f"      • Vetoed: {room_summary['vetoed_decisions']}")
    print(f"      • Files: {room_summary['files_shared']}")
    print(f"      • Code executions: {room_summary['code_executions']}")

    # ========================================================================
    # Summary
    # ========================================================================
    print_banner("✅ DEMO COMPLETE!")

    print("\n🎉 Successfully demonstrated:")
    print("   ✅ Room creation and membership (5 Claudes)")
    print("   ✅ Sub-channels (code, testing, bugs)")
    print("   ✅ Enhanced voting (simple majority, consensus, veto)")
    print("   ✅ Weighted voting (coordinator 2.0x, reviewer 1.5x)")
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

    print("\n🚀 'A room full of Claudes collaborating in real-time!'")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
