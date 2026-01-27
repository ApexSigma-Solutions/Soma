#!/usr/bin/env python
"""
Test MCP integration with Codex consultation.
"""

import asyncio
import httpx


async def test_consult_codex():
    """Test the consult_codex MCP tool."""
    base_url = "http://127.0.0.1:8765"

    # Test 1: Safe action (should be approved)
    try:
        response = await httpx.AsyncClient().post(
            f"{base_url}/mcp/tools/consult_codex",
            json={"action_description": "run unit tests"},
        )
        result = response.json()
        print("Test 1 - Safe action:")
        print(f"  Allowed: {result.get('allowed')}")
        print(f"  Reason: {result.get('reason')}")
        assert result.get("allowed") is True, "Safe action should be approved"
    except Exception as e:
        print(f"Test 1 failed: {e}")

    # Test 2: Prohibited action (should be vetoed if constraint exists)
    try:
        response = await httpx.AsyncClient().post(
            f"{base_url}/mcp/tools/consult_codex",
            json={"action_description": "skip venv check"},
        )
        result = response.json()
        print("\nTest 2 - Prohibited action:")
        print(f"  Allowed: {result.get('allowed')}")
        print(f"  Reason: {result.get('reason')}")
        if result.get("constraint_id"):
            print(f"  Constraint ID: {result.get('constraint_id')}")
    except Exception as e:
        print(f"Test 2 failed: {e}")

    print("\n✅ All MCP integration tests completed!")


if __name__ == "__main__":
    asyncio.run(test_consult_codex())
