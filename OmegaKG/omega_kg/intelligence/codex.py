"""
Codex - The Knowledge Graph Interface

Codex provides a clean interface to Neo4j for retrieving constraints and contexts.
It handles connection management and data retrieval.
"""

import logging
from typing import List, Optional
from neo4j import GraphDatabase
from omega_kg.settings import settings

from .models import Constraint, Context
from .exceptions import (
    CodexConnectionError,
    ConstraintNotFoundError,
    ContextNotFoundError,
)

logger = logging.getLogger(__name__)


class Codex:
    """
    Interface to the Knowledge Graph (Neo4j) for constraint retrieval.

    Codex manages the connection to Neo4j and provides methods to retrieve
    constraints and contexts from the graph.
    """

    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Initialize Codex with Neo4j connection parameters.

        Args:
            uri: Neo4j URI (defaults to settings.NEO4J_URI)
            username: Neo4j username (defaults to settings.NEO4J_USER)
            password: Neo4j password (defaults to settings.NEO4J_PASSWORD)
        """
        self._uri = uri or settings.neo4j_uri
        self._username = username or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._driver: Optional[GraphDatabase.driver] = None
        self._connected = False

    def connect(self) -> None:
        """
        Establish connection to Neo4j.

        Raises:
            CodexConnectionError: If connection fails
        """
        try:
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._username, self._password)
            )
            # Verify connection
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"✅ Codex connected to Neo4j at {self._uri}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise CodexConnectionError(f"Failed to connect to Neo4j: {e}")

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._connected = False
            logger.info("Codex connection closed")

    def is_connected(self) -> bool:
        """Check if Codex is connected to Neo4j."""
        return self._connected

    def get_constraints(self, context: str = None) -> List[Constraint]:
        """
        Retrieve constraints from the Knowledge Graph.

        Args:
            context: Optional context name to filter constraints

        Returns:
            List of Constraint objects

        Raises:
            CodexConnectionError: If not connected to Neo4j
        """
        if not self._connected:
            raise CodexConnectionError("Codex is not connected to Neo4j")

        constraints = []

        try:
            with self._driver.session() as session:
                if context:
                    # Get constraints for a specific context
                    result = session.run(
                        """
                        MATCH (c:Constraint)-[:GOVERNS]->(ctx:Context {name: $context})
                        RETURN c
                    """,
                        context=context,
                    )
                else:
                    # Get all constraints
                    result = session.run("MATCH (c:Constraint) RETURN c")

                for record in result:
                    node = record["c"]
                    constraint = Constraint(
                        id=node["id"],
                        description=node.get("description", ""),
                        severity=node.get("severity", "WARNING"),
                        created_at=node.get("created_at"),
                    )
                    constraints.append(constraint)

                logger.info(
                    f"Retrieved {len(constraints)} constraints"
                    + (f" for context '{context}'" if context else "")
                )

        except Exception as e:
            logger.error(f"Failed to retrieve constraints: {e}")
            raise

        return constraints

    def get_constraint(self, constraint_id: str) -> Constraint:
        """
        Retrieve a specific constraint by ID.

        Args:
            constraint_id: Unique constraint identifier

        Returns:
            Constraint object

        Raises:
            ConstraintNotFoundError: If constraint not found
            CodexConnectionError: If not connected to Neo4j
        """
        if not self._connected:
            raise CodexConnectionError("Codex is not connected to Neo4j")

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Constraint {id: $id})
                    RETURN c
                """,
                    id=constraint_id,
                )

                record = result.single()
                if not record:
                    raise ConstraintNotFoundError(
                        f"Constraint '{constraint_id}' not found"
                    )

                node = record["c"]
                return Constraint(
                    id=node["id"],
                    description=node.get("description", ""),
                    severity=node.get("severity", "WARNING"),
                    created_at=node.get("created_at"),
                )

        except ConstraintNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve constraint '{constraint_id}': {e}")
            raise

    def get_contexts(self) -> List[Context]:
        """
        Retrieve all contexts from the Knowledge Graph.

        Returns:
            List of Context objects

        Raises:
            CodexConnectionError: If not connected to Neo4j
        """
        if not self._connected:
            raise CodexConnectionError("Codex is not connected to Neo4j")

        contexts = []

        try:
            with self._driver.session() as session:
                result = session.run("MATCH (c:Context) RETURN c")

                for record in result:
                    node = record["c"]
                    context = Context(
                        name=node["name"], description=node.get("description")
                    )
                    contexts.append(context)

                logger.info(f"Retrieved {len(contexts)} contexts")

        except Exception as e:
            logger.error(f"Failed to retrieve contexts: {e}")
            raise

        return contexts

    def get_context(self, name: str) -> Context:
        """
        Retrieve a specific context by name.

        Args:
            name: Context name

        Returns:
            Context object

        Raises:
            ContextNotFoundError: If context not found
            CodexConnectionError: If not connected to Neo4j
        """
        if not self._connected:
            raise CodexConnectionError("Codex is not connected to Neo4j")

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Context {name: $name})
                    RETURN c
                """,
                    name=name,
                )

                record = result.single()
                if not record:
                    raise ContextNotFoundError(f"Context '{name}' not found")

                node = record["c"]
                return Context(name=node["name"], description=node.get("description"))

        except ContextNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve context '{name}': {e}")
            raise

    def metabolize_failure(self, incident_report: str) -> Constraint:
        """
        Parse an incident report and create a new constraint.

        Args:
            incident_report: Text description of the incident

        Returns:
            Constraint object (DB insertion optional for this task)
        """
        from .models import Constraint, SeverityLevel
        from datetime import datetime

        import hashlib

        # Extract key information from incident report
        # Simple heuristic: look for patterns like "missing", "failed", "error"
        description = incident_report.strip()

        # Generate constraint ID
        digest = hashlib.md5(description.encode("utf-8")).hexdigest()
        constraint_id = f"ENV_{digest[:8].upper()}"

        # Determine severity based on keywords
        severity = (
            SeverityLevel.CRITICAL
            if "critical" in description.lower()
            else SeverityLevel.WARNING
        )

        constraint = Constraint(
            id=constraint_id,
            description=description,
            severity=severity,
            created_at=datetime.now(),
        )

        logger.info(f"Metabolized failure into constraint: {constraint_id}")
        return constraint

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
