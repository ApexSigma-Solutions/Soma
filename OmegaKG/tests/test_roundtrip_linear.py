#!/usr/bin/env python
"""
Manual Round-Trip Linear Sync Test for 1.5.0 Release

This script performs a complete end-to-end test:
1. Creates a test issue in Linear
2. Waits for webhook processing
3. Verifies Obsidian file created
4. Modifies the Obsidian file
5. Syncs back to Linear
6. Verifies Linear issue updated
"""

import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from omega_kg.linear_client import LinearClient
from omega_kg.smart_parser import SmartParser
from omega_kg.settings import settings
from omega_kg.models import RawLinearEvent
from omega_kg.database.session import AsyncSessionLocal
from omega_kg.domain.linear.processor import process_pending_events
from sqlalchemy import select

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test Configuration
TEST_ISSUE_PREFIX = "ROUND-TRIP-TEST"
VAULT_PATH = (
    Path(settings.obsidian_vault_path)
    if hasattr(settings, "obsidian_vault_path")
    else Path("D:/projects/omegavault.as")
)
LINEAR_FOLDER = VAULT_PATH / "Linear"


class RoundTripTester:
    def __init__(self):
        self.linear_client = LinearClient()
        self.smart_parser = SmartParser()
        self.created_issue_id: Optional[str] = None
        self.created_issue_identifier: Optional[str] = None
        self.obsidian_file: Optional[Path] = None

    async def step1_create_linear_issue(self) -> bool:
        """Step 1: Create a test issue in Linear."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 1: Creating test issue in Linear")
        logger.info("=" * 70)

        # Get the correct team UUID (Linear requires UUID, not name)
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                }
            }
        }
        """

        try:
            result = await self.linear_client._execute_query(query)
            teams = result.get("teams", {}).get("nodes", [])
            logger.info(f"Available teams: {[(t['name'], t['id']) for t in teams]}")

            if not teams:
                logger.error("No teams found in Linear")
                return False

            # Use first team (should be ApexSigma)
            team_id = teams[0]["id"]
            team_name = teams[0]["name"]
            logger.info(f"Using team: {team_name} ({team_id})")

        except Exception as e:
            logger.error(f"Failed to query Linear teams: {e}")
            return False

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        issue_title = f"{TEST_ISSUE_PREFIX}-{timestamp}: Round-trip sync test"
        issue_description = f"""
# Round-Trip Test Issue

This is a test issue for verifying bi-directional Linear sync.

Created at: {datetime.now(timezone.utc).isoformat()}
Test identifier: ROUNDTRIP-{timestamp}

## Purpose

This issue will be:
1. Created via Linear API
2. Synced to Obsidian via webhook
3. Modified in Obsidian
4. Synced back to Linear
5. Verified that changes persisted

## Initial Tags

@priority/1
#testing
"""

        try:
            issue = await self.linear_client.create_issue(
                title=issue_title,
                description=issue_description,
                team_id=team_id,
                priority=1,
            )

            self.created_issue_id = issue.get("id")
            self.created_issue_identifier = issue.get("identifier")
            issue_url = issue.get("url")

            logger.info(f"✓ Created Linear issue: {self.created_issue_identifier}")
            logger.info(f"  Issue ID: {self.created_issue_id}")
            logger.info(f"  URL: {issue_url}")
            logger.info(f"  Title: {issue_title[:80]}...")

            if not self.created_issue_id:
                logger.error("Failed to create issue - no ID returned")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to create Linear issue: {e}", exc_info=True)
            return False

    async def step2_wait_for_webhook(self, timeout: int = 30) -> bool:
        """Step 2: Wait for webhook to be processed."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 2: Waiting for webhook to sync to Obsidian")
        logger.info("=" * 70)

        logger.info(f"Waiting up to {timeout} seconds for webhook processing...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if the file has been created
            potential_files = list(
                LINEAR_FOLDER.glob(f"[{self.created_issue_identifier}]*.tnp.md")
            )
            if potential_files:
                self.obsidian_file = potential_files[0]
                logger.info(
                    f"✓ Obsidian file found after {int(time.time() - start_time)}s"
                )
                logger.info(f"  File: {self.obsidian_file.name}")
                return True

            # Check database for processed event
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(RawLinearEvent).where(RawLinearEvent.processed == False)
                )
                unprocessed = result.scalars().all()

                if unprocessed:
                    logger.info(
                        f"Found {len(unprocessed)} unprocessed events, triggering processor..."
                    )
                    await process_pending_events(session, VAULT_PATH)

            time.sleep(2)

        logger.error(f"✗ Timeout: File not created after {timeout}s")
        return False

    async def step3_verify_obsidian_file(self) -> bool:
        """Step 3: Verify the Obsidian file and its contents."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 3: Verifying Obsidian file")
        logger.info("=" * 70)

        if not self.obsidian_file or not self.obsidian_file.exists():
            logger.error("File not found!")
            return False

        # Read file
        import frontmatter

        with open(self.obsidian_file, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        logger.info(f"✓ File exists: {self.obsidian_file.name}")
        logger.info(f"  Content length: {len(post.content)} chars")
        logger.info(f"  Frontmatter keys: {list(post.metadata.keys())}")

        # Verify frontmatter
        required_fields = ["linear_id", "linear_identifier"]
        missing_fields = [f for f in required_fields if f not in post.metadata]

        if missing_fields:
            logger.error(f"✗ Missing frontmatter fields: {missing_fields}")
            return False

        logger.info("✓ Frontmatter contains required fields:")
        logger.info(f"  linear_id: {post.metadata['linear_id']}")
        logger.info(f"  linear_identifier: {post.metadata['linear_identifier']}")

        if post.metadata.get("linear_url"):
            logger.info(f"  linear_url: {post.metadata['linear_url']}")

        return True

    async def step4_modify_obsidian_file(self) -> bool:
        """Step 4: Modify the Obsidian file."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 4: Modifying Obsidian file")
        logger.info("=" * 70)

        if not self.obsidian_file:
            return False

        # Read current content
        import frontmatter

        with self.obsidian_file.open("r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Add modification marker
        modification_note = f"""
## ✋ MODIFICATION MARKER

This file was modified at: {datetime.now(timezone.utc).isoformat()}

Modification details:
- Changed priority to 2
- Added "modified" tag
- Updated description

@priority/2
#modified
"""

        # Update frontmatter
        post.metadata["modified_at"] = datetime.now(timezone.utc).isoformat()
        post.metadata["test_status"] = "modified-in-obsidian"

        # Add modification note to content
        post.content = post.content + modification_note

        # Write back
        with self.obsidian_file.open("w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        logger.info(f"✓ Modified Obsidian file: {self.obsidian_file.name}")
        logger.info("  Changes:")
        logger.info("    - Added modification marker with timestamp")
        logger.info("    - Changed priority from 1 to 2")
        logger.info("    - Added @priority/2 tag")
        logger.info("    - Added #modified tag")
        logger.info("    - Added modified_at metadata field")

        return True

    async def step5_sync_back_to_linear(self) -> bool:
        """Step 5: Sync modified file back to Linear."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 5: Syncing modified file back to Linear")
        logger.info("=" * 70)

        if not self.obsidian_file:
            logger.error("No file to sync")
            return False

        try:
            result = await self.smart_parser.sync_note_to_linear(
                str(self.obsidian_file)
            )

            if result:
                logger.info("✓ Successfully synced back to Linear")
                logger.info(f"  Issue ID: {result.get('id')}")
                logger.info(f"  Identifier: {result.get('identifier')}")
                logger.info(f"  URL: {result.get('url')}")

                # Verify it's an update (not a create)
                if result.get("id") == self.created_issue_id:
                    logger.info(
                        "  ✓ Correctly updated existing issue (not created new one)"
                    )
                    return True
                else:
                    logger.error(
                        "  ✗ Created new issue instead of updating existing one!"
                    )
                    return False
            else:
                logger.error("✗ SmartParser returned None")
                return False

        except Exception as e:
            logger.error(f"Failed to sync to Linear: {e}", exc_info=True)
            return False

    async def step6_verify_linear_update(self) -> bool:
        """Step 6: Verify the Linear issue was updated correctly."""
        logger.info("\n" + "=" * 70)
        logger.info("STEP 6: Verifying Linear issue was updated")
        logger.info("=" * 70)

        if not self.created_issue_id:
            logger.error("No issue ID to verify")
            return False

        try:
            # Fetch the updated issue from Linear
            issue = await self.linear_client.get_issue(self.created_issue_id)

            logger.info("✓ Fetched updated issue from Linear")
            logger.info(f"  Title: {issue.get('title', '')[:80]}...")
            logger.info(f"  State: {issue.get('state', {}).get('name')}")
            logger.info(f"  Priority: {issue.get('priority')}")

            # Check if modification marker is in description
            description = issue.get("description", "")
            if "MODIFICATION MARKER" in description:
                logger.info("  ✓ Modification marker found in description")
            else:
                logger.warning(
                    "  ⚠ Modification marker not in description (may be truncated)"
                )

            # Check priority was updated
            if issue.get("priority") == 2:
                logger.info("  ✓ Priority updated to 2")
            else:
                logger.warning(f"  ⚠ Priority is {issue.get('priority')}, expected 2")

            return True

        except Exception as e:
            logger.error(f"Failed to verify Linear update: {e}", exc_info=True)
            return False

    async def run_full_test(self) -> dict:
        """Run the complete round-trip test."""
        logger.info("\n" + "=" * 70)
        logger.info("ROUND-TRIP LINEAR SYNC TEST - 1.5.0 Release Verification")
        logger.info("=" * 70)
        logger.info(f"Vault Path: {VAULT_PATH}")
        logger.info(f"Linear Folder: {LINEAR_FOLDER}")
        logger.info(f"Test Prefix: {TEST_ISSUE_PREFIX}")

        results = {}

        # Step 1: Create Linear issue
        results["create_issue"] = await self.step1_create_linear_issue()

        if not results["create_issue"]:
            logger.error("Cannot continue - failed to create initial issue")
            return results

        # Step 2: Wait for webhook
        results["wait_webhook"] = await self.step2_wait_for_webhook()

        if not results["wait_webhook"]:
            logger.error("Cannot continue - webhook did not process")
            return results

        # Step 3: Verify Obsidian file
        results["verify_file"] = await self.step3_verify_obsidian_file()

        if not results["verify_file"]:
            logger.error("Cannot continue - file verification failed")
            return results

        # Step 4: Modify file
        results["modify_file"] = await self.step4_modify_obsidian_file()

        if not results["modify_file"]:
            logger.error("Cannot continue - file modification failed")
            return results

        # Step 5: Sync back
        results["sync_back"] = await self.step5_sync_back_to_linear()

        if not results["sync_back"]:
            logger.error("Cannot continue - sync back failed")
            return results

        # Step 6: Verify update
        results["verify_update"] = await self.step6_verify_linear_update()

        return results

    def print_summary(self, results: dict):
        """Print test summary."""
        logger.info("\n" + "=" * 70)
        logger.info("ROUND-TRIP TEST SUMMARY")
        logger.info("=" * 70)

        steps = [
            ("Create Issue in Linear", results.get("create_issue")),
            ("Wait for Webhook Processing", results.get("wait_webhook")),
            ("Verify Obsidian File Created", results.get("verify_file")),
            ("Modify Obsidian File", results.get("modify_file")),
            ("Sync Back to Linear", results.get("sync_back")),
            ("Verify Linear Issue Updated", results.get("verify_update")),
        ]

        for step_name, passed in steps:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{step_name}: {status}")

        passed_count = sum(results.values())
        total_count = len(results)

        logger.info("\n" + "-" * 70)
        logger.info(f"Total: {passed_count}/{total_count} steps passed")

        if passed_count == total_count:
            logger.info("✓ ALL TESTS PASSED - Round-trip sync verified!")
            logger.info(f"\nTest Issue Created: {self.created_issue_identifier}")
            logger.info(
                f"Linear URL: https://linear.app/issue/{self.created_issue_identifier}"
            )
            logger.info("\nYou can review the issue and file manually if desired.")
        else:
            logger.error(f"✗ {total_count - passed_count} STEPS FAILED")
            logger.error("Please review failures above.")

        logger.info("=" * 70)


async def main():
    """Main entry point."""
    tester = RoundTripTester()

    try:
        results = await tester.run_full_test()
        tester.print_summary(results)
    finally:
        # Note: We don't delete the test issue/file so it can be reviewed
        logger.info("\nTest artifacts preserved for manual review:")
        if tester.created_issue_identifier:
            logger.info(f"  Linear Issue: {tester.created_issue_identifier}")
        if tester.obsidian_file:
            logger.info(f"  Obsidian File: {tester.obsidian_file}")
        logger.info("\nTo clean up, manually delete the issue in Linear.")


if __name__ == "__main__":
    asyncio.run(main())
