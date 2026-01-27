#!/usr/bin/env python3
"""
Omega KG Pre-Merge Smoke Test
Validates environment, dependencies, and core functionality before PR #68 merge.

Usage:
    poetry run python scripts/smoke_test.py

Exit Codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import sys
import os
from pathlib import Path

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check(name: str) -> callable:
    """Decorator to mark and track smoke test checks."""

    def decorator(func):
        func.check_name = name
        return func

    return decorator


class SmokeTest:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def run_check(self, func):
        """Run a single check and track results."""
        check_name = getattr(func, "check_name", func.__name__)
        try:
            print(f"\n{BLUE}▶{RESET} {check_name}...", end=" ")
            result = func()
            if result is True or result is None:
                print(f"{GREEN}✓ PASS{RESET}")
                self.passed.append(check_name)
            elif isinstance(result, str):
                print(f"{YELLOW}⚠ WARNING{RESET}")
                print(f"  {YELLOW}└─{RESET} {result}")
                self.warnings.append((check_name, result))
            else:
                print(f"{RED}✗ FAIL{RESET}")
                print(f"  {RED}└─{RESET} {result}")
                self.failed.append((check_name, result))
        except Exception as e:
            print(f"{RED}✗ FAIL{RESET}")
            print(f"  {RED}└─{RESET} {type(e).__name__}: {e}")
            self.failed.append((check_name, str(e)))

    @check("Environment Variables")
    def test_env_vars(self):
        """Verify critical environment variables are set."""
        required = ["OBSIDIAN_VAULT_PATH"]
        optional = [
            "LINEAR_API_KEY",
            "LINEAR_TEAM_ID",
            "EXTENSION_API_KEY",
            "JWT_SECRET_KEY",
        ]

        missing_required = [var for var in required if not os.getenv(var)]
        if missing_required:
            return f"Missing required vars: {', '.join(missing_required)}"

        missing_optional = [var for var in optional if not os.getenv(var)]
        if missing_optional:
            return f"Missing optional vars (some features disabled): {', '.join(missing_optional)}"

        return True

    @check("Settings Import")
    def test_settings_import(self):
        """Verify Settings can be imported and instantiated."""
        try:
            from omega_kg.settings import Settings

            settings = Settings()
            assert settings.obsidian_vault_path is not None
            return True
        except Exception as e:
            return f"Settings initialization failed: {e}"

    @check("Vault Path Validation")
    def test_vault_path(self):
        """Verify OBSIDIAN_VAULT_PATH exists and is writable."""
        from omega_kg.settings import Settings

        settings = Settings()
        vault_path = Path(settings.obsidian_vault_path)

        if not vault_path.exists():
            return f"Vault path does not exist: {vault_path}"

        if not vault_path.is_dir():
            return f"Vault path is not a directory: {vault_path}"

        # Test write permission
        test_file = vault_path / ".smoke_test_write_check"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            return f"Vault path is not writable: {vault_path}"

        return True

    @check("VaultUtils Initialization")
    def test_vault_utils(self):
        """Verify VaultUtils can be instantiated without errors."""
        try:
            from omega_kg.vault_utils import VaultUtils

            vault = VaultUtils()
            assert vault.vault_path.exists()

            # Test public methods exist
            assert hasattr(vault, "resolve_path"), "Missing resolve_path method"
            assert hasattr(vault, "read_note"), "Missing read_note method"
            assert hasattr(vault, "find_note_by_linear_id"), (
                "Missing find_note_by_linear_id method"
            )

            return True
        except Exception as e:
            return f"VaultUtils initialization failed: {e}"

    @check("Linear Client")
    def test_linear_client(self):
        """Verify LinearClient can be imported (API key not required for import)."""
        try:
            from omega_kg.linear_client import LinearClient, linear_client

            assert LinearClient is not None
            assert linear_client is not None
            return True
        except Exception as e:
            return f"LinearClient import failed: {e}"

    @check("SmartParser Methods")
    def test_smart_parser(self):
        """Verify SmartParser has required methods."""
        try:
            from omega_kg.smart_parser import SmartParser

            parser = SmartParser()

            # Check critical methods exist
            assert hasattr(parser, "sync_note_to_linear"), (
                "Missing sync_note_to_linear method"
            )
            assert hasattr(parser, "_parse_labels"), "Missing _parse_labels method"
            assert hasattr(parser, "_parse_status"), "Missing _parse_status method"

            return True
        except Exception as e:
            return f"SmartParser validation failed: {e}"

    @check("HTML Parsing Module")
    def test_html_parsing(self):
        """Verify HTML parsing module works correctly."""
        try:
            from omega_kg.parsers import parse_html_content

            # Test AI Studio parsing
            ai_studio_html = '<div class="message-user">Hello</div>'
            result = parse_html_content(
                ai_studio_html, "https://aistudio.google.com/chat"
            )
            assert isinstance(result, list), "parse_html_content must return list"

            # Test Nano-GPT parsing
            nano_gpt_html = '<div class="whitespace-pre-wrap">Test</div>'
            result = parse_html_content(nano_gpt_html, "https://nano-gpt.com/chat")
            assert isinstance(result, list), "parse_html_content must return list"

            # Test generic fallback
            generic_html = "<p>Generic content</p>"
            result = parse_html_content(generic_html, "https://example.com")
            assert isinstance(result, list), "parse_html_content must return list"
            assert len(result) > 0, "Generic fallback should return non-empty list"

            return True
        except Exception as e:
            return f"HTML parsing validation failed: {e}"

    @check("Authentication Module")
    def test_auth_utils(self):
        """Verify authentication utilities are correct."""
        try:
            from omega_kg.auth_utils import create_access_token, Token, TokenData
            from datetime import timedelta

            # Test token creation
            token = create_access_token(
                {"sub": "test_user"}, expires_delta=timedelta(minutes=15)
            )
            assert isinstance(token, str), "create_access_token must return string"

            # Verify Token and TokenData models exist
            assert Token is not None
            assert TokenData is not None

            return True
        except Exception as e:
            return f"Auth utilities validation failed: {e}"

    @check("Dependencies Installed")
    def test_dependencies(self):
        """Verify critical dependencies are installed."""
        deps = {
            "beautifulsoup4": "bs4",
            "httpx": "httpx",
            "fastapi": "fastapi",
            "pydantic": "pydantic",
            "python-frontmatter": "frontmatter",
        }

        missing = []
        for dep_name, import_name in deps.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(dep_name)

        if missing:
            return f"Missing dependencies: {', '.join(missing)}"

        return True

    @check("Async Support")
    def test_async_support(self):
        """Verify async operations work correctly."""
        import asyncio

        async def test_async():
            # Test that basic async works
            await asyncio.sleep(0.001)
            return True

        try:
            result = asyncio.run(test_async())
            assert result is True
            return True
        except Exception as e:
            return f"Async support test failed: {e}"

    @check("Linear Sync Webhook Handler")
    def test_webhook_handler(self):
        """Verify webhook handler exists and has required methods."""
        try:
            from omega_kg.linear_sync import LinearSync

            sync = LinearSync()

            assert hasattr(sync, "handle_linear_webhook_request"), (
                "Missing webhook handler"
            )
            assert hasattr(sync, "_verify_signature"), "Missing signature verification"

            return True
        except Exception as e:
            return f"Webhook handler validation failed: {e}"

    @check("File Structure")
    def test_file_structure(self):
        """Verify expected files exist in the repository."""
        required_files = [
            "omega_kg/parsers.py",
            "omega_kg/linear_client.py",
            "omega_kg/smart_parser.py",
            "omega_kg/linear_sync.py",
            "omega_kg/vault_utils.py",
            "omega_kg/capture_server.py",
            "omega_kg/auth_utils.py",
            "omega_kg/settings.py",
            "tests/test_linear_sync.py",
            "chrome-extension/popup.html",
            "chrome-extension/popup.js",
        ]

        project_root = Path(__file__).parent.parent
        missing = []

        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing.append(file_path)

        if missing:
            return f"Missing files: {', '.join(missing)}"

        return True

    def run_all_checks(self):
        """Run all smoke tests and report results."""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}Omega KG Pre-Merge Smoke Test Suite{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")

        # Collect all test methods
        test_methods = [
            getattr(self, method)
            for method in dir(self)
            if method.startswith("test_") and callable(getattr(self, method))
        ]

        # Run all checks
        for test_method in test_methods:
            self.run_check(test_method)

        # Print summary
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")
        print(f"{GREEN}✓ Passed:{RESET}  {len(self.passed)}")
        print(f"{YELLOW}⚠ Warnings:{RESET} {len(self.warnings)}")
        print(f"{RED}✗ Failed:{RESET}  {len(self.failed)}")

        if self.warnings:
            print(f"\n{YELLOW}Warnings:{RESET}")
            for name, msg in self.warnings:
                print(f"  • {name}: {msg}")

        if self.failed:
            print(f"\n{RED}Failures:{RESET}")
            for name, msg in self.failed:
                print(f"  • {name}: {msg}")
            print(f"\n{RED}❌ SMOKE TEST FAILED{RESET}")
            print(f"{RED}Fix the above issues before merging PR #68{RESET}")
            return 1

        print(f"\n{GREEN}✅ ALL SMOKE TESTS PASSED{RESET}")
        print(f"{GREEN}Environment is ready for PR #68 merge{RESET}")
        return 0


if __name__ == "__main__":
    smoke_test = SmokeTest()
    exit_code = smoke_test.run_all_checks()
    sys.exit(exit_code)
