"""
LinearSync - Bi-directional Sync Between Linear and Obsidian

This module handles syncing status changes between Linear and local Obsidian markdown files.

Key Features:
- Listens for IssueUpdated webhook events from Linear (inbound sync)
- Creates new Linear issues from local Obsidian notes (outbound sync)
- Maps Linear state types to vault status tags
- Updates YAML frontmatter status field in matching files
- Handles files that may have been moved or renamed (search by linear_id)
- Idempotent sync via linear_id frontmatter tracking
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import frontmatter

from omega_kg.linear_client import LinearClient
from omega_kg.settings import settings
from omega_kg.vault_utils import VaultUtils

logger = logging.getLogger(__name__)


# Mapping from Linear state type to vault status
# Linear state types: started, completed, canceled, triage, backlog
LINEAR_TO_VAULT_STATUS = {
    "started": "In Progress",
    "completed": "Done",
    "canceled": "Canceled",
    "triage": "Backlog",
    "backlog": "Backlog",
}

# Reverse mapping for validation
VAULT_TO_LINEAR_STATUS = {v: k for k, v in LINEAR_TO_VAULT_STATUS.items()}


class LinearSyncError(Exception):
    """Base exception for LinearSync operations."""

    pass


class FileNotFoundError(LinearSyncError):
    """Raised when no file is found for the given linear_id."""

    pass


class NoStatusChangeError(LinearSyncError):
    """Raised when the status in the payload matches the current file status."""

    pass


class LinearAPIError(LinearSyncError):
    """Raised when the Linear API returns an error."""

    pass


class LinearSync:
    """
    Handles synchronization of Linear issue status changes to local Obsidian files.

    This class is the "write-back" side of the Linear-Obsidian sync pipeline.
    It receives webhook events from Linear, finds the matching local file by linear_id,
    and updates the frontmatter status field.

    Usage:
        sync = LinearSync(vault_path="/path/to/vault")
        sync.update_local_note(payload)  # payload from Linear webhook

    Attributes:
        vault_utils: VaultUtils instance for file operations
        vault_path: Path to the Obsidian vault
    """

    def __init__(
        self,
        vault_path: Optional[Path] = None,
        linear_client: Optional[LinearClient] = None,
    ):
        """
        Initialize LinearSync with vault path.

        Args:
            vault_path: Path to Obsidian vault. If None, uses settings default.
            linear_client: Optional LinearClient instance for API calls.
                          If None, creates a new instance.
        """
        self.vault_path = (
            Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
        )
        self.vault_utils = VaultUtils(self.vault_path)
        self.linear_client = linear_client or LinearClient()
        self.team_id = settings.linear_team_id
        logger.info(f"LinearSync initialized with vault: {self.vault_path}")

    def map_linear_state_to_vault_status(self, state_name: str, state_type: str) -> str:
        """
        Map a Linear state name/type to a vault status string.

        Args:
            state_name: The display name from Linear (e.g., "Todo", "Done")
            state_type: The state type from Linear (e.g., "started", "completed")

        Returns:
            Vault-compatible status string
        """
        # First try to use the state type mapping
        if state_type in LINEAR_TO_VAULT_STATUS:
            return LINEAR_TO_VAULT_STATUS[state_type]

        # Fallback: Try to match by state name (case-insensitive)
        state_name_lower = state_name.lower()
        if "done" in state_name_lower or "complete" in state_name_lower:
            return "Done"
        elif "cancel" in state_name_lower:
            return "Canceled"
        elif "backlog" in state_name_lower or "triage" in state_name_lower:
            return "Backlog"
        elif "progress" in state_name_lower or "started" in state_name_lower:
            return "In Progress"
        elif "todo" in state_name_lower:
            return "Todo"

        # Default fallback
        logger.warning(
            f"Unknown Linear state: {state_name} ({state_type}), defaulting to Backlog"
        )
        return "Backlog"

    def extract_issue_data(self, payload: Dict[str, Any]) -> tuple[str, str, str, str]:
        """
        Extract issue data from a Linear webhook payload.

        Args:
            payload: The webhook payload dictionary

        Returns:
            Tuple of (issue_id, state_name, state_type, identifier)

        Raises:
            KeyError: If required fields are missing from payload
        """
        data = payload.get("data", {})
        if not data:
            raise KeyError("Payload missing 'data' field")

        issue_id = data.get("id")
        if not issue_id:
            raise KeyError("Payload missing 'data.id' field (issue_id)")

        # Extract state information
        state_data = data.get("state", {})
        if isinstance(state_data, dict):
            state_name = state_data.get("name", "Unknown")
            state_type = state_data.get("type", "backlog")
        else:
            # State might be just an ID if not expanded
            state_name = "Unknown"
            state_type = "backlog"

        identifier = data.get("identifier", issue_id)

        return issue_id, state_name, state_type, identifier

    def find_note_by_linear_id(self, linear_id: str) -> Optional[Path]:
        """
        Find the note file matching a Linear issue ID.

        This handles cases where the file may have been moved or renamed.

        Args:
            linear_id: The Linear issue ID to search for

        Returns:
            Path to the matching file, or None if not found
        """
        return self.vault_utils.find_note_by_linear_id(linear_id)

    def get_current_status(self, file_path: Path) -> Optional[str]:
        """
        Get the current status from a note's frontmatter.

        Args:
            file_path: Path to the note file

        Returns:
            Current status string, or None if not set
        """
        metadata = self.vault_utils.read_note_frontmatter(file_path)
        return metadata.get("status")

    def update_local_note(self, payload: Dict[str, Any]) -> bool:
        """
        Update the local markdown file when an issue is updated in Linear.

        This is the main entry point for handling IssueUpdated webhook events.
        It extracts the issue data, finds the matching local file, maps the Linear
        state to a vault status, and updates the frontmatter.

        Args:
            payload: The webhook payload from Linear (parsed JSON dict)

        Returns:
            True if the update was successful, False otherwise

        Raises:
            FileNotFoundError: If no file is found for the linear_id
            NoStatusChangeError: If the status hasn't changed
            LinearSyncError: For other sync errors
        """
        try:
            # Extract issue data from payload
            issue_id, state_name, state_type, identifier = self.extract_issue_data(
                payload
            )

            logger.info(
                f"Processing status update for {identifier} (issue_id: {issue_id}): "
                f"state={state_name} ({state_type})"
            )

            # Find the local file by linear_id
            file_path = self.find_note_by_linear_id(issue_id)

            if not file_path:
                # Try searching by identifier as fallback
                logger.warning(
                    f"No file found for linear_id={issue_id}, trying identifier={identifier}"
                )
                file_path = self.find_note_by_linear_id(identifier)

            if not file_path:
                logger.error(
                    f"Could not find local file for issue {identifier} "
                    f"(linear_id={issue_id}). File may have been deleted or moved."
                )
                raise FileNotFoundError(
                    f"No note found for linear_id={issue_id} or identifier={identifier}"
                )

            # Map Linear state to vault status
            new_status = self.map_linear_state_to_vault_status(state_name, state_type)

            # Get current status to check if change is needed
            current_status = self.get_current_status(file_path)

            if current_status == new_status:
                logger.info(
                    f"Status unchanged for {identifier}: '{current_status}' "
                    f"(skipping update)"
                )
                return True  # Not an error, just no change needed

            # Update the frontmatter
            success = self.vault_utils.update_note_frontmatter(
                file_path, {"status": new_status}
            )

            if success:
                logger.info(
                    f"✓ Updated status for {identifier}: "
                    f"'{current_status}' → '{new_status}'"
                )
                return True
            else:
                logger.error(f"Failed to update frontmatter for {file_path}")
                raise LinearSyncError(f"Failed to update frontmatter for {file_path}")

        except FileNotFoundError:
            raise
        except NoStatusChangeError:
            raise
        except KeyError as e:
            logger.error(f"Invalid payload structure: {e}")
            raise LinearSyncError(f"Invalid payload: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating local note: {e}", exc_info=True)
            raise LinearSyncError(f"Unexpected error: {e}")

    def handle_issue_updated(self, payload: Dict[str, Any]) -> bool:
        """
        Handle an IssueUpdated webhook event from Linear.

        This is an alias for update_local_note() with semantic naming for webhook handlers.

        Args:
            payload: The webhook payload from Linear

        Returns:
            True if processed successfully
        """
        return self.update_local_note(payload)

    # -------------------------------------------------------------------------
    # Outbound Sync: Obsidian → Linear
    # -------------------------------------------------------------------------

    def _extract_title_from_content(self, content: str) -> str:
        """
        Extract title from the first H1 heading in markdown content.

        Args:
            content: The markdown body content.

        Returns:
            The title extracted from first H1, or empty string if not found.
        """
        # Match # Title or #Title (with optional leading whitespace)
        match = re.match(r"^#\s+(.+)$", content.strip(), re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def _map_vault_status_to_linear_state(
        self, vault_status: str, team_id: str
    ) -> Optional[str]:
        """
        Map a vault status string to a Linear Workflow State ID.

        This is a simplified mapping. In production, you would query
        Linear's workflow states API to get actual state IDs for your team.

        Args:
            vault_status: The status from vault frontmatter.
            team_id: The Linear team ID for state lookup.

        Returns:
            Linear state ID, or None if not found/mapped.
        """
        # Default state mappings - these should be customized based on your Linear workflow
        # Common default states (these are example IDs, real ones come from Linear API)
        status_mappings = {
            "backlog": None,  # Backlog usually has no specific state ID (creates in backlog)
            "todo": None,
            "in_progress": None,
            "done": None,
            "canceled": None,
            "cancelled": None,
        }

        # If we have a specific mapping, return the state ID
        normalized_status = vault_status.lower().replace(" ", "_")
        return status_mappings.get(normalized_status)

    def create_from_note(self, note_path: str) -> str:
        """
        Create a Linear issue from an Obsidian note.

        This method handles the outbound sync from local markdown files to Linear:
        1. Checks for existing linear_id (idempotency)
        2. Parses frontmatter and content
        3. Creates issue in Linear
        4. Writes back linear_id to frontmatter

        Args:
            note_path: Path to the markdown note (relative or absolute).

        Returns:
            The Linear issue ID (e.g., "LIN-123") or existing ID if already synced.

        Raises:
            LinearSyncError: If file not found, API error, or write failure.
        """
        resolved_path = self.vault_utils.resolve_path(note_path)

        logger.info(f"[create_from_note] Processing note: {resolved_path}")

        # -------------------------------------------------------------------------
        # Step 1: Load and parse the note
        # -------------------------------------------------------------------------
        try:
            with resolved_path.open("r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        except OSError as e:
            logger.error(f"Failed to read note file: {resolved_path} - {e}")
            raise LinearSyncError(f"Failed to read note: {e}")

        metadata = post.metadata
        content = post.content

        # -------------------------------------------------------------------------
        # Step 2: Idempotency check - return existing linear_id if present
        # -------------------------------------------------------------------------
        existing_linear_id = metadata.get("linear_id")
        if existing_linear_id:
            logger.info(
                f"[create_from_note] Idempotency skip: Note already synced to Linear "
                f"with ID: {existing_linear_id}"
            )
            return str(existing_linear_id)

        # -------------------------------------------------------------------------
        # Step 3: Extract data for Linear issue creation
        # -------------------------------------------------------------------------
        # Title: Prefer frontmatter 'title', fallback to first H1, fallback to filename
        title = metadata.get("title") or self._extract_title_from_content(content)
        if not title:
            title = resolved_path.stem  # Use filename without extension
            logger.warning(
                f"[create_from_note] No title found, using filename: {title}"
            )

        # Description: Use the full body content
        description = content.strip()
        if not description:
            description = f"Issue created from note: {resolved_path.name}"
            logger.warning("[create_from_note] Empty description, using fallback")

        # Status: Map vault status to Linear state if needed
        vault_status = str(metadata.get("status", "backlog"))
        state_id = self._map_vault_status_to_linear_state(
            vault_status, str(self.team_id)
        )

        # -------------------------------------------------------------------------
        # Step 4: Create issue in Linear
        # -------------------------------------------------------------------------
        if not self.team_id:
            logger.error(
                "[create_from_note] LINEAR_TEAM_ID is not configured. "
                "Cannot create issues without a team ID."
            )
            raise LinearSyncError(
                "LINEAR_TEAM_ID not configured. Set LINEAR_TEAM_ID environment variable."
            )

        try:
            title_display = f"{title[:50]}..." if len(str(title)) > 50 else str(title)
            logger.info(
                f'[create_from_note] Creating Linear issue: title="{title_display}", '
                f"team_id={self.team_id}"
            )

            # Call the async Linear API (LinearClient.create_issue is async)
            result = asyncio.run(
                self.linear_client.create_issue(
                    title=str(title),
                    description=str(description),
                    team_id=str(self.team_id),
                    state_id=state_id,
                )
            )

            # Extract the issue ID from response
            issue_id = result.get("id") if isinstance(result, dict) else None
            identifier = (
                result.get("identifier", issue_id)
                if isinstance(result, dict)
                else issue_id
            )

            if not issue_id:
                logger.error(
                    f"[create_from_note] API response missing issue ID: {result}"
                )
                raise LinearAPIError(
                    "Failed to create Linear issue: No issue ID in response"
                )

            logger.info(
                f"[create_from_note] ✓ Created Linear issue: {identifier} (ID: {issue_id})"
            )

        except Exception as e:
            logger.error(f"[create_from_note] Failed to create Linear issue: {e}")
            raise LinearAPIError(f"Linear API error: {e}")

        # -------------------------------------------------------------------------
        # Step 5: Write back linear_id to frontmatter
        # -------------------------------------------------------------------------
        write_success = self.vault_utils.update_note_frontmatter(
            resolved_path, {"linear_id": identifier}
        )

        if not write_success:
            logger.error(
                f"[create_from_note] Failed to write linear_id back to note: {resolved_path}"
            )
            # Don't raise here - the issue was created in Linear,
            # but we should log the inconsistency
            logger.warning(
                f"[create_from_note] Manual fix needed: Add linear_id={identifier} "
                f"to frontmatter of {resolved_path}"
            )

        return str(identifier) if identifier else ""


# Convenience function for quick initialization
def get_linear_sync(vault_path: Optional[Path] = None) -> LinearSync:
    """
    Get a LinearSync instance.

    Args:
        vault_path: Optional vault path override

    Returns:
        LinearSync instance
    """
    return LinearSync(vault_path)


# TEST HARNESS
if __name__ == "__main__":
    import tempfile
    from pathlib import Path as PathLib

    print("[TEST] Running LinearSync Test Harness")

    # Create a temporary vault for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = PathLib(tmpdir)

        # Create a test note with frontmatter
        test_note_content = """---
linear_id: test-issue-123
status: Todo
identifier: TEST-123
---
# Test Issue

This is a test issue for LinearSync.
"""
        test_note_path = vault_path / "Linear" / "TEST-123.md"
        test_note_path.parent.mkdir(parents=True, exist_ok=True)
        test_note_path.write_text(test_note_content, encoding="utf-8")

        print(f"Created test note: {test_note_path}")

        # Initialize LinearSync
        sync = LinearSync(vault_path=vault_path)

        # Test 1: Extract issue data
        print("\n--- Test 1: Extract Issue Data ---")
        test_payload = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "test-issue-123",
                "identifier": "TEST-123",
                "state": {"name": "Done", "type": "completed"},
            },
        }

        issue_id, state_name, state_type, identifier = sync.extract_issue_data(
            test_payload
        )
        print(f"  issue_id: {issue_id}")
        print(f"  state_name: {state_name}")
        print(f"  state_type: {state_type}")
        print(f"  identifier: {identifier}")
        assert issue_id == "test-issue-123"
        assert state_name == "Done"
        assert state_type == "completed"
        print("  ✓ Test 1 passed")

        # Test 2: Map Linear state to vault status
        print("\n--- Test 2: Map Linear State to Vault Status ---")
        status = sync.map_linear_state_to_vault_status("Done", "completed")
        print(f"  'Done' (completed) → '{status}'")
        assert status == "Done"
        status = sync.map_linear_state_to_vault_status("In Progress", "started")
        print(f"  'In Progress' (started) → '{status}'")
        assert status == "In Progress"
        status = sync.map_linear_state_to_vault_status("Backlog", "backlog")
        print(f"  'Backlog' (backlog) → '{status}'")
        assert status == "Backlog"
        print("  ✓ Test 2 passed")

        # Test 3: Find note by linear_id
        print("\n--- Test 3: Find Note by linear_id ---")
        found_path = sync.find_note_by_linear_id("test-issue-123")
        print(f"  Found: {found_path}")
        assert found_path == test_note_path
        print("  ✓ Test 3 passed")

        # Test 4: Get current status
        print("\n--- Test 4: Get Current Status ---")
        current = sync.get_current_status(test_note_path)
        print(f"  Current status: '{current}'")
        assert current == "Todo"
        print("  ✓ Test 4 passed")

        # Test 5: Update local note
        print("\n--- Test 5: Update Local Note ---")
        result = sync.update_local_note(test_payload)
        print(f"  Update result: {result}")
        assert result is True

        # Verify the update
        metadata = sync.vault_utils.read_note_frontmatter(test_note_path)
        new_status = metadata.get("status")
        print(f"  New status: '{new_status}'")
        assert new_status == "Done"
        print("  ✓ Test 5 passed")

        # Test 6: No-change scenario
        print("\n--- Test 6: No-Change Scenario ---")
        same_payload = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "test-issue-123",
                "identifier": "TEST-123",
                "state": {"name": "Done", "type": "completed"},
            },
        }
        result = sync.update_local_note(same_payload)
        print(f"  No-change result: {result}")
        assert result is True  # Should return True (success, no change needed)
        print("  ✓ Test 6 passed")

        # Test 7: File not found scenario
        print("\n--- Test 7: File Not Found Scenario ---")
        not_found_payload = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "non-existent-issue",
                "identifier": "NON-EXISTENT",
                "state": {"name": "Done", "type": "completed"},
            },
        }
        try:
            sync.update_local_note(not_found_payload)
            print("  ✗ Expected FileNotFoundError")
            assert False
        except FileNotFoundError:
            print("  ✓ FileNotFoundError raised correctly")
        print("  ✓ Test 7 passed")

        print("\n" + "=" * 50)
        print("[✓] All LinearSync tests passed!")
        print("=" * 50)
