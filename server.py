"""
Multi-Claude Message Bus
Enables 3-way communication: Code <-> Browser <-> Desktop

Phase 1 upgrades:
- True SSE push (no polling, instant delivery)
- SQLite persistence (messages survive restarts)
- FTS5 full-text search on message payloads
- Event sourcing (append-only, full audit trail)
- /api/search endpoint for agents to find context
"""

import json
import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = "bridge_messages.db"
db_local = threading.local()

# SSE subscriber queues — each connected client gets its own queue
_subscribers: dict[str, list[queue.Queue]] = {}  # client_id -> [Queue, ...]
_subscribers_lock = threading.Lock()


# ── Database ──────────────────────────────────────────────────────────────────


def get_db():
    if not hasattr(db_local, "conn"):
        db_local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        db_local.conn.row_factory = sqlite3.Row
    return db_local.conn


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id        TEXT PRIMARY KEY,
            seq       INTEGER NOT NULL,
            ts        TEXT    NOT NULL,
            from_c    TEXT    NOT NULL,
            to_c      TEXT    NOT NULL,
            msg_type  TEXT    NOT NULL,
            payload   TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ts    ON messages(ts);
        CREATE INDEX IF NOT EXISTS idx_to_c  ON messages(to_c);
        CREATE INDEX IF NOT EXISTS idx_seq   ON messages(seq);

        -- Sequence counter (event sourcing)
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        INSERT OR IGNORE INTO meta VALUES ('seq', '0');

        -- FTS5 full-text search
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            id UNINDEXED,
            msg_type,
            payload,
            content=messages,
            content_rowid=rowid
        );

        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, id, msg_type, payload)
            VALUES (new.rowid, new.id, new.msg_type, new.payload);
        END;
    """
    )
    conn.commit()
    conn.close()


def next_seq(conn) -> int:
    conn.execute("UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key='seq'")
    return conn.execute("SELECT value FROM meta WHERE key='seq'").fetchone()[0]


def insert_message(msg: dict) -> None:
    conn = get_db()
    seq = next_seq(conn)
    conn.execute(
        "INSERT INTO messages (id, seq, ts, from_c, to_c, msg_type, payload) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            msg["id"],
            seq,
            msg["timestamp"],
            msg["from"],
            msg["to"],
            msg["type"],
            json.dumps(msg["payload"]),
        ),
    )
    conn.commit()


def rows_to_messages(rows) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "seq": r["seq"],
                "timestamp": r["ts"],
                "from": r["from_c"],
                "to": r["to_c"],
                "type": r["msg_type"],
                "payload": json.loads(r["payload"]),
            }
        )
    return out


# ── SSE fan-out ───────────────────────────────────────────────────────────────


def _fanout(msg: dict, to_client: str):
    """Push message to all SSE subscribers interested in this client id."""
    targets = {"all", to_client}
    with _subscribers_lock:
        for cid, queues in _subscribers.items():
            if cid in targets or to_client == "all":
                for q in queues:
                    try:
                        q.put_nowait(msg)
                    except queue.Full:
                        pass


def _register(client_id: str) -> queue.Queue:
    q = queue.Queue(maxsize=200)
    with _subscribers_lock:
        _subscribers.setdefault(client_id, []).append(q)
    return q


def _unregister(client_id: str, q: queue.Queue):
    with _subscribers_lock:
        lst = _subscribers.get(client_id, [])
        if q in lst:
            lst.remove(q)


# ── Message factory ───────────────────────────────────────────────────────────


def make_message(data: dict) -> dict:
    return {
        "id": f"msg-{int(time.time() * 1000)}-{id(data) % 9999:04d}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": data.get("from", "unknown"),
        "to": data.get("to", "all"),
        "type": data.get("type", "broadcast"),
        "payload": data.get("payload", {}),
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@app.route("/api/send", methods=["POST"])
def send_message():
    data = request.json or {}
    msg = make_message(data)
    insert_message(msg)
    _fanout(msg, msg["to"])
    return jsonify({"status": "ok", "message_id": msg["id"], "seq": msg.get("seq")})


@app.route("/api/messages", methods=["GET"])
def get_messages():
    """Polling fallback — returns messages newer than `since` timestamp."""
    since = request.args.get("since", "")
    to_filter = request.args.get("to", "all")

    conn = get_db()
    if to_filter == "all":
        rows = conn.execute(
            "SELECT * FROM messages WHERE ts > ? ORDER BY seq", (since,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM messages WHERE ts > ? AND to_c IN (?,?) ORDER BY seq",
            (since, to_filter, "all"),
        ).fetchall()

    return jsonify({"messages": rows_to_messages(rows)})


@app.route("/api/subscribe")
def subscribe():
    """
    True SSE push stream — no polling inside the server.
    Client connects once; messages arrive instantly when sent.
    """
    client_id = request.args.get("client", "all")
    last_seq = int(request.args.get("since_seq", 0))

    q = _register(client_id)

    def stream():
        try:
            # Replay any missed messages since reconnect
            conn = get_db()
            if last_seq:
                missed = conn.execute(
                    "SELECT * FROM messages WHERE seq > ? AND to_c IN (?,?) ORDER BY seq",
                    (last_seq, client_id, "all"),
                ).fetchall()
                for row in rows_to_messages(missed):
                    yield f"data: {json.dumps(row)}\n\n"

            # Yield SSE heartbeat every 15s, real messages instantly
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            _unregister(client_id, q)

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/search")
def search():
    """
    FTS5 full-text search across all messages.
    Agents use this to find relevant past context.
    GET /api/search?q=deployment+error&limit=10
    """
    q_str = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)

    if not q_str:
        return jsonify({"error": "q parameter required"}), 400

    conn = get_db()
    rows = conn.execute(
        """
        SELECT m.* FROM messages m
        JOIN messages_fts f ON m.rowid = f.rowid
        WHERE messages_fts MATCH ?
        ORDER BY m.seq DESC
        LIMIT ?
        """,
        (q_str, limit),
    ).fetchall()

    return jsonify({"results": rows_to_messages(rows), "query": q_str})


@app.route("/api/status")
def status():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    with _subscribers_lock:
        active = {k: len(v) for k, v in _subscribers.items() if v}

    return jsonify(
        {
            "status": "running",
            "message_count": count,
            "active_subscribers": active,
            "transport": "SSE + polling fallback",
            "persistence": "SQLite (append-only)",
        }
    )


@app.route("/api/clear", methods=["POST"])
def clear():
    """Dev helper: wipe all messages (preserves schema)."""
    conn = get_db()
    conn.execute("DELETE FROM messages")
    conn.execute("UPDATE meta SET value='0' WHERE key='seq'")
    conn.commit()
    return jsonify({"status": "cleared"})


# ── Boot ──────────────────────────────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    print("🚀 Multi-Claude Message Bus  http://localhost:5001")
    print("📡 SSE push:     GET  /api/subscribe?client=code&since_seq=0")
    print("📤 Send:         POST /api/send")
    print("🔍 Search (FTS): GET  /api/search?q=<query>")
    print("📋 Poll:         GET  /api/messages")
    print("💾 Persistence:  SQLite  bridge_messages.db")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
