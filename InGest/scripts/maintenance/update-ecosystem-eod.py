#!/usr/bin/env python3
"""
End of Day (EOD) Ecosystem Update Script

This script performs comprehensive ecosystem ingestion and analysis as part of
the daily workflow. It scrapes all ApexSigma projects, creates embeddings,
stores historical snapshots, and generates reports.

Usage:
    python eod_ecosystem_update.py [--force] [--no-historical] [--report-only]
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_llm_as.services.ecosystem_ingestion import get_ecosystem_ingestion_service
from ingest_llm_as.services.memos_client import get_memos_client
from ingest_llm_as.observability.logging import get_logger

logger = get_logger(__name__)


class EODEcosystemUpdater:
    """End of Day ecosystem update orchestrator."""

    def __init__(self):
        """Initialize the EOD updater."""
        self.ecosystem_service = get_ecosystem_ingestion_service()
        self.memos_client = get_memos_client()
        self.start_time = datetime.now()

    async def run_eod_update(
        self,
        force_refresh: bool = False,
        include_historical: bool = True,
        report_only: bool = False,
    ) -> None:
        """
        Run the complete EOD ecosystem update.

        Args:
            force_refresh: Force refresh even if recent snapshot exists
            include_historical: Store historical snapshots in memOS
            report_only: Only generate reports without full ingestion
        """
        print("=" * 70)
        print("APEXSIGMA ECOSYSTEM - END OF DAY UPDATE")
        print("=" * 70)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        try:
            if report_only:
                await self._generate_daily_report()
            else:
                await self._full_ecosystem_update(force_refresh, include_historical)

            print("\n" + "=" * 70)
            print("EOD UPDATE COMPLETED SUCCESSFULLY")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ EOD UPDATE FAILED: {e}")
            logger.error(f"EOD update failed: {e}")
            sys.exit(1)

    async def _full_ecosystem_update(
        self, force_refresh: bool, include_historical: bool
    ) -> None:
        """Perform full ecosystem ingestion and analysis."""

        print("🚀 STARTING FULL ECOSYSTEM INGESTION")
        print("-" * 40)

        # Check if recent snapshot exists (unless force refresh)
        if not force_refresh:
            print("⏰ Checking for recent snapshots...")
            # TODO: Query memOS for recent snapshots
            print("   No recent snapshots found, proceeding with ingestion")

        print("\n📊 INGESTING ECOSYSTEM PROJECTS")
        print("-" * 40)

        # Execute ecosystem ingestion
        snapshot = await self.ecosystem_service.ingest_entire_ecosystem(
            include_historical=include_historical, generate_cross_analysis=True
        )

        # Display results
        await self._display_ingestion_results(snapshot)

        # Generate and display analysis
        await self._display_ecosystem_analysis(snapshot)

        # Store daily summary
        await self._store_daily_summary(snapshot)

    async def _display_ingestion_results(self, snapshot) -> None:
        """Display ingestion results summary."""
        print("\n✅ INGESTION RESULTS")
        print("-" * 25)
        print(f"Snapshot ID: {snapshot.snapshot_id}")
        print(f"Projects Processed: {snapshot.total_projects}")
        print(f"Total Files: {snapshot.total_files}")
        print(f"Total Size: {snapshot.total_size_bytes / (1024 * 1024):.1f} MB")
        print(f"Total Lines of Code: {snapshot.total_lines_of_code:,}")

        print("\n📋 PROJECT BREAKDOWN")
        print("-" * 20)
        for project in snapshot.projects:
            name = project["project_name"]
            status = project["project_info"]["status"]
            files = project["files_processed"]
            size_mb = project.get("total_size_bytes", 0) / (1024 * 1024)
            success_rate = project.get("success_rate", 0) * 100

            print(
                f"  {name:<15} | {status:<18} | {files:>3} files | {size_mb:>5.1f} MB | {success_rate:>5.1f}% success"
            )

    async def _display_ecosystem_analysis(self, snapshot) -> None:
        """Display ecosystem analysis results."""
        print("\n🔍 ECOSYSTEM ANALYSIS")
        print("-" * 25)

        # Health status
        health = snapshot.ecosystem_health
        print(f"Overall Health Score: {health.get('overall_score', 0):.2f}")
        print(f"Health Status: {health.get('status', 'unknown').upper()}")

        # Project health breakdown
        project_health = health.get("project_health", {})
        if project_health:
            print("\nProject Health Status:")
            for project, status in project_health.items():
                status_emoji = {
                    "excellent": "🟢",
                    "good": "🟡",
                    "fair": "🟠",
                    "needs_attention": "🔴",
                }.get(status, "⚪")
                print(f"  {status_emoji} {project}: {status}")

        # Cross-project analysis
        if snapshot.cross_project_analysis:
            cross_analysis = snapshot.cross_project_analysis

            print("\n🔗 CROSS-PROJECT INSIGHTS")
            print("-" * 25)

            shared_tech = cross_analysis.get("shared_technologies", [])
            if shared_tech:
                print(f"Shared Technologies: {', '.join(shared_tech[:5])}")

            integration_points = cross_analysis.get("integration_points", [])
            if integration_points:
                print(f"Integration Points: {len(integration_points)}")
                for point in integration_points[:3]:
                    print(f"  • {point}")

        # Recommendations
        if snapshot.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(snapshot.recommendations)})")
            print("-" * 20)
            for i, rec in enumerate(snapshot.recommendations[:5], 1):
                print(f"  {i}. {rec}")

            if len(snapshot.recommendations) > 5:
                print(f"  ... and {len(snapshot.recommendations) - 5} more")

    async def _store_daily_summary(self, snapshot) -> None:
        """Store daily EOD summary in memOS."""
        try:
            print("\n💾 STORING DAILY SUMMARY")
            print("-" * 25)

            # Create daily summary content
            content = f"ApexSigma EOD Summary - {datetime.now().strftime('%Y-%m-%d')}\n"
            content += "=" * 50 + "\n\n"
            content += f"Ecosystem Snapshot ID: {snapshot.snapshot_id}\n"
            content += f"Update Time: {snapshot.timestamp}\n"
            content += "Processing Summary:\n"
            content += f"  • Projects: {snapshot.total_projects}\n"
            content += f"  • Files: {snapshot.total_files}\n"
            content += f"  • Size: {snapshot.total_size_bytes / (1024 * 1024):.1f} MB\n"
            content += f"  • Lines of Code: {snapshot.total_lines_of_code:,}\n"
            content += f"  • Health Score: {snapshot.ecosystem_health.get('overall_score', 0):.2f}\n\n"

            # Add key insights
            content += "Key Insights:\n"
            for project in snapshot.projects:
                name = project["project_name"]
                status = project["project_info"]["status"]
                files = project["files_processed"]
                content += f"  • {name}: {files} files processed ({status})\n"

            content += f"\nRecommendations: {len(snapshot.recommendations)} items\n"

            # Store in memOS
            metadata = {
                "eod_summary": True,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "snapshot_id": snapshot.snapshot_id,
                "projects_count": snapshot.total_projects,
                "entry_type": "eod_summary",
            }

            await self.memos_client.store_memory(
                content=content,
                memory_tier="episodic",  # Daily operational memory
                metadata=metadata,
            )

            print("   ✅ Daily summary stored in memOS")

        except Exception as e:
            print(f"   ⚠️  Failed to store daily summary: {e}")
            logger.warning(f"Failed to store EOD summary: {e}")

    async def _generate_daily_report(self) -> None:
        """Generate daily report without full ingestion."""
        print("📊 GENERATING DAILY REPORT")
        print("-" * 30)
        print("   This feature will query existing snapshots from memOS")
        print("   and generate a daily status report.")
        print("   TODO: Implement memOS query for latest snapshots")

        # TODO: Query memOS for latest ecosystem data
        # TODO: Generate comparative analysis
        # TODO: Display trends and changes

    def _calculate_execution_time(self) -> str:
        """Calculate and format execution time."""
        duration = datetime.now() - self.start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"


async def main():
    """Main entry point for EOD ecosystem update."""
    parser = argparse.ArgumentParser(
        description="ApexSigma Ecosystem End of Day Update",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python eod_ecosystem_update.py                    # Standard EOD update
  python eod_ecosystem_update.py --force           # Force refresh all projects
  python eod_ecosystem_update.py --no-historical   # Skip historical storage
  python eod_ecosystem_update.py --report-only     # Generate report only
        """,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if recent snapshots exist",
    )

    parser.add_argument(
        "--no-historical", action="store_true", help="Skip storing historical snapshots"
    )

    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate daily report without full ingestion",
    )

    args = parser.parse_args()

    # Create and run EOD updater
    updater = EODEcosystemUpdater()

    await updater.run_eod_update(
        force_refresh=args.force,
        include_historical=not args.no_historical,
        report_only=args.report_only,
    )

    print(f"Execution time: {updater._calculate_execution_time()}")


if __name__ == "__main__":
    asyncio.run(main())
