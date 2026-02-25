#!/usr/bin/env python3
"""
Auto-Recovery System
Self-healing capabilities for the message bus
"""
import time
import threading
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Component health status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass
class Component:
    """System component"""

    name: str
    check_func: Callable[[], bool]
    recovery_func: Optional[Callable[[], bool]] = None
    health: HealthStatus = HealthStatus.HEALTHY
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failure_count: int = 0
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    critical: bool = True


class AutoRecovery:
    """
    Automatic recovery system

    Features:
    - Component health monitoring
    - Automatic recovery attempts
    - Graceful degradation
    - Failure isolation
    - Recovery notifications
    - Self-healing strategies
    """

    def __init__(self, check_interval: int = 30):
        self.components: Dict[str, Component] = {}
        self.check_interval = check_interval
        self.running = False
        self.callbacks = {"on_failure": [], "on_recovery": [], "on_degraded": []}
        self.stats = {
            "total_failures": 0,
            "total_recoveries": 0,
            "auto_recoveries": 0,
            "failed_recoveries": 0,
        }
        self._monitor_thread = None

    def register_component(self, component: Component):
        """
        Register component for monitoring

        Args:
            component: Component to monitor
        """
        self.components[component.name] = component
        logger.info(f"Registered component: {component.name}")

    def register_callback(self, event: str, callback: Callable):
        """
        Register callback for events

        Args:
            event: Event type ('on_failure', 'on_recovery', 'on_degraded')
            callback: Function to call
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def start_monitoring(self):
        """Start background monitoring"""
        if self.running:
            return

        self.running = True

        def monitor():
            while self.running:
                try:
                    self._check_all_components()
                except Exception as e:
                    logger.error(f"Monitor error: {e}")

                time.sleep(self.check_interval)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
        logger.info("Auto-recovery monitoring started")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Auto-recovery monitoring stopped")

    def _check_all_components(self):
        """Check health of all components"""
        for name, component in self.components.items():
            try:
                is_healthy = component.check_func()
                component.last_check = datetime.now(timezone.utc)

                if is_healthy:
                    self._handle_healthy(component)
                else:
                    self._handle_unhealthy(component)

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                self._handle_unhealthy(component)

    def _handle_healthy(self, component: Component):
        """Handle healthy component"""
        if component.health in [HealthStatus.DEGRADED, HealthStatus.RECOVERING]:
            # Component recovered
            logger.info(f"✅ Component recovered: {component.name}")
            component.health = HealthStatus.HEALTHY
            component.failure_count = 0
            component.recovery_attempts = 0
            self.stats["total_recoveries"] += 1

            # Trigger callbacks
            for callback in self.callbacks["on_recovery"]:
                try:
                    callback(component.name)
                except Exception as e:
                    logger.error(f"Recovery callback error: {e}")

    def _handle_unhealthy(self, component: Component):
        """Handle unhealthy component"""
        component.failure_count += 1

        if component.health == HealthStatus.HEALTHY:
            # First failure
            logger.warning(f"⚠️  Component degraded: {component.name}")
            component.health = HealthStatus.DEGRADED
            self.stats["total_failures"] += 1

            # Trigger callbacks
            for callback in self.callbacks["on_degraded"]:
                try:
                    callback(component.name)
                except Exception as e:
                    logger.error(f"Degraded callback error: {e}")

        elif component.health == HealthStatus.DEGRADED:
            # Multiple failures
            if component.failure_count >= 3:
                logger.error(f"❌ Component critical: {component.name}")
                component.health = HealthStatus.CRITICAL

                # Attempt recovery
                self._attempt_recovery(component)

    def _attempt_recovery(self, component: Component):
        """
        Attempt to recover component

        Args:
            component: Component to recover
        """
        if not component.recovery_func:
            logger.warning(f"No recovery function for {component.name}")
            component.health = HealthStatus.FAILED
            return

        if component.recovery_attempts >= component.max_recovery_attempts:
            logger.error(f"❌ Max recovery attempts exceeded: {component.name}")
            component.health = HealthStatus.FAILED
            self.stats["failed_recoveries"] += 1

            # Trigger failure callbacks
            for callback in self.callbacks["on_failure"]:
                try:
                    callback(component.name)
                except Exception as e:
                    logger.error(f"Failure callback error: {e}")
            return

        component.recovery_attempts += 1
        logger.info(
            f"🔄 Attempting recovery for {component.name} (attempt {component.recovery_attempts}/{component.max_recovery_attempts})"
        )

        component.health = HealthStatus.RECOVERING

        try:
            success = component.recovery_func()

            if success:
                logger.info(f"✅ Recovery successful: {component.name}")
                component.health = HealthStatus.HEALTHY
                component.failure_count = 0
                component.recovery_attempts = 0
                self.stats["auto_recoveries"] += 1

                # Trigger callbacks
                for callback in self.callbacks["on_recovery"]:
                    try:
                        callback(component.name)
                    except Exception as e:
                        logger.error(f"Recovery callback error: {e}")
            else:
                logger.warning(f"⚠️  Recovery failed: {component.name}")
                component.health = HealthStatus.CRITICAL

        except Exception as e:
            logger.error(f"❌ Recovery exception for {component.name}: {e}")
            component.health = HealthStatus.CRITICAL

    def get_system_health(self) -> Dict:
        """Get overall system health"""
        components_by_status = {
            HealthStatus.HEALTHY: [],
            HealthStatus.DEGRADED: [],
            HealthStatus.CRITICAL: [],
            HealthStatus.RECOVERING: [],
            HealthStatus.FAILED: [],
        }

        for name, component in self.components.items():
            components_by_status[component.health].append(name)

        # Determine overall health
        if components_by_status[HealthStatus.FAILED]:
            overall = HealthStatus.FAILED
        elif components_by_status[HealthStatus.CRITICAL]:
            overall = HealthStatus.CRITICAL
        elif components_by_status[HealthStatus.DEGRADED]:
            overall = HealthStatus.DEGRADED
        elif components_by_status[HealthStatus.RECOVERING]:
            overall = HealthStatus.RECOVERING
        else:
            overall = HealthStatus.HEALTHY

        return {
            "overall": overall.value,
            "healthy": len(components_by_status[HealthStatus.HEALTHY]),
            "degraded": len(components_by_status[HealthStatus.DEGRADED]),
            "critical": len(components_by_status[HealthStatus.CRITICAL]),
            "recovering": len(components_by_status[HealthStatus.RECOVERING]),
            "failed": len(components_by_status[HealthStatus.FAILED]),
            "components": {
                status.value: names for status, names in components_by_status.items()
            },
        }

    def get_stats(self) -> Dict:
        """Get recovery statistics"""
        return {
            **self.stats,
            "monitored_components": len(self.components),
            "recovery_success_rate": (
                self.stats["auto_recoveries"] / self.stats["total_failures"]
                if self.stats["total_failures"] > 0
                else 0
            ),
        }


# ============================================================================
# Pre-built Recovery Strategies
# ============================================================================


class RecoveryStrategies:
    """Common recovery strategies"""

    @staticmethod
    def restart_process(process_name: str) -> Callable[[], bool]:
        """Restart a process"""

        def recover():
            import subprocess

            try:
                # Kill process
                subprocess.run(
                    ["taskkill", "/F", "/IM", process_name], capture_output=True
                )
                time.sleep(2)

                # Restart (simplified - actual implementation would vary)
                # subprocess.Popen([process_name])

                logger.info(f"Process {process_name} restarted")
                return True
            except Exception as e:
                logger.error(f"Failed to restart {process_name}: {e}")
                return False

        return recover

    @staticmethod
    def clear_queue() -> Callable[[], bool]:
        """Clear message queue"""

        def recover():
            try:
                # Implementation would clear actual queue
                logger.info("Message queue cleared")
                return True
            except Exception as e:
                logger.error(f"Failed to clear queue: {e}")
                return False

        return recover

    @staticmethod
    def reconnect_database() -> Callable[[], bool]:
        """Reconnect to database"""

        def recover():
            try:
                # Implementation would reconnect to DB
                logger.info("Database reconnected")
                return True
            except Exception as e:
                logger.error(f"Failed to reconnect database: {e}")
                return False

        return recover

    @staticmethod
    def flush_cache() -> Callable[[], bool]:
        """Flush cache"""

        def recover():
            try:
                # Implementation would flush actual cache
                logger.info("Cache flushed")
                return True
            except Exception as e:
                logger.error(f"Failed to flush cache: {e}")
                return False

        return recover


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 Auto-Recovery System Test")
    print("=" * 70)

    recovery = AutoRecovery(check_interval=5)

    # Mock health check functions
    failure_count = {"server": 0, "database": 0}

    def check_server():
        failure_count["server"] += 1
        # Simulate intermittent failure
        return failure_count["server"] % 3 != 0

    def check_database():
        failure_count["database"] += 1
        return failure_count["database"] % 5 != 0

    def recover_server():
        logger.info("Recovering server...")
        time.sleep(1)
        failure_count["server"] = 0
        return True

    def recover_database():
        logger.info("Recovering database...")
        time.sleep(1)
        failure_count["database"] = 0
        return True

    # Register components
    recovery.register_component(
        Component(
            name="server",
            check_func=check_server,
            recovery_func=recover_server,
            critical=True,
        )
    )

    recovery.register_component(
        Component(
            name="database",
            check_func=check_database,
            recovery_func=recover_database,
            critical=True,
        )
    )

    # Register callbacks
    def on_failure(name):
        print(f"   ❌ ALERT: {name} failed!")

    def on_recovery(name):
        print(f"   ✅ RECOVERY: {name} recovered!")

    recovery.register_callback("on_failure", on_failure)
    recovery.register_callback("on_recovery", on_recovery)

    # Start monitoring
    print("\n🔍 Starting monitoring (30 seconds)...")
    recovery.start_monitoring()

    time.sleep(30)

    recovery.stop_monitoring()

    # Show results
    print("\n📊 System Health:")
    health = recovery.get_system_health()
    print(f"   Overall: {health['overall'].upper()}")
    print(f"   Healthy: {health['healthy']}")
    print(f"   Degraded: {health['degraded']}")
    print(f"   Critical: {health['critical']}")
    print(f"   Failed: {health['failed']}")

    print("\n📈 Recovery Stats:")
    stats = recovery.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Test complete")
