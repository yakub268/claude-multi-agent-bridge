#!/usr/bin/env python3
"""
Test: Claudes discussing how to improve the collaboration room
"""
from collaboration_room import CollaborationHub, MemberRole
import time


def main():
    print("="*80)
    print("🧪 TEST: Claudes Brainstorming Collaboration Room Improvements")
    print("="*80)

    # Create hub and room
    hub = CollaborationHub()
    room_id = hub.create_room("How to Improve Collaboration Room")
    room = hub.get_room(room_id)

    print(f"\n📍 Room: {room_id}")
    print(f"💡 Topic: {room.topic}\n")

    # Join with different roles
    print("👥 Participants joining...")
    room.join("claude-code", MemberRole.COORDINATOR)
    room.join("claude-browser", MemberRole.RESEARCHER)
    room.join("claude-desktop-1", MemberRole.CODER)
    room.join("claude-desktop-2", MemberRole.REVIEWER)
    room.join("claude-desktop-3", MemberRole.PARTICIPANT)
    time.sleep(0.3)

    print("\n💬 Discussion starting...\n")
    time.sleep(0.5)

    # Coordinator initiates
    room.send_message(
        "claude-code",
        "Let's brainstorm improvements to our collaboration room. What features would make it even better?"
    )
    time.sleep(0.3)

    # Browser Claude researches
    room.send_message(
        "claude-browser",
        "I'll research collaboration tools. Key features I see: persistent chat history, file sharing, code execution, voting systems, AI summarization."
    )
    time.sleep(0.3)

    # Desktop 1 suggests
    room.send_message(
        "claude-desktop-1",
        "We should add voice channels! Multiple Claudes could communicate via voice synthesis + STT."
    )
    time.sleep(0.3)

    # Desktop 2 builds on idea
    room.send_message(
        "claude-desktop-2",
        "Building on that - what about screen sharing? One Claude could share artifacts/visualizations."
    )
    time.sleep(0.3)

    # Ask question
    q1_id = room.ask_question(
        "claude-desktop-3",
        "Should we add persistence? Right now conversations are lost on restart."
    )
    time.sleep(0.3)

    # Answer with reasoning
    room.answer_question(
        "claude-code",
        q1_id,
        "YES! Add SQLite persistence. Store: messages, decisions, tasks, room state. Enable: history replay, audit trail, resume conversations."
    )
    time.sleep(0.3)

    # Another idea
    room.send_message(
        "claude-browser",
        "Idea: Add sub-rooms or channels. Main room + focused side discussions. Like Discord channels."
    )
    time.sleep(0.3)

    # Technical suggestion
    room.send_message(
        "claude-desktop-1",
        "For real-time: integrate WebSocket push notifications instead of polling. Sub-100ms message delivery."
    )
    time.sleep(0.3)

    # Ask technical question
    q2_id = room.ask_question(
        "claude-desktop-2",
        "How do we handle conflicts? What if two Claudes propose different solutions?"
    )
    time.sleep(0.3)

    # Technical answer
    room.answer_question(
        "claude-code",
        q2_id,
        "Implement voting system. Proposals need majority approval. Also add 'consensus mode' - all must agree for critical decisions."
    )
    time.sleep(0.3)

    # More ideas flowing
    room.send_message(
        "claude-desktop-3",
        "We need better task tracking. Kanban board? With states: todo, in_progress, review, done."
    )
    time.sleep(0.3)

    room.send_message(
        "claude-browser",
        "Add code execution! Sandbox where Claudes can run Python/JS snippets and see results collaboratively."
    )
    time.sleep(0.3)

    room.send_message(
        "claude-desktop-1",
        "Integration with GitHub. Create issues, PRs, review code - all from the collaboration room."
    )
    time.sleep(0.3)

    # Propose decision
    dec1_id = room.propose_decision(
        "claude-code",
        "Priority 1 improvements: (1) SQLite persistence, (2) WebSocket push, (3) Voting system"
    )
    time.sleep(0.3)

    # Vote on decision
    room.approve_decision(dec1_id, "claude-browser")
    room.approve_decision(dec1_id, "claude-desktop-1")
    room.approve_decision(dec1_id, "claude-desktop-2")
    time.sleep(0.3)

    # Second decision
    dec2_id = room.propose_decision(
        "claude-code",
        "Priority 2 improvements: (4) Sub-rooms/channels, (5) Kanban board, (6) Code execution sandbox"
    )
    time.sleep(0.3)

    room.approve_decision(dec2_id, "claude-browser")
    room.approve_decision(dec2_id, "claude-desktop-3")
    time.sleep(0.3)

    # Assign implementation tasks
    room.assign_task("claude-code", "Implement SQLite persistence layer", "claude-desktop-1")
    room.assign_task("claude-code", "Add WebSocket push notifications", "claude-desktop-2")
    room.assign_task("claude-code", "Build voting system UI/logic", "claude-desktop-3")
    time.sleep(0.3)

    # Summary
    room.send_message(
        "claude-code",
        "Excellent brainstorming! We identified 10+ improvements. Top 6 prioritized. Tasks assigned. Let's build!"
    )
    time.sleep(0.5)

    # Display conversation
    print("\n" + "="*80)
    print("📜 FULL CONVERSATION")
    print("="*80)

    for msg in room.get_messages(limit=50):
        timestamp = msg.timestamp.strftime("%H:%M:%S")
        sender = msg.from_client[:18].ljust(18)

        # Color code by type
        if msg.type == "system":
            prefix = "🔔"
        elif msg.type == "question":
            prefix = "❓"
        elif msg.type == "answer":
            prefix = "💡"
        elif msg.type == "decision":
            prefix = "🎯"
        elif msg.type == "task":
            prefix = "📋"
        else:
            prefix = "💬"

        print(f"{prefix} [{timestamp}] {sender} │ {msg.text}")

    # Summary
    print("\n" + "="*80)
    print("📊 SESSION SUMMARY")
    print("="*80)

    summary = room.get_summary()
    print(f"Total Messages: {summary['total_messages']}")
    print(f"Active Members: {summary['active_members']}")
    print(f"Decisions Made: {summary['total_decisions']}")
    print(f"Decisions Approved: {summary['approved_decisions']}")
    print(f"Tasks Created: {summary['total_tasks']}")

    print("\n" + "="*80)
    print("🎯 DECISIONS REACHED")
    print("="*80)

    for i, decision in enumerate(room.decisions, 1):
        status = "✅ APPROVED" if decision['approved'] else "⏳ PENDING"
        approvals = len(decision['approved_by'])
        print(f"\n{i}. {status} ({approvals} votes)")
        print(f"   {decision['text']}")
        print(f"   Proposed by: {decision['proposed_by']}")

    print("\n" + "="*80)
    print("📋 TASKS ASSIGNED")
    print("="*80)

    for i, task in enumerate(room.tasks, 1):
        status = "✅ DONE" if task['completed'] else "🔄 IN PROGRESS"
        print(f"\n{i}. {status}")
        print(f"   {task['text']}")
        print(f"   Assignee: {task['assignee']}")

    print("\n" + "="*80)
    print("💡 KEY IMPROVEMENTS IDENTIFIED")
    print("="*80)

    improvements = [
        "1. SQLite persistence - Store all messages, decisions, tasks",
        "2. WebSocket push notifications - Sub-100ms real-time delivery",
        "3. Voting system with consensus mode - Democratic decision making",
        "4. Sub-rooms/channels - Focused side discussions",
        "5. Kanban board - Better task tracking (todo/in_progress/review/done)",
        "6. Code execution sandbox - Run Python/JS collaboratively",
        "7. Voice channels - Voice synthesis + STT communication",
        "8. Screen sharing - Share artifacts and visualizations",
        "9. File sharing - Exchange documents and code",
        "10. GitHub integration - Create issues/PRs from room",
        "11. AI summarization - Auto-summarize long discussions",
        "12. Message threading - Better conversation organization"
    ]

    for improvement in improvements:
        print(f"   {improvement}")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE - Collaboration room successfully facilitated")
    print("   brainstorming among 5 Claudes with different roles!")
    print("="*80)


if __name__ == '__main__':
    main()
