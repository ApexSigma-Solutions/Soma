"""
Prometheus Metrics Integration

Exposes metrics for webhook processing and circuit breaker monitoring.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import logging

from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)

# Webhook request metrics
webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total number of webhook requests received",
    ["service", "endpoint", "status"],
)

webhook_processing_duration_seconds = Histogram(
    "webhook_processing_duration_seconds",
    "Time spent processing webhook requests",
    ["service", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Current circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service", "circuit_breaker"],
)

circuit_breaker_transitions_total = Counter(
    "circuit_breaker_transitions_total",
    "Total number of circuit breaker state transitions",
    ["service", "circuit_breaker", "from_state", "to_state"],
)

# Dead letter queue metrics
dlq_messages_total = Counter(
    "dlq_messages_total",
    "Total number of messages written to dead letter queue",
    ["service"],
)

# Service info
service_info = Info(
    "service_info",
    "Service information",
    ["service", "version"],
)


def record_webhook_request(
    service: str,
    endpoint: str,
    status: str,
    duration_seconds: float,
) -> None:
    """
    Record webhook request metrics.

    Args:
        service: Service name (e.g., "ingest-llm")
        endpoint: Endpoint path (e.g., "/webhook/linear")
        status: HTTP status code or error type
        duration_seconds: Request processing time in seconds
    """
    webhook_requests_total.labels(
        service=service,
        endpoint=endpoint,
        status=status,
    ).inc()
    webhook_processing_duration_seconds.labels(
        service=service,
        endpoint=endpoint,
    ).observe(duration_seconds)

    logger.debug(
        "Webhook request metrics recorded",
        extra={
            "service": service,
            "endpoint": endpoint,
            "status": status,
            "duration_seconds": duration_seconds,
        },
    )


def record_circuit_breaker_state(
    service: str,
    circuit_breaker: str,
    state: str,
) -> None:
    """
    Record circuit breaker state.

    Args:
        service: Service name
        circuit_breaker: Circuit breaker identifier
        state: Current state ("closed", "open", "half_open")
    """
    state_map = {"closed": 0, "open": 1, "half_open": 2}
    state_value = state_map.get(state, 0)

    circuit_breaker_state.labels(
        service=service,
        circuit_breaker=circuit_breaker,
    ).set(state_value)

    logger.debug(
        "Circuit breaker state recorded",
        extra={
            "service": service,
            "circuit_breaker": circuit_breaker,
            "state": state,
        },
    )


def record_circuit_breaker_transition(
    service: str,
    circuit_breaker: str,
    from_state: str,
    to_state: str,
) -> None:
    """
    Record circuit breaker state transition.

    Args:
        service: Service name
        circuit_breaker: Circuit breaker identifier
        from_state: Previous state
        to_state: New state
    """
    circuit_breaker_transitions_total.labels(
        service=service,
        circuit_breaker=circuit_breaker,
        from_state=from_state,
        to_state=to_state,
    ).inc()

    logger.info(
        "Circuit breaker transition recorded",
        extra={
            "service": service,
            "circuit_breaker": circuit_breaker,
            "from_state": from_state,
            "to_state": to_state,
        },
    )


def record_dlq_message(service: str) -> None:
    """
    Record dead letter queue message write.

    Args:
        service: Service name
    """
    dlq_messages_total.labels(service=service).inc()

    logger.debug(
        "DLQ message metric recorded",
        extra={"service": service},
    )


def set_service_info(service: str, version: str) -> None:
    """
    Set service information metrics.

    Args:
        service: Service name
        version: Service version
    """
    service_info.labels(service=service, version=version).info(
        {"version": version, "service": service}
    )


def get_metrics_content_type() -> str:
    """
    Get Prometheus metrics content type.

    Returns:
        str: Content-Type header value for metrics endpoint
    """
    return "text/plain; version=0.0.4"
