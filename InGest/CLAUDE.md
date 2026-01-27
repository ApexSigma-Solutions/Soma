# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InGest-LLM.as is a Python 3.13 + FastAPI microservice that ingests content into **memOS.as** (multi-tier memory store). It provides REST endpoints for text ingestion, Python repository analysis, and project documentation generation with local embedding support.

## Development

```bash
# Install dependencies
poetry install

# Run development server (auto-reload)
poetry run uvicorn src.ingest_llm_as.main:app --reload

# Run with specific host/port
poetry run uvicorn src.ingest_llm_as.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

```bash
# All tests
poetry run pytest

# Specific test markers (defined in pytest.ini)
poetry run pytest -m unit              # Unit tests only
poetry run pytest -m integration       # Integration tests
poetry run pytest -m e2e               # End-to-end tests
poetry run pytest -m docker            # Tests requiring Docker
poetry run pytest -m "not integration"  # Skip integration tests

# Specific test file
poetry run pytest tests/test_memos_integration_core.py -v

# Core integration runner (checks /health first)
python scripts/testing/test-core-integration.py
```

## Docker

```bash
docker build -t ingest-llm-as .
docker run -p 8000:8000 ingest-llm-as
```

## High-Level Architecture

### Application Entry Point
- [main.py](src/ingest_llm_as/main.py) - Creates FastAPI app, includes all routers, defines `/health` endpoint

### API Routers (`src/ingest_llm_as/api/`)
| Router | Purpose |
|--------|---------|
| [ingestion.py](src/ingest_llm_as/api/ingestion.py) | `POST /ingest/text` - clean + chunk + (optional) embed → store to memOS |
| [repository.py](src/ingest_llm_as/api/repository.py) | `POST /ingest/python-repo` - repo discovery + per-file processing → memOS |
| [ecosystem.py](src/ingest_llm_as/api/ecosystem.py) | Project ecosystem analysis endpoints |
| [analysis.py](src/ingest_llm_as/api/analysis.py) | Project analysis endpoints |
| [omega_ingest.py](src/ingest_llm_as/api/omega_ingest.py) | Omega-flavored ingestion endpoints |
| [eod_logs.py](src/ingest_llm_as/api/eod_logs.py) | End-of-day logging router |

### Core Processing Pipeline
1. **Content Processing** ([content_processor.py](src/ingest_llm_as/utils/content_processor.py)):
   - `ContentProcessor` - chunks content intelligently (sentence/paragraph boundaries)
   - `process_content_with_embeddings()` - text processing with embedding generation
   - `process_python_code_with_embeddings()` - Python AST parsing with embeddings

2. **Python AST Parser** ([python_ast_parser.py](src/ingest_llm_as/parsers/python_ast_parser.py)):
   - Extracts functions, classes, imports, decorators
   - Generates searchable content for code elements
   - Calculates complexity scores

### External Services Integration
- **memOS.as Client** ([memos_client.py](src/ingest_llm_as/services/memos_client.py)):
  - HTTP client for storing content in multi-tier memory system
  - Tier mapping: WORKING="1" (Redis), EPISODIC="2" (Postgres+Qdrant), SEMANTIC="3" (Neo4j), PROCEDURAL="2" (code)

- **Repository Processor** ([repository_processor.py](src/ingest_llm_as/services/repository_processor.py)):
  - Git clone support for remote repos
  - File discovery with include/exclude patterns
  - Batch processing with progress tracking

- **Vectorizer** ([vectorizer.py](src/ingest_llm_as/services/vectorizer.py)):
  - LM Studio integration (via OpenAI-compatible API)
  - Model selection based on content type (code vs text)
  - Moving toward Ollama for local model runtime

### Observability Stack
- [langfuse_client.py](src/ingest_llm_as/observability/langfuse_client.py) - Langfuse LLM observability
- [logging.py](src/ingest_llm_as/observability/logging.py) - Structured logging (structlog)
- [metrics.py](src/ingest_llm_as/observability/metrics.py) - Prometheus metrics
- [tracing.py](src/ingest_llm_as/observability/tracing.py) - OpenTelemetry tracing

## Project Conventions

### Critical: Settings are Non-Cached
Settings are **intentionally non-cached** to avoid stale configuration issues. Always call `get_settings()` inside constructors or request-scoped code:

```python
from ingest_llm_as.config import get_settings

class MyService:
    def __init__(self):
        # CORRECT: Fresh settings on each instantiation
        settings = get_settings()
        self.base_url = settings.memos_base_url

# NEVER import settings directly at module level
# from ingest_llm_as.config import settings  # AVOID
```

### Environment Variables
- **Prefix**: `INGEST_` (see [config.py](src/ingest_llm_as/config.py))
- **Config file**: `.env` (use `.env.example` as template)
- **Key settings**:
  - `INGEST_MEMOS_BASE_URL` - memOS API endpoint
  - `INGEST_LM_STUDIO_BASE_URL` - LM Studio/Ollama endpoint
  - `INGEST_EMBEDDING_ENABLED` - Enable/disable embeddings

### memOS Tier Mapping
Code/procedural content routes to **Tier 2** (Postgres + Qdrant) by default. This mapping is opinionated and defined in `MemOSClient.store_memory()`.

### Embedding Provider
LM Studio references are legacy. The project is migrating to **Ollama** as the local model runtime. When touching embeddings, concentrate provider-specific changes in `services/vectorizer.py`.

## External Dependencies

This microservice is **self-contained** with no external library dependencies. All functionality is implemented within the service.

### memOS.as Connectivity
Configured via environment variables (see [config.py](src/ingest_llm_as/config.py)):
- `INGEST_MEMOS_BASE_URL` - API base URL
- `INGEST_MEMOS_API_KEY` - Optional authentication
- `INGEST_MEMOS_TIMEOUT` - Request timeout

## Common Issues

### Settings Not Updating
If settings appear cached, ensure you're calling `get_settings()` instead of importing the `settings` singleton at module level.

### memOS Connection Failures
Check `INGEST_MEMOS_BASE_URL` in `.env`. The health check endpoint is at `/health` relative to the base URL.

### Embedding Generation Failing
1. Verify LM Studio/Ollama is running at `INGEST_LM_STUDIO_BASE_URL`
2. Check `INGEST_LM_STUDIO_ENABLED=true`
3. Ensure the embedding model is loaded in the local runtime

## Important Files

| File | Purpose |
|------|---------|
| [main.py](src/ingest_llm_as/main.py) | FastAPI app entry point |
| [config.py](src/ingest_llm_as/config.py) | Settings configuration (non-cached) |
| [models.py](src/ingest_llm_as/models.py) | Pydantic request/response models |
| [pyproject.toml](pyproject.toml) | Poetry dependencies |
| [.env.example](.env.example) | Environment template |
