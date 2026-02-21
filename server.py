"""
Multi-Claude Message Bus
Enables 3-way communication: Code <-> Browser <-> Desktop
"""
import json
import time
import threading
from collections import deque
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow browser extension to POST

# Message queue (last 100 messages)
message_queue = deque(maxlen=100)
message_lock = threading.Lock()

# Active clients (for Server-Sent Events)
clients = []


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
            "payload": self.payload
        }


@app.route('/api/send', methods=['POST'])
def send_message():
    """Send a message to the bus"""
    data = request.json
    msg = Message(
        from_client=data.get('from', 'unknown'),
        to_client=data.get('to', 'all'),
        msg_type=data.get('type', 'broadcast'),
        payload=data.get('payload', {})
    )

    with message_lock:
        message_queue.append(msg.to_dict())

    return jsonify({"status": "ok", "message_id": msg.id})


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Get recent messages (polling endpoint)"""
    since = request.args.get('since')  # timestamp
    to_filter = request.args.get('to', 'all')  # filter by recipient

    with message_lock:
        messages = list(message_queue)

    # Filter by timestamp
    if since:
        messages = [m for m in messages if m['timestamp'] > since]

    # Filter by recipient (include 'all' and direct messages)
    if to_filter != 'all':
        messages = [m for m in messages if m['to'] in [to_filter, 'all']]

    return jsonify({"messages": messages})


@app.route('/api/subscribe')
def subscribe():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        last_id = None
        while True:
            with message_lock:
                new_messages = [m for m in message_queue if m['id'] != last_id]

            if new_messages:
                for msg in new_messages:
                    yield f"data: {json.dumps(msg)}\n\n"
                    last_id = msg['id']

            time.sleep(0.5)  # Poll every 500ms

    return app.response_class(
        event_stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/status', methods=['GET'])
def status():
    """Health check + message count"""
    with message_lock:
        count = len(message_queue)

    return jsonify({
        "status": "running",
        "message_count": count,
        "clients": ["code", "browser", "desktop", "extension"]
    })


if __name__ == '__main__':
    print("🚀 Multi-Claude Message Bus starting on http://localhost:5001")
    print("📡 Endpoints:")
    print("   POST /api/send        - Send message")
    print("   GET  /api/messages    - Poll messages")
    print("   GET  /api/subscribe   - SSE stream")
    print("   GET  /api/status      - Health check")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
