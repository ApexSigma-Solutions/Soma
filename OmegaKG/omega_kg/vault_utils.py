"""
Omega_KG Vault Utilities (vault_utils.py)

This module acts as the "Filesystem Adapter" for the application.
Its only responsibility is to safely read and write frontmatter
to Markdown files in the Obsidian vault.

It imports the 'settings' object from omega_kg.settings to get the
vault path.
"""

import logging
from pathlib import Path
import frontmatter
from omega_kg.settings import settings
from typing import Any, Mapping, Dict, Optional

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class VaultUtils:
    """
    A class to handle safe read/write operations on the Obsidian vault.
    """

    def __init__(self, vault_path: str | Path = settings.obsidian_vault_path):
        """
        Initializes the VaultUtils with the path to the Obsidian vault.

        Args:
            vault_path (str | Path): The path to the Obsidian vault.
                                     Defaults to settings.obsidian_vault_path.

        Raises:
            ValueError: If the vault_path is not a valid directory.
        """
        if not vault_path:
            error_msg = (
                "[X] FAILURE: Obsidian vault path is not set. "
                "Please set OBSIDIAN_VAULT_PATH environment variable."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.vault_path = Path(vault_path)

        if not self.vault_path.exists():
            error_msg = (
                f"[X] FAILURE: Obsidian vault path does not exist: {self.vault_path}\n"
                f"Please create the directory or update OBSIDIAN_VAULT_PATH."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not self.vault_path.is_dir():
            error_msg = (
                f"[X] FAILURE: Obsidian vault path is not a directory: {self.vault_path}\n"
                f"Expected a directory, got a file."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"VaultUtils initialized. Vault path: {self.vault_path}")

    def resolve_path(self, note_path: str | Path) -> Path:
        """
        Resolves a given path to an absolute path within the vault.

        If 'note_path' is already absolute, it's used as is.
        If it's relative, it's joined with the vault root.

        Args:
            note_path (str | Path): The relative or absolute path to the note.

        Returns:
            Path: The resolved, absolute path to the note.
        """
        note_file = Path(note_path)
        if note_file.is_absolute():
            return note_file
        else:
            return self.vault_path / note_file

    def read_note_frontmatter(self, note_path: str | Path) -> Dict[str, Any]:
        """
        Safely reads the frontmatter from a specified note.

        Args:
            note_path (str | Path): The path to the note (relative to the vault
                                     or absolute).

        Returns:
            Dict[str, Any]: The note's frontmatter. Returns empty dict if file not found
                            or has no frontmatter.
        """
        resolved_path = self.resolve_path(note_path)

        if not resolved_path.is_file():
            logger.warning(f"File not found: {resolved_path}")
            return {}

        try:
            with resolved_path.open("r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                return post.metadata
        except OSError as e:
            logger.error(
                f"Failed to read or parse frontmatter from {resolved_path}: {e}"
            )
            return {}

    def update_note_frontmatter(
        self, note_path: str | Path, updates: Mapping[str, Any]
    ) -> bool:
        """
        Safely updates the frontmatter of a specified note.

        Reads the entire note, merges the 'updates' mapping into the
        existing frontmatter (overwriting keys if they exist), and then
        writes the entire note back to disk.

        Args:
            note_path (str | Path): The path to the note (relative or absolute).
            updates (Mapping[str, Any]): A mapping of key-value pairs to
                                         add or overwrite in the frontmatter.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        resolved_path = self.resolve_path(note_path)

        if not resolved_path.is_file():
            logger.error(f"Cannot update frontmatter, file not found: {resolved_path}")
            return False

        try:
            # Read the entire file as a string first to be safe
            content_str = resolved_path.read_text(encoding="utf-8")
            post = frontmatter.loads(content_str)

            # Update the metadata
            post.metadata.update(updates)

            # Write the entire post back
            with resolved_path.open("w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            logger.info(f"Successfully updated frontmatter for: {resolved_path.name}")
            return True

        except OSError as e:
            logger.error(f"Failed to write updated frontmatter to {resolved_path}: {e}")
            return False

    def find_note_by_linear_id(self, linear_id: str) -> Optional[Path]:
        """
        Scans the vault for a note with the matching 'linear_id' in frontmatter.

        Args:
            linear_id (str): The Linear Issue ID to search for.

        Returns:
            Optional[Path]: The path to the matching note, or None if not found.
        """
        # Iterate over all .md files in the vault
        # rglob is recursive
        for note_path in self.vault_path.rglob("*.md"):
            try:
                # Parse frontmatter once (removed fragile 2KB heuristic)
                metadata = self.read_note_frontmatter(note_path)
                if metadata and str(metadata.get("linear_id")) == linear_id:
                    logger.info(
                        f"Found matching note for linear_id {linear_id}: {note_path}"
                    )
                    return note_path

            except Exception as e:
                logger.warning(f"Error scanning {note_path} for linear_id: {e}")
                continue

        logger.info(f"No note found for linear_id: {linear_id}")
        return None


# -----------------------------------------------------------------------------
# TEST HARNESS
#
# To run this test:
# 1. Create a dummy file: 'my_test_note.md' in your vault root
#    with some frontmatter (e.g., ---
#                                status: draft
#                                ---
#                                My note content)
# 2. Run: poetry run python omega_kg/vault_utils.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    print("[TEST] Running VaultUtils Test Harness - vault_utils.py:146")

    try:
        # --- CONFIGURATION ---
        # This file MUST exist in your vault root for the test to run
        TEST_NOTE_PATH = "my_test_note.md"

        # Ensure the vault path is set and valid before instantiating VaultUtils
        vault_path = getattr(settings, "obsidian_vault_path", None)

        # Defensive check as requested
        if not vault_path or not Path(vault_path).is_dir():
            msg = (
                f"[X] FAILURE: settings.obsidian_vault_path is not set or is not a "
                f"valid directory: {vault_path}"
            )
            print(msg)
            exit(1)

        utils = VaultUtils(vault_path)
        test_file_abs = utils.resolve_path(TEST_NOTE_PATH)

        if not test_file_abs.is_file():
            print(f"[X] FAILURE: Test file not found at {test_file_abs}")
            print(
                f"Please create '{TEST_NOTE_PATH}' in your vault root to run this test."
            )
            # Create it automatically if missing to be helpful in local dev
            try:
                print(f"Attempting to create dummy test file at {test_file_abs}...")
                with open(test_file_abs, "w") as f:
                    f.write(
                        "---\nstatus: draft\n---\n# Test Note\nAuto-created by test harness."
                    )
                print("✓ Created dummy test file.")
            except Exception as e:
                print(f"Failed to create test file: {e}")
                exit(1)

        print(f"Testing against: {test_file_abs}")

        # 1. Test Read
        print("\n Testing Read - vault_utils.py:169")
        metadata: Dict[str, Any] = utils.read_note_frontmatter(TEST_NOTE_PATH)
        print(f"Original metadata: {metadata} - vault_utils.py:171")

        # 2. Test Write
        print("\n Testing Write - vault_utils.py:174")
        new_data = {
            "linear_id": f"test_id_{int(time.time())}",
            "status": "active",
            "new_key": 123,
        }
        print(f"Applying updates: {new_data} - vault_utils.py:180")

        success = utils.update_note_frontmatter(TEST_NOTE_PATH, new_data)

        if not success:
            raise ValueError("update_note_frontmatter returned False")

        # 3. Test Verify
        print("\n Testing Verify - vault_utils.py:188")
        updated_metadata: Dict[str, Any] = utils.read_note_frontmatter(TEST_NOTE_PATH)
        print(f"Updated metadata: {updated_metadata} - vault_utils.py:190")

        # Assertions (simplified to avoid type checker issues)
        assert updated_metadata["linear_id"] == new_data["linear_id"]
        assert updated_metadata["status"] == "active"
        assert updated_metadata["new_key"] == 123

        print("\n - vault_utils.py:197" + "=" * 40)
        print("[✓] SUCCESS: VaultUtils test passed! - vault_utils.py:198")
        print("= - vault_utils.py:199" * 40 + "" + "\n")
    except (ValueError, OSError, AssertionError) as e:
        import traceback

        print("\n - vault_utils.py:202" + "!" * 40)
        print("[X] FAILURE: VaultUtils Test Harness FAILED - vault_utils.py:203")
        print(f"Error: {e} - vault_utils.py:204")
        traceback.print_exc()
        print("= - vault_utils.py:206" * 40 + "" + "\n")
