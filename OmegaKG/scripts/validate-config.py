#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Validator for Omega KG
Ensures all required configuration is present and valid.
"""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def check_env_file():
    """Verify .env file exists and has required variables."""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Run: cp .env.example .env")
        return False
    print("✓ .env file exists")
    return True


def check_required_vars():
    """Check for required environment variables."""
    required_vars = {
        "OBSIDIAN_VAULT_PATH": "Path to your Obsidian vault",
        "NEO4J_PASSWORD": "Neo4j database password",
        "POSTGRES_PASSWORD": "PostgreSQL database password",
        "EXTENSION_API_KEY_PRD": "Chrome extension API key",
        "JWT_SECRET_KEY": "JWT signing secret",
    }

    insecure_defaults = {
        "NEO4J_PASSWORD": "change_me_secure_password",
        "POSTGRES_PASSWORD": "omega_dev_password",
        "EXTENSION_API_KEY_PRD": "change_me_secure_api_key",
        "JWT_SECRET_KEY": "change_me_to_secure_random_string",
    }

    issues = []

    # Load .env file
    env_vars = {}
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value.strip('"').strip("'")

    print("\nChecking required variables:")
    for var, description in required_vars.items():
        if var not in env_vars or not env_vars[var]:
            print(f"❌ {var}: NOT SET - {description}")
            issues.append(var)
        elif var in insecure_defaults and env_vars[var] == insecure_defaults[var]:
            print(f"⚠️  {var}: USING DEFAULT VALUE - SECURITY RISK!")
            issues.append(var)
        else:
            print(f"✓ {var}: configured")

    return len(issues) == 0


def check_vault_path():
    """Verify Obsidian vault path is valid."""
    env_vars = {}
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value.strip('"').strip("'")

    vault_path = env_vars.get("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        print("\n❌ OBSIDIAN_VAULT_PATH not set in .env")
        return False

    vault_path = Path(vault_path.replace("\\\\", "\\"))
    if not vault_path.exists():
        print(f"\n❌ Vault path does not exist: {vault_path}")
        print("   Create the directory or update VAULT_PATH in .env")
        return False

    print(f"\n✓ Vault path exists: {vault_path}")

    # Check for required subdirectories
    required_dirs = ["Tasks", "AI_Conversations"]
    for dir_name in required_dirs:
        dir_path = vault_path / dir_name
        if not dir_path.exists():
            print(f"⚠️  Creating {dir_name} directory...")
            dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ {dir_name} directory exists")

    return True


def check_python_packages():
    """Verify required Python packages are installed."""
    try:
        import neo4j
        import fastapi
        import pydantic_settings

        print("\n✓ Core Python packages installed")
        return True
    except ImportError as e:
        print(f"\n❌ Missing Python package: {e}")
        print("   Run: poetry install")
        return False


def generate_secure_key():
    """Generate a secure random key."""
    import secrets

    return secrets.token_urlsafe(32)


def main():
    """Run all configuration checks."""
    print("=" * 60)
    print("Omega KG Configuration Validator")
    print("=" * 60)

    checks = [
        ("Environment File", check_env_file),
        ("Required Variables", check_required_vars),
        ("Vault Path", check_vault_path),
        ("Python Packages", check_python_packages),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Configuration Summary:")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False

    if not all_passed:
        print("\n⚠️  Configuration issues found!")
        print("\nTo fix security issues, generate secure keys:")
        print('python -c "import secrets; print(secrets.token_urlsafe(32))"')
        print("\nThen update your .env file with the generated values.")
        sys.exit(1)
    else:
        print("\n✓ Configuration is valid and secure!")
        sys.exit(0)


if __name__ == "__main__":
    main()
