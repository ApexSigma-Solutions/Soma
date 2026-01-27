# Omega_KG

**A Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits.**

Omega_KG enables intelligent knowledge capture and task lifecycle management by:
- Capturing AI conversations through a Chrome browser extension
- Syncing conversations and tasks bidirectionally with Linear
- Tracking implementation through Git commits
- Organizing everything in a Neo4j knowledge graph
- Enforcing task lifecycle policies with automated state transitions

## Features

### 🧠 Chrome Extension
- Capture conversations from Claude, ChatGPT, Gemini, and Perplexity
- Automatic sync to Obsidian vault
- Periodic health checks and batch percolation

### 📊 Knowledge Graph
- Neo4j-based storage with rich relationship modeling
- Links between decisions, tasks, commits, and sessions
- Query-friendly Cypher-based data model

### 🔄 Task Lifecycle Management
- Automated state transitions: draft → ready → active → blocked → completed → archived
- Time-based rules and stale task detection
- Email notifications before auto-transitions
- Linear integration for team sync

### 🎯 Obsidian Integration
- Markdown-first workflow
- Frontmatter-based task metadata
- Automatic sync with Linear updates

## Quick Start

### Prerequisites
- Python 3.13+
- Poetry
- Neo4j (local or cloud instance)
- Obsidian vault (optional, for markdown storage)

### Setup

1. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/ApexSigma-Solutions/omega_kg.git
   cd omega_kg
   poetry install --with dev
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Neo4j URI, credentials, and Obsidian vault path
   ```

3. **Run the capture server:**
   ```bash
   poetry run capture-server
   # Server runs on http://localhost:8765
   ```

4. **Install the Chrome extension:**
   - Open `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` directory

### Core Commands

```bash
# Run lifecycle enforcement (dry-run mode)
poetry run python -m omega_kg.lifecycle --dry-run

# Start capture server (entry point)
poetry run capture-server

# Reorganized Scripts (categorized by function)
# Example: Run smoke test
poetry run python scripts/testing/test-smoke.py

# Example: Verify database connectivity
poetry run python scripts/database/verify-phase2-readiness.py

# Run all tests
poetry run pytest

# Check code quality
poetry run ruff check .
poetry run mypy omega_kg/
```

## Architecture

### Modules

- **`capture_server.py`**: FastAPI server for receiving conversation captures
- **`lifecycle.py`**: Task state management and automation
- **`linear_sync.py`**: Bidirectional Linear ↔ Obsidian sync
- **`percolation.py`**: Extract commits/tasks from markdown into Neo4j
- **`settings.py`**: Pydantic-based configuration management

### Data Model

**Nodes:**
- `ChatSession`: Conversation sessions with metadata
- `Decision`: Key decisions made during sessions
- `Task`: Tasks with lifecycle state and Linear integration
- `Commit`: Git commits linked to tasks

**Relationships:**
- `ChatSession -[:CONTAINS]-> Decision`
- `Task -[:IMPLEMENTS]-> Decision`
- `Commit -[:IMPLEMENTS]-> Task`

## Configuration

Environment variables (see `.env.example`):

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Obsidian
OBSIDIAN_VAULT_PATH=./vault

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
EMAIL_TO=recipient@example.com
```

## Development

### Code Quality

Pre-commit hooks ensure code quality:
```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### Documentation

Documentation is built with MkDocs:
```bash
poetry run mkdocs serve
# View at http://localhost:8000
```

## Documentation References

- **Comprehensive Guides**: `OmegaVault/ApexSigma/development/projects/OmegaKG/` - Consolidated project documentation
- **Script Reference**: `scripts/SCRIPTS_REFERENCE.md` - Complete guide to categorized scripts
- **Governance Docs**: `docs/GOVERNANCE/` - Active development patterns

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "Add my feature"`
3. Push to remote: `git push origin feature/my-feature`
4. Open a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, feature requests, or questions:
- Open an [issue](https://github.com/ApexSigma-Solutions/omega_kg/issues)
- **Comprehensive Documentation**: `OmegaVault/ApexSigma/development/projects/OmegaKG/` - Consolidated project guides
- **Script Reference**: `scripts/SCRIPTS_REFERENCE.md` - Complete guide to categorized scripts
- **Governance Docs**: `docs/GOVERNANCE/` - Active development patterns
