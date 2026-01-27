"""Metrics shim.

The Prometheus metrics stack has been removed temporarily.
This module provides no-op functions with the same API used by the service.
"""

from __future__ import annotations

from typing import Any


def setup_metrics(app: Any) -> None:
    return None


def record_ingestion_start(endpoint: str, content_type: str, content_size: int):
    """Record the start of an ingestion operation."""
    return None


def record_ingestion_complete(
    endpoint: str,
    content_type: str,
    duration: float,
    status: str,
    chunks_processed: int = 0,
    memory_tier: str = "semantic",
):
    """Record the completion of an ingestion operation."""
    return None


def record_memos_request(endpoint: str, method: str, status_code: int, duration: float):
    """Record a request to memOS.as service."""
    return None


def init_service_metrics(version: str, environment: str = "development"):
    """Initialize service-level metrics."""
    return None
