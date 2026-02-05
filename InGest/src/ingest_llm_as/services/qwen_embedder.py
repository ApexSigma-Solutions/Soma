"""Qwen3 Embedding Service for InGest.

Provides async embedding generation using the Qwen3-Embed-0.6B-F16 model
running on Docker Model Runner (localhost:12434).

TN-SOMA-303: Updated to use Docker Model Runner naming conventions (EMBED_*)
and kept as fallback for when OmegaKG Graph Native Cloud is offline.

Implements CST-ORG-003: InGest (The Stomach) is the ONLY service allowed
to call the Embedding Model (now via fallback).
"""

import logging
import os
from typing import List

import httpx

logger = logging.getLogger(__name__)

# Docker Model Runner Configuration (TN-SOMA-303: Graph Native Cloud)
# Uses EMBED_BASE_URL and EMBED_MODEL per Docker Model Runner naming conventions
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://localhost:12434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "ai/qwen3-embedding:0.6B-F16")
EMBED_DIMENSION = int(os.getenv("EMBED_DIMENSION", "768"))


class QwenEmbedder:
    """Async Qwen3 Embedding client using OpenAI-compatible API (Docker Model Runner).

    Endpoints:
        POST /v1/embeddings - Generate embeddings for text

    Example:
        ```python
        embedder = QwenEmbedder()
        async with embedder:
            vector = await embedder.embed("Hello, world!")
        ```
    """

    def __init__(
        self,
        base_url: str = EMBED_BASE_URL,
        model: str = EMBED_MODEL,
        timeout: float = 30.0,
    ):
        """Initialize the embedder.

        Args:
            base_url: Docker Model Runner server URL
            model: Model name for embedding
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "QwenEmbedder":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text string.

        Args:
            text: Input text to embed.

        Returns:
            List[float]: The embedding vector.

        Raises:
            RuntimeError: If client is not initialized (context manager).
            httpx.HTTPError: If API request fails.
        """
        if self._client is None:
            raise RuntimeError(
                "QwenEmbedder must be used as an async context manager (async with ...)"
            )

        # Docker Model Runner uses OpenAI-compatible /v1/embeddings
        url = f"{self.base_url}/v1/embeddings"
        payload = {"model": self.model, "input": text}

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # OpenAI format: data -> data[0] -> embedding
            return data["data"][0]["embedding"]
            
        except httpx.HTTPError as e:
            logger.error(f"Embedding failed for text prefix '{text[:20]}...': {e}")
            raise