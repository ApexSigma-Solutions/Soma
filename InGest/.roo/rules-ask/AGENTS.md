# Ask Mode Rules

This file provides guidance for agents working in Ask mode (explanations, documentation, understanding concepts).

## Project Documentation Rules (Non-Obvious Only)

- **Settings are non-cached by design**: When explaining configuration behavior, note that `get_settings()` reloads from `.env` on every call - this is intentional, not a bug.
- **memOS tier mapping is opinionated**: Procedural/code content routes to Tier 2 (Postgres + Qdrant) via hardcoded `tier_mapping` dict in [`MemOSClient.store_memory`](src/ingest_llm_as/services/memos_client.py:128).
- **ContentProcessor violates settings pattern**: The module-level `settings` import at line 14 bypasses the non-cached design - this is legacy code, not the intended pattern.
- **Knowledge structures use POML**: All knowledge graph data must use XML-based POML serialization (see `prompts/` directory for examples like `agent_context_template.poml`).
- **Multiple ingestion endpoints**: The service has separate routers for different ingestion types - `ingestion`, `repository`, `ecosystem`, `analysis`, and `omega_ingest` (see [`main.py:34-39`](src/ingest_llm_as/main.py:34-39)).
- **AST parsing with fallback**: Python code processing uses AST parser but falls back to text processing on failure - this is intentional for robustness (see [`content_processor.py:376`](src/ingest_llm_as/utils/content_processor.py:376)).
- **Langfuse observability is optional**: All tracing calls check `langfuse_client.enabled` before execution - can be disabled via settings.
