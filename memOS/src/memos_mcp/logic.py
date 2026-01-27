"""
Core logic layer for memOS MCP Server.

This module provides the business logic for memory operations, bridging
the MCP server interface with the database layer.
"""

import logging
from typing import Any, Dict, List, Optional

from memos_mcp.database import get_database, get_pgvector_store
from memos_mcp.config import settings

logger = logging.getLogger(__name__)


class MemosLogic:
    """Core logic layer for memOS MCP Server."""

    def __init__(self, settings_obj=None):
        """Initialize the MemosLogic layer."""
        self.settings = settings_obj or settings
        self.db = None
        self._pgvector = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connections."""
        self.db = get_database()
        self._pgvector = get_pgvector_store()
        # Pre-warm the connection pool
        await self._pgvector._get_pool()
        self._initialized = True
        logger.info("✅ MemosLogic initialized with PGVectorStore")

    async def shutdown(self):
        """Shutdown database connections."""
        logger.info("🛑 MemosLogic shutting down...")
        if self._pgvector:
            await self._pgvector.close()
        self.db = None
        self._pgvector = None
        self._initialized = False

    async def search(self, query: str, limit: int = 5) -> str:
        """
        Search memories using semantic similarity.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            String representation of search results
        """
        try:
            results = await retrieve_context("default", query, limit)
            if not results:
                return f"No memories found for query: {query}"

            # Format results for display
            formatted = []
            for r in results:
                score = r.get("similarity", 0)
                content = r.get("content", "")[:200]  # Truncate for display
                formatted.append(f"[{score:.2f}] {content}...")

            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Search failed: {e}"

    async def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory with embedding.

        Args:
            content: The memory content to store
            tags: Optional list of tags
            metadata: Optional full metadata dictionary. If provided, tags are merged into it.

        Returns:
            String representation of the result
        """
        try:
            # Prepare metadata
            final_metadata = metadata or {}
            if tags:
                # Merge tags into metadata, potentially appending if 'tags' key exists
                existing_tags = final_metadata.get("tags", [])
                if isinstance(existing_tags, list):
                    final_metadata["tags"] = list(set(existing_tags + tags))
                else:
                    final_metadata["tags"] = tags

            result = await store_memory("default", content, final_metadata)
            if result.get("status") == "success":
                return f"Memory stored successfully (ID: {result.get('memory_id')})"
            return f"Store failed: {result.get('message')}"
        except Exception as e:
            logger.error(f"Store error: {e}")
            return f"Store failed: {e}"

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        if not self._pgvector:
            return {"error": "PGVectorStore not initialized"}
        try:
            return await self._pgvector.get_stats()
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"error": str(e)}


async def store_memory(
    agent_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store persistent memory for an agent with vector embedding.

    Args:
        agent_id: ID of the agent storing the memory
        content: The memory content
        metadata: Optional metadata dict

    Returns:
        Dict with status, memory_id, and embedding info
    """
    pgvector = get_pgvector_store()

    try:
        # Extract tags from metadata if present
        tags = None
        if metadata and "tags" in metadata:
            tags = metadata.pop("tags", None)

        # Generate embedding
        embedding = await pgvector.generate_embedding(content)

        memory_id = await pgvector.store_memory(
            content=content,
            agent_id=agent_id,
            embedding=embedding,
            embedding_model=settings.embedding_model,
            metadata=metadata,
            tags=tags,
        )

        logger.info(f"Stored memory {memory_id} for agent {agent_id}")
        return {
            "status": "success",
            "memory_id": memory_id,
            "has_embedding": True,
            "embedding_model": settings.embedding_model,
        }

    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        return {"status": "error", "message": str(e)}


async def retrieve_context(
    agent_id: str,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context from agent memory using semantic search.

    Args:
        agent_id: ID of the agent
        query: The search query
        top_k: Number of results to return
        score_threshold: Minimum similarity score

    Returns:
        List of matching memories with similarity scores
    """
    pgvector = get_pgvector_store()

    try:
        # Generate query embedding
        query_embedding = await pgvector.generate_embedding(query)

        results = await pgvector.search_memories(
            query_embedding=query_embedding,
            top_k=top_k,
            score_threshold=score_threshold,
            agent_id=agent_id if agent_id != "default" else None,
        )

        logger.debug(f"Retrieved {len(results)} memories for query")
        return results

    except Exception as e:
        logger.error(f"Failed to retrieve context: {e}")
        return []


async def register_tool(
    tool_name: str,
    description: str,
    usage: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Register tool awareness in agent memory."""
    db = get_database()
    try:
        tool_id = db.register_tool(
            name=tool_name, description=description, usage=usage, tags=tags
        )
        if tool_id is None:
            return {"status": "error", "message": "Failed to register tool"}
        return {"status": "success", "tool_id": tool_id}
    except Exception as e:
        logger.error(f"Failed to register tool: {e}")
        return {"status": "error", "message": str(e)}


async def memory_graph(agent_id: str) -> Dict[str, Any]:
    """Access agent's memory graph structure."""
    # TODO: Implement Neo4j graph integration
    return {"agent_id": agent_id, "nodes": [], "edges": []}


async def tool_registry() -> List[Dict[str, Any]]:
    """Access agent's known tools."""
    db = get_database()
    try:
        return db.get_all_tools()
    except Exception as e:
        logger.error(f"Failed to get all tools: {e}")
        return []


async def get_memory(memory_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single memory by ID."""
    pgvector = get_pgvector_store()
    try:
        return await pgvector.get_memory(memory_id)
    except Exception as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        return None


async def delete_memory(memory_id: int, agent_id: str = "system") -> bool:
    """Delete a memory by ID."""
    pgvector = get_pgvector_store()
    try:
        return await pgvector.delete_memory(memory_id, agent_id)
    except Exception as e:
        logger.error(f"Failed to delete memory {memory_id}: {e}")
        return False
