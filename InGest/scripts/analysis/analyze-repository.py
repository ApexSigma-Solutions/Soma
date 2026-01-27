#!/usr/bin/env python3
"""
Repository self-analysis script for InGest-LLM.as
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ingest_llm_as.services.repository_processor import get_repository_processor
from ingest_llm_as.models import (
    RepositoryIngestionRequest,
    RepositorySource,
    IngestionMetadata,
)


async def analyze_current_repository():
    """Analyze the current InGest-LLM.as repository."""

    print("=" * 60)
    print("INGEST-LLM.AS REPOSITORY ANALYSIS REPORT")
    print("=" * 60)
    print()

    # Get repository processor
    processor = get_repository_processor()

    # Create analysis request
    request = RepositoryIngestionRequest(
        repository_source=RepositorySource.LOCAL_PATH,
        source_path=".",
        metadata=IngestionMetadata(
            source="self_analysis",
            tags=["ingest_llm_as", "self_report", "repository_analysis"],
            custom_fields={"analysis_type": "self_repository_report"},
        ),
        include_patterns=[
            "**/*.py",
            "**/*.md",
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.json",
            "**/*.txt",
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
        ],
        max_files=200,
        max_file_size=1_000_000,  # 1MB limit
        process_async=False,
    )

    print("🔍 Starting repository analysis...")
    print(f"📂 Repository Path: {Path.cwd()}")
    print()

    try:
        # Execute analysis
        response = await processor.process_repository(request)

        # Display results
        print("📊 ANALYSIS RESULTS")
        print("-" * 30)
        print(f"Status: {response.status.value}")
        print(f"Ingestion ID: {response.ingestion_id}")
        print(f"Repository: {response.repository_path}")
        print()

        print("📈 DISCOVERY METRICS")
        print("-" * 30)
        print(f"Files Discovered: {response.files_discovered}")
        print(f"Files Processed: {len(response.files_processed)}")
        print(f"Discovery Time: {response.discovery_time_ms}ms")
        print(f"Processing Time: {response.processing_time_ms}ms")
        print(f"Total Time: {response.total_time_ms}ms")
        print()

        if response.processing_summary:
            summary = response.processing_summary

            print("🔬 PROCESSING SUMMARY")
            print("-" * 30)
            print(f"Elements Extracted: {summary.total_elements_extracted}")
            print(f"Chunks Created: {summary.total_chunks_created}")
            print(f"Embeddings Generated: {summary.total_embeddings_generated}")
            print(f"Average Complexity: {summary.average_complexity:.2f}")
            print(
                f"Processing Efficiency: {summary.total_elements_extracted / max(1, response.processing_time_ms) * 1000:.1f} elements/sec"
            )
            print()

            print("📁 FILE TYPE DISTRIBUTION")
            print("-" * 30)
            for file_type, count in sorted(summary.file_type_distribution.items()):
                print(f"{file_type:>10}: {count:>3} files")
            print()

            if summary.largest_files:
                print("📏 LARGEST FILES")
                print("-" * 30)
                for i, file_info in enumerate(summary.largest_files[:10], 1):
                    size_kb = file_info["size"] / 1024
                    print(f"{i:>2}. {file_info['path']:<40} ({size_kb:>6.1f} KB)")
                print()

            if summary.most_complex_files:
                print("🧮 MOST COMPLEX FILES")
                print("-" * 30)
                for i, file_info in enumerate(summary.most_complex_files[:10], 1):
                    print(
                        f"{i:>2}. {file_info['path']:<40} (complexity: {file_info['complexity']:>5.2f})"
                    )
                print()

            if summary.processing_errors:
                print("⚠️  PROCESSING ERRORS")
                print("-" * 30)
                for i, error in enumerate(summary.processing_errors[:5], 1):
                    print(f"{i}. {error}")
                print()

        # Display file processing details
        successful_files = [
            f for f in response.files_processed if f.status.value == "completed"
        ]
        failed_files = [
            f for f in response.files_processed if f.status.value == "failed"
        ]

        print("✅ PROCESSING SUCCESS BREAKDOWN")
        print("-" * 30)
        print(f"Successful Files: {len(successful_files)}")
        print(f"Failed Files: {len(failed_files)}")
        if len(response.files_processed) > 0:
            success_rate = len(successful_files) / len(response.files_processed) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        print()

        # Show Python-specific metrics
        python_files = [f for f in successful_files if f.relative_path.endswith(".py")]
        if python_files:
            total_elements = sum(f.elements_extracted for f in python_files)
            total_chunks = sum(f.chunks_created for f in python_files)
            avg_complexity = sum(
                f.complexity_score for f in python_files if f.complexity_score
            ) / len([f for f in python_files if f.complexity_score])

            print("🐍 PYTHON CODE ANALYSIS")
            print("-" * 30)
            print(f"Python Files: {len(python_files)}")
            print(f"Code Elements: {total_elements}")
            print(f"Code Chunks: {total_chunks}")
            print(f"Average Complexity: {avg_complexity:.2f}")
            print(f"Elements per File: {total_elements / len(python_files):.1f}")
            print()

        print("📝 REPOSITORY INSIGHTS")
        print("-" * 30)

        # Calculate some insights
        total_size = sum(f.file_size for f in successful_files)
        print(f"Total Code Size: {total_size / 1024:.1f} KB")

        if python_files:
            print(f"Average File Size: {total_size / len(python_files) / 1024:.1f} KB")

        # Check for test coverage
        test_files = [f for f in successful_files if "test" in f.relative_path.lower()]
        if python_files:
            test_coverage = len(test_files) / len(python_files) * 100
            print(
                f"Test File Ratio: {len(test_files)}/{len(python_files)} ({test_coverage:.1f}%)"
            )

        print()
        print("🎯 RECOMMENDATIONS")
        print("-" * 30)

        if summary and summary.average_complexity > 5:
            print("• Consider refactoring high-complexity functions")

        if len(python_files) > 20:
            print("• Consider organizing code into more packages/modules")

        if test_coverage < 50:
            print("• Consider adding more test coverage")

        if any(f.file_size > 50000 for f in successful_files):
            print("• Consider splitting large files into smaller modules")

        print("• Repository analysis completed successfully!")
        print()

        print("=" * 60)
        print(f"Report generated for ingestion ID: {response.ingestion_id}")
        print("All data has been stored in memOS for future reference.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_current_repository())
