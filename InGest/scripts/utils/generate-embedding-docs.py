#!/usr/bin/env python3
"""
Generate Project Documentation using Nomic Embeddings

This script uses nomic-embed-code-i1 to analyze code similarity
and generate documentation for ApexSigma projects.
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ingest_llm_as.services.nomic_code_analyzer import get_nomic_code_analyzer

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class EmbeddingDocumentationCLI:
    """Command-line interface for embedding-based documentation generation."""

    def __init__(self):
        """Initialize the CLI."""
        if DEPENDENCIES_AVAILABLE:
            self.analyzer = get_nomic_code_analyzer()
        else:
            self.analyzer = None
        self.start_time = datetime.now()

    async def run_documentation_generation(
        self,
        project_name: str = None,
        generate_all: bool = False,
        output_dir: str = None,
    ) -> None:
        """Run embedding-based documentation generation."""

        print("=" * 80)
        print("APEXSIGMA EMBEDDING-BASED DOCUMENTATION GENERATOR")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Model: nomic-embed-code-i1 (Code Embeddings)")
        print()

        if not DEPENDENCIES_AVAILABLE:
            print("⚠️  Dependencies not installed. Running simplified analysis...")
            await self._run_simplified_analysis(project_name, generate_all)
            return

        try:
            if project_name:
                await self._analyze_single_project(project_name, output_dir)
            elif generate_all:
                await self._analyze_all_projects(output_dir)
            else:
                print("Please specify --project PROJECT_NAME or --all")
                return

            print("\\n" + "=" * 80)
            print("EMBEDDING ANALYSIS COMPLETED")
            execution_time = (datetime.now() - self.start_time).total_seconds()
            print(f"Execution time: {execution_time:.1f} seconds")
            print("=" * 80)

        except Exception as e:
            print(f"\\nAnalysis failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if self.analyzer:
                await self.analyzer.close()

    async def _analyze_single_project(self, project_name: str, output_dir: str) -> None:
        """Analyze a single project using embeddings."""

        print(f"ANALYZING PROJECT: {project_name}")
        print("-" * 50)

        # Check if project exists
        available_projects = ["InGest-LLM.as", "memos.as", "devenviro.as", "tools.as"]
        if project_name not in available_projects:
            print(f"Unknown project: {project_name}")
            print(f"Available projects: {', '.join(available_projects)}")
            return

        print("Generating code embeddings...")
        print("This may take 1-2 minutes depending on project size...")
        print()

        # Analyze the project
        analyses = await self.analyzer.analyze_all_projects()

        if project_name in analyses:
            analysis = analyses[project_name]
            await self._save_project_analysis(
                project_name, analysis, analyses, output_dir
            )
            print(f"✓ Analysis completed for {project_name}")
        else:
            print(f"✗ Failed to analyze {project_name}")

    async def _analyze_all_projects(self, output_dir: str) -> None:
        """Analyze all projects using embeddings."""

        print("ANALYZING ALL APEXSIGMA PROJECTS")
        print("-" * 40)

        print("Performing comprehensive embedding analysis...")
        print("This may take 3-5 minutes for all projects...")
        print()

        # Analyze all projects
        analyses = await self.analyzer.analyze_all_projects()

        print("ANALYSIS RESULTS")
        print("-" * 20)

        for project_name, analysis in analyses.items():
            print(f"{project_name:<15} | ✓ Success")
            await self._save_project_analysis(
                project_name, analysis, analyses, output_dir
            )

        # Generate ecosystem report
        ecosystem_report = await self.analyzer.generate_embedding_analysis_report(
            analyses
        )
        await self._save_ecosystem_report(ecosystem_report, output_dir)

        print()
        print(f"📊 Summary: {len(analyses)} projects analyzed")
        print(f"✓ Generated documentation for: {', '.join(analyses.keys())}")

    async def _save_project_analysis(
        self, project_name: str, analysis, all_analyses: dict, output_dir: str
    ) -> None:
        """Save project analysis to markdown and JSON files."""

        # Determine output directory
        if output_dir:
            docs_dir = Path(output_dir)
        else:
            project_path = (
                Path("C:\\Users\\steyn\\ApexSigmaProjects.Dev") / project_name
            )
            docs_dir = project_path / ".md" / ".projects"

        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create markdown report
        markdown_content = self._create_embedding_markdown(
            project_name, analysis, all_analyses
        )
        markdown_file = (
            docs_dir / f"{project_name.lower().replace('.', '_')}_embeddings.md"
        )

        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Create JSON data
        json_data = {
            "project_name": project_name,
            "generated_at": datetime.now().isoformat(),
            "analysis_method": "nomic-embed-code-i1",
            "analysis": {
                "description": analysis.description,
                "architecture_type": analysis.architecture_type,
                "core_components": analysis.core_components,
                "api_patterns": analysis.api_patterns,
                "dependencies": analysis.dependencies,
                "similarity_scores": analysis.similarity_scores,
            },
        }

        json_file = (
            docs_dir / f"{project_name.lower().replace('.', '_')}_embeddings.json"
        )
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        print(f"  📁 Documentation saved to: {docs_dir}")
        print(f"      - {markdown_file.name}")
        print(f"      - {json_file.name}")

    def _create_embedding_markdown(
        self, project_name: str, analysis, all_analyses: dict
    ) -> str:
        """Create markdown documentation from embedding analysis."""

        content = f"""# {project_name} - Code Embedding Analysis

**Generated by Embedding Analysis** | **Model**: nomic-embed-code-i1  
**Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📋 Project Overview

**Description**: {analysis.description}

**Architecture Type**: {analysis.architecture_type.title()}

## 🏗️ Core Components

"""

        if analysis.core_components:
            for i, component in enumerate(analysis.core_components, 1):
                content += f"### {i}. {component.get('name', 'Unknown Component')}\\n"
                content += f"**Type**: {component.get('type', 'Unknown')}\\n\\n"
                content += (
                    f"{component.get('description', 'No description available.')}\\n\\n"
                )
        else:
            content += "*No core components identified.*\\n\\n"

        # API Patterns
        content += "## 🌐 API Patterns\\n\\n"
        if analysis.api_patterns:
            for pattern in analysis.api_patterns:
                content += f"- {pattern}\\n"
            content += "\\n"
        else:
            content += "*No API patterns detected.*\\n\\n"

        # Dependencies
        content += "## 📦 Dependencies\\n\\n"
        if analysis.dependencies:
            for dep in analysis.dependencies:
                content += f"- {dep}\\n"
            content += "\\n"
        else:
            content += "*No dependencies identified.*\\n\\n"

        # Similarity Analysis
        content += "## 🔗 Project Similarity Analysis\\n\\n"
        if analysis.similarity_scores:
            content += "Based on code embedding similarity:\\n\\n"

            # Sort by similarity score
            sorted_similarities = sorted(
                analysis.similarity_scores.items(), key=lambda x: x[1], reverse=True
            )

            content += "| Project | Similarity Score | Relationship |\\n"
            content += "|---------|------------------|--------------|\\n"

            for other_project, score in sorted_similarities:
                if score > 0.8:
                    relationship = "Very Similar"
                elif score > 0.6:
                    relationship = "Similar"
                elif score > 0.4:
                    relationship = "Somewhat Similar"
                else:
                    relationship = "Different"

                content += f"| {other_project} | {score:.3f} | {relationship} |\\n"

            content += "\\n"

            # Insights
            if sorted_similarities:
                most_similar = sorted_similarities[0]
                content += f"**Key Insight**: {project_name} is most similar to **{most_similar[0]}** "
                content += f"with a similarity score of {most_similar[1]:.3f}.\\n\\n"
        else:
            content += "*No similarity analysis available.*\\n\\n"

        # Architecture Insights
        content += "## 🏛️ Architecture Insights\\n\\n"

        if analysis.architecture_type == "microservice":
            content += "- **Microservice Architecture**: This project follows microservice patterns with API endpoints and modular design.\\n"
        elif analysis.architecture_type == "monolith":
            content += "- **Monolithic Architecture**: This project contains multiple components in a single codebase.\\n"
        elif analysis.architecture_type == "library":
            content += "- **Library Architecture**: This project provides reusable functionality as a library.\\n"
        else:
            content += "- **Tool Architecture**: This project appears to be a development tool or utility.\\n"

        if "REST API" in analysis.api_patterns:
            content += "- **REST API Integration**: The project implements REST API patterns for external communication.\\n"

        if "Object-Oriented Design" in analysis.api_patterns:
            content += "- **Object-Oriented Design**: The codebase uses class-based design patterns.\\n"

        content += "\\n"

        # Footer
        content += "---\\n\\n"
        content += "*This document was automatically generated using code embedding analysis.*\\n"
        content += "*The analysis is based on semantic similarity of code structures and patterns.*\\n"

        return content

    async def _save_ecosystem_report(self, report: str, output_dir: str) -> None:
        """Save ecosystem-wide analysis report."""

        if output_dir:
            base_dir = Path(output_dir)
        else:
            base_dir = Path(
                "C:\\Users\\steyn\\ApexSigmaProjects.Dev\\InGest-LLM.as\\.md\\.projects"
            )

        base_dir.mkdir(parents=True, exist_ok=True)

        report_file = base_dir / "apexsigma_ecosystem_embeddings.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  📄 Ecosystem report saved to: {report_file}")

    async def _run_simplified_analysis(
        self, project_name: str, generate_all: bool
    ) -> None:
        """Run simplified analysis without dependencies."""

        print("SIMPLIFIED EMBEDDING ANALYSIS")
        print("-" * 35)

        projects = {
            "InGest-LLM.as": "Data ingestion microservice with FastAPI and repository processing",
            "memos.as": "Memory Operating System with multi-tiered storage and knowledge graphs",
            "devenviro.as": "Agent orchestrator with task assignment and workflow management",
            "tools.as": "Development tooling suite with CLI automation and build systems",
        }

        if project_name:
            if project_name in projects:
                print(f"Project: {project_name}")
                print(f"Description: {projects[project_name]}")
                print()
                print("📋 To get full embedding analysis:")
                print("1. Install dependencies: poetry install")
                print("2. Ensure LM Studio is running with nomic-embed-code-i1")
                print("3. Re-run this script")
            else:
                print(f"Unknown project: {project_name}")
        elif generate_all:
            print("ApexSigma Projects Overview:")
            for proj, desc in projects.items():
                print(f"  {proj}: {desc}")

            print()
            print("📋 To get full embedding analysis for all projects:")
            print("1. Install dependencies: poetry install")
            print("2. Ensure LM Studio is running with nomic-embed-code-i1")
            print("3. Re-run with --all flag")


async def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Generate embedding-based project documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_embedding_docs.py --project InGest-LLM.as    # Single project
  python generate_embedding_docs.py --all                     # All projects
  python generate_embedding_docs.py --all --output ./docs     # Custom output
        """,
    )

    parser.add_argument(
        "--project",
        metavar="PROJECT_NAME",
        help="Generate documentation for a specific project",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate documentation for all ApexSigma projects",
    )

    parser.add_argument(
        "--output",
        metavar="OUTPUT_DIR",
        help="Custom output directory (default: project/.md/.projects/)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.project and not args.all:
        parser.print_help()
        print("\\nError: Must specify either --project PROJECT_NAME or --all")
        sys.exit(1)

    if args.project and args.all:
        print("Error: Cannot specify both --project and --all")
        sys.exit(1)

    # Create CLI instance and run
    cli = EmbeddingDocumentationCLI()

    await cli.run_documentation_generation(
        project_name=args.project, generate_all=args.all, output_dir=args.output
    )


if __name__ == "__main__":
    print("ApexSigma Embedding-Based Documentation Generator")
    print("Requires: nomic-embed-code-i1 running on http://172.22.144.1:12345")
    print()

    asyncio.run(main())
