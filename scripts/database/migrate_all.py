"""
Soma Ecosystem Migration Manager

Manages Alembic migrations for all services in the ecosystem.
Provides rollback, status, and validation capabilities.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class MigrationManager:
    """Manages migrations across all Soma services."""

    def __init__(self, project_root: str = "D:\\projects\\Soma"):
        self.project_root = Path(project_root)
        self.services = {
            "InGress": "InGress",
            "InGest": "InGest",
            "OmegaKG": "OmegaKG",
            "memOS": "memOS",
        }

    def _get_poetry_command(self) -> str:
        """Get Poetry command or fallback to pip/python."""
        try:
            result = subprocess.run(
                ["poetry", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return "poetry"
        except FileNotFoundError:
            pass

        return "python"

    def _run_migration(
        self, service_name: str, action: str = "upgrade"
    ) -> subprocess.CompletedProcess:
        """
        Run migration for a specific service.

        Args:
            service_name: Name of the service (e.g., 'InGest')
            action: Migration action ('upgrade', 'downgrade', 'current', 'history')

        Returns:
            Subprocess result
        """
        service_path = self.project_root / self.services[service_name]
        alembic_ini = service_path / "alembic.ini"

        if not alembic_ini.exists():
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr=f"No alembic.ini found for {service_name}",
            )

        poetry_cmd = self._get_poetry_command()

        if poetry_cmd == "poetry":
            command = ["poetry", "run", "alembic", action]
            if action == "upgrade":
                command.append("head")
        else:
            command = ["python", "-m", "alembic", action]
            if action == "upgrade":
                command.append("head")

        print(f"\n{'=' * 60}")
        print(f"Running {action} for {service_name}")
        print(f"{'=' * 60}")
        print(f"Path: {service_path}")
        print(f"Command: {' '.join(command)}")

        result = subprocess.run(
            command, cwd=service_path, capture_output=True, text=True, timeout=120
        )

        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}", file=sys.stderr)

        if result.returncode == 0:
            print(f"✅ {action} completed successfully for {service_name}")
        else:
            print(
                f"❌ {action} failed for {service_name} (exit code: {result.returncode})"
            )

        return result

    def migrate_all(self, action: str = "upgrade") -> Dict[str, bool]:
        """
        Run migration for all services.

        Args:
            action: Migration action ('upgrade', 'downgrade', 'current')

        Returns:
            Dictionary of service names to success status
        """
        results = {}

        for service_name in self.services.keys():
            result = self._run_migration(service_name, action)
            results[service_name] = result.returncode == 0

        return results

    def migrate_service(self, service_name: str, action: str = "upgrade") -> bool:
        """
        Run migration for a specific service.

        Args:
            service_name: Name of the service
            action: Migration action

        Returns:
            True if successful, False otherwise
        """
        if service_name not in self.services:
            print(f"❌ Unknown service: {service_name}")
            print(f"Available services: {', '.join(self.services.keys())}")
            return False

        result = self._run_migration(service_name, action)
        return result.returncode == 0

    def status_all(self) -> None:
        """Show migration status for all services."""
        print("\n" + "=" * 60)
        print("Soma Ecosystem Migration Status")
        print("=" * 60)

        for service_name in self.services.keys():
            print(f"\n{service_name}:")
            result = self._run_migration(service_name, "current")

            if result.returncode == 0:
                print(f"  Current: {result.stdout.strip()}")
            else:
                print(f"  Error: {result.stderr.strip()}")

        print("\n" + "=" * 60)

    def validate_migrations(self) -> Dict[str, bool]:
        """
        Validate that all services have migrations configured.

        Returns:
            Dictionary of service names to validation status
        """
        print("\n" + "=" * 60)
        print("Validating Migration Configuration")
        print("=" * 60)

        results = {}

        for service_name, service_dir in self.services.items():
            service_path = self.project_root / service_dir
            alembic_ini = service_path / "alembic.ini"
            alembic_dir = service_path / "alembic"
            versions_dir = alembic_dir / "versions"

            has_config = alembic_ini.exists()
            has_dir = alembic_dir.exists()
            has_versions = versions_dir.exists() if has_dir else False

            version_count = 0
            if has_versions:
                version_count = len(list(versions_dir.glob("*.py")))

            valid = has_config and has_dir and has_versions and version_count > 0

            results[service_name] = valid

            status = "VALID" if valid else "INVALID"
            print(f"\n{status}: {service_name}")
            found_config = "Found" if has_config else "Missing"
            found_dir = "Found" if has_dir else "Missing"
            found_versions = "Found" if has_versions else "Missing"
            print(f"  alembic.ini: {found_config}")
            print(f"  alembic/: {found_dir}")
            print(f"  versions/: {found_versions}")
            print(f"  migrations: {version_count} file(s)")

        print("\n" + "=" * 60)
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Soma Ecosystem Migration Manager")

    subparsers = parser.add_subparsers(dest="action", help="Migration action")

    parser.add_argument(
        "--service", "-s", help="Specific service to migrate (default: all)"
    )

    parser.add_argument(
        "--project-root",
        "-r",
        default="D:\\projects\\Soma",
        help="Project root directory",
    )

    subparsers.add_parser("upgrade", help="Upgrade all services to latest migrations")
    subparsers.add_parser("downgrade", help="Downgrade migrations (one revision)")
    subparsers.add_parser("status", help="Show current migration status")
    subparsers.add_parser("validate", help="Validate migration configuration")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    manager = MigrationManager(args.project_root)

    if args.action == "upgrade":
        if args.service:
            success = manager.migrate_service(args.service, "upgrade")
            sys.exit(0 if success else 1)
        else:
            results = manager.migrate_all("upgrade")
            success_count = sum(1 for v in results.values() if v)
            print(f"\n{'=' * 60}")
            print(f"Summary: {success_count}/{len(results)} services upgraded")
            print(f"{'=' * 60}")
            sys.exit(0 if all(results.values()) else 1)

    elif args.action == "downgrade":
        if args.service:
            success = manager.migrate_service(args.service, "downgrade")
            sys.exit(0 if success else 1)
        else:
            results = manager.migrate_all("downgrade")
            sys.exit(0 if all(results.values()) else 1)

    elif args.action == "status":
        manager.status_all()

    elif args.action == "validate":
        results = manager.validate_migrations()
        success_count = sum(1 for v in results.values() if v)
        print(f"\n{'=' * 60}")
        print(f"Summary: {success_count}/{len(results)} services valid")
        print(f"{'=' * 60}")
        sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
