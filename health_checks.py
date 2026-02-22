#!/usr/bin/env python3
"""
Health Check System for Multi-Agent Bridge
Kubernetes-style liveness and readiness probes
"""
from flask import Blueprint, jsonify
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import time
import psutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """
    Individual health check

    Example:
        def check_database():
            try:
                db.execute("SELECT 1")
                return True, "Database responsive"
            except Exception as e:
                logger.error(f"Database check failed: {e}")
                return False, "Database connection failed"

        check = HealthCheck(
            name="database",
            check_func=check_database,
            critical=True
        )
    """
    name: str
    check_func: Callable[[], tuple]  # Returns (bool, str)
    critical: bool = True
    timeout: float = 5.0
    enabled: bool = True


class HealthCheckManager:
    """
    Manage health checks for liveness and readiness

    Kubernetes Integration:
        livenessProbe:
          httpGet:
            path: /health/live
            port: 5001
          initialDelaySeconds: 10
          periodSeconds: 30

        readinessProbe:
          httpGet:
            path: /health/ready
            port: 5001
          initialDelaySeconds: 5
          periodSeconds: 10
    """

    def __init__(self, app=None):
        self.liveness_checks: List[HealthCheck] = []
        self.readiness_checks: List[HealthCheck] = []
        self.start_time = time.time()
        self.last_check_results = {}

        # Register built-in checks
        self._register_builtin_checks()

        if app:
            self.register_routes(app)

    def _register_builtin_checks(self):
        """Register default health checks"""

        # System resources check
        def check_system_resources():
            """Check CPU and memory are not maxed out"""
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            if cpu > 95:
                return False, f"CPU at {cpu}%"
            if memory.percent > 95:
                return False, f"Memory at {memory.percent}%"

            return True, f"CPU: {cpu}%, Memory: {memory.percent}%"

        self.add_liveness_check(HealthCheck(
            name="system_resources",
            check_func=check_system_resources,
            critical=True
        ))

        # Disk space check
        def check_disk_space():
            """Check disk space available"""
            disk = psutil.disk_usage('/')

            if disk.percent > 95:
                return False, f"Disk at {disk.percent}%"

            return True, f"Disk: {disk.percent}%"

        self.add_liveness_check(HealthCheck(
            name="disk_space",
            check_func=check_disk_space,
            critical=False  # Warning only
        ))

    def add_liveness_check(self, check: HealthCheck):
        """
        Add liveness check

        Liveness checks determine if the application should be restarted.
        Examples: deadlocks, infinite loops, corrupted state
        """
        self.liveness_checks.append(check)

    def add_readiness_check(self, check: HealthCheck):
        """
        Add readiness check

        Readiness checks determine if the application can handle traffic.
        Examples: database connection, external API availability
        """
        self.readiness_checks.append(check)

    def check_liveness(self) -> Dict:
        """
        Execute liveness checks

        Returns:
            {
                'status': 'healthy' | 'unhealthy',
                'checks': {...},
                'uptime': seconds
            }
        """
        results = self._run_checks(self.liveness_checks)

        # Any critical check failing = unhealthy
        critical_failures = [
            name for name, result in results['checks'].items()
            if not result['passed'] and result['critical']
        ]

        status = 'unhealthy' if critical_failures else 'healthy'

        return {
            'status': status,
            'checks': results['checks'],
            'uptime': time.time() - self.start_time,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def check_readiness(self) -> Dict:
        """
        Execute readiness checks

        Returns:
            {
                'status': 'ready' | 'not_ready',
                'checks': {...}
            }
        """
        results = self._run_checks(self.readiness_checks)

        # Any critical check failing = not ready
        critical_failures = [
            name for name, result in results['checks'].items()
            if not result['passed'] and result['critical']
        ]

        status = 'not_ready' if critical_failures else 'ready'

        return {
            'status': status,
            'checks': results['checks'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _run_checks(self, checks: List[HealthCheck]) -> Dict:
        """Run a list of health checks"""
        check_results = {}

        for check in checks:
            if not check.enabled:
                continue

            start = time.time()

            try:
                passed, message = check.check_func()
                duration = time.time() - start

                check_results[check.name] = {
                    'passed': passed,
                    'message': message,
                    'duration': duration,
                    'critical': check.critical
                }

            except Exception as e:
                duration = time.time() - start

                check_results[check.name] = {
                    'passed': False,
                    'message': f"Check failed: {str(e)}",
                    'duration': duration,
                    'critical': check.critical
                }

        self.last_check_results = check_results

        return {
            'checks': check_results,
            'total': len(checks),
            'passed': sum(1 for r in check_results.values() if r['passed']),
            'failed': sum(1 for r in check_results.values() if not r['passed'])
        }

    def register_routes(self, app):
        """Register health check routes on Flask app"""
        bp = Blueprint('health', __name__, url_prefix='/health')

        @bp.route('/live', methods=['GET'])
        def liveness_probe():
            """
            Liveness probe endpoint

            Returns 200 if healthy, 503 if unhealthy.
            Used by Kubernetes to restart unhealthy pods.
            """
            result = self.check_liveness()

            status_code = 200 if result['status'] == 'healthy' else 503

            return jsonify(result), status_code

        @bp.route('/ready', methods=['GET'])
        def readiness_probe():
            """
            Readiness probe endpoint

            Returns 200 if ready, 503 if not ready.
            Used by Kubernetes to route traffic only to ready pods.
            """
            result = self.check_readiness()

            status_code = 200 if result['status'] == 'ready' else 503

            return jsonify(result), status_code

        @bp.route('/startup', methods=['GET'])
        def startup_probe():
            """
            Startup probe endpoint

            Returns 200 once application is fully initialized.
            Delays liveness/readiness checks until startup complete.
            """
            uptime = time.time() - self.start_time

            # Consider started after 5 seconds
            started = uptime > 5

            return jsonify({
                'status': 'started' if started else 'starting',
                'uptime': uptime
            }), 200 if started else 503

        @bp.route('/status', methods=['GET'])
        def health_status():
            """
            Combined health status

            Returns detailed status of all checks.
            """
            liveness = self.check_liveness()
            readiness = self.check_readiness()

            overall_status = 'healthy'
            if liveness['status'] == 'unhealthy':
                overall_status = 'unhealthy'
            elif readiness['status'] == 'not_ready':
                overall_status = 'degraded'

            return jsonify({
                'status': overall_status,
                'liveness': liveness,
                'readiness': readiness
            })

        app.register_blueprint(bp)


# ============================================================================
# Common Health Check Functions
# ============================================================================

class CommonChecks:
    """Pre-built health check functions"""

    @staticmethod
    def database_check(db_connection):
        """Check database connectivity"""
        def check():
            try:
                db_connection.execute("SELECT 1")
                return True, "Database responsive"
            except Exception as e:
                return False, f"Database error: {str(e)}"
        return check

    @staticmethod
    def redis_check(redis_client):
        """Check Redis connectivity"""
        def check():
            try:
                redis_client.ping()
                return True, "Redis responsive"
            except Exception as e:
                return False, f"Redis error: {str(e)}"
        return check

    @staticmethod
    def external_api_check(url: str, timeout: int = 5):
        """Check external API availability"""
        def check():
            import requests
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code < 500:
                    return True, f"API responsive ({response.status_code})"
                else:
                    return False, f"API error {response.status_code}"
            except Exception as e:
                return False, f"API unreachable: {str(e)}"
        return check

    @staticmethod
    def message_queue_check(queue):
        """Check message queue is not backed up"""
        def check():
            size = queue.qsize()
            max_size = queue.maxsize

            if size > max_size * 0.9:
                return False, f"Queue nearly full ({size}/{max_size})"

            return True, f"Queue size: {size}/{max_size}"
        return check

    @staticmethod
    def websocket_connections_check(max_connections: int = 100):
        """Check WebSocket connection count"""
        def check():
            # This would integrate with actual WebSocket tracker
            # Placeholder implementation
            active_connections = 0  # Get from WebSocket manager

            if active_connections > max_connections:
                return False, f"Too many connections: {active_connections}"

            return True, f"Connections: {active_connections}"
        return check

    @staticmethod
    def file_system_check(path: str, min_free_gb: float = 1.0):
        """Check file system has minimum free space"""
        def check():
            try:
                disk = psutil.disk_usage(path)
                free_gb = disk.free / (1024 ** 3)

                if free_gb < min_free_gb:
                    return False, f"Low disk space: {free_gb:.2f} GB"

                return True, f"Free space: {free_gb:.2f} GB"
            except Exception as e:
                return False, f"Filesystem error: {str(e)}"
        return check


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    from flask import Flask

    print("="*70)
    print("🏥 Health Check System Test")
    print("="*70)

    app = Flask(__name__)

    # Create health check manager
    health = HealthCheckManager(app)

    # Add custom liveness check
    def check_application_state():
        """Check application is not in corrupted state"""
        # Simulate check
        return True, "Application state OK"

    health.add_liveness_check(HealthCheck(
        name="application_state",
        check_func=check_application_state,
        critical=True
    ))

    # Add custom readiness check
    def check_external_service():
        """Check external service is available"""
        # Simulate check
        return True, "External service available"

    health.add_readiness_check(HealthCheck(
        name="external_service",
        check_func=check_external_service,
        critical=True
    ))

    # Add database check using helper
    def mock_db_execute(query):
        """Mock database"""
        return True

    class MockDB:
        execute = staticmethod(mock_db_execute)

    health.add_readiness_check(HealthCheck(
        name="database",
        check_func=CommonChecks.database_check(MockDB),
        critical=True
    ))

    # Print endpoints
    print("\n🔗 Health check endpoints:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('health'):
            methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
            print(f"   {methods:8s} {rule.rule}")

    # Test liveness
    print("\n🔍 Liveness check:")
    liveness = health.check_liveness()
    print(f"   Status: {liveness['status']}")
    print(f"   Uptime: {liveness['uptime']:.2f}s")
    for name, result in liveness['checks'].items():
        status = "✅" if result['passed'] else "❌"
        print(f"   {status} {name}: {result['message']}")

    # Test readiness
    print("\n🔍 Readiness check:")
    readiness = health.check_readiness()
    print(f"   Status: {readiness['status']}")
    for name, result in readiness['checks'].items():
        status = "✅" if result['passed'] else "❌"
        print(f"   {status} {name}: {result['message']}")

    print("\n✅ Test complete")
    print("\nTo test with server:")
    print("   python health_checks.py")
    print("   curl http://localhost:8080/health/live")
    print("   curl http://localhost:8080/health/ready")

    # Optionally run server
    # app.run(port=8080, debug=True)
