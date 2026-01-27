# InGest-LLM.as — Copilot instructions

## What this service is
- Python 3.13 + FastAPI microservice that ingests content into **memOS.as** (multi-tier memory store).
- Entrypoint: `src/ingest_llm_as/main.py` (creates `FastAPI()` and includes routers).

## Code map (start here)
- API routers: `src/ingest_llm_as/api/`
  - `ingestion.py` (`POST /ingest/text`) → clean + chunk + (optional) embed → store to memOS
  - `repository.py` (`POST /ingest/python-repo`) → repo discovery → per-file processing → store to memOS
  - `ecosystem.py` / `analysis.py` (project analysis endpoints)
  - `omega_ingest.py` / `omega_ingest_simple.py` (Omega-flavored endpoints)
- Core processing:
  - Content chunking + embedding hook: `src/ingest_llm_as/utils/content_processor.py`
  - Python structure extraction (AST): `src/ingest_llm_as/parsers/python_ast_parser.py`
- External integration:
  - memOS HTTP client: `src/ingest_llm_as/services/memos_client.py`
  - Repo ingestion orchestration: `src/ingest_llm_as/services/repository_processor.py`
  - Embedding adapter (provider-specific): `src/ingest_llm_as/services/vectorizer.py`

## Project conventions that matter
- **Settings are intentionally non-cached.** Prefer `from ingest_llm_as.config import get_settings` and call `get_settings()` inside constructors / request-scoped code.
  - Example: `MemOSClient.__init__` uses `get_settings()` (see `services/memos_client.py`).
  - Env file: `.env`; env prefix: `INGEST_` (see `src/ingest_llm_as/config.py`).
- **memOS tier mapping is opinionated.** Procedural/code content routes to Tier 2 (see `tier_mapping` inside `MemOSClient.store_memory`).
- **Embeddings:** LM Studio references are legacy; this project is moving to **Ollama** as the local model runtime.
  - When touching embeddings, concentrate provider-specific changes in `services/vectorizer.py` and keep callers (`ContentProcessor`) API-stable.

## Dev workflows (what maintainers actually run)
- Local dev: `poetry install` then `poetry run uvicorn src.ingest_llm_as.main:app --reload` (see `README.md`).
- Tests: `pytest` with markers defined in `pytest.ini` (e.g. `integration`, `e2e`, `docker`, `repository_ingestion`).
- Core integration runner: `scripts/run_core_integration_tests.py` (checks `/health`, then runs `tests/test_memos_integration_core.py`).
- Docker: `Dockerfile` builds and runs the service.

## External deps / gotchas
- Depends on a local workspace library: `apexsigma-core` via `../../libs/apexsigma-core` (see `pyproject.toml`).
- memOS connectivity is configured via `INGEST_MEMOS_BASE_URL` / `INGEST_MEMOS_API_KEY` / `INGEST_MEMOS_TIMEOUT` (see `src/ingest_llm_as/config.py`).
- Telemetry/observability is currently undecided—avoid adding new tracing/metrics/logging integrations while implementing features.
