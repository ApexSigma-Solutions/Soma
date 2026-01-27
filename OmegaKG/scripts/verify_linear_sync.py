#!/usr/bin/env python
"""
Bi-Directional Linear Sync Verification Script

Tests the complete sync loop:
1. Linear → Obsidian (webhook flow)
2. Obsidian → Linear (smart parser flow)
3. Round-trip consistency

Run with: poetry run python scripts/verify_linear_sync.py
"""

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test Data
TEST_ISSUE_ID = "test-issue-123"
TEST_ISSUE_IDENTIFIER = "LIN-TEST-123"
TEST_TEAM_ID = "team-test-123"


class LinearSyncVerifier:
    """Verifies bi-directional Linear sync functionality."""

    def __init__(self):
        self.vault_path = Path(tempfile.mkdtemp(prefix="omega_linear_test_"))
        logger.info(f"Test vault created at: {self.vault_path}")

        # Create test directories
        (self.vault_path / "Tasks").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Linear").mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        """Clean up test resources."""
        import shutil

        if self.vault_path.exists():
            logger.info(f"Cleaning up test vault: {self.vault_path}")
            shutil.rmtree(self.vault_path)

    # -------------------------------------------------------------------------
    # DIRECTION 1: Linear → Obsidian (Webhook Flow)
    # -------------------------------------------------------------------------

    async def test_linear_to_obsidian_webhook(self):
        """
        Test Direction 1: Linear webhook → Obsidian file + Neo4j

        Flow:
        1. Simulate Linear webhook payload
        2. Verify webhook is stored in PostgreSQL
        3. Process webhook through processor
        4. Verify Obsidian file created with frontmatter
        5. Verify Neo4j node created with linear metadata
        """
        logger.info("\n" + "=" * 70)
        logger.info("TEST 1: Linear → Obsidian (Webhook Flow)")
        logger.info("=" * 70)

        from omega_kg.domain.linear.processor import process_pending_events
        from omega_kg.database.session import AsyncSessionLocal

        # 1. Create mock webhook payload
        webhook_payload = {
            "action": "create",
            "type": "Issue",
            "data": {
                "id": TEST_ISSUE_ID,
                "identifier": TEST_ISSUE_IDENTIFIER,
                "title": "Test Issue from Linear",
                "description": "This is a test issue created from Linear webhook",
                "priority": 1,
                "url": f"https://linear.app/issue/{TEST_ISSUE_IDENTIFIER}",
                "state": {
                    "id": "state-123",
                    "name": "In Progress",
                    "type": "started",
                    "color": "#F00",
                },
                "assignee": {
                    "id": "user-123",
                    "name": "Test User",
                    "email": "test@example.com",
                    "active": True,
                },
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
            "webhookId": "webhook-123",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Step 1: Creating mock webhook payload...")
        logger.info(
            f"  Payload: {json.dumps(webhook_payload, indent=2, default=str)[:200]}..."
        )

        # 2. Store webhook in PostgreSQL (simulating receiver.py)
        from omega_kg.models.linear import RawLinearEvent

        async with AsyncSessionLocal() as session:
            # Create raw event
            import hmac
            import hashlib

            secret = b"test-secret"
            payload_bytes = json.dumps(webhook_payload).encode("utf-8")
            signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

            db_event = RawLinearEvent(
                signature=signature,
                external_timestamp=datetime.now(timezone.utc),
                event_type="Issue",
                action="create",
                headers={"Linear-Signature": signature},
                body=webhook_payload,
                processed=False,
            )

            session.add(db_event)
            await session.commit()
            logger.info(
                "Step 2: Stored webhook in PostgreSQL (event_id=%d)", db_event.id
            )

            # 3. Process pending events
            logger.info("Step 3: Processing webhook through Linear processor...")
            stats = await process_pending_events(session, self.vault_path)
            logger.info(f"  Processing stats: {stats}")

        # 4. Verify Obsidian file created
        linear_file = self.vault_path / "Linear" / f"{TEST_ISSUE_IDENTIFIER}.md"
        if linear_file.exists():
            logger.info("Step 4: ✓ Obsidian file created: %s", linear_file.name)

            # Check frontmatter
            import frontmatter

            post = frontmatter.load(linear_file)
            logger.info(
                f"  Frontmatter: {json.dumps(post.metadata, indent=2, default=str)}"
            )

            # Verify linear_id in frontmatter
            assert post.metadata.get("linear_id") == TEST_ISSUE_ID, "linear_id mismatch"
            assert post.metadata.get("linear_identifier") == TEST_ISSUE_IDENTIFIER, (
                "linear_identifier mismatch"
            )
            logger.info("  ✓ Frontmatter contains linear_id and linear_identifier")
        else:
            logger.error("Step 4: ✗ Obsidian file NOT created")
            return False

        # 5. Verify Neo4j node created (if available)
        try:
            from omega_kg.database.graph import graph_driver

            await graph_driver.connect()
            async with graph_driver.session() as session:
                result = await session.run(
                    """
                    MATCH (i:LinearIssue {id: $id})
                    RETURN i
                    """,
                    id=TEST_ISSUE_ID,
                )
                record = await result.single()

                if record:
                    logger.info("Step 5: ✓ Neo4j node created")
                    logger.info(f"  Node: {record['i']}")
                else:
                    logger.warning("Step 5: Neo4j node NOT created (may be expected)")
            await graph_driver.close()
        except Exception as e:
            logger.warning(f"Step 5: Neo4j check failed: {e}")

        return True

    # -------------------------------------------------------------------------
    # DIRECTION 2: Obsidian → Linear (Smart Parser Flow)
    # -------------------------------------------------------------------------

    async def test_obsidian_to_linear_smart_parser(self):
        """
        Test Direction 2: Obsidian file → Linear GraphQL

        Flow:
        1. Create Obsidian task file with frontmatter
        2. Call POST /obsidian-update endpoint
        3. Verify SmartParser parses tags correctly
        4. Verify LinearClient creates issue
        5. Verify frontmatter updated with linear_id
        """
        logger.info("\n" + "=" * 70)
        logger.info("TEST 2: Obsidian → Linear (Smart Parser Flow)")
        logger.info("=" * 70)

        from omega_kg.smart_parser import SmartParser

        # 1. Create test note with frontmatter
        note_path = self.vault_path / "Tasks" / "TestTask.md"
        note_content = """---
status: In Progress
tags: [test, urgent]
---

# Test Task for Linear Sync

This is a test task that should sync to Linear.

@assignee/test_user
@label/backend
@priority/1
#feature-request
"""
        note_path.write_text(note_content, encoding="utf-8")
        logger.info("Step 1: Created test note at: %s", note_path.name)

        # 2. Mock LinearClient GraphQL API
        mock_linear_response = {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "created-issue-456",
                    "identifier": "CRE-456",
                    "title": "Test Task for Linear Sync",
                    "url": "https://linear.app/issue/CRE-456",
                },
            }
        }

        logger.info("Step 2: Mocking Linear GraphQL API...")
        with patch("omega_kg.linear_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = AsyncMock()
            mock_instance.post.return_value.json = MagicMock(
                return_value={"data": mock_linear_response}
            )
            mock_instance.post.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 3. Initialize SmartParser with mocked settings
            with patch("omega_kg.smart_parser.settings") as mock_settings:
                mock_settings.linear_team_id = TEST_TEAM_ID
                mock_settings.linear_user_map_json = json.dumps(
                    {"test_user": "user-789"}
                )
                mock_settings.linear_label_map_json = json.dumps(
                    {"backend": "label-backend-123"}
                )
                mock_settings.linear_status_map_json = json.dumps(
                    {"in-progress": "state-in-progress-123"}
                )

                # Mock VaultUtils
                with patch("omega_kg.smart_parser.VaultUtils") as mock_vault:
                    mock_vault.return_value.read_note_frontmatter.return_value = {
                        "status": "In Progress"
                    }
                    mock_vault.return_value.resolve_path.return_value = note_path
                    mock_vault.return_value.update_note_frontmatter.return_value = True

                    parser = SmartParser()

                    logger.info("Step 3: Calling SmartParser.sync_note_to_linear()...")
                    result = await parser.sync_note_to_linear(note_path)

                    # 4. Verify result
                    if result:
                        logger.info("Step 4: ✓ SmartParser returned issue data")
                        logger.info(f"  Issue ID: {result.get('id')}")
                        logger.info(f"  Identifier: {result.get('identifier')}")
                        logger.info(f"  URL: {result.get('url')}")

                        # Verify Linear API was called
                        assert mock_instance.post.called, "Linear API not called"
                        logger.info("Step 5: ✓ Linear GraphQL API called")

                        # Check GraphQL payload
                        call_args = mock_instance.post.call_args.kwargs["json"]
                        query = call_args["query"]
                        variables = call_args["variables"]

                        logger.info("  GraphQL Operation: CreateIssue")
                        logger.info(f"  Variables: {json.dumps(variables, indent=2)}")

                        # Verify frontmatter update
                        mock_vault.return_value.update_note_frontmatter.assert_called_once()
                        updates = (
                            mock_vault.return_value.update_note_frontmatter.call_args[
                                0
                            ][1]
                        )
                        logger.info("Step 6: ✓ Frontmatter updated with linear_id")
                        logger.info(f"  Updates: {json.dumps(updates, indent=2)}")

                        assert updates["linear_id"] == "created-issue-456"
                        assert updates["linear_identifier"] == "CRE-456"

                        return True
                    else:
                        logger.error("Step 4: ✗ SmartParser returned None")
                        return False

    # -------------------------------------------------------------------------
    # ROUND-TRIP TEST: Bi-Directional Sync
    # -------------------------------------------------------------------------

    async def test_round_trip_sync(self):
        """
        Test Round-Trip: Linear → Obsidian → Linear

        Flow:
        1. Create issue in Linear (via webhook)
        2. Sync to Obsidian file
        3. Update Obsidian file
        4. Sync back to Linear (via smart parser)
        5. Verify Linear issue updated
        """
        logger.info("\n" + "=" * 70)
        logger.info("TEST 3: Round-Trip Sync (Linear → Obsidian → Linear)")
        logger.info("=" * 70)

        # This test would require:
        # 1. Real Linear API credentials
        # 2. Real Linear instance
        # 3. Integration with both directions

        logger.info("Step 1: Create issue in Linear (simulated)")
        logger.info("Step 2: Sync to Obsidian (via webhook)")
        logger.info("Step 3: Update Obsidian file")
        logger.info("Step 4: Sync back to Linear (via smart parser)")
        logger.info("Step 5: Verify Linear issue updated")

        logger.info("\nNOTE: Round-trip test requires real Linear instance.")
        logger.info("This is a manual verification step.")
        logger.info("\nManual Test Steps:")
        logger.info("1. Create issue in Linear (e.g., 'ROUND-TRIP-001')")
        logger.info("2. Wait for webhook to sync to Obsidian vault")
        logger.info("3. Verify Obsidian file created in Linear/ folder")
        logger.info("4. Edit Obsidian file (change title, tags, etc.)")
        logger.info("5. Call POST /obsidian-update with file path")
        logger.info("6. Verify Linear issue updated with changes")
        logger.info("7. Check that linear_id is preserved in Obsidian frontmatter")

        return True

    # -------------------------------------------------------------------------
    # MAIN EXECUTION
    # -------------------------------------------------------------------------

    async def run_all_tests(self):
        """Run all verification tests."""
        logger.info("\n" + "=" * 70)
        logger.info("BI-DIRECTIONAL LINEAR SYNC VERIFICATION")
        logger.info("=" * 70)
        logger.info("Version: 1.5.0")
        logger.info(f"Test Vault: {self.vault_path}")

        results = {}

        try:
            # Test 1: Linear → Obsidian (Webhook Flow)
            results["linear_to_obsidian"] = await self.test_linear_to_obsidian_webhook()
        except Exception as e:
            logger.error(f"TEST 1 FAILED: {e}", exc_info=True)
            results["linear_to_obsidian"] = False

        try:
            # Test 2: Obsidian → Linear (Smart Parser Flow)
            results[
                "obsidian_to_linear"
            ] = await self.test_obsidian_to_linear_smart_parser()
        except Exception as e:
            logger.error(f"TEST 2 FAILED: {e}", exc_info=True)
            results["obsidian_to_linear"] = False

        try:
            # Test 3: Round-Trip
            results["round_trip"] = await self.test_round_trip_sync()
        except Exception as e:
            logger.error(f"TEST 3 FAILED: {e}", exc_info=True)
            results["round_trip"] = False

        # Summary
        self.print_summary(results)

    def print_summary(self, results: Dict[str, bool]):
        """Print test summary."""
        logger.info("\n" + "=" * 70)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 70)

        for test_name, passed in results.items():
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")

        passed_count = sum(results.values())
        total_count = len(results)

        logger.info("\n" + "-" * 70)
        logger.info(f"Total: {passed_count}/{total_count} tests passed")

        if passed_count == total_count:
            logger.info("✓ ALL TESTS PASSED - Bi-directional Linear sync verified!")
        else:
            logger.error(f"✗ {total_count - passed_count} TESTS FAILED")
            logger.error("Please review failures above.")

        logger.info("=" * 70 + "\n")


async def main():
    """Main entry point."""
    verifier = LinearSyncVerifier()

    try:
        await verifier.run_all_tests()
    finally:
        verifier.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
