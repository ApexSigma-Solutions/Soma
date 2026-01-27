# OmegaKG Project Overview

## Project Purpose
OmegaKG is a Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits. It enables intelligent knowledge capture and task lifecycle management.

### Core Capabilities
- **Chrome Extension**: Capture conversations from Claude, ChatGPT, Gemini, and Perplexity
- **Knowledge Graph**: Neo4j-based storage with rich relationship modeling
- **Task Lifecycle**: Automated state transitions and stale task detection
- **Obsidian Integration**: Markdown-first workflow with frontmatter metadata
- **Linear Sync**: Bidirectional sync of conversations and tasks

## Technology Stack
- **Language**: Python 3.12/3.13
- **Database**: Neo4j (async driver), PostgreSQL (with SQLAlchemy + asyncpg + pgvector)
- **Web Framework**: FastAPI + Uvicorn
- **Task Queue**: APScheduler (batch percolation every 5 minutes)
- **Authentication**: JWT (PyJWT) + Passlib
- **Vector Search**: pgvector for embeddings
- **Markdown**: python-frontmatter for task metadata
- **NLP**: spaCy for text processing
- **Testing**: pytest, testcontainers (Neo4j, PostgreSQL)

## Platform
Windows-based development environment

## Key Directories (in Omega_KG_stable)
- `/omega_kg/` - Main package
- `/tests/` - Test suite (81+ tests, ~46% coverage, target: 80%+)
- `/alembic/` - Database migrations
- `/docs/` - Documentation (mkdocs)
- `/scripts/` - Utility scripts
- `/chrome-extension/` - Browser extension source
- `/monitoring/` - Monitoring utilities
- `/templates/` - FastAPI/HTML templates
