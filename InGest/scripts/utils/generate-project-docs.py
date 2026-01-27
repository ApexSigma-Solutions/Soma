#!/usr/bin/env python3
"""
Generate Project Documentation Script

This script generates AI-powered project outlines and Mermaid diagrams
and saves them in each project's .md/.projects/ directory.

Usage:
    python generate_project_docs.py [--project PROJECT_NAME] [--all] [--force]
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_llm_as.services.project_documentation_generator import (
    get_project_documentation_generator,
)


class ProjectDocumentationCLI:
    """Command-line interface for project documentation generation."""

    def __init__(self):
        """Initialize the CLI."""
        self.doc_generator = get_project_documentation_generator()
        self.start_time = datetime.now()

    async def run_documentation_generation(
        self, project_name: str = None, generate_all: bool = False, force: bool = False
    ) -> None:
        """Run documentation generation."""

        print("=" * 80)
        print("APEXSIGMA PROJECT DOCUMENTATION GENERATOR")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("AI Model: qwen/qwen3-4b-thinking-2507")
        print()

        try:
            if project_name:
                await self._generate_single_project_docs(project_name, force)
            elif generate_all:
                await self._generate_all_project_docs(force)
            else:
                print("Please specify --project PROJECT_NAME or --all")
                return

            print("\n" + "=" * 80)
            print("DOCUMENTATION GENERATION COMPLETED")
            execution_time = (datetime.now() - self.start_time).total_seconds()
            print(f"Execution time: {execution_time:.1f} seconds")
            print("=" * 80)

        except Exception as e:
            print(f"\nDocumentation generation failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await self.doc_generator.close()

    async def _generate_single_project_docs(
        self, project_name: str, force: bool
    ) -> None:
        """Generate documentation for a single project."""

        print(f"GENERATING DOCUMENTATION FOR: {project_name}")
        print("-" * 50)

        # Check if project exists
        available_projects = ["InGest-LLM.as", "memos.as", "devenviro.as", "tools.as"]
        if project_name not in available_projects:
            print(f"Unknown project: {project_name}")
            print(f"Available projects: {', '.join(available_projects)}")
            return

        # Check if docs already exist
        project_path = self.doc_generator.projects[project_name]
        docs_dir = project_path / ".md" / ".projects"

        if docs_dir.exists() and not force:
            existing_files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.mmd"))
            if existing_files:
                print(f"Documentation already exists in {docs_dir}")
                print("Use --force to regenerate")
                return

        print("Analyzing project with Qwen AI model...")
        print("This may take 1-3 minutes depending on project complexity...")
        print()

        # Generate documentation
        success = await self.doc_generator.generate_single_project_documentation(
            project_name
        )

        if success:
            print("✅ Documentation generated successfully!")
            print(f"📁 Location: {docs_dir}")
            print()
            self._show_generated_files(docs_dir, project_name)
        else:
            print(f"❌ Failed to generate documentation for {project_name}")

    async def _generate_all_project_docs(self, force: bool) -> None:
        """Generate documentation for all projects."""

        print("GENERATING DOCUMENTATION FOR ALL PROJECTS")
        print("-" * 45)

        if not force:
            # Check for existing docs
            existing_projects = []
            for project_name, project_path in self.doc_generator.projects.items():
                docs_dir = project_path / ".md" / ".projects"
                if docs_dir.exists():
                    existing_files = list(docs_dir.glob("*.md")) + list(
                        docs_dir.glob("*.mmd")
                    )
                    if existing_files:
                        existing_projects.append(project_name)

            if existing_projects:
                print(
                    f"Documentation already exists for: {', '.join(existing_projects)}"
                )
                print("Use --force to regenerate all documentation")
                print()

        print("Performing comprehensive ecosystem analysis...")
        print("This may take 3-8 minutes for complete analysis...")
        print()

        # Generate all documentation
        results = await self.doc_generator.generate_all_project_documentation()

        print("GENERATION RESULTS")
        print("-" * 20)

        successful_projects = []
        failed_projects = []

        for project_name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{project_name:<15} | {status}")

            if success:
                successful_projects.append(project_name)
                project_path = self.doc_generator.projects[project_name]
                docs_dir = project_path / ".md" / ".projects"
                print(f"{'':>15}   📁 {docs_dir}")
            else:
                failed_projects.append(project_name)

        print()
        print(
            f"📊 Summary: {len(successful_projects)} successful, {len(failed_projects)} failed"
        )

        if successful_projects:
            print(f"✅ Generated documentation for: {', '.join(successful_projects)}")

        if failed_projects:
            print(f"❌ Failed to generate for: {', '.join(failed_projects)}")

    def _show_generated_files(self, docs_dir: Path, project_name: str) -> None:
        """Show the generated files."""

        project_prefix = project_name.lower().replace(".", "_")

        expected_files = [
            f"{project_prefix}_outline.md",
            f"{project_prefix}_diagram.mmd",
            f"{project_prefix}_data.json",
            "README.md",
            "apexsigma_ecosystem.mmd",
        ]

        print("Generated files:")
        for filename in expected_files:
            file_path = docs_dir / filename
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                print(f"  ✅ {filename:<30} ({size_kb:.1f} KB)")
            else:
                print(f"  ❌ {filename:<30} (missing)")

        print()
        print("Usage:")
        print(f"  📖 View outline: cat '{docs_dir}/{project_prefix}_outline.md'")
        print(
            f"  🎨 View diagram: Copy '{docs_dir}/{project_prefix}_diagram.mmd' to https://mermaid.live"
        )
        print(
            f"  📊 Access data: Load '{docs_dir}/{project_prefix}_data.json' in your application"
        )


async def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Generate AI-powered project documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_project_docs.py --project InGest-LLM.as    # Single project
  python generate_project_docs.py --project memos.as        # Single project
  python generate_project_docs.py --all                     # All projects
  python generate_project_docs.py --all --force             # Regenerate all
        """,
    )

    parser.add_argument(
        "--project",
        metavar="PROJECT_NAME",
        help="Generate documentation for a specific project (InGest-LLM.as, memos.as, devenviro.as, tools.as)",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate documentation for all ApexSigma projects",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if documentation already exists",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.project and not args.all:
        parser.print_help()
        print("\nError: Must specify either --project PROJECT_NAME or --all")
        sys.exit(1)

    if args.project and args.all:
        print("Error: Cannot specify both --project and --all")
        sys.exit(1)

    # Create CLI instance and run
    cli = ProjectDocumentationCLI()

    await cli.run_documentation_generation(
        project_name=args.project, generate_all=args.all, force=args.force
    )


if __name__ == "__main__":
    print("ApexSigma Project Documentation Generator")
    print("Requires: Qwen model running on http://172.22.144.1:12345")
    print()

    asyncio.run(main())
