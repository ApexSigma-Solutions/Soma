#!/usr/bin/env python3
"""
Automated Housekeeping Script for Omega KG Root Directory

This script performs routine maintenance on the root directory by:
1. Moving diagnostic reports to docs/ folder
2. Organizing temporary and log files
3. Cleaning up empty directories
4. Staging and committing changes to git

Usage:
    python scripts/housekeeping.py [--dry-run] [--commit] [--push]
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HousekeepingManager:
    """Manages automated housekeeping tasks."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.root_dir = Path.cwd()
        self.actions = []
        self.changes_made = False

    def log_action(self, action: str):
        """Log an action that will be performed."""
        status = "[DRY RUN] " if self.dry_run else ""
        print(f"{status}{action}")
        self.actions.append(action)

    def move_file(self, src: Path, dst: Path, description: str):
        """Move a file to a new location."""
        if not src.exists():
            print(f"[SKIP] Source file does not exist: {src}")
            return

        if dst.exists():
            print(f"[SKIP] Destination already exists: {dst}")
            return

        if self.dry_run:
            self.log_action(f"Would move: {src} → {dst} ({description})")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            self.log_action(f"Moved: {src} → {dst} ({description})")
            self.changes_made = True

    def clean_temp_dir(self, temp_dir: Path, description: str):
        """Clean a temporary directory while preserving structure."""
        if not temp_dir.exists():
            print(f"[SKIP] Directory does not exist: {temp_dir}")
            return

        # List contents before cleaning
        contents = list(temp_dir.iterdir())

        if not contents:
            print(f"[SKIP] Directory already empty: {temp_dir}")
            return

        if self.dry_run:
            files_count = len([p for p in contents if p.is_file()])
            dirs_count = len([p for p in contents if p.is_dir()])
            self.log_action(
                f"Would clean: {temp_dir} ({files_count} files, {dirs_count} dirs) - {description}"
            )
        else:
            # Clean directory contents
            for item in contents:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            # Create .gitkeep to preserve directory
            gitkeep = temp_dir / ".gitkeep"
            gitkeep.write_text(f"# Temporary working directory for {description}\n")

            self.log_action(f"Cleaned: {temp_dir} ({description})")
            self.changes_made = True

    def check_and_move_diagnostics(self):
        """Find and move diagnostic reports from root to docs/."""
        print("\n=== Checking for diagnostic files in root directory ===")

        # Files to look for in root
        diagnostic_patterns = [
            ("diagnostic_health_report.json", "docs/"),
            ("*_diagnostic_*.json", "docs/"),
            ("*_health_*.json", "docs/"),
            ("*_audit_*.json", "docs/"),
            ("*.log", "logs/"),
            ("*_report.md", "docs/"),
        ]

        root_files = list(self.root_dir.glob("*.json")) + list(
            self.root_dir.glob("*.md")
        )

        for file_path in root_files:
            for pattern, dest_dir in diagnostic_patterns:
                # Check if file matches pattern (simple contains check)
                if pattern.replace("*", "") in file_path.name:
                    dest_path = self.root_dir / dest_dir / file_path.name
                    self.move_file(file_path, dest_path, "diagnostic report")
                    break

    def organize_temp_directories(self):
        """Clean temporary working directories."""
        print("\n=== Cleaning temporary directories ===")

        temp_dirs = [
            (self.root_dir / ".omegakg_temp", "Omega KG development"),
            (self.root_dir / ".temp", "temporary files"),
        ]

        for temp_dir, description in temp_dirs:
            self.clean_temp_dir(temp_dir, description)

    def check_for_orphaned_files(self):
        """Find orphaned files that should be organized."""
        print("\n=== Checking for orphaned files ===")

        # Check for common orphaned file patterns
        orphaned_patterns = [
            "*.pyc",
            "__pycache__",
            "*.tmp",
            "*.bak",
        ]

        for pattern in orphaned_patterns:
            matches = list(self.root_dir.glob(pattern))
            if matches:
                print(f"Found {len(matches)} items matching '{pattern}'")

    def stage_and_commit(self, commit: bool = False, push: bool = False):
        """Stage and commit changes using git."""
        if not self.changes_made and not self.dry_run:
            print("\n[INFO] No changes to commit")
            return

        if self.dry_run and commit:
            self.log_action("Would stage and commit changes to git")
            return

        if not commit:
            print("\n[INFO] Skipping git operations (use --commit to enable)")
            return

        print("\n=== Git Operations ===")

        try:
            import subprocess

            # Check git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )

            if not result.stdout.strip():
                print("[INFO] No changes to commit")
                return

            # Add changes
            subprocess.run(["git", "add", "-A"], cwd=self.root_dir, check=True)
            self.log_action("Staged changes")

            # Create commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"""housekeeping: automated root directory maintenance

- Organized diagnostic reports and documentation
- Cleaned temporary working directories
- Maintained proper directory structure

Timestamp: {timestamp}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg], cwd=self.root_dir, check=True
            )
            self.log_action("Committed changes to git")

            # Push if requested
            if push:
                subprocess.run(
                    ["git", "push", "origin", "beta"], cwd=self.root_dir, check=True
                )
                self.log_action("Pushed to origin/beta")

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Git operation failed: {e}")
            return

    def generate_report(self):
        """Generate a housekeeping report."""
        print("\n" + "=" * 80)
        print("HOUSEKEEPING REPORT")
        print("=" * 80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Working Directory: {self.root_dir}")

        if self.actions:
            print(f"\nActions Performed ({len(self.actions)}):")
            for i, action in enumerate(self.actions, 1):
                print(f"  {i}. {action}")
        else:
            print("\nNo actions performed")

        if self.changes_made:
            print("\n[OK] Changes were made to the repository")
        else:
            print("\n[INFO] No changes were made")

        print("=" * 80)

    def run(self, commit: bool = False, push: bool = False):
        """Run the complete housekeeping process."""
        print("=" * 80)
        print("OMEGA KG ROOT DIRECTORY HOUSEKEEPING")
        print("=" * 80)

        # Perform housekeeping tasks
        self.check_and_move_diagnostics()
        self.organize_temp_directories()
        self.check_for_orphaned_files()

        # Git operations
        self.stage_and_commit(commit=commit, push=push)

        # Generate report
        self.generate_report()

        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated housekeeping for Omega KG root directory"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--commit", action="store_true", help="Stage and commit changes to git"
    )

    parser.add_argument(
        "--push",
        action="store_true",
        help="Push changes to remote repository (implies --commit)",
    )

    args = parser.parse_args()

    # Push implies commit
    if args.push:
        args.commit = True

    # Run housekeeping
    manager = HousekeepingManager(dry_run=args.dry_run)
    return manager.run(commit=args.commit, push=args.push)


if __name__ == "__main__":
    sys.exit(main())
