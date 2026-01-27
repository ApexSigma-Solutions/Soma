#!/usr/bin/env python3
"""
Chat Thread Summarizer with Progress Logging

This script takes chat threads, summarizes them, and automatically saves progress
with environment snapshots to memOS.as for historical tracking.
"""

import asyncio
import argparse
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ingest_llm_as.services.llm_cache import get_llm_cache
    from ingest_llm_as.services.memos_client import get_memos_client

    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False


class ChatThreadSummarizer:
    """Summarizes chat threads and saves progress to memOS.as."""

    def __init__(self, memos_base_url: str = "http://devenviro_memos_api:8090"):
        """Initialize the summarizer."""
        self.memos_base_url = memos_base_url
        self.session_id = f"chat_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def summarize_chat_thread(
        self, chat_file_path: str, output_dir: str = None, save_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Summarize a chat thread and optionally save progress.

        Args:
            chat_file_path: Path to chat thread file
            output_dir: Directory to save summary (optional)
            save_progress: Whether to save progress to memOS.as

        Returns:
            Dictionary containing summary results
        """

        print("CHAT THREAD SUMMARIZER")
        print("=" * 50)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Session ID: {self.session_id}")
        print()

        # Load chat thread
        chat_data = await self._load_chat_thread(chat_file_path)

        # Create environment snapshot
        env_snapshot = await self._create_environment_snapshot()

        # Generate summary
        summary = await self._generate_summary(chat_data, env_snapshot)

        # Save summary to file if requested
        if output_dir:
            await self._save_summary_to_file(summary, output_dir)

        # Save progress to memOS.as if requested
        if save_progress and SERVICES_AVAILABLE:
            await self._save_progress_to_memos(summary, env_snapshot)

        print("SUCCESS: Chat thread summarization completed!")
        return summary

    async def _load_chat_thread(self, file_path: str) -> Dict[str, Any]:
        """Load and parse chat thread from file."""

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Chat thread file not found: {file_path}")

        print(f"Loading chat thread: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Try to parse as JSON first
            try:
                chat_data = json.loads(content)
                print("   Format: JSON")
            except json.JSONDecodeError:
                # Treat as plain text and structure it
                chat_data = {
                    "format": "text",
                    "content": content,
                    "lines": content.splitlines(),
                    "word_count": len(content.split()),
                    "char_count": len(content),
                }
                print("   Format: Plain text")

            print(f"   Size: {file_path.stat().st_size} bytes")

            # Add metadata
            chat_data["metadata"] = {
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "loaded_at": datetime.now().isoformat(),
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            }

            return chat_data

        except Exception as e:
            print(f"ERROR: Error loading chat thread: {e}")
            raise

    async def _create_environment_snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of the current development environment."""

        print("Creating environment snapshot...")

        try:
            import subprocess

            # Get git status
            try:
                git_status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent,
                )
                git_changes = (
                    git_status.stdout.strip().splitlines()
                    if git_status.returncode == 0
                    else []
                )
            except:
                git_changes = ["git_not_available"]

            # Get recent git commits
            try:
                git_log = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent,
                )
                recent_commits = (
                    git_log.stdout.strip().splitlines()
                    if git_log.returncode == 0
                    else []
                )
            except Exception as e:
                recent_commits = [f"git_log_not_available: {e}"]

            # Get running containers
            try:
                docker_ps = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--format",
                        "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                containers = (
                    docker_ps.stdout.strip().splitlines()
                    if docker_ps.returncode == 0
                    else []
                )
            except:
                containers = ["docker_not_available"]

            # Get network status
            try:
                network_inspect = subprocess.run(
                    [
                        "docker",
                        "network",
                        "inspect",
                        "apexsigma_net",
                        "--format",
                        "{{range .Containers}}{{.Name}} {{end}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                network_containers = (
                    network_inspect.stdout.strip().split()
                    if network_inspect.returncode == 0
                    else []
                )
            except:
                network_containers = ["network_not_available"]

            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "environment": {
                    "git_changes": git_changes,
                    "recent_commits": recent_commits,
                    "running_containers": containers,
                    "network_containers": network_containers,
                    "python_version": sys.version,
                    "working_directory": str(Path.cwd()),
                },
                "apexsigma_status": {
                    "containers_running": len(
                        [c for c in containers if "devenviro" in c or "toolsas" in c]
                    ),
                    "network_unified": "apexsigma_net" in " ".join(network_containers),
                    "integration_ready": len(network_containers) > 5,
                },
            }

            print(f"   Git changes: {len(git_changes)}")
            print(f"   Running containers: {len(containers) - 1}")  # -1 for header
            print(f"   Network containers: {len(network_containers)}")

            return snapshot

        except Exception as e:
            print(f"WARNING: Environment snapshot limited due to error: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "environment": {"error": str(e)},
                "apexsigma_status": {"error": "could_not_determine"},
            }

    async def _generate_summary(
        self, chat_data: Dict[str, Any], env_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary of the chat thread."""

        print("Generating chat summary...")

        # Extract key information based on content type
        if chat_data.get("format") == "text":
            content = chat_data["content"]
            lines = chat_data["lines"]
        else:
            # Handle JSON format
            content = json.dumps(chat_data, indent=2)
            lines = content.splitlines()

        # Basic analysis
        analysis = {
            "content_type": chat_data.get("format", "unknown"),
            "total_lines": len(lines),
            "total_words": len(content.split()),
            "total_characters": len(content),
            "estimated_reading_time_minutes": len(content.split())
            / 200,  # 200 wpm average
        }

        # Extract patterns and keywords
        content_lower = content.lower()

        # Technical keywords
        tech_keywords = {
            "docker": content_lower.count("docker"),
            "network": content_lower.count("network"),
            "container": content_lower.count("container"),
            "apexsigma": content_lower.count("apexsigma"),
            "memos": content_lower.count("memos"),
            "ingest": content_lower.count("ingest"),
            "integration": content_lower.count("integration"),
            "error": content_lower.count("error"),
            "success": content_lower.count("success"),
            "test": content_lower.count("test"),
        }

        # Find important sections (simple heuristic)
        important_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(
                keyword in line_lower
                for keyword in [
                    "error",
                    "success",
                    "complete",
                    "failed",
                    "✅",
                    "❌",
                    "critical",
                ]
            ):
                important_lines.append(
                    {
                        "line_number": i + 1,
                        "content": line.strip()[:100] + "..."
                        if len(line.strip()) > 100
                        else line.strip(),
                    }
                )

        # Generate summary
        summary = {
            "session_id": self.session_id,
            "generated_at": datetime.now().isoformat(),
            "source_file": chat_data["metadata"]["file_path"],
            "source_hash": chat_data["metadata"]["content_hash"],
            "analysis": analysis,
            "technical_keywords": tech_keywords,
            "important_sections": important_lines[:10],  # Top 10
            "environment_snapshot": env_snapshot,
            "summary_text": self._generate_summary_text(
                analysis, tech_keywords, important_lines
            ),
            "recommendations": self._generate_recommendations(
                tech_keywords, env_snapshot
            ),
        }

        print(f"   Content analyzed: {analysis['total_words']} words")
        print(f"   Important sections found: {len(important_lines)}")
        print(
            f"   Top keywords: {sorted(tech_keywords.items(), key=lambda x: x[1], reverse=True)[:3]}"
        )

        return summary

    def _generate_summary_text(
        self, analysis: Dict, keywords: Dict, important_lines: List
    ) -> str:
        """Generate human-readable summary text."""

        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:3]
        top_keywords_text = ", ".join([f"{k} ({v})" for k, v in top_keywords if v > 0])

        summary_text = f"""
Chat Thread Summary:

Content: {analysis["total_words"]} words across {analysis["total_lines"]} lines
Reading Time: ~{analysis["estimated_reading_time_minutes"]:.1f} minutes

Key Topics: {top_keywords_text}

Important Activities:
"""

        for item in important_lines[:5]:
            summary_text += f"- Line {item['line_number']}: {item['content']}\n"

        return summary_text.strip()

    def _generate_recommendations(
        self, keywords: Dict, env_snapshot: Dict
    ) -> List[str]:
        """Generate recommendations based on content analysis."""

        recommendations = []

        # Docker/container focus
        if keywords.get("docker", 0) > 5:
            recommendations.append(
                "Heavy Docker usage detected - consider documenting container setup"
            )

        if keywords.get("error", 0) > 3:
            recommendations.append(
                "Multiple errors mentioned - review error resolution patterns"
            )

        if keywords.get("integration", 0) > 2:
            recommendations.append(
                "Integration work in progress - document integration patterns"
            )

        # Environment-based recommendations
        if env_snapshot.get("apexsigma_status", {}).get("integration_ready"):
            recommendations.append(
                "ApexSigma ecosystem is operational - good time for integration testing"
            )

        if len(env_snapshot.get("environment", {}).get("git_changes", [])) > 5:
            recommendations.append(
                "Many uncommitted changes - consider creating a checkpoint commit"
            )

        return recommendations

    async def _save_summary_to_file(
        self, summary: Dict[str, Any], output_dir: str
    ) -> None:
        """Save summary to file."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = output_path / f"chat_summary_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Save as markdown
        md_file = output_path / f"chat_summary_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# Chat Thread Summary\n\n")
            f.write(f"**Generated**: {summary['generated_at']}\\n")
            f.write(f"**Session**: {summary['session_id']}\\n")
            f.write(f"**Source**: {summary['source_file']}\\n\\n")
            f.write(summary["summary_text"])
            f.write("\\n\\n## Recommendations\\n\\n")
            for rec in summary["recommendations"]:
                f.write(f"- {rec}\\n")

        print("Summary saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Markdown: {md_file}")

    async def _save_progress_to_memos(
        self, summary: Dict[str, Any], env_snapshot: Dict[str, Any]
    ) -> None:
        """Save progress to memOS.as."""

        print("Saving progress to memOS.as...")

        try:
            # Use direct HTTP client since we're in container context
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare progress log
                progress_data = {
                    "content": f"CHAT THREAD SUMMARY: Processed chat thread with {summary['analysis']['total_words']} words. Key topics: {', '.join([k for k, v in summary['technical_keywords'].items() if v > 0][:3])}. Environment snapshot captured with {len(env_snapshot['environment'].get('running_containers', []))} running containers.",
                    "metadata": {
                        "source": "ChatThreadSummarizer",
                        "session_id": summary["session_id"],
                        "event_type": "chat_summary_completed",
                        "timestamp": summary["generated_at"],
                        "priority": "NORMAL",
                        "summary_stats": summary["analysis"],
                        "technical_keywords": summary["technical_keywords"],
                        "environment_snapshot": env_snapshot,
                        "source_file": summary["source_file"],
                        "source_hash": summary["source_hash"],
                        "recommendations": summary["recommendations"],
                    },
                }

                # Send to memOS.as
                response = await client.post(
                    f"{self.memos_base_url}/memory/store",
                    json=progress_data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    print(
                        f"SUCCESS: Progress saved to memOS.as (Memory ID: {result.get('memory_id')})"
                    )
                else:
                    print(
                        f"WARNING: Failed to save to memOS.as: {response.status_code}"
                    )

        except Exception as e:
            print(f"WARNING: Could not save to memOS.as: {e}")


async def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Summarize chat threads with automatic progress logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chat_thread_summarizer.py chat.txt                    # Summarize and save to memOS.as
  python chat_thread_summarizer.py chat.txt --output ./summaries  # Save to custom directory
  python chat_thread_summarizer.py chat.txt --no-progress     # Skip memOS.as logging
        """,
    )

    parser.add_argument("chat_file", help="Path to chat thread file to summarize")

    parser.add_argument(
        "--output",
        metavar="DIR",
        help="Output directory for summary files (default: ./.md/.projects/summaries/)",
    )

    parser.add_argument(
        "--no-progress", action="store_true", help="Skip saving progress to memOS.as"
    )

    parser.add_argument(
        "--memos-url",
        default="http://devenviro_memos_api:8090",
        help="memOS.as base URL (default: http://devenviro_memos_api:8090)",
    )

    args = parser.parse_args()

    # Default output directory
    if not args.output:
        args.output = Path(".md/.projects/summaries")

    # Create summarizer
    summarizer = ChatThreadSummarizer(memos_base_url=args.memos_url)

    try:
        # Run summarization
        summary = await summarizer.summarize_chat_thread(
            chat_file_path=args.chat_file,
            output_dir=args.output,
            save_progress=not args.no_progress,
        )

        print()
        print("SUMMARY RESULTS")
        print("-" * 20)
        print(f"Words processed: {summary['analysis']['total_words']}")
        print(f"Important sections: {len(summary['important_sections'])}")
        print(f"Recommendations: {len(summary['recommendations'])}")
        print(f"Session ID: {summary['session_id']}")

        print()
        print("SUCCESS: Chat thread summarization completed successfully!")

    except Exception as e:
        print(f"\\nERROR: Summarization failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("ApexSigma Chat Thread Summarizer")
    print("Automatic progress logging with environment snapshots")
    print()

    asyncio.run(main())
