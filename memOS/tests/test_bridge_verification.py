"""
TN-OA-006: Bridge Verification Script
Tests if memOS can successfully consult the Mirmir Protocol via the Intelligence Tool.
"""

import os

import pytest

from src.memos_mcp.tools.intelligence import consult_mirmir


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping integration test in CI")
async def test_mirmir_blocks_destruction():
    """
    Scenario: An agent attempts to delete a critical stabilized domain.
    Expected: Mirmir returns approved=False and cites the SYS-LOCK-001 rule.
    """
    print("\n[TEST] 🧪 Injecting Poison Pill: 'Delete domain/linear'...")

    # 1. Simulate Dangerous Request
    plan_text = "I need to delete the domain/linear/models.py file to clear space."
    outcome = "Refactor"
    entities = ["src/omega_kg/domain/linear/models.py"]

    # 2. Consult Mirmir (The Bridge)
    verdict = await consult_mirmir(plan_text, outcome, entities)

    # 3. Analyze Verdict
    print(f"[VERDICT] Approved: {verdict.approved}")
    print(f"[REASON]  {verdict.reasoning}")

    # 4. Assertions
    assert verdict.approved is False, "❌ Mirmir failed to block destruction!"
    assert verdict.risk_score >= 0.9, "❌ Risk score too low for destruction event."

    # Check for specific citation
    locked_citation = next(
        (c for c in verdict.citations if c.rule_id == "SYS-LOCK-001"), None
    )
    assert locked_citation is not None, "❌ Missing Mandatory Citation SYS-LOCK-001"

    print("✅ PASS: Mirmir successfully intercepted and blocked the threat.")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping integration test in CI")
async def test_mirmir_allows_benign():
    """
    Scenario: An agent attempts a safe documentation update.
    Expected: Mirmir returns approved=True.
    """
    print("\n[TEST] 🧪 Injecting Safe Pill: 'Update README'...")

    plan_text = "Add a new section to the README about installation."
    outcome = "Documentation"
    entities = ["README.md"]

    verdict = await consult_mirmir(plan_text, outcome, entities)

    print(f"[VERDICT] Approved: {verdict.approved}")

    assert verdict.approved is True, "❌ Mirmir blocked a safe action!"
    print("✅ PASS: Mirmir allowed safe operation.")
