#!/usr/bin/env python3
"""
Admin API for Multi-Agent Bridge
Management endpoints for monitoring and control
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import psutil
import time


class AdminAPI:
    """
    Administrative API endpoints

    Features:
    - System health monitoring
    - Connection management
    - Message queue inspection
    - Performance metrics
    - Configuration updates
    - Emergency controls
    """

    def __init__(self, app, message_store=None, auth_manager=None):
        self.app = app
        self.message_store = message_store
        self.auth_manager = auth_manager
        self.start_time = time.time()

        # Create blueprint
        self.bp = Blueprint('admin', __name__, url_prefix='/admin')
        self._register_routes()
        app.register_blueprint(self.bp)

    def _register_routes(self):
        """Register admin routes"""

        @self.bp.route('/health', methods=['GET'])
        def health_check():
            """Comprehensive health check"""
            return jsonify(self._get_health_status())

        @self.bp.route('/metrics', methods=['GET'])
        def metrics():
            """Prometheus-compatible metrics"""
            return self._get_prometheus_metrics(), 200, {
                'Content-Type': 'text/plain; version=0.0.4'
            }

        @self.bp.route('/connections', methods=['GET'])
        def list_connections():
            """List active connections"""
            return jsonify(self._get_connections())

        @self.bp.route('/connections/<client_id>', methods=['DELETE'])
        def disconnect_client(client_id):
            """Forcefully disconnect a client"""
            result = self._disconnect_client(client_id)
            return jsonify(result)

        @self.bp.route('/messages', methods=['GET'])
        def admin_messages():
            """Query messages with admin privileges"""
            return jsonify(self._query_messages())

        @self.bp.route('/messages/search', methods=['POST'])
        def search_messages():
            """Full-text search in messages"""
            query = request.json.get('query', '')
            limit = request.json.get('limit', 50)

            if self.message_store:
                results = self.message_store.search_messages(query, limit)
                return jsonify({'results': results, 'count': len(results)})

            return jsonify({'error': 'Persistence not enabled'}), 400

        @self.bp.route('/messages/cleanup', methods=['POST'])
        def cleanup_messages():
            """Delete old messages"""
            days = request.json.get('days', 7)

            if self.message_store:
                deleted = self.message_store.cleanup_old_messages(days)
                return jsonify({'deleted': deleted})

            return jsonify({'error': 'Persistence not enabled'}), 400

        @self.bp.route('/stats', methods=['GET'])
        def statistics():
            """Detailed statistics"""
            return jsonify(self._get_statistics())

        @self.bp.route('/keys', methods=['GET'])
        def list_keys():
            """List all API keys (admin only)"""
            if not self.auth_manager:
                return jsonify({'error': 'Auth not enabled'}), 400

            keys = []
            for key_hash, data in self.auth_manager.keys.items():
                keys.append({
                    'client_id': data['client_id'],
                    'permissions': data['permissions'],
                    'rate_limit': data['rate_limit'],
                    'created_at': data['created_at'],
                    'expires_at': data.get('expires_at'),
                    'active': data.get('active', True),
                    'usage': self.auth_manager.usage_stats.get(key_hash, {})
                })

            return jsonify({'keys': keys, 'count': len(keys)})

        @self.bp.route('/keys', methods=['POST'])
        def create_key():
            """Create new API key"""
            if not self.auth_manager:
                return jsonify({'error': 'Auth not enabled'}), 400

            data = request.json
            key = self.auth_manager.generate_key(
                client_id=data.get('client_id', 'user'),
                permissions=set(data.get('permissions', ['read', 'write'])),
                rate_limit=data.get('rate_limit', 1000),
                expires_days=data.get('expires_days')
            )

            return jsonify({'api_key': key})

        @self.bp.route('/keys/<key_hash>', methods=['DELETE'])
        def revoke_key(key_hash):
            """Revoke an API key"""
            if not self.auth_manager:
                return jsonify({'error': 'Auth not enabled'}), 400

            # This is simplified - in production you'd verify the key_hash
            return jsonify({'status': 'revoked'})

        @self.bp.route('/config', methods=['GET'])
        def get_config():
            """Get current configuration"""
            return jsonify(self._get_config())

        @self.bp.route('/config', methods=['POST'])
        def update_config():
            """Update configuration (hot reload)"""
            updates = request.json
            result = self._update_config(updates)
            return jsonify(result)

        @self.bp.route('/emergency/pause', methods=['POST'])
        def emergency_pause():
            """Pause message processing"""
            # Implementation would set a flag that processing loop checks
            return jsonify({'status': 'paused'})

        @self.bp.route('/emergency/resume', methods=['POST'])
        def emergency_resume():
            """Resume message processing"""
            return jsonify({'status': 'resumed'})

        @self.bp.route('/emergency/clear', methods=['POST'])
        def emergency_clear():
            """Clear all queues (emergency only)"""
            # Clear in-memory queue
            # Clear pending acks
            return jsonify({'status': 'cleared'})

    def _get_health_status(self):
        """Get comprehensive health status"""
        uptime = time.time() - self.start_time

        # System resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health = {
            'status': 'healthy',
            'uptime_seconds': uptime,
            'timestamp': datetime.now(timezone.utc).isoformat(),

            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent
            },

            'checks': {
                'memory': 'ok' if memory.percent < 90 else 'warning',
                'cpu': 'ok' if cpu_percent < 80 else 'warning',
                'disk': 'ok' if disk.percent < 90 else 'warning',
            }
        }

        # Overall status
        if any(v == 'warning' for v in health['checks'].values()):
            health['status'] = 'degraded'

        return health

    def _get_prometheus_metrics(self):
        """Generate Prometheus-compatible metrics"""
        uptime = time.time() - self.start_time

        metrics = []

        # Uptime
        metrics.append('# HELP bridge_uptime_seconds Server uptime in seconds')
        metrics.append('# TYPE bridge_uptime_seconds gauge')
        metrics.append(f'bridge_uptime_seconds {uptime}')

        # System metrics
        metrics.append('# HELP bridge_cpu_percent CPU usage percentage')
        metrics.append('# TYPE bridge_cpu_percent gauge')
        metrics.append(f'bridge_cpu_percent {psutil.cpu_percent(interval=0.1)}')

        metrics.append('# HELP bridge_memory_percent Memory usage percentage')
        metrics.append('# TYPE bridge_memory_percent gauge')
        metrics.append(f'bridge_memory_percent {psutil.virtual_memory().percent}')

        # Database metrics
        if self.message_store:
            stats = self.message_store.get_stats()

            metrics.append('# HELP bridge_messages_total Total messages')
            metrics.append('# TYPE bridge_messages_total counter')
            metrics.append(f'bridge_messages_total {stats["total_messages"]}')

            metrics.append('# HELP bridge_delivery_rate Message delivery rate')
            metrics.append('# TYPE bridge_delivery_rate gauge')
            metrics.append(f'bridge_delivery_rate {stats["delivery_rate"]}')

        return '\n'.join(metrics)

    def _get_connections(self):
        """Get active connections"""
        # This would integrate with the actual connection tracker
        return {
            'active': 0,
            'by_client': {},
            'total_connected': 0
        }

    def _disconnect_client(self, client_id: str):
        """Disconnect a client"""
        # Implementation would close WebSocket connections
        return {'status': 'disconnected', 'client_id': client_id}

    def _query_messages(self):
        """Admin query for messages"""
        if not self.message_store:
            return {'error': 'Persistence not enabled'}

        to_client = request.args.get('to')
        from_client = request.args.get('from')
        msg_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))

        messages = self.message_store.get_messages(
            to_client=to_client,
            from_client=from_client,
            msg_type=msg_type,
            limit=limit
        )

        return {
            'messages': messages,
            'count': len(messages)
        }

    def _get_statistics(self):
        """Get detailed statistics"""
        stats = {
            'uptime': time.time() - self.start_time,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if self.message_store:
            stats['database'] = self.message_store.get_stats()

        if self.auth_manager:
            stats['auth'] = {
                'total_keys': len(self.auth_manager.keys),
                'active_keys': sum(1 for k in self.auth_manager.keys.values() if k.get('active', True))
            }

        return stats

    def _get_config(self):
        """Get current configuration"""
        return {
            'auth_enabled': self.auth_manager is not None,
            'persistence_enabled': self.message_store is not None,
            'version': '1.1.0'
        }

    def _update_config(self, updates):
        """Update configuration"""
        # This would update runtime config
        return {'status': 'updated', 'changes': updates}


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    from flask import Flask

    app = Flask(__name__)

    # Add admin API
    admin = AdminAPI(app)

    print("="*70)
    print("🔧 Admin API Endpoints:")
    print("="*70)

    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('admin'):
            methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
            print(f"{methods:8s} {rule.rule}")

    print("\nStarting test server on http://localhost:8080")
    print("Try: curl http://localhost:8080/admin/health")

    app.run(port=8080, debug=True)
