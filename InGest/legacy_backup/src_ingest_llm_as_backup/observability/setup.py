"""Observability setup shim.

Observability is intentionally removed for now.

This module stays in place for backward compatibility with older imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ObservabilityManager:
    """No-op observability manager."""

    def setup_all(self, app: Any) -> None:
        return None

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "metrics_enabled": False,
            "tracing_enabled": False,
            "logging_structured": False,
            "langfuse_enabled": False,
        }

    def get_integrations_status(self) -> Dict[str, Any]:
        return {}


observability = ObservabilityManager()


def setup_observability(app: Any) -> ObservabilityManager:
    observability.setup_all(app)
    return observability


def get_observability_status() -> Dict[str, Any]:
    return {
        "observability": observability.get_health_status(),
        "integrations": observability.get_integrations_status(),
    }
