# Omega_KG: AI Coding Agent Instructions

## Project Overview

This is a general-purpose Python project managed with Poetry. The main application logic resides in the `omega_kg/` directory.

## Project Architecture & Conventions

- **Single Python package**: All code is under `omega_kg/`. Main config is in `omega_kg/settings.py` using Pydantic `BaseSettings` for all environment/config management.
- **Environment variables**: Reference `.env.example` for required variables. Keep it in sync with `Settings` fields.
- **Dependency management**: Use Poetry (`pyproject.toml`).
  - For development: `poetry install --with dev`
  - For documentation: `poetry install --with docs`
- **Testing**: Tests are located under `tests/`. Use `pytest` for all testing.
- **Documentation**: Core documentation has been migrated to `OmegaVault`.
  - Vault Root: `OmegaVault/ApexSigma/Development/Projects/OmegaKG`
  - History/Reports: `00_History/`
  - Implementation: `Implementation/`

## Workflows & Tooling

- **Linting/Formatting**: Use the project's configured linters and formatters (Ruff, Black, isort). These are available via `poetry` and enforced by `.pre-commit-config.yaml`.
- **CI/CD**: GitHub Actions run Semgrep, Trivy, Snyk, and pytest with coverage. See `.github/workflows/ci.yml` for details.
- **Pre-commit**: Enforced via `.pre-commit-config.yaml` (Black, Ruff, Flake8, Semgrep, Trivy, Snyk, ZAP, pytest, etc.).
- **MkDocs deploy**: Docs are deployed via GitHub Actions (`.github/workflows/mkdocs.yml`).

## Key Commands

- **Install dependencies**: `poetry install --with dev,docs`
- **Run tests**: `poetry run pytest`
- **Run linting and formatting**: `ruff check .` and `black .`, or run `pre-commit run --all-files`
- **Build documentation**: `mkdocs build`
- **Serve documentation locally**: `mkdocs serve`

## Patterns & Examples

- **Settings pattern**: All config must extend `omega_kg/settings.py:Settings` (Pydantic). Example usage:

```python
from omega_kg.settings import Settings
settings = Settings()
print(settings.database_url)
```

- **Adding dependencies**: Use `poetry add <package>` and update `pyproject.toml`.
- **Adding environment variables**: Update both `omega_kg/settings.py` and `.env.example`.
- **Adding Tests**: Add new tests to the `tests/` directory.
- **Adding Docs**: Add docstrings to all public classes/functions for `mkdocstrings`.

## Key Files

- `omega_kg/settings.py`: Central config (Pydantic BaseSettings)
- `.env.example`: Reference for all required env vars
- `pyproject.toml`: Poetry config
- `.pre-commit-config.yaml`: Lint/test hooks
- (Trunk removed): use `.pre-commit-config.yaml` and CI pipeline for linting and security checks
- `.github/workflows/ci.yml`: CI pipeline
- `docs/`, `mkdocs.yml`: Documentation
