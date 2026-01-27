#!/usr/bin/env python3
"""
Repository Inventory & Dependency Scan Script
=============================================

Automated analysis tool for Phase 1 Discovery & Baseline.
Scans for: Ghost Tests, config fragmentation, hardcoded credentials, legacy references.

Usage:
    python scripts/analyze_repository.py [--output reports/repository_inventory.json]

Author: SigmaDev11
Date: 2025-12-12
Version: 1.0
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone


class RepositoryAnalyzer:
    """Comprehensive repository analysis for Omega_KG Core hardening."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.results: Dict[str, Any] = {
            "scan_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "root_path": str(self.root_path),
                "version": "1.0",
            },
            "ghost_tests": [],
            "config_fragmentation": [],
            "hardcoded_secrets": [],
            "legacy_references": [],
            "file_statistics": {},
            "dependency_analysis": {},
        }

        # Patterns for detection
        self.ghost_test_patterns = [
            r"\.ignore[/\\]",
            r"__pycache__",
            r"\.pytest_cache",
            r"node_modules",
        ]

        self.secret_patterns = [
            r"(?i)(password|pwd|pass)\s*[:=]\s*['\"][^'\"]{3,}",
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][^'\"]{10,}",
            r"(?i)(secret|token|jwt)\s*[:=]\s*['\"][^'\"]{8,}",
            r"(?i)(private[_-]?key|privatekey)\s*[:=]\s*['\"][^'\"]{20,}",
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
            r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
        ]

        self.legacy_patterns = [
            r"(?i)memos",
            r"(?i)ingest[_-]?llm",
            r"(?i)memos\.ai",
            r"(?i)ingest_llm",
            r"(?i)memos_ai",
        ]

        self.config_files = [
            "pytest.ini",
            "pyproject.toml",
            "setup.cfg",
            ".env",
            ".env.example",
            "docker-compose.yml",
            "docker-compose.override.yml",
        ]

    def scan_repository(self) -> Dict[str, Any]:
        """Execute complete repository scan."""
        print("🔍 Starting Repository Inventory & Dependency Scan...")
        print(f"📁 Root Path: {self.root_path}")

        # Phase 1: File system inventory
        self._scan_file_system()

        # Phase 2: Ghost tests detection
        self._scan_ghost_tests()

        # Phase 3: Config fragmentation
        self._scan_config_fragmentation()

        # Phase 4: Hardcoded secrets
        self._scan_hardcoded_secrets()

        # Phase 5: Legacy references
        self._scan_legacy_references()

        # Phase 6: Dependency analysis
        self._analyze_dependencies()

        print("✅ Repository scan completed successfully!")
        return self.results

    def _scan_file_system(self):
        """Generate file system statistics."""
        print("📊 Scanning file system...")

        file_types: Dict[str, int] = {}
        total_files = 0
        total_lines = 0

        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                total_files += 1
                ext = file_path.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1

                # Count lines for text files
                try:
                    if ext in [
                        ".py",
                        ".md",
                        ".json",
                        ".yaml",
                        ".yml",
                        ".toml",
                        ".ini",
                        ".cfg",
                    ]:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            lines = len(f.readlines())
                            total_lines += lines
                except Exception:
                    pass

        self.results["file_statistics"] = {
            "total_files": total_files,
            "total_lines": total_lines,
            "file_types": file_types,
            "directories": len(list(self.root_path.iterdir())),
        }

        print(
            f"   📈 Files: {total_files}, Lines: {total_lines}, Extensions: {len(file_types)}"
        )

    def _scan_ghost_tests(self):
        """Detect "Ghost Tests" in .ignore directories and other hidden locations."""
        print("👻 Scanning for Ghost Tests...")

        ghost_locations: List[str] = []

        # Find .ignore directories
        for ignore_dir in self.root_path.rglob(".ignore"):
            if ignore_dir.is_dir():
                ghost_locations.append(str(ignore_dir))
                # Scan for test files within
                for test_file in ignore_dir.rglob("*test*.py"):
                    ghost_locations.append(f"  - {test_file}")

        # Find other potential ghost locations
        potential_ghosts = [
            "tests/.ignore",
            "test/.ignore",
            ".ignore/",
            "__pycache__/",
            ".pytest_cache/",
        ]

        for location in potential_ghosts:
            path = self.root_path / location
            if path.exists():
                ghost_locations.append(f"⚠️  Potential ghost location: {path}")

        self.results["ghost_tests"] = ghost_locations
        print(f"   📋 Found {len(ghost_locations)} potential ghost test locations")

    def _scan_config_fragmentation(self):
        """Detect multiple configuration files that may cause conflicts."""
        print("🔧 Scanning for config fragmentation...")

        config_files_found: List[Dict[str, Any]] = []

        for config_file in self.config_files:
            for path in self.root_path.rglob(config_file):
                config_files_found.append(
                    {
                        "file": str(path),
                        "size": path.stat().st_size if path.exists() else 0,
                        "modified": datetime.fromtimestamp(
                            path.stat().st_mtime
                        ).isoformat(),
                    }
                )

        # Check for multiple pytest.ini files
        pytest_files = [f for f in config_files_found if "pytest.ini" in f["file"]]

        self.results["config_fragmentation"] = {
            "total_config_files": len(config_files_found),
            "pytest_ini_files": pytest_files,
            "all_config_files": config_files_found,
            "fragmentation_detected": len(pytest_files) > 1,
        }

        print(
            f"   📄 Found {len(config_files_found)} config files, {len(pytest_files)} pytest.ini files"
        )

    def _scan_hardcoded_secrets(self):
        """Scan for hardcoded secrets and credentials."""
        print("🔒 Scanning for hardcoded secrets...")

        secrets_found: List[Dict[str, Any]] = []

        for py_file in self.root_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                    for line_num, line in enumerate(lines, 1):
                        for pattern in self.secret_patterns:
                            if re.search(pattern, line):
                                secrets_found.append(
                                    {
                                        "file": str(py_file),
                                        "line": line_num,
                                        "content": line.strip(),
                                        "pattern": pattern,
                                    }
                                )
            except Exception as e:
                print(f"   ⚠️  Could not read {py_file}: {e}")

        self.results["hardcoded_secrets"] = secrets_found
        print(f"   🔑 Found {len(secrets_found)} potential hardcoded secrets")

    def _scan_legacy_references(self):
        """Scan for legacy references to memos and ingest_llm."""
        print("🗂️  Scanning for legacy references...")

        legacy_found: List[Dict[str, Any]] = []

        # Scan all text files
        text_extensions = {
            ".py",
            ".md",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".txt",
        }

        for file_path in self.root_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")

                        for line_num, line in enumerate(lines, 1):
                            for pattern in self.legacy_patterns:
                                if re.search(pattern, line):
                                    legacy_found.append(
                                        {
                                            "file": str(file_path),
                                            "line": line_num,
                                            "content": line.strip(),
                                            "pattern": pattern,
                                        }
                                    )
                except Exception as e:
                    print(f"   ⚠️  Could not read {file_path}: {e}")

        self.results["legacy_references"] = legacy_found
        print(f"   📜 Found {len(legacy_found)} legacy references")

    def _analyze_dependencies(self):
        """Analyze Python dependencies and potential security issues."""
        print("📦 Analyzing dependencies...")

        # Check for pyproject.toml
        pyproject_path = self.root_path / "pyproject.toml"
        poetry_deps: Dict[str, Any] = {}

        if pyproject_path.exists():
            try:
                import tomllib

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    poetry_deps = (
                        data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                    )
            except ImportError:
                print("   ⚠️  tomllib not available, skipping pyproject.toml analysis")
            except Exception as e:
                print(f"   ⚠️  Could not parse pyproject.toml: {e}")

        # Check for requirements files
        requirements_files = list(self.root_path.glob("requirements*.txt"))

        self.results["dependency_analysis"] = {
            "poetry_dependencies": poetry_deps,
            "requirements_files": [str(f) for f in requirements_files],
            "total_dependencies": len(poetry_deps),
        }

        print(f"   📊 Found {len(poetry_deps)} Poetry dependencies")

    def save_results(self, output_path: str = "reports/repository_inventory.json"):
        """Save scan results to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"💾 Results saved to: {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Repository Inventory & Dependency Scan"
    )
    parser.add_argument(
        "--root", default=".", help="Repository root path (default: current directory)"
    )
    parser.add_argument(
        "--output", default="reports/repository_inventory.json", help="Output file path"
    )

    args = parser.parse_args()

    try:
        analyzer = RepositoryAnalyzer(args.root)
        results = analyzer.scan_repository()
        analyzer.save_results(args.output)

        # Print summary
        print("\n" + "=" * 60)
        print("📋 PHASE 1 - TASK 1.1 SUMMARY")
        print("=" * 60)
        print(f"📁 Repository: {results['scan_metadata']['root_path']}")
        print(f"⏰ Scan Time: {results['scan_metadata']['timestamp']}")
        print(f"📄 Files Scanned: {results['file_statistics']['total_files']}")
        print(f"🔒 Secrets Found: {len(results['hardcoded_secrets'])}")
        print(f"👻 Ghost Tests: {len(results['ghost_tests'])}")
        print(
            f"🔧 Config Fragmentation: {'Yes' if results['config_fragmentation']['fragmentation_detected'] else 'No'}"
        )
        legacy_refs = results.get("legacy_references", [])
        print(f"📜 Legacy References: {len(legacy_refs)}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"❌ Error during scan: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
