#!/usr/bin/env python3
"""
Phase 4: Failure Recovery Check
Tests malformed events and verifies error handling with transaction rollback.
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


async def create_malformed_event(
    session: AsyncSession, test_name: str
) -> RawLinearEvent:
    """Create a malformed event for testing error handling."""
    print(f"\n=== Creating Malformed Event: {test_name} ===")

    # Test case 1: Missing required fields
    malformed_payloads = {
        "missing_id": {
            "type": "Issue",
            "action": "create",
            "data": {
                # Missing 'id'
                "identifier": "MALFORMED-001",
                "title": "Missing ID Field",
                "state": {"type": "started"},
            },
        },
        "missing_identifier": {
            "type": "Issue",
            "action": "create",
            "data": {
                "id": "malformed-002",
                # Missing 'identifier'
                "title": "Missing Identifier",
                "state": {"type": "started"},
            },
        },
        "invalid_json": {
            "type": "Issue",
            "action": "create",
            "data": {
                "id": "malformed-003",
                "identifier": "MALFORMED-003",
                "title": "Test",
                "state": {"type": "started"},
                # Missing required fields
            },
        },
    }

    payload = malformed_payloads.get(test_name, malformed_payloads["missing_id"])

    event = RawLinearEvent(
        signature=f"malformed-signature-{test_name}",
        event_type="Issue",
        action="create",
        headers={"content-type": "application/json"},
        body=payload,
        processed=False,
        received_at=datetime.now(timezone.utc),
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    print(f"[OK] Created malformed event ID: {event.id}")
    print(f"  Test: {test_name}")

    return event


async def verify_error_handling(session: AsyncSession, event_id: int) -> bool:
    """Verify error was properly logged and event not marked as processed."""
    print(f"\n=== Verifying Error Handling for Event {event_id} ===")

    result = await session.execute(
        select(RawLinearEvent).where(RawLinearEvent.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        print(f"[FAIL] Event not found: {event_id}")
        return False

    checks = {
        "Not processed": not event.processed,
        "Has error_log": event.error_log is not None,
        "Error logged": "error" in event.error_log.lower()
        if event.error_log
        else False,
    }

    all_ok = True
    for check_name, result in checks.items():
        if result:
            print(f"  [OK] {check_name}")
        else:
            print(f"  [FAIL] {check_name}")
            all_ok = False

    if event.error_log:
        print(f"\n  Error message: {event.error_log[:200]}")

    return all_ok


async def verify_system_continuity(session: AsyncSession) -> bool:
    """Verify system continues to operate after errors."""
    print("\n=== Verifying System Continuity ===")

    from omega_kg.settings import settings

    vault_path = Path(settings.obsidian_vault_path)

    # Create a valid event
    valid_event_data = {
        "type": "Issue",
        "action": "create",
        "data": {
            "id": "continuity-test-001",
            "identifier": "CONTINUITY-001",
            "title": "System Continuity Test",
            "description": "<p>Testing that system continues after errors</p>",
            "priority": 3,
            "state": {"id": "state-1", "name": "Backlog", "type": "backlog"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    }

    valid_event = RawLinearEvent(
        signature="continuity-signature",
        event_type="Issue",
        action="create",
        headers={"content-type": "application/json"},
        body=valid_event_data,
        processed=False,
        received_at=datetime.now(timezone.utc),
    )

    session.add(valid_event)
    await session.commit()
    await session.refresh(valid_event)

    print(f"  Created valid continuity test event: {valid_event.id}")

    # Process events
    stats = await process_pending_events(session, vault_path)

    print(f"  Processing stats: {stats}")

    # Verify valid event was processed
    if stats["processed"] >= 1:
        print("  [OK] System continues processing after errors")
        return True
    else:
        print("  [FAIL] System stopped processing after errors")
        return False


async def test_transaction_rollback():
    """Test that malformed events don't corrupt the database."""
    print("\n=== Testing Transaction Rollback ===")

    async with AsyncSessionLocal() as session:
        try:
            # Create malformed event
            event = await create_malformed_event(session, "missing_id")
            event_id = event.id

            # Note: process_pending_events commits each event individually
            # So we need to test within the same transaction context
            from omega_kg.settings import settings

            vault_path = Path(settings.obsidian_vault_path)

            # Process with error handling
            stats = await process_pending_events(session, vault_path)

            # Verify error was handled
            error_ok = await verify_error_handling(session, event_id)

            # Verify system continuity
            continuity_ok = await verify_system_continuity(session)

            return error_ok and continuity_ok

        except Exception as e:
            print(f"\n[FAIL] Transaction test error: {e}")
            import traceback

            traceback.print_exc()
            return False


async def count_error_events(session: AsyncSession) -> dict:
    """Count events with errors to verify tracking."""
    print("\n=== Error Event Statistics ===")

    result = await session.execute(
        select(RawLinearEvent).where(RawLinearEvent.error_log.isnot(None))
    )
    error_events = result.scalars().all()

    stats = {
        "total_errors": len(error_events),
        "unprocessed_with_errors": sum(1 for e in error_events if not e.processed),
        "processed_with_errors": sum(1 for e in error_events if e.processed),
    }

    print(f"  Total events with errors: {stats['total_errors']}")
    print(f"  Unprocessed: {stats['unprocessed_with_errors']}")
    print(f"  Processed: {stats['processed_with_errors']}")

    # Show recent errors
    if error_events:
        print("\n  Recent errors:")
        for event in error_events[-5:]:
            print(f"    ID {event.id}: {event.error_log[:80]}")

    return stats


async def main():
    """Run all Phase 4 failure recovery tests."""
    print("=" * 60)
    print("PHASE 4: Failure Recovery Check")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            # Test malformed event handling
            rollback_ok = await test_transaction_rollback()

            # Count error events
            error_stats = await count_error_events(session)

            print("\n" + "=" * 60)
            print("PHASE 4 SUMMARY")
            print("=" * 60)

            results = {
                "transaction_rollback": rollback_ok,
                "error_tracking": error_stats["total_errors"] > 0,
            }

            for check, result in results.items():
                status = "[PASS]" if result else "[FAIL]"
                print(f"{check:20s}: {status}")

            all_passed = all(results.values())

            if all_passed:
                print("\n[OK] Failure recovery verified")
                print("  System properly handles malformed events")
                print("  Errors are logged without stopping processing")
            else:
                print("\n[FAIL] Failure recovery issues detected")
                print("  Review error handling implementation")

            return 0 if all_passed else 1

        except Exception as e:
            print(f"\n[FAIL] Phase 4 test error: {e}")
            import traceback

            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
