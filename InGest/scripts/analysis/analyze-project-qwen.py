#!/usr/bin/env python3
"""
Qwen Project Analysis Script

This script demonstrates using the local Qwen model to analyze ApexSigma projects
and generate comprehensive outlines and flow diagrams.

Usage:
    python qwen_project_analysis.py [--single PROJECT_NAME] [--diagram-only] [--save-output]
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_llm_as.services.project_analyzer import get_qwen_project_analyzer


class QwenAnalysisDemo:
    """Demonstration of Qwen-powered project analysis."""

    def __init__(self):
        """Initialize the demo."""
        self.analyzer = get_qwen_project_analyzer()
        self.start_time = datetime.now()

    async def run_full_analysis(self, save_output: bool = False) -> None:
        """Run comprehensive analysis of all projects."""

        print("=" * 80)
        print("APEXSIGMA PROJECT ANALYSIS - QWEN MODEL")
        print("=" * 80)
        print("Model: qwen/qwen3-4b-thinking-2507")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        try:
            print("CHECKING PROJECT AVAILABILITY")
            print("-" * 35)

            available_projects = []
            for project_name, project_path in self.analyzer.projects.items():
                exists = project_path.exists()
                status = "Available" if exists else "Not found"
                print(f"  {project_name:<15} | {status}")
                if exists:
                    available_projects.append(project_name)

            print(
                f"\nFound {len(available_projects)}/{len(self.analyzer.projects)} projects"
            )

            if len(available_projects) == 0:
                print(
                    "No projects found. Ensure ApexSigmaProjects.Dev directory exists."
                )
                return

            print("\nANALYZING PROJECTS WITH QWEN MODEL")
            print("-" * 40)
            print("This may take 2-5 minutes depending on project complexity...")
            print()

            # Perform comprehensive analysis
            flow_diagram = await self.analyzer.analyze_all_projects()

            # Display results
            await self._display_project_outlines(flow_diagram.projects)
            await self._display_relationships(flow_diagram.relationships)
            await self._display_architecture_summary(flow_diagram.architecture_summary)
            await self._display_mermaid_diagram(flow_diagram)

            # Save output if requested
            if save_output:
                await self._save_analysis_output(flow_diagram)

            print("\n" + "=" * 80)
            print("QWEN ANALYSIS COMPLETED SUCCESSFULLY")
            execution_time = (datetime.now() - self.start_time).total_seconds()
            print(f"Execution time: {execution_time:.1f} seconds")
            print("=" * 80)

        except Exception as e:
            print(f"\nAnalysis failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await self.analyzer.close()

    async def run_single_project_analysis(self, project_name: str) -> None:
        """Analyze a single project."""

        print("=" * 80)
        print(f"SINGLE PROJECT ANALYSIS: {project_name}")
        print("=" * 80)
        print("Model: qwen/qwen3-4b-thinking-2507")
        print()

        try:
            if project_name not in self.analyzer.projects:
                print(f"Project '{project_name}' not found.")
                print(f"Available projects: {', '.join(self.analyzer.projects.keys())}")
                return

            project_path = self.analyzer.projects[project_name]
            if not project_path.exists():
                print(f"Project directory not found: {project_path}")
                return

            print(f"Analyzing {project_name}...")
            print("This may take 1-2 minutes...")
            print()

            # Analyze single project
            outline = await self.analyzer._analyze_single_project(
                project_name, project_path
            )

            if outline:
                await self._display_single_project_outline(outline)
            else:
                print("Failed to analyze project.")

        except Exception as e:
            print(f"Single project analysis failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await self.analyzer.close()

    async def run_diagram_only(self) -> None:
        """Generate only the flow diagram."""

        print("=" * 80)
        print("APEXSIGMA ECOSYSTEM FLOW DIAGRAM")
        print("=" * 80)
        print()

        try:
            flow_diagram = await self.analyzer.analyze_all_projects()
            await self._display_mermaid_diagram(flow_diagram)

        except Exception as e:
            print(f"Diagram generation failed: {e}")
        finally:
            await self.analyzer.close()

    async def _display_project_outlines(self, projects) -> None:
        """Display project outlines."""

        print("PROJECT OUTLINES")
        print("-" * 20)

        for project in projects:
            print(f"\n{project.project_name}")
            print("=" * len(project.project_name))
            print(f"Type: {project.architecture_type}")
            print(f"Description: {project.description}")

            if project.core_components:
                print("\nCore Components:")
                for comp in project.core_components[:5]:  # Limit display
                    print(
                        f"  • {comp.get('name', 'Unknown')}: {comp.get('description', 'No description')}"
                    )

            if project.api_endpoints:
                print("\nAPI Endpoints:")
                for endpoint in project.api_endpoints[:5]:  # Limit display
                    method = endpoint.get("method", "GET")
                    path = endpoint.get("path", "/unknown")
                    desc = endpoint.get("description", "No description")
                    print(f"  • {method} {path}: {desc}")

            if project.key_features:
                print("\nKey Features:")
                for feature in project.key_features[:5]:
                    print(f"  • {feature}")

            if project.dependencies:
                print(f"\nDependencies: {', '.join(project.dependencies[:5])}")

    async def _display_relationships(self, relationships) -> None:
        """Display project relationships."""

        print("\n\nPROJECT RELATIONSHIPS")
        print("-" * 25)

        if not relationships:
            print("No relationships identified.")
            return

        for rel in relationships:
            arrow = self._get_relationship_arrow(rel.relationship_type)
            print(f"\n{rel.source} {arrow} {rel.target}")
            print(f"  Type: {rel.relationship_type}")
            print(f"  Protocol: {rel.protocol}")
            print(f"  Data Flow: {rel.data_flow}")
            print(f"  Description: {rel.description}")

    def _get_relationship_arrow(self, rel_type: str) -> str:
        """Get arrow representation for relationship type."""
        arrows = {
            "depends_on": "→",
            "communicates_with": "↔",
            "stores_in": "⇒",
            "orchestrates": "⇝",
        }
        return arrows.get(rel_type, "→")

    async def _display_architecture_summary(self, summary: str) -> None:
        """Display architecture summary."""

        print("\n\nARCHITECTURE SUMMARY")
        print("-" * 25)

        if summary:
            # Format the summary for better readability
            paragraphs = summary.split("\n\n")
            for paragraph in paragraphs:
                if paragraph.strip():
                    print(f"\n{paragraph.strip()}")
        else:
            print("No architecture summary generated.")

    async def _display_mermaid_diagram(self, flow_diagram) -> None:
        """Display Mermaid diagram."""

        print("\n\nMERMAID FLOW DIAGRAM")
        print("-" * 25)

        try:
            mermaid_code = await self.analyzer.generate_mermaid_diagram(flow_diagram)

            print("\nGenerated Mermaid diagram code:")
            print("```mermaid")
            print(mermaid_code)
            print("```")

            print("\nTo visualize this diagram:")
            print("1. Copy the code above")
            print("2. Paste it into https://mermaid.live")
            print("3. Or use a Mermaid plugin in your editor")

        except Exception as e:
            print(f"Failed to generate Mermaid diagram: {e}")

    async def _display_single_project_outline(self, outline) -> None:
        """Display outline for a single project."""

        print(f"PROJECT: {outline.project_name}")
        print("=" * (9 + len(outline.project_name)))

        print(f"\nArchitecture Type: {outline.architecture_type}")
        print(f"Description: {outline.description}")

        sections = [
            ("Core Components", outline.core_components),
            ("API Endpoints", outline.api_endpoints),
            ("Data Models", [{"name": model} for model in outline.data_models]),
            ("Services", outline.services),
            ("Key Features", [{"name": feature} for feature in outline.key_features]),
            ("Dependencies", [{"name": dep} for dep in outline.dependencies]),
        ]

        for section_name, items in sections:
            if items:
                print(f"\n{section_name}:")
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("method", "Unknown"))
                        desc = item.get("description", item.get("path", ""))
                        if desc:
                            print(f"  • {name}: {desc}")
                        else:
                            print(f"  • {name}")
                    else:
                        print(f"  • {item}")

    async def _save_analysis_output(self, flow_diagram) -> None:
        """Save analysis output to files."""

        try:
            output_dir = Path("analysis_output")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save complete analysis as JSON
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "projects": [
                    {
                        "project_name": p.project_name,
                        "description": p.description,
                        "architecture_type": p.architecture_type,
                        "core_components": p.core_components,
                        "api_endpoints": p.api_endpoints,
                        "data_models": p.data_models,
                        "services": p.services,
                        "dependencies": p.dependencies,
                        "key_features": p.key_features,
                        "integration_points": p.integration_points,
                    }
                    for p in flow_diagram.projects
                ],
                "relationships": [
                    {
                        "source": r.source,
                        "target": r.target,
                        "relationship_type": r.relationship_type,
                        "protocol": r.protocol,
                        "description": r.description,
                        "data_flow": r.data_flow,
                    }
                    for r in flow_diagram.relationships
                ],
                "architecture_summary": flow_diagram.architecture_summary,
                "integration_patterns": flow_diagram.integration_patterns,
            }

            json_file = output_dir / f"ecosystem_analysis_{timestamp}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(analysis_data, f, indent=2)

            # Save Mermaid diagram
            mermaid_code = await self.analyzer.generate_mermaid_diagram(flow_diagram)
            mermaid_file = output_dir / f"ecosystem_diagram_{timestamp}.mmd"
            with open(mermaid_file, "w", encoding="utf-8") as f:
                f.write(mermaid_code)

            print("\n\nOUTPUT SAVED")
            print("-" * 15)
            print(f"JSON Analysis: {json_file}")
            print(f"Mermaid Diagram: {mermaid_file}")

        except Exception as e:
            print(f"Failed to save output: {e}")


async def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Qwen-powered ApexSigma project analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qwen_project_analysis.py                         # Full ecosystem analysis
  python qwen_project_analysis.py --single InGest-LLM.as # Single project analysis
  python qwen_project_analysis.py --diagram-only         # Generate diagram only
  python qwen_project_analysis.py --save-output          # Save results to files
        """,
    )

    parser.add_argument(
        "--single", metavar="PROJECT_NAME", help="Analyze only a single project"
    )

    parser.add_argument(
        "--diagram-only", action="store_true", help="Generate only the flow diagram"
    )

    parser.add_argument(
        "--save-output", action="store_true", help="Save analysis output to files"
    )

    args = parser.parse_args()

    # Create demo instance
    demo = QwenAnalysisDemo()

    # Run appropriate analysis
    if args.single:
        await demo.run_single_project_analysis(args.single)
    elif args.diagram_only:
        await demo.run_diagram_only()
    else:
        await demo.run_full_analysis(args.save_output)


if __name__ == "__main__":
    # Check if Qwen model is accessible
    print("Qwen Project Analysis Tool")
    print("Requires: qwen/qwen3-4b-thinking-2507 running on http://localhost:1234")
    print()

    asyncio.run(main())
