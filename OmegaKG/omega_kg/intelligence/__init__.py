"""
Intelligence Layer - The "Brain" of OmegaKG

This module provides governance and constraint enforcement for the Knowledge Graph.
It implements the "Great Divorce" - separating logic from storage.

Components:
- Codex: Interface to Neo4j for constraint retrieval
- Mirmir: Constraint review and enforcement logic
- Models: Pydantic models for constraints, contexts, incidents, and verdicts
"""

from .codex import Codex
from .mirmir import Mirmir
from .models import Constraint, Context, Incident, Verdict
from .exceptions import IntelligenceError, CodexVetoError

__all__ = [
    "Codex",
    "Mirmir",
    "Constraint",
    "Context",
    "Incident",
    "Verdict",
    "IntelligenceError",
    "CodexVetoError",
]
