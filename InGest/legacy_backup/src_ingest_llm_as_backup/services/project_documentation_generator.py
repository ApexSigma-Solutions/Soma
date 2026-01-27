"""
Project Documentation Generator

This service generates and saves project outlines and Mermaid diagrams
in each project's .md/.projects/ directory using the Qwen model.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from .project_analyzer import (
    get_qwen_project_analyzer,
    ProjectOutline,
    ServiceRelationship,
)
from ..observability.logging import get_logger

logger = get_logger(__name__)


class ProjectDocumentationGenerator:
    """
    Generates and saves project documentation using Qwen AI analysis.

    Creates comprehensive project outlines and flow diagrams in each
    project's .md/.projects/ directory for local documentation.
    """

    def __init__(self):
        """Initialize the documentation generator."""
        self.logger = get_logger(__name__)
        self.analyzer = get_qwen_project_analyzer()

        # ApexSigma project paths
        self.base_path = Path("C:\\Users\\steyn\\ApexSigmaProjects.Dev")
        self.projects = {
            "InGest-LLM.as": self.base_path / "InGest-LLM.as",
            "memos.as": self.base_path / "memos.as",
            "devenviro.as": self.base_path / "devenviro.as",
            "tools.as": self.base_path / "tools.as",
        }

    async def generate_all_project_documentation(self) -> Dict[str, bool]:
        """
        Generate documentation for all ApexSigma projects.

        Returns:
            Dict[str, bool]: Success status for each project
        """
        self.logger.info("Starting project documentation generation for all projects")

        results = {}

        # Analyze all projects first to get relationships
        self.logger.info("Performing comprehensive ecosystem analysis...")
        flow_diagram = await self.analyzer.analyze_all_projects()

        # Generate documentation for each project
        for project_name, project_path in self.projects.items():
            if project_path.exists():
                self.logger.info(f"Generating documentation for {project_name}")

                # Find this project's outline
                project_outline = None
                for outline in flow_diagram.projects:
                    if outline.project_name == project_name:
                        project_outline = outline
                        break

                if project_outline:
                    success = await self._generate_project_documentation(
                        project_name,
                        project_path,
                        project_outline,
                        flow_diagram.relationships,
                    )
                    results[project_name] = success
                else:
                    self.logger.warning(f"No outline generated for {project_name}")
                    results[project_name] = False
            else:
                self.logger.warning(f"Project path not found: {project_path}")
                results[project_name] = False

        # Generate ecosystem-wide diagram
        await self._generate_ecosystem_diagram(flow_diagram)

        self.logger.info(f"Documentation generation complete: {results}")
        return results

    async def generate_single_project_documentation(self, project_name: str) -> bool:
        """
        Generate documentation for a single project.

        Args:
            project_name: Name of the project to document

        Returns:
            bool: Success status
        """
        if project_name not in self.projects:
            self.logger.error(f"Unknown project: {project_name}")
            return False

        project_path = self.projects[project_name]
        if not project_path.exists():
            self.logger.error(f"Project path not found: {project_path}")
            return False

        self.logger.info(f"Generating documentation for {project_name}")

        # Analyze the specific project
        project_outline = await self.analyzer._analyze_single_project(
            project_name, project_path
        )

        if not project_outline:
            self.logger.error(f"Failed to analyze {project_name}")
            return False

        # Get ecosystem relationships for context
        flow_diagram = await self.analyzer.analyze_all_projects()

        return await self._generate_project_documentation(
            project_name, project_path, project_outline, flow_diagram.relationships
        )

    async def _generate_project_documentation(
        self,
        project_name: str,
        project_path: Path,
        outline: ProjectOutline,
        relationships: List[ServiceRelationship],
    ) -> bool:
        """Generate documentation files for a single project."""

        try:
            # Create .md/.projects directory
            docs_dir = project_path / ".md" / ".projects"
            docs_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(timezone.utc)

            # Generate project outline markdown
            outline_content = self._create_project_outline_markdown(
                outline, relationships, timestamp
            )
            outline_file = (
                docs_dir / f"{project_name.lower().replace('.', '_')}_outline.md"
            )

            with open(outline_file, "w", encoding="utf-8") as f:
                f.write(outline_content)

            # Generate project-specific Mermaid diagram
            diagram_content = self._create_project_mermaid_diagram(
                outline, relationships
            )
            diagram_file = (
                docs_dir / f"{project_name.lower().replace('.', '_')}_diagram.mmd"
            )

            with open(diagram_file, "w", encoding="utf-8") as f:
                f.write(diagram_content)

            # Generate JSON data file
            json_content = self._create_project_json_data(
                outline, relationships, timestamp
            )
            json_file = docs_dir / f"{project_name.lower().replace('.', '_')}_data.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_content, f, indent=2)

            # Generate README for the documentation
            readme_content = self._create_documentation_readme(project_name, timestamp)
            readme_file = docs_dir / "README.md"

            with open(readme_file, "w", encoding="utf-8") as f:
                f.write(readme_content)

            self.logger.info(f"Documentation generated for {project_name}:")
            self.logger.info(f"  - Outline: {outline_file}")
            self.logger.info(f"  - Diagram: {diagram_file}")
            self.logger.info(f"  - Data: {json_file}")
            self.logger.info(f"  - README: {readme_file}")

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to generate documentation for {project_name}: {e}"
            )
            return False

    def _create_project_outline_markdown(
        self,
        outline: ProjectOutline,
        relationships: List[ServiceRelationship],
        timestamp: datetime,
    ) -> str:
        """Create comprehensive project outline in Markdown format."""

        content = f"""# {outline.project_name} - Project Outline

**Generated by AI Analysis** | **Model**: qwen/qwen3-4b-thinking-2507  
**Timestamp**: {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

## 📋 Project Overview

**Description**: {outline.description}

**Architecture Type**: {outline.architecture_type.title()}

## 🏗️ Core Components

"""

        if outline.core_components:
            for i, component in enumerate(outline.core_components, 1):
                content += f"### {i}. {component.get('name', 'Unknown Component')}\n"
                content += f"**Type**: {component.get('type', 'Unknown')}\n\n"
                content += (
                    f"{component.get('description', 'No description available.')}\n\n"
                )
        else:
            content += "*No core components identified.*\n\n"

        # API Endpoints
        content += "## 🌐 API Endpoints\n\n"
        if outline.api_endpoints:
            content += "| Method | Path | Description |\n"
            content += "|--------|------|-------------|\n"
            for endpoint in outline.api_endpoints:
                method = endpoint.get("method", "GET")
                path = endpoint.get("path", "/unknown")
                desc = endpoint.get("description", "No description")
                content += f"| `{method}` | `{path}` | {desc} |\n"
            content += "\n"
        else:
            content += "*No API endpoints identified.*\n\n"

        # Data Models
        content += "## 📊 Data Models\n\n"
        if outline.data_models:
            for model in outline.data_models:
                content += f"- `{model}`\n"
            content += "\n"
        else:
            content += "*No data models identified.*\n\n"

        # Services
        content += "## 🔧 Services\n\n"
        if outline.services:
            for service in outline.services:
                name = service.get("name", "Unknown Service")
                desc = service.get("description", "No description")
                stype = service.get("type", "unknown")
                content += f"### {name}\n"
                content += f"**Type**: {stype.title()}\n\n"
                content += f"{desc}\n\n"
        else:
            content += "*No services identified.*\n\n"

        # Dependencies
        content += "## 📦 Dependencies\n\n"
        if outline.dependencies:
            for dep in outline.dependencies:
                content += f"- {dep}\n"
            content += "\n"
        else:
            content += "*No external dependencies identified.*\n\n"

        # Key Features
        content += "## ✨ Key Features\n\n"
        if outline.key_features:
            for feature in outline.key_features:
                content += f"- {feature}\n"
            content += "\n"
        else:
            content += "*No key features identified.*\n\n"

        # Integration Points
        content += "## 🔗 Integration Points\n\n"
        if outline.integration_points:
            for integration in outline.integration_points:
                content += f"- {integration}\n"
            content += "\n"
        else:
            content += "*No integration points identified.*\n\n"

        # Service Relationships
        project_relationships = [
            rel
            for rel in relationships
            if rel.source == outline.project_name or rel.target == outline.project_name
        ]

        content += "## 🔄 Service Relationships\n\n"
        if project_relationships:
            content += "### Outgoing Relationships\n"
            outgoing = [
                rel
                for rel in project_relationships
                if rel.source == outline.project_name
            ]
            if outgoing:
                for rel in outgoing:
                    arrow = self._get_relationship_arrow(rel.relationship_type)
                    content += f"- **{rel.target}** {arrow} *{rel.relationship_type}* via {rel.protocol}\n"
                    content += f"  - {rel.description}\n"
                    content += f"  - Data flow: {rel.data_flow}\n\n"
            else:
                content += "*No outgoing relationships.*\n\n"

            content += "### Incoming Relationships\n"
            incoming = [
                rel
                for rel in project_relationships
                if rel.target == outline.project_name
            ]
            if incoming:
                for rel in incoming:
                    arrow = self._get_relationship_arrow(rel.relationship_type)
                    content += f"- **{rel.source}** {arrow} *{rel.relationship_type}* via {rel.protocol}\n"
                    content += f"  - {rel.description}\n"
                    content += f"  - Data flow: {rel.data_flow}\n\n"
            else:
                content += "*No incoming relationships.*\n\n"
        else:
            content += "*No service relationships identified.*\n\n"

        # Footer
        content += "---\n\n"
        content += "*This document was automatically generated using AI analysis of the project structure and codebase.*\n"
        content += "*For the latest version, regenerate using the ApexSigma documentation tools.*\n"

        return content

    def _create_project_mermaid_diagram(
        self, outline: ProjectOutline, relationships: List[ServiceRelationship]
    ) -> str:
        """Create project-specific Mermaid diagram."""

        diagram = f"---\ntitle: {outline.project_name} Architecture\n---\n\n"
        diagram += "graph TD\n"

        # Main project node
        project_id = outline.project_name.replace(".", "_").replace("-", "_")
        diagram += f"    {project_id}[{outline.project_name}<br/>{outline.architecture_type}]\n"

        # Add core components
        if outline.core_components:
            for i, component in enumerate(
                outline.core_components[:5], 1
            ):  # Limit to 5 components
                comp_id = f"{project_id}_comp_{i}"
                comp_name = component.get("name", f"Component{i}")
                comp_type = component.get("type", "component")
                diagram += f"    {comp_id}[{comp_name}<br/>{comp_type}]\n"
                diagram += f"    {project_id} --> {comp_id}\n"

        # Add related services from relationships
        project_relationships = [
            rel
            for rel in relationships
            if rel.source == outline.project_name or rel.target == outline.project_name
        ]

        related_services = set()
        for rel in project_relationships:
            if rel.source != outline.project_name:
                related_services.add(rel.source)
            if rel.target != outline.project_name:
                related_services.add(rel.target)

        # Add related service nodes
        for service in related_services:
            service_id = service.replace(".", "_").replace("-", "_")
            diagram += f"    {service_id}[{service}]\n"

        # Add relationship arrows
        for rel in project_relationships:
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

            diagram += f"    {source_id} {arrow} {target_id}\n"

        # Add styling
        diagram += (
            "\n    classDef projectNode fill:#e3f2fd,stroke:#1976d2,stroke-width:3px\n"
        )
        diagram += "    classDef componentNode fill:#f3e5f5,stroke:#7b1fa2\n"
        diagram += "    classDef serviceNode fill:#e8f5e8,stroke:#388e3c\n"
        diagram += f"\n    class {project_id} projectNode\n"

        if outline.core_components:
            comp_ids = [
                f"{project_id}_comp_{i}"
                for i in range(1, min(6, len(outline.core_components) + 1))
            ]
            diagram += f"    class {','.join(comp_ids)} componentNode\n"

        if related_services:
            service_ids = [
                service.replace(".", "_").replace("-", "_")
                for service in related_services
            ]
            diagram += f"    class {','.join(service_ids)} serviceNode\n"

        return diagram

    def _create_project_json_data(
        self,
        outline: ProjectOutline,
        relationships: List[ServiceRelationship],
        timestamp: datetime,
    ) -> Dict[str, Any]:
        """Create structured JSON data for the project."""

        project_relationships = [
            {
                "source": rel.source,
                "target": rel.target,
                "relationship_type": rel.relationship_type,
                "protocol": rel.protocol,
                "description": rel.description,
                "data_flow": rel.data_flow,
            }
            for rel in relationships
            if rel.source == outline.project_name or rel.target == outline.project_name
        ]

        return {
            "project_name": outline.project_name,
            "generated_at": timestamp.isoformat(),
            "analysis_model": "qwen/qwen3-4b-thinking-2507",
            "project_data": {
                "description": outline.description,
                "architecture_type": outline.architecture_type,
                "core_components": outline.core_components,
                "api_endpoints": outline.api_endpoints,
                "data_models": outline.data_models,
                "services": outline.services,
                "dependencies": outline.dependencies,
                "key_features": outline.key_features,
                "integration_points": outline.integration_points,
            },
            "relationships": project_relationships,
            "metadata": {
                "total_components": len(outline.core_components),
                "total_endpoints": len(outline.api_endpoints),
                "total_dependencies": len(outline.dependencies),
                "total_relationships": len(project_relationships),
            },
        }

    def _create_documentation_readme(
        self, project_name: str, timestamp: datetime
    ) -> str:
        """Create README for the project documentation directory."""

        content = f"""# {project_name} - Project Documentation

This directory contains automatically generated documentation for the {project_name} project.

## 📁 Files

### `{project_name.lower().replace(".", "_")}_outline.md`
Comprehensive project outline with:
- Project overview and architecture type
- Core components and services
- API endpoints and data models
- Dependencies and integrations
- Service relationships

### `{project_name.lower().replace(".", "_")}_diagram.mmd`
Mermaid diagram showing:
- Project architecture
- Core components
- Related services
- Relationship flows

### `{project_name.lower().replace(".", "_")}_data.json`
Structured JSON data containing:
- Complete project analysis
- Relationship mappings
- Metadata and statistics

## 🤖 Generation Info

**Generated**: {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}  
**Model**: qwen/qwen3-4b-thinking-2507  
**Source**: AI analysis of project structure and codebase  

## 🔄 Updating Documentation

To regenerate this documentation:

```bash
# From InGest-LLM.as directory
python scripts/generate_project_docs.py --project {project_name}

# Or generate for all projects
python scripts/generate_project_docs.py --all
```

## 📊 Using the Documentation

### Viewing the Diagram
```bash
# Copy the .mmd file content to https://mermaid.live
# Or use a Mermaid plugin in your editor
```

### Accessing the Data
```python
import json

with open('{project_name.lower().replace(".", "_")}_data.json', 'r') as f:
    project_data = json.load(f)

print(project_data['project_data']['description'])
```

---

*Part of the ApexSigma ecosystem documentation system*
"""

        return content

    async def _generate_ecosystem_diagram(self, flow_diagram) -> None:
        """Generate ecosystem-wide diagram in each project."""

        try:
            ecosystem_mermaid = await self.analyzer.generate_mermaid_diagram(
                flow_diagram
            )

            for project_name, project_path in self.projects.items():
                if project_path.exists():
                    docs_dir = project_path / ".md" / ".projects"
                    docs_dir.mkdir(parents=True, exist_ok=True)

                    ecosystem_file = docs_dir / "apexsigma_ecosystem.mmd"
                    with open(ecosystem_file, "w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write("title: ApexSigma Ecosystem Architecture\n")
                        f.write("---\n\n")
                        f.write(ecosystem_mermaid)

                    self.logger.info(f"Ecosystem diagram saved to {ecosystem_file}")

        except Exception as e:
            self.logger.error(f"Failed to generate ecosystem diagram: {e}")

    def _get_relationship_arrow(self, rel_type: str) -> str:
        """Get arrow representation for relationship type."""
        arrows = {
            "depends_on": "→",
            "communicates_with": "↔",
            "stores_in": "⇒",
            "orchestrates": "⇝",
        }
        return arrows.get(rel_type, "→")

    async def close(self):
        """Close the analyzer client."""
        await self.analyzer.close()


# Global documentation generator instance
_doc_generator: Optional[ProjectDocumentationGenerator] = None


def get_project_documentation_generator() -> ProjectDocumentationGenerator:
    """Get the global project documentation generator instance."""
    global _doc_generator
    if _doc_generator is None:
        _doc_generator = ProjectDocumentationGenerator()
    return _doc_generator
