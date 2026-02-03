"""SimpleMem Stage 3: Hybrid Retriever.

Implements Adaptive Query-Aware Retrieval with three search layers:
- Semantic: Dense vector similarity (via LanceDB/Ollama embeddings)
- Lexical: BM25 keyword matching
- Symbolic: Metadata filtering (timestamps, entities, topics)

Query complexity (Cq) determines retrieval depth:
- Simple queries → ~100 tokens
- Complex queries → ~1000 tokens
"""

import asyncio
from dataclasses import dataclass, field
import logging
from datetime import datetime

import lancedb
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for hybrid retrieval."""

    lancedb_uri: str = "/opt/soma/memory/lancedb"  # Container path
    table_name: str = "soma_memories"
    ollama_base_url: str = "http://model-runner.docker.internal"
    embedding_model: str = "qwen3-embedding:0.6B-F16"

    # Retrieval parameters
    semantic_weight: float = 0.5
    lexical_weight: float = 0.3
    symbolic_weight: float = 0.2
    max_results: int = 10

    # Complexity thresholds
    simple_query_tokens: int = 100
    complex_query_tokens: int = 1000


@dataclass
class MemoryResult:
    """A single memory retrieval result."""

    id: str
    content: str
    score: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    symbolic_score: float = 0.0
    entities: list[str] = field(default_factory=list)
    created_at: str = ""
    source: str = ""


def estimate_query_complexity(query: str) -> float:
    """Estimate query complexity (Cq) for adaptive retrieval.

    Returns a value between 0 and 1:
    - 0-0.3: Simple (direct questions, single facts)
    - 0.3-0.6: Moderate (multi-part questions)
    - 0.6-1.0: Complex (reasoning, synthesis required)
    """
    # Simple heuristics for complexity estimation
    complexity = 0.0

    # Length factor
    word_count = len(query.split())
    if word_count > 20:
        complexity += 0.3
    elif word_count > 10:
        complexity += 0.2
    else:
        complexity += 0.1

    # Question words indicating complexity
    complex_indicators = [
        "why",
        "how",
        "explain",
        "analyze",
        "compare",
        "relationship",
        "difference",
        "impact",
        "effect",
    ]
    simple_indicators = ["what", "when", "where", "who", "which"]

    query_lower = query.lower()
    for indicator in complex_indicators:
        if indicator in query_lower:
            complexity += 0.2
            break

    for indicator in simple_indicators:
        if indicator in query_lower:
            complexity -= 0.1
            break

    # Multiple clauses suggest complexity
    if " and " in query_lower or " or " in query_lower:
        complexity += 0.15

    return max(0.0, min(1.0, complexity))


class HybridRetriever:
    """SimpleMem Stage 3: Adaptive Query-Aware Retrieval.

    Combines semantic, lexical, and symbolic search for optimal memory retrieval.
    memOS is READ-ONLY for long-term memory (Neo4j/LanceDB).
    """

    def __init__(self, config: RetrievalConfig | None = None):
        self.config = config or RetrievalConfig()
        self._db = None
        self._table = None
        self._bm25_corpus = []
        self._bm25 = None

    async def initialize(self) -> None:
        """Initialize LanceDB connection and BM25 index."""
        try:
            # Run blocking lancedb.connect() in thread pool to avoid blocking event loop
            self._db = await asyncio.to_thread(lancedb.connect, self.config.lancedb_uri)

            if self.config.table_name in self._db.table_names():
                self._table = self._db.open_table(self.config.table_name)
                await self._rebuild_bm25_index()
            else:
                logger.warning(f"Table {self.config.table_name} not found in LanceDB")

        except Exception as e:
            logger.error(f"Failed to initialize HybridRetriever: {e}")

    async def _rebuild_bm25_index(self) -> None:
        """Rebuild BM25 index from LanceDB content."""
        if not self._table:
            return

        try:
            # Fetch all documents for BM25
            df = self._table.to_pandas()
            self._bm25_corpus = [
                {"id": row["id"], "tokens": row.get("tokens", "").split()}
                for _, row in df.iterrows()
            ]

            if self._bm25_corpus:
                tokenized = [doc["tokens"] for doc in self._bm25_corpus]
                self._bm25 = BM25Okapi(tokenized)
                logger.info(f"BM25 index built with {len(self._bm25_corpus)} documents")

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using Ollama."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.config.ollama_base_url}/api/embed",
                json={"model": self.config.embedding_model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embeddings", [[]])[0]

    async def _semantic_search(self, query: str, limit: int) -> list[tuple[str, float]]:
        """Perform semantic (vector) search."""
        if not self._table:
            return []

        try:
            query_embedding = await self._generate_embedding(query)

            # LanceDB vector search
            results = self._table.search(query_embedding).limit(limit).to_list()

            return [
                (r["id"], 1 - r["_distance"]) for r in results
            ]  # Convert distance to similarity

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _lexical_search(self, query: str, limit: int) -> list[tuple[str, float]]:
        """Perform BM25 lexical search."""
        if not self._bm25 or not self._bm25_corpus:
            return []

        try:
            query_tokens = query.lower().split()
            scores = self._bm25.get_scores(query_tokens)

            # Get top-k results
            indexed_scores = list(enumerate(scores))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, score in indexed_scores[:limit]:
                if score > 0:
                    doc_id = self._bm25_corpus[idx]["id"]
                    results.append(
                        (doc_id, score / max(scores) if max(scores) > 0 else 0)
                    )

            return results

        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return []

    async def _symbolic_filter(
        self,
        entity_filter: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> set[str]:
        """Filter by symbolic metadata."""
        if not self._table:
            return set()

        try:
            df = self._table.to_pandas()
            mask = [True] * len(df)

            if entity_filter:
                entity_set = set(e.lower() for e in entity_filter)
                mask = [
                    any(e.lower() in entity_set for e in row.get("entities", []))
                    for _, row in df.iterrows()
                ]

            # Date filtering would go here

            return set(df[mask]["id"].tolist())

        except Exception as e:
            logger.error(f"Symbolic filter failed: {e}")
            return set()

    async def retrieve(
        self,
        query: str,
        entity_filter: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[MemoryResult]:
        """Perform hybrid retrieval with adaptive depth.

        Args:
            query: The search query
            entity_filter: Optional list of entities to filter by
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            List of MemoryResult objects sorted by combined score
        """
        if not self._table:
            logger.warning("HybridRetriever not initialized")
            return []

        # Estimate complexity for adaptive retrieval
        complexity = estimate_query_complexity(query)
        limit = (
            int(
                self.config.simple_query_tokens
                + (self.config.complex_query_tokens - self.config.simple_query_tokens)
                * complexity
            )
            // 50
        )  # Rough tokens-to-documents estimate

        limit = max(5, min(limit, self.config.max_results))

        logger.info(
            f"Query complexity: {complexity:.2f}, retrieving up to {limit} results"
        )

        # Perform searches
        semantic_results = await self._semantic_search(query, limit * 2)
        lexical_results = self._lexical_search(query, limit * 2)

        # Apply symbolic filter if specified
        allowed_ids = None
        if entity_filter or date_from or date_to:
            allowed_ids = await self._symbolic_filter(entity_filter, date_from, date_to)

        # Combine scores
        combined: dict[str, dict[str, float]] = {}

        for doc_id, score in semantic_results:
            if allowed_ids is None or doc_id in allowed_ids:
                combined.setdefault(
                    doc_id, {"semantic": 0, "lexical": 0, "symbolic": 0}
                )
                combined[doc_id]["semantic"] = score

        for doc_id, score in lexical_results:
            if allowed_ids is None or doc_id in allowed_ids:
                combined.setdefault(
                    doc_id, {"semantic": 0, "lexical": 0, "symbolic": 0}
                )
                combined[doc_id]["lexical"] = score

        # Calculate final scores
        results = []
        for doc_id, scores in combined.items():
            final_score = (
                scores["semantic"] * self.config.semantic_weight
                + scores["lexical"] * self.config.lexical_weight
                + (1.0 if allowed_ids and doc_id in allowed_ids else 0.0)
                * self.config.symbolic_weight
            )

            # Fetch content from LanceDB
            try:
                df = self._table.to_pandas()
                row = df[df["id"] == doc_id].iloc[0]
                content = row.get("content", "")
                entities = row.get("entities", [])
                created_at = row.get("created_at", "")
            except (IndexError, KeyError):
                content = ""
                entities = []
                created_at = ""

            results.append(
                MemoryResult(
                    id=doc_id,
                    content=content,
                    score=final_score,
                    semantic_score=scores["semantic"],
                    lexical_score=scores["lexical"],
                    symbolic_score=1.0
                    if allowed_ids and doc_id in allowed_ids
                    else 0.0,
                    entities=entities if isinstance(entities, list) else [],
                    created_at=created_at,
                )
            )

        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]


# Global instance for MCP tools
_retriever: HybridRetriever | None = None


async def get_retriever() -> HybridRetriever:
    """Get or create the global HybridRetriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
        await _retriever.initialize()
    return _retriever
