#!/usr/bin/env python3
"""
WebSocket-enabled Message Bus Server
Real-time bi-directional communication (upgrade from polling)
"""
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from collections import defaultdict, deque
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

# Import collaboration bridge
try:
    from collab_ws_integration import CollabWSBridge
    COLLAB_ENABLED = True
except ImportError:
    COLLAB_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("Collaboration features not available (collab_ws_integration.py missing)")

# Setup logging with UTF-8 encoding (fixes Windows emoji issues)
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('message_bus_ws.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
# Force stdout to UTF-8 for emoji support
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins='*')
sock = Sock(app)

# In-memory message store
message_store = deque(maxlen=500)  # Keep last 500 messages
message_ttl = 300  # 5 minutes

# WebSocket connections by client
ws_connections = defaultdict(set)  # client_id -> set of websocket connections
connection_metadata = {}  # ws -> {client_id, connected_at}

# Metrics
metrics = {
    'total_messages': 0,
    'total_connections': 0,
    'active_connections': 0,
    'errors': 0,
    'messages_per_minute': 0,
    'last_message_time': None
}

# Message acknowledgment tracking
pending_acks = {}  # message_id -> {sent_to: set(), acked_by: set(), timestamp}

# Collaboration bridge
collab_bridge = CollabWSBridge() if COLLAB_ENABLED else None


# ============================================================================
# WebSocket Handlers
# ============================================================================

@sock.route('/ws/<client_id>')
def websocket_handler(ws, client_id):
    """
    WebSocket connection handler
    Maintains persistent connection for real-time messaging
    """
    logger.info(f"WebSocket connection opened: {client_id}")

    # Register connection
    ws_connections[client_id].add(ws)
    connection_metadata[ws] = {
        'client_id': client_id,
        'connected_at': datetime.now(timezone.utc).isoformat()
    }

    # Register with collab bridge
    if collab_bridge:
        collab_bridge.register_ws_connection(ws, client_id)

    metrics['total_connections'] += 1
    metrics['active_connections'] = sum(len(conns) for conns in ws_connections.values())

    try:
        # Send connection confirmation
        ws.send(json.dumps({
            'type': 'connection_confirmed',
            'client_id': client_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'server': 'claude-bridge-ws-v1.0'
        }))

        # Listen for incoming messages
        while True:
            data = ws.receive()
            if data is None:
                break

            try:
                message = json.loads(data)
                handle_ws_message(ws, client_id, message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_id}: {e}")
                ws.send(json.dumps({
                    'type': 'error',
                    'error': 'Invalid JSON',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }))
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                metrics['errors'] += 1

    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        # Cleanup on disconnect
        ws_connections[client_id].discard(ws)
        if ws in connection_metadata:
            del connection_metadata[ws]

        # Unregister from collab bridge
        if collab_bridge:
            collab_bridge.unregister_ws_connection(ws)

        if not ws_connections[client_id]:
            del ws_connections[client_id]

        metrics['active_connections'] = sum(len(conns) for conns in ws_connections.values())
        logger.info(f"WebSocket connection closed: {client_id}")


def handle_ws_message(ws, client_id, message):
    """Handle incoming WebSocket messages"""
    msg_type = message.get('type')

    if msg_type == 'send':
        # Send message to another client
        handle_send_message(client_id, message)

    elif msg_type == 'ack':
        # Acknowledge message receipt
        handle_message_ack(client_id, message)

    elif msg_type == 'ping':
        # Respond to ping
        ws.send(json.dumps({
            'type': 'pong',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }))

    elif msg_type == 'subscribe':
        # Client confirms subscription (already handled by connection)
        logger.info(f"{client_id} confirmed subscription")

    elif msg_type == 'collab':
        # Collaboration room action
        request_id = message.get('request_id', 'default')

        if collab_bridge:
            try:
                response = collab_bridge.handle_collab_message(ws, client_id, message)
                ws.send(json.dumps({
                    'type': 'message',
                    'message': {
                        'id': request_id,
                        'from': 'server',
                        'to': client_id,
                        'type': 'collab_response',
                        'payload': {
                            'response': response
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                }))
            except Exception as e:
                logger.error(f"Collab error from {client_id}: {e}")
                ws.send(json.dumps({
                    'type': 'message',
                    'message': {
                        'id': request_id,
                        'from': 'server',
                        'to': client_id,
                        'type': 'collab_response',
                        'payload': {
                            'response': {
                                'status': 'error',
                                'error': str(e)
                            }
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                }))
        else:
            ws.send(json.dumps({
                'type': 'error',
                'error': 'Collaboration features not available'
            }))

    else:
        logger.warning(f"Unknown message type from {client_id}: {msg_type}")


def handle_send_message(from_client, message_data):
    """Handle sending a message to target client(s)"""
    to_client = message_data.get('to')
    msg_type = message_data.get('msg_type', 'message')
    payload = message_data.get('payload', {})

    if not to_client:
        logger.error(f"No 'to' field in message from {from_client}")
        return

    # Create message
    msg_id = f"msg-{int(time.time()*1000)}"
    timestamp = datetime.now(timezone.utc).isoformat()

    msg = {
        'id': msg_id,
        'from': from_client,
        'to': to_client,
        'type': msg_type,
        'payload': payload,
        'timestamp': timestamp,
        'requires_ack': message_data.get('require_ack', False)
    }

    # Store message
    message_store.append(msg)

    # Update metrics
    metrics['total_messages'] += 1
    metrics['last_message_time'] = timestamp

    # Track for acknowledgment if required
    if msg['requires_ack']:
        pending_acks[msg_id] = {
            'sent_to': {to_client},
            'acked_by': set(),
            'timestamp': timestamp
        }

    # Deliver via WebSocket
    deliver_message(msg)

    logger.info(f"Message {msg_id}: {from_client} -> {to_client} ({msg_type})")


def deliver_message(message):
    """Deliver message to target client via WebSocket"""
    to_client = message['to']

    if to_client in ws_connections:
        # Deliver to all connections for this client
        dead_connections = set()

        for ws in ws_connections[to_client]:
            try:
                ws.send(json.dumps({
                    'type': 'message',
                    'message': message
                }))
            except Exception as e:
                logger.error(f"Failed to deliver to {to_client}: {e}")
                dead_connections.add(ws)

        # Cleanup dead connections
        for ws in dead_connections:
            ws_connections[to_client].discard(ws)
    else:
        logger.debug(f"Client {to_client} not connected, message queued")


def handle_message_ack(client_id, ack_data):
    """Handle message acknowledgment"""
    msg_id = ack_data.get('message_id')

    if msg_id in pending_acks:
        pending_acks[msg_id]['acked_by'].add(client_id)
        logger.info(f"Message {msg_id} acknowledged by {client_id}")

        # Check if all recipients acked
        if pending_acks[msg_id]['acked_by'] >= pending_acks[msg_id]['sent_to']:
            logger.info(f"Message {msg_id} fully acknowledged")
            del pending_acks[msg_id]


# ============================================================================
# REST API (Backward Compatibility)
# ============================================================================

@app.route('/api/send', methods=['POST'])
def http_send():
    """HTTP endpoint for sending messages (backward compatible)"""
    try:
        data = request.json

        from_client = data.get('from')
        to_client = data.get('to')
        msg_type = data.get('type', 'message')
        payload = data.get('payload', {})

        if not from_client or not to_client:
            return jsonify({'error': 'Missing from or to'}), 400

        # Create message
        msg_id = f"msg-{int(time.time()*1000)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        msg = {
            'id': msg_id,
            'from': from_client,
            'to': to_client,
            'type': msg_type,
            'payload': payload,
            'timestamp': timestamp,
            'requires_ack': False
        }

        # Store and deliver
        message_store.append(msg)
        metrics['total_messages'] += 1
        metrics['last_message_time'] = timestamp

        deliver_message(msg)

        return jsonify({'status': 'sent', 'message_id': msg_id}), 200

    except Exception as e:
        logger.error(f"Error in /api/send: {e}")
        metrics['errors'] += 1
        return jsonify({'error': str(e)}), 500


@app.route('/api/messages', methods=['GET'])
def http_get_messages():
    """HTTP endpoint for getting messages (backward compatible with polling)"""
    try:
        to_client = request.args.get('to')
        since = request.args.get('since')
        limit = int(request.args.get('limit', 100))

        if not to_client:
            return jsonify({'error': 'Missing to parameter'}), 400

        # Filter messages
        messages = []
        for msg in reversed(message_store):
            if msg['to'] == to_client:
                if since and msg['timestamp'] <= since:
                    continue
                messages.append(msg)
                if len(messages) >= limit:
                    break

        messages.reverse()  # Chronological order

        return jsonify({
            'count': len(messages),
            'messages': messages
        }), 200

    except Exception as e:
        logger.error(f"Error in /api/messages: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status and metrics"""
    # Calculate messages per minute
    if metrics['last_message_time']:
        last_time = datetime.fromisoformat(metrics['last_message_time'].replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        if elapsed > 0:
            metrics['messages_per_minute'] = round(metrics['total_messages'] / (elapsed / 60), 2)

    status = {
        'status': 'running',
        'mode': 'websocket',
        'version': '1.3.0',
        'features': {
            'websocket': True,
            'collaboration': COLLAB_ENABLED,
            'acknowledgments': True,
            'rest_api': True
        },
        'metrics': metrics,
        'connections': {
            'active': metrics['active_connections'],
            'by_client': {client: len(conns) for client, conns in ws_connections.items()}
        },
        'queue': {
            'current': len(message_store),
            'max': message_store.maxlen
        },
        'pending_acks': len(pending_acks)
    }

    # Add collab stats if available
    if collab_bridge:
        status['collaboration'] = {
            'rooms': len(collab_bridge.hub.rooms),
            'active_rooms': collab_bridge.hub.list_rooms()
        }

    return jsonify(status), 200


@app.route('/api/clear', methods=['POST'])
def clear_messages():
    """Clear message store"""
    message_store.clear()
    pending_acks.clear()
    logger.info("Message store cleared")
    return jsonify({'status': 'cleared'}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


# ============================================================================
# Collaboration API Endpoints
# ============================================================================

@app.route('/api/collab/rooms', methods=['GET'])
def list_collab_rooms():
    """List all collaboration rooms"""
    if not collab_bridge:
        return jsonify({'error': 'Collaboration not available'}), 503

    try:
        rooms = collab_bridge.hub.list_rooms()
        return jsonify({
            'status': 'success',
            'rooms': rooms,
            'total': len(rooms)
        }), 200
    except Exception as e:
        logger.error(f"Error listing rooms: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/collab/rooms/<room_id>', methods=['GET'])
def get_collab_room(room_id):
    """Get room details"""
    if not collab_bridge:
        return jsonify({'error': 'Collaboration not available'}), 503

    try:
        room = collab_bridge.hub.get_room(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404

        summary = room.get_summary()
        return jsonify({
            'status': 'success',
            'room': summary
        }), 200
    except Exception as e:
        logger.error(f"Error getting room {room_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    logger.info("="*70)
    logger.info("🚀 CLAUDE MULTI-AGENT BRIDGE - WebSocket Server v1.3")
    logger.info("="*70)
    logger.info("")
    logger.info("📡 Server: http://localhost:5001")
    logger.info("🔌 WebSocket: ws://localhost:5001/ws/<client_id>")
    logger.info("📊 Status: http://localhost:5001/api/status")
    logger.info("🤝 Collab Rooms: http://localhost:5001/api/collab/rooms")
    logger.info("")
    logger.info("Features:")
    logger.info("  ✅ Real-time WebSocket connections")
    logger.info("  ✅ Message acknowledgment support")
    logger.info("  ✅ Backward compatible REST API")
    logger.info("  ✅ Connection pooling per client")
    logger.info("  ✅ Automatic reconnection support")
    if COLLAB_ENABLED:
        logger.info("  ✅ Collaboration rooms (enhanced voting, channels, code execution)")
        logger.info("  ✅ File sharing between Claudes")
        logger.info("  ✅ Kanban board integration")
        logger.info("  ✅ GitHub integration (issues/PRs)")
    else:
        logger.info("  ⚠️  Collaboration features disabled (missing dependencies)")
    logger.info("")
    logger.info("Starting server...")
    logger.info("="*70)

    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
