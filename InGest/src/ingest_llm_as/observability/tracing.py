"""Tracing shim.

The OpenTelemetry tracing stack has been removed temporarily.
This module provides no-op helpers with the same API used by the service.
"""

from __future__ import annotations

from typing import Any, Callable, Optional


def setup_tracing(app: Any) -> None:
    return None


def get_tracer() -> None:
    return None


def trace_ingestion_operation(operation_name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def trace_memos_request(endpoint: str, method: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def add_span_attributes(**attributes: Any) -> None:
    return None


def add_span_event(name: str, attributes: Optional[dict] = None) -> None:
    return None
