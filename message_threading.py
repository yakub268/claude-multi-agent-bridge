#!/usr/bin/env python3
"""
Message Threading System
Organize conversations with reply chains and thread navigation

Features:
- Reply-to references
- Thread visualization
- Thread statistics
- Nested conversation tracking
- Thread export
"""
import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ThreadNode:
    """Single message in a thread"""
    message_id: str
    from_client: str
    text: str
    timestamp: str
    reply_to: Optional[str] = None
    replies: List[str] = None  # Child message IDs

    def __post_init__(self):
        if self.replies is None:
            self.replies = []


@dataclass
class Thread:
    """Complete conversation thread"""
    thread_id: str
    root_message_id: str
    messages: Dict[str, ThreadNode]  # message_id -> ThreadNode
    depth: int
    message_count: int
    participants: Set[str]
    created_at: str
    last_updated: str


class MessageThreading:
    """
    Message threading system

    Features:
    - Build thread trees from messages
    - Navigate threads (parent, children, siblings)
    - Thread statistics and analytics
    - Thread export (JSON, text)
    - Thread visualization (ASCII tree)
    """

    def __init__(self):
        self.threads: Dict[str, Thread] = {}  # thread_id -> Thread
        self.message_to_thread: Dict[str, str] = {}  # message_id -> thread_id

    def add_message(self,
                   message_id: str,
                   from_client: str,
                   text: str,
                   timestamp: str,
                   reply_to: Optional[str] = None):
        """
        Add message to threading system

        Args:
            message_id: Unique message ID
            from_client: Sender client ID
            text: Message text
            timestamp: ISO timestamp
            reply_to: Optional parent message ID

        Returns:
            Thread ID this message belongs to
        """
        node = ThreadNode(
            message_id=message_id,
            from_client=from_client,
            text=text,
            timestamp=timestamp,
            reply_to=reply_to
        )

        if reply_to:
            # This is a reply - add to existing thread
            if reply_to in self.message_to_thread:
                # Parent exists
                thread_id = self.message_to_thread[reply_to]
                thread = self.threads[thread_id]

                # Add to thread
                thread.messages[message_id] = node
                thread.message_count += 1
                thread.participants.add(from_client)
                thread.last_updated = timestamp

                # Update parent's replies list
                if reply_to in thread.messages:
                    thread.messages[reply_to].replies.append(message_id)

                # Track message to thread
                self.message_to_thread[message_id] = thread_id

                # Update depth
                thread.depth = self._calculate_depth(thread)

                logger.debug(f"Added reply {message_id} to thread {thread_id}")
                return thread_id
            else:
                # Parent not found, create new thread
                logger.warning(f"Reply parent {reply_to} not found, creating new thread")
                return self._create_new_thread(node)
        else:
            # No reply_to - this starts a new thread
            return self._create_new_thread(node)

    def _create_new_thread(self, root_node: ThreadNode) -> str:
        """Create new thread with root message"""
        thread_id = f"thread-{root_node.message_id}"

        thread = Thread(
            thread_id=thread_id,
            root_message_id=root_node.message_id,
            messages={root_node.message_id: root_node},
            depth=1,
            message_count=1,
            participants={root_node.from_client},
            created_at=root_node.timestamp,
            last_updated=root_node.timestamp
        )

        self.threads[thread_id] = thread
        self.message_to_thread[root_node.message_id] = thread_id

        logger.debug(f"Created new thread {thread_id}")
        return thread_id

    def _calculate_depth(self, thread: Thread) -> int:
        """Calculate max depth of thread"""
        def get_depth(message_id: str, current_depth: int = 1) -> int:
            node = thread.messages.get(message_id)
            if not node or not node.replies:
                return current_depth

            max_child_depth = current_depth
            for reply_id in node.replies:
                child_depth = get_depth(reply_id, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth

        return get_depth(thread.root_message_id)

    def get_thread(self, message_id: str) -> Optional[Thread]:
        """Get thread containing message"""
        thread_id = self.message_to_thread.get(message_id)
        if thread_id:
            return self.threads.get(thread_id)
        return None

    def get_thread_messages(self, message_id: str) -> List[ThreadNode]:
        """Get all messages in thread, in chronological order"""
        thread = self.get_thread(message_id)
        if not thread:
            return []

        messages = list(thread.messages.values())
        messages.sort(key=lambda m: m.timestamp)
        return messages

    def get_replies(self, message_id: str) -> List[ThreadNode]:
        """Get direct replies to message"""
        thread = self.get_thread(message_id)
        if not thread:
            return []

        node = thread.messages.get(message_id)
        if not node or not node.replies:
            return []

        return [thread.messages[reply_id] for reply_id in node.replies]

    def get_parent(self, message_id: str) -> Optional[ThreadNode]:
        """Get parent message"""
        thread = self.get_thread(message_id)
        if not thread:
            return None

        node = thread.messages.get(message_id)
        if not node or not node.reply_to:
            return None

        return thread.messages.get(node.reply_to)

    def get_thread_chain(self, message_id: str) -> List[ThreadNode]:
        """Get chain from root to this message"""
        thread = self.get_thread(message_id)
        if not thread:
            return []

        chain = []
        current_id = message_id

        # Walk up to root
        while current_id:
            node = thread.messages.get(current_id)
            if not node:
                break

            chain.insert(0, node)
            current_id = node.reply_to

        return chain

    def visualize_thread(self, thread_id: str, max_text_length: int = 60) -> str:
        """
        Generate ASCII tree visualization of thread

        Args:
            thread_id: Thread ID
            max_text_length: Max characters to show per message

        Returns:
            ASCII tree string
        """
        thread = self.threads.get(thread_id)
        if not thread:
            return "Thread not found"

        lines = []
        lines.append(f"Thread: {thread_id}")
        lines.append(f"Messages: {thread.message_count} | Depth: {thread.depth} | Participants: {len(thread.participants)}")
        lines.append("")

        def render_node(message_id: str, prefix: str = "", is_last: bool = True):
            node = thread.messages[message_id]

            # Truncate text
            text = node.text
            if len(text) > max_text_length:
                text = text[:max_text_length - 3] + "..."

            # Format line
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{node.from_client}: {text}"
            lines.append(line)

            # Render children
            if node.replies:
                new_prefix = prefix + ("    " if is_last else "│   ")
                for i, reply_id in enumerate(node.replies):
                    is_last_child = (i == len(node.replies) - 1)
                    render_node(reply_id, new_prefix, is_last_child)

        # Start from root
        render_node(thread.root_message_id, "", True)

        return "\n".join(lines)

    def get_thread_stats(self, thread_id: str) -> Dict:
        """Get thread statistics"""
        thread = self.threads.get(thread_id)
        if not thread:
            return {}

        # Count messages per participant
        participant_counts = defaultdict(int)
        for node in thread.messages.values():
            participant_counts[node.from_client] += 1

        # Calculate avg depth
        depths = []
        for node in thread.messages.values():
            chain = self.get_thread_chain(node.message_id)
            depths.append(len(chain))

        avg_depth = sum(depths) / len(depths) if depths else 0

        # Find most active participant
        most_active = max(participant_counts.items(), key=lambda x: x[1]) if participant_counts else (None, 0)

        return {
            'thread_id': thread_id,
            'message_count': thread.message_count,
            'max_depth': thread.depth,
            'avg_depth': round(avg_depth, 2),
            'participants': len(thread.participants),
            'participant_breakdown': dict(participant_counts),
            'most_active': most_active[0],
            'most_active_count': most_active[1],
            'created_at': thread.created_at,
            'last_updated': thread.last_updated
        }

    def export_thread(self, thread_id: str, filepath: str, format: str = "json"):
        """
        Export thread to file

        Args:
            thread_id: Thread ID
            filepath: Output file path
            format: "json" or "text"
        """
        thread = self.threads.get(thread_id)
        if not thread:
            logger.error(f"Thread {thread_id} not found")
            return

        if format == "json":
            # Export as JSON
            thread_data = {
                'thread_id': thread.thread_id,
                'root_message_id': thread.root_message_id,
                'depth': thread.depth,
                'message_count': thread.message_count,
                'participants': list(thread.participants),
                'created_at': thread.created_at,
                'last_updated': thread.last_updated,
                'messages': [asdict(node) for node in thread.messages.values()]
            }

            with open(filepath, 'w') as f:
                json.dump(thread_data, f, indent=2)

        else:  # text format
            lines = []
            lines.append(f"THREAD: {thread_id}")
            lines.append(f"Created: {thread.created_at}")
            lines.append(f"Last Updated: {thread.last_updated}")
            lines.append(f"Messages: {thread.message_count} | Depth: {thread.depth}")
            lines.append(f"Participants: {', '.join(thread.participants)}")
            lines.append("")
            lines.append("=" * 80)
            lines.append("")

            # Write messages in tree order
            def write_node(message_id: str, indent: int = 0):
                node = thread.messages[message_id]
                prefix = "  " * indent
                lines.append(f"{prefix}[{node.from_client}] {node.text}")
                lines.append(f"{prefix}  └─ {node.timestamp}")
                if node.replies:
                    lines.append("")
                    for reply_id in node.replies:
                        write_node(reply_id, indent + 1)

            write_node(thread.root_message_id)

            with open(filepath, 'w') as f:
                f.write("\n".join(lines))

        logger.info(f"Thread {thread_id} exported to {filepath}")

    def list_all_threads(self) -> List[Dict]:
        """List all threads with basic info"""
        return [
            {
                'thread_id': t.thread_id,
                'message_count': t.message_count,
                'depth': t.depth,
                'participants': len(t.participants),
                'created_at': t.created_at,
                'last_updated': t.last_updated
            }
            for t in self.threads.values()
        ]


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("🧵 Message Threading System - Test")
    print("=" * 80)

    threading = MessageThreading()

    # Create conversation thread
    print("\n📝 Building conversation thread...\n")

    # Root message
    threading.add_message("msg-1", "claude-code", "Should we use FastAPI or Flask?", "2026-02-22T10:00:00Z")

    # First level replies
    threading.add_message("msg-2", "claude-desktop-1", "I vote for FastAPI - better async support", "2026-02-22T10:01:00Z", reply_to="msg-1")
    threading.add_message("msg-3", "claude-desktop-2", "FastAPI +1, also has automatic API docs", "2026-02-22T10:02:00Z", reply_to="msg-1")

    # Second level replies
    threading.add_message("msg-4", "claude-code", "Great points! FastAPI it is.", "2026-02-22T10:03:00Z", reply_to="msg-2")
    threading.add_message("msg-5", "claude-desktop-1", "Should we use SQLAlchemy or raw SQL?", "2026-02-22T10:04:00Z", reply_to="msg-4")

    # Third level reply
    threading.add_message("msg-6", "claude-desktop-2", "SQLAlchemy for sure - easier migrations", "2026-02-22T10:05:00Z", reply_to="msg-5")

    # Another first level reply (creates branch)
    threading.add_message("msg-7", "claude-desktop-3", "What about Pydantic for data validation?", "2026-02-22T10:06:00Z", reply_to="msg-1")
    threading.add_message("msg-8", "claude-code", "Yes! FastAPI uses Pydantic natively", "2026-02-22T10:07:00Z", reply_to="msg-7")

    # Visualize thread
    thread = threading.get_thread("msg-1")
    print(threading.visualize_thread(thread.thread_id))

    # Stats
    print("\n" + "=" * 80)
    stats = threading.get_thread_stats(thread.thread_id)
    print(f"\n📊 Thread Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Export
    threading.export_thread(thread.thread_id, "test_thread.json", format="json")
    threading.export_thread(thread.thread_id, "test_thread.txt", format="text")
    print(f"\n✅ Thread exported to test_thread.json and test_thread.txt")

    # Test navigation
    print(f"\n🧭 Navigation Test:")
    print(f"   Replies to msg-1: {len(threading.get_replies('msg-1'))} messages")
    print(f"   Parent of msg-6: {threading.get_parent('msg-6').message_id}")
    chain = threading.get_thread_chain("msg-6")
    print(f"   Chain to msg-6: {' → '.join([n.message_id for n in chain])}")

    # List all threads
    print(f"\n📋 All Threads:")
    for thread_info in threading.list_all_threads():
        print(f"   {thread_info['thread_id']}: {thread_info['message_count']} messages, depth {thread_info['depth']}")

    print("\n✅ Message Threading test complete!")
