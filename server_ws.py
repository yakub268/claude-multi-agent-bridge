#!/usr/bin/env python3
"""
WebSocket-enabled Message Bus Server
Real-time bi-directional communication (upgrade from polling)
"""
import os
import json
import time
import uuid
import asyncio
import logging
import threading
from datetime import datetime, timezone
from collections import defaultdict, deque
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

# Import datetime utilities for consistent timezone handling
from datetime_utils import utc_now, utc_timestamp, parse_iso_timestamp, seconds_since

# Import collaboration bridge
try:
    from collab_ws_integration import CollabWSBridge
    COLLAB_ENABLED = True
except ImportError:
    COLLAB_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("Collaboration features not available (collab_ws_integration.py missing)")

# Import monitoring
try:
    from monitoring import MetricsCollector
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("Monitoring not available (monitoring.py missing)")

# Import auth
try:
    from auth import TokenAuth, RateLimiter
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("Authentication not available (auth.py missing)")

# Setup logging with UTF-8 encoding (fixes Windows emoji issues)
import sys

# Configure logging based on environment
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_format = os.getenv('LOG_FORMAT', 'standard')

if log_format == 'json':
    # JSON logging for structured log aggregation (ELK, Datadog, etc.)
    log_formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    )
else:
    # Standard logging
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# File handler
file_handler = logging.FileHandler('message_bus_ws.log', encoding='utf-8')
file_handler.setFormatter(log_formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level),
    handlers=[file_handler, console_handler]
)

# Force stdout to UTF-8 for emoji support
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)
logger.info(f"Logging configured: level={log_level}, format={log_format}")

app = Flask(__name__)

# Request ID middleware for distributed tracing
@app.before_request
def add_request_id():
    """Add unique request ID to each request for tracing"""
    request.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    # Log request with ID
    if request.method != 'OPTIONS':  # Skip OPTIONS preflight
        logger.debug(f"[{request.request_id[:8]}] {request.method} {request.path}")

@app.after_request
def add_request_id_header(response):
    """Add request ID to response headers"""
    if hasattr(request, 'request_id'):
        response.headers['X-Request-ID'] = request.request_id
    return response

# CORS configuration - whitelist specific origins (not '*')
# To allow all origins (NOT recommended for production), set CORS_ORIGINS env var to '*'
import os
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000').split(',')
if '*' in allowed_origins:
    logger.warning("⚠️  CORS allowing ALL origins - not recommended for production!")
    CORS(app, origins='*')
else:
    logger.info(f"CORS whitelist: {allowed_origins}")
    CORS(app, origins=allowed_origins)

sock = Sock(app)

# In-memory message store
message_store = deque(maxlen=500)  # Keep last 500 messages
message_ttl = 300  # 5 minutes

# Connection limits (prevent resource exhaustion)
MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', '1000'))  # Total connections
MAX_CONNECTIONS_PER_CLIENT = int(os.getenv('MAX_CONNECTIONS_PER_CLIENT', '10'))  # Per client ID

# Start background cleanup task for message TTL
def cleanup_old_messages():
    """Background task to remove expired messages"""
    import threading
    while True:
        time.sleep(60)  # Run every minute
        try:
            now = utc_now()
            expired = []

            for msg in list(message_store):
                try:
                    msg_time = parse_iso_timestamp(msg['timestamp'])
                    age_seconds = (now - msg_time).total_seconds()
                    if age_seconds > message_ttl:
                        expired.append(msg)
                except Exception:
                    pass

            for msg in expired:
                try:
                    message_store.remove(msg)
                except ValueError:
                    pass  # Already removed

            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired messages")
        except Exception as e:
            logger.error(f"Message cleanup error: {e}")

def cleanup_old_acks():
    """Background task to remove expired pending acks"""
    ack_ttl = 600  # 10 minutes - acks shouldn't be pending this long
    while True:
        time.sleep(120)  # Run every 2 minutes
        try:
            now = utc_now()
            expired = []

            for msg_id, ack_data in list(pending_acks.items()):
                try:
                    ack_time = parse_iso_timestamp(ack_data['timestamp'])
                    age_seconds = (now - ack_time).total_seconds()
                    if age_seconds > ack_ttl:
                        expired.append(msg_id)
                except Exception:
                    pass

            for msg_id in expired:
                try:
                    del pending_acks[msg_id]
                except KeyError:
                    pass  # Already removed

            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired pending acks")
        except Exception as e:
            logger.error(f"Pending acks cleanup error: {e}")

# Start cleanup threads
cleanup_msg_thread = threading.Thread(target=cleanup_old_messages, daemon=True)
cleanup_msg_thread.start()

cleanup_ack_thread = threading.Thread(target=cleanup_old_acks, daemon=True)
cleanup_ack_thread.start()

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

# Monitoring
metrics_collector = MetricsCollector() if MONITORING_ENABLED else None

# Authentication
token_auth = TokenAuth() if AUTH_ENABLED else None
rate_limiter = RateLimiter() if AUTH_ENABLED else None

# Redis backend (optional, initialized later if REDIS_HOST is configured)
redis_backend = None


# ============================================================================
# WebSocket Handlers
# ============================================================================

@sock.route('/ws/<client_id>')
def websocket_handler(ws, client_id):
    """
    WebSocket connection handler
    Maintains persistent connection for real-time messaging
    """
    # Generate unique connection ID to prevent race conditions
    import uuid
    connection_id = str(uuid.uuid4())

    logger.info(f"WebSocket connection opened: {client_id} (conn_id: {connection_id[:8]})")

    # Check connection limits (prevent resource exhaustion)
    total_connections = sum(len(conns) for conns in ws_connections.values())
    client_connections = len(ws_connections[client_id])

    if total_connections >= MAX_CONNECTIONS:
        logger.warning(f"Connection limit reached ({total_connections}/{MAX_CONNECTIONS}), rejecting {client_id}")
        ws.send(json.dumps({
            'type': 'error',
            'error': f'Server connection limit reached ({MAX_CONNECTIONS} connections)',
            'timestamp': utc_timestamp()
        }))
        ws.close()
        return

    if client_connections >= MAX_CONNECTIONS_PER_CLIENT:
        logger.warning(f"Per-client connection limit reached for {client_id} ({client_connections}/{MAX_CONNECTIONS_PER_CLIENT})")
        ws.send(json.dumps({
            'type': 'error',
            'error': f'Connection limit reached for client ({MAX_CONNECTIONS_PER_CLIENT} connections per client)',
            'timestamp': utc_timestamp()
        }))
        ws.close()
        return

    # Register connection with unique ID
    ws_connections[client_id].add(ws)
    connection_metadata[ws] = {
        'client_id': client_id,
        'connection_id': connection_id,
        'connected_at': utc_timestamp()
    }

    # Register with collab bridge
    if collab_bridge:
        collab_bridge.register_ws_connection(ws, client_id)

    # Update metrics
    metrics['total_connections'] += 1
    metrics['active_connections'] = sum(len(conns) for conns in ws_connections.values())

    # Record monitoring metrics
    if metrics_collector:
        metrics_collector.record_connection_open(client_id)

    try:
        # Send connection confirmation
        ws.send(json.dumps({
            'type': 'connection_confirmed',
            'client_id': client_id,
            'timestamp': utc_timestamp(),
            'server': 'claude-bridge-ws-v1.0'
        }))

        # Server-side heartbeat to detect dead connections
        last_ping_time = time.time()
        ping_interval = 30  # Send ping every 30 seconds

        # Listen for incoming messages
        while True:
            # Non-blocking receive with timeout for heartbeat
            data = ws.receive(timeout=1.0)

            # Send server ping if interval elapsed
            current_time = time.time()
            if current_time - last_ping_time >= ping_interval:
                try:
                    ws.send(json.dumps({
                        'type': 'ping',
                        'timestamp': utc_timestamp()
                    }))
                    last_ping_time = current_time
                except Exception as e:
                    logger.warning(f"Failed to send ping to {client_id}: {e}")
                    break  # Connection is dead

            if data is None:
                continue  # Timeout, no data received

            try:
                message = json.loads(data)
                handle_ws_message(ws, client_id, message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_id}: {e}")
                ws.send(json.dumps({
                    'type': 'error',
                    'error': 'Invalid JSON',
                    'timestamp': utc_timestamp()
                }))
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                metrics['errors'] += 1

    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        # Cleanup on disconnect - use connection_id to avoid race conditions
        conn_info = connection_metadata.get(ws)
        if conn_info:
            logger.info(f"WebSocket connection closed: {client_id} (conn_id: {conn_info['connection_id'][:8]})")

        # Remove this specific connection
        ws_connections[client_id].discard(ws)
        if ws in connection_metadata:
            del connection_metadata[ws]

        # Unregister from collab bridge
        if collab_bridge:
            collab_bridge.unregister_ws_connection(ws)

        # Clean up client_id entry if no more connections
        if client_id in ws_connections and not ws_connections[client_id]:
            del ws_connections[client_id]

        metrics['active_connections'] = sum(len(conns) for conns in ws_connections.values())

        # Record monitoring metrics
        if metrics_collector:
            metrics_collector.record_connection_close(client_id)

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
            'timestamp': utc_timestamp()
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
                        'timestamp': utc_timestamp()
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
                        'timestamp': utc_timestamp()
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

    # Create message (using UUID to prevent collisions)
    msg_id = f"msg-{uuid.uuid4().hex[:16]}"
    timestamp = utc_timestamp()

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
# REST API (Backward Compatibility + Versioned)
# ============================================================================

# Version 1 API (current, recommended)
@app.route('/api/v1/send', methods=['POST'])
@app.route('/api/send', methods=['POST'])  # Backward compatibility (unversioned)
def http_send():
    """HTTP endpoint for sending messages (backward compatible)"""
    try:
        # Rate limiting - ALWAYS applied (not just when client provides header)
        client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

        if rate_limiter and not rate_limiter.is_allowed(client_identifier):
            logger.warning(f"Rate limit exceeded for {client_identifier}")
            return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

        # Authentication (optional)
        if token_auth:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
                verified_client = token_auth.verify_token(token)
                if not verified_client:
                    return jsonify({'error': 'Invalid token'}), 401

        data = request.json

        from_client = data.get('from')
        to_client = data.get('to')
        msg_type = data.get('type', 'message')
        payload = data.get('payload', {})

        if not from_client or not to_client:
            return jsonify({'error': 'Missing from or to'}), 400

        # Create message (using UUID to prevent collisions)
        msg_id = f"msg-{uuid.uuid4().hex[:16]}"
        timestamp = utc_timestamp()
        send_time = time.time()

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

        # Record monitoring metrics
        if metrics_collector:
            latency_ms = (time.time() - send_time) * 1000
            metrics_collector.record_message(from_client, to_client, latency_ms)

        return jsonify({'status': 'sent', 'message_id': msg_id}), 200

    except Exception as e:
        logger.error(f"Error in /api/send: {e}")
        metrics['errors'] += 1

        # Record error in monitoring
        if metrics_collector:
            metrics_collector.record_message_error('http_send_error')

        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/messages', methods=['GET'])
@app.route('/api/messages', methods=['GET'])  # Backward compatibility
def http_get_messages():
    """HTTP endpoint for getting messages (backward compatible with polling)"""
    try:
        # Rate limiting
        client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

        if rate_limiter and not rate_limiter.is_allowed(client_identifier):
            logger.warning(f"Rate limit exceeded for {client_identifier}")
            return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

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


@app.route('/api/v1/status', methods=['GET'])
@app.route('/api/status', methods=['GET'])  # Backward compatibility
def get_status():
    """Get server status and metrics"""
    # Rate limiting
    client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

    if rate_limiter and not rate_limiter.is_allowed(client_identifier):
        logger.warning(f"Rate limit exceeded for {client_identifier}")
        return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

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


@app.route('/api/v1/clear', methods=['POST'])
@app.route('/api/clear', methods=['POST'])  # Backward compatibility
def clear_messages():
    """Clear message store"""
    # Rate limiting
    client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

    if rate_limiter and not rate_limiter.is_allowed(client_identifier):
        logger.warning(f"Rate limit exceeded for {client_identifier}")
        return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

    message_store.clear()
    pending_acks.clear()
    logger.info("Message store cleared")
    return jsonify({'status': 'cleared'}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}), 200


@app.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    if not MONITORING_ENABLED:
        return jsonify({'error': 'Monitoring not enabled'}), 503

    try:
        from prometheus_client import generate_latest, REGISTRY
        from flask import Response
        return Response(generate_latest(REGISTRY), mimetype='text/plain')
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        return jsonify({'error': 'Metrics unavailable'}), 500


# ============================================================================
# Collaboration API Endpoints
# ============================================================================

@app.route('/api/v1/collab/rooms', methods=['GET'])
@app.route('/api/collab/rooms', methods=['GET'])  # Backward compatibility
def list_collab_rooms():
    """List all collaboration rooms"""
    # Rate limiting
    client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

    if rate_limiter and not rate_limiter.is_allowed(client_identifier):
        logger.warning(f"Rate limit exceeded for {client_identifier}")
        return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

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


@app.route('/api/v1/collab/rooms/<room_id>', methods=['GET'])
@app.route('/api/collab/rooms/<room_id>', methods=['GET'])  # Backward compatibility
def get_collab_room(room_id):
    """Get room details"""
    # Rate limiting
    client_identifier = request.headers.get('X-Client-ID') or request.remote_addr

    if rate_limiter and not rate_limiter.is_allowed(client_identifier):
        logger.warning(f"Rate limit exceeded for {client_identifier}")
        return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

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
# Graceful Shutdown
# ============================================================================

import signal
import sys

def graceful_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    logger.info("="*70)
    logger.info("🛑 SHUTTING DOWN GRACEFULLY")
    logger.info("="*70)

    # Close all WebSocket connections
    logger.info(f"Closing {sum(len(conns) for conns in ws_connections.values())} WebSocket connections...")
    for client_id, connections in list(ws_connections.items()):
        for ws in list(connections):
            try:
                ws.send(json.dumps({
                    'type': 'server_shutdown',
                    'message': 'Server is shutting down',
                    'timestamp': utc_timestamp()
                }))
                ws.close()
            except Exception as e:
                logger.debug(f"Error closing connection for {client_id}: {e}")

    # Close collaboration rooms
    if collab_bridge:
        logger.info(f"Closing {len(collab_bridge.hub.rooms)} collaboration rooms...")
        for room_id in list(collab_bridge.hub.rooms.keys()):
            try:
                collab_bridge.hub.close_room(room_id)
            except Exception as e:
                logger.debug(f"Error closing room {room_id}: {e}")

    # Close Redis connection (if configured)
    if redis_backend:
        logger.info("Closing Redis connection...")
        try:
            redis_backend.close()
        except Exception as e:
            logger.debug(f"Error closing Redis: {e}")

    logger.info("✅ Shutdown complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

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
