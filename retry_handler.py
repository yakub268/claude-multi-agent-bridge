#!/usr/bin/env python3
"""
Retry Handler with Exponential Backoff
Circuit breaker pattern for fault tolerance
"""
import time
import logging
from functools import wraps
from typing import Callable, Optional, Tuple
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents cascading failures by:
    - Opening circuit after threshold failures
    - Rejecting requests while open
    - Testing recovery in half-open state
    """

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 success_threshold: int = 2):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function through circuit breaker

        Raises:
            CircuitOpenError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit entering HALF_OPEN state")
            else:
                raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.success_threshold:
                self._close_circuit()
        else:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self._open_circuit()

        elif self.failure_count >= self.failure_threshold:
            self._open_circuit()

    def _open_circuit(self):
        """Open the circuit"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")

    def _close_circuit(self):
        """Close the circuit"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info("Circuit breaker CLOSED - recovered")

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt recovery"""
        if not self.last_failure_time:
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info("Circuit breaker manually RESET")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


def retry_with_backoff(max_retries: int = 3,
                       base_delay: float = 1.0,
                       max_delay: float = 60.0,
                       exponential_base: float = 2.0,
                       jitter: bool = True):
    """
    Decorator for retry with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff (2 = double each time)
        jitter: Add randomness to prevent thundering herd

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def unstable_function():
            # might fail randomly
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if attempt == max_retries:
                        # Final attempt failed
                        raise e

                    # Calculate backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (±25%)
                    if jitter:
                        import random
                        jitter_range = delay * 0.25
                        delay += random.uniform(-jitter_range, jitter_range)

                    logging.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """
    Decorator to wrap function with circuit breaker

    Example:
        breaker = CircuitBreaker(failure_threshold=5)

        @with_circuit_breaker(breaker)
        def api_call():
            # external API call
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Combined Retry + Circuit Breaker
# ============================================================================

class ResilientCaller:
    """
    Combines retry logic with circuit breaker

    Use this for external API calls, database connections, etc.
    """

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0):
        """
        Initialize resilient caller

        Args:
            max_retries: Retries per call
            base_delay: Initial retry delay
            failure_threshold: Failures before circuit opens
            recovery_timeout: Seconds before recovery attempt
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with retry + circuit breaker

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: If all retries failed
        """
        @retry_with_backoff(
            max_retries=self.max_retries,
            base_delay=self.base_delay
        )
        def wrapped():
            return self.circuit_breaker.call(func, *args, **kwargs)

        return wrapped()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("="*70)
    print("🧪 Retry + Circuit Breaker Test")
    print("="*70)

    # Simulated unreliable function
    call_count = 0

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    def unreliable_function():
        global call_count
        call_count += 1

        if call_count < 3:
            print(f"   ❌ Attempt {call_count} failed")
            raise ConnectionError("Service unavailable")

        print(f"   ✅ Attempt {call_count} succeeded")
        return "Success!"

    # Test retry
    print("\n📞 Testing retry with backoff...")
    try:
        result = unreliable_function()
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test circuit breaker
    print("\n📞 Testing circuit breaker...")
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=2)

    def failing_function():
        raise RuntimeError("Always fails")

    # Trigger circuit opening
    for i in range(5):
        try:
            breaker.call(failing_function)
        except RuntimeError:
            print(f"   Attempt {i+1}: Failed (expected)")
        except CircuitOpenError:
            print(f"   Attempt {i+1}: Circuit OPEN (blocked)")

    # Wait for recovery
    print("\n⏳ Waiting 2s for recovery...")
    time.sleep(2)

    try:
        breaker.call(failing_function)
    except RuntimeError:
        print("   ✅ Circuit attempted recovery (HALF_OPEN)")

    print(f"\n📊 Final state: {breaker.state.value}")
