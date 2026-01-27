"""
Linear Webhook Receiver

Handles Linear webhook events with circuit breaker and DLQ support.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import logging
import os
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..core.circuit_breaker import CircuitBreaker
from ..core.dlq_handler import write_to_dlq
from ..core.linear_webhook import get_webhook_secret, verify_signature
from ..core import github_webhook
from ..core.saga_orchestrator import SagaOrchestrator
from ..core.metrics import (
    record_circuit_breaker_state,
    record_circuit_breaker_transition,
    record_dlq_message,
    record_webhook_request,
    set_service_info,
)

logger = logging.getLogger(__name__)

from ..config import get_settings

# Initialize circuit breaker
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "300"))

circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
    timeout_seconds=CIRCUIT_BREAKER_TIMEOUT,
    name="linear_webhook",
)

github_circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
    timeout_seconds=CIRCUIT_BREAKER_TIMEOUT,
    name="github_webhook",
)

settings = get_settings()
# Use raw_db_url but ensure it's compatible with asyncpg pure (no +asyncpg) if needed
# Actually SagaOrchestrator takes postgres_dsn. If raw_db_url has +asyncpg, asyncpg might strictly require postgresql://
# The app's ConversationIngestor does a replace on line 48: .replace("postgresql+asyncpg", "postgresql")
# We should replicate that safety or fix it in SagaOrchestrator.
# Looking at SagaOrchestrator (viewed earlier), it just takes dsn.
# Let's clean the DSN here to be safe.
clean_dsn = settings.raw_db_url.replace("postgresql+asyncpg", "postgresql")
saga = SagaOrchestrator(postgres_dsn=clean_dsn)

router = APIRouter(tags=["webhook"])


@router.post("/webhook/linear", status_code=status.HTTP_202_ACCEPTED)
async def receive_linear_webhook(request: Request) -> Dict[str, Any]:
    """
    Receive and process Linear webhook events.

    Validates signature using HMAC-SHA256, checks circuit breaker state,
    processes payload, and writes to DLQ on failure. Returns HTTP 202
    on successful acceptance, 401 on signature failure, and 503 when
    circuit breaker is open.

    Args:
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: Response with correlation ID and status

    Raises:
        HTTPException: 401 for invalid signature, 503 for circuit open
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Extract headers
        signature = request.headers.get("Linear-Signature", "")
        request_id = request.headers.get("X-Request-ID", correlation_id)

        logger.info(
            "Linear webhook received",
            extra={
                "correlation_id": correlation_id,
                "request_id": request_id,
                "signature_present": bool(signature),
            },
        )

        # Check circuit breaker state
        if not circuit_breaker.is_closed():
            cb_status = circuit_breaker.get_status()
            logger.warning(
                "Circuit breaker is OPEN, rejecting request",
                extra={
                    "correlation_id": correlation_id,
                    "circuit_breaker_status": cb_status,
                },
            )

            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/linear",
                status="503",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service Unavailable",
                    "message": "Circuit breaker is open",
                    "correlation_id": correlation_id,
                    "circuit_breaker": cb_status,
                },
            )

        # Read payload
        try:
            payload_bytes = await request.body()
            payload = await request.json()
        except Exception as e:
            logger.error(
                "Failed to read webhook payload",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

            circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/linear",
                status="400",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Bad Request",
                    "message": "Invalid payload format",
                    "correlation_id": correlation_id,
                },
            )

        # Begin saga transaction
        await saga.begin_transaction(payload)

        # Verify signature
        try:
            secret = get_webhook_secret()
        except Exception as e:
            logger.error(f"Error retrieving user secret: {e}", exc_info=True)
            secret = None

        if not secret:
            logger.error(
                "LINEAR_WEBHOOK_SECRET not configured",
                extra={"correlation_id": correlation_id},
            )

            circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/linear",
                status="500",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal Server Error",
                    "message": "Webhook secret not configured",
                    "correlation_id": correlation_id,
                },
            )

        if not verify_signature(payload_bytes, signature, secret):
            logger.warning(
                "Invalid webhook signature",
                extra={
                    "correlation_id": correlation_id,
                    "signature": signature[:16] + "...",
                },
            )

            circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/linear",
                status="401",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Unauthorized",
                    "message": "Invalid webhook signature",
                    "correlation_id": correlation_id,
                },
            )

        # Process webhook payload
        result = await _process_webhook_payload(payload, correlation_id)
        await saga.commit_transaction(payload)

        # Record success
        circuit_breaker.record_success()
        duration_seconds = time.time() - start_time

        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="202",
            duration_seconds=duration_seconds,
        )

        logger.info(
            "Webhook processed successfully",
            extra={
                "correlation_id": correlation_id,
                "duration_seconds": duration_seconds,
            },
        )

        return {
            "status": "accepted",
            "correlation_id": correlation_id,
            "message": "Webhook received and queued for processing",
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(
            "Failed to process webhook payload",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        # Write to DLQ
        if clean_dsn:
            try:
                if 'payload' in locals():
                    dlq_id = await write_to_dlq(
                        payload=payload,
                        error_message=str(e),
                        correlation_id=correlation_id,
                        postgres_dsn=clean_dsn,
                    )

                    if dlq_id:
                        record_dlq_message(service="ingest-llm")
                        logger.info(
                            "Payload written to DLQ",
                            extra={
                                "correlation_id": correlation_id,
                                "dlq_id": dlq_id,
                            },
                        )
            except Exception as dlq_error:
                 logger.error(f"Failed to write to DLQ: {dlq_error}")

        # Record failure
        circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="500",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": f"Failed to process webhook: {str(e)}",
                "correlation_id": correlation_id,
            },
        )


@router.post("/webhook/github", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(request: Request) -> Dict[str, Any]:
    """
    Receive and process GitHub webhook events.

    Validates signature using HMAC-SHA256, checks circuit breaker state,
    processes payload, and writes to DLQ on failure. Returns HTTP 202
    on successful acceptance, 401 on signature failure, and 503 when
    circuit breaker is open.

    Args:
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: Response with correlation ID and status

    Raises:
        HTTPException: 401 for invalid signature, 503 for circuit open
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Extract headers
        signature = request.headers.get("X-Hub-Signature-256", "")
        request_id = request.headers.get("X-GitHub-Delivery", correlation_id)

        logger.info(
            "GitHub webhook received",
            extra={
                "correlation_id": correlation_id,
                "request_id": request_id,
                "signature_present": bool(signature),
            },
        )

        # Check circuit breaker state
        if not github_circuit_breaker.is_closed():
            cb_status = github_circuit_breaker.get_status()
            logger.warning(
                "GitHub Circuit breaker is OPEN, rejecting request",
                extra={
                    "correlation_id": correlation_id,
                    "circuit_breaker_status": cb_status,
                },
            )

            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/github",
                status="503",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service Unavailable",
                    "message": "Circuit breaker is open",
                    "correlation_id": correlation_id,
                    "circuit_breaker": cb_status,
                },
            )

        # Read payload
        try:
            payload_bytes = await request.body()
            payload = await request.json()
        except Exception as e:
            logger.error(
                "Failed to read GitHub webhook payload",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

            github_circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/github",
                status="400",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Bad Request",
                    "message": "Invalid payload format",
                    "correlation_id": correlation_id,
                },
            )

        # Begin saga transaction
        await saga.begin_transaction(payload)

        # Verify signature
        try:
            secret = github_webhook.get_webhook_secret()
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}", exc_info=True)
            secret = None

        if not secret:
            logger.error(
                "GITHUB_WEBHOOK_SECRET not configured",
                extra={"correlation_id": correlation_id},
            )

            github_circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/github",
                status="500",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal Server Error",
                    "message": "Webhook secret not configured",
                    "correlation_id": correlation_id,
                },
            )

        if not github_webhook.verify_signature(payload_bytes, signature, secret):
            logger.warning(
                "Invalid GitHub webhook signature",
                extra={
                    "correlation_id": correlation_id,
                    "signature": signature[:16] + "...",
                },
            )

            github_circuit_breaker.record_failure()
            record_webhook_request(
                service="ingest-llm",
                endpoint="/webhook/github",
                status="401",
                duration_seconds=time.time() - start_time,
            )

            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Unauthorized",
                    "message": "Invalid webhook signature",
                    "correlation_id": correlation_id,
                },
            )

        # Process webhook payload
        await _process_github_webhook_payload(payload, correlation_id)
        await saga.commit_transaction(payload)

        # Record success
        github_circuit_breaker.record_success()
        duration_seconds = time.time() - start_time

        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/github",
            status="202",
            duration_seconds=duration_seconds,
        )

        logger.info(
            "GitHub Webhook processed successfully",
            extra={
                "correlation_id": correlation_id,
                "duration_seconds": duration_seconds,
            },
        )

        return {
            "status": "accepted",
            "correlation_id": correlation_id,
            "message": "Webhook received and queued for processing",
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(
            "Failed to process GitHub webhook payload",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        # Write to DLQ
        if clean_dsn:
            try:
                # Need to handle potential UnboundLocalError for payload if reading failed totally
                # But we caught reading error earlier, so payload exists if we got here?
                # Actually if reading failed we raised HTTPException, so we are safe.
                # However, if 'payload' is not defined (e.g. error before reading), we need check.
                if 'payload' in locals():
                    dlq_id = await write_to_dlq(
                        payload=payload,
                        error_message=str(e),
                        correlation_id=correlation_id,
                        postgres_dsn=clean_dsn,
                    )

                    if dlq_id:
                        record_dlq_message(service="ingest-llm")
                        logger.info(
                            "Payload written to DLQ",
                            extra={
                                "correlation_id": correlation_id,
                                "dlq_id": dlq_id,
                            },
                        )
            except Exception as dlq_error:
                logger.error(f"Failed to write to DLQ: {dlq_error}")

        # Record failure
        github_circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/github",
            status="500",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": f"Failed to process webhook: {str(e)}",
                "correlation_id": correlation_id,
            },
        )



async def _process_webhook_payload(
    payload: Dict[str, Any],
    correlation_id: str,
) -> None:
    """
    Process Linear webhook payload.

    Extracts event type and data, then writes to Neo4j database.
    This is a placeholder for actual processing logic.

    Args:
        payload: Linear webhook payload
        correlation_id: Request correlation ID for tracing

    Raises:
        Exception: If processing fails
    """
    event_type = payload.get("type", "unknown")
    action = payload.get("action", "unknown")
    data = payload.get("data", {})

    logger.info(
        "Processing Linear webhook event",
        extra={
            "correlation_id": correlation_id,
            "event_type": event_type,
            "action": action,
        },
    )

    # TODO: Implement actual Neo4j write logic
    # This will be implemented in TN-100.3

    logger.debug(
        "Webhook payload data",
        extra={
            "correlation_id": correlation_id,
            "event_type": event_type,
            "data_keys": list(data.keys()),
        },
    )


async def _process_github_webhook_payload(
    payload: Dict[str, Any],
    correlation_id: str,
) -> None:
    """
    Process GitHub webhook payload.

    Args:
        payload: GitHub webhook payload
        correlation_id: Request correlation ID for tracing

    Raises:
        Exception: If processing fails
    """
    # Look for X-GitHub-Event header which is not in payload usually,
    # but strictly speaking we might want to pass it down.
    # For now, just logging basic info.

    logger.info(
        "Processing GitHub webhook event",
        extra={
            "correlation_id": correlation_id,
            "payload_keys": list(payload.keys()),
        },
    )

