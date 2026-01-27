#!/usr/bin/env python3
"""
Phase 2: Logic Implementation Review
Checks for code correctness, mapping alignment, and error handling gaps.
"""

import sys
from pathlib import Path


def check_processor_logic():
    """Review processor.py for logic correctness."""
    print("\n=== Processor Logic Review ===")

    processor_path = Path("omega_kg/domain/linear/processor.py")

    if not processor_path.exists():
        print(f"[FAIL] File not found: {processor_path}")
        return False

    content = processor_path.read_text()

    checks = [
        ("AsyncSession type hint", "AsyncSession"),
        ("RawLinearEvent import", "from omega_kg.models import"),
        ("SELECT unprocessed events", "where(RawLinearEvent.processed == False)"),
        ("ORDER BY received_at", "order_by(RawLinearEvent.received_at)"),
        ("ValidationError handling", "except ValidationError"),
        ("Error logging", "error_log"),
        ("Session commit", "await session.commit()"),
        ("Graph writer usage", "GraphWriter"),
        ("Embedding generation", "_generate_issue_embedding"),
    ]

    all_ok = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"  [OK] {check_name}")
        else:
            print(f"  [FAIL] {check_name}: NOT FOUND")
            all_ok = False

    return all_ok


def check_mapper_alignment():
    """Verify mapper.py aligns with RawLinearEvent model."""
    print("\n=== Mapper Frontmatter Alignment ===")

    mapper_path = Path("omega_kg/domain/linear/mapper.py")

    if not mapper_path.exists():
        print(f"[FAIL] File not found: {mapper_path}")
        return False

    content = mapper_path.read_text()

    # Read RawLinearEvent model
    model_path = Path("omega_kg/models/linear.py")
    if model_path.exists():
        model_content = model_path.read_text()
    else:
        print("[FAIL] Model file not found")
        return False

    checks = [
        ("linear_id field", '"linear_id":'),
        ("identifier field", '"identifier":'),
        ("status mapping", "self._map_state"),
        ("priority handling", 'frontmatter["priority"]'),
        ("assignee handling", 'frontmatter["assignee"]'),
        ("createdAt handling", 'frontmatter["created"]'),
        ("updatedAt handling", 'frontmatter["updated"]'),
        ("YAML frontmatter", "yaml.dump"),
        ("Linear subdirectory", 'vault_path / "Linear"'),
    ]

    all_ok = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"  [OK] {check_name}")
        else:
            print(f"  [FAIL] {check_name}: NOT FOUND")
            all_ok = False

    return all_ok


def check_error_handling():
    """Verify comprehensive error handling."""
    print("\n=== Error Handling Coverage ===")

    processor_path = Path("omega_kg/domain/linear/processor.py")

    if not processor_path.exists():
        print(f"[FAIL] File not found: {processor_path}")
        return False

    content = processor_path.read_text()

    # Check for different error scenarios
    error_scenarios = [
        ("Validation errors", "except ValidationError"),
        ("Processing errors", "except Exception"),
        ("Error logging to DB", "values(error_log=error_msg)"),
        ("Continue on errors", 'stats["errors"] += 1'),
        ("Clear error on success", "error_log=None"),
    ]

    all_ok = True
    for scenario, pattern in error_scenarios:
        if pattern in content:
            print(f"  [OK] {scenario}")
        else:
            print(f"  [FAIL] {scenario}: NOT FOUND")
            all_ok = False

    return all_ok


def check_hardcoded_paths():
    """Check for hardcoded paths that should use configuration."""
    print("\n=== Configuration Drift Check ===")

    files_to_check = [
        "omega_kg/domain/linear/processor.py",
        "omega_kg/domain/linear/mapper.py",
    ]

    hardcoded_patterns = [
        "d:/projects/omegavault.as",
        "/home/user/projects",
        "./vault",
        "http://localhost:11434",
    ]

    issues_found = []

    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            for pattern in hardcoded_patterns:
                if pattern in content:
                    issues_found.append(f"  {file_path}: {pattern}")

    if issues_found:
        print("  [FAIL] Hardcoded paths found:")
        for issue in issues_found:
            print(issue)
        return False
    else:
        print("  [OK] No hardcoded paths found")
        return True


def check_embedding_service():
    """Verify embedding service integration."""
    print("\n=== Embedding Service Integration ===")

    processor_path = Path("omega_kg/domain/linear/processor.py")

    if not processor_path.exists():
        print(f"[FAIL] File not found: {processor_path}")
        return False

    content = processor_path.read_text()

    checks = [
        ("Embedding import", "from omega_kg.domain.common.embedding_service"),
        ("Embedding generation call", "await generate_embedding"),
        ("Non-blocking on failure", "except Exception as e"),
        ("Optional embedding storage", "if embedding:"),
    ]

    all_ok = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"  [OK] {check_name}")
        else:
            print(f"  [WARN] {check_name}: NOT FOUND (optional)")

    return all_ok


def check_linear_status_map():
    """Verify LINEAR_STATUS_MAP in config.py"""
    print("\n=== Linear Status Mapping ===")

    config_path = Path("omega_kg/config.py")

    if not config_path.exists():
        print(f"[FAIL] File not found: {config_path}")
        return False

    try:
        content = config_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("[FAIL] Cannot read config.py (encoding issue)")
        return False

    checks = [
        ("LINEAR_STATUS_MAP defined", "LINEAR_STATUS_MAP"),
        ("Backlog mapping", '"Backlog":'),
        ("Todo mapping", '"Todo":'),
        ("In Progress mapping", '"In Progress":'),
        ("Done mapping", '"Done":'),
    ]

    all_ok = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"  [OK] {check_name}")
        else:
            print(f"  [FAIL] {check_name}: NOT FOUND")
            all_ok = False

    return all_ok


def main():
    """Run all Phase 2 reviews."""
    print("=" * 60)
    print("PHASE 2: Logic Implementation Review")
    print("=" * 60)

    results = {
        "processor": check_processor_logic(),
        "mapper": check_mapper_alignment(),
        "error_handling": check_error_handling(),
        "config_drift": check_hardcoded_paths(),
        "embedding": check_embedding_service(),
        "status_map": check_linear_status_map(),
    }

    print("\n" + "=" * 60)
    print("PHASE 2 SUMMARY")
    print("=" * 60)

    for check, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{check:15s}: {status}")

    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    if all_passed:
        print("[OK] All Phase 2 checks passed")
    else:
        print("[FAIL] Some Phase 2 checks failed")
        print("Please review code issues before proceeding to Phase 3")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
