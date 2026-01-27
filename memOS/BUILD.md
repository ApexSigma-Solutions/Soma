# Build & Run Guide (v0.1.0-aligned)

## Prerequisites
- Python 3.12+
- Poetry 2.0+
- Docker (Optional)

## Quick Start (Standalone)

```powershell
# Install Dependencies
poetry install

# Run Server (Port 8768)
./scripts/run-standalone.ps1
```

## Docker Build

```powershell
docker build -t memos-mcp:latest .
docker run -p 8768:8768 memos-mcp:latest
```

## Testing

```powershell
# Run Unit Tests
poetry run pytest

# Run Integration (Requires Neo4j)
poetry run pytest -m integration
```
