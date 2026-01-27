"""
Ingestion API endpoints.

This module implements the core ingestion endpoints for processing
and storing content in the memOS.as memory system.
"""

import json
import time
import traceback
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..config import settings, get_settings
from ..database.session import get_ingest_db
from ..db_models.raw_ingestion import RawIngestion
from ..models import (
    IngestionRequest,
    IngestionResponse,
    IngestionResult,
    ProcessingStatus,
    MemoryTier,
    WorkingExperienceRequest,
    IngestionMetadata,
    SourceType,
    ContentType,
)
from ..services.conversation_synthesizer import (
    ConversationSynthesizer,
    ConversionDigest,
)


from ..observability.langfuse_client import get_langfuse_client
from ..observability.logging import (
    get_logger,
    log_ingestion_start,
    log_ingestion_complete,
)
from ..observability.metrics import (
    record_ingestion_start,
    record_ingestion_complete,
)
from ..observability.tracing import add_span_attributes
from ..utils.content_processor import (
    ContentProcessor,
    create_ingestion_metadata,
)
from src.shared.system_health import SystemHealth
from ingest_llm_as.services.memos_client import (
    get_memos_client,
    MemOSClient,
    MemOSConnectionError,
    MemOSAPIError,
    generate_content_hash,
)


class QueueStatus(BaseModel):
    pending_count: int
    processed_count: int
    total_count: int
    oldest_pending_age_seconds: Optional[float]


class IngestStats(BaseModel):
    queue: QueueStatus
    throughput_24h: int
    error_rate_24h: float
    system_healthy: bool


logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class ServiceConfig(BaseModel):
    async_processing: bool
    chunk_size: int
    embedding_model: str
    summarizer_model: str
    llm_provider: str


@router.get("/config", response_model=ServiceConfig)
def get_service_config():
    """Return current service configuration."""
    current_settings = get_settings()
    return ServiceConfig(
        async_processing=current_settings.enable_async_processing,
        chunk_size=current_settings.default_chunk_size,
        embedding_model="nomic-embed-text-v1.5",  # Currently hardcoded in processor
        summarizer_model=current_settings.summarization_model,
        llm_provider=current_settings.llm_provider,
    )


@router.post("/text", response_model=IngestionResponse)
async def ingest_text(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_ingest_db),
    memos_client: MemOSClient = Depends(get_memos_client),
) -> IngestionResponse:
    """
    Ingest text content into the memory system.

    This endpoint processes text content, chunks it if necessary,
    and stores it in the appropriate memOS.as memory tiers.

    CRITICAL: Raw data is persisted to PostgreSQL BEFORE any processing
    to ensure 100% data retention (TN-CORE-101).

    Args:
        request: Ingestion request with content and metadata
        background_tasks: FastAPI background tasks for async processing
        db: Synchronous database session for raw persistence
        memos_client: memOS.as client dependency

    Returns:
        IngestionResponse: Processing status and results

    Raises:
        HTTPException: On validation or processing errors
    """
    print("DEBUG ingest_text: Endpoint called")
    start_time = time.time()
    ingestion_id = uuid4()

    # STEP 1: IMMEDIATE RAW PERSISTENCE (TN-CORE-101)
    # Write raw data to PostgreSQL BEFORE any processing to ensure data retention
    try:
        payload_dict = request.model_dump()

        raw_record = RawIngestion(
            ingestion_id=ingestion_id,
            source_type="text",
            content_type=request.metadata.content_type.value,
            raw_payload=payload_dict,
            raw_metadata={
                "source": request.metadata.source.value,
                "tags": request.metadata.tags,
                "source_url": request.metadata.source_url,
                "title": request.metadata.title,
            },
            captured_at=datetime.now(timezone.utc),
            processed=False,
        )
        db.add(raw_record)
        db.commit()

        logger.info("Raw ingestion persisted: %s", ingestion_id)

    except IntegrityError:
        db.rollback()
        logger.warning("Duplicate ingestion ID: %s", ingestion_id)
        raise HTTPException(
            status_code=409,
            detail=f"Ingestion {ingestion_id} already exists",
        ) from None
    except Exception as e:
        db.rollback()
        logger.exception("Failed to persist raw ingestion: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to persist raw ingestion data",
        ) from e

    # Initialize Langfuse tracing
    langfuse_client = get_langfuse_client()
    trace_id = None

    if langfuse_client.enabled:
        trace_id = langfuse_client.create_trace(
            name="text_ingestion",
            metadata={
                "ingestion_id": str(ingestion_id),
                "content_type": request.metadata.content_type.value,
                "content_size": len(request.content),
                "source_type": request.metadata.source.value,
                "process_async": request.process_async,
                "endpoint": "/ingest/text",
            },
            tags=["ingestion", "text", request.metadata.content_type.value],
            input_data={
                "content_preview": request.content[:200] + "..."
                if len(request.content) > 200
                else request.content,
                "metadata": request.metadata.model_dump(),
                "chunk_size": request.chunk_size,
            },
        )

    # Record metrics and logging
    record_ingestion_start(
        "/ingest/text",
        request.metadata.content_type.value,
        len(request.content),
    )
    log_ingestion_start(
        logger,
        str(ingestion_id),
        request.metadata.content_type.value,
        len(request.content),
        request.metadata.model_dump(),
    )

    # Add tracing attributes
    add_span_attributes(
        ingestion_id=str(ingestion_id),
        content_type=request.metadata.content_type.value,
        content_size=len(request.content),
        source_type=request.metadata.source.value,
    )

    try:
        # Initialize content processor with embedding capability
        processor = ContentProcessor(chunk_size=request.chunk_size)

        # Validate content size early
        if len(request.content) > settings.max_content_size:
            raise HTTPException(
                status_code=413,
                detail=f"Content too large: {len(request.content)} > {settings.max_content_size}",
            )

        # Check memOS.as connectivity
        # Temporarily disabled for debugging
        # if not await memos_client.health_check():
        #     raise HTTPException(
        #         status_code=503, detail="memOS.as service unavailable"
        #     )

        # Detect content type for intelligent processing
        detected_type = processor.detect_content_type(
            content=request.content, file_path=request.metadata.source_url
        )

        # Process content with embeddings - use AST parser for Python code
        if detected_type == "python" or request.metadata.content_type.value == "code":
            processing_result = await processor.process_python_code_with_embeddings(
                source_code=request.content,
                file_path=request.metadata.source_url,
                content_type=request.metadata.content_type.value,
            )
        else:
            processing_result = await processor.process_content_with_embeddings(
                content=request.content,
                content_type=request.metadata.content_type.value,
                detected_type=detected_type,
            )

        chunks = processing_result["chunks"]
        embeddings = processing_result["embeddings"]
        processing_stats = processing_result["processing_stats"]

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No valid content chunks could be created",
            )

        logger.info(
            "Created %s chunks for ingestion %s",
            len(chunks),
            ingestion_id,
            extra={
                "embeddings_generated": processing_stats["embeddings_generated"],
                "embedding_enabled": processing_stats["embedding_enabled"],
            },
        )

        # Process synchronously or asynchronously based on request
        if request.process_async and settings.enable_async_processing:
            # Queue for background processing
            background_tasks.add_task(
                _process_chunks_async,
                chunks,
                embeddings,
                request,
                ingestion_id,
                processor,
            )

            # Return immediate response
            response = IngestionResponse(
                ingestion_id=ingestion_id,
                status=ProcessingStatus.PENDING,
                total_chunks=len(chunks),
                message="Ingestion queued for async processing",
            )
        else:
            # Process synchronously
            results = await _process_chunks_sync(
                chunks, embeddings, request, processor, memos_client
            )

            # Determine overall status
            failed_results = [r for r in results if r.status == ProcessingStatus.FAILED]
            overall_status = (
                ProcessingStatus.FAILED
                if failed_results
                else ProcessingStatus.COMPLETED
            )

            response = IngestionResponse(
                ingestion_id=ingestion_id,
                status=overall_status,
                total_chunks=len(chunks),
                results=results,
                processing_time_ms=int((time.time() - start_time) * 1000),
                message=f"Processed {len(results)} chunks, {len(failed_results)} failed",
            )

            # STEP 3: MARK AS PROCESSED
            try:
                raw_record.processed = True
                raw_record.processed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Raw ingestion marked as processed: %s", ingestion_id)
            except Exception as e:
                db.rollback()
                logger.error("Failed to mark ingestion as processed: %s", e)

        # Record completion metrics and logging
        duration_ms = int((time.time() - start_time) * 1000)
        chunks_count = len(getattr(response, "results", []))

        record_ingestion_complete(
            "/ingest/text",
            request.metadata.content_type.value,
            duration_ms / 1000,
            response.status.value,
            chunks_count,
        )

        log_ingestion_complete(
            logger,
            str(ingestion_id),
            response.status.value,
            duration_ms,
            chunks_count,
        )

        # Update Langfuse trace with completion data
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "status": response.status.value,
                    "total_chunks": response.total_chunks,
                    "processing_time_ms": duration_ms,
                    "chunks_processed": chunks_count,
                },
            )

            # Add quality score based on success rate
            success_rate = 1.0 if response.status == ProcessingStatus.COMPLETED else 0.0
            if response.results:
                failed_count = len(
                    [r for r in response.results if r.status == ProcessingStatus.FAILED]
                )
                success_rate = (len(response.results) - failed_count) / len(
                    response.results
                )

            langfuse_client.score_trace(
                trace_id=trace_id,
                name="ingestion_success_rate",
                value=success_rate,
                comment=f"Ingestion completed with {chunks_count} chunks processed",
            )

        return response

    except HTTPException:
        raise
    except MemOSConnectionError as e:
        logger.error(f"memOS.as connection error in ingestion {ingestion_id}: {e}")
        raise HTTPException(
            status_code=503, detail="Memory storage service unavailable"
        )
    except MemOSAPIError as e:
        logger.error(f"memOS.as API error in ingestion {ingestion_id}: {e}")
        raise HTTPException(status_code=502, detail="Memory storage service error")
    except Exception as e:
        logger.error(f"Unexpected error in ingestion {ingestion_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during ingestion"
        )


@router.post("/file", response_model=IngestionResponse)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_ingest_db),
    memos_client: MemOSClient = Depends(get_memos_client),
) -> IngestionResponse:
    """
    Ingest a file (PDF, Text, Markdown) into the memory system.

    CRITICAL: Raw file data is persisted to PostgreSQL BEFORE any processing
    to ensure 100% data retention (TN-CORE-101).
    """
    start_time = time.time()
    ingestion_id = uuid4()

    try:
        # Read file data
        content_bytes = await file.read()
        filename = file.filename or "unknown"

        # STEP 1: IMMEDIATE RAW PERSISTENCE (TN-CORE-101)
        # Write raw file data to PostgreSQL BEFORE any processing
        try:
            # Validate file size
            if len(content_bytes) > settings.max_content_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large: {len(content_bytes)} > {settings.max_content_size}",
                )

            raw_record = RawIngestion(
                ingestion_id=ingestion_id,
                source_type="file",
                content_type=file.content_type or "application/octet-stream",
                raw_payload={
                    "filename": filename,
                    "size": len(content_bytes),
                    "content_type": file.content_type,
                },
                file_data=content_bytes,  # Store binary data in BYTEA column
                raw_metadata={
                    "filename": filename,
                    "original_content_type": file.content_type,
                },
                captured_at=datetime.now(timezone.utc),
                processed=False,
            )
            db.add(raw_record)
            db.commit()

            logger.info(f"Raw file ingestion persisted: {ingestion_id} ({filename})")

        except IntegrityError:
            db.rollback()
            logger.warning(f"Duplicate ingestion ID: {ingestion_id}")
            raise HTTPException(
                status_code=409, detail=f"Ingestion {ingestion_id} already exists"
            )
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            logger.error("Failed to persist raw file ingestion")
            raise HTTPException(
                status_code=500, detail="Failed to persist raw file data"
            )

        # STEP 2: PROCESS FILE (existing logic)
        processor = ContentProcessor()

        if filename.lower().endswith(".pdf"):
            # Process PDF
            processing_result = await processor.process_pdf_content(
                content_bytes, filename
            )
        else:
            # Process as text
            text_content = content_bytes.decode("utf-8")
            processing_result = await processor.process_content_with_embeddings(
                content=text_content, content_type="documentation", detected_type="text"
            )

        chunks = processing_result["chunks"]
        embeddings = processing_result["embeddings"]

        # Create metadata
        metadata = IngestionMetadata(
            source=SourceType.UPLOAD,
            content_type=ContentType.DOCUMENTATION,
            source_url=filename,
            title=filename,
        )

        request = IngestionRequest(
            content="[FILE CONTENT]",  # identifying placeholder
            metadata=metadata,
            process_async=False,
        )

        # Process chunks synchronously
        results = await _process_chunks_sync(
            chunks, embeddings, request, processor, memos_client
        )

        failed_results = [r for r in results if r.status == ProcessingStatus.FAILED]
        overall_status = (
            ProcessingStatus.FAILED if failed_results else ProcessingStatus.COMPLETED
        )

        # STEP 3: MARK AS PROCESSED
        try:
            # We need to fetch the record again or keep a reference
            # But here we have the ingestion_id
            from sqlalchemy import update

            db.execute(
                update(RawIngestion)
                .where(RawIngestion.ingestion_id == ingestion_id)
                .values(processed=True, processed_at=datetime.now(timezone.utc))
            )
            db.commit()
            logger.info("File ingestion marked as processed in DB.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to mark file as processed: {e}")

        return IngestionResponse(
            ingestion_id=ingestion_id,
            status=overall_status,
            total_chunks=len(chunks),
            results=results,
            processing_time_ms=int((time.time() - start_time) * 1000),
            message=f"Processed file {filename}: {len(results)} chunks",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experience", response_model=IngestionResponse)
async def ingest_experience(
    request: WorkingExperienceRequest,
    background_tasks: BackgroundTasks,
    memos_client: MemOSClient = Depends(get_memos_client),
) -> IngestionResponse:
    """
    Ingest a working experience promoted from memOS.MCP.
    """
    print("DEBUG ingest_experience: Endpoint called")
    start_time = time.time()
    ingestion_id = uuid4()

    # Create standardized metadata
    metadata = IngestionMetadata(
        source=request.source,
        content_type=request.type,
        custom_fields=request.metadata,
        title=f"Experience from {request.metadata.get('session_id', 'unknown')}",
        tags=["working-experience", "promotion"],
    )

    # Convert to IngestionRequest for consistent processing
    ingestion_req = IngestionRequest(
        content=request.content,
        metadata=metadata,
        process_async=False,  # Force sync for promotion feedback
    )

    # Initialize Langfuse tracing
    langfuse_client = get_langfuse_client()
    trace_id = None

    if langfuse_client.enabled:
        trace_id = langfuse_client.create_trace(
            name="experience_ingestion",
            metadata={
                "ingestion_id": str(ingestion_id),
                "content_type": request.type.value,
                "session_id": request.metadata.get("session_id"),
                "source": request.source.value,
            },
            tags=["ingestion", "experience", "memos-mcp"],
            input_data={
                "content": request.content,
                "metadata": request.metadata,
            },
        )

    # Record metrics
    log_ingestion_start(
        logger,
        str(ingestion_id),
        request.type.value,
        len(request.content),
        request.metadata,
    )

    try:
        # Initialize processor
        processor = ContentProcessor()

        # Process content (generate embeddings)
        # Experience is treated as text/semantic
        processing_result = await processor.process_content_with_embeddings(
            content=request.content,
            content_type=request.type.value,
            detected_type="text",  # Always treat as text for now
        )

        chunks = processing_result["chunks"]
        embeddings = processing_result["embeddings"]

        if not chunks:
            raise HTTPException(status_code=400, detail="No content chunks created")

        # Process Synchronously
        results = await _process_chunks_sync(
            chunks, embeddings, ingestion_req, processor, memos_client
        )

        # Determine status
        failed_results = [r for r in results if r.status == ProcessingStatus.FAILED]
        overall_status = (
            ProcessingStatus.FAILED if failed_results else ProcessingStatus.COMPLETED
        )

        response = IngestionResponse(
            ingestion_id=ingestion_id,
            status=overall_status,
            total_chunks=len(chunks),
            results=results,
            processing_time_ms=int((time.time() - start_time) * 1000),
            message=f"Promoted {len(results)} chunks to memory",
        )

        # Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        log_ingestion_complete(
            logger,
            str(ingestion_id),
            response.status.value,
            duration_ms,
            len(results),
        )

        return response

    except Exception as e:
        logger.error(f"Error in ingest_experience: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digest", response_model=ConversionDigest)
async def digest_conversation(
    request: IngestionRequest,
    synthesizer: ConversationSynthesizer = Depends(ConversationSynthesizer),
) -> ConversionDigest:
    """
    Synthesize raw conversation messages into a structured digest.
    Does NOT store in memOS, just returns the analysis.
    """
    try:
        # Assuming content is the raw JSON messages list as string or we use IngestionRequest.content for text
        # If it's the raw payload from extensions, we might need a specific model
        # For now, we'll try to parse request.content as JSON if it's a list
        try:
            messages = json.loads(request.content)
            if not isinstance(messages, list):
                messages = [{"role": "user", "content": request.content}]
        except (json.JSONDecodeError, TypeError):
            messages = [{"role": "user", "content": request.content}]

        return await synthesizer.synthesize(
            messages=messages, platform=request.metadata.source.value
        )
    except Exception as e:
        logger.error(f"Digest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_chunks_sync(
    chunks: List[str],
    embeddings: List[Optional[List[float]]],
    request: IngestionRequest,
    processor: ContentProcessor,
    memos_client: MemOSClient,
) -> List[IngestionResult]:
    """
    Process chunks synchronously with embeddings.

    Args:
        chunks: Content chunks to process
        embeddings: Corresponding embeddings for each chunk
        request: Original ingestion request
        processor: Content processor instance
        memos_client: memOS.as client

    Returns:
        List[IngestionResult]: Processing results for each chunk
    """
    results = []

    for i, chunk in enumerate(chunks):
        try:
            # Get corresponding embedding for this chunk
            embedding = embeddings[i] if i < len(embeddings) else None

            result = await _process_single_chunk(
                chunk=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                request=request,
                processor=processor,
                memos_client=memos_client,
                embedding=embedding,
            )
            results.append(result)

        except Exception as e:
            # Capture full traceback and error type to aid debugging
            logger.error(
                f"Error processing chunk {i}: {e} ({type(e).__name__})\n{traceback.format_exc()}"
            )

            # Create failed result
            result = IngestionResult(
                memory_tier=MemoryTier.SEMANTIC,  # Default tier
                content_hash=generate_content_hash(chunk),
                chunk_size=len(chunk),
                status=ProcessingStatus.FAILED,
                error_message=f"{type(e).__name__}: {e}",
            )
            results.append(result)

    return results


async def _process_chunks_async(
    chunks: List[str],
    embeddings: List[Optional[List[float]]],
    request: IngestionRequest,
    ingestion_id: UUID,
    processor: ContentProcessor,
):
    """
    Process chunks asynchronously in background with embeddings.

    Args:
        chunks: Content chunks to process
        embeddings: Corresponding embeddings for each chunk
        request: Original ingestion request
        ingestion_id: Unique ingestion identifier
        processor: Content processor instance
    """
    logger.info(f"Starting async processing for ingestion {ingestion_id}")

    try:
        # Use a fresh client context to avoid un-awaited coroutine issues
        async with MemOSClient() as memos_client:
            await _process_chunks_sync(
                chunks, embeddings, request, processor, memos_client
            )

        # TODO: Store results for later retrieval via status endpoint
        logger.info(f"Async processing completed for ingestion {ingestion_id}")

    except Exception as e:
        logger.error(f"Async processing failed for ingestion {ingestion_id}: {e}")


async def _process_single_chunk(
    chunk: str,
    chunk_index: int,
    total_chunks: int,
    request: IngestionRequest,
    processor: ContentProcessor,
    memos_client: MemOSClient,
    embedding: Optional[List[float]] = None,
) -> IngestionResult:
    """
    Process a single content chunk.

    Args:
        chunk: Content chunk to process
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks
        request: Original ingestion request
        processor: Content processor instance
        memos_client: memOS.as client

    Returns:
        IngestionResult: Processing result for this chunk
    """
    try:
        print(f"DEBUG: Processing chunk {chunk_index}, starting...")

        # Generate content hash for deduplication
        content_hash = generate_content_hash(chunk)
        print(f"DEBUG: Generated content hash: {content_hash}")

        # Extract additional metadata from content
        content_metadata = processor.extract_metadata_from_content(chunk)
        print("DEBUG: Extracted content metadata")

        # Create comprehensive metadata
        storage_metadata = create_ingestion_metadata(
            original_metadata=request.metadata.model_dump(),
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            processing_info=content_metadata,
        )
        print("DEBUG: Created storage metadata")

        # Determine memory tier based on content type and metadata
        memory_tier = _determine_memory_tier(request.metadata.content_type)
        print(f"DEBUG: Determined memory tier: {memory_tier}")

        # Store in memOS.as with embedding
        print("DEBUG: About to call memos_client.store_memory")
        storage_response = await memos_client.store_memory(
            content=chunk,
            memory_tier=memory_tier,
            metadata=storage_metadata,
            embedding=embedding,
        )
        print("DEBUG: memOS storage completed successfully")

        # Create result - handle case where memory_id may not be returned
        result_memory_id = None
        if hasattr(storage_response, "memory_id") and storage_response.memory_id:
            # memOS.as returns integer memory_id, use it directly
            result_memory_id = storage_response.memory_id

        print("DEBUG: About to create IngestionResult")
        result = IngestionResult(
            memory_id=result_memory_id,
            memory_tier=memory_tier,
            content_hash=content_hash,
            chunk_size=len(chunk),
            status=ProcessingStatus.COMPLETED
            if storage_response.success
            else ProcessingStatus.FAILED,
        )
        print("DEBUG: Created IngestionResult successfully")
        return result

    except Exception as e:
        print(f"DEBUG: Exception occurred in _process_single_chunk: {e}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback

        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise


def _determine_memory_tier(content_type) -> MemoryTier:
    """
    Determine appropriate memory tier for content type.

    Args:
        content_type: Type of content being ingested

    Returns:
        MemoryTier: Appropriate memory tier
    """
    # Simple mapping for now - can be enhanced with ML-based classification
    # Normalize to a lowercase string whether enum or str
    try:
        ct_str = (
            content_type.value if hasattr(content_type, "value") else str(content_type)
        )
        ct_str = ct_str.lower()
    except Exception:
        ct_str = "text"

    tier_mapping = {
        "text": MemoryTier.SEMANTIC,
        "documentation": MemoryTier.SEMANTIC,
        "markdown": MemoryTier.SEMANTIC,
        "code": MemoryTier.PROCEDURAL,
        "json": MemoryTier.SEMANTIC,
        # Add common aliases
        "python": MemoryTier.PROCEDURAL,
        "source_code": MemoryTier.PROCEDURAL,
    }

    return tier_mapping.get(ct_str, MemoryTier.SEMANTIC)


@router.get("/queue", response_model=QueueStatus)
async def get_queue_status():
    """
    Get current status of the conversation ingestion queue.
    Queries the raw_ingestions table filtered by source_type='conversation'.
    """
    db_url = settings.raw_db_url.replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    try:
        # Get counts for conversation records only
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                COUNT(*) as total,
                EXTRACT(EPOCH FROM (NOW() - MIN(captured_at) FILTER (WHERE processed = FALSE))) as oldest_age
            FROM raw_ingestions
            WHERE source_type LIKE 'conversation%'
        """)

        return QueueStatus(
            pending_count=stats["pending"] or 0,
            processed_count=stats["processed"] or 0,
            total_count=stats["total"] or 0,
            oldest_pending_age_seconds=stats["oldest_age"],
        )
    except Exception as e:
        logger.error(f"Queue status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()


@router.get("/stats", response_model=IngestStats)
async def get_ingest_stats():
    """
    Get comprehensive ingestion statistics for the dashboard.
    """
    db_url = settings.raw_db_url.replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    try:
        # 1. Queue Status
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                COUNT(*) as total,
                EXTRACT(EPOCH FROM (NOW() - MIN(captured_at) FILTER (WHERE processed = FALSE))) as oldest_age
            FROM raw_ingestions
            WHERE source_type LIKE 'conversation%'
        """)

        queue = QueueStatus(
            pending_count=stats["pending"] or 0,
            processed_count=stats["processed"] or 0,
            total_count=stats["total"] or 0,
            oldest_pending_age_seconds=stats["oldest_age"],
        )

        # 2. Throughput & Error Rate (last 24h)
        # Throughput = count of PROCESSED items
        metrics = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE processed = TRUE) as total_24h,
                COUNT(*) FILTER (WHERE processing_attempts > 1 AND processed = FALSE) as errors_24h
            FROM raw_ingestions
            WHERE (captured_at > NOW() - INTERVAL '24 hours' OR processed_at > NOW() - INTERVAL '24 hours')
        """)

        total_24h = metrics["total_24h"] or 0
        errors_24h = metrics["errors_24h"] or 0
        error_rate = (errors_24h / total_24h * 100) if total_24h > 0 else 0.0

        return IngestStats(
            queue=queue,
            throughput_24h=total_24h,
            error_rate_24h=round(error_rate, 2),
            system_healthy=SystemHealth.is_healthy(),
        )
    except Exception as e:
        logger.error(f"Ingest stats check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()


@router.get("/status/{ingestion_id}")
async def get_ingestion_status(ingestion_id: str):
    """
    Get status of an async ingestion operation.

    Args:
        ingestion_id: UUID of the ingestion operation

    Returns:
        Current status of the ingestion
    """
    # TODO: Implement status tracking for async operations
    return {"message": "Status tracking not yet implemented"}
