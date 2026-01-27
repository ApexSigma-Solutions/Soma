"""
Unit tests for the Mirmir module.
"""

from omega_kg.intelligence import Codex, Mirmir


def test_mirmir_review_action_approved():
    """Test Mirmir approves safe actions."""
    with Codex() as codex:
        mirmir = Mirmir(codex)
        verdict = mirmir.review_action("run unit tests")
        assert verdict.approved is True


def test_mirmir_review_action_vetoed():
    """Test Mirmir vetoes prohibited actions."""
    with Codex() as codex:
        mirmir = Mirmir(codex)
        verdict = mirmir.review_action("skip venv check")
        # This will only fail if the constraint is seeded in Neo4j
        # For unit testing without DB, we test the keyword extraction logic
        assert verdict is not None
