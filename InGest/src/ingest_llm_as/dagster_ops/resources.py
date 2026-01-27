"""Dagster Resources for Soma InGest.

Resources provide database connections and API clients to Dagster ops/assets.
Follows "Apartment Complex" dependency isolation - all connections are local to InGest.
"""

from dagster import ConfigurableResource
from pydantic import Field
import asyncpg
import redis.asyncio as aioredis
import httpx


class PostgresResource(ConfigurableResource):
    """PostgreSQL connection resource for LanceDB metadata and transaction tracking."""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    user: str = Field(default="postgres", description="PostgreSQL user")
    password: str = Field(default="postgres", description="PostgreSQL password")
    database: str = Field(default="soma_data", description="PostgreSQL database")

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    async def get_connection(self) -> asyncpg.Connection:
        """Get an async PostgreSQL connection."""
        return await asyncpg.connect(dsn=self.dsn)


class RedisResource(ConfigurableResource):
    """Redis connection resource for working memory and pub/sub."""

    url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    async def get_client(self) -> aioredis.Redis:
        """Get an async Redis client."""
        return aioredis.from_url(self.url)


class OllamaResource(ConfigurableResource):
    """Ollama/Docker Model Runner resource for local embedding generation.

    Supports both:
    - Ollama: http://localhost:11434
    - Docker Model Runner: http://model-runner.docker.internal
    """

    base_url: str = Field(
        default="http://model-runner.docker.internal",
        description="Model Runner API base URL",
    )
    embedding_model: str = Field(
        default="qwen3-embedding:0.6B-F16", description="Embedding model to use"
    )

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using Docker Model Runner or Ollama."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embedding_model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            # Both Ollama and Model Runner return {"embeddings": [[...]]}
            return data.get("embeddings", [[]])[0]


class OmegaKGClient(ConfigurableResource):
    """HTTP client for OmegaKG Guardian API.

    memOS and InGest use this to commit memories to the Brain.
    Enforces the "Guardian-only-writer" constraint.
    """

    base_url: str = Field(
        default="http://localhost:8765", description="OmegaKG API base URL"
    )
    internal_key: str = Field(
        default="soma_secret_key", description="Internal authentication key"
    )
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    async def commit_knowledge(
        self, raw_id: str, type: str, digest: dict, metadata: dict | None = None
    ) -> dict:
        """Commit processed knowledge to OmegaKG Guardian."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/guardian/commit",
                json={
                    "raw_id": raw_id,
                    "type": type,
                    "digest": digest,
                    "metadata": metadata or {},
                },
                headers={"X-Soma-Key": self.internal_key},
            )
            response.raise_for_status()
            return response.json()

    async def store_embedding(
        self,
        raw_id: str,
        node_label: str,
        embedding: list[float],
        content: str | None = None,
    ) -> dict:
        """Store embedding via OmegaKG Guardian."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/guardian/store_embedding",
                json={
                    "raw_id": raw_id,
                    "node_label": node_label,
                    "embedding": embedding,
                    "content": content,
                },
                headers={"X-Soma-Key": self.internal_key},
            )
            response.raise_for_status()
            return response.json()

    async def validate_against_codex(self, content: str) -> dict:
        """Validate content against Mirmir Protocol Codex of Consequences."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/guardian/validate", json={"content": content}
            )
            response.raise_for_status()
            return response.json()
