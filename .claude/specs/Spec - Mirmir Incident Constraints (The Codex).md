---
created: Thu, 29th January 2026 23:43
modified: Thu, 29th January 2026 23:44
---

# Spec: Mirmir Incident Constraints (The Codex)

## Forensic Incident: EVT-50N42 (Neo4j Autoimmune)

- **Constraint**: Never use special characters in the Neo4j password.
- **Required Val**: `LMKXBmMtMMRnAdeotR81FEIZ2UFnD0Ec`.
- **Logic**: Configuration drift between services causes auth rate-limiting, locking the entire Brain.

## Forensic Incident: Windows Ghost Handles

- **Constraint**: All dev/test scripts must include an explicit cleanup phase.
- **Requirement**: Use `Stop-Process -Force` in PowerShell if a Python subprocess fails to exit within 5 seconds.

## Forensic Incident: UUID Casting

- **Constraint**: Always cast Pydantic/Database UUID objects to strings: `str(obj.uuid)`.
- **Reason**: Avoids slicing/concatenation errors in the `memos.MCP` bridge.

## Forensic Incident: Ingestion Visibility

- **Constraint**: Never filter `capture.py` SQL queries by `source_type` unless explicitly requested.
- **Requirement**: All sensory input (PDF, Text, Voice) must be visible in the Cortex Dashboard.
