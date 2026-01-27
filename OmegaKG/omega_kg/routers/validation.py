"""Validation API router for knowledge digest validation and storage.

This router implements the validation API gateway - the single entry point
for validated knowledge storage in OmegaKG. Workers submit digests here
instead of writing directly to Neo4j/pgvector.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncDriver
import asyncpg

from ..auth.validation_auth import ValidatedToken
from ..models.validation_schemas import (
    KnowledgeDigest,
    ValidationResponse,
    ValidationStatus,
)
from ..services.knowledge_store import KnowledgeStore, KnowledgeStoreError
from ..database.adapters import get_neo4j_driver, get_pg_pool
from ..settings import Settings, get_settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate", tags=["validation"])


async def get_knowledge_store(
    neo4j_driver: Annotated[AsyncDriver, Depends(get_neo4j_driver)],
    pg_pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> KnowledgeStore:
    """Dependency to get KnowledgeStore instance.

    Args:
        neo4j_driver: Neo4j driver
        pg_pool: PostgreSQL connection pool
        settings: Application settings

    Returns:
        KnowledgeStore: Knowledge store service
    """
    return KnowledgeStore(neo4j_driver, pg_pool, settings)


@router.post("/validate-and-store", response_model=ValidationResponse)
async def validate_and_store_knowledge(
    digest: KnowledgeDigest,
    token: ValidatedToken,
    knowledge_store: Annotated[KnowledgeStore, Depends(get_knowledge_store)],
) -> ValidationResponse:
    """Validate and store knowledge digest.

    This endpoint is the single entry point for validated knowledge storage.
    Workers submit digests here instead of writing directly to databases.

    CRITICAL: This endpoint enforces:
    - Zero Trust authentication (BWS_ACCESS_TOKEN required)
    - Quality validation (content length, required fields)
    - Deduplication (source_id uniqueness)
    - Atomic transactions (Neo4j + pgvector or rollback)

    Args:
        digest: Validated knowledge digest
        token: Validated service token (from dependency)
        knowledge_store: Knowledge store service (from dependency)

    Returns:
        ValidationResponse: Validation result with node IDs

    Raises:
        HTTPException: On validation or storage errors
    """
    logger.info(
        f"Received validation request: {digest.source_id} "
        f"(type={digest.digest_type.value})"
    )

    # STEP 1: Quality validation
    try:
        _validate_digest_quality(digest)
    except ValueError as e:
        logger.warning(f"Quality validation failed for {digest.source_id}: {e}")
        return ValidationResponse(
            status=ValidationStatus.REJECTED,
            message=f"Quality validation failed: {e}",
            source_id=digest.source_id,
            digest_type=digest.digest_type,
        )

    # STEP 2: Deduplication check
    try:
        is_duplicate = await knowledge_store.check_duplicate(
            digest.source_id,
            digest.digest_type,
        )

        if is_duplicate:
            logger.info(f"Duplicate detected: {digest.source_id}")
            return ValidationResponse(
                status=ValidationStatus.DUPLICATE,
                message=f"Knowledge with source_id {digest.source_id} already exists",
                source_id=digest.source_id,
                digest_type=digest.digest_type,
            )
    except Exception as e:
        logger.error(f"Deduplication check failed for {digest.source_id}: {e}")
        return ValidationResponse(
            status=ValidationStatus.ERROR,
            message=f"Deduplication check failed: {e}",
            source_id=digest.source_id,
            digest_type=digest.digest_type,
        )

    # STEP 3: Atomic storage
    try:
        neo4j_node_id, vector_id = await knowledge_store.store_knowledge(digest)

        logger.info(
            f"Successfully stored knowledge: {digest.source_id} "
            f"(neo4j={neo4j_node_id}, vector={vector_id})"
        )

        return ValidationResponse(
            status=ValidationStatus.ACCEPTED,
            message="Knowledge digest validated and stored successfully",
            neo4j_node_id=neo4j_node_id,
            vector_id=vector_id,
            source_id=digest.source_id,
            digest_type=digest.digest_type,
        )

    except KnowledgeStoreError as e:
        logger.error(f"Storage failed for {digest.source_id}: {e}")
        return ValidationResponse(
            status=ValidationStatus.ERROR,
            message=f"Storage failed: {e}",
            source_id=digest.source_id,
            digest_type=digest.digest_type,
        )
    except Exception as e:
        logger.error(f"Unexpected error storing {digest.source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )


def _validate_digest_quality(digest: KnowledgeDigest) -> None:
    """Validate digest quality before storage.

    Args:
        digest: Knowledge digest to validate

    Raises:
        ValueError: If validation fails
    """
    # Check content length
    if len(digest.content) < 10:
        raise ValueError("Content too short (minimum 10 characters)")

    # Check title
    if not digest.title.strip():
        raise ValueError("Title cannot be empty")

    # Check embedding
    if not digest.embedding or len(digest.embedding) != 1024:
        raise ValueError("Invalid embedding (must be 1024 dimensions)")

    # Check source_id format
    if not digest.source_id or len(digest.source_id) < 3:
        raise ValueError("Invalid source_id (minimum 3 characters)")


@router.get("/health")
async def validation_health() -> dict:
    """Health check for validation API.

    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": "validation-api",
        "version": "1.0.0",
    }
