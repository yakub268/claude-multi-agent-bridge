#!/usr/bin/env python3
"""
Server-Sent Events (SSE) Streaming
Real-time event streaming for browser clients
"""
from flask import Blueprint, Response, request
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from queue import Queue, Empty
from threading import Lock
import uuid


@dataclass
class SSEClient:
    """
    SSE client connection

    Attributes:
        client_id: Unique client identifier
        queue: Message queue for this client
        last_event_id: Last event ID sent (for reconnection)
        connected_at: Connection timestamp
        subscriptions: Set of event types client is subscribed to
    """
    client_id: str
    queue: Queue
    last_event_id: Optional[str] = None
    connected_at: Optional[datetime] = None
    subscriptions: set = None

    def __post_init__(self):
        if self.connected_at is None:
            self.connected_at = datetime.now(timezone.utc)
        if self.subscriptions is None:
            self.subscriptions = set()


class SSEManager:
    """
    Manage Server-Sent Events connections

    Features:
    - Multiple concurrent client connections
    - Event filtering by type
    - Automatic reconnection support
    - Heartbeat/keep-alive
    - Per-client message queues
    - Broadcast to all or filtered clients

    Usage:
        manager = SSEManager()

        # Client connects
        @app.route('/stream')
        def stream():
            return Response(
                manager.stream_events('client-123'),
                mimetype='text/event-stream'
            )

        # Broadcast event
        manager.broadcast('message_received', {
            'from': 'code',
            'text': 'Hello'
        })
    """

    def __init__(self, max_queue_size: int = 100, heartbeat_interval: int = 30):
        self.clients: Dict[str, SSEClient] = {}
        self.max_queue_size = max_queue_size
        self.heartbeat_interval = heartbeat_interval
        self.event_counter = 0
        self.lock = Lock()
        self.stats = {
            'total_connections': 0,
            'total_events_sent': 0,
            'total_broadcasts': 0
        }

    def register_client(self, client_id: str, subscriptions: Optional[set] = None) -> SSEClient:
        """
        Register new SSE client

        Args:
            client_id: Unique client ID
            subscriptions: Set of event types to subscribe to (None = all)

        Returns:
            SSEClient instance
        """
        with self.lock:
            if client_id in self.clients:
                # Reconnection - reuse queue
                client = self.clients[client_id]
            else:
                # New connection
                client = SSEClient(
                    client_id=client_id,
                    queue=Queue(maxsize=self.max_queue_size),
                    subscriptions=subscriptions or set()
                )
                self.clients[client_id] = client
                self.stats['total_connections'] += 1

            return client

    def unregister_client(self, client_id: str):
        """Remove client on disconnect"""
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]

    def send_event(self, client_id: str, event_type: str, data: Dict, event_id: Optional[str] = None):
        """
        Send event to specific client

        Args:
            client_id: Target client ID
            event_type: Event type (e.g., 'message', 'notification')
            data: Event payload
            event_id: Optional event ID (for replay)
        """
        with self.lock:
            if client_id not in self.clients:
                return

            client = self.clients[client_id]

            # Check subscription filter
            if client.subscriptions and event_type not in client.subscriptions:
                return

            # Generate event ID if not provided
            if event_id is None:
                self.event_counter += 1
                event_id = f"event-{self.event_counter}"

            # Enqueue event
            try:
                client.queue.put({
                    'id': event_id,
                    'event': event_type,
                    'data': data,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, block=False)

                client.last_event_id = event_id
                self.stats['total_events_sent'] += 1

            except Exception:
                # Queue full - skip event
                pass

    def broadcast(self, event_type: str, data: Dict, exclude: Optional[List[str]] = None):
        """
        Broadcast event to all clients

        Args:
            event_type: Event type
            data: Event payload
            exclude: List of client IDs to exclude
        """
        exclude = exclude or []

        with self.lock:
            self.event_counter += 1
            event_id = f"event-{self.event_counter}"
            self.stats['total_broadcasts'] += 1

            for client_id in list(self.clients.keys()):
                if client_id not in exclude:
                    self.send_event(client_id, event_type, data, event_id)

    def stream_events(self, client_id: str, subscriptions: Optional[set] = None) -> Generator:
        """
        Generate SSE stream for client

        Args:
            client_id: Client ID
            subscriptions: Event types to subscribe to

        Yields:
            SSE-formatted messages
        """
        client = self.register_client(client_id, subscriptions)

        try:
            # Send initial connection event
            yield self._format_event('connected', {
                'client_id': client_id,
                'timestamp': client.connected_at.isoformat()
            })

            last_heartbeat = time.time()

            while True:
                # Check for messages in queue
                try:
                    event = client.queue.get(timeout=1)
                    yield self._format_event(event['event'], event['data'], event['id'])

                except Empty:
                    # No messages - check if heartbeat needed
                    now = time.time()
                    if now - last_heartbeat > self.heartbeat_interval:
                        yield self._format_heartbeat()
                        last_heartbeat = now

        except GeneratorExit:
            # Client disconnected
            self.unregister_client(client_id)

    def _format_event(self, event_type: str, data: Dict, event_id: Optional[str] = None) -> str:
        """
        Format event in SSE format

        SSE Format:
            id: event-123
            event: message_received
            data: {"from": "code", "text": "hello"}

            (blank line separator)
        """
        lines = []

        if event_id:
            lines.append(f"id: {event_id}")

        lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")  # Blank line to end event

        return "\n".join(lines) + "\n"

    def _format_heartbeat(self) -> str:
        """Format heartbeat/keep-alive message"""
        return f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"

    def get_stats(self) -> Dict:
        """Get streaming statistics"""
        with self.lock:
            return {
                **self.stats,
                'active_clients': len(self.clients),
                'total_queued': sum(c.queue.qsize() for c in self.clients.values())
            }

    def get_client_info(self, client_id: str) -> Optional[Dict]:
        """Get info about specific client"""
        with self.lock:
            if client_id not in self.clients:
                return None

            client = self.clients[client_id]

            return {
                'client_id': client.client_id,
                'connected_at': client.connected_at.isoformat(),
                'subscriptions': list(client.subscriptions),
                'queue_size': client.queue.qsize(),
                'last_event_id': client.last_event_id
            }


# ============================================================================
# Flask Integration
# ============================================================================

def create_sse_blueprint(manager: SSEManager) -> Blueprint:
    """
    Create Flask blueprint with SSE endpoints

    Args:
        manager: SSEManager instance

    Returns:
        Flask Blueprint
    """
    bp = Blueprint('streaming', __name__, url_prefix='/stream')

    @bp.route('/events', methods=['GET'])
    def stream_all_events():
        """
        Stream all events

        Query params:
            ?client_id=xyz - Client identifier
            ?subscribe=event1,event2 - Filter event types
        """
        client_id = request.args.get('client_id', str(uuid.uuid4()))
        subscribe = request.args.get('subscribe', '')

        subscriptions = set(subscribe.split(',')) if subscribe else None

        return Response(
            manager.stream_events(client_id, subscriptions),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Disable nginx buffering
                'Connection': 'keep-alive'
            }
        )

    @bp.route('/broadcast', methods=['POST'])
    def broadcast_event():
        """
        Broadcast event to all clients

        Body:
            {
                "event": "notification",
                "data": {...}
            }
        """
        payload = request.json
        event_type = payload.get('event', 'message')
        data = payload.get('data', {})

        manager.broadcast(event_type, data)

        return {'status': 'broadcasted'}

    @bp.route('/send', methods=['POST'])
    def send_event():
        """
        Send event to specific client

        Body:
            {
                "client_id": "xyz",
                "event": "notification",
                "data": {...}
            }
        """
        payload = request.json
        client_id = payload['client_id']
        event_type = payload.get('event', 'message')
        data = payload.get('data', {})

        manager.send_event(client_id, event_type, data)

        return {'status': 'sent'}

    @bp.route('/stats', methods=['GET'])
    def stats():
        """Get streaming statistics"""
        return manager.get_stats()

    @bp.route('/clients', methods=['GET'])
    def list_clients():
        """List connected clients"""
        with manager.lock:
            clients = []
            for client_id in manager.clients.keys():
                info = manager.get_client_info(client_id)
                if info:
                    clients.append(info)

            return {'clients': clients, 'count': len(clients)}

    return bp


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    from flask import Flask
    import threading

    print("="*70)
    print("📡 Server-Sent Events Test")
    print("="*70)

    app = Flask(__name__)

    # Create SSE manager
    sse_manager = SSEManager()

    # Register blueprint
    app.register_blueprint(create_sse_blueprint(sse_manager))

    # Simulate broadcasts
    def broadcast_loop():
        """Simulate periodic broadcasts"""
        time.sleep(2)  # Wait for server to start

        events = [
            ('message_received', {'from': 'code', 'text': 'Hello world'}),
            ('notification', {'type': 'info', 'message': 'System update available'}),
            ('error', {'code': 500, 'message': 'Something went wrong'}),
        ]

        for i in range(3):
            event_type, data = events[i % len(events)]
            print(f"\n📤 Broadcasting: {event_type}")
            sse_manager.broadcast(event_type, data)
            time.sleep(5)

    # Start broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()

    print("\n🔗 SSE Endpoints:")
    print("   GET  /stream/events?client_id=xyz")
    print("   POST /stream/broadcast")
    print("   POST /stream/send")
    print("   GET  /stream/stats")
    print("   GET  /stream/clients")

    print("\n📋 Test with curl:")
    print("   # Stream events")
    print("   curl http://localhost:8080/stream/events?client_id=test-1")
    print("")
    print("   # Subscribe to specific events")
    print("   curl http://localhost:8080/stream/events?subscribe=message_received,notification")
    print("")
    print("   # Broadcast")
    print("   curl -X POST http://localhost:8080/stream/broadcast \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"event\": \"test\", \"data\": {\"msg\": \"hello\"}}'")

    print("\n🚀 Starting server on http://localhost:8080")
    print("   Press Ctrl+C to stop")

    app.run(port=8080, debug=False, threaded=True)
