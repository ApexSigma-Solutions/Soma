"""Langfuse client shim.

Observability is intentionally removed for now.

This module remains to preserve import compatibility across the codebase, but
provides a no-op implementation (no external deps, no network calls).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class _NoOpLangfuseSDK:
    """Mimics the small subset of the Langfuse SDK used in this repo."""

    def trace(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        return None

    def generation(self, *args: Any, **kwargs: Any) -> None:
        return None

    def flush(self) -> None:
        return None


class LangfuseClient:
    """Langfuse client for LLM observability."""

    def __init__(self):
        """Initialize a no-op Langfuse client."""
        self.client = _NoOpLangfuseSDK()

    def is_available(self) -> bool:
        """Check if Langfuse client is available."""
        return False

    @property
    def enabled(self) -> bool:
        """Check if Langfuse client is enabled (alias for is_available)."""
        return False

    def create_trace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a new trace."""
        return None

    def create_generation(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create a generation record."""
        return None

    def create_score(self, name: str, value: float, comment: Optional[str] = None):
        """Create a score for evaluation."""
        return None

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: Optional[str] = None,
    ) -> None:
        """Compatibility method used throughout the codebase."""
        return None

    def flush(self):
        """Flush pending events."""
        return None


# Global client instance
_langfuse_client = None


def get_langfuse_client() -> LangfuseClient:
    """Get the global Langfuse client instance."""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client
