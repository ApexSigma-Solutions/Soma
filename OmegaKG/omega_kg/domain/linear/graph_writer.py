"""
Graph Writer - Linear Domain Service

Projects Linear Pydantic models into Neo4j graph topology.
Uses idempotent MERGE operations (Leaf -> Hub -> Edge pattern).
Phase 6: TN-LINEAR-06 - Graph Topology
Phase 7: TN-LINEAR-07 - Embedding enrichment
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.domain.linear.models import LinearIssue, LinearUser

logger = logging.getLogger(__name__)

# Embedding configuration (Phase 7)
EMBEDDING_DIMENSIONS = 1024


class GraphWriter:
    """
    Domain service for projecting Linear Models into the Neo4j Graph.
    Uses idempotent MERGE operations (Leaf -> Hub -> Edge).
    """

    def __init__(self, driver: AsyncGraphDriver):
        self.driver = driver

    async def upsert_user(self, user: LinearUser):
        """
        Merges a LinearUser node into the graph.
        """
        query = """
        MERGE (u:LinearUser {id: $id})
        SET u.name = $name,
            u.email = $email,
            u.active = $active,
            u.updated_at = $updated_at
        RETURN u.id as id
        """

        # Safe handling of Optional fields
        updated_at_iso = (
            user.updatedAt.isoformat() if user.updatedAt else datetime.now().isoformat()
        )

        params = {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "active": user.active,
            "updated_at": updated_at_iso,
        }

        try:
            async with self.driver.session() as session:
                await session.run(query, params)
                logger.debug(f"Upserted User: {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Failed to upsert User {user.id}: {e}")
            raise

    async def upsert_issue(
        self, issue: LinearIssue, embedding: Optional[List[float]] = None
    ):
        """
        Merges a LinearIssue node and establishes relationships.
        Direction: (Issue)-[:ASSIGNED_TO]->(User)

        Args:
            issue: The LinearIssue to upsert
            embedding: Optional 1024-dim vector for semantic search (Phase 7)

        Raises:
            ValueError: If embedding is provided but not exactly 1024 dimensions
        """
        # Validate embedding dimensions if provided
        if embedding is not None and len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Embedding must be exactly {EMBEDDING_DIMENSIONS} floats, "
                f"got {len(embedding)}"
            )

        # 1. Upsert the Issue Node (base properties)
        issue_query = """
        MERGE (i:LinearIssue {id: $id})
        SET i.identifier = $identifier,
            i.title = $title,
            i.priority = $priority,
            i.status = $status,
            i.url = $url,
            i.created_at = $created_at,
            i.updated_at = $updated_at
        """

        # Conditionally add embedding to the SET clause
        if embedding is not None:
            issue_query += ", i.embedding = $embedding"

        # Safe handling of Optional timestamps - store None instead of current time for missing data
        created_at_iso = issue.createdAt.isoformat() if issue.createdAt else None
        updated_at_iso = issue.updatedAt.isoformat() if issue.updatedAt else None
        status_name = issue.state.name if issue.state else "Unknown"

        params: Dict[str, Any] = {
            "id": str(issue.id),
            "identifier": issue.identifier,
            "title": issue.title,
            "priority": issue.priority,
            "status": status_name,
            "url": issue.url,
            "created_at": created_at_iso,
            "updated_at": updated_at_iso,
        }

        # Add embedding to params if provided (Phase 7)
        if embedding is not None:
            params["embedding"] = embedding

        async with self.driver.session() as session:
            try:
                await session.run(issue_query, params)
                logger.debug(f"Upserted Issue: {issue.identifier}")

                # 2. Handle Assignee Relationship
                if issue.assignee:
                    await self.upsert_user(issue.assignee)

                    # Direction: (Issue) -> (User)
                    assign_query = """
                    MATCH (i:LinearIssue {id: $issue_id})
                    MATCH (u:LinearUser {id: $user_id})
                    MERGE (i)-[r:ASSIGNED_TO]->(u)
                    RETURN type(r)
                    """
                    await session.run(
                        assign_query,
                        {
                            "issue_id": str(issue.id),
                            "user_id": str(issue.assignee.id),
                        },
                    )
                    logger.debug(
                        f"Linked Issue {issue.identifier} -> User {issue.assignee.name}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to process graph topology for Issue {issue.identifier}: {e}"
                )
                # Raise to ensure data consistency in pipeline
                raise
