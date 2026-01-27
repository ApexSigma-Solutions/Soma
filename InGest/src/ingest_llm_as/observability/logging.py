"""Logging helpers backed by structlog.

This module provides structured logging capabilities used across the codebase.
It writes JSON logs to d:/projects/OmegaKG/logs/ingest_llm_as.json.log
and pretty prints to console.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

_configured = False


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog and stdlib logging."""
    global _configured
    if _configured:
        return

    log_dir = Path("d:/projects/OmegaKG/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    service_name = "ingest_llm_as"

    level = getattr(logging, log_level.upper(), logging.INFO)

    file_handler = logging.FileHandler(
        log_dir / f"{service_name}.json.log", encoding="utf-8"
    )
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Clean root logger
    logging.getLogger().handlers.clear()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Console Formatter
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)

    # JSON File Formatter
    def add_service_name(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors
        + [add_service_name, structlog.processors.dict_tracebacks],
    )
    json_file_handler = logging.FileHandler(
        log_dir / f"{service_name}.json.log", encoding="utf-8"
    )
    json_file_handler.setFormatter(json_formatter)
    json_file_handler.setLevel(level)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(json_file_handler)

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    setup_logging()
    return structlog.get_logger(name)


def log_ingestion_start(
    logger: Any,
    ingestion_id: str,
    content_type: str,
    content_size: int,
    metadata: Dict[str, Any] = None,
):
    """Log the start of an ingestion operation."""
    logger.info(
        "ingestion_started",
        ingestion_id=ingestion_id,
        content_type=content_type,
        content_size=content_size,
        metadata=metadata or {},
    )


def log_ingestion_complete(
    logger: Any,
    ingestion_id: str,
    status: str,
    duration_ms: int,
    chunks_processed: int = 0,
    memory_tier: str = "semantic",
    error_message: Optional[str] = None,
):
    """Log the completion of an ingestion operation."""
    log_method = logger.info if status == "completed" else logger.error
    log_method(
        "ingestion_complete",
        ingestion_id=ingestion_id,
        status=status,
        duration_ms=duration_ms,
        chunks_processed=chunks_processed,
        memory_tier=memory_tier,
        error_message=error_message,
    )


def log_memos_request(
    logger: Any,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Log a request to memOS.as service."""
    log_method = logger.info if 200 <= status_code < 400 else logger.error
    log_method(
        "memos_request",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
        request_size=request_size,
        response_size=response_size,
        error_message=error_message,
    )


def log_content_processing(
    logger: Any,
    operation: str,
    content_size: int,
    chunks_created: int = 0,
    processing_time_ms: int = 0,
    metadata: Dict[str, Any] = None,
):
    """Log content processing operations."""
    logger.info(
        "content_processing",
        operation=operation,
        content_size=content_size,
        chunks_created=chunks_created,
        processing_time_ms=processing_time_ms,
        metadata=metadata or {},
    )


def log_health_check(
    logger: Any,
    service: str,
    status: str,
    response_time_ms: int,
    details: Dict[str, Any] = None,
):
    """Log health check results."""
    logger.info(
        "health_check",
        target_service=service,
        status=status,
        response_time_ms=response_time_ms,
        details=details or {},
    )


class IngestionContextFilter:
    """Context filter for ingestion-specific logging."""

    def __init__(self, ingestion_id: str):
        self.ingestion_id = ingestion_id
        self.token = None

    def __enter__(self):
        self.token = structlog.contextvars.bind_contextvars(
            ingestion_id=self.ingestion_id
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            structlog.contextvars.reset_contextvars(**self.token)
