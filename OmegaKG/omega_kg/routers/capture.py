"""
Capture Router

FastAPI router for conversation capture endpoints.
Handles Chrome extension conversation capture, JWT token exchange, and vector health checks.

Extracted from capture_server.py for modularity.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Security, Depends
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from omega_kg.auth_utils import (
    create_access_token,
    get_static_api_key,
    validate_access_token,
)

# Use Ingest Session for Raw Storage (same as Terminal)
from omega_kg.database.ingest_session import get_ingest_db
from omega_kg.models.capture import CaptureResponse, ConversationData, Token
from pydantic import BaseModel

from omega_kg.parsers import parse_html_content
from omega_kg.settings import settings
from omega_kg.utils.capture_utils import (
    generate_conversation_hash,
)
from omega_kg.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Security limits
MAX_HTML_SIZE = (
    10 * 1024 * 1024
)  # 10MB - increased to accommodate larger conversation captures

router = APIRouter(prefix="/capture", tags=["Capture"])


class OmegaStats(BaseModel):
    total_captures: int
    recent_captures_24h: int
    neo4j_status: str
    postgres_status: str
    active_sessions: int


# Import percolate function from main module (to avoid circular import)
# This will be injected/passed when the router is used
_percolate_to_neo4j_with_embedding = None


def set_percolate_function(func):
    """Set the percolate function to avoid circular imports."""
    global _percolate_to_neo4j_with_embedding
    _percolate_to_neo4j_with_embedding = func


@router.post("/auth/token", response_model=Token)
async def login_for_access_token(
    _api_key: str = Security(get_static_api_key),
) -> Token:
    """
    Exchange static API key for a short-lived JWT Bearer token.

    The Chrome extension calls this endpoint with the bootstrap API key (X-API-Key header)
    to receive a short-lived JWT token for subsequent API requests.

    Args:
        _api_key: Validated static API key from X-API-Key header

    Returns:
        Token model with access_token and token_type

    Raises:
        HTTPException: 403 if API key is invalid
    """
    logger.info("Token request received")
    access_token = create_access_token(data={"sub": "chrome_extension_user"})
    return Token(access_token=access_token, token_type="bearer")


@router.options("/capture")
async def capture_options():
    """Handle CORS preflight requests for /capture endpoint"""
    return {"message": "CORS preflight OK"}


@router.post("/capture", response_model=CaptureResponse)
async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
    db_session: Any = Depends(get_ingest_db),
) -> CaptureResponse:
    """
    Capture a conversation from the Chrome extension.

    Writes raw JSON to 'raw_ingestions' table in Ingest Database using
    the consolidated RawIngestion model from InGest-LLM service.
    """
    # --- Security Hardening ---
    # 1. Check Content-Length Header (Fail Fast)
    content_length = int(request.headers.get("content-length", 0))
    if content_length > MAX_HTML_SIZE:
        logger.warning(f"Payload too large: {content_length} bytes")
        raise HTTPException(
            status_code=413,
            detail=f"Payload exceeds maximum allowed size of {MAX_HTML_SIZE} bytes",
        )

    # 2. Check parsed HTML content size (Logic Validation)
    if hasattr(data, "raw_html") and data.raw_html:
        if len(data.raw_html) > MAX_HTML_SIZE:
            logger.warning("HTML content field exceeds limit")
            raise HTTPException(status_code=413, detail="HTML content too large")

    # 3. PARSING LOGIC
    if (not data.messages) and data.raw_html:
        logger.info(
            f"Detecting Raw HTML. Attempting server-side parsing for: {data.url}"
        )
        try:
            data.messages = parse_html_content(data.raw_html, data.url or "unknown")
            logger.info(f"✓ Successfully parsed {len(data.messages)} messages.")
        except Exception as e:
            logger.error(f"HTML Parsing failed: {e}")
            data.messages = [{"role": "system", "content": f"Parsing failed: {e}"}]

    # 4. VALIDATION
    if not data.messages and not data.content:
        raise HTTPException(
            status_code=422, detail="No messages provided and HTML parsing failed."
        )

    # 5. STORAGE to raw_lake table (unified data lake)
    try:
        conv_hash = generate_conversation_hash(data)

        # Map platform to source/event_type for unified raw_lake
        source = "chrome"  # All Chrome extension captures
        event_type = (
            f"conversation-{data.platform}" if data.platform else "conversation-unknown"
        )

        # Get client IP from request
        client_ip = request.client.host if request.client else None

        # Direct insert to raw_lake table
        insert_stmt = text("""
            INSERT INTO raw_lake (source, event_type, payload, client_ip, ingested_at, processing_status)
            VALUES (:source, :event_type, :payload::jsonb, :client_ip, NOW(), 'PENDING')
            ON CONFLICT DO NOTHING
            RETURNING id
        """)

        result = await db_session.execute(
            insert_stmt,
            {
                "source": source,
                "event_type": event_type,
                "payload": data.model_dump_json(),
                "client_ip": client_ip,
            },
        )
        await db_session.commit()

        row = result.fetchone()
        if row:
            logger.info(
                f"Raw conversation captured to raw_lake: {conv_hash} (id: {row[0]})"
            )
        else:
            logger.info(f"Duplicate conversation ignored: {conv_hash}")

        return CaptureResponse(
            success=True,
            file_path="[RAW_LAKE]",
            nodes_created=0,
            message=f"Successfully queued conversation {conv_hash} for processing.",
        )
    except IntegrityError:
        await db_session.rollback()
        logger.info(f"Duplicate conversation captured: {conv_hash}. Ignoring.")
        return CaptureResponse(
            success=True,
            file_path="[RAW_LAKE]",
            nodes_created=0,
            message=f"Conversation {conv_hash} already exists. Ignored.",
        )
    except Exception as e:
        support_id = str(uuid.uuid4())
        logger.exception(f"Critical Error {support_id} during capture: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal error storing raw conversation",
                "id": support_id,
            },
        )


@router.get("/recent", response_model=List[CaptureResponse])
async def get_recent_captures(
    limit: int = 10,
    db_session: Any = Depends(get_ingest_db),
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> List[CaptureResponse]:
    """
    Get the most recent captured conversations from raw_lake table.
    Filters for event_type starting with 'conversation-' to exclude other ingestion types.
    """
    try:
        stmt = text("""
            SELECT id, source, event_type, ingested_at, payload
            FROM raw_lake
            WHERE event_type LIKE 'conversation-%'
            ORDER BY ingested_at DESC
            LIMIT :limit
        """)
        result = await db_session.execute(stmt, {"limit": limit})
        rows = result.fetchall()

        response = []
        for row in rows:
            # Extract platform from event_type (e.g., "conversation-Perplexity" -> "Perplexity")
            platform = (
                row.event_type.replace("conversation-", "")
                if row.event_type
                else "unknown"
            )
            response.append(
                CaptureResponse(
                    success=True,
                    file_path=f"raw_lake://{row.id}",
                    nodes_created=0,
                    message=f"Captured via {platform} at {row.ingested_at}",
                )
            )

        return response
    except Exception as e:
        logger.error(f"Failed to fetch recent captures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=OmegaStats)
async def get_omega_stats(
    db_session: Any = Depends(get_ingest_db),
    _token_payload: Dict[str, Any] = Security(validate_access_token),
):
    """
    Get statistics for the OmegaKG core service.
    """
    from omega_kg.database.graph import graph_driver

    try:
        # 1. Capture Counts from raw_lake (PostgreSQL)
        total_q = text(
            "SELECT COUNT(*) FROM raw_lake WHERE event_type LIKE 'conversation-%'"
        )
        recent_q = text("""
            SELECT COUNT(*) FROM raw_lake 
            WHERE event_type LIKE 'conversation-%' 
            AND ingested_at > NOW() - INTERVAL '24 hours'
        """)

        total_r = await db_session.execute(total_q)
        recent_r = await db_session.execute(recent_q)

        total_captures = total_r.scalar() or 0
        recent_24h = recent_r.scalar() or 0

        # 2. Session Count (unique sources in raw_lake)
        sessions_q = text("SELECT COUNT(DISTINCT source) FROM raw_lake")
        sessions_r = await db_session.execute(sessions_q)
        active_sessions = sessions_r.scalar() or 0

        # 3. Neo4j Status
        neo4j_healthy = await graph_driver.verify_connectivity()
        neo4j_status = "ONLINE" if neo4j_healthy else "OFFLINE"

        return OmegaStats(
            total_captures=total_captures,
            recent_captures_24h=recent_24h,
            neo4j_status=neo4j_status,
            postgres_status="ONLINE",  # If we reached here, PG is up
            active_sessions=active_sessions,
        )
    except Exception as e:
        logger.error(f"Failed to fetch Omega stats: {e}")
        return OmegaStats(
            total_captures=0,
            recent_captures_24h=0,
            neo4j_status="UNKNOWN",
            postgres_status="ERROR",
            active_sessions=0,
        )


@router.get("/health/vectors")
async def health_check_vectors() -> Dict[str, Any]:
    """
    Get vector store health metrics for monitoring.

    Returns:
        dict: Health status with pending/ready/failed counts and worker state
    """
    try:
        vector_store = await get_vector_store()
        stats = await vector_store.get_stats()

        pending_count = stats.get("pending_count", 0)
        failed_count = stats.get("failed_count", 0)

        # Determine health status
        if failed_count > 100:
            status = "unhealthy"
        elif pending_count > 1000:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_records": stats.get("total_records", 0),
            "pending_count": pending_count,
            "ready_count": stats.get("ready_count", 0),
            "failed_count": failed_count,
            "avg_retry_count": round(stats.get("avg_retry_count", 0), 2),
            "worker_running": True,
        }
    except Exception as e:
        logger.error(f"Vector health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "worker_running": False,
        }


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint with timeouts and graceful degradation.

    Checks connectivity to Obsidian vault, Neo4j, and PostgreSQL.
    Uses singleton drivers where available to avoid connection pool exhaustion.
    """
    import asyncio

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vault_accessible": False,
        "neo4j_connected": False,
        "postgres_connected": False,
    }

    # Vault check (fast, local filesystem)
    try:
        vault_path = Path(settings.obsidian_vault_path)
        health_status["vault_accessible"] = vault_path.exists()
        health_status["vault_path"] = str(vault_path)
    except Exception as e:
        logger.warning(f"Vault check failed: {e}")

    # Neo4j check with timeout - uses singleton AsyncGraphDriver
    try:
        from omega_kg.database.graph import graph_driver

        result = await asyncio.wait_for(graph_driver.verify_connectivity(), timeout=5.0)
        health_status["neo4j_connected"] = result
    except asyncio.TimeoutError:
        health_status["neo4j_error"] = "Connection timeout"
        logger.warning("Neo4j check timed out")
    except Exception as e:
        logger.warning(f"Neo4j check failed: {e}")
        health_status["neo4j_error"] = str(e)

    # PostgreSQL check with timeout - uses engine directly
    try:
        from omega_kg.database.session import engine

        async with asyncio.timeout(5.0):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                health_status["postgres_connected"] = True
    except asyncio.TimeoutError:
        health_status["postgres_error"] = "Connection timeout"
        logger.warning("PostgreSQL check timed out")
    except Exception as e:
        logger.warning(f"PostgreSQL check failed: {e}")
        health_status["postgres_error"] = str(e)

    # Determine overall status
    failed_checks = sum(
        [
            not health_status.get("vault_accessible", True),
            not health_status.get("neo4j_connected", True),
            not health_status.get("postgres_connected", True),
        ]
    )
    if failed_checks >= 2:
        health_status["status"] = "unhealthy"
    elif failed_checks == 1:
        health_status["status"] = "degraded"

    return health_status


@router.get("/health/installation")
async def get_installation_status() -> Dict[str, Any]:
    """
    Get real-time status of Python environment and package installation.

    Returns:
        JSON with installation status, version, and troubleshooting links
    """
    try:
        import omega_kg

        version = getattr(omega_kg, "__version__", "unknown")
        installed = True
    except ImportError:
        installed = False
        version = None

    status = {
        "status": "healthy" if installed else "unhealthy",
        "omega_kg_installed": installed,
        "version": version,
        "timestamp": datetime.now().isoformat(),
    }

    if not installed:
        status["details"] = {
            "error": "Package not installed",
            "troubleshooting": "Run scripts/setup_omega_kg.ps1 or pip install -e .",
            "documentation": "docs/INSTALLATION_TROUBLESHOOTING.md",
        }

    return status


__all__ = ["router", "set_percolate_function"]
