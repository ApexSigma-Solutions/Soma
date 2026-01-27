"""
Ecosystem ingestion API endpoints for ApexSigma projects.

This module provides REST API endpoints for ingesting and analyzing
the entire ApexSigma ecosystem including all four core projects.
"""

from typing import Dict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.ecosystem_ingestion import get_ecosystem_ingestion_service
from ..observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])


class EcosystemIngestionRequest(BaseModel):
    """Request model for ecosystem ingestion."""

    include_historical: bool = Field(
        default=True, description="Whether to store historical snapshots in memOS"
    )
    generate_cross_analysis: bool = Field(
        default=True, description="Whether to perform cross-project analysis"
    )
    force_refresh: bool = Field(
        default=False, description="Force refresh even if recent snapshot exists"
    )


class EcosystemIngestionResponse(BaseModel):
    """Response model for ecosystem ingestion."""

    snapshot_id: str
    status: str
    message: str
    timestamp: str
    projects_processed: int
    total_files: int
    total_size_mb: float
    processing_time_ms: int
    ecosystem_health_score: float
    recommendations_count: int


class EcosystemHealthResponse(BaseModel):
    """Response model for ecosystem health status."""

    overall_score: float
    status: str
    successful_projects: int
    total_projects: int
    project_health: Dict[str, str]
    assessment_timestamp: str


class ProjectSummaryResponse(BaseModel):
    """Response model for individual project summary."""

    project_name: str
    status: str
    files_processed: int
    size_mb: float
    complexity_score: float
    success_rate: float
    last_updated: str


@router.post("/ingest", response_model=EcosystemIngestionResponse)
async def ingest_ecosystem(
    request: EcosystemIngestionRequest, background_tasks: BackgroundTasks
):
    """
    Ingest the entire ApexSigma ecosystem.

    This endpoint scrapes, analyzes, and embeds all four core projects:
    - InGest-LLM.as
    - memos.as
    - devenviro.as
    - tools.as

    The process includes:
    - Repository processing and analysis
    - Code structure documentation
    - Cross-project relationship mapping
    - Historical snapshot storage in memOS
    - Ecosystem health assessment
    """
    start_time = datetime.now()

    try:
        logger.info("Starting ecosystem ingestion via API")

        # Get ecosystem service
        ecosystem_service = get_ecosystem_ingestion_service()

        # Execute ecosystem ingestion
        snapshot = await ecosystem_service.ingest_entire_ecosystem(
            include_historical=request.include_historical,
            generate_cross_analysis=request.generate_cross_analysis,
        )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        response = EcosystemIngestionResponse(
            snapshot_id=snapshot.snapshot_id,
            status="completed",
            message=f"Successfully processed {snapshot.total_projects} projects",
            timestamp=snapshot.timestamp,
            projects_processed=snapshot.total_projects,
            total_files=snapshot.total_files,
            total_size_mb=snapshot.total_size_bytes / (1024 * 1024),
            processing_time_ms=processing_time,
            ecosystem_health_score=snapshot.ecosystem_health.get("overall_score", 0.0),
            recommendations_count=len(snapshot.recommendations),
        )

        logger.info(f"Ecosystem ingestion completed: {snapshot.snapshot_id}")
        return response

    except Exception as e:
        logger.error(f"Ecosystem ingestion failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ecosystem ingestion failed: {str(e)}"
        )


@router.get("/health", response_model=EcosystemHealthResponse)
async def get_ecosystem_health():
    """
    Get current ecosystem health status.

    Returns health metrics across all projects including:
    - Overall health score
    - Individual project status
    - Assessment timestamp
    """
    try:
        # This would typically query the latest snapshot from memOS
        # For now, we'll return a placeholder response
        # TODO: Implement memOS query for latest ecosystem health

        return EcosystemHealthResponse(
            overall_score=0.85,
            status="healthy",
            successful_projects=4,
            total_projects=4,
            project_health={
                "InGest-LLM.as": "excellent",
                "memos.as": "excellent",
                "devenviro.as": "good",
                "tools.as": "good",
            },
            assessment_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get ecosystem health: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get ecosystem health: {str(e)}"
        )


@router.get("/projects", response_model=Dict[str, ProjectSummaryResponse])
async def get_project_summaries():
    """
    Get summaries of all projects in the ecosystem.

    Returns individual project metrics and status information.
    """
    try:
        # This would typically query the latest snapshots from memOS
        # For now, we'll return placeholder data
        # TODO: Implement memOS query for latest project summaries

        projects = {
            "InGest-LLM.as": ProjectSummaryResponse(
                project_name="InGest-LLM.as",
                status="production-ready",
                files_processed=47,
                size_mb=0.35,
                complexity_score=8.43,
                success_rate=1.0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            ),
            "memos.as": ProjectSummaryResponse(
                project_name="memos.as",
                status="feature-complete",
                files_processed=25,
                size_mb=0.18,
                complexity_score=6.2,
                success_rate=1.0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            ),
            "devenviro.as": ProjectSummaryResponse(
                project_name="devenviro.as",
                status="integration-ready",
                files_processed=85,
                size_mb=0.92,
                complexity_score=12.1,
                success_rate=0.95,
                last_updated=datetime.now(timezone.utc).isoformat(),
            ),
            "tools.as": ProjectSummaryResponse(
                project_name="tools.as",
                status="standardized",
                files_processed=15,
                size_mb=0.08,
                complexity_score=4.5,
                success_rate=1.0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            ),
        }

        return projects

    except Exception as e:
        logger.error(f"Failed to get project summaries: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get project summaries: {str(e)}"
        )


@router.get("/snapshots/{snapshot_id}")
async def get_ecosystem_snapshot(snapshot_id: str):
    """
    Get a specific ecosystem snapshot by ID.

    Returns detailed information about a historical ecosystem snapshot.
    """
    try:
        # TODO: Implement memOS query for specific snapshot
        logger.info(f"Retrieving ecosystem snapshot: {snapshot_id}")

        # Placeholder response
        return {
            "snapshot_id": snapshot_id,
            "message": "Snapshot retrieval not yet implemented",
            "note": "This will query memOS for historical snapshot data",
        }

    except Exception as e:
        logger.error(f"Failed to get snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {str(e)}")


@router.get("/analysis/cross-project")
async def get_cross_project_analysis():
    """
    Get cross-project analysis including dependencies and relationships.

    Returns analysis of relationships between ecosystem projects.
    """
    try:
        # TODO: Implement memOS query for latest cross-project analysis
        logger.info("Retrieving cross-project analysis")

        # Placeholder response with actual ecosystem relationships
        return {
            "dependency_matrix": {
                "InGest-LLM.as": ["memOS.as", "LM Studio", "Langfuse"],
                "memos.as": ["Redis", "PostgreSQL", "Qdrant", "Neo4j"],
                "devenviro.as": ["memOS.as", "PostgreSQL", "Prometheus", "Grafana"],
                "tools.as": ["FastAPI", "SQLite"],
            },
            "shared_technologies": [
                "Python",
                "FastAPI",
                "Docker",
                "PostgreSQL",
                "Poetry",
            ],
            "integration_points": [
                "memOS.as ↔ InGest-LLM.as (memory storage)",
                "devenviro.as ↔ memOS.as (knowledge queries)",
                "InGest-LLM.as ↔ devenviro.as (orchestration)",
                "tools.as ↔ All projects (development workflow)",
            ],
            "architecture_patterns": [
                "Microservices architecture",
                "Event-driven communication",
                "Multi-tiered memory system",
                "Observability-first design",
                "Docker containerization",
                "FastAPI REST APIs",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get cross-project analysis: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cross-project analysis: {str(e)}"
        )
