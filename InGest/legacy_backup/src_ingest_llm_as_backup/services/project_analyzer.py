"""
Project Analyzer Service using Qwen Local Model

This service uses the local Qwen model to analyze each ApexSigma project
and generate comprehensive outlines and flow diagrams showing relationships.
"""

import json
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from ..observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProjectOutline:
    """Structured outline of a project."""

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


@dataclass
class ServiceRelationship:
    """Relationship between services."""

    source: str
    target: str
    relationship_type: (
        str  # "depends_on", "communicates_with", "stores_in", "orchestrates"
    )
    protocol: str  # "HTTP/REST", "Direct", "Database", "Memory"
    description: str
    data_flow: str  # "bidirectional", "source_to_target", "target_to_source"


@dataclass
class EcosystemFlowDiagram:
    """Complete ecosystem flow diagram."""

    projects: List[ProjectOutline]
    relationships: List[ServiceRelationship]
    data_flows: List[Dict[str, Any]]
    integration_patterns: List[str]
    architecture_summary: str


class QwenProjectAnalyzer:
    """
    Analyzes ApexSigma projects using the local Qwen model.

    Uses qwen/qwen3-4b-thinking-2507 to generate comprehensive project
    outlines and relationship diagrams.
    """

    def __init__(self, qwen_base_url: str = "http://172.22.144.1:12345/v1"):
        """Initialize the Qwen analyzer."""
        self.qwen_base_url = qwen_base_url
        self.logger = get_logger(__name__)
        self.client = httpx.AsyncClient(timeout=60.0)

        # Project paths
        self.base_path = Path("C:\\Users\\steyn\\ApexSigmaProjects.Dev")
        self.projects = {
            "InGest-LLM.as": self.base_path / "InGest-LLM.as",
            "memos.as": self.base_path / "memos.as",
            "devenviro.as": self.base_path / "devenviro.as",
            "tools.as": self.base_path / "tools.as",
        }

    async def analyze_all_projects(self) -> EcosystemFlowDiagram:
        """
        Analyze all ApexSigma projects and generate ecosystem flow diagram.

        Returns:
            EcosystemFlowDiagram: Complete ecosystem analysis
        """
        self.logger.info("Starting comprehensive project analysis with Qwen model")

        # Analyze each project individually
        project_outlines = []
        for project_name, project_path in self.projects.items():
            if project_path.exists():
                self.logger.info(f"Analyzing project: {project_name}")
                outline = await self._analyze_single_project(project_name, project_path)
                if outline:
                    project_outlines.append(outline)

        # Generate relationship analysis
        relationships = await self._analyze_project_relationships(project_outlines)

        # Generate data flow analysis
        data_flows = await self._analyze_data_flows(project_outlines, relationships)

        # Generate architecture summary
        architecture_summary = await self._generate_architecture_summary(
            project_outlines, relationships, data_flows
        )

        return EcosystemFlowDiagram(
            projects=project_outlines,
            relationships=relationships,
            data_flows=data_flows,
            integration_patterns=self._extract_integration_patterns(relationships),
            architecture_summary=architecture_summary,
        )

    async def _analyze_single_project(
        self, project_name: str, project_path: Path
    ) -> Optional[ProjectOutline]:
        """Analyze a single project using Qwen model."""

        try:
            # Gather project information
            project_info = await self._gather_project_info(project_path)

            # Create analysis prompt for Qwen
            prompt = self._create_project_analysis_prompt(project_name, project_info)

            # Query Qwen model
            analysis_result = await self._query_qwen_model(prompt)

            # Parse and structure the result
            outline = self._parse_project_outline(project_name, analysis_result)

            return outline

        except Exception as e:
            self.logger.error(f"Failed to analyze project {project_name}: {e}")
            return None

    async def _gather_project_info(self, project_path: Path) -> Dict[str, Any]:
        """Gather comprehensive information about a project."""

        project_info = {
            "structure": {},
            "key_files": {},
            "dependencies": [],
            "apis": [],
            "services": [],
        }

        # Analyze directory structure
        project_info["structure"] = self._analyze_directory_structure(project_path)

        # Find key files
        key_files = [
            "README.md",
            "pyproject.toml",
            "docker-compose.yml",
            "Dockerfile",
            "main.py",
            "app.py",
            "models.py",
        ]

        for file_name in key_files:
            file_path = project_path / file_name
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    project_info["key_files"][file_name] = content[
                        :2000
                    ]  # Limit content
                except Exception as e:
                    self.logger.warning(f"Could not read {file_path}: {e}")

        # Find Python main files and APIs
        for py_file in project_path.glob("**/*.py"):
            if py_file.name in ["main.py", "app.py"] or "api" in str(py_file):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if len(content) < 5000:  # Only include smaller files
                        project_info["apis"].append(
                            {
                                "file": str(py_file.relative_to(project_path)),
                                "content": content[:1500],
                            }
                        )
                except Exception:
                    pass

        return project_info

    def _analyze_directory_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze the directory structure of a project."""

        structure = {"directories": [], "file_counts": {}}

        try:
            for item in project_path.iterdir():
                if (
                    item.is_dir()
                    and not item.name.startswith(".")
                    and item.name != "__pycache__"
                ):
                    structure["directories"].append(item.name)

            # Count file types
            for ext in [".py", ".md", ".yml", ".yaml", ".json", ".toml"]:
                count = len(list(project_path.glob(f"**/*{ext}")))
                if count > 0:
                    structure["file_counts"][ext] = count

        except Exception as e:
            self.logger.warning(f"Error analyzing structure for {project_path}: {e}")

        return structure

    def _create_project_analysis_prompt(
        self, project_name: str, project_info: Dict[str, Any]
    ) -> str:
        """Create a comprehensive analysis prompt for Qwen."""

        prompt = f"""As an expert software architect, analyze the ApexSigma project "{project_name}" and provide a comprehensive outline.

PROJECT INFORMATION:
Project: {project_name}
Directory Structure: {project_info.get("structure", {}).get("directories", [])}
File Counts: {project_info.get("structure", {}).get("file_counts", {})}

KEY FILES CONTENT:
"""

        # Add key file contents
        for file_name, content in project_info.get("key_files", {}).items():
            prompt += f"\n{file_name}:\n```\n{content[:800]}\n```\n"

        # Add API information
        if project_info.get("apis"):
            prompt += "\nAPI FILES:\n"
            for api_info in project_info["apis"][:2]:  # Limit to 2 API files
                prompt += f"\n{api_info['file']}:\n```python\n{api_info['content'][:800]}\n```\n"

        prompt += """

Please provide a detailed analysis in the following JSON format:

{
  "description": "Brief description of the project's purpose",
  "architecture_type": "microservice/monolith/library/tool",
  "core_components": [
    {"name": "component_name", "description": "what it does", "type": "service/api/database/etc"}
  ],
  "api_endpoints": [
    {"method": "GET/POST", "path": "/endpoint", "description": "what it does"}
  ],
  "data_models": ["ModelName1", "ModelName2"],
  "services": [
    {"name": "service_name", "description": "what it provides", "type": "internal/external"}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "key_features": ["feature1", "feature2"],
  "integration_points": ["integrates with X via Y", "stores data in Z"]
}

Focus on:
1. The main purpose and architecture pattern
2. Key services and components
3. API endpoints and data models
4. External dependencies
5. Integration points with other systems
6. Unique features and capabilities

Provide only the JSON response, no additional text."""

        return prompt

    async def _query_qwen_model(self, prompt: str) -> str:
        """Query the local Qwen model."""

        try:
            response = await self.client.post(
                f"{self.qwen_base_url}/chat/completions",
                json={
                    "model": "qwen/qwen3-4b-thinking-2507",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert software architect analyzing codebases. Provide detailed, accurate JSON responses.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                self.logger.error(
                    f"Qwen API error: {response.status_code} - {response.text}"
                )
                return ""

        except Exception as e:
            self.logger.error(f"Error querying Qwen model: {e}")
            return ""

    def _parse_project_outline(
        self, project_name: str, analysis_result: str
    ) -> Optional[ProjectOutline]:
        """Parse the Qwen analysis result into a ProjectOutline."""

        try:
            # Clean the response and extract JSON
            json_str = analysis_result.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]

            data = json.loads(json_str.strip())

            return ProjectOutline(
                project_name=project_name,
                description=data.get("description", ""),
                architecture_type=data.get("architecture_type", "unknown"),
                core_components=data.get("core_components", []),
                api_endpoints=data.get("api_endpoints", []),
                data_models=data.get("data_models", []),
                services=data.get("services", []),
                dependencies=data.get("dependencies", []),
                key_features=data.get("key_features", []),
                integration_points=data.get("integration_points", []),
            )

        except Exception as e:
            self.logger.error(f"Error parsing analysis result for {project_name}: {e}")
            self.logger.debug(f"Raw result: {analysis_result[:500]}")
            return None

    async def _analyze_project_relationships(
        self, project_outlines: List[ProjectOutline]
    ) -> List[ServiceRelationship]:
        """Analyze relationships between projects using Qwen."""

        # Create relationship analysis prompt
        prompt = self._create_relationship_analysis_prompt(project_outlines)

        # Query Qwen for relationship analysis
        relationship_result = await self._query_qwen_model(prompt)

        # Parse relationships
        return self._parse_relationships(relationship_result)

    def _create_relationship_analysis_prompt(
        self, project_outlines: List[ProjectOutline]
    ) -> str:
        """Create prompt for analyzing project relationships."""

        prompt = """Analyze the relationships between these ApexSigma projects and identify how they interact:

PROJECTS:
"""

        for outline in project_outlines:
            prompt += f"\n{outline.project_name}:\n"
            prompt += f"  Type: {outline.architecture_type}\n"
            prompt += f"  Description: {outline.description}\n"
            prompt += f"  Key Features: {', '.join(outline.key_features[:3])}\n"
            prompt += f"  Dependencies: {', '.join(outline.dependencies[:3])}\n"
            prompt += (
                f"  Integration Points: {', '.join(outline.integration_points[:2])}\n"
            )

        prompt += """

Based on the project information, identify the relationships between these services. 

Provide your analysis in this JSON format:

{
  "relationships": [
    {
      "source": "Project1",
      "target": "Project2", 
      "relationship_type": "depends_on|communicates_with|stores_in|orchestrates",
      "protocol": "HTTP/REST|Direct|Database|Memory",
      "description": "how they interact",
      "data_flow": "bidirectional|source_to_target|target_to_source"
    }
  ]
}

Focus on:
1. Direct dependencies (one service needs another)
2. Communication patterns (APIs, databases, memory)
3. Data flow directions
4. Integration protocols

Provide only the JSON response."""

        return prompt

    def _parse_relationships(
        self, relationship_result: str
    ) -> List[ServiceRelationship]:
        """Parse relationship analysis result."""

        try:
            # Clean and parse JSON
            json_str = relationship_result.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]

            data = json.loads(json_str.strip())

            relationships = []
            for rel_data in data.get("relationships", []):
                relationships.append(
                    ServiceRelationship(
                        source=rel_data.get("source", ""),
                        target=rel_data.get("target", ""),
                        relationship_type=rel_data.get("relationship_type", "unknown"),
                        protocol=rel_data.get("protocol", "unknown"),
                        description=rel_data.get("description", ""),
                        data_flow=rel_data.get("data_flow", "unknown"),
                    )
                )

            return relationships

        except Exception as e:
            self.logger.error(f"Error parsing relationships: {e}")
            return []

    async def _analyze_data_flows(
        self,
        project_outlines: List[ProjectOutline],
        relationships: List[ServiceRelationship],
    ) -> List[Dict[str, Any]]:
        """Analyze data flows between projects."""

        data_flows = []

        # Create data flows based on relationships
        for rel in relationships:
            if rel.relationship_type in ["stores_in", "communicates_with"]:
                data_flows.append(
                    {
                        "flow_id": f"{rel.source}_to_{rel.target}",
                        "source": rel.source,
                        "target": rel.target,
                        "data_type": self._infer_data_type(rel),
                        "protocol": rel.protocol,
                        "direction": rel.data_flow,
                        "description": rel.description,
                    }
                )

        return data_flows

    def _infer_data_type(self, relationship: ServiceRelationship) -> str:
        """Infer the type of data being exchanged."""

        if (
            "memory" in relationship.description.lower()
            or "storage" in relationship.description.lower()
        ):
            return "knowledge_data"
        elif (
            "api" in relationship.description.lower()
            or "endpoint" in relationship.description.lower()
        ):
            return "api_requests"
        elif (
            "task" in relationship.description.lower()
            or "orchestrat" in relationship.description.lower()
        ):
            return "task_coordination"
        elif (
            "ingest" in relationship.description.lower()
            or "process" in relationship.description.lower()
        ):
            return "content_data"
        else:
            return "general_data"

    async def _generate_architecture_summary(
        self,
        project_outlines: List[ProjectOutline],
        relationships: List[ServiceRelationship],
        data_flows: List[Dict[str, Any]],
    ) -> str:
        """Generate overall architecture summary using Qwen."""

        prompt = f"""Provide a comprehensive architecture summary for the ApexSigma ecosystem based on this analysis:

PROJECTS ({len(project_outlines)}):
"""

        for outline in project_outlines:
            prompt += f"- {outline.project_name}: {outline.description} ({outline.architecture_type})\n"

        prompt += f"\nRELATIONSHIPS ({len(relationships)}):\n"
        for rel in relationships:
            prompt += f"- {rel.source} → {rel.target}: {rel.relationship_type} via {rel.protocol}\n"

        prompt += f"\nDATA FLOWS ({len(data_flows)}):\n"
        for flow in data_flows:
            prompt += f"- {flow['source']} → {flow['target']}: {flow['data_type']} ({flow['direction']})\n"

        prompt += """

Provide a 2-3 paragraph architectural summary that describes:
1. The overall system architecture pattern
2. How the services work together
3. Key integration points and data flows
4. The ecosystem's purpose and capabilities

Write in clear, technical language suitable for developers and architects."""

        summary = await self._query_qwen_model(prompt)
        return summary.strip()

    def _extract_integration_patterns(
        self, relationships: List[ServiceRelationship]
    ) -> List[str]:
        """Extract integration patterns from relationships."""

        patterns = set()

        for rel in relationships:
            if rel.protocol == "HTTP/REST":
                patterns.add("REST API Integration")
            elif rel.protocol == "Database":
                patterns.add("Database-Mediated Communication")
            elif rel.protocol == "Memory":
                patterns.add("Shared Memory Integration")
            elif rel.relationship_type == "orchestrates":
                patterns.add("Service Orchestration")
            elif rel.relationship_type == "stores_in":
                patterns.add("Data Storage Integration")

        return list(patterns)

    async def generate_mermaid_diagram(self, flow_diagram: EcosystemFlowDiagram) -> str:
        """Generate a Mermaid diagram representation of the ecosystem."""

        mermaid = "graph TD\n"

        # Add project nodes
        for project in flow_diagram.projects:
            node_id = project.project_name.replace(".", "_").replace("-", "_")
            mermaid += f"    {node_id}[{project.project_name}<br/>{project.architecture_type}]\n"

        # Add relationships
        for rel in flow_diagram.relationships:
            source_id = rel.source.replace(".", "_").replace("-", "_")
            target_id = rel.target.replace(".", "_").replace("-", "_")

            if rel.relationship_type == "depends_on":
                arrow = "-->"
            elif rel.relationship_type == "communicates_with":
                arrow = "<-->"
            elif rel.relationship_type == "stores_in":
                arrow = "==>"
            elif rel.relationship_type == "orchestrates":
                arrow = "-..->"
            else:
                arrow = "-->"

            mermaid += f"    {source_id} {arrow} {target_id}\n"

        # Add styling
        mermaid += "\n    classDef microservice fill:#e1f5fe\n"
        mermaid += "    classDef database fill:#f3e5f5\n"
        mermaid += "    classDef orchestrator fill:#fff3e0\n"

        return mermaid

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global analyzer instance
_qwen_analyzer: Optional[QwenProjectAnalyzer] = None


def get_qwen_project_analyzer() -> QwenProjectAnalyzer:
    """Get the global Qwen project analyzer instance."""
    global _qwen_analyzer
    if _qwen_analyzer is None:
        _qwen_analyzer = QwenProjectAnalyzer()
    return _qwen_analyzer
