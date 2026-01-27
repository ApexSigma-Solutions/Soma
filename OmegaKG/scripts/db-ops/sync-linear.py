#!/usr/bin/env python
"""
Sync Linear Script (sync_linear.py)

Usage:
    python scripts/sync_linear.py "Tasks/My Task.md"

This script manually triggers the SmartParser for a specific note,
creating or updating the corresponding Linear issue.
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Ensure the project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# pylint: disable=wrong-import-position
from omega_kg.smart_parser import SmartParser  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Sync an Obsidian note to Linear.")
    parser.add_argument(
        "note_path",
        help="Path to the Obsidian note (relative to vault root or absolute)",
    )
    args = parser.parse_args()

    note_path = args.note_path
    logger.info(f"Starting sync for: {note_path}")

    try:
        smart_parser = SmartParser()
        result = await smart_parser.sync_note_to_linear(note_path)

        if result:
            print(f"\nSUCCESS: Synced note to Linear Issue {result.get('identifier')}")
            print(f"URL: {result.get('url')}")
            sys.exit(0)
        else:
            print("\nFAILED: Sync returned no result (check logs for details).")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"An error occurred during sync: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
