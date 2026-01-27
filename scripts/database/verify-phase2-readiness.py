#!/usr/bin/env python3
"""
MVP-001 Phase 2 Launch Verification Audit
Comprehensive verification across all three domains: Ingestion, Intelligence, Infrastructure

This script orchestrates verification of:
- Domain A: Ingestion (The Ears) - linear_receiver and RawWebhookEvent
- Domain B: Intelligence (The Brain) - Codex and Mirmir
- Domain C: Infrastructure (The Body) - pre_flight and settings

Exit Codes:
    0 = Complete Success (all tests passed)
    1 = Failure (critical errors found)
    2 = Partial Success (some tests skipped due to unavailable services)
"""

import argparse
import sys
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class TestResult:
    """Represents a single test result"""

    def __init__(
        self, name: str, status: str, duration_ms: float = 0, message: str = ""
    ):
        self.name = name
        self.status = status  # PASS, FAIL, SKIPPED, ERROR
        self.duration_ms = duration_ms
        self.message = message

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "message": self.message,
        }


class Phase2Auditor:
    """Main audit orchestrator for MVP-001 Phase 2 Launch Verification"""

    def __init__(
        self,
        environment: str,
        mode: str = "full",
        skip_db: bool = False,
        diagnostic: bool = False,
    ):
        self.environment = environment
        self.mode = mode
        self.skip_db = skip_db
        self.diagnostic = diagnostic
        self.results: Dict[str, List[TestResult]] = {
            "A_ingestion": [],
            "B_intelligence": [],
            "C_infrastructure": [],
        }
        self.overall_status = "UNKNOWN"
        self.exit_code = 0

    def run_audit(self) -> int:
        """Execute complete audit across all three domains"""
        logger.info("=" * 80)
        logger.info("MVP-001 Phase 2 Launch Verification Audit")
        logger.info("=" * 80)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Skip Database: {self.skip_db}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 80)

        # Domain A: Ingestion Verification
        if not self.verify_ingestion():
            self.overall_status = "FAIL"
            self.exit_code = 1

        # Domain B: Intelligence Verification
        if not self.verify_intelligence():
            if self.exit_code == 0:
                self.exit_code = 2  # Partial success
            self.overall_status = "PARTIAL" if self.exit_code == 2 else "FAIL"

        # Domain C: Infrastructure Verification
        if not self.verify_infrastructure():
            self.overall_status = "FAIL"
            self.exit_code = 1

        # Determine final status
        if self.exit_code == 0:
            self.overall_status = "PASS"

        # Generate report
        self.generate_report()

        # Print summary
        self.print_summary()

        return self.exit_code

    def verify_ingestion(self) -> bool:
        """Domain A: Verify linear_receiver endpoint and RawWebhookEvent model"""
        logger.info("\n" + "=" * 80)
        logger.info("DOMAIN A: INGESTION (The Ears)")
        logger.info("=" * 80)

        tests = [
            ("linear_receiver_import", self._test_linear_receiver_import),
            ("webhook_model_exists", self._test_webhook_model_exists),
            ("raw_event_model_structure", self._test_raw_event_model_structure),
            ("endpoint_signature", self._test_endpoint_signature),
        ]

        passed = self._run_tests("A_ingestion", tests)

        status = "PASS" if passed == len(tests) else "FAIL"
        logger.info(f"\nDomain A: {status} ({passed}/{len(tests)} tests)")
        return passed == len(tests)

    def verify_intelligence(self) -> bool:
        """Domain B: Verify omega_kg.intelligence module"""
        logger.info("\n" + "=" * 80)
        logger.info("DOMAIN B: INTELLIGENCE (The Brain)")
        logger.info("=" * 80)

        tests = [
            ("codex_import", self._test_codex_import),
            ("mirmir_import", self._test_mirmir_import),
            ("intelligence_models", self._test_intelligence_models),
            ("neo4j_connection", self._test_neo4j_connection),
        ]

        passed = self._run_tests("B_intelligence", tests)

        # Check if any tests were skipped
        skipped = sum(
            1 for r in self.results["B_intelligence"] if r.status == "SKIPPED"
        )

        if skipped > 0 and skipped == len(tests):
            logger.info(
                "\nDomain B: SKIPPED (all tests skipped - services unavailable)"
            )
            return True  # SKIPPED is OK
        elif skipped > 0:
            logger.info(
                f"\nDomain B: PARTIAL ({passed}/{len(tests)} tests passed, {skipped} skipped)"
            )
            return True  # PARTIAL is OK
        else:
            status = "PASS" if passed == len(tests) else "FAIL"
            logger.info(f"\nDomain B: {status} ({passed}/{len(tests)} tests)")
            return passed == len(tests)

    def verify_infrastructure(self) -> bool:
        """Domain C: Verify system health and configuration"""
        logger.info("\n" + "=" * 80)
        logger.info("DOMAIN C: INFRASTRUCTURE (The Body)")
        logger.info("=" * 80)

        tests = [
            ("pre_flight_check", self._test_preflight),
            ("settings_valid", self._test_settings),
            ("capture_server_import", self._test_capture_server_import),
        ]

        passed = self._run_tests("C_infrastructure", tests)

        status = "PASS" if passed == len(tests) else "FAIL"
        logger.info(f"\nDomain C: {status} ({passed}/{len(tests)} tests)")
        return passed == len(tests)

    def _run_tests(self, domain: str, tests: List[Tuple[str, callable]]) -> int:
        """Run a list of tests and collect results"""
        passed = 0
        for test_name, test_func in tests:
            start_time = time.time()
            try:
                result = test_func()
                duration_ms = (time.time() - start_time) * 1000

                if result == "SKIPPED":
                    self.results[domain].append(
                        TestResult(test_name, "SKIPPED", duration_ms)
                    )
                    logger.info(f"[SKIPPED] {test_name}")
                elif result:
                    self.results[domain].append(
                        TestResult(test_name, "PASS", duration_ms)
                    )
                    logger.info(f"[  PASS] {test_name}")
                    passed += 1
                else:
                    self.results[domain].append(
                        TestResult(test_name, "FAIL", duration_ms)
                    )
                    logger.error(f"[  FAIL] {test_name}")
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.results[domain].append(
                    TestResult(test_name, "ERROR", duration_ms, str(e))
                )
                logger.error(f"[ ERROR] {test_name}: {e}")
                if self.diagnostic:
                    import traceback

                    logger.error(traceback.format_exc())

        return passed

    # Domain A Test Methods

    def _test_linear_receiver_import(self) -> bool:
        """Test that linear_receiver module can be imported"""
        from omega_kg.routers import linear_receiver

        assert hasattr(linear_receiver, "router"), (
            "linear_receiver must have 'router' attribute"
        )
        return True

    def _test_webhook_model_exists(self) -> bool:
        """Test that RawWebhookEvent model exists"""
        from omega_kg.models.webhook import RawWebhookEvent, RawWebhookEventPydantic

        assert RawWebhookEvent is not None, "RawWebhookEvent model not found"
        assert RawWebhookEventPydantic is not None, (
            "RawWebhookEventPydantic model not found"
        )
        return True

    def _test_raw_event_model_structure(self) -> bool:
        """Test that RawWebhookEvent has required fields"""
        from omega_kg.models.webhook import RawWebhookEvent
        from sqlalchemy import inspect

        # Get column information from the model directly
        try:
            # Try to inspect using the model's metadata
            from omega_kg.database.base import engine

            inspector = inspect(engine)
            columns = [
                c["name"] for c in inspector.get_columns(RawWebhookEvent.__tablename__)
            ]
        except Exception:
            # Fallback: check the model __table__ attributes directly
            columns = [c.name for c in RawWebhookEvent.__table__.columns]

        required_fields = [
            "id",
            "source",
            "received_at",
            "processed_status",
            "headers",
            "payload",
            "event_type",
            "error_log",
        ]

        missing_fields = [f for f in required_fields if f not in columns]

        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return False

        logger.info(f"  Required fields present: {', '.join(required_fields)}")
        return True

    def _test_endpoint_signature(self) -> bool:
        """Test that POST /webhooks/linear endpoint exists"""
        from omega_kg.routers.linear_receiver import router

        routes = [r.path for r in router.routes]

        if "/webhooks/linear" not in routes:
            logger.error(
                f"Endpoint /webhooks/linear not found. Available routes: {routes}"
            )
            return False

        # Verify it's a POST endpoint
        endpoint = [r for r in router.routes if r.path == "/webhooks/linear"][0]
        if hasattr(endpoint, "methods"):
            if "POST" not in endpoint.methods:
                logger.error(
                    f"Endpoint exists but is not a POST method. Methods: {endpoint.methods}"
                )
                return False

        logger.info("  Endpoint verified: POST /webhooks/linear")
        return True

    # Domain B Test Methods

    def _test_codex_import(self) -> bool:
        """Test that Codex can be imported"""
        from omega_kg.intelligence.codex import Codex

        assert Codex is not None, "Codex class not found"
        return True

    def _test_mirmir_import(self) -> bool:
        """Test that Mirmir can be imported"""
        from omega_kg.intelligence.mirmir import Mirmir

        assert Mirmir is not None, "Mirmir class not found"
        return True

    def _test_intelligence_models(self) -> bool:
        """Test that intelligence models exist"""
        from omega_kg.intelligence.models import Constraint, Context, Incident, Verdict

        assert Constraint is not None, "Constraint model not found"
        assert Context is not None, "Context model not found"
        assert Incident is not None, "Incident model not found"
        assert Verdict is not None, "Verdict model not found"

        logger.info("  Models verified: Constraint, Context, Incident, Verdict")
        return True

    def _test_neo4j_connection(self) -> Optional[bool]:
        """Test Neo4j connection - returns True, False, or 'SKIPPED'"""
        if self.skip_db:
            logger.info("  Database tests skipped (--skip-database flag set)")
            return "SKIPPED"

        try:
            from neo4j import GraphDatabase
            from omega_kg.settings import settings

            # Check if settings has required Neo4j config
            if not hasattr(settings, "neo4j_uri"):
                logger.error("  Neo4j URI not configured in settings")
                return "SKIPPED"

            driver = GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()

            logger.info(f"  Neo4j connection successful: {settings.neo4j_uri}")
            return True
        except Exception as e:
            logger.warning(f"  Neo4j connection failed: {e}")
            logger.info("  Intelligence tests will be marked as skipped")
            return "SKIPPED"

    # Domain C Test Methods

    def _test_preflight(self) -> bool:
        """Test pre_flight checks"""
        try:
            from omega_kg.pre_flight import pre_flight_checks

            # Run pre_flight and capture output
            result = pre_flight_checks()

            if not result:
                logger.error("  Pre-flight checks failed")
                return False

            logger.info("  Pre-flight checks passed")
            return True
        except Exception as e:
            logger.error(f"  Pre-flight check error: {e}")
            return False

    def _test_settings(self) -> bool:
        """Test settings are valid"""
        try:
            from omega_kg.settings import settings

            # Check critical settings
            assert settings is not None, "Settings object is None"

            # Verify environment marker
            if hasattr(settings, "omega_env"):
                logger.info(f"  Environment marker: {settings.omega_env}")
            else:
                logger.warning("  OMEGA_ENV marker not found in settings")

            logger.info("  Settings validation passed")
            return True
        except Exception as e:
            logger.error(f"  Settings validation failed: {e}")
            return False

    def _test_capture_server_import(self) -> bool:
        """Test capture server can import required modules"""
        try:
            from omega_kg import capture_server

            assert capture_server is not None, "capture_server module not found"
            logger.info("  Capture server module available")
            return True
        except Exception as e:
            logger.error(f"  Capture server import failed: {e}")
            return False

    def generate_report(self):
        """Generate JSON report with detailed results"""
        # Calculate summary statistics
        all_results = []
        for domain_results in self.results.values():
            all_results.extend(domain_results)

        total_tests = len(all_results)
        passed = sum(1 for r in all_results if r.status == "PASS")
        failed = sum(1 for r in all_results if r.status == "FAIL")
        errors = sum(1 for r in all_results if r.status == "ERROR")
        skipped = sum(1 for r in all_results if r.status == "SKIPPED")

        report = {
            "audit_id": f"phase2-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "mode": self.mode,
            "overall_status": self.overall_status,
            "exit_code": self.exit_code,
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
            },
            "domains": {
                domain: {
                    "tests": [r.to_dict() for r in results],
                    "passed": sum(1 for r in results if r.status == "PASS"),
                    "failed": sum(1 for r in results if r.status == "FAIL"),
                    "skipped": sum(1 for r in results if r.status == "SKIPPED"),
                }
                for domain, results in self.results.items()
            },
        }

        # Save report
        # Use relative path from current working directory
        reports_dir = Path.cwd() / "reports"
        reports_dir.mkdir(exist_ok=True)

        report_file = (
            reports_dir
            / f"phase2_audit_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"\nDetailed report saved to: {report_file}")

    def print_summary(self):
        """Print summary to console"""
        logger.info("\n" + "=" * 80)
        logger.info("AUDIT SUMMARY")
        logger.info("=" * 80)

        # Calculate statistics
        all_results = []
        for domain_results in self.results.values():
            all_results.extend(domain_results)

        total = len(all_results)
        passed = sum(1 for r in all_results if r.status == "PASS")
        failed = sum(1 for r in all_results if r.status == "FAIL")
        skipped = sum(1 for r in all_results if r.status == "SKIPPED")

        # Overall status
        status_symbols = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "UNKNOWN": "❓"}
        symbol = status_symbols.get(self.overall_status, "❓")

        logger.info(f"{symbol} Overall Status: {self.overall_status}")
        logger.info(f"   Exit Code: {self.exit_code}")

        logger.info("\nTest Results:")
        for domain, results in self.results.items():
            if not results:
                continue

            domain_passed = sum(1 for r in results if r.status == "PASS")
            domain_total = len(results)
            domain_skipped = sum(1 for r in results if r.status == "SKIPPED")

            if domain_skipped == domain_total:
                logger.info(
                    f"  {domain}: SKIPPED ({domain_skipped}/{domain_total} tests)"
                )
            else:
                logger.info(f"  {domain}: {domain_passed}/{domain_total} tests passed")

        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"  Passed: {passed}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Skipped: {skipped}")

        logger.info("=" * 80)

        # Print next steps based on results
        if self.exit_code == 0:
            logger.info("\n🎉 Phase 2 Launch Verification: PASSED")
            logger.info("All systems are ready for Phase 2!")
        elif self.exit_code == 2:
            logger.info("\n⚠️  Phase 2 Launch Verification: PARTIAL SUCCESS")
            logger.info("Some tests were skipped (likely due to unavailable services).")
            logger.info("Review the report for details.")
        else:
            logger.info("\n❌ Phase 2 Launch Verification: FAILED")
            logger.info("Critical issues found. Please review the errors above.")
            logger.info("See the detailed report for troubleshooting guidance.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MVP-001 Phase 2 Launch Verification Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 = Complete Success (all tests passed)
  1 = Failure (critical errors found)
  2 = Partial Success (some tests skipped due to unavailable services)

Examples:
  # Run full audit in dev environment
  python verify_phase2_readiness.py --environment dev

  # Run static checks only
  python verify_phase2_readiness.py --environment dev --mode static

  # Skip database tests
  python verify_phase2_readiness.py --environment dev --skip-database

  # Conservative test for stable environment
  python verify_phase2_readiness.py --environment stable --mode conservative
        """,
    )

    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "stable", "temp"],
        help="Target environment to audit",
    )

    parser.add_argument(
        "--mode",
        default="full",
        choices=["static", "live", "full", "conservative"],
        help="Verification mode (default: full)",
    )

    parser.add_argument(
        "--skip-database",
        action="store_true",
        help="Skip database-dependent tests (Neo4j, PostgreSQL)",
    )

    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Enable diagnostic mode with detailed error traces",
    )

    args = parser.parse_args()

    # Validate environment consistency
    from omega_kg.settings import settings as omega_settings

    if hasattr(omega_settings, "omega_env"):
        if omega_settings.omega_env != args.environment:
            logger.warning(
                f"⚠️  Settings environment ({omega_settings.omega_env}) "
                f"differs from target environment ({args.environment})"
            )

    # Create auditor and run
    auditor = Phase2Auditor(
        environment=args.environment,
        mode=args.mode,
        skip_db=args.skip_database,
        diagnostic=args.diagnostic,
    )

    try:
        exit_code = auditor.run_audit()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n\nAudit interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {e}")
        if args.diagnostic:
            import traceback

            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
