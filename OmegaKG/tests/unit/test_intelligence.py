"""
Unit tests for the intelligence layer.
"""


def test_import_intelligence_package():
    """Verify intelligence package can be imported."""
    from omega_kg.intelligence import Codex, Mirmir

    assert Codex is not None
    assert Mirmir is not None
