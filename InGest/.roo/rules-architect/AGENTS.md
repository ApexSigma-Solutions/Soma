# Architect Mode Rules

This file provides architectural guidance for agents working in Architect mode.

## Project Architecture Rules (Non-Obvious Only)

- **Settings are intentionally non-cached**: Architectural design choice to reload from `.env` on every access via `get_settings()` - prevents stale config in long-running processes.
- **memOS tier mapping is opinionated**: Procedural/code content MUST route to Tier 2 (Postgres + Qdrant) via hardcoded `tier_mapping` dict in [`MemOSClient.store_memory`](src/ingest_llm_as/services/memos_client.py:128) - this is an architectural constraint, not configurable.
- **apexsigma-core is a local dependency**: Path reference `../../libs/apexsigma-core` - this creates a monorepo coupling that must exist for installation.
- **Knowledge structures use POML**: All knowledge graph data must use XML-based POML serialization (see `prompts/` directory) - this is an architectural data format decision.
- **MemOSClient uses singleton pattern**: Global instance via `get_memos_client()` function - architectural choice for connection pooling and resource management.
- **ContentProcessor violates settings pattern**: Module-level `settings` import at line 14 bypasses non-cached design - this is legacy code that should be refactored.
- **Python AST parsing with fallback**: Code processing uses AST parser but falls back to text processing on failure - architectural robustness pattern for graceful degradation.
- **Langfuse observability is optional**: All tracing calls check `langfuse_client.enabled` before execution - feature flag architecture for optional observability.
- **Multiple ingestion routers**: Separate routers for `ingestion`, `repository`, `ecosystem`, `analysis`, and `omega_ingest` - architectural separation of concerns (see [`main.py:34-39`](src/ingest_llm_as/main.py:34-39)).
- **FastAPI app factory pattern**: `create_app()` function returns configured FastAPI instance - supports testing and multiple app instances.
