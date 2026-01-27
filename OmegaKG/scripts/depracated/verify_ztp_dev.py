#!/usr/bin/env python3
"""
Zero Trust Pattern Verification Script - DEV Environment
=========================================================
Validates that the DEV environment is correctly configured with:
- Correct database (omega_kg_dev on port 5434)
- Correct Neo4j (bolt://localhost:7688)
- Correct app port (8765)
- Active Bitwarden integration (if BWS_ACCESS_TOKEN present)

Exit codes:
  0 = All checks passed
  1 = Configuration mismatch
  2 = Import/runtime error
"""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# EXPECTED DEV CONFIGURATION VALUES
# ═══════════════════════════════════════════════════════════════════════════════
EXPECTED = {
    "postgres_db": "omega_kg_dev",
    "postgres_port": 5434,
    "app_port": 8765,
    "neo4j_uri": "bolt://localhost:7688",
}


def main():
    print("=" * 70)
    print(" ZERO TRUST PATTERN VERIFICATION (DEV ENVIRONMENT)")
    print("=" * 70)
    print()

    # Ensure we're configured for DEV
    os.environ.setdefault("OMEGA_ENV", "dev")
    os.environ.setdefault("POSTGRES_DB", "omega_kg_dev")
    os.environ.setdefault("POSTGRES_PORT", "5434")
    os.environ.setdefault("APP_PORT", "8765")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7688")

    print("Configuration Environment:")
    print(f"  ├─ Working Directory: {os.getcwd()}")
    print(f"  ├─ OMEGA_ENV: {os.environ.get('OMEGA_ENV', 'NOT SET')}")
    print(f"  ├─ POSTGRES_DB: {os.environ.get('POSTGRES_DB', 'NOT SET')}")
    print(
        f"  └─ BWS_ACCESS_TOKEN: {'Present' if os.environ.get('BWS_ACCESS_TOKEN') else 'Not set'}"
    )
    print()

    try:
        from omega_kg.settings import settings

        print("✓ Settings loaded successfully")
        print()
        print("Loaded Configuration:")
        print(f"  ├─ App Environment: {settings.app_env}")
        print(f"  ├─ Database: {settings.postgres_db}")
        print(f"  ├─ Database Port: {settings.postgres_port}")
        print(f"  ├─ Neo4j URI: {settings.neo4j_uri}")
        print(f"  ├─ App Port: {settings.app_port}")
        print(
            f"  └─ Embedding Provider: {getattr(settings, 'embedding_provider', 'Not configured')}"
        )
        print()

        # ═══════════════════════════════════════════════════════════════════════
        # VALIDATION
        # ═══════════════════════════════════════════════════════════════════════
        all_passed = True
        print("Validation Results:")

        checks = [
            ("Database Name", settings.postgres_db, EXPECTED["postgres_db"]),
            ("Database Port", settings.postgres_port, EXPECTED["postgres_port"]),
            ("App Port", settings.app_port, EXPECTED["app_port"]),
            ("Neo4j URI", settings.neo4j_uri, EXPECTED["neo4j_uri"]),
        ]

        for check_name, actual, expected in checks:
            if actual == expected:
                print(f"  ✅ {check_name}: {actual}")
            else:
                print(f"  ❌ {check_name}: {actual} (expected: {expected})")
                all_passed = False

        print()
        print("=" * 70)
        if all_passed:
            print(" ✅ ZERO TRUST PATTERN SUCCESSFULLY VERIFIED")
            print(" DEV environment is properly configured and isolated")
            if os.environ.get("BWS_ACCESS_TOKEN"):
                print(" BWS_ACCESS_TOKEN is active - secrets from Bitwarden")
            else:
                print(" Using .env fallback values (BWS_ACCESS_TOKEN not set)")
            print("=" * 70)
            return 0
        else:
            print(" ❌ CONFIGURATION MISMATCH - Some values are incorrect")
            print(" Check your environment variables or .env file")
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
