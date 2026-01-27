"""
Embedding Service - Provider-Agnostic Vector Generation

Generates 1024-dimension embeddings using:
1. Ollama (local bge-m3:567m) - primary, fastest, 1024 dims native
2. Nano-GPT (hosted BAAI bge-m3) - fallback, 1024 dims
3. Gemini - secondary fallback, truncated from 3072 to 1024 dims
4. Mock - deterministic for development

Phase 7: TN-LINEAR-07 - The Enrichment (Embeddings)
"""

import logging
from typing import List

import httpx
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from omega_kg.settings import settings

logger = logging.getLogger(__name__)

# --- STARTUP INITIALIZATION LOGGING ---
# Log the configured embedding provider at module import time for diagnostics
_embedding_provider = settings.embedding_provider
_ollama_url = settings.ollama_base_url
logger.info(
    f"✓ Embedding Service initialized with provider: {_embedding_provider}, "
    f"Ollama base URL: {_ollama_url}"
)

# Provider configuration
OLLAMA_EMBEDDING_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "bge-m3:567m"

NANOGPT_EMBEDDING_URL = "https://nano-gpt.com/api/v1/embeddings"
NANOGPT_MODEL = "BAAI/bge-m3"

EMBEDDING_DIMENSIONS = 1024


# Dynamic URL Construction (use settings-based URL at runtime)
def get_ollama_url() -> str:
    """Get the Ollama embeddings endpoint URL from settings."""
    base_url = settings.ollama_base_url.rstrip("/")
    return f"{base_url}/api/embeddings"


# ----------------------------------------------------------------------
# Primary Provider: Ollama (local bge-m3:567m) - 1024 dimensions
# ----------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _embed_ollama(text: str) -> List[float]:
    """
    Generate embedding using local Ollama service (bge-m3:567m).

    Args:
        text: Input text to embed

    Returns:
        1024-dimension float vector

    Raises:
        RuntimeError: If Ollama service is not running
        ValueError: If response doesn't contain valid 1024-dim embedding
        httpx.HTTPError: On API communication failure
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {"model": OLLAMA_MODEL, "prompt": text}
        url = get_ollama_url()

        response = await client.post(
            url,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Ollama raw response keys: {list(data.keys())}")

        embedding: List[float] = data.get("embedding")

        if not embedding or len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Ollama returned invalid embedding "
                f"(expected {EMBEDDING_DIMENSIONS} dims, got {len(embedding) if embedding else 'None'})"
            )

        return embedding


# ----------------------------------------------------------------------
# Secondary Provider: Nano-GPT (hosted BAAI bge-m3) - 1024 dimensions
# ----------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_not_exception_type(RuntimeError),  # Don't retry on missing API key
    reraise=True,
)
async def _embed_nanogpt(text: str) -> List[float]:
    """
    Generate embedding using Nano-GPT's hosted BAAI bge-m3 model.

    Args:
        text: Input text to embed

    Returns:
        1024-dimension float vector

    Raises:
        RuntimeError: If API key is missing
        ValueError: If response doesn't contain valid 1024-dim embedding
        httpx.HTTPError: On API communication failure
    """
    api_key = settings.nanogpt_api_key
    if not api_key:
        raise RuntimeError("Nano-GPT API key missing (NANOGPT_API_KEY not set)")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # NanoGPT API expects 'input' as string
        payload = {"model": NANOGPT_MODEL, "input": text}
        headers = {"Authorization": f"Bearer {api_key}"}

        response = await client.post(
            NANOGPT_EMBEDDING_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Nano-GPT raw response: {data}")

        # Handle OpenAI-compatible response format
        if "data" in data and len(data["data"]) > 0:
            embedding: List[float] = data["data"][0].get("embedding")
        else:
            embedding = data.get("embedding")

        if not embedding or len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Nano-GPT returned invalid embedding "
                f"(expected {EMBEDDING_DIMENSIONS} dims, got {len(embedding) if embedding else 'None'})"
            )

        return embedding


# ----------------------------------------------------------------------
# Fallback Provider: Gemini - 3072 dims → truncated to 1024
# ----------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_not_exception_type(RuntimeError),  # Don't retry on missing API key
    reraise=True,
)
async def _embed_gemini(text: str) -> List[float]:
    """
    Generate embedding using Gemini API, truncating to 1024 dimensions.

    Gemini's gemini-embedding-001 returns 3072 dimensions.
    We truncate to the first 1024 to match the Neo4j index.

    Args:
        text: Input text to embed

    Returns:
        1024-dimension float vector (truncated from 3072)

    Raises:
        RuntimeError: If Gemini API key is missing
        ValueError: If response has fewer than 1024 dimensions
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("Gemini API key missing (GEMINI_API_KEY not set)")

    # Use httpx for Gemini API (OpenAI-compatible endpoint)
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"model": "gemini-embedding-001", "input": text}
        headers = {"Authorization": f"Bearer {api_key}"}

        response = await client.post(
            "https://generativelanguage.googleapis.com/v1/embeddings",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()

        # Handle response format
        if "data" in data and len(data["data"]) > 0:
            raw_embedding: List[float] = data["data"][0].get("embedding")
        else:
            raw_embedding = data.get("embedding")

        if not raw_embedding or len(raw_embedding) < EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Gemini returned fewer than {EMBEDDING_DIMENSIONS} dimensions "
                f"(got {len(raw_embedding) if raw_embedding else 'None'})"
            )

        # Truncate to 1024 dimensions to match Neo4j index
        return list(raw_embedding[:EMBEDDING_DIMENSIONS])


# Fallback: Local Mock Embeddings (for development/testing)
# This provides deterministic 1024-dim vectors when real services fail.
def _embed_mock(text: str) -> List[float]:
    """
    Generate a deterministic mock embedding (1024 dims) based on text hash.

    Used when real embedding services are unavailable or for testing.

    Args:
        text: Input text

    Returns:
        1024-dimension float vector (deterministic based on input)
    """
    import hashlib

    # Create a deterministic seed from the text
    hash_digest = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(hash_digest[:4], byteorder="big")

    # Use seeded random to generate 1024 floats
    import random

    rng = random.Random(seed)
    return [rng.random() for _ in range(EMBEDDING_DIMENSIONS)]


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
async def generate_embedding(text: str) -> List[float]:
    """
    Generate a 1024-dimension embedding for the given text.

    Provider hierarchy:
    1. Ollama (local bge-m3:567m) - primary, fastest, native 1024-dim
    2. Nano-GPT (BAAI bge-m3) - fallback, 1024-dim
    3. Gemini (gemini-embedding-001) - secondary fallback, truncated from 3072 to 1024
    4. Mock (deterministic hash-based) - final fallback for development

    Args:
        text: Input text to embed (e.g., "Issue Title + Description")

    Returns:
        List of 1024 floats representing the semantic embedding

    Raises:
        RuntimeError: If no embedding provider is available

    Example:
        >>> embedding = await generate_embedding("Fix login button alignment")
        >>> len(embedding)
        1024
    """
    ollama_enabled = getattr(settings, "ollama_enabled", True)
    nano_gpt_enabled = getattr(settings, "nano_gpt_enabled", True)
    gemini_enabled = getattr(settings, "gemini_enabled", True)

    if not ollama_enabled and not nano_gpt_enabled and not gemini_enabled:
        raise RuntimeError("No embedding provider available")

    # Try Ollama first (local, fastest)
    if ollama_enabled:
        try:
            result: List[float] = await _embed_ollama(text)
            logger.debug(f"Generated {EMBEDDING_DIMENSIONS}-dim embedding via Ollama")
            return result
        except Exception as err:
            logger.warning(
                f"Ollama embedding failed ({err}); attempting Nano-GPT fallback"
            )

    # Try Nano-GPT (if key is configured)
    if nano_gpt_enabled and settings.nanogpt_api_key:
        try:
            result = await _embed_nanogpt(text)
            logger.debug(f"Generated {EMBEDDING_DIMENSIONS}-dim embedding via Nano-GPT")
            return result
        except Exception as err:
            logger.warning(
                f"Nano-GPT embedding failed ({err}); attempting Gemini fallback"
            )

    # Fallback to Gemini (if key is configured)
    if gemini_enabled and settings.gemini_api_key:
        try:
            result = await _embed_gemini(text)
            logger.debug(
                f"Generated {EMBEDDING_DIMENSIONS}-dim embedding via Gemini (truncated)"
            )
            return result
        except Exception as err:
            logger.warning(
                f"Gemini embedding also failed: {err}; using mock embeddings"
            )

    # Final fallback: use mock embeddings (deterministic, for development)
    try:
        result = _embed_mock(text)
        logger.warning(
            "Using mock embeddings (no real provider available). "
            "These are deterministic hash-based vectors suitable for development only."
        )
        return result
    except Exception as err:
        logger.error(f"Even mock embeddings failed: {err}")
        raise RuntimeError(f"All embedding providers failed. Last error: {err}")
