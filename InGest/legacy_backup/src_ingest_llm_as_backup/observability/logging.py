"""Logging helpers.

The project is intentionally removing the observability stack (OTel/Prometheus/
Langfuse/structlog) for now.

This module keeps the *same* helper functions used across the codebase, but
backs them with Python's standard library :mod:`logging`.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Optional


_configured = False


def setup_logging(log_level: str = "INFO") -> None:
    """Configure stdlib logging.

    Called lazily by :func:`get_logger`.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str = __name__) -> logging.Logger:
    """Get a logger instance.

    We intentionally avoid any structured logging dependencies right now.
    """
    setup_logging()
    return logging.getLogger(name)


def log_ingestion_start(
    logger: logging.Logger,
    ingestion_id: str,
    content_type: str,
    content_size: int,
    metadata: Dict[str, Any] = None,
):
    """Log the start of an ingestion operation."""
    logger.info(
        "Ingestion started | ingestion_id=%s content_type=%s content_size=%s metadata=%s",
        ingestion_id,
        content_type,
        content_size,
        metadata or {},
    )


def log_ingestion_complete(
    logger: logging.Logger,
    ingestion_id: str,
    status: str,
    duration_ms: int,
    chunks_processed: int = 0,
    memory_tier: str = "semantic",
    error_message: Optional[str] = None,
):
    """Log the completion of an ingestion operation."""
    msg = (
        "Ingestion complete | ingestion_id=%s status=%s duration_ms=%s "
        "chunks_processed=%s memory_tier=%s error=%s"
    )
    if status == "completed":
        logger.info(
            msg,
            ingestion_id,
            status,
            duration_ms,
            chunks_processed,
            memory_tier,
            error_message,
        )
    else:
        logger.error(
            msg,
            ingestion_id,
            status,
            duration_ms,
            chunks_processed,
            memory_tier,
            error_message,
        )


def log_memos_request(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Log a request to memOS.as service."""
    msg = (
        "memOS request | method=%s endpoint=%s status_code=%s duration_ms=%s "
        "request_size=%s response_size=%s error=%s"
    )
    if 200 <= status_code < 400:
        logger.info(
            msg,
            method,
            endpoint,
            status_code,
            duration_ms,
            request_size,
            response_size,
            error_message,
        )
    else:
        logger.error(
            msg,
            method,
            endpoint,
            status_code,
            duration_ms,
            request_size,
            response_size,
            error_message,
        )


def log_content_processing(
    logger: logging.Logger,
    operation: str,
    content_size: int,
    chunks_created: int = 0,
    processing_time_ms: int = 0,
    metadata: Dict[str, Any] = None,
):
    """Log content processing operations."""
    logger.info(
        "Content processing | operation=%s content_size=%s chunks_created=%s processing_time_ms=%s metadata=%s",
        operation,
        content_size,
        chunks_created,
        processing_time_ms,
        metadata or {},
    )


def log_health_check(
    logger: logging.Logger,
    service: str,
    status: str,
    response_time_ms: int,
    details: Dict[str, Any] = None,
):
    """Log health check results."""
    logger.info(
        "Health check | target_service=%s status=%s response_time_ms=%s details=%s",
        service,
        status,
        response_time_ms,
        details or {},
    )


class IngestionContextFilter:
    """Context filter for ingestion-specific logging."""

    def __init__(self, ingestion_id: str):
        self.ingestion_id = ingestion_id

    def __enter__(self):
        # No structured context binding while observability stack is removed.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None
