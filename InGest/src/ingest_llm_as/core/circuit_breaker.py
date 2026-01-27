"""
Circuit Breaker Implementation

Thread-safe circuit breaker pattern for fault tolerance in webhook processing.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation with state transitions.

    Tracks failure counts and implements automatic recovery after timeout.
    Trips to OPEN state after threshold failures, transitions to HALF_OPEN
    after timeout period, and returns to CLOSED on successful trial request.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_seconds: int = 300,
        name: str = "default",
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before tripping (default: 3)
            timeout_seconds: Seconds to wait before attempting recovery (default: 300)
            name: Circuit breaker identifier for logging
        """
        self._failure_threshold = failure_threshold
        self._timeout_seconds = timeout_seconds
        self._name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

        logger.info(
            "Circuit breaker initialized",
            extra={
                "circuit_breaker": name,
                "state": self._state.value,
                "failure_threshold": failure_threshold,
                "timeout_seconds": timeout_seconds,
            },
        )

    def record_failure(self) -> None:
        """
        Record a failure and update circuit state if threshold exceeded.

        Increments failure counter and transitions to OPEN state if threshold
        is reached or if in HALF_OPEN state (trial failure). Logs state
        transition with timestamp.
        """
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            # In HALF_OPEN state, any failure trips the circuit immediately
            if self._state == CircuitState.HALF_OPEN:
                previous_state = self._state.value
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker tripped to OPEN (HALF_OPEN failure)",
                    extra={
                        "circuit_breaker": self._name,
                        "previous_state": previous_state,
                        "new_state": self._state.value,
                        "failure_count": self._failure_count,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            elif self._failure_count >= self._failure_threshold:
                if self._state != CircuitState.OPEN:
                    previous_state = self._state.value
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker tripped to OPEN",
                        extra={
                            "circuit_breaker": self._name,
                            "previous_state": previous_state,
                            "new_state": self._state.value,
                            "failure_count": self._failure_count,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
            else:
                logger.warning(
                    "Failure recorded",
                    extra={
                        "circuit_breaker": self._name,
                        "state": self._state.value,
                        "failure_count": self._failure_count,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

    def record_success(self) -> None:
        """
        Record a success and reset circuit state.

        Resets failure counter and transitions from HALF_OPEN to CLOSED.
        Logs state transition with timestamp.
        """
        with self._lock:
            previous_state = self._state.value
            self._failure_count = 0
            self._last_failure_time = None

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(
                    "Circuit breaker recovered to CLOSED",
                    extra={
                        "circuit_breaker": self._name,
                        "previous_state": previous_state,
                        "new_state": self._state.value,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            else:
                logger.info(
                    "Success recorded",
                    extra={
                        "circuit_breaker": self._name,
                        "state": self._state.value,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

    def is_closed(self) -> bool:
        """
        Check if circuit is closed or should transition to HALF_OPEN.

        Returns True if circuit is CLOSED or if sufficient time has elapsed
        to transition from OPEN to HALF_OPEN state.

        Returns:
            bool: True if requests should be allowed, False otherwise
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._last_failure_time is None:
                    return False

                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._timeout_seconds:
                    previous_state = self._state.value
                    self._state = CircuitState.HALF_OPEN
                    logger.info(
                        "Circuit breaker transitioned to HALF_OPEN",
                        extra={
                            "circuit_breaker": self._name,
                            "previous_state": previous_state,
                            "new_state": self._state.value,
                            "elapsed_seconds": elapsed,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    return True

                return False

            # HALF_OPEN state - allow trial request
            return True

    def get_state(self) -> CircuitState:
        """
        Get current circuit breaker state.

        Automatically transitions from OPEN to HALF_OPEN if timeout has elapsed.
        Returns:
            CircuitState: Current state (CLOSED, OPEN, or HALF_OPEN)
        """
        with self._lock:
            # Check if we need to transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN and self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._timeout_seconds:
                    previous_state = self._state.value
                    self._state = CircuitState.HALF_OPEN
                    logger.info(
                        "Circuit breaker transitioned to HALF_OPEN",
                        extra={
                            "circuit_breaker": self._name,
                            "previous_state": previous_state,
                            "new_state": self._state.value,
                            "elapsed_seconds": elapsed,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
            return self._state

    def get_failure_count(self) -> int:
        """
        Get current failure count.

        Returns:
            int: Number of consecutive failures
        """
        with self._lock:
            return self._failure_count

    def get_status(self) -> dict:
        """
        Get comprehensive circuit breaker status.

        Returns:
            dict: Status information including state, failure count, and
                   time until recovery if applicable
        """
        with self._lock:
            # Ensure we check for timeout transition first
            current_state = self.get_state()

            status = {
                "name": self._name,
                "state": current_state.value,
                "is_closed": current_state == CircuitState.CLOSED,
                "failure_count": self._failure_count,
                "failure_threshold": self._failure_threshold,
                "timeout_seconds": self._timeout_seconds,
                "last_failure_time": (
                    datetime.fromtimestamp(self._last_failure_time).isoformat()
                    if self._last_failure_time
                    else None
                ),
            }

            if self._state == CircuitState.OPEN and self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                remaining = max(0, self._timeout_seconds - elapsed)
                status["seconds_until_half_open"] = remaining
                status["recovery_time"] = (
                    datetime.utcnow() + timedelta(seconds=remaining)
                ).isoformat()

            return status
