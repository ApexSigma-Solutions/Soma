# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## First steps for agents

1. Read `.github/instructions/copilot-instructions.md` for a concise, repo-focused guide.
2. Read `.roo/rules-architect/AGENTS.md` for non-obvious architecture rules and constraints.
3. Review `README.md` and `.env.example` to set up local environment before running anything.

## Build & Test Commands

- **Install dependencies**: `poetry install --with dev`
- **Run single test**: `poetry run pytest tests/test_filename.py::test_function_name`
- **Run tests with coverage**: `poetry run pytest --cov=omega_kg`
- **Lint code**: `poetry run ruff check .`
- **Format code**: `poetry run ruff format .`
- **Type checking**: `poetry run mypy omega_kg/`
- **Pre-commit hooks**: `poetry run pre-commit run --all-files`

## Critical Project-Specific Patterns

### Hardcoded Conventions
- **AI_Conversations folder**: Capture server writes to hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:204)
- **Task file naming**: Tasks use UID-based naming in `Tasks/` directory with glob pattern `f"Tasks/**/{uid}*.md"` (lifecycle.py:358)

### Mock Mode Behavior
- **Auto-fallback**: System automatically switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Mock data**: Lifecycle enforcement returns predefined mock results when no database connection (lifecycle.py:231-260)

### Authentication & Security
- **JWT tokens**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:389-410)
- **Environment-based configuration**: ALL configuration loaded from .env file using .env.example as template - no hardcoded secrets in code (settings.py:16-18)
- **Portable configuration**: Copy .env.example to .env and fill values - application reads all settings from environment variables (settings.py:16-18)

### Agent guidance
- Always update `.env.example` whenever `settings.py` adds or removes a required environment variable. The `.env.example` is the canonical model for settings and helps agents know which keys to expect.
- Avoid duplicating `.env` values in source or in docs; always use `.env.example` + local `.env` file for runtime secrets and local paths.
- Pydantic uses `.env` at runtime via `settings.py`'s `env_file`. Treat `.env.example` as the schema/default model used for onboarding and automated checks.

### Database Patterns
- **Dual persistence**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter sync (lifecycle.py:317-391)
- **Session management**: All Neo4j operations use context manager pattern `with driver.session() as session:`
- **Health checks**: Connection validation via `RETURN 1` query before operations (lifecycle.py:138)

### Task Lifecycle Rules
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

### Scripts & Entry Points
- **CLI**: `omega` command via `omega_kg.cli:cli`
- **Capture server**: `capture-server` command via `omega_kg.capture_server:main` (runs on port 8765)
- **Lifecycle enforcement**: `python -m omega_kg.lifecycle --dry-run`
- **Functional Scripts**: Reorganized into `scripts/` subdirectories:
  - `db-ops/`: Database sync and percolation (e.g., `sync-linear.py`)
  - `maintenance/`: Environment and hook management (e.g., `setup-venv.ps1`)
  - `troubleshooting/`: Diagnostic tools (e.g., `diagnose-capture.ps1`)
  - `testing/`: Smoke and integration tests (e.g., `test-smoke.py`)
  - `startup/`: Development and service startup (e.g., `start-dev.ps1`)

## Code Style Guidelines

- **Type hints**: Required for all functions (mypy configured with `disallow_untyped_defs = false` but `check_untyped_defs = true`)
- **Docstrings**: Google-style docstrings with parameter descriptions
- **Logging**: Use `logger = logging.getLogger(__name__)` pattern
- **Error handling**: Specific exception types (ServiceUnavailable, AuthError, ConnectionError)
- **Import order**: Standard library, third-party, local imports

## Testing Requirements

- **Test markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.requires_neo4j`
- **Mock fixtures**: Use `mock_env_vars`, `mock_neo4j_driver`, `task_lifecycle_mock` from conftest.py
- **Test vault**: Tests create `./test_vault` directory automatically
- **Neo4j tests**: Mark with `requires_neo4j` and provide mock driver when possible

## Critical Gotchas

- **Settings validation**: Pydantic fails fast on missing required env vars (settings.py:108-119)
- **File encoding**: Always use `encoding="utf-8"` for file operations
- **Date handling**: Use `datetime.now().isoformat()` for consistent timestamps
- **CORS configuration**: Chrome extension ID must match exactly in CORS origins (capture_server.py:68)
- **Pre-commit hooks**: Custom hooks prevent root-level test scripts and bytecode files
- **Environment setup**: Application requires .env file based on .env.example template for all configuration