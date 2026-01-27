"""Langfuse event smoke test (skips if env not configured)."""

import os
import pytest
from langfuse import Langfuse


@pytest.mark.integration
def test_langfuse_connection_or_skip() -> None:
    """Send an event to Langfuse when env is set; otherwise skip."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST")

    if not all([public_key, secret_key, host]):
        pytest.skip("Langfuse environment variables not set")

    # Initialize Langfuse client
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )

    # Test the connection by sending a simple event and flush
    trace = langfuse.trace(name="test-trace")
    trace.event(name="test-event", metadata={"test": "test"})
    langfuse.flush()
