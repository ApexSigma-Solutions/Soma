"""
Context tools for querying OmegaKG and PGVector.
"""

from typing import Any, Dict, List, Optional
import logging

from ..database.pgvector_store import get_pgvector_store
from ..database.neo4j import get_neo4j_driver
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
    # We use the agent_id or session_id if available to scope this
    # For now, if no session_id is passed, we might miss specific context
    # ideally retrieve_context should take session_id.
    # Looking at the signature, we don't have session_id.
    # Let's add session_id as an optional arg or rely on agent_id matching session.
    # For this iteration, we'll try to fetch recent scratchpad if agent_id is treated as session.
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
    Retrieve related concepts from the Neo4j knowledge graph.

    Args:
        concept_id: The ID/Name of the starting concept
        depth: Traversal depth (default: 1)
        relationship_types: Optional list of relationship types to follow

    Returns:
        Graph subgraph showing related concepts
    """
    driver = get_neo4j_driver()
    if not driver:
        return {
            "concept": concept_id,
            "error": "Neo4j driver not initialized",
            "relations": [],
        }

    query = """
    MATCH (start)
    WHERE (start.name = $concept_id OR start.id = $concept_id)
    CALL apoc.path.subgraphAll(start, {
        maxLevel: $depth,
        relationshipFilter: $rel_filter
    })
    YIELD nodes, relationships
    RETURN nodes, relationships
    """

    # Construct relationship filter (e.g., "RELATED_TO>|DEPENDS_ON")
    rel_filter = ">|<".join(relationship_types) if relationship_types else ""

    try:
        with driver.session() as session:
            result = session.run(
                query, concept_id=concept_id, depth=depth, rel_filter=rel_filter
            )
            record = result.single()

            if not record:
                return {
                    "concept": concept_id,
                    "message": "Concept not found",
                    "relations": [],
                }

            nodes = [dict(node) for node in record["nodes"]]
            rels = [
                {
                    "start": rel.start_node["name"]
                    if "name" in rel.start_node
                    else rel.start_node.id,
                    "type": rel.type,
                    "end": rel.end_node["name"]
                    if "name" in rel.end_node
                    else rel.end_node.id,
                    "properties": dict(rel),
                }
                for rel in record["relationships"]
            ]

            return {
                "concept": concept_id,
                "node_count": len(nodes),
                "nodes": nodes,
                "relationships": rels,
            }

    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
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
