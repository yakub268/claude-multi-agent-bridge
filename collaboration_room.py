#!/usr/bin/env python3
"""
Collaboration Room
Multiple Claudes collaborating in real-time with zero effort

Vision: A room full of Claudes talking and working together instantly
"""
import time
import json
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque
from enum import Enum
import uuid


class MemberRole(Enum):
    """Claude member roles"""

    COORDINATOR = "coordinator"  # Leads the discussion
    RESEARCHER = "researcher"  # Finds information
    CODER = "coder"  # Writes code
    REVIEWER = "reviewer"  # Reviews work
    TESTER = "tester"  # Tests solutions
    DOCUMENTER = "documenter"  # Writes docs
    PARTICIPANT = "participant"  # General participant


@dataclass
class RoomMember:
    """Member of collaboration room"""

    client_id: str
    role: MemberRole = MemberRole.PARTICIPANT
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    contributions: int = 0


@dataclass
class RoomMessage:
    """Message in collaboration room"""

    id: str
    from_client: str
    text: str
    timestamp: datetime
    mentions: Set[str] = field(default_factory=set)
    reply_to: Optional[str] = None
    type: str = "message"  # message, question, answer, idea, decision


class CollaborationRoom:
    """
    Real-time collaboration room for multiple Claudes

    Features:
    - Instant broadcast to all members
    - Role-based participation
    - Threaded conversations
    - @mentions
    - Shared context (all see same messages)
    - Auto-join (zero setup)
    - Real-time updates (zero lag)
    - Decision tracking
    - Task assignment
    """

    def __init__(self, room_id: str, topic: str = "General Collaboration"):
        self.room_id = room_id
        self.topic = topic
        self.members: Dict[str, RoomMember] = {}
        self.messages = deque(maxlen=1000)  # Keep last 1000 messages
        self.decisions = []
        self.tasks = []
        self.created_at = datetime.now(timezone.utc)
        self.message_callbacks: List[Callable] = []

    def join(self, client_id: str, role: MemberRole = MemberRole.PARTICIPANT) -> bool:
        """
        Join the collaboration room

        Args:
            client_id: Client identifier
            role: Member role

        Returns:
            True if joined successfully
        """
        if client_id in self.members:
            # Already in room
            return False

        member = RoomMember(client_id=client_id, role=role)
        self.members[client_id] = member

        # Broadcast join announcement
        self._broadcast_system_message(f"🎉 {client_id} ({role.value}) joined the room")

        return True

    def leave(self, client_id: str):
        """Leave the room"""
        if client_id in self.members:
            member = self.members[client_id]
            member.active = False

            self._broadcast_system_message(f"👋 {client_id} left the room")

    def send_message(
        self,
        from_client: str,
        text: str,
        reply_to: Optional[str] = None,
        msg_type: str = "message",
    ) -> RoomMessage:
        """
        Send message to room (broadcasts to all)

        Args:
            from_client: Sender
            text: Message text
            reply_to: Optional message ID to reply to
            msg_type: Message type

        Returns:
            Room message
        """
        if from_client not in self.members:
            raise ValueError(f"Client {from_client} not in room")

        # Extract @mentions
        mentions = self._extract_mentions(text)

        # Create message
        message = RoomMessage(
            id=str(uuid.uuid4()),
            from_client=from_client,
            text=text,
            timestamp=datetime.now(timezone.utc),
            mentions=mentions,
            reply_to=reply_to,
            type=msg_type,
        )

        # Add to history
        self.messages.append(message)

        # Update contribution count
        self.members[from_client].contributions += 1

        # Trigger callbacks (for real-time delivery)
        self._trigger_callbacks(message)

        return message

    def get_messages(
        self,
        since: Optional[datetime] = None,
        from_client: Optional[str] = None,
        limit: int = 100,
    ) -> List[RoomMessage]:
        """
        Get room messages

        Args:
            since: Get messages after this time
            from_client: Filter by sender
            limit: Max messages

        Returns:
            List of messages
        """
        messages = list(self.messages)

        # Filter by time
        if since:
            messages = [m for m in messages if m.timestamp > since]

        # Filter by sender
        if from_client:
            messages = [m for m in messages if m.from_client == from_client]

        # Limit
        return messages[-limit:]

    def get_thread(self, message_id: str) -> List[RoomMessage]:
        """
        Get message thread (original + all replies)

        Args:
            message_id: Original message ID

        Returns:
            List of messages in thread
        """
        thread = []

        # Find original message
        original = None
        for msg in self.messages:
            if msg.id == message_id:
                original = msg
                thread.append(msg)
                break

        if not original:
            return []

        # Find replies
        for msg in self.messages:
            if msg.reply_to == message_id:
                thread.append(msg)

        return thread

    def ask_question(self, from_client: str, question: str) -> str:
        """
        Ask question to room (highlights as question)

        Args:
            from_client: Asker
            question: Question text

        Returns:
            Question message ID
        """
        msg = self.send_message(from_client, f"❓ {question}", msg_type="question")
        return msg.id

    def answer_question(self, from_client: str, question_id: str, answer: str) -> str:
        """
        Answer a question

        Args:
            from_client: Answerer
            question_id: Question message ID
            answer: Answer text

        Returns:
            Answer message ID
        """
        msg = self.send_message(
            from_client, f"💡 {answer}", reply_to=question_id, msg_type="answer"
        )
        return msg.id

    def propose_decision(self, from_client: str, decision: str) -> str:
        """
        Propose a decision for the room

        Args:
            from_client: Proposer
            decision: Decision text

        Returns:
            Decision message ID
        """
        msg = self.send_message(
            from_client, f"🎯 DECISION: {decision}", msg_type="decision"
        )

        self.decisions.append(
            {
                "id": msg.id,
                "text": decision,
                "proposed_by": from_client,
                "proposed_at": msg.timestamp,
                "approved_by": set(),
                "approved": False,
            }
        )

        return msg.id

    def approve_decision(self, decision_id: str, approver: str):
        """Approve a decision"""
        for decision in self.decisions:
            if decision["id"] == decision_id:
                decision["approved_by"].add(approver)

                # Check if majority approved (>50% of active members)
                active_count = sum(1 for m in self.members.values() if m.active)
                if len(decision["approved_by"]) > active_count / 2:
                    decision["approved"] = True

                    self._broadcast_system_message(
                        f"✅ Decision approved: {decision['text']}"
                    )

    def assign_task(self, from_client: str, task: str, assignee: str) -> str:
        """
        Assign task to member

        Args:
            from_client: Assigner
            task: Task description
            assignee: Member to assign to

        Returns:
            Task message ID
        """
        msg = self.send_message(from_client, f"📋 @{assignee} {task}", msg_type="task")

        self.tasks.append(
            {
                "id": msg.id,
                "text": task,
                "assignee": assignee,
                "assigned_by": from_client,
                "assigned_at": msg.timestamp,
                "completed": False,
            }
        )

        return msg.id

    def complete_task(self, task_id: str, completer: str):
        """Mark task as completed"""
        for task in self.tasks:
            if task["id"] == task_id and task["assignee"] == completer:
                task["completed"] = True
                task["completed_at"] = datetime.now(timezone.utc)

                self._broadcast_system_message(
                    f"✅ @{completer} completed: {task['text']}"
                )

    def on_message(self, callback: Callable):
        """
        Register callback for new messages (real-time)

        Args:
            callback: Function called with RoomMessage
        """
        self.message_callbacks.append(callback)

    def get_active_members(self) -> List[RoomMember]:
        """Get list of active members"""
        return [m for m in self.members.values() if m.active]

    def get_summary(self) -> Dict:
        """Get room summary"""
        active_members = self.get_active_members()

        return {
            "room_id": self.room_id,
            "topic": self.topic,
            "created_at": self.created_at.isoformat(),
            "total_members": len(self.members),
            "active_members": len(active_members),
            "total_messages": len(self.messages),
            "total_decisions": len(self.decisions),
            "approved_decisions": sum(1 for d in self.decisions if d["approved"]),
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks if t["completed"]),
            "members_by_role": self._get_role_distribution(),
        }

    def _extract_mentions(self, text: str) -> Set[str]:
        """Extract @mentions from text"""
        import re

        mentions = set()
        for match in re.finditer(r"@(\w+)", text):
            mentions.add(match.group(1))
        return mentions

    def _broadcast_system_message(self, text: str):
        """Broadcast system message"""
        message = RoomMessage(
            id=str(uuid.uuid4()),
            from_client="SYSTEM",
            text=text,
            timestamp=datetime.now(timezone.utc),
            type="system",
        )
        self.messages.append(message)
        self._trigger_callbacks(message)

    def _trigger_callbacks(self, message: RoomMessage):
        """Trigger message callbacks for real-time delivery"""
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Callback error: {e}")

    def _get_role_distribution(self) -> Dict:
        """Get member count by role"""
        distribution = {}
        for member in self.members.values():
            role = member.role.value
            distribution[role] = distribution.get(role, 0) + 1
        return distribution


class CollaborationHub:
    """
    Hub managing multiple collaboration rooms

    Features:
    - Create rooms on demand
    - Auto-discover rooms
    - Join any room instantly
    - Cross-room messaging
    - Room persistence
    """

    def __init__(self):
        self.rooms: Dict[str, CollaborationRoom] = {}

    def create_room(self, topic: str) -> str:
        """
        Create collaboration room

        Args:
            topic: Room topic

        Returns:
            Room ID
        """
        room_id = str(uuid.uuid4())[:8]
        room = CollaborationRoom(room_id=room_id, topic=topic)
        self.rooms[room_id] = room
        return room_id

    def get_room(self, room_id: str) -> Optional[CollaborationRoom]:
        """Get room by ID"""
        return self.rooms.get(room_id)

    def list_rooms(self) -> List[Dict]:
        """List all rooms"""
        return [
            {
                "room_id": room.room_id,
                "topic": room.topic,
                "members": len(room.get_active_members()),
                "messages": len(room.messages),
            }
            for room in self.rooms.values()
        ]

    def join_room(
        self, room_id: str, client_id: str, role: MemberRole = MemberRole.PARTICIPANT
    ) -> bool:
        """Join a room"""
        room = self.get_room(room_id)
        if room:
            return room.join(client_id, role)
        return False


# ============================================================================
# Example Usage - Room Full of Claudes Collaborating
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🤝 Collaboration Room - Multiple Claudes Working Together")
    print("=" * 70)

    # Create hub
    hub = CollaborationHub()

    # Create room
    room_id = hub.create_room("Build a Web Scraper")
    room = hub.get_room(room_id)

    print(f"\n📍 Room created: {room_id}")
    print(f"📋 Topic: {room.topic}")

    # Multiple Claudes join
    print("\n👥 Claudes joining...")
    room.join("claude-code", MemberRole.COORDINATOR)
    room.join("claude-browser", MemberRole.RESEARCHER)
    room.join("claude-desktop-1", MemberRole.CODER)
    room.join("claude-desktop-2", MemberRole.REVIEWER)
    room.join("claude-desktop-3", MemberRole.TESTER)

    time.sleep(0.5)

    # Collaboration begins!
    print("\n💬 Collaboration starting...")

    # Coordinator starts
    room.send_message(
        "claude-code",
        "Let's build a web scraper. @claude-browser can you research best practices?",
    )

    time.sleep(0.2)

    # Researcher responds
    room.send_message(
        "claude-browser",
        "✅ Researching now. BeautifulSoup + requests is standard. Selenium for dynamic pages.",
    )

    time.sleep(0.2)

    # Ask question
    q_id = room.ask_question(
        "claude-desktop-1", "Should we use async for multiple pages?"
    )

    time.sleep(0.2)

    # Answer question
    room.answer_question(
        "claude-browser", q_id, "Yes! Use aiohttp + asyncio for 10x faster scraping"
    )

    time.sleep(0.2)

    # Propose decision
    dec_id = room.propose_decision(
        "claude-code", "Use BeautifulSoup + aiohttp for async scraping"
    )

    time.sleep(0.2)

    # Approve decision
    room.approve_decision(dec_id, "claude-browser")
    room.approve_decision(dec_id, "claude-desktop-1")
    room.approve_decision(dec_id, "claude-desktop-2")

    time.sleep(0.2)

    # Assign tasks
    room.assign_task("claude-code", "Write scraper class", "claude-desktop-1")
    room.assign_task("claude-code", "Write tests", "claude-desktop-3")
    room.assign_task("claude-code", "Review code quality", "claude-desktop-2")

    time.sleep(0.2)

    # Complete tasks
    room.send_message("claude-desktop-1", "Done! Scraper class ready for review.")
    room.complete_task(room.tasks[0]["id"], "claude-desktop-1")

    # Show conversation
    print("\n📜 Conversation history:")
    for msg in room.get_messages(limit=20):
        timestamp = msg.timestamp.strftime("%H:%M:%S")
        sender = msg.from_client[:15].ljust(15)
        print(f"  [{timestamp}] {sender} │ {msg.text}")

    # Show summary
    print("\n📊 Room Summary:")
    summary = room.get_summary()
    for key, value in summary.items():
        if not isinstance(value, dict):
            print(f"   {key}: {value}")

    print("\n✅ Collaboration complete - All Claudes worked together instantly!")
