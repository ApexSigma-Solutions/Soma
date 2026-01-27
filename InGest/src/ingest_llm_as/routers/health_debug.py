"""
Ingest-LLM Health Router (SIMPLIFIED DEBUG VERSION)

Provides health check endpoints for ingest-llm service.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

from typing import Any, Dict

from fastapi import APIRouter, Response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Simple health check for debugging.
    """
    return {
        "status": "ok",
        "message": "Service is running (simplified version)",
    }


@router.get("/health-full")
async def health_check_full() -> Dict[str, Any]:
    """
    Full health check with database connectivity.
    """
    from ..core.circuit_breaker import CircuitBreaker
    from ..core.health_checker import verify_omega_connection

    circuit_breaker = CircuitBreaker()
    status = verify_omega_connection()
    cb_status = circuit_breaker.get_status()

    return {
        "status": "ok",
        "upstream": "ok",
        "neo4j": status,
        "circuit_breaker": cb_status,
    }


@router.get("/metrics")
async def metrics() -> Response:
    """
    Expose Prometheus metrics for scraping.
    """
    from prometheus_client import generate_latest
    from ..core.metrics import get_metrics_content_type

    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type(),
    )
