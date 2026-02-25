"""
Multi-Claude Message Bus v2
Enhanced with: logging, error handling, persistence, metrics
"""

import os
import json
import time
import threading
import sqlite3
import logging
import secrets
from collections import deque
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("message_bus.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Restrict CORS to localhost only for security
CORS(app, resources={r"/*": {"origins": ["http://localhost:*", "http://127.0.0.1:*"]}})

# Configuration
MAX_QUEUE_SIZE = 500
DB_PATH = "message_bus.db"
PERSIST_ENABLED = True

# Security: Admin token from environment variable or auto-generated
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", secrets.token_urlsafe(32))
if not os.getenv("ADMIN_TOKEN"):
    logger.warning(
        "No ADMIN_TOKEN environment variable set. Using auto-generated token.\n"
        "Set ADMIN_TOKEN environment variable in production.\n"
        f"Current token (save this): {ADMIN_TOKEN}"
    )

# In-memory queue (fast access)
message_queue = deque(maxlen=MAX_QUEUE_SIZE)
message_lock = threading.Lock()

# Metrics
metrics = {
    "total_messages": 0,
    "messages_by_client": {},
    "errors": 0,
    "start_time": datetime.utcnow().isoformat(),
}
metrics_lock = threading.Lock()


class Database:
    """SQLite persistence for messages"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    from_client TEXT NOT NULL,
                    to_client TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON messages(timestamp)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_to_client
                ON messages(to_client)
            """
            )
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def save_message(self, msg_dict):
        """Persist message to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO messages
                    (id, timestamp, from_client, to_client, type, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        msg_dict["id"],
                        msg_dict["timestamp"],
                        msg_dict["from"],
                        msg_dict["to"],
                        msg_dict["type"],
                        json.dumps(msg_dict["payload"]),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save message {msg_dict['id']}: {e}")

    def load_recent(self, limit=100):
        """Load recent messages from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, from_client, to_client, type, payload
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                messages = []
                for row in cursor:
                    messages.append(
                        {
                            "id": row[0],
                            "timestamp": row[1],
                            "from": row[2],
                            "to": row[3],
                            "type": row[4],
                            "payload": json.loads(row[5]),
                        }
                    )
                return list(reversed(messages))
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")
            return []

    def get_stats(self):
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                total = cursor.fetchone()[0]

                cursor = conn.execute(
                    """
                    SELECT from_client, COUNT(*)
                    FROM messages
                    GROUP BY from_client
                """
                )
                by_client = dict(cursor.fetchall())

                return {"total": total, "by_client": by_client}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total": 0, "by_client": {}}


# Initialize database
db = Database(DB_PATH) if PERSIST_ENABLED else None

# Load recent messages into queue on startup
if db:
    recent = db.load_recent(MAX_QUEUE_SIZE)
    message_queue.extend(recent)
    logger.info(f"Loaded {len(recent)} messages from database")


class Message:
    def __init__(self, from_client, to_client, msg_type, payload):
        self.id = f"msg-{int(time.time() * 1000)}"
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.from_client = from_client
        self.to_client = to_client
        self.msg_type = msg_type
        self.payload = payload

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "from": self.from_client,
            "to": self.to_client,
            "type": self.msg_type,
            "payload": self.payload,
        }

    def validate(self):
        """Validate message fields"""
        if not self.from_client or not isinstance(self.from_client, str):
            raise ValueError("Invalid 'from' field")
        if not self.to_client or not isinstance(self.to_client, str):
            raise ValueError("Invalid 'to' field")
        if not self.msg_type or not isinstance(self.msg_type, str):
            raise ValueError("Invalid 'type' field")
        if not isinstance(self.payload, dict):
            raise ValueError("Payload must be a dict")
        return True


def update_metrics(from_client):
    """Update message metrics"""
    with metrics_lock:
        metrics["total_messages"] += 1
        if from_client not in metrics["messages_by_client"]:
            metrics["messages_by_client"][from_client] = 0
        metrics["messages_by_client"][from_client] += 1


@app.route("/api/send", methods=["POST"])
def send_message():
    """Send a message to the bus"""
    try:
        data = request.json

        if not data:
            logger.warning("Received empty request body")
            return jsonify({"error": "Empty request body"}), 400

        msg = Message(
            from_client=data.get("from", "unknown"),
            to_client=data.get("to", "all"),
            msg_type=data.get("type", "broadcast"),
            payload=data.get("payload", {}),
        )

        # Validate
        msg.validate()
        msg_dict = msg.to_dict()

        # Add to queue
        with message_lock:
            message_queue.append(msg_dict)

        # Persist to database
        if db:
            db.save_message(msg_dict)

        # Update metrics
        update_metrics(msg.from_client)

        logger.info(
            f"Message {msg.id}: {msg.from_client} -> {msg.to_client} ({msg.msg_type})"
        )

        return jsonify({"status": "ok", "message_id": msg.id})

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        with metrics_lock:
            metrics["errors"] += 1
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in send_message: {e}")
        with metrics_lock:
            metrics["errors"] += 1
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/messages", methods=["GET"])
def get_messages():
    """Get recent messages (polling endpoint)"""
    try:
        since = request.args.get("since")
        to_filter = request.args.get("to", "all")
        limit = int(request.args.get("limit", 100))

        # Cap limit
        limit = min(limit, MAX_QUEUE_SIZE)

        with message_lock:
            messages = list(message_queue)

        # Filter by timestamp
        if since:
            messages = [m for m in messages if m["timestamp"] > since]

        # Filter by recipient
        if to_filter != "all":
            messages = [m for m in messages if m["to"] in [to_filter, "all"]]

        # Apply limit
        messages = messages[-limit:]

        return jsonify({"messages": messages, "count": len(messages)})

    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": "Invalid parameters"}), 400

    except Exception as e:
        logger.error(f"Error in get_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/subscribe")
def subscribe():
    """Server-Sent Events endpoint for real-time updates"""

    def event_stream():
        last_id = None
        try:
            while True:
                with message_lock:
                    new_messages = [m for m in message_queue if m["id"] != last_id]

                if new_messages:
                    for msg in new_messages:
                        yield f"data: {json.dumps(msg)}\n\n"
                        last_id = msg["id"]

                time.sleep(0.5)
        except GeneratorExit:
            logger.info("Client disconnected from SSE stream")
        except Exception as e:
            logger.error(f"Error in event_stream: {e}")

    return app.response_class(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/status", methods=["GET"])
def status():
    """Health check + statistics"""
    try:
        with message_lock:
            queue_count = len(message_queue)

        with metrics_lock:
            current_metrics = metrics.copy()

        db_stats = db.get_stats() if db else {"total": 0, "by_client": {}}

        uptime_seconds = (
            datetime.utcnow()
            - datetime.fromisoformat(current_metrics["start_time"].replace("Z", ""))
        ).total_seconds()

        return jsonify(
            {
                "status": "running",
                "uptime_seconds": int(uptime_seconds),
                "queue": {"current": queue_count, "max": MAX_QUEUE_SIZE},
                "metrics": {
                    "total_messages": current_metrics["total_messages"],
                    "by_client": current_metrics["messages_by_client"],
                    "errors": current_metrics["errors"],
                    "messages_per_minute": (
                        round(
                            current_metrics["total_messages"] / (uptime_seconds / 60), 2
                        )
                        if uptime_seconds > 0
                        else 0
                    ),
                },
                "database": db_stats if db else {"enabled": False},
                "clients": ["code", "browser", "desktop", "extension"],
            }
        )

    except Exception as e:
        logger.error(f"Error in status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/clear", methods=["POST"])
def clear_messages():
    """Clear message queue (admin endpoint)"""
    try:
        auth = request.headers.get("Authorization")
        expected_auth = f"Bearer {ADMIN_TOKEN}"
        if auth != expected_auth:
            logger.warning(f"Unauthorized clear attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401

        with message_lock:
            message_queue.clear()

        logger.warning("Message queue cleared by admin")
        return jsonify({"status": "ok", "cleared": True})

    except Exception as e:
        logger.error(f"Error in clear_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🚀 Multi-Claude Message Bus v2 starting")
    logger.info("=" * 70)
    logger.info("📡 Server: http://localhost:5001")
    logger.info(f"📊 Persistence: {'Enabled' if PERSIST_ENABLED else 'Disabled'}")
    logger.info("📝 Log file: message_bus.log")
    logger.info("")
    logger.info("Endpoints:")
    logger.info("   POST /api/send        - Send message")
    logger.info("   GET  /api/messages    - Poll messages")
    logger.info("   GET  /api/subscribe   - SSE stream")
    logger.info("   GET  /api/status      - Health check + stats")
    logger.info("   POST /api/clear       - Clear queue (admin)")
    logger.info("=" * 70)

    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
