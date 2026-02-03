"""Qwen3 Embedding Service for InGest.

Provides async embedding generation using the Qwen3-Embed-0.6B-F16 model
running on Ollama (localhost:12434).

Implements CST-ORG-003: InGest (The Stomach) is the ONLY service allowed
to call the Embedding Model.
"""

import logging
import os
from typing import List

import httpx

logger = logging.getLogger(__name__)

# Ollama Configuration per spec
OLLAMA_BASE_URL = os.getenv("SOMA_OLLAMA_URL", "http://localhost:12434")
QWEN_MODEL = os.getenv("SOMA_EMBED_MODEL", "ai/qwen3-embedding:0.6B-F16")
EMBED_DIMENSION = int(os.getenv("SOMA_EMBED_DIMENSION", "768"))


class QwenEmbedder:
    """Async Qwen3 Embedding client using Ollama API.

    Endpoints:
        POST /api/embeddings - Generate embeddings for text

    Example:
        ```python
        embedder = QwenEmbedder()
        async with embedder:
            vector = await embedder.embed("Hello, world!")
        ```
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = QWEN_MODEL,
        timeout: float = 30.0,
    ):
        """Initialize the embedder.

        Args:
            base_url: Ollama server URL
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

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If response is malformed
        """
        if not self._client:
            raise RuntimeError("QwenEmbedder must be used as async context manager")

        endpoint = f"{self.base_url}/api/embeddings"

        try:
            response = await self._client.post(
                endpoint,
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding")

            if not embedding:
                raise ValueError(f"No embedding in response: {data}")

            logger.debug(
                "embedding_generated",
                extra={"model": self.model, "dimension": len(embedding)},
            )

            return embedding

        except httpx.HTTPError as e:
            logger.error("embedding_failed", extra={"error": str(e)})
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [await self.embed(text) for text in texts]


# Factory function for singleton pattern
_embedder_instance: QwenEmbedder | None = None


async def get_embedder() -> QwenEmbedder:
    """Get or create the singleton embedder instance."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = QwenEmbedder()
    return _embedder_instance
