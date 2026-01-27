# Code Mode Rules

This file provides coding-specific guidance for agents working in Code mode.

## Project Coding Rules (Non-Obvious Only)

- **Settings are intentionally non-cached**: Always use `get_settings()` function, never import the `settings` instance directly. The `settings = get_settings()` at module level exists only for backward compatibility.
- **memOS tier mapping is opinionated**: Procedural/code content MUST route to Tier 2 - this is enforced in [`MemOSClient.store_memory`](src/ingest_llm_as/services/memos_client.py:128) via the `tier_mapping` dict.
- **apexsigma-core is a local dependency**: Path reference `../../libs/apexsigma-core` - ensure this sibling repo exists or installs will fail.
- **poml for knowledge structures**: All knowledge graph data must use XML-based POML serialization (see `prompts/` directory for examples).
- **MemOSClient uses singleton pattern**: Use `get_memos_client()` function for global instance, not direct instantiation (see [`memos_client.py:242`](src/ingest_llm_as/services/memos_client.py:242)).
- **ContentProcessor violates settings pattern**: Module-level `settings` import at line 14 bypasses non-cached design - use `get_settings()` in new code.
- **Python AST parsing with fallback**: Code processing uses AST parser but falls back to text processing on failure (see [`content_processor.py:376`](src/ingest_llm_as/utils/content_processor.py:376)).
- **Langfuse observability is optional**: Can be disabled via settings, all tracing calls check `langfuse_client.enabled` before execution.

## Code Style

- Ruff handles linting and formatting automatically via pre-commit hooks
- Run `ruff check src/ --fix` before committing
- Run `ruff format src/` before committing
- Type hints are expected - use mypy to verify: `mypy src/`

## Testing Requirements

- Tests use pytest with markers: `integration`, `e2e`, `docker`, `repository_ingestion`
- Run unit tests only: `pytest -m "not integration"`
- Integration tests require memOS running at `INGEST_MEMOS_BASE_URL`
