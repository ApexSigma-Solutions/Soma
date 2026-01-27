"""
Ingest-LLM Health Router

Provides health check endpoints for ingest-llm service.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import os
from typing import Any, Dict

from fastapi import APIRouter, Response
from prometheus_client import generate_latest

from ..core.circuit_breaker import CircuitBreaker
from ..core.health_checker import verify_omega_connection
from ..core.metrics import get_metrics_content_type, set_service_info
from ..core.saga_orchestrator import SagaOrchestrator

router = APIRouter(tags=["health"])

# Initialize circuit breaker
circuit_breaker = CircuitBreaker()

# Initialize service info (idempotent)
try:
    set_service_info(service="ingest-llm", version="1.0.0")
except ValueError:
    pass  # Already initialized

# Initialize Saga orchestrator with explicit postgres_dsn
postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://user:pass@postgres:5432/omega")
saga_orchestrator = SagaOrchestrator(postgres_dsn=postgres_dsn)


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Check health status of ingest-llm service and its dependencies.

    Verifies connectivity to upstream services, particularly Omega KG
    Neo4j database connection, and checks for stuck Saga transactions.
    Returns a comprehensive status report including circuit breaker
    state and Saga transaction health.

    Returns:
        Dict containing:
            - status: Overall service status ("ok", "degraded")
            - upstream: Upstream service status
            - neo4j: Connection status dictionary
            - circuit_breaker: Circuit breaker status and metrics
            - saga: Saga transaction status with stuck transaction count
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Health check requested")

    status = verify_omega_connection()
    logger.info(f"Neo4j status: {status}")

    cb_status = circuit_breaker.get_status()
    logger.info(f"Circuit breaker status: {cb_status}")

    if not status.get("neo4j_reachable", False):
        logger.warning("Neo4j not reachable, returning degraded status")
        return {
            "status": "degraded",
            "upstream": "error",
            "neo4j": status,
            "circuit_breaker": cb_status,
        }

    # Check for stuck Saga transactions (with timeout to avoid hanging)
    import asyncio

    logger.info("Checking for stuck Saga transactions...")
    try:
        stuck_count = await asyncio.wait_for(
            saga_orchestrator.get_stuck_transactions(),
            timeout=2.0,  # 2 second timeout
        )
        logger.info(f"Stuck transactions count: {stuck_count}")
    except asyncio.TimeoutError:
        # If PostgreSQL is unreachable, skip saga check
        logger.warning("Saga check timed out, skipping")
        stuck_count = 0
    except Exception as e:
        logger.error(f"Error checking stuck transactions: {e}")
        stuck_count = 0

    if stuck_count > 0:
        return {
            "status": "degraded",
            "upstream": "ok",
            "neo4j": status,
            "circuit_breaker": cb_status,
            "saga": {"stuck_transactions": stuck_count},
        }

    logger.info("Health check complete - status: OK")
    return {
        "status": "ok",
        "upstream": "ok",
        "neo4j": status,
        "circuit_breaker": cb_status,
        "saga": {"stuck_transactions": 0},
    }


@router.get("/metrics")
async def metrics() -> Response:
    """
    Expose Prometheus metrics for scraping.

    Returns Prometheus metrics in text format for scraping by
    Prometheus server.

    Returns:
        Response: Prometheus metrics in text/plain format
    """
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type(),
    )
