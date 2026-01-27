"""
Pydantic models for the Intelligence Layer

Defines the data structures for constraints, contexts, incidents, and verdicts.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Severity levels for constraints"""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Constraint(BaseModel):
    """
    Represents a governance constraint in the Knowledge Graph.

    Constraints are rules that govern actions within specific contexts.
    """

    id: str = Field(..., description="Unique identifier for the constraint")
    description: str = Field(
        ..., description="Human-readable description of the constraint"
    )
    severity: SeverityLevel = Field(
        default=SeverityLevel.WARNING, description="Severity level"
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )
    contexts: List[str] = Field(
        default_factory=list, description="Contexts this constraint governs"
    )

    class Config:
        use_enum_values = True


class Context(BaseModel):
    """
    Represents a context in the Knowledge Graph.

    Contexts are domains or areas where constraints apply.
    """

    name: str = Field(..., description="Unique name for the context")
    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )

    class Config:
        use_enum_values = True


class Incident(BaseModel):
    """
    Represents an incident where a constraint was violated.

    Incidents are logged when actions violate constraints.
    """

    id: str = Field(..., description="Unique identifier for the incident")
    constraint_id: str = Field(..., description="ID of the violated constraint")
    action: str = Field(..., description="The action that caused the violation")
    context: str = Field(..., description="Context where the violation occurred")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the incident occurred"
    )
    resolved: bool = Field(
        default=False, description="Whether the incident has been resolved"
    )

    class Config:
        use_enum_values = True


class Verdict(BaseModel):
    """
    Represents the verdict from Mirmir's constraint review.

    A verdict determines whether an action is approved, vetoed, or requires warning.
    """

    approved: bool = Field(..., description="Whether the action is approved")
    message: str = Field(..., description="Explanation of the verdict")
    constraints_checked: List[str] = Field(
        default_factory=list, description="IDs of constraints checked"
    )
    violations: List[str] = Field(
        default_factory=list, description="IDs of violated constraints"
    )
    warnings: List[str] = Field(
        default_factory=list, description="IDs of constraints with warnings"
    )

    class Config:
        use_enum_values = True
