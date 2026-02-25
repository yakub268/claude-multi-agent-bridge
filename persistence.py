#!/usr/bin/env python3
"""
Message Persistence Layer
SQLite backend for message history and replay
"""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


class MessageStore:
    """
    Persistent message storage with SQLite

    Features:
    - Message history with full metadata
    - Fast queries by client, type, timestamp
    - Message replay capability
    - Automatic cleanup of old messages
    - Connection pooling
    """

    def __init__(self, db_path: str = "message_bus.db"):
        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                from_client TEXT NOT NULL,
                to_client TEXT NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                timestamp TEXT NOT NULL,
                requires_ack BOOLEAN DEFAULT 0,
                acked BOOLEAN DEFAULT 0,
                delivered BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,

                INDEX idx_to_client (to_client),
                INDEX idx_from_client (from_client),
                INDEX idx_type (type),
                INDEX idx_timestamp (timestamp),
                INDEX idx_created_at (created_at)
            )
        """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_stats (
                date TEXT PRIMARY KEY,
                total_messages INTEGER DEFAULT 0,
                by_client TEXT,  -- JSON
                by_type TEXT,    -- JSON
                avg_latency REAL,
                errors INTEGER DEFAULT 0
            )
        """
        )

        self.conn.commit()

    def save_message(self, message: Dict) -> bool:
        """Save message to database"""
        try:
            self.conn.execute(
                """
                INSERT INTO messages (
                    id, from_client, to_client, type, payload,
                    priority, timestamp, requires_ack, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message["id"],
                    message["from"],
                    message["to"],
                    message["type"],
                    json.dumps(message["payload"]),
                    message.get("priority", 5),
                    message["timestamp"],
                    message.get("requires_ack", False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            self.conn.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving message: {e}")
            return False

    def get_messages(
        self,
        to_client: Optional[str] = None,
        from_client: Optional[str] = None,
        msg_type: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
        undelivered_only: bool = False,
    ) -> List[Dict]:
        """
        Query messages with filters

        Args:
            to_client: Filter by recipient
            from_client: Filter by sender
            msg_type: Filter by message type
            since: Get messages after this timestamp
            limit: Max results
            undelivered_only: Only get undelivered messages

        Returns:
            List of messages
        """
        query = "SELECT * FROM messages WHERE 1=1"
        params = []

        if to_client:
            query += " AND to_client = ?"
            params.append(to_client)

        if from_client:
            query += " AND from_client = ?"
            params.append(from_client)

        if msg_type:
            query += " AND type = ?"
            params.append(msg_type)

        if since:
            query += " AND timestamp > ?"
            params.append(since)

        if undelivered_only:
            query += " AND delivered = 0"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            messages.append(
                {
                    "id": row["id"],
                    "from": row["from_client"],
                    "to": row["to_client"],
                    "type": row["type"],
                    "payload": json.loads(row["payload"]),
                    "priority": row["priority"],
                    "timestamp": row["timestamp"],
                    "requires_ack": bool(row["requires_ack"]),
                    "acked": bool(row["acked"]),
                    "delivered": bool(row["delivered"]),
                }
            )

        return list(reversed(messages))  # Chronological order

    def mark_delivered(self, message_id: str) -> bool:
        """Mark message as delivered"""
        try:
            self.conn.execute(
                "UPDATE messages SET delivered = 1 WHERE id = ?", (message_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error marking delivered: {e}")
            return False

    def mark_acked(self, message_id: str) -> bool:
        """Mark message as acknowledged"""
        try:
            self.conn.execute(
                "UPDATE messages SET acked = 1 WHERE id = ?", (message_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error marking acked: {e}")
            return False

    def get_conversation(
        self, client1: str, client2: str, limit: int = 50
    ) -> List[Dict]:
        """Get conversation between two clients"""
        cursor = self.conn.execute(
            """
            SELECT * FROM messages
            WHERE (from_client = ? AND to_client = ?)
               OR (from_client = ? AND to_client = ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (client1, client2, client2, client1, limit),
        )

        rows = cursor.fetchall()
        messages = []

        for row in rows:
            messages.append(
                {
                    "id": row["id"],
                    "from": row["from_client"],
                    "to": row["to_client"],
                    "type": row["type"],
                    "payload": json.loads(row["payload"]),
                    "timestamp": row["timestamp"],
                }
            )

        return list(reversed(messages))

    def cleanup_old_messages(self, days: int = 7) -> int:
        """Delete messages older than N days"""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()

        cursor = self.conn.execute(
            "DELETE FROM messages WHERE created_at < ?", (cutoff_iso,)
        )

        self.conn.commit()
        return cursor.rowcount

    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT from_client) as unique_senders,
                COUNT(DISTINCT to_client) as unique_recipients,
                COUNT(CASE WHEN delivered = 1 THEN 1 END) as delivered,
                COUNT(CASE WHEN acked = 1 THEN 1 END) as acked
            FROM messages
        """
        )

        row = cursor.fetchone()

        return {
            "total_messages": row["total"],
            "unique_senders": row["unique_senders"],
            "unique_recipients": row["unique_recipients"],
            "delivered": row["delivered"],
            "acknowledged": row["acked"],
            "delivery_rate": row["delivered"] / row["total"] if row["total"] > 0 else 0,
            "ack_rate": row["acked"] / row["total"] if row["total"] > 0 else 0,
        }

    def search_messages(self, query: str, limit: int = 50) -> List[Dict]:
        """Full-text search in message payloads"""
        cursor = self.conn.execute(
            """
            SELECT * FROM messages
            WHERE payload LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (f"%{query}%", limit),
        )

        rows = cursor.fetchall()
        messages = []

        for row in rows:
            messages.append(
                {
                    "id": row["id"],
                    "from": row["from_client"],
                    "to": row["to_client"],
                    "type": row["type"],
                    "payload": json.loads(row["payload"]),
                    "timestamp": row["timestamp"],
                }
            )

        return messages

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🗄️  Message Persistence Test")
    print("=" * 70)

    # Create store
    store = MessageStore("test_messages.db")

    # Save messages
    messages = [
        {
            "id": "msg-1",
            "from": "code",
            "to": "browser",
            "type": "command",
            "payload": {"text": "What is 2+2?"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "msg-2",
            "from": "browser",
            "to": "code",
            "type": "response",
            "payload": {"response": "4"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]

    print("\n📝 Saving messages...")
    for msg in messages:
        store.save_message(msg)
        print(f"   Saved: {msg['id']}")

    # Query
    print("\n📊 Querying messages to 'browser'...")
    results = store.get_messages(to_client="browser", limit=10)
    print(f"   Found {len(results)} messages")

    # Conversation
    print("\n💬 Getting conversation: code <-> browser")
    conversation = store.get_conversation("code", "browser")
    for msg in conversation:
        print(f"   {msg['from']} → {msg['to']}: {msg['type']}")

    # Stats
    print("\n📈 Database stats:")
    stats = store.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Cleanup
    store.close()
    print("\n✅ Test complete")
