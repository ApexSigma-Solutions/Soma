# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Non-Obvious Project Conventions

- **Settings are intentionally non-cached**: Use `get_settings()` function from [`src/ingest_llm_as/config.py`](src/ingest_llm_as/config.py:76), not cached module-level instance. Settings reload from `.env` on every call.
- **Env prefix is `INGEST_`**: All environment variables use this prefix (e.g., `INGEST_MEMOS_BASE_URL`), configured in [`config.py`](src/ingest_llm_as/config.py:67).
- **memOS tier mapping is opinionated**: Procedural/code content routes to Tier 2 (see [`MemOSClient.store_memory`](src/ingest_llm_as/services/memos_client.py:128)).
- **Microservice is self-contained**: This project has no external library dependencies - all functionality is implemented within the service.
- **poml for knowledge structures**: All knowledge graph data must use XML-based POML serialization (see `prompts/` directory for examples).
- **MemOSClient uses singleton pattern**: Use `get_memos_client()` function for global instance, not direct instantiation (see [`memos_client.py:242`](src/ingest_llm_as/services/memos_client.py:242)).
- **ContentProcessor violates settings pattern**: Module-level `settings` import at line 14 bypasses non-cached design - use `get_settings()` in new code.
- **Python AST parsing with fallback**: Code processing uses AST parser but falls back to text processing on failure (see [`content_processor.py:376`](src/ingest_llm_as/utils/content_processor.py:376)).
- **Langfuse observability is optional**: Can be disabled via settings, all tracing calls check `langfuse_client.enabled` before execution.
