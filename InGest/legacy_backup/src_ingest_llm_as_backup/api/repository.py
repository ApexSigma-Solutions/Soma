"""
Repository ingestion API endpoints.

This module implements endpoints for ingesting and analyzing Python repositories
including local directories, Git repositories, and comprehensive project analysis.
"""

import time
from typing import Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from ..models import (
    RepositoryIngestionRequest,
    RepositoryIngestionResponse,
    RepositoryAnalysisRequest,
    RepositoryAnalysisResponse,
    ProcessingStatus,
)
from ..services.repository_processor import get_repository_processor
from ..services.memos_client import (
    get_memos_client,
    MemOSClient,
    MemOSConnectionError,
    MemOSAPIError,
)
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
from ..observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["repository"])

# In-memory storage for async ingestion status (in production, use Redis or database)
_ingestion_status: Dict[str, RepositoryIngestionResponse] = {}


@router.post("/python-repo", response_model=RepositoryIngestionResponse)
async def ingest_python_repository(
    request: RepositoryIngestionRequest,
    background_tasks: BackgroundTasks,
    memos_client: MemOSClient = Depends(get_memos_client),
) -> RepositoryIngestionResponse:
    """
    Ingest a Python repository for comprehensive code analysis.

    This endpoint processes entire Python repositories, extracting code elements,
    generating embeddings, and storing everything in the memOS.as memory system
    with full observability and analysis.

    Args:
        request: Repository ingestion request with source and configuration
        background_tasks: FastAPI background tasks for async processing
        memos_client: memOS.as client dependency

    Returns:
        RepositoryIngestionResponse: Processing status and results

    Raises:
        HTTPException: On validation or processing errors
    """
    start_time = time.time()
    ingestion_id = uuid4()

    # Initialize Langfuse tracing
    langfuse_client = get_langfuse_client()
    trace_id = None

    if langfuse_client.enabled:
        trace_id = langfuse_client.create_trace(
            name="repository_ingestion_api",
            metadata={
                "ingestion_id": str(ingestion_id),
                "repository_source": request.repository_source.value,
                "source_path": request.source_path,
                "max_files": request.max_files,
                "max_file_size": request.max_file_size,
                "process_async": request.process_async,
                "endpoint": "/ingest/python-repo",
            },
            tags=[
                "repository",
                "ingestion",
                "api",
                request.repository_source.value,
            ],
            input_data={
                "repository_source": request.repository_source.value,
                "source_path": request.source_path,
                "max_files": request.max_files,
                "max_file_size": request.max_file_size,
                "include_patterns": request.include_patterns,
                "exclude_patterns": request.exclude_patterns[:3],  # First 3 for brevity
                "process_async": request.process_async,
            },
        )

    # Record metrics and logging
    record_ingestion_start("/ingest/python-repo", "repository", 0)  # Size not known yet
    log_ingestion_start(
        logger,
        str(ingestion_id),
        "repository",
        0,
        {
            "repository_source": request.repository_source.value,
            "source_path": request.source_path,
            "max_files": request.max_files,
        },
    )

    # Add tracing attributes
    add_span_attributes(
        ingestion_id=str(ingestion_id),
        content_type="repository",
        content_size=0,
        source_type=request.repository_source.value,
    )

    try:
        # Check memOS.as connectivity
        if not await memos_client.health_check():
            raise HTTPException(status_code=503, detail="memOS.as service unavailable")

        # Add ingestion ID to metadata for tracking
        request.metadata.custom_fields = request.metadata.custom_fields or {}
        request.metadata.custom_fields["ingestion_id"] = str(ingestion_id)

        # Get repository processor
        repo_processor = get_repository_processor()

        # Process repository
        response = await repo_processor.process_repository(request)
        response.ingestion_id = ingestion_id

        # Store response for status tracking if async
        if request.process_async:
            _ingestion_status[str(ingestion_id)] = response

        # Record completion metrics and logging
        duration_ms = int((time.time() - start_time) * 1000)
        files_processed = (
            len(response.files_processed) if response.files_processed else 0
        )

        record_ingestion_complete(
            "/ingest/python-repo",
            "repository",
            duration_ms / 1000,
            response.status.value,
            files_processed,
        )

        log_ingestion_complete(
            logger,
            str(ingestion_id),
            response.status.value,
            duration_ms,
            files_processed,
        )

        # Update Langfuse trace with completion data
        if langfuse_client.enabled and trace_id:
            success_rate = (
                1.0
                if response.status == ProcessingStatus.COMPLETED
                else 0.5
                if response.status == ProcessingStatus.PENDING
                else 0.0
            )

            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "status": response.status.value,
                    "files_discovered": response.files_discovered,
                    "files_to_process": response.files_to_process,
                    "files_processed": files_processed,
                    "discovery_time_ms": response.discovery_time_ms,
                    "processing_time_ms": response.processing_time_ms,
                    "total_time_ms": duration_ms,
                    "process_async": request.process_async,
                },
            )

            # Score the repository ingestion
            langfuse_client.score_trace(
                trace_id=trace_id,
                name="repository_ingestion_success",
                value=success_rate,
                comment=f"Repository ingestion: {response.status.value}, {files_processed} files",
            )

            # Add repository size metrics
            if response.files_to_process > 0:
                size_score = min(
                    1.0, response.files_to_process / 100
                )  # Normalize to reasonable repo size
                langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="repository_size_complexity",
                    value=size_score,
                    comment=f"Repository size: {response.files_to_process} Python files to process",
                )

        return response

    except HTTPException:
        raise
    except (ValueError, RuntimeError) as e:
        # Handle repository-specific errors (invalid paths, clone failures, etc.)
        error_msg = str(e)
        logger.error(
            f"Repository processing error in ingestion {ingestion_id}: {error_msg}"
        )

        # Record error in Langfuse
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "success": False,
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "duration_before_error_ms": int((time.time() - start_time) * 1000),
                },
            )

            langfuse_client.score_trace(
                trace_id=trace_id,
                name="repository_ingestion_success",
                value=0.0,
                comment=f"Failed: {error_msg}",
            )

        raise HTTPException(status_code=400, detail=error_msg)
    except MemOSConnectionError as e:
        logger.error(
            f"memOS.as connection error in repository ingestion {ingestion_id}: {e}"
        )
        raise HTTPException(
            status_code=503, detail="Memory storage service unavailable"
        )
    except MemOSAPIError as e:
        logger.error(f"memOS.as API error in repository ingestion {ingestion_id}: {e}")
        raise HTTPException(status_code=502, detail="Memory storage service error")
    except Exception as e:
        logger.error(f"Unexpected error in repository ingestion {ingestion_id}: {e}")

        # Record error in Langfuse
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_before_error_ms": int((time.time() - start_time) * 1000),
                },
            )

            langfuse_client.score_trace(
                trace_id=trace_id,
                name="repository_ingestion_success",
                value=0.0,
                comment=f"Failed: {str(e)}",
            )

        raise HTTPException(
            status_code=500,
            detail="Internal server error during repository ingestion",
        )


@router.get(
    "/python-repo/status/{ingestion_id}",
    response_model=RepositoryIngestionResponse,
)
async def get_repository_ingestion_status(
    ingestion_id: str,
) -> RepositoryIngestionResponse:
    """
    Get the status of a repository ingestion operation.

    Args:
        ingestion_id: UUID of the repository ingestion operation

    Returns:
        RepositoryIngestionResponse: Current status and results

    Raises:
        HTTPException: If ingestion ID not found
    """
    if ingestion_id not in _ingestion_status:
        raise HTTPException(
            status_code=404,
            detail=f"Repository ingestion {ingestion_id} not found",
        )

    response = _ingestion_status[ingestion_id]

    # Update message based on current status
    if response.status == ProcessingStatus.PENDING:
        response.message = f"Repository processing in progress: {len(response.files_processed)} files completed"
    elif response.status == ProcessingStatus.COMPLETED:
        response.message = f"Repository processing completed: {len(response.files_processed)} files processed"

    return response


@router.post("/python-repo/analyze", response_model=RepositoryAnalysisResponse)
async def analyze_repository(
    request: RepositoryAnalysisRequest,
    memos_client: MemOSClient = Depends(get_memos_client),
) -> RepositoryAnalysisResponse:
    """
    Analyze an already ingested repository for insights and recommendations.

    This endpoint performs comprehensive analysis of an ingested repository,
    providing code quality metrics, architectural insights, and optimization
    recommendations.

    Args:
        request: Repository analysis request
        memos_client: memOS.as client dependency

    Returns:
        RepositoryAnalysisResponse: Comprehensive analysis results

    Raises:
        HTTPException: If repository not found or analysis fails
    """
    # Check if ingestion exists
    ingestion_id_str = str(request.ingestion_id)
    if ingestion_id_str not in _ingestion_status:
        raise HTTPException(
            status_code=404,
            detail=f"Repository ingestion {ingestion_id_str} not found",
        )

    ingestion_response = _ingestion_status[ingestion_id_str]

    if ingestion_response.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Repository ingestion {ingestion_id_str} is not completed yet",
        )

    try:
        # Perform analysis based on ingestion results
        analysis = _perform_repository_analysis(
            ingestion_response, request.analysis_type
        )

        return RepositoryAnalysisResponse(
            ingestion_id=request.ingestion_id,
            analysis_type=request.analysis_type,
            **analysis,
        )

    except Exception as e:
        logger.error(f"Repository analysis failed for {ingestion_id_str}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Repository analysis failed: {str(e)}"
        )


def _perform_repository_analysis(
    ingestion_response: RepositoryIngestionResponse, analysis_type: str
) -> Dict[str, Any]:
    """
    Perform comprehensive repository analysis.

    Args:
        ingestion_response: Results from repository ingestion
        analysis_type: Type of analysis to perform

    Returns:
        Dict[str, Any]: Analysis results
    """
    if not ingestion_response.processing_summary:
        return {
            "total_lines_of_code": 0,
            "code_to_comment_ratio": 0.0,
            "average_function_complexity": 0.0,
            "module_dependencies": {},
            "class_hierarchy": {},
            "documentation_coverage": 0.0,
            "test_coverage_estimate": 0.0,
            "optimization_suggestions": ["Repository processing incomplete"],
            "refactoring_opportunities": [],
        }

    summary = ingestion_response.processing_summary
    files_processed = ingestion_response.files_processed

    # Calculate total lines of code (estimate from file sizes)
    total_loc = sum(
        result.file_size // 50
        for result in files_processed
        if result.status == ProcessingStatus.COMPLETED
    )  # Rough estimate

    # Documentation coverage (files with docstrings vs total)
    python_files = [
        r
        for r in files_processed
        if r.relative_path.endswith(".py") and r.status == ProcessingStatus.COMPLETED
    ]
    documented_files = [
        r for r in python_files if r.elements_extracted > 0
    ]  # Assume extracted elements indicate documentation
    doc_coverage = len(documented_files) / len(python_files) if python_files else 0.0

    # Test coverage estimate (presence of test files)
    test_files = [r for r in files_processed if "test" in r.relative_path.lower()]
    test_coverage_estimate = (
        min(1.0, len(test_files) / len(python_files)) if python_files else 0.0
    )

    # Generate optimization suggestions
    suggestions = []
    refactoring_opportunities = []

    if summary.average_complexity > 5.0:
        suggestions.append("Consider refactoring high complexity functions")
        refactoring_opportunities.append(
            "Reduce cyclomatic complexity of complex functions"
        )

    if doc_coverage < 0.5:
        suggestions.append("Improve documentation coverage")

    if test_coverage_estimate < 0.3:
        suggestions.append("Increase test coverage")

    if summary.total_files_failed > 0:
        suggestions.append(
            f"Fix {summary.total_files_failed} files that failed processing"
        )

    # Large file analysis
    large_files = [
        f for f in summary.largest_files if f.get("size", 0) > 50000
    ]  # > 50KB
    if large_files:
        suggestions.append(f"Consider splitting {len(large_files)} large files")
        refactoring_opportunities.extend(
            [f"Split large file: {f['path']}" for f in large_files[:3]]
        )

    return {
        "total_lines_of_code": total_loc,
        "code_to_comment_ratio": 0.1,  # Placeholder - would need detailed analysis
        "average_function_complexity": summary.average_complexity,
        "module_dependencies": {},  # Would need import analysis
        "class_hierarchy": {},  # Would need inheritance analysis
        "documentation_coverage": doc_coverage,
        "test_coverage_estimate": test_coverage_estimate,
        "optimization_suggestions": suggestions,
        "refactoring_opportunities": refactoring_opportunities,
    }
