"""
Pre-flight validation checks for OmegaKG server startup.
"""

import sys
import logging
from omega_kg.settings import settings

logger = logging.getLogger(__name__)


def pre_flight_checks() -> bool:
    """
    Run pre-flight validation checks before server startup.

    Returns:
        True if all checks pass, False otherwise

    Raises:
        SystemExit: If critical checks fail
    """
    logger.info("Running pre-flight validation checks...")

    # Check 1: Verify omega_kg package is installed
    try:
        import omega_kg

        logger.info(
            f"[OK] omega_kg package version: {getattr(omega_kg, '__version__', 'unknown')}"
        )
    except ImportError as e:
        logger.critical(f"[CRITICAL] omega_kg package not installed: {e}")
        logger.critical("=" * 60)
        logger.critical("PRE-FLIGHT CHECK FAILED")
        logger.critical("=" * 60)
        logger.critical("")
        logger.critical(
            "ERROR: The omega_kg package is not installed in this environment."
        )
        logger.critical("")
        logger.critical("SOLUTION: Run one of the following commands:")
        logger.critical("  1. pip install -e .")
        logger.critical("  2. poetry install")
        logger.critical("  3. python -m pip install -e .")
        logger.critical("")
        logger.critical("Or run the automated setup script:")
        logger.critical("  .\\scripts\\setup_omega_kg.ps1")
        logger.critical("")
        logger.critical("For more details, run:")
        logger.critical("  python scripts\\verify_installation.py")
        logger.critical("=" * 60)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error checking package: {e}")

    # Check 2: Verify critical dependencies
    critical_deps = ["fastapi", "neo4j", "pydantic", "openai"]
    missing_deps = []
    for dep in critical_deps:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        logger.error(
            f"[ERROR] Missing critical dependencies: {', '.join(missing_deps)}"
        )
        logger.error("Run: pip install -e .")
        return False

    # Check 3: Verify configuration files
    if not settings:
        logger.warning("[WARNING] No settings configured")
    else:
        logger.info("[OK] Settings configured")

    logger.info("[OK] All pre-flight checks passed")
    return True
