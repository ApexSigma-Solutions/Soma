"""
Unit tests for the Codex module.
"""

from omega_kg.intelligence.codex import Codex
from omega_kg.intelligence.models import Constraint, SeverityLevel
from datetime import datetime


def test_codex_metabolize_failure():
    """Test metabolize_failure creates valid Constraint."""
    with Codex() as codex:
        constraint = codex.metabolize_failure("Package not installed")
        assert constraint.id is not None
        assert "Package not installed" in constraint.description


def test_codex_constraint_creation():
    """Test creating a constraint directly."""
    constraint = Constraint(
        id="TEST_CONSTRAINT_001",
        description="Test constraint for unit testing",
        severity=SeverityLevel.WARNING,
        created_at=datetime.now(),
    )
    assert constraint.id == "TEST_CONSTRAINT_001"
    assert constraint.severity == SeverityLevel.WARNING
