#!/usr/bin/env python3
"""
Phase 6: Consolidated Health Report
Aggregates all diagnostic checks and generates comprehensive health report.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))


async def generate_health_report():
    """Generate comprehensive health report."""
    print("=" * 80)
    print("LINEAR REFINERY DIAGNOSTIC HEALTH REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Working Directory: {Path.cwd()}")

    report = {
        "timestamp": datetime.now().isoformat(),
        "working_directory": str(Path.cwd()),
        "checks": {},
        "summary": {},
        "recommendations": [],
    }

    # Phase 1: Environment
    print("\n" + "=" * 80)
    print("PHASE 1: ENVIRONMENT & DEPENDENCY AUDIT")
    print("=" * 80)

    try:
        from omega_kg.settings import settings

        report["checks"]["environment"] = {
            "database_url_configured": bool(settings.database_url),
            "obsidian_vault_configured": bool(settings.obsidian_vault_path),
            "embedding_provider": settings.embedding_provider,
            "ollama_base_url": settings.ollama_base_url,
            "postgres_config": {
                "user": settings.postgres_user,
                "server": settings.postgres_server,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
            },
        }

        for key, value in report["checks"]["environment"].items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")

        # Test PostgreSQL
        import asyncpg

        try:
            db_url = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
            conn = await asyncpg.connect(db_url)
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            report["checks"]["environment"]["postgres_connection"] = "OK"
            print("\n[OK] PostgreSQL connection: OK")
        except Exception as e:
            report["checks"]["environment"]["postgres_connection"] = f"FAILED: {e}"
            print("\n[FAIL] PostgreSQL connection: FAILED")
            report["recommendations"].append(
                "Fix PostgreSQL connection before proceeding"
            )

    except Exception as e:
        report["checks"]["environment"] = {"error": str(e)}
        print(f"\n[FAIL] Environment check failed: {e}")
        report["recommendations"].append("Check environment configuration")

    # Phase 2: Code Review
    print("\n" + "=" * 80)
    print("PHASE 2: LOGIC IMPLEMENTATION REVIEW")
    print("=" * 80)

    code_checks = {
        "processor_exists": Path("omega_kg/domain/linear/processor.py").exists(),
        "mapper_exists": Path("omega_kg/domain/linear/mapper.py").exists(),
        "models_defined": Path("omega_kg/models/linear.py").exists(),
        "embedding_service_exists": Path(
            "omega_kg/domain/common/embedding_service.py"
        ).exists(),
    }

    report["checks"]["code_structure"] = code_checks

    for check, result in code_checks.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {check}")

    if not all(code_checks.values()):
        report["recommendations"].append("Missing critical code files")

    # Phase 3: E2E Test
    print("\n" + "=" * 80)
    print("PHASE 3: LIVE E2E HEARTBEAT TEST")
    print("=" * 80)

    try:
        from omega_kg.database.session import AsyncSessionLocal
        from omega_kg.models import RawLinearEvent
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            # Check for DIAG-001
            result = await session.execute(
                select(RawLinearEvent).where(
                    RawLinearEvent.body.contains({"data": {"identifier": "DIAG-001"}})
                )
            )
            diag_events = result.scalars().all()

            report["checks"]["e2e_test"] = {
                "diag_events_found": len(diag_events),
                "processed_count": sum(1 for e in diag_events if e.processed),
            }

            print(f"DIAG-001 events found: {len(diag_events)}")
            print(f"Processed: {report['checks']['e2e_test']['processed_count']}")

            if diag_events:
                latest = diag_events[-1]
                print("\nLatest event:")
                print(f"  ID: {latest.id}")
                print(f"  Processed: {latest.processed}")
                print(f"  Error: {latest.error_log}")

                if latest.processed:
                    print("[OK] E2E test successful")
                else:
                    print("[FAIL] E2E test incomplete")
                    report["recommendations"].append("Review DIAG-001 event processing")

    except Exception as e:
        report["checks"]["e2e_test"] = {"error": str(e)}
        print(f"\n[FAIL] E2E test check failed: {e}")
        report["recommendations"].append("Run Phase 3 E2E test manually")

    # Phase 4: Error Handling
    print("\n" + "=" * 80)
    print("PHASE 4: FAILURE RECOVERY CHECK")
    print("=" * 80)

    try:
        from omega_kg.database.session import AsyncSessionLocal
        from omega_kg.models import RawLinearEvent
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RawLinearEvent).where(RawLinearEvent.error_log.isnot(None))
            )
            error_events = result.scalars().all()

            report["checks"]["error_handling"] = {
                "total_errors": len(error_events),
                "unprocessed_errors": sum(1 for e in error_events if not e.processed),
            }

            print(f"Events with errors: {len(error_events)}")
            print(
                f"Unprocessed with errors: {report['checks']['error_handling']['unprocessed_errors']}"
            )

            if error_events:
                print("\nRecent errors:")
                for event in error_events[-3:]:
                    print(f"  ID {event.id}: {event.error_log[:80]}")

    except Exception as e:
        report["checks"]["error_handling"] = {"error": str(e)}
        print(f"\n[FAIL] Error handling check failed: {e}")

    # Phase 5: Ollama
    print("\n" + "=" * 80)
    print("PHASE 5: OLLAMA SERVICE CHECK")
    print("=" * 80)

    try:
        import httpx

        ollama_url = settings.ollama_base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/version")

            if response.status_code == 200:
                data = response.json()
                report["checks"]["ollama"] = {
                    "status": "running",
                    "version": data.get("version"),
                    "url": ollama_url,
                }
                print("[OK] Ollama is running")
                print(f"  Version: {data.get('version')}")
                print(f"  URL: {ollama_url}")
            else:
                report["checks"]["ollama"] = {
                    "status": "error",
                    "http_code": response.status_code,
                }
                print(f"[FAIL] Ollama returned: {response.status_code}")
                report["recommendations"].append("Start Ollama service")

    except Exception as e:
        report["checks"]["ollama"] = {"status": "unavailable", "error": str(e)}
        print(f"[FAIL] Ollama not available: {e}")
        report["recommendations"].append("Install and start Ollama service")

    # Phase 6: Summary
    print("\n" + "=" * 80)
    print("PHASE 6: CONSOLIDATED HEALTH REPORT")
    print("=" * 80)

    # Calculate overall health score
    health_score = 0
    max_score = 0

    if report["checks"].get("environment", {}).get("postgres_connection") == "OK":
        health_score += 20
    max_score += 20

    if all(report["checks"].get("code_structure", {}).values()):
        health_score += 20
    max_score += 20

    if report["checks"].get("e2e_test", {}).get("processed_count", 0) > 0:
        health_score += 30
    max_score += 30

    if report["checks"].get("ollama", {}).get("status") == "running":
        health_score += 30
    max_score += 30

    health_percentage = (health_score / max_score * 100) if max_score > 0 else 0

    report["summary"] = {
        "health_score": f"{health_score}/{max_score}",
        "health_percentage": f"{health_percentage:.1f}%",
        "status": "HEALTHY"
        if health_percentage >= 80
        else "NEEDS_ATTENTION"
        if health_percentage >= 50
        else "CRITICAL",
    }

    print(f"\nOverall Health Score: {report['summary']['health_score']}")
    print(f"Health Percentage: {report['summary']['health_percentage']}")
    print(f"Status: {report['summary']['status']}")

    # Recommendations
    if report["recommendations"]:
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")
    else:
        print("\n[OK] No critical recommendations")

    # Save report
    report_path = Path("diagnostic_health_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n[OK] Report saved to: {report_path}")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

    return 0 if health_percentage >= 80 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(generate_health_report()))
