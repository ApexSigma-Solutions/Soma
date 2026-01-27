"""Soma-specific MCP tools for memOS.

Tools for interacting with the Soma ecosystem:
- InGress (sensory data ingestion)
- OmegaKG (graph queries and codex promotion)
"""

import json
import logging
import os
from typing import Any, Dict

import httpx
from mcp import Tool

logger = logging.getLogger(__name__)

# Environment Configuration
INGRESS_URL = os.getenv("SOMA_INGRESS_URL", "http://localhost:8000")
INGRESS_API_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")
OMEGAKG_URL = os.getenv("OMEGA_KG_URL", "http://localhost:8765")

# Neo4j read-only client (for query_brain tool)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://apexsigma.neo4j.stable:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "omega_user")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "omega_dev_password")


# ============================================================================
# Tool: ingest_signal
# ============================================================================
@Tool()
async def ingest_signal(
    source: str,
    event_type: str,
    payload: Dict[str, Any],
) -> str:
    """Manually push data to InGress (The Senses).

    Use this to inject signals into the Soma sensory lake for processing.

    Args:
        source: Origin of data (obsidian, github, chrome, terminal, manual)
        event_type: Type of event (file_mod, push, web_capture, agent_thought)
        payload: JSON payload with signal data

    Returns:
        Status message with ingestion reference ID
    """
    endpoint = f"{INGRESS_URL}/api/v1/manual/ingest"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                endpoint,
                json={"source": source, "event_type": event_type, "payload": payload},
                headers={"X-API-Key": INGRESS_API_KEY},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("signal_ingested", ref=data.get("ref"), source=source)
            return f"✓ Signal ingested: {data.get('ref', 'unknown')}"

        except httpx.HTTPError as e:
            logger.error("ingress_failed", error=str(e))
            return f"✗ Ingestion failed: {str(e)}"


# ============================================================================
# Tool: query_brain
# ============================================================================
@Tool()
async def query_brain(cypher: str, limit: int = 10) -> str:
    """Search the Neo4j knowledge graph (read-only).

    Execute Cypher queries against the Soma Brain. Only SELECT/MATCH queries
    are allowed - no WRITE operations (CREATE/MERGE/DELETE).

    Args:
        cypher: Read-only Cypher query (MATCH/RETURN)
        limit: Maximum number of results to return

    Returns:
        JSON representation of query results
    """
    # Validate read-only query
    cypher_lower = cypher.strip().lower()
    if any(
        keyword in cypher_lower
        for keyword in ["create", "merge", "delete", "set", "remove"]
    ):
        return "✗ WRITE operations not allowed. memOS has read-only access to Neo4j."

    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        async with driver.session() as session:
            result = await session.run(cypher)
            records = await result.data()

            # Limit results
            records = records[:limit]

            await driver.close()

            logger.info("brain_query_success", count=len(records))
            return json.dumps(
                {"status": "success", "count": len(records), "results": records},
                indent=2,
            )

    except Exception as e:
        logger.error("brain_query_failed", error=str(e))
        return f"✗ Query failed: {str(e)}"


# ============================================================================
# Tool: promote_to_codex
# ============================================================================
@Tool()
async def promote_to_codex(
    constraint_type: str,
    rule: str,
    context: str,
    severity: str = "warning",
) -> str:
    """Promote working memory to the Codex of Consequences via OmegaKG.

    Use this to persist learned constraints into the Mirmir Protocol system.
    memOS does NOT write directly to Neo4j - it sends promotion requests to
    OmegaKG which has exclusive write authority.

    Args:
        constraint_type: Type of constraint (poison_pill, anti_pattern, known_failure)
        rule: The constraint rule to enforce
        context: Context and explanation for the constraint
        severity: Severity level (info, warning, critical)

    Returns:
        Status message with promotion confirmation
    """
    endpoint = f"{OMEGAKG_URL}/api/v1/codex/promote"

    payload = {
        "type": constraint_type,
        "rule": rule,
        "context": context,
        "severity": severity,
        "source": "memOS",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                endpoint,
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("codex_promoted", type=constraint_type)
            return f"✓ Promoted to Codex: {data.get('ref', 'unknown')}"

        except httpx.HTTPError as e:
            logger.error("codex_promotion_failed", error=str(e))
            return f"✗ Promotion failed: {str(e)}"
