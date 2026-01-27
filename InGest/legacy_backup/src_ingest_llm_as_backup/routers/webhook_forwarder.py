"""
Linear Webhook Forwarder Shim

Temporary proxy that forwards Linear webhooks to the ingest-llm service.
This shim will be removed once DNS routing is configured.

Phase: TN-LINEAR-06 - Webhook Ingestion
"""

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..config import get_settings
from ..observability.logging import get_logger


logger = get_logger(__name__)


class ForwarderSettings(BaseSettings):
    """Settings for the webhook forwarder."""

    ingest_llm_url: str = Field(
        default="http://ingest-llm:8000",
        description="URL of the ingest-llm service to forward webhooks to",
    )
    forwarder_timeout: int = Field(
        default=5,
        description="Timeout in seconds for forwarding requests",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FORWARDER_",
        extra="ignore",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


def get_forwarder_settings() -> ForwarderSettings:
    """
    Get forwarder settings instance.

    Returns:
        ForwarderSettings: The forwarder configuration.
    """
    return ForwarderSettings()


router = APIRouter(prefix="/webhook", tags=["webhook-forwarder"])


@router.post("/linear", status_code=status.HTTP_202_ACCEPTED)
async def forward_linear_webhook(request: Request) -> dict:
    """
    Forward Linear webhook to the ingest-llm service.

    This endpoint acts as a temporary proxy, forwarding webhooks to the
    ingest-llm service. It handles connection errors and returns
    HTTP 503 when the ingest-llm service is unavailable.

    Args:
        request: The incoming FastAPI request.

    Returns:
        dict: Response indicating the forwarding result.

    Raises:
        HTTPException: If forwarding fails or ingest-llm is unavailable.
    """
    settings = get_forwarder_settings()
    ingest_settings = get_settings()

    # Generate correlation ID for tracing
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    logger.info(
        "Forwarding Linear webhook",
        extra={
            "correlation_id": correlation_id,
            "service": "webhook-forwarder",
            "target_url": settings.ingest_llm_url,
        },
    )

    # Read request body
    body = await request.body()

    # Prepare headers for forwarding
    headers = {
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "X-Correlation-ID": correlation_id,
        "Linear-Signature": request.headers.get("Linear-Signature", ""),
    }

    # Forward to ingest-llm service
    try:
        async with httpx.AsyncClient(timeout=settings.forwarder_timeout) as client:
            response = await client.post(
                f"{settings.ingest_llm_url}/webhook/linear",
                content=body,
                headers=headers,
            )

            if response.status_code == status.HTTP_202_ACCEPTED:
                logger.info(
                    "Webhook forwarded successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "service": "webhook-forwarder",
                        "status_code": response.status_code,
                    },
                )
                return {
                    "status": "forwarded",
                    "correlation_id": correlation_id,
                    "message": "Webhook forwarded to ingest-llm service",
                }
            else:
                logger.warning(
                    "Ingest-llm service returned unexpected status",
                    extra={
                        "correlation_id": correlation_id,
                        "service": "webhook-forwarder",
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ingest-llm service returned status {response.status_code}",
                )

    except httpx.TimeoutException:
        logger.error(
            "Timeout forwarding webhook to ingest-llm service",
            extra={
                "correlation_id": correlation_id,
                "service": "webhook-forwarder",
                "timeout": settings.forwarder_timeout,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingest-llm service timeout. Service may be unavailable.",
        )

    except httpx.ConnectError as e:
        logger.error(
            "Connection error forwarding webhook to ingest-llm service",
            extra={
                "correlation_id": correlation_id,
                "service": "webhook-forwarder",
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to ingest-llm service. Service may be unavailable.",
        )

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error forwarding webhook to ingest-llm service",
            extra={
                "correlation_id": correlation_id,
                "service": "webhook-forwarder",
                "status_code": e.response.status_code,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ingest-llm service returned error: {str(e)}",
        )

    except Exception as e:
        logger.error(
            "Unexpected error forwarding webhook",
            extra={
                "correlation_id": correlation_id,
                "service": "webhook-forwarder",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error forwarding webhook: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def forwarder_health() -> dict:
    """
    Health check endpoint for the webhook forwarder.

    Returns:
        dict: Health status of the forwarder.
    """
    settings = get_forwarder_settings()

    return {
        "service": "webhook-forwarder",
        "status": "healthy",
        "target_url": settings.ingest_llm_url,
        "timeout_seconds": settings.forwarder_timeout,
    }
