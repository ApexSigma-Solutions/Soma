from omega_kg.routers.log_summary import parse_summary_md


def test_parse_summary_md():
    content = """# Daily Log Summary - 2026-01-18
**Generated At:** 2026-01-18T10:00:00.000
**Monitoring Started:** 2026-01-18T00:00:00.000

## 📊 Statistics

| Service | Level | Count |
|---|---|---|
| Omega | ERROR | 5 |
| Ingest | WARNING | 2 |
| memOS | INFO | 100 |

## 🚨 Critical Errors & Anomalies

### [Omega] Documentation Enforcement Failed
- **Timestamp:** 2026-01-18T09:30:00
- **Count:** 3

### [Ingest] Neo4j Connection Timeout
- **Timestamp:** 2026-01-18T08:15:00
- **Count:** 1

## ⚠️ Warnings

- Insecure JWT algorithm configured: none
- Vector store pool initialization delayed

## 🛠️ Suggested Actions (Issues to Create)

1. Fix Neo4j auth timeout in OmegaKG
2. Update Spacy models to 3.7.2
"""
    report = parse_summary_md(content)

    assert report.date == "2026-01-18"
    assert len(report.stats) == 3

    # Check length of critical errors
    assert len(report.critical_errors) == 2, (
        f"Expected 2 critical errors, got {len(report.critical_errors)}: {report.critical_errors}"
    )

    # Check length of actions
    assert len(report.suggested_actions) == 2, (
        f"Expected 2 suggested actions, got {len(report.suggested_actions)}: {report.suggested_actions}"
    )
