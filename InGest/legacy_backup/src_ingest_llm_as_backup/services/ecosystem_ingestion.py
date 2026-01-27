"""
ApexSigma Ecosystem Ingestion Service

This module provides comprehensive ingestion capabilities for the entire ApexSigma
ecosystem, including all four core projects: InGest-LLM.as, memos.as, devenviro.as,
and tools.as. It creates historical snapshots and maintains a living knowledge base.
"""

import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from uuid import uuid4

from ..models import (
    RepositoryIngestionRequest,
    RepositorySource,
    IngestionMetadata,
    MemoryTier,
)
from ..services.repository_processor import get_repository_processor
from ..services.progress_logger import get_progress_logger
from ..services.memos_client import get_memos_client
from ..observability.logging import get_logger
from ..observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)


@dataclass
class ProjectInfo:
    """Information about an ApexSigma project."""

    name: str
    path: str
    description: str
    status: str
    primary_language: str
    key_features: List[str]
    dependencies: List[str]


@dataclass
class EcosystemSnapshot:
    """Complete snapshot of the ApexSigma ecosystem."""

    snapshot_id: str
    timestamp: str
    total_projects: int
    total_files: int
    total_size_bytes: int
    total_lines_of_code: int
    projects: List[Dict[str, Any]]
    cross_project_analysis: Dict[str, Any]
    ecosystem_health: Dict[str, Any]
    recommendations: List[str]


class EcosystemIngestionService:
    """
    Comprehensive ingestion service for the entire ApexSigma ecosystem.

    Handles scraping, analyzing, and embedding all four core projects with
    historical tracking and cross-project relationship analysis.
    """

    def __init__(self, base_path: str = "C:\\Users\\steyn\\ApexSigmaProjects.Dev"):
        """Initialize the ecosystem ingestion service."""
        self.base_path = Path(base_path)
        self.logger = get_logger(__name__)
        self.langfuse_client = get_langfuse_client()
        self.progress_logger = get_progress_logger()
        self.memos_client = get_memos_client()
        self.repository_processor = get_repository_processor()

        # Define ApexSigma projects
        self.projects = {
            "InGest-LLM.as": ProjectInfo(
                name="InGest-LLM.as",
                path="InGest-LLM.as",
                description="Data ingestion microservice for processing and embedding content",
                status="production-ready",
                primary_language="python",
                key_features=[
                    "Repository ingestion",
                    "Python AST parsing",
                    "Embedding generation",
                    "Progress tracking",
                    "memOS integration",
                    "Comprehensive observability",
                ],
                dependencies=["memOS.as", "LM Studio", "Langfuse"],
            ),
            "memos.as": ProjectInfo(
                name="memos.as",
                path="memos.as",
                description="Memory Operating System - central brain and knowledge storage",
                status="feature-complete",
                primary_language="python",
                key_features=[
                    "Multi-tiered memory",
                    "Knowledge graph",
                    "Vector storage",
                    "Redis caching",
                    "PostgreSQL persistence",
                    "Neo4j relationships",
                ],
                dependencies=["Redis", "PostgreSQL", "Qdrant", "Neo4j"],
            ),
            "devenviro.as": ProjectInfo(
                name="devenviro.as",
                path="devenviro.as",
                description="Orchestrator and team lead of the agent society",
                status="integration-ready",
                primary_language="python",
                key_features=[
                    "Agent orchestration",
                    "Task assignment",
                    "Workflow management",
                    "Multi-model integration",
                    "Observability stack",
                    "Communication protocols",
                ],
                dependencies=["memOS.as", "PostgreSQL", "Prometheus", "Grafana"],
            ),
            "tools.as": ProjectInfo(
                name="tools.as",
                path="tools.as",
                description="Developer tooling suite for ecosystem automation",
                status="standardized",
                primary_language="python",
                key_features=[
                    "CLI tooling",
                    "Documentation automation",
                    "Development workflows",
                    "Build systems",
                    "Deployment tools",
                ],
                dependencies=["FastAPI", "SQLite"],
            ),
        }

    async def ingest_entire_ecosystem(
        self, include_historical: bool = True, generate_cross_analysis: bool = True
    ) -> EcosystemSnapshot:
        """
        Ingest the entire ApexSigma ecosystem.

        Args:
            include_historical: Whether to store historical snapshots
            generate_cross_analysis: Whether to perform cross-project analysis

        Returns:
            EcosystemSnapshot: Complete ecosystem analysis
        """
        snapshot_id = str(uuid4())
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Starting ecosystem ingestion - Snapshot ID: {snapshot_id}")

        # Create Langfuse trace for ecosystem ingestion
        trace_id = None
        if self.langfuse_client.enabled:
            trace_id = self.langfuse_client.create_trace(
                name="ecosystem_ingestion",
                metadata={
                    "snapshot_id": snapshot_id,
                    "projects_count": len(self.projects),
                    "include_historical": include_historical,
                    "generate_cross_analysis": generate_cross_analysis,
                },
                tags=["ecosystem", "complete_ingestion", "apexsigma"],
            )

        project_results = []
        total_files = 0
        total_size = 0
        total_lines = 0

        try:
            # Process each project
            for project_name, project_info in self.projects.items():
                self.logger.info(f"Processing project: {project_name}")

                project_result = await self._ingest_single_project(
                    project_info, snapshot_id, trace_id
                )

                if project_result:
                    project_results.append(project_result)
                    total_files += project_result.get("files_processed", 0)
                    total_size += project_result.get("total_size_bytes", 0)
                    total_lines += project_result.get("total_lines_of_code", 0)

            # Generate cross-project analysis
            cross_analysis = {}
            if generate_cross_analysis and project_results:
                cross_analysis = await self._generate_cross_project_analysis(
                    project_results, snapshot_id
                )

            # Generate ecosystem health metrics
            ecosystem_health = self._calculate_ecosystem_health(project_results)

            # Generate recommendations
            recommendations = self._generate_ecosystem_recommendations(
                project_results, cross_analysis, ecosystem_health
            )

            # Create ecosystem snapshot
            snapshot = EcosystemSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                total_projects=len(project_results),
                total_files=total_files,
                total_size_bytes=total_size,
                total_lines_of_code=total_lines,
                projects=project_results,
                cross_project_analysis=cross_analysis,
                ecosystem_health=ecosystem_health,
                recommendations=recommendations,
            )

            # Store historical snapshot if requested
            if include_historical:
                await self._store_ecosystem_snapshot(snapshot)

            # Record success in Langfuse
            if self.langfuse_client.enabled and trace_id:
                self.langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": True,
                        "snapshot_id": snapshot_id,
                        "projects_processed": len(project_results),
                        "total_files": total_files,
                        "total_size_mb": total_size / (1024 * 1024),
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                    },
                )

                # Score ecosystem complexity
                complexity_score = min(1.0, total_files / 1000)  # Normalize
                self.langfuse_client.score_trace(
                    trace_id=trace_id,
                    name="ecosystem_complexity",
                    value=complexity_score,
                    comment=f"Ecosystem with {total_files} files across {len(project_results)} projects",
                )

            total_time = int((time.time() - start_time) * 1000)
            self.logger.info(
                f"Ecosystem ingestion complete: {len(project_results)} projects, "
                f"{total_files} files, {total_time}ms"
            )

            return snapshot

        except Exception as e:
            self.logger.error(f"Ecosystem ingestion failed: {e}")

            # Record error in Langfuse
            if self.langfuse_client.enabled and trace_id:
                self.langfuse_client.client.trace(
                    id=trace_id,
                    output={
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

            raise

    async def _ingest_single_project(
        self,
        project_info: ProjectInfo,
        snapshot_id: str,
        parent_trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Ingest a single project in the ecosystem.

        Args:
            project_info: Project information
            snapshot_id: Ecosystem snapshot ID
            parent_trace_id: Parent Langfuse trace ID

        Returns:
            Optional[Dict[str, Any]]: Project ingestion results
        """
        project_path = self.base_path / project_info.path

        if not project_path.exists():
            self.logger.warning(f"Project path not found: {project_path}")
            return None

        try:
            # Create ingestion request
            request = RepositoryIngestionRequest(
                repository_source=RepositorySource.LOCAL_PATH,
                source_path=str(project_path),
                metadata=IngestionMetadata(
                    source="ecosystem_ingestion",
                    tags=[
                        "apexsigma",
                        "ecosystem",
                        project_info.name.lower().replace(".", "_"),
                        project_info.status,
                        "historical_snapshot",
                    ],
                    custom_fields={
                        "ecosystem_snapshot_id": snapshot_id,
                        "project_name": project_info.name,
                        "project_status": project_info.status,
                        "primary_language": project_info.primary_language,
                        "ingestion_type": "ecosystem_complete",
                    },
                ),
                include_patterns=[
                    "**/*.py",
                    "**/*.md",
                    "**/*.yml",
                    "**/*.yaml",
                    "**/*.toml",
                    "**/*.json",
                    "**/*.sql",
                    "**/*.sh",
                    "**/*.js",
                    "**/*.ts",
                    "**/*.dockerfile",
                    "**/Dockerfile",
                ],
                exclude_patterns=[
                    "__pycache__/**",
                    ".pytest_cache/**",
                    ".git/**",
                    ".venv/**",
                    "venv/**",
                    "*.pyc",
                    ".env*",
                    "node_modules/**",
                    ".mypy_cache/**",
                    "*.egg-info/**",
                    "dist/**",
                    "build/**",
                    ".coverage",
                    "htmlcov/**",
                    "logs/**",
                    "*.log",
                    "tmp/**",
                    "temp/**",
                ],
                max_files=500,  # Reasonable limit per project
                max_file_size=2_000_000,  # 2MB limit
                process_async=False,
            )

            # Process the project repository
            response = await self.repository_processor.process_repository(request)

            if response.status.value == "completed":
                # Extract project metrics
                project_result = {
                    "project_name": project_info.name,
                    "project_info": asdict(project_info),
                    "ingestion_id": str(response.ingestion_id),
                    "repository_path": str(project_path),
                    "files_discovered": response.files_discovered,
                    "files_processed": len(response.files_processed),
                    "discovery_time_ms": response.discovery_time_ms,
                    "processing_time_ms": response.processing_time_ms,
                    "total_time_ms": response.total_time_ms,
                    "processing_summary": asdict(response.processing_summary)
                    if response.processing_summary
                    else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # Calculate additional metrics
                successful_files = [
                    f for f in response.files_processed if f.status.value == "completed"
                ]
                project_result.update(
                    {
                        "success_rate": len(successful_files)
                        / len(response.files_processed)
                        if response.files_processed
                        else 0,
                        "total_size_bytes": sum(f.file_size for f in successful_files),
                        "total_elements_extracted": sum(
                            f.elements_extracted for f in successful_files
                        ),
                        "total_lines_of_code": self._estimate_total_lines(
                            successful_files
                        ),
                        "average_complexity": self._calculate_average_complexity(
                            successful_files
                        ),
                        "file_types": self._analyze_file_types(successful_files),
                    }
                )

                return project_result
            else:
                self.logger.error(
                    f"Project ingestion failed for {project_info.name}: {response.message}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error ingesting project {project_info.name}: {e}")
            return None

    async def _generate_cross_project_analysis(
        self, project_results: List[Dict[str, Any]], snapshot_id: str
    ) -> Dict[str, Any]:
        """Generate cross-project analysis and relationships."""
        analysis = {
            "dependency_matrix": {},
            "shared_technologies": [],
            "size_comparison": {},
            "complexity_comparison": {},
            "architecture_patterns": [],
            "integration_points": [],
        }

        # Analyze dependencies between projects
        for project in project_results:
            project_name = project["project_name"]
            project_info = project["project_info"]

            analysis["dependency_matrix"][project_name] = project_info.get(
                "dependencies", []
            )

            # Size comparison
            analysis["size_comparison"][project_name] = {
                "files": project.get("files_processed", 0),
                "size_mb": project.get("total_size_bytes", 0) / (1024 * 1024),
                "lines_of_code": project.get("total_lines_of_code", 0),
            }

            # Complexity comparison
            analysis["complexity_comparison"][project_name] = {
                "average_complexity": project.get("average_complexity", 0),
                "elements_extracted": project.get("total_elements_extracted", 0),
            }

        # Identify shared technologies
        all_dependencies = set()
        for project in project_results:
            deps = project["project_info"].get("dependencies", [])
            all_dependencies.update(deps)

        analysis["shared_technologies"] = list(all_dependencies)

        # Identify architecture patterns
        analysis["architecture_patterns"] = [
            "Microservices architecture",
            "Event-driven communication",
            "Multi-tiered memory system",
            "Observability-first design",
            "Docker containerization",
            "FastAPI REST APIs",
        ]

        # Integration points
        analysis["integration_points"] = [
            "memOS.as ↔ InGest-LLM.as (memory storage)",
            "devenviro.as ↔ memOS.as (knowledge queries)",
            "InGest-LLM.as ↔ devenviro.as (orchestration)",
            "tools.as ↔ All projects (development workflow)",
        ]

        return analysis

    def _calculate_ecosystem_health(
        self, project_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall ecosystem health metrics."""
        if not project_results:
            return {"status": "unhealthy", "score": 0.0}

        total_projects = len(project_results)
        successful_projects = len(
            [p for p in project_results if p.get("success_rate", 0) > 0.8]
        )

        # Calculate health score
        health_score = successful_projects / total_projects

        # Assess individual project health
        project_health = {}
        for project in project_results:
            name = project["project_name"]
            success_rate = project.get("success_rate", 0)
            complexity = project.get("average_complexity", 0)

            if success_rate > 0.9 and complexity < 10:
                project_health[name] = "excellent"
            elif success_rate > 0.8 and complexity < 15:
                project_health[name] = "good"
            elif success_rate > 0.7:
                project_health[name] = "fair"
            else:
                project_health[name] = "needs_attention"

        return {
            "overall_score": health_score,
            "status": "healthy"
            if health_score > 0.8
            else "needs_attention"
            if health_score > 0.6
            else "unhealthy",
            "successful_projects": successful_projects,
            "total_projects": total_projects,
            "project_health": project_health,
            "assessment_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_ecosystem_recommendations(
        self,
        project_results: List[Dict[str, Any]],
        cross_analysis: Dict[str, Any],
        health: Dict[str, Any],
    ) -> List[str]:
        """Generate ecosystem-level recommendations."""
        recommendations = []

        # Health-based recommendations
        if health["overall_score"] < 0.8:
            recommendations.append(
                "Improve project ingestion success rates across the ecosystem"
            )

        # Complexity recommendations
        high_complexity_projects = [
            p["project_name"]
            for p in project_results
            if p.get("average_complexity", 0) > 12
        ]
        if high_complexity_projects:
            recommendations.append(
                f"Consider refactoring high-complexity projects: {', '.join(high_complexity_projects)}"
            )

        # Size recommendations
        large_projects = [
            p["project_name"]
            for p in project_results
            if p.get("total_size_bytes", 0) > 1_000_000  # > 1MB
        ]
        if len(large_projects) > 2:
            recommendations.append(
                "Monitor codebase growth and consider modularization"
            )

        # Documentation recommendations
        total_md_files = sum(
            p.get("file_types", {}).get(".md", 0) for p in project_results
        )
        total_py_files = sum(
            p.get("file_types", {}).get(".py", 0) for p in project_results
        )

        if total_py_files > 0 and (total_md_files / total_py_files) < 0.3:
            recommendations.append("Increase documentation coverage across projects")

        # Integration recommendations
        recommendations.extend(
            [
                "Maintain regular ecosystem snapshots for historical analysis",
                "Continue developing cross-project integration patterns",
                "Implement automated ecosystem health monitoring",
                "Consider creating unified development workflows across projects",
            ]
        )

        return recommendations

    async def _store_ecosystem_snapshot(self, snapshot: EcosystemSnapshot) -> None:
        """Store ecosystem snapshot in memOS for historical reference."""
        try:
            # Create comprehensive ecosystem report
            content = f"ApexSigma Ecosystem Snapshot\n{'=' * 50}\n\n"
            content += f"Snapshot ID: {snapshot.snapshot_id}\n"
            content += f"Timestamp: {snapshot.timestamp}\n"
            content += f"Projects Analyzed: {snapshot.total_projects}\n"
            content += f"Total Files: {snapshot.total_files}\n"
            content += (
                f"Total Size: {snapshot.total_size_bytes / (1024 * 1024):.1f} MB\n"
            )
            content += f"Total Lines of Code: {snapshot.total_lines_of_code:,}\n\n"

            # Project summaries
            content += "Project Summaries\n" + "-" * 20 + "\n"
            for project in snapshot.projects:
                content += f"\n{project['project_name']}:\n"
                content += f"  Status: {project['project_info']['status']}\n"
                content += f"  Files: {project['files_processed']}\n"
                content += (
                    f"  Size: {project.get('total_size_bytes', 0) / 1024:.1f} KB\n"
                )
                content += f"  Complexity: {project.get('average_complexity', 0):.2f}\n"

            # Cross-project analysis
            if snapshot.cross_project_analysis:
                content += "\n\nCross-Project Analysis\n" + "-" * 25 + "\n"
                content += f"Shared Technologies: {', '.join(snapshot.cross_project_analysis.get('shared_technologies', []))}\n"
                content += f"Architecture Patterns: {len(snapshot.cross_project_analysis.get('architecture_patterns', []))}\n"
                content += f"Integration Points: {len(snapshot.cross_project_analysis.get('integration_points', []))}\n"

            # Ecosystem health
            content += "\n\nEcosystem Health\n" + "-" * 20 + "\n"
            content += f"Overall Score: {snapshot.ecosystem_health.get('overall_score', 0):.2f}\n"
            content += f"Status: {snapshot.ecosystem_health.get('status', 'unknown')}\n"

            # Recommendations
            if snapshot.recommendations:
                content += "\n\nRecommendations\n" + "-" * 15 + "\n"
                for rec in snapshot.recommendations:
                    content += f"• {rec}\n"

            # Store in memOS
            metadata = {
                "snapshot_id": snapshot.snapshot_id,
                "ecosystem_snapshot": True,
                "projects_count": snapshot.total_projects,
                "total_files": snapshot.total_files,
                "entry_type": "ecosystem_snapshot",
            }

            await self.memos_client.store_memory(
                content=content,
                memory_tier=MemoryTier.SEMANTIC,  # Long-term ecosystem knowledge
                metadata=metadata,
            )

            # Also store detailed JSON data
            json_content = "ApexSigma Ecosystem Snapshot - Detailed Data\n\n"
            json_content += json.dumps(asdict(snapshot), indent=2)

            await self.memos_client.store_memory(
                content=json_content,
                memory_tier=MemoryTier.SEMANTIC,
                metadata={
                    **metadata,
                    "entry_type": "ecosystem_snapshot_data",
                    "format": "json",
                },
            )

            self.logger.info(
                f"Stored ecosystem snapshot {snapshot.snapshot_id} in memOS"
            )

        except Exception as e:
            self.logger.warning(f"Failed to store ecosystem snapshot in memOS: {e}")

    def _estimate_total_lines(self, successful_files: List[Any]) -> int:
        """Estimate total lines of code from file results."""
        return sum(
            max(1, f.file_size // 50) for f in successful_files
        )  # ~50 chars per line

    def _calculate_average_complexity(self, successful_files: List[Any]) -> float:
        """Calculate average complexity across files."""
        complexities = [
            f.complexity_score
            for f in successful_files
            if f.complexity_score and f.complexity_score > 0
        ]
        return sum(complexities) / len(complexities) if complexities else 0.0

    def _analyze_file_types(self, successful_files: List[Any]) -> Dict[str, int]:
        """Analyze file type distribution."""
        file_types = {}
        for file_result in successful_files:
            ext = Path(file_result.relative_path).suffix or "no_extension"
            file_types[ext] = file_types.get(ext, 0) + 1
        return file_types


# Global ecosystem ingestion service instance
_ecosystem_service: Optional[EcosystemIngestionService] = None


def get_ecosystem_ingestion_service() -> EcosystemIngestionService:
    """
    Get the global ecosystem ingestion service instance.

    Returns:
        EcosystemIngestionService: Configured service instance
    """
    global _ecosystem_service
    if _ecosystem_service is None:
        _ecosystem_service = EcosystemIngestionService()
    return _ecosystem_service
