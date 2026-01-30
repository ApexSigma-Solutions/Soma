import os
from fastapi import APIRouter, HTTPException, Header, Depends
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


# Security validation function
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
            f"Allowed labels: {[l.value for l in ValidNodeLabels]}",
        )


# ==============================================================================

# --- CONFIGURATION ---
SOMA_INTERNAL_KEY = os.getenv("SOMA_INTERNAL_KEY")

# The Codex of Consequences (In-Memory Cache for poison pills)
# Maps File Hash -> Consequence (e.g., "POISON_PILL", "DUPLICATE")
CODEX_HASH_CACHE: Dict[str, str] = {}

router = APIRouter(
    prefix="/guardian",
    tags=["Guardian", "Immune System"],
    responses={403: {"description": "Immune Response Triggered (Blocked)"}},
)


# --- DEPENDENCIES ---
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


# =============================================================================
# Pydantic Models - Flexible Knowledge Schema
# =============================================================================
# Models imported from omega_kg.models.validation_schemas for consistency


class CommitRequest(BaseModel):
    raw_id: str
    type: str  # 'conversation', 'terminal', 'memory_atom', or any custom type
    digest: KnowledgeDigest
    metadata: Dict[str, Any] = {}


class CommitResponse(BaseModel):
    success: bool
    message: str
    storage_results: Dict[str, Any]


class IngestRequest(BaseModel):
    """Request for hash-based poison pill validation."""

    file_hash: str
    file_name: str
    source_organ: str
    metadata: Optional[Dict[str, Any]] = None


class ValidateRequest(BaseModel):
    """Request to validate content against Codex of Consequences."""

    content: str
    context: Optional[str] = None
    action_type: Optional[str] = None  # e.g., 'write_neo4j', 'ingest_file'


class ValidateResponse(BaseModel):
    """Validation result from Mirmir Protocol check."""

    allowed: bool
    violations: List[str] = []
    warnings: List[str] = []
    codex_rules_checked: int = 0


class StoreEmbeddingRequest(BaseModel):
    """Request from InGest to store embedding via Guardian (sole writer)."""

    raw_id: str
    node_label: str
    embedding: List[float]
    content: Optional[str] = None


# =============================================================================
# Codex of Consequences (Mirmir Protocol)
# =============================================================================

# Known failure patterns - these would be stored in Neo4j in production
CODEX_RULES = [
    {
        "id": "CON-001",
        "pattern": "null bytes",
        "description": "Binary null bytes cause infinite retry loops (EVT-LOOP-589)",
        "action": "block",
    },
    {
        "id": "CON-002",
        "pattern": "UTF-16 BOM",
        "description": "UTF-16 encoded files crash the parser",
        "action": "block",
    },
    {
        "id": "CON-003",
        "pattern": "vector_index_worker",
        "description": "Direct Neo4j writes from workers cause auth rate limits",
        "action": "warn",
    },
]


async def _check_codex(content: str, context: Optional[str] = None) -> ValidateResponse:
    """Validate content against the Codex of Consequences.

    Part of the Mirmir Protocol - institutional learning from failure.
    """
    violations = []
    warnings = []

    for rule in CODEX_RULES:
        pattern = rule["pattern"].lower()
        check_content = (content + (context or "")).lower()

        if pattern in check_content:
            if rule["action"] == "block":
                violations.append(f"[{rule['id']}] {rule['description']}")
            else:
                warnings.append(f"[{rule['id']}] {rule['description']}")

    return ValidateResponse(
        allowed=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        codex_rules_checked=len(CODEX_RULES),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/validate", response_model=ValidateResponse)
async def validate_against_codex(request: ValidateRequest) -> ValidateResponse:
    """Validate content against Mirmir Protocol Codex of Consequences.

    This endpoint checks proposed actions/content against known failure patterns.
    Used by InGest and other services before committing data.
    """
    logger.info(f"Guardian validating content (action: {request.action_type})")
    return await _check_codex(request.content, request.context)


@router.post("/validate/hash")
async def validate_ingest_hash(
    request: IngestRequest,
    authorized: str = Depends(verify_soma_key),
):
    """
    Mirmir Protocol Validation - Hash-based poison pill check.
    Checks the Codex of Consequences before allowing ingestion.
    """
    logger.info(
        f"Guardian scanning artifact: {request.file_name} ({request.file_hash})"
    )

    # 1. Check Codex for known Poison Pills
    if request.file_hash in CODEX_HASH_CACHE:
        consequence = CODEX_HASH_CACHE[request.file_hash]
        if consequence == "POISON_PILL":
            logger.error(
                f"Guardian Block: Known Poison Pill detected: {request.file_hash}"
            )
            raise HTTPException(
                status_code=409, detail="Codex Restriction: This artifact is toxic."
            )

    return {"status": "ALLOWED", "message": "Artifact cleared for metabolism."}


@router.post("/codex/log")
async def log_consequence(
    file_hash: str,
    consequence: str,
    authorized: str = Depends(verify_soma_key),
):
    """
    Metabolize Failure: Log a toxic artifact to the Codex.
    Called by InGest when it catches a Poison Pill.
    """
    CODEX_HASH_CACHE[file_hash] = consequence
    logger.warning(f"Codex Updated: {file_hash} marked as {consequence}")
    return {"status": "LOGGED"}


@router.post("/commit", response_model=CommitResponse)
async def commit_knowledge(
    request: CommitRequest,
    authorized: str = Depends(verify_soma_key),
) -> CommitResponse:
    """
    Guardian endpoint to commit prepped knowledge to the ecosystem.
    Evaluates relevance via Codex and handles distribution to Graph, Vault, and Vector tiers.

    This is the SOLE writer to Neo4j - all services must commit through Guardian.
    """
    logger.info(f"Guardian received commit request for {request.type}:{request.raw_id}")

    # 1. Codex Validation (Mirmir Protocol)
    codex_result = await _check_codex(request.digest.summary, request.type)
    if not codex_result.allowed:
        logger.warning(
            f"Codex violations for {request.raw_id}: {codex_result.violations}"
        )
        return CommitResponse(
            success=False,
            message=f"Blocked by Codex: {', '.join(codex_result.violations)}",
            storage_results={
                "status": "codex_blocked",
                "violations": codex_result.violations,
            },
        )

    # Log warnings but continue
    if codex_result.warnings:
        logger.warning(f"Codex warnings for {request.raw_id}: {codex_result.warnings}")

    # 2. Noise Filter / Relevance Check
    is_relevant = _evaluate_relevance(request)
    if not is_relevant:
        return CommitResponse(
            success=True,
            message="Item marked as noise and skipped for persistence.",
            storage_results={"status": "filtered_out"},
        )

    results = {}

    # 3. Neo4j - Graph Topology (Guardian is sole writer)
    try:
        results["graph"] = await _store_graph(request)
    except Exception as e:
        logger.error(f"Graph storage failed: {e}")
        results["graph"] = {"success": False, "error": str(e)}

    # 4. Obsidian - Documentation Tier
    try:
        results["vault"] = await _store_vault(request)
    except Exception as e:
        logger.error(f"Vault storage failed: {e}")
        results["vault"] = {"success": False, "error": str(e)}

    # 5. Vector Store - Handled within Graph Storage (Neo4j Vector Index)
    # Historic PGVector write disabled in favor of consolidated Neo4j storage
    results["vector"] = {"success": True, "message": "Stored in Neo4j Graph"}

    return CommitResponse(
        success=True,
        message=f"Knowledge committed for {request.raw_id}",
        storage_results=results,
    )


@router.post("/store_embedding", response_model=CommitResponse)
async def store_embedding(
    request: StoreEmbeddingRequest,
    x_soma_key: str = Depends(verify_soma_key),
):
    """
    Store an embedding for an existing node (or create anchor) in Neo4j.
    Used by InGest Vector Indexer.
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


def _evaluate_relevance(request: CommitRequest) -> bool:
    """
    Guardian logic to determine if data is worth storing.
    Currently a simple heuristic, but intended for LLM evaluation.
    """
    # Filter out empty or extremely short summaries
    if len(request.digest.summary) < 20:
        return False

    # Filter out known 'noise' patterns in terminal
    if request.type == "terminal":
        command = request.metadata.get("command", "")
        if any(p in command for p in ["ls", "cd", "clear", "cls", "dir"]):
            return False

    return True


async def _store_graph(request: CommitRequest) -> Dict:
    """Store nodes and edges from flexible digest to Neo4j.

    Supports both:
    - New flexible schema (nodes/edges with arbitrary labels and properties)
    - Legacy schema (entities with name/type)
    """
    async with graph_driver.session() as session:
        node_count = 0
        edge_count = 0

        # 1. Create the root MemoryAtom node (anchor for this digest)
        await session.run(
            """
            MERGE (m:MemoryAtom {raw_id: $raw_id})
            SET m.title = $title,
                m.summary = $summary,
                m.type = $type,
                m.embedding = $embedding,
                m.processed_at = datetime()
            """,
            raw_id=request.raw_id,
            title=request.digest.title,
            summary=request.digest.summary,
            type=request.type,
            embedding=request.digest.embedding,
        )
        node_count += 1

        # 2. Create flexible nodes (new schema)
        node_id_map = {}  # Map digest node IDs to Neo4j elementIds
        for node in request.digest.nodes:
            # Dynamically build property SET clause
            props = {**node.properties, "digest_id": request.raw_id}
            result = await session.run(
                f"""
                MERGE (n:{node.label} {{id: $node_id, digest_id: $digest_id}})
                SET n += $props
                RETURN elementId(n) as neo4j_id
                """,
                node_id=node.id,
                digest_id=request.raw_id,
                props=props,
            )
            record = await result.single()
            if record:
                node_id_map[node.id] = record["neo4j_id"]
            node_count += 1

            # Link to root MemoryAtom
            await session.run(
                f"""
                MATCH (m:MemoryAtom {{raw_id: $raw_id}})
                MATCH (n:{node.label} {{id: $node_id, digest_id: $digest_id}})
                MERGE (m)-[:CONTAINS]->(n)
                """,
                raw_id=request.raw_id,
                node_id=node.id,
                digest_id=request.raw_id,
            )

        # 3. Create flexible edges (new schema)
        for edge in request.digest.edges:
            # Find source and target nodes by their digest IDs
            await session.run(
                f"""
                MATCH (src {{id: $source_id, digest_id: $digest_id}})
                MATCH (tgt {{id: $target_id, digest_id: $digest_id}})
                MERGE (src)-[r:{edge.type}]->(tgt)
                SET r += $props
                """,
                source_id=edge.source_id,
                target_id=edge.target_id,
                digest_id=request.raw_id,
                props=edge.properties,
            )
            edge_count += 1

        # 4. Store embedding on root node if provided
        if request.digest.embedding:
            await session.run(
                """
                MATCH (m:MemoryAtom {raw_id: $raw_id})
                SET m.embedding = $embedding
                """,
                raw_id=request.raw_id,
                embedding=request.digest.embedding,
            )

        return {
            "success": True,
            "nodes_created": node_count,
            "edges_created": edge_count,
            "root_type": "MemoryAtom",
        }


async def _store_vault(request: CommitRequest) -> Dict:
    """Store digest to Obsidian vault as markdown note."""
    tags_str = ", ".join(request.digest.tags)
    safe_type = request.type.lower().replace(" ", "_")

    # Extract node summaries for the markdown
    node_lines = []
    for node in request.digest.nodes:
        name = node.properties.get("name", node.properties.get("content", node.id))
        node_lines.append(f"- **{node.label}**: {name}")

    # Extract edge summaries
    edge_lines = []
    for edge in request.digest.edges:
        edge_lines.append(f"- {edge.source_id} --[{edge.type}]--> {edge.target_id}")

    content = f"""---
uid: {request.raw_id}
title: {request.digest.title}
type: {request.type}
tags: [{tags_str}]
created: {datetime.utcnow().isoformat()}
---

# {request.digest.title}

## Summary
{request.digest.summary}

## Nodes
{chr(10).join(node_lines) if node_lines else "_No nodes extracted_"}

## Relationships
{chr(10).join(edge_lines) if edge_lines else "_No relationships extracted_"}
"""
    write_to_obsidian(safe_type, content, request.raw_id[:8])
    return {"success": True, "path": f"{safe_type}/{request.raw_id[:8]}.md"}


async def _store_vector(request: CommitRequest) -> Dict:
    vector_store = await get_vector_store()

    # Determine node label based on type
    if request.type == "conversation":
        node_label = "ChatSession"
    elif request.type == "terminal":
        node_label = "TerminalExecution"
    else:
        node_label = "Entity"  # Default fallback

    # Use asynchronous store_pending method
    # Content and metadata are stored in Neo4j (via _store_graph) and PGVector (via worker)
    # The store_pending method only queues the ID for embedding generation
    vector_id = await vector_store.store_pending(
        message_id=request.raw_id,
        node_label=node_label,
    )
    return {"success": True, "vector_id": vector_id}


@router.get("/health")
async def health_check():
    """Guardian immune system health check."""
    return {
        "system": "Guardian",
        "status": "ACTIVE",
        "codex_entries": len(CODEX_HASH_CACHE),
        "immune_system": "ENABLED" if SOMA_INTERNAL_KEY else "DISABLED",
    }
