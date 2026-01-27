# Suggested Commands for OmegaKG Development

## Environment Setup
```powershell
# Install dependencies (includes dev tools)
poetry install --with dev

# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell
```

## Running Services
```bash
poetry run capture-server    # FastAPI capture server (port 8765)
poetry run omega --help      # CLI tools help
```

## Testing
```bash
# Run all tests
poetry run pytest

# Specific test file
poetry run pytest tests/test_capture.py

# Single test
poetry run pytest tests/test_capture.py::test_func -v

# Fast unit tests only
poetry run pytest -m "unit"

# Neo4j-dependent tests
poetry run pytest -m "requires_neo4j"

# Skip slow tests
poetry run pytest -m "not slow"

# With coverage report
poetry run pytest --cov=omega_kg --cov-report=term-missing --cov-report=html
```

## Code Quality
```bash
# Linting
poetry run ruff check .

# Lint + auto-fix
poetry run ruff check --fix .

# Format code
poetry run ruff format .

# Run all pre-commit hooks
poetry run pre-commit run --all-files

# Type checking
poetry run mypy omega_kg/

# Security linting
poetry run bandit -r .
```

## Database Migrations
```bash
# Generate migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head
```

## Development Workflow (Task Completion Checklist)
1. `poetry run ruff format .` - Format code
2. `poetry run ruff check --fix .` - Auto-fix lint issues
3. `poetry run mypy omega_kg/` - Type checking
4. `poetry run pytest --cov=omega_kg` - Tests with coverage
5. Ensure coverage ≥80% (currently ~46%)
6. `poetry run pre-commit run --all-files` - Final check before commit

## Windows-Specific
```powershell
# Navigate to main project
cd Omega_KG_stable
ls omega_kg/               # Main package
ls tests/                  # Test files
```
