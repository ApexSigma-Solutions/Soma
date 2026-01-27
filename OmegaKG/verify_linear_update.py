#!/usr/bin/env python
"""Verify Linear issue update"""

import asyncio
from omega_kg.linear_client import LinearClient


async def main():
    client = LinearClient()
    issue = await client.get_issue("ALPHA-62")

    print("=" * 70)
    print("VERIFICATION: Linear Issue After Obsidian Sync")
    print("=" * 70)
    print(f"Identifier: {issue.get('identifier')}")
    print(f"Title: {issue.get('title', '')[:80]}...")
    print(f"State: {issue.get('state', {}).get('name')}")
    print(f"Priority: {issue.get('priority')}")
    print()

    # Check if description contains modification marker
    desc = issue.get("description", "")
    if "MODIFICATION MARKER" in desc:
        print("✓ MODIFICATION MARKER found in description!")
        print("✓ This confirms bi-directional sync is working!")
    else:
        print("⚠ MODIFICATION MARKER not in description")
        print("  (May be truncated or Linear API limits)")
    print()
    print("Description preview:")
    print(desc[:500])


if __name__ == "__main__":
    asyncio.run(main())
