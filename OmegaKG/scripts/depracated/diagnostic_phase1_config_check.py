#!/usr/bin/env python3
"""
Phase 1: Configuration and Environment Audit
Verifies all critical configuration settings and dependencies.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_kg.settings import settings
from omega_kg.database.session import engine
import asyncpg
import asyncio


async def check_postgres_connection():
    """Verify PostgreSQL connectivity with asyncpg driver."""
    print("\n=== PostgreSQL Connection Check ===")
    try:
        # asyncpg requires postgresql:// not postgresql+asyncpg://
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        version = await conn.fetchval("SELECT version()")
        print("[OK] PostgreSQL connected successfully")
        print("  Driver: asyncpg")
        print(f"  Version: {version}")
        await conn.close()
        return True
    except Exception as e:
        print(f"[FAIL] PostgreSQL connection failed: {e}")
        return False


def check_obsidian_vault():
    """Verify Obsidian vault path."""
    print("\n=== Obsidian Vault Check ===")
    vault_path = Path(settings.obsidian_vault_path)

    if vault_path.exists():
        print(f"[OK] Vault path exists: {vault_path}")

        # Check if writable
        if os.access(vault_path, os.W_OK):
            print("  [OK] Vault is writable")
        else:
            print("  [FAIL] Vault is not writable")
            return False

        # Check for Linear subdirectory
        linear_dir = vault_path / "Linear"
        if linear_dir.exists():
            print("  [OK] Linear subdirectory exists")
        else:
            print("  [WARN] Linear subdirectory does not exist (will be created)")

        return True
    else:
        print(f"[FAIL] Vault path does not exist: {vault_path}")
        print(f"  Expected: {vault_path}")
        return False


def check_environment_variables():
    """Verify critical environment variables."""
    print("\n=== Environment Variables Check ===")

    checks = [
        ("DATABASE_URL", settings.database_url),
        ("OBSIDIAN_VAULT_PATH", settings.obsidian_vault_path),
        ("POSTGRES_USER", settings.postgres_user),
        ("POSTGRES_SERVER", settings.postgres_server),
        ("POSTGRES_PORT", settings.postgres_port),
        ("POSTGRES_DB", settings.postgres_db),
        ("EMBEDDING_PROVIDER", settings.embedding_provider),
        ("OLLAMA_BASE_URL", settings.ollama_base_url),
    ]

    all_ok = True
    for name, value in checks:
        if value:
            print(f"[OK] {name}: {value}")
        else:
            print(f"[FAIL] {name}: NOT SET")
            all_ok = False

    return all_ok


async def check_database_schema():
    """Verify raw_linear_events table exists with correct schema."""
    print("\n=== Database Schema Check ===")
    try:
        from sqlalchemy import text

        async with engine.begin() as conn:
            # Check table exists
            result = await conn.execute(
                text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'raw_linear_events'
                )
            """)
            )
            table_exists = result.scalar()

            if table_exists:
                print("[OK] Table 'raw_linear_events' exists")

                # Check columns
                columns_result = await conn.execute(
                    text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'raw_linear_events'
                    ORDER BY ordinal_position
                """)
                )
                columns = columns_result.fetchall()

                print(f"  Columns ({len(columns)}):")
                required_columns = {
                    "id": "integer",
                    "signature": "character varying",
                    "event_type": "character varying",
                    "headers": "jsonb",
                    "body": "jsonb",
                    "processed": "boolean",
                    "error_log": "character varying",
                }

                # Convert tuples to dicts for easier access
                column_dict = {
                    row[0]: {
                        "column_name": row[0],
                        "data_type": row[1],
                        "is_nullable": row[2],
                    }
                    for row in columns
                }
                for col_name, expected_type in required_columns.items():
                    if col_name in column_dict:
                        actual_type = column_dict[col_name]["data_type"]
                        if expected_type in actual_type:
                            print(f"    [OK] {col_name}: {actual_type}")
                        else:
                            print(
                                f"    [WARN] {col_name}: {actual_type} (expected {expected_type})"
                            )
                    else:
                        print(f"    [FAIL] {col_name}: MISSING")
                        all_ok = False

                # Check index
                indexes_result = await conn.execute(
                    text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'raw_linear_events'
                """)
                )
                indexes = indexes_result.fetchall()
                index_names = [row[0] for row in indexes]

                if "ix_raw_linear_events_processed_received_at" in index_names:
                    print("  [OK] Composite index exists")
                else:
                    print("  [WARN] Composite index not found")

                return True
            else:
                print("[FAIL] Table 'raw_linear_events' does not exist")
                return False
    except Exception as e:
        print(f"[FAIL] Schema check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all Phase 1 checks."""
    print("=" * 60)
    print("PHASE 1: Environment & Dependency Audit")
    print("=" * 60)

    results = {
        "config": check_environment_variables(),
        "vault": check_obsidian_vault(),
        "postgres": await check_postgres_connection(),
        "schema": await check_database_schema(),
    }

    print("\n" + "=" * 60)
    print("PHASE 1 SUMMARY")
    print("=" * 60)

    for check, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{check:12s}: {status}")

    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    if all_passed:
        print("[OK] All Phase 1 checks passed")
    else:
        print("[FAIL] Some Phase 1 checks failed")
        print("Please resolve issues before proceeding to Phase 2")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
