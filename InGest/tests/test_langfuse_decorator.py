"""Langfuse decorator smoke test (skips if env not configured)."""

import os
import pytest
from langfuse import Langfuse
from langfuse import observe


@pytest.mark.integration
def test_langfuse_decorator_or_skip() -> None:
    """Test Langfuse decorator when env is set; otherwise skip."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST")

    if not all([public_key, secret_key, host]):
        pytest.skip("Langfuse environment variables not set")

    # Initialize Langfuse client
    try:
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
    except Exception as e:
        pytest.fail(f"Error initializing Langfuse client: {e}")

    @observe()
    def my_llm_feature() -> str:
        """Test function with Langfuse decorator."""
        return "LLM feature executed"

    # Test decorated function
    try:
        result = my_llm_feature()
        assert result == "LLM feature executed"
    except Exception as e:
        pytest.fail(f"Error executing decorated function: {e}")

    # Flush events
    langfuse.flush()
