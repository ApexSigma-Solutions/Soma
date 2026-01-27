# Debug Mode Rules

This file provides debugging-specific guidance for agents working in Debug mode.

## Project Debug Rules (Non-Obvious Only)

- **Settings reload on every access**: When debugging settings issues, remember that `get_settings()` creates a fresh instance each time - cached values won't persist across calls.
- **memOS client singleton**: The global `get_memos_client()` instance is created once and reused - if debugging connection issues, check if the instance needs to be recreated.
- **Langfuse tracing can be disabled**: All observability calls check `langfuse_client.enabled` before execution - set `INGEST_LANGFUSE_ENABLED=false` to disable tracing during debugging.
- **AST parsing fallback**: Python code processing falls back to text processing on AST parse failures - check logs for "AST parsing failed" messages to identify problematic code.
- **ContentProcessor settings violation**: The module-level `settings` import at line 14 bypasses the non-cached design - this may cause stale config values during debugging.
- **memOS tier mapping**: Procedural/code content routes to Tier 2 via hardcoded `tier_mapping` dict - verify tier routing by checking the numeric tier value in API calls.
