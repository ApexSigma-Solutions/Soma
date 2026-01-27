"""
Project Analysis API endpoints using Qwen local model.

This module provides REST API endpoints for generating project outlines
and flow diagrams using the local Qwen model.
"""

from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.project_analyzer import get_qwen_project_analyzer
from ..observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


class ProjectAnalysisRequest(BaseModel):
    """Request model for project analysis."""

    include_diagrams: bool = Field(
        default=True, description="Whether to generate flow diagrams"
    )
    detail_level: str = Field(
        default="comprehensive",
        description="Analysis detail level: basic, standard, comprehensive",
    )


class ProjectOutlineResponse(BaseModel):
    """Response model for project outline."""

    project_name: str
    description: str
    architecture_type: str
    core_components: List[Dict[str, str]]
    api_endpoints: List[Dict[str, str]]
    data_models: List[str]
    services: List[Dict[str, str]]
    dependencies: List[str]
    key_features: List[str]
    integration_points: List[str]


class ServiceRelationshipResponse(BaseModel):
    """Response model for service relationship."""

    source: str
    target: str
    relationship_type: str
    protocol: str
    description: str
    data_flow: str


class EcosystemAnalysisResponse(BaseModel):
    """Response model for complete ecosystem analysis."""

    analysis_id: str
    timestamp: str
    projects: List[ProjectOutlineResponse]
    relationships: List[ServiceRelationshipResponse]
    data_flows: List[Dict[str, Any]]
    integration_patterns: List[str]
    architecture_summary: str
    mermaid_diagram: str


@router.post("/projects", response_model=EcosystemAnalysisResponse)
async def analyze_projects(request: ProjectAnalysisRequest):
    """
    Analyze all ApexSigma projects using the local Qwen model.

    This endpoint uses qwen/qwen3-4b-thinking-2507 to generate:
    - Comprehensive project outlines for each service
    - Relationship mapping between services
    - Data flow analysis
    - Architecture summary
    - Mermaid flow diagram

    The analysis includes:
    - Project structure and components
    - API endpoints and data models
    - Service dependencies and integrations
    - Cross-project relationships
    - Overall ecosystem architecture
    """
    try:
        logger.info("Starting Qwen-powered project analysis")

        # Get analyzer instance
        analyzer = get_qwen_project_analyzer()

        # Perform comprehensive analysis
        flow_diagram = await analyzer.analyze_all_projects()

        # Generate Mermaid diagram if requested
        mermaid_diagram = ""
        if request.include_diagrams:
            mermaid_diagram = await analyzer.generate_mermaid_diagram(flow_diagram)

        # Convert to response format
        projects_response = [
            ProjectOutlineResponse(
                project_name=p.project_name,
                description=p.description,
                architecture_type=p.architecture_type,
                core_components=p.core_components,
                api_endpoints=p.api_endpoints,
                data_models=p.data_models,
                services=p.services,
                dependencies=p.dependencies,
                key_features=p.key_features,
                integration_points=p.integration_points,
            )
            for p in flow_diagram.projects
        ]

        relationships_response = [
            ServiceRelationshipResponse(
                source=r.source,
                target=r.target,
                relationship_type=r.relationship_type,
                protocol=r.protocol,
                description=r.description,
                data_flow=r.data_flow,
            )
            for r in flow_diagram.relationships
        ]

        analysis_id = f"qwen_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        response = EcosystemAnalysisResponse(
            analysis_id=analysis_id,
            timestamp=datetime.now().isoformat(),
            projects=projects_response,
            relationships=relationships_response,
            data_flows=flow_diagram.data_flows,
            integration_patterns=flow_diagram.integration_patterns,
            architecture_summary=flow_diagram.architecture_summary,
            mermaid_diagram=mermaid_diagram,
        )

        logger.info(
            f"Analysis completed: {len(projects_response)} projects, {len(relationships_response)} relationships"
        )
        return response

    except Exception as e:
        logger.error(f"Project analysis failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Project analysis failed: {str(e)}"
        )


@router.get("/projects/{project_name}", response_model=ProjectOutlineResponse)
async def analyze_single_project(project_name: str):
    """
    Analyze a single ApexSigma project using Qwen model.

    Returns detailed outline and analysis for the specified project.
    """
    try:
        logger.info(f"Analyzing single project: {project_name}")

        analyzer = get_qwen_project_analyzer()

        # Check if project exists
        if project_name not in analyzer.projects:
            raise HTTPException(
                status_code=404, detail=f"Project '{project_name}' not found"
            )

        project_path = analyzer.projects[project_name]
        outline = await analyzer._analyze_single_project(project_name, project_path)

        if not outline:
            raise HTTPException(
                status_code=500, detail=f"Failed to analyze project '{project_name}'"
            )

        return ProjectOutlineResponse(
            project_name=outline.project_name,
            description=outline.description,
            architecture_type=outline.architecture_type,
            core_components=outline.core_components,
            api_endpoints=outline.api_endpoints,
            data_models=outline.data_models,
            services=outline.services,
            dependencies=outline.dependencies,
            key_features=outline.key_features,
            integration_points=outline.integration_points,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single project analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/relationships", response_model=List[ServiceRelationshipResponse])
async def get_project_relationships():
    """
    Get relationships between ApexSigma projects.

    Returns detailed mapping of how services interact with each other.
    """
    try:
        logger.info("Analyzing project relationships")

        analyzer = get_qwen_project_analyzer()
        flow_diagram = await analyzer.analyze_all_projects()

        return [
            ServiceRelationshipResponse(
                source=r.source,
                target=r.target,
                relationship_type=r.relationship_type,
                protocol=r.protocol,
                description=r.description,
                data_flow=r.data_flow,
            )
            for r in flow_diagram.relationships
        ]

    except Exception as e:
        logger.error(f"Relationship analysis failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Relationship analysis failed: {str(e)}"
        )


@router.get("/diagram/mermaid")
async def get_mermaid_diagram(
    format: str = Query(default="text", description="Output format: text or html"),
):
    """
    Generate Mermaid flow diagram of the ApexSigma ecosystem.

    Returns the diagram in either text format (for embedding) or HTML format (for viewing).
    """
    try:
        logger.info("Generating Mermaid flow diagram")

        analyzer = get_qwen_project_analyzer()
        flow_diagram = await analyzer.analyze_all_projects()
        mermaid_code = await analyzer.generate_mermaid_diagram(flow_diagram)

        if format == "html":
            html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ApexSigma Ecosystem Flow Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <h1>ApexSigma Ecosystem Architecture</h1>
    <div class="mermaid">
{mermaid_code}
    </div>
    <script>
        mermaid.initialize({{startOnLoad:true}});
    </script>
</body>
</html>
            """
            return {"format": "html", "content": html_template}
        else:
            return {"format": "mermaid", "content": mermaid_code}

    except Exception as e:
        logger.error(f"Diagram generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Diagram generation failed: {str(e)}"
        )


@router.get("/architecture-summary")
async def get_architecture_summary():
    """
    Get comprehensive architecture summary of the ApexSigma ecosystem.

    Returns a detailed summary generated by Qwen model describing the
    overall system architecture, integration patterns, and capabilities.
    """
    try:
        logger.info("Generating architecture summary")

        analyzer = get_qwen_project_analyzer()
        flow_diagram = await analyzer.analyze_all_projects()

        return {
            "summary": flow_diagram.architecture_summary,
            "integration_patterns": flow_diagram.integration_patterns,
            "projects_count": len(flow_diagram.projects),
            "relationships_count": len(flow_diagram.relationships),
            "data_flows_count": len(flow_diagram.data_flows),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Architecture summary generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Architecture summary generation failed: {str(e)}"
        )
