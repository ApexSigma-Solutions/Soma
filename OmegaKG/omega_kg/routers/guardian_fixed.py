"""
Guardian Router - Security Fix for Cypher Injection

This file contains the Cypher injection vulnerability fix for the
OmegaKG Guardian router. The vulnerability was in line 295 where
request.node_label was interpolated directly into a Cypher query.

The fix introduces:
1. Enum validation for node labels
2. Whitelist of valid node types
3. Prevention of malicious label injection
"""

from fastapi import APIRouter, HTTPException, Header
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
import enum

from omega_kg.database.graph import graph_driver
from omega_kg.vector_store import get_vector_store
from omega_kg.utils.capture_utils import write_to_obsidian
from omega_kg.models.validation_schemas import KnowledgeDigest

logger = logging.getLogger("Soma.Guardian")

# ==============================================================================
# SECURITY FIX: Valid Node Labels Enum
# ==============================================================================

class ValidNodeLabels(enum.Enum):
    """
    Whitelist of valid Neo4j node labels.
    This prevents Cypher injection by enforcing a controlled set of labels.
    """
    ATOMIC_FACT = "AtomicFact"
    MEMORY_ATOM = "MemoryAtom"
    TASK = "Task"
    TASK_PLAN = "TaskPlan"
    ADR = "ADR"
    BACKLOG_PLAN = "BacklogPlan"
    PLAN = "Plan"
    CONSTRAINT = "Constraint"
    CONTEXT = "Context"
    INCIDENT = "Incident"
    CODE_BLOCK = "CodeBlock"
    ERROR_LOG = "ErrorLog"
    CONCEPT = "Concept"
    FILE = "File"
    LINEAR_ISSUE = "LinearIssue"

# ==============================================================================

SOMA_INTERNAL_KEY = os.getenv("SOMA_INTERNAL_KEY")

# The Codex of Consequences (In-Memory Cache for poison pills)
# Maps File Hash -> Consequence (e.g., "POISON_PILL", "DUPLICATE")
CODEX_HASH_CACHE: Dict[str, str] = {}

router = APIRouter(
    prefix="/guardian",
    tags=["Guardian", "Immune System"],
    responses={403: {"description": "Immune Response Triggered (Blocked)"}},
)

# ==============================================================================
# DEPENDENCIES
# ==============================================================================

async def verify_soma_key(x_soma_key: str = Header(...)):
    """
    Validates that the request comes from a verified organ (Stomach/Hands).
    This is the Autoimmune Response - blocks unauthorized writes to Neo4j.
    """
    if not SOMA_INTERNAL_KEY:
        logger.warning("SOMA_INTERNAL_KEY not configured - immune system disabled")
        return "disabled"
    if x_soma_key != SOMA_INTERNAL_KEY:
        logger.warning(
            f"Autoimmune Alert: Invalid Internal Key provided: {x_soma_key[:4]}***"
        )
        raise HTTPException(
            status_code=403, detail="Soma Autoimmune Response: Unauthorized Organ"
        )
    return x_soma_key


# ==============================================================================
# SECURITY VALIDATION
# ==============================================================================

def validate_node_label(label: str) -> str:
    """
    Validate and sanitize a Neo4j node label to prevent Cypher injection.

    Args:
        label: Proposed node label from request

    Returns:
        Validated label name

    Raises:
        HTTPException: If label is not in whitelist
    """
    try:
        # Convert to enum value to validate
        validated = ValidNodeLabels(label)
        return validated.value
    except ValueError:
        logger.error(
            f"Attempted to use invalid node label: {label}. "
            f"This may indicate a Cypher injection attempt."
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node label: {label}. "
                   f"Allowed labels: {[l.value for l in ValidNodeLabels]}"
        )


# ==============================================================================
# Pydantic Models - Flexible Knowledge Schema
# ==============================================================================
# Models imported from omega_kg.models.validation_schemas for consistency


# ==============================================================================
# ROUTES
# ==============================================================================

@router.post("/store_embedding")
async def store_embedding(
    request: CommitRequest,
    soma_key: str = Depends(verify_soma_key),
):
    """
    Store an embedding for an existing node (or create anchor) in Neo4j.
    Used by InGest Vector Indexer.

    SECURITY FIX: Node label is now validated before Cypher execution.
    """
    async with graph_driver.session() as session:
        # SECURITY FIX: Validate node_label BEFORE using it in Cypher
        validated_label = validate_node_label(request.node_label)

        # Update existing node or create generic MemoryAtom
        # We try to match by raw_id/digest_id
        result = await session.run(
            f"""
            MERGE (n:{validated_label} {{raw_id: $raw_id}})
            SET n.embedding = $embedding,
                n.processed_at = datetime()
            RETURN elementId(n) as id
            """,
            raw_id=request.raw_id,
            embedding=request.embedding,
        )
        record = await result.single()
        node_id = record["id"] if record else "unknown"

        return CommitResponse(
            success=True,
            message="Embedding stored",
            storage_results={"graph": {"node_id": node_id}},
        )


# ==============================================================================

def _evaluate_relevance(request: CommitRequest) -> bool:
    """
    Guardian logic to determine if data is worth storing.