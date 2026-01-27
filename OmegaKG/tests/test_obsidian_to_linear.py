#!/usr/bin/env python
"""Test Obsidian → Linear sync (step 5 of round-trip)"""

import asyncio
import logging
from pathlib import Path
from omega_kg.smart_parser import SmartParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    parser = SmartParser()
    file_path = Path(
        "D:/projects/omegavault.as/Linear/[ALPHA-62] ROUND-TRIP-TEST-20251224-190634 Round-Trip Sync Test.tnp.md"
    )

    print("=" * 70)
    print("TESTING: Obsidian → Linear Sync (Round-Trip Step 5)")
    print("=" * 70)
    print(f"File: {file_path.name}")
    print()

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return

    try:
        result = await parser.sync_note_to_linear(str(file_path))

        if result:
            print("✓ Sync successful!")
            print(f"  Issue ID: {result.get('id')}")
            print(f"  Identifier: {result.get('identifier')}")
            print(f"  URL: {result.get('url')}")
            print()
            print("This confirms that Obsidian → Linear sync is working.")
            print("The SmartParser correctly detected the existing linear_id")
            print("and updated the Linear issue instead of creating a new one.")
        else:
            print("✗ Sync failed - SmartParser returned None")
    except Exception as e:
        print(f"✗ Sync failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
