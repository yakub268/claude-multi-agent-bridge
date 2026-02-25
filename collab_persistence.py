#!/usr/bin/env python3
"""
Collaboration Room Persistence
SQLite storage for rooms, messages, decisions, tasks, files

Enables:
- Room state persistence across server restarts
- Message history retrieval
- Decision and vote tracking
- Task management persistence
- File metadata storage
"""
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict


class CollabPersistence:
    """
    Persistence layer for collaboration rooms

    Features:
    - SQLite database storage
    - Room state persistence
    - Message history
    - Decision tracking
    - Task management
    - File metadata
    - Analytics queries
    """

    def __init__(self, db_path: str = "collaboration_rooms.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)

        # Rooms table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        # Create index for rooms
        conn.execute("CREATE INDEX IF NOT EXISTS idx_active ON rooms(active)")

        # Members table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                room_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                role TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                contributions INTEGER DEFAULT 0,
                vote_weight REAL DEFAULT 1.0,

                PRIMARY KEY (room_id, client_id),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                from_client TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT DEFAULT 'message',
                channel TEXT DEFAULT 'main',
                reply_to TEXT,

                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Create indexes for messages
        conn.execute("CREATE INDEX IF NOT EXISTS idx_room_time ON messages(room_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_channel ON messages(room_id, channel)")

        # Decisions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                text TEXT NOT NULL,
                proposed_by TEXT NOT NULL,
                proposed_at TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                required_votes INTEGER,
                approved INTEGER DEFAULT 0,
                vetoed INTEGER DEFAULT 0,

                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Votes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                decision_id TEXT NOT NULL,
                voter TEXT NOT NULL,
                approve INTEGER DEFAULT 1,
                veto INTEGER DEFAULT 0,
                voted_at TEXT NOT NULL,

                PRIMARY KEY (decision_id, voter),
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        """)

        # Tasks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                text TEXT NOT NULL,
                assignee TEXT,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,

                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Files table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                size INTEGER NOT NULL,
                content_type TEXT,
                channel TEXT DEFAULT 'main',
                content BLOB NOT NULL,

                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Code executions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS code_executions (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                executed_by TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                language TEXT NOT NULL,
                code TEXT NOT NULL,
                output TEXT,
                error TEXT,
                exit_code INTEGER DEFAULT 0,
                execution_time_ms REAL,

                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Channels table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                topic TEXT,
                created_at TEXT NOT NULL,

                PRIMARY KEY (room_id, channel_id),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        conn.commit()
        conn.close()

    # ========================================================================
    # Room Operations
    # ========================================================================

    def save_room(self, room_id: str, topic: str, created_at: datetime):
        """Save or update room"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO rooms (room_id, topic, created_at, active)
            VALUES (?, ?, ?, 1)
        """, (room_id, topic, created_at.isoformat()))
        conn.commit()
        conn.close()

    def get_room(self, room_id: str) -> Optional[Dict]:
        """Get room by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM rooms WHERE room_id = ?",
            (room_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_rooms(self, active_only: bool = True) -> List[Dict]:
        """List all rooms"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM rooms"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_at DESC"

        cursor = conn.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # Member Operations
    # ========================================================================

    def save_member(self, room_id: str, client_id: str, role: str,
                   joined_at: datetime, vote_weight: float = 1.0):
        """Save or update member"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO members
            (room_id, client_id, role, joined_at, active, vote_weight)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (room_id, client_id, role, joined_at.isoformat(), vote_weight))
        conn.commit()
        conn.close()

    def get_members(self, room_id: str, active_only: bool = True) -> List[Dict]:
        """Get room members"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM members WHERE room_id = ?"
        params = [room_id]

        if active_only:
            query += " AND active = 1"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # Message Operations
    # ========================================================================

    def save_message(self, message_id: str, room_id: str, from_client: str,
                    text: str, timestamp: datetime, msg_type: str = "message",
                    channel: str = "main", reply_to: Optional[str] = None):
        """Save message"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO messages
            (id, room_id, from_client, text, timestamp, type, channel, reply_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, room_id, from_client, text, timestamp.isoformat(),
              msg_type, channel, reply_to))
        conn.commit()
        conn.close()

    def get_messages(self, room_id: str, channel: Optional[str] = None,
                    since: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get room messages"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM messages WHERE room_id = ?"
        params = [room_id]

        if channel:
            query += " AND channel = ?"
            params.append(channel)

        if since:
            query += " AND timestamp > ?"
            params.append(since)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        messages = [dict(row) for row in rows]
        messages.reverse()  # Chronological order
        return messages

    # ========================================================================
    # Decision & Vote Operations
    # ========================================================================

    def save_decision(self, decision_id: str, room_id: str, text: str,
                     proposed_by: str, proposed_at: datetime,
                     vote_type: str, required_votes: int):
        """Save decision"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO decisions
            (id, room_id, text, proposed_by, proposed_at, vote_type, required_votes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (decision_id, room_id, text, proposed_by, proposed_at.isoformat(),
              vote_type, required_votes))
        conn.commit()
        conn.close()

    def save_vote(self, decision_id: str, voter: str, approve: bool = True,
                 veto: bool = False):
        """Save vote"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO votes
            (decision_id, voter, approve, veto, voted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (decision_id, voter, 1 if approve else 0, 1 if veto else 0,
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    def update_decision_status(self, decision_id: str, approved: bool = False,
                              vetoed: bool = False):
        """Update decision approval/veto status"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE decisions
            SET approved = ?, vetoed = ?
            WHERE id = ?
        """, (1 if approved else 0, 1 if vetoed else 0, decision_id))
        conn.commit()
        conn.close()

    def update_decision_text(self, decision_id: str, new_text: str):
        """Update decision text (for amendments)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE decisions
            SET text = ?
            WHERE id = ?
        """, (new_text, decision_id))
        conn.commit()
        conn.close()

    # ========================================================================
    # File Operations
    # ========================================================================

    def save_file(self, file_id: str, room_id: str, name: str,
                 uploaded_by: str, uploaded_at: datetime, size: int,
                 content_type: str, content: bytes, channel: str = "main"):
        """Save file"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO files
            (id, room_id, name, uploaded_by, uploaded_at, size, content_type, channel, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_id, room_id, name, uploaded_by, uploaded_at.isoformat(),
              size, content_type, channel, content))
        conn.commit()
        conn.close()

    def get_file(self, file_id: str) -> Optional[Dict]:
        """Get file by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    # ========================================================================
    # Analytics
    # ========================================================================

    def get_room_stats(self, room_id: str) -> Dict:
        """Get room statistics"""
        conn = sqlite3.connect(self.db_path)

        stats = {}

        # Member count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM members WHERE room_id = ? AND active = 1",
            (room_id,)
        )
        stats['active_members'] = cursor.fetchone()[0]

        # Message count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE room_id = ?",
            (room_id,)
        )
        stats['total_messages'] = cursor.fetchone()[0]

        # Decision count
        cursor = conn.execute(
            "SELECT COUNT(*), SUM(approved), SUM(vetoed) FROM decisions WHERE room_id = ?",
            (room_id,)
        )
        row = cursor.fetchone()
        stats['total_decisions'] = row[0] or 0
        stats['approved_decisions'] = row[1] or 0
        stats['vetoed_decisions'] = row[2] or 0

        # Task count
        cursor = conn.execute(
            "SELECT COUNT(*), SUM(completed) FROM tasks WHERE room_id = ?",
            (room_id,)
        )
        row = cursor.fetchone()
        stats['total_tasks'] = row[0] or 0
        stats['completed_tasks'] = row[1] or 0

        # File count
        cursor = conn.execute(
            "SELECT COUNT(*), SUM(size) FROM files WHERE room_id = ?",
            (room_id,)
        )
        row = cursor.fetchone()
        stats['files_shared'] = row[0] or 0
        stats['total_file_size'] = row[1] or 0

        # Code execution count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM code_executions WHERE room_id = ?",
            (room_id,)
        )
        stats['code_executions'] = cursor.fetchone()[0]

        # Channel count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE room_id = ?",
            (room_id,)
        )
        stats['channels'] = cursor.fetchone()[0]

        conn.close()
        return stats


if __name__ == '__main__':
    print("=" * 80)
    print("💾 Collaboration Room Persistence - Test")
    print("=" * 80)

    db = CollabPersistence("test_collab.db")

    # Save room
    room_id = "test-room-123"
    db.save_room(room_id, "Test Room", datetime.now(timezone.utc))
    print("\n✅ Room saved")

    # Save members
    db.save_member(room_id, "claude-code", "coordinator",
                   datetime.now(timezone.utc), vote_weight=2.0)
    db.save_member(room_id, "claude-desktop-1", "coder",
                   datetime.now(timezone.utc))
    print("✅ Members saved")

    # Save messages
    db.save_message("msg-1", room_id, "claude-code", "Hello room!",
                   datetime.now(timezone.utc))
    db.save_message("msg-2", room_id, "claude-desktop-1", "Hi there!",
                   datetime.now(timezone.utc), reply_to="msg-1")
    print("✅ Messages saved")

    # Get stats
    stats = db.get_room_stats(room_id)
    print("\n📊 Room Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Persistence test complete!")
