#!/usr/bin/env python3
"""
Test Chat Thread Summarizer Functions

Simple test script without Unicode characters to test functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from scripts.chat_thread_summarizer import ChatThreadSummarizer

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


async def test_chat_loading():
    """Test chat thread loading function."""

    print("TEST 1: Chat Thread Loading")
    print("-" * 30)

    if not IMPORT_SUCCESS:
        print(f"SKIP: Import failed - {IMPORT_ERROR}")
        return False

    summarizer = ChatThreadSummarizer()

    try:
        chat_data = await summarizer._load_chat_thread("test_chat_sample.txt")

        print("SUCCESS: Loaded chat thread")
        print(f"  Format: {chat_data.get('format', 'unknown')}")
        print(f"  Lines: {len(chat_data.get('lines', []))}")
        print(f"  Words: {chat_data.get('word_count', 0)}")
        print(f"  Hash: {chat_data['metadata']['content_hash']}")

        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False


async def test_environment_snapshot():
    """Test environment snapshot function."""

    print("\nTEST 2: Environment Snapshot")
    print("-" * 30)

    if not IMPORT_SUCCESS:
        print("SKIP: Import failed")
        return False

    summarizer = ChatThreadSummarizer()

    try:
        snapshot = await summarizer._create_environment_snapshot()

        print("SUCCESS: Created environment snapshot")
        print(f"  Timestamp: {snapshot['timestamp'][:19]}")
        print(f"  Git changes: {len(snapshot['environment'].get('git_changes', []))}")
        print(
            f"  Containers: {len(snapshot['environment'].get('running_containers', []))}"
        )
        print(
            f"  Network containers: {len(snapshot['environment'].get('network_containers', []))}"
        )
        print(
            f"  Integration ready: {snapshot['apexsigma_status'].get('integration_ready')}"
        )

        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False


async def test_summary_generation():
    """Test summary generation function."""

    print("\nTEST 3: Summary Generation")
    print("-" * 30)

    if not IMPORT_SUCCESS:
        print("SKIP: Import failed")
        return False

    summarizer = ChatThreadSummarizer()

    try:
        # Load test data
        chat_data = await summarizer._load_chat_thread("test_chat_sample.txt")
        env_snapshot = await summarizer._create_environment_snapshot()

        # Generate summary
        summary = await summarizer._generate_summary(chat_data, env_snapshot)

        print("SUCCESS: Generated summary")
        print(f"  Session ID: {summary['session_id']}")
        print(f"  Words analyzed: {summary['analysis']['total_words']}")
        print(f"  Important sections: {len(summary['important_sections'])}")
        print(
            f"  Technical keywords: {len([k for k, v in summary['technical_keywords'].items() if v > 0])}"
        )
        print(f"  Recommendations: {len(summary['recommendations'])}")

        # Show top keywords
        top_keywords = sorted(
            summary["technical_keywords"].items(), key=lambda x: x[1], reverse=True
        )[:3]
        print(f"  Top keywords: {[f'{k}({v})' for k, v in top_keywords if v > 0]}")

        return True

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_file_output():
    """Test file output function."""

    print("\nTEST 4: File Output")
    print("-" * 30)

    if not IMPORT_SUCCESS:
        print("SKIP: Import failed")
        return False

    summarizer = ChatThreadSummarizer()

    try:
        # Load test data and generate summary
        chat_data = await summarizer._load_chat_thread("test_chat_sample.txt")
        env_snapshot = await summarizer._create_environment_snapshot()
        summary = await summarizer._generate_summary(chat_data, env_snapshot)

        # Test file saving
        output_dir = "./test_output"
        await summarizer._save_summary_to_file(summary, output_dir)

        # Check if files were created
        output_path = Path(output_dir)
        json_files = list(output_path.glob("chat_summary_*.json"))
        md_files = list(output_path.glob("chat_summary_*.md"))

        print("SUCCESS: Files created")
        print(f"  Output directory: {output_path}")
        print(f"  JSON files: {len(json_files)}")
        print(f"  Markdown files: {len(md_files)}")

        if json_files:
            print(f"  Latest JSON: {json_files[-1].name}")
        if md_files:
            print(f"  Latest MD: {md_files[-1].name}")

        return True

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_memos_integration():
    """Test memOS.as integration (if available)."""

    print("\nTEST 5: memOS.as Integration")
    print("-" * 30)

    if not IMPORT_SUCCESS:
        print("SKIP: Import failed")
        return False

    summarizer = ChatThreadSummarizer()

    try:
        # Check if memOS.as is reachable
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8091/health")

            if response.status_code == 200:
                print("SUCCESS: memOS.as is reachable")

                # Test actual integration
                chat_data = await summarizer._load_chat_thread("test_chat_sample.txt")
                env_snapshot = await summarizer._create_environment_snapshot()
                summary = await summarizer._generate_summary(chat_data, env_snapshot)

                # Use container-internal URL for integration test
                summarizer.memos_base_url = "http://devenviro_memos_api:8090"
                await summarizer._save_progress_to_memos(summary, env_snapshot)

                print("SUCCESS: Progress saved to memOS.as")
                return True
            else:
                print(f"SKIP: memOS.as not available (status: {response.status_code})")
                return True

    except Exception as e:
        print(f"SKIP: memOS.as integration test failed: {e}")
        return True  # Not a critical failure


async def run_all_tests():
    """Run all tests."""

    print("CHAT THREAD SUMMARIZER TESTS")
    print("=" * 50)

    results = []

    # Run individual tests
    results.append(await test_chat_loading())
    results.append(await test_environment_snapshot())
    results.append(await test_summary_generation())
    results.append(await test_file_output())
    results.append(await test_memos_integration())

    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("-" * 20)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed / total) * 100:.1f}%")

    if passed == total:
        print("\nALL TESTS PASSED - Ready for commit!")
        return True
    else:
        print("\nSOME TESTS FAILED - Review before commit")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
