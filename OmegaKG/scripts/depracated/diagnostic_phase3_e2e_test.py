#!/usr/bin/env python3
"""
Phase 3: Live E2E Heartbeat Test
Creates DIAG-001 test event and verifies end-to-end processing.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.session import AsyncSessionLocal
from omega_kg.models import RawLinearEvent
from omega_kg.domain.linear.processor import process_pending_events

# Test event data - DIAG-001
DIAG_001_PAYLOAD = {
    "type": "Issue",
    "action": "create",
    "data": {
        "id": "diag-001-id",
        "identifier": "DIAG-001",
        "title": "Diagnostic Test Event",
        "description": "<p>This is a diagnostic test event created by the audit system.</p>",
        "priority": 2,
        "state": {
            "id": "state-diag",
            "name": "In Progress",
            "type": "started",
        },
        "assignee": {
            "id": "user-diag",
            "name": "Diagnostic User",
            "email": "diag@test.local",
        },
        "labels": [{"id": "label-diag", "name": "diagnostic"}],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
}


async def create_diagnostic_event(session: AsyncSession) -> RawLinearEvent:
    """Create DIAG-001 test event in database."""
    print("\n=== Creating DIAG-001 Test Event ===")

    event = RawLinearEvent(
        signature="diagnostic-signature-diag-001",
        event_type="Issue",
        action="create",
        headers={"content-type": "application/json"},
        body=DIAG_001_PAYLOAD,
        processed=False,
        received_at=datetime.now(timezone.utc),
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    print(f"[OK] Created event ID: {event.id}")
    print(f"  Signature: {event.signature}")
    print(f"  Event Type: {event.event_type}")
    print(f"  Processed: {event.processed}")

    return event


async def verify_file_created(vault_path: Path, expected_filename: str) -> bool:
    """Verify markdown file was created in vault."""
    print("\n=== Verifying File Creation ===")

    expected_file = vault_path / "Linear" / expected_filename

    if expected_file.exists():
        print(f"[OK] File created: {expected_file}")

        # Read and display content
        content = expected_file.read_text(encoding="utf-8")
        print(f"\nFile size: {len(content)} bytes")

        # Check for expected content
        checks = [
            ("linear_id", "diag-001-id" in content),
            ("identifier", "DIAG-001" in content),
            ("title", "# Diagnostic Test Event" in content),
            ("status", "status: active" in content or "status: In Progress" in content),
            ("assignee", "Diagnostic User" in content),
            ("tags", "diagnostic" in content.lower()),
        ]

        print("\nContent validation:")
        all_ok = True
        for check_name, result in checks:
            if result:
                print(f"  [OK] {check_name}")
            else:
                print(f"  [WARN] {check_name}: not found")
                all_ok = False

        return all_ok
    else:
        print(f"[FAIL] File not created: {expected_file}")

        # Check if Linear directory exists
        linear_dir = vault_path / "Linear"
        if linear_dir.exists():
            files = list(linear_dir.glob("*.md"))
            print(f"  Files in Linear directory: {len(files)}")
            for f in files:
                print(f"    - {f.name}")
        else:
            print("  Linear directory does not exist")

        return False


async def verify_database_update(session: AsyncSession, event_id: int) -> bool:
    """Verify database record was updated to processed=TRUE."""
    print("\n=== Verifying Database Update ===")

    result = await session.execute(
        select(RawLinearEvent).where(RawLinearEvent.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event:
        if event.processed:
            print(f"[OK] Event marked as processed: {event.id}")
            print(f"  Received at: {event.received_at}")

            if event.error_log:
                print(f"  [WARN] error_log is set: {event.error_log}")
                return False
            else:
                print("  [OK] No errors in error_log")
                return True
        else:
            print(f"[FAIL] Event NOT marked as processed: {event.id}")
            if event.error_log:
                print(f"  Error: {event.error_log}")
            return False
    else:
        print(f"[FAIL] Event not found in database: {event_id}")
        return False


async def run_e2e_test():
    """Run complete E2E test with DIAG-001 event."""
    print("=" * 60)
    print("PHASE 3: Live E2E Heartbeat Test")
    print("=" * 60)

    from omega_kg.settings import settings

    # Import vault path
    vault_path = Path(settings.obsidian_vault_path)
    expected_filename = "[DIAG-001] Diagnostic Test Event.md"

    async with AsyncSessionLocal() as session:
        try:
            # Step 1: Create test event
            event = await create_diagnostic_event(session)

            # Step 2: Process events
            print("\n=== Processing Events ===")
            stats = await process_pending_events(session, vault_path)

            print("\nProcessing statistics:")
            print(f"  Processed: {stats['processed']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Skipped: {stats['skipped']}")

            # Step 3: Verify file created
            file_ok = await verify_file_created(vault_path, expected_filename)

            # Step 4: Verify database update
            db_ok = await verify_database_update(session, event.id)

            print("\n" + "=" * 60)
            print("PHASE 3 SUMMARY")
            print("=" * 60)

            results = {
                "event_created": event.id is not None,
                "event_processed": stats["processed"] > 0,
                "file_created": file_ok,
                "db_updated": db_ok,
            }

            for check, result in results.items():
                status = "[PASS]" if result else "[FAIL]"
                print(f"{check:15s}: {status}")

            all_passed = all(results.values())

            if all_passed:
                print("\n[OK] E2E test completed successfully")
                print(f"  Event ID: {event.id}")
                print(f"  File: Linear/{expected_filename}")
                print("  Data is ready for review in Obsidian vault")
            else:
                print("\n[FAIL] E2E test failed")
                print("  Check logs for details")

            return 0 if all_passed else 1

        except Exception as e:
            print(f"\n[FAIL] E2E test error: {e}")
            import traceback

            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_e2e_test()))
