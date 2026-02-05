"""Hybrid Cognitive Service for OmegaKG.

TN-SOMA-301: Implements the "Brain Upgrade" for Graph Native Cloud architecture.
Uses an OpenAI-format API (Gemini) for LLM extraction and Docker Model Runner
(Qwen3) for local embeddings.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from omega_kg.settings import settings

logger = logging.getLogger("omega_kg.cognitive")


class ExtractedNode(BaseModel):
    """A node extracted from text by the LLM."""

    id: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class ExtractedEdge(BaseModel):
    """An edge extracted from text by the LLM."""

    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphExtractionResult(BaseModel):
    """Result of LLM graph extraction."""

    nodes: List[ExtractedNode] = Field(default_factory=list)
    edges: List[ExtractedEdge] = Field(default_factory=list)


class CognitiveResult(BaseModel):
    """Complete result of cognitive processing."""

    embedding: List[float]
    graph: GraphExtractionResult
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Graph extraction prompt for LLM
EXTRACTION_PROMPT = """Analyze the following text and extract a knowledge graph.
Return JSON with this structure:
{
  "nodes": [{"id": "unique_id", "label": "Concept|Person|Organization|Event|Location", "properties": {"name": "...", ...}}],
  "edges": [{"source": "node_id", "target": "node_id", "type": "RELATES_TO|MENTIONS|CREATED_BY|PART_OF", "properties": {}}]
}

Rules:
- Use descriptive, unique IDs (lowercase_snake_case)
- Label must be one of: Concept, Person, Organization, Event, Location, Document, Topic
- Edge types: RELATES_TO, MENTIONS, CREATED_BY, PART_OF, REFERS_TO, DERIVED_FROM
- Keep it focused - extract only meaningful entities and relationships
- Return ONLY valid JSON, no markdown

TEXT:
{text}
"""


class HybridCognitiveService:
    """Service combining LLM extraction (Gemini) with local embeddings (Qwen3).

    Uses OpenAI-format API clients for flexibility with different providers.

    Example:
        ```python
        async with HybridCognitiveService() as cognitive:
            result = await cognitive.process_ingestion(
                text="Some content to process",
                source="manual",
            )
        ```
    """

    def __init__(
        self,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
        embed_base_url: Optional[str] = None,
        embed_model: Optional[str] = None,
    ):
        """Initialize the cognitive service.

        Args:
            llm_api_key: API key for LLM (defaults to settings.llm_api_key)
            llm_base_url: Base URL for LLM API (defaults to settings.llm_base_url)
            llm_model: Model name for LLM (defaults to settings.llm_model)
            embed_base_url: Base URL for embedding service (defaults to settings.embed_base_url)
            embed_model: Model name for embeddings (defaults to settings.embed_model)
        """
        self.llm_api_key = (
            llm_api_key or settings.llm_api_key or settings.gemini_api_key
        )
        self.llm_base_url = (llm_base_url or settings.llm_base_url).rstrip("/")
        self.llm_model = llm_model or settings.llm_model
        self.embed_base_url = (embed_base_url or settings.embed_base_url).rstrip("/")
        self.embed_model = embed_model or settings.embed_model
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "HybridCognitiveService":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def extract_graph(self, text: str) -> GraphExtractionResult:
        """Extract knowledge graph from text using LLM.

        Args:
            text: Input text to analyze.

        Returns:
            GraphExtractionResult with extracted nodes and edges.
        """
        if not self._client:
            raise RuntimeError("Service must be used within async context manager")

        prompt = EXTRACTION_PROMPT.format(text=text[:8000])  # Limit context

        try:
            response = await self._client.post(
                f"{self.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You extract knowledge graphs from text. Return only valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            # Clean up response - remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            graph_data = json.loads(content)
            nodes = [ExtractedNode(**n) for n in graph_data.get("nodes", [])]
            edges = [ExtractedEdge(**e) for e in graph_data.get("edges", [])]

            return GraphExtractionResult(nodes=nodes, edges=edges)

        except Exception as e:
            logger.warning(f"Graph extraction failed: {e}")
            return GraphExtractionResult()

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using local Qwen3 model.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        if not self._client:
            raise RuntimeError("Service must be used within async context manager")

        try:
            response = await self._client.post(
                f"{self.embed_base_url}/v1/embeddings",
                json={"model": self.embed_model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        return [await self.embed_text(t) for t in texts]

    async def process_ingestion(
        self,
        text: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CognitiveResult:
        """Full cognitive processing pipeline.

        1. Extract knowledge graph using LLM
        2. Generate embedding using local model

        Args:
            text: Content to process.
            source: Origin of content.
            metadata: Additional metadata.

        Returns:
            CognitiveResult with embedding and graph.
        """
        metadata = metadata or {}

        # Run extraction and embedding in parallel conceptually
        graph = await self.extract_graph(text)
        embedding = await self.embed_text(text)

        return CognitiveResult(
            embedding=embedding,
            graph=graph,
            source=source,
            metadata=metadata,
        )


# Singleton factory
_cognitive_service: Optional[HybridCognitiveService] = None


def get_cognitive_service() -> HybridCognitiveService:
    """Get or create the cognitive service singleton."""
    global _cognitive_service
    if _cognitive_service is None:
        _cognitive_service = HybridCognitiveService()
    return _cognitive_service
