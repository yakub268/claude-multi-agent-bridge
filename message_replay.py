#!/usr/bin/env python3
"""
Message Replay & History Viewer
Debug tool for tracking and replaying message flows
"""
import json
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MessageRecord:
    """Complete message record with metadata"""
    id: str
    from_client: str
    to_client: str
    type: str
    payload: Dict
    timestamp: str
    delivered: bool = False
    acked: bool = False
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    replay_count: int = 0


class MessageReplay:
    """
    Message replay and history viewer

    Features:
    - Complete message history
    - Timeline visualization
    - Message flow tracking (request → response)
    - Replay messages (for debugging)
    - Export to various formats
    - Search and filter
    - Performance analysis
    """

    def __init__(self, db_path: str = "message_history.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_history (
                id TEXT PRIMARY KEY,
                from_client TEXT NOT NULL,
                to_client TEXT NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                delivered INTEGER DEFAULT 0,
                acked INTEGER DEFAULT 0,
                latency_ms REAL,
                error TEXT,
                replay_count INTEGER DEFAULT 0,
                recorded_at TEXT NOT NULL,

                INDEX idx_timestamp (timestamp),
                INDEX idx_from_to (from_client, to_client),
                INDEX idx_type (type)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_flows (
                flow_id TEXT PRIMARY KEY,
                request_id TEXT,
                response_id TEXT,
                initiated_at TEXT,
                completed_at TEXT,
                total_latency_ms REAL,

                FOREIGN KEY (request_id) REFERENCES message_history(id),
                FOREIGN KEY (response_id) REFERENCES message_history(id)
            )
        """)

        conn.commit()
        conn.close()

    def record_message(self, message: MessageRecord):
        """
        Record message to history

        Args:
            message: Message to record
        """
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            INSERT OR REPLACE INTO message_history
            (id, from_client, to_client, type, payload, timestamp,
             delivered, acked, latency_ms, error, replay_count, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id,
            message.from_client,
            message.to_client,
            message.type,
            json.dumps(message.payload),
            message.timestamp,
            1 if message.delivered else 0,
            1 if message.acked else 0,
            message.latency_ms,
            message.error,
            message.replay_count,
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()
        conn.close()

    def get_history(self, limit: int = 100,
                   from_client: Optional[str] = None,
                   to_client: Optional[str] = None,
                   msg_type: Optional[str] = None,
                   since: Optional[str] = None) -> List[MessageRecord]:
        """
        Get message history with filters

        Args:
            limit: Max messages
            from_client: Filter by sender
            to_client: Filter by recipient
            msg_type: Filter by type
            since: Get messages after this timestamp

        Returns:
            List of message records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM message_history WHERE 1=1"
        params = []

        if from_client:
            query += " AND from_client = ?"
            params.append(from_client)

        if to_client:
            query += " AND to_client = ?"
            params.append(to_client)

        if msg_type:
            query += " AND type = ?"
            params.append(msg_type)

        if since:
            query += " AND timestamp > ?"
            params.append(since)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            messages.append(MessageRecord(
                id=row['id'],
                from_client=row['from_client'],
                to_client=row['to_client'],
                type=row['type'],
                payload=json.loads(row['payload']),
                timestamp=row['timestamp'],
                delivered=bool(row['delivered']),
                acked=bool(row['acked']),
                latency_ms=row['latency_ms'],
                error=row['error'],
                replay_count=row['replay_count']
            ))

        conn.close()
        return list(reversed(messages))

    def get_conversation(self, client1: str, client2: str, limit: int = 50) -> List[MessageRecord]:
        """Get conversation between two clients"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT * FROM message_history
            WHERE (from_client = ? AND to_client = ?)
               OR (from_client = ? AND to_client = ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """, (client1, client2, client2, client1, limit))

        rows = cursor.fetchall()
        messages = []

        for row in rows:
            messages.append(MessageRecord(
                id=row['id'],
                from_client=row['from_client'],
                to_client=row['to_client'],
                type=row['type'],
                payload=json.loads(row['payload']),
                timestamp=row['timestamp'],
                delivered=bool(row['delivered']),
                acked=bool(row['acked']),
                latency_ms=row['latency_ms'],
                error=row['error'],
                replay_count=row['replay_count']
            ))

        conn.close()
        return list(reversed(messages))

    def replay_message(self, message_id: str, send_func) -> bool:
        """
        Replay a message

        Args:
            message_id: Message ID to replay
            send_func: Function to send message

        Returns:
            True if replayed successfully
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            "SELECT * FROM message_history WHERE id = ?",
            (message_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        # Reconstruct message
        message = {
            'id': f"{row['id']}-replay",
            'from': row['from_client'],
            'to': row['to_client'],
            'type': row['type'],
            'payload': json.loads(row['payload']),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            '_replay': True,
            '_original_id': row['id']
        }

        # Send message
        try:
            send_func(message)

            # Update replay count
            conn.execute(
                "UPDATE message_history SET replay_count = replay_count + 1 WHERE id = ?",
                (message_id,)
            )
            conn.commit()
            conn.close()

            return True

        except Exception as e:
            conn.close()
            print(f"❌ Replay failed: {e}")
            return False

    def export_timeline(self, output_path: str, format: str = 'json'):
        """
        Export message timeline

        Args:
            output_path: Output file path
            format: Export format ('json', 'csv', 'html')
        """
        messages = self.get_history(limit=10000)

        if format == 'json':
            self._export_json(messages, output_path)
        elif format == 'csv':
            self._export_csv(messages, output_path)
        elif format == 'html':
            self._export_html(messages, output_path)

    def _export_json(self, messages: List[MessageRecord], output_path: str):
        """Export to JSON"""
        data = [asdict(msg) for msg in messages]

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _export_csv(self, messages: List[MessageRecord], output_path: str):
        """Export to CSV"""
        import csv

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['ID', 'From', 'To', 'Type', 'Timestamp',
                           'Delivered', 'Acked', 'Latency (ms)', 'Error'])

            # Rows
            for msg in messages:
                writer.writerow([
                    msg.id,
                    msg.from_client,
                    msg.to_client,
                    msg.type,
                    msg.timestamp,
                    msg.delivered,
                    msg.acked,
                    msg.latency_ms,
                    msg.error or ''
                ])

    def _export_html(self, messages: List[MessageRecord], output_path: str):
        """Export to HTML timeline"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Message Timeline</title>
    <style>
        body { font-family: monospace; background: #0f172a; color: #e2e8f0; padding: 20px; }
        .timeline { max-width: 1200px; margin: 0 auto; }
        .message { background: #1e293b; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }
        .header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .route { color: #94a3b8; }
        .timestamp { opacity: 0.6; font-size: 12px; }
        .type { background: #334155; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .latency { color: #10b981; }
        .error { color: #ef4444; }
    </style>
</head>
<body>
    <div class="timeline">
        <h1>📊 Message Timeline</h1>
"""

        for msg in messages:
            html += """
        <div class="message">
            <div class="header">
                <span class="route">{msg.from_client} → {msg.to_client}</span>
                <span class="timestamp">{msg.timestamp}</span>
            </div>
            <span class="type">{msg.type}</span>
"""
            if msg.latency_ms:
                html += f'            <span class="latency">{msg.latency_ms:.1f}ms</span>\n'

            if msg.error:
                html += f'            <span class="error">Error: {msg.error}</span>\n'

            html += "        </div>\n"

        html += """
    </div>
</body>
</html>
"""

        with open(output_path, 'w') as f:
            f.write(html)

    def analyze_performance(self) -> Dict:
        """
        Analyze message performance

        Returns:
            Performance metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency,
                COUNT(CASE WHEN delivered = 1 THEN 1 END) as delivered,
                COUNT(CASE WHEN acked = 1 THEN 1 END) as acked,
                COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as errors
            FROM message_history
            WHERE latency_ms IS NOT NULL
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'total_messages': row[0],
            'avg_latency_ms': row[1] or 0,
            'min_latency_ms': row[2] or 0,
            'max_latency_ms': row[3] or 0,
            'delivery_rate': row[4] / row[0] if row[0] > 0 else 0,
            'ack_rate': row[5] / row[0] if row[0] > 0 else 0,
            'error_rate': row[6] / row[0] if row[0] > 0 else 0
        }

    def get_stats(self) -> Dict:
        """Get replay statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT from_client) as unique_senders,
                COUNT(DISTINCT to_client) as unique_recipients,
                SUM(replay_count) as total_replays
            FROM message_history
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'total_messages': row[0],
            'unique_senders': row[1],
            'unique_recipients': row[2],
            'total_replays': row[3]
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("🔍 Message Replay & History Viewer Test")
    print("="*70)

    replay = MessageReplay(db_path="test_history.db")

    # Record some messages
    print("\n1️⃣ Recording messages...")

    messages = [
        MessageRecord(
            id="msg-1",
            from_client="code",
            to_client="browser",
            type="command",
            payload={'text': 'What is 2+2?'},
            timestamp=datetime.now(timezone.utc).isoformat(),
            delivered=True,
            latency_ms=45.2
        ),
        MessageRecord(
            id="msg-2",
            from_client="browser",
            to_client="code",
            type="claude_response",
            payload={'response': '4'},
            timestamp=datetime.now(timezone.utc).isoformat(),
            delivered=True,
            acked=True,
            latency_ms=1200.5
        ),
    ]

    for msg in messages:
        replay.record_message(msg)
        print(f"   Recorded: {msg.id}")

    # Get history
    print("\n2️⃣ Getting history...")
    history = replay.get_history(limit=10)
    for msg in history:
        print(f"   [{msg.timestamp}] {msg.from_client} → {msg.to_client}: {msg.type}")

    # Get conversation
    print("\n3️⃣ Getting conversation...")
    conversation = replay.get_conversation('code', 'browser')
    print(f"   Found {len(conversation)} messages")

    # Performance analysis
    print("\n4️⃣ Performance analysis:")
    perf = replay.analyze_performance()
    for key, value in perf.items():
        print(f"   {key}: {value}")

    # Export timeline
    print("\n5️⃣ Exporting timeline...")
    replay.export_timeline('timeline.json', format='json')
    replay.export_timeline('timeline.html', format='html')
    print("   Exported: timeline.json, timeline.html")

    # Stats
    print("\n6️⃣ Replay stats:")
    stats = replay.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Test complete")
