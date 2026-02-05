"""
Context tools for querying OmegaKG and PGVector.

TN-SOMA-304: Refactored to use OmegaKGClient instead of direct Neo4j driver.
"""

from typing import Any, Dict, List, Optional
import logging

from ..database.pgvector_store import get_pgvector_store
from ..services.omegakg_client import OmegaKGClient
from ..memory import get_redis_client

logger = logging.getLogger(__name__)


async def retrieve_context(
    query: str, limit: int = 5, threshold: float = 0.5, agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve semantic context from the knowledge base.

    Searches PGVector for relevant memories and includes related
    working memory context.

    Args:
        query: The semantic query string
        limit: Max results to return
        threshold: Minimum similarity score (0.0-1.0)
        agent_id: Optional agent ID filter

    Returns:
        Structured context package with relevance scores
    """
    store = get_pgvector_store()
    redis = get_redis_client()

    # 1. Fetch Working Memory (Redis)
    working_context = {}
    if agent_id:
        working_context = await redis.get_working_memory(agent_id)

    # 2. Generate query embedding
    query_embedding = await store.generate_embedding(query)

    # 3. Search vector store
    results = await store.search_memories(
        query_embedding=query_embedding,
        top_k=limit,
        score_threshold=threshold,
        agent_id=agent_id,
    )

    # 4. Format results context-package style
    context_pieces = []
    for r in results:
        context_pieces.append(
            {
                "source": "pgvector",
                "id": r["id"],
                "content": r["content"],
                "relevance": r["similarity"],
                "metadata": r["metadata"] or {},
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )

    return {
        "query": query,
        "working_memory": working_context,
        "results_count": len(context_pieces),
        "long_term_memory": context_pieces,
        "sources": ["pgvector", "redis"],
    }


async def get_concepts(
    concept_id: str, depth: int = 1, relationship_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Retrieve related concepts from the OmegaKG knowledge graph via Guardian.

    TN-SOMA-304: Uses OmegaKGClient instead of direct Neo4j driver.

    Args:
        concept_id: The ID/Name of the starting concept
        depth: Traversal depth (default: 1)
        relationship_types: Optional list of relationship types to follow

    Returns:
        Graph subgraph showing related concepts
    """
    client = OmegaKGClient()

    # Build relationship filter clause
    rel_clause = ""
    if relationship_types:
        rel_types = "|".join([f":{t}" for t in relationship_types])
        rel_clause = f"-[{rel_types}*0..{depth}]-"
    else:
        rel_clause = f"-[*0..{depth}]-"

    # Simple traversal query (APOC may not be available via Guardian)
    query = f"""
    MATCH (start)-[r{rel_clause}](related)
    WHERE start.name = $concept_id OR start.id = $concept_id
    RETURN DISTINCT start, type(r) as rel_type, related
    LIMIT 50
    """

    try:
        # Note: Guardian query uses different parameter passing
        # Using a simpler query that works with string interpolation
        simple_query = f"""
        MATCH (start)
        WHERE start.name = '{concept_id}' OR start.id = '{concept_id}'
        OPTIONAL MATCH (start)-[r]->(related)
        RETURN start, type(r) as rel_type, related
        LIMIT 50
        """

        results = await client.query(simple_query, limit=50)

        nodes = []
        rels = []
        seen_nodes = set()

        for record in results:
            if record.get("start") and record["start"] not in seen_nodes:
                nodes.append(record["start"])
                seen_nodes.add(str(record["start"]))
            if record.get("related") and record["related"] not in seen_nodes:
                nodes.append(record["related"])
                seen_nodes.add(str(record["related"]))
            if record.get("rel_type"):
                rels.append(
                    {
                        "start": concept_id,
                        "type": record["rel_type"],
                        "end": str(record.get("related", {}).get("name", "unknown")),
                    }
                )

        return {
            "concept": concept_id,
            "node_count": len(nodes),
            "nodes": nodes,
            "relationships": rels,
        }

    except Exception as e:
        logger.error(f"OmegaKG query failed: {e}")
        return {"concept": concept_id, "error": str(e), "relations": []}


async def get_constraints(action_type: str, context_tags: List[str]) -> List[str]:
    """
    Get constraints from Mimir/Codex for a given action.

    Args:
        action_type: The type of action (e.g., "code_modification", "deployment")
        context_tags: Tags describing the context

    Returns:
        List of applicable constraints/rules
    """
    # Placeholder for Mimir integration
    return [
        "Constraint 1: Verify all changes with tests",
        "Constraint 2: Do not modify protected core files",
    ]
