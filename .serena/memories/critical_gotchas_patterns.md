# Project Patterns & Critical Gotchas

## Hardcoded Conventions
- **AI_Conversations folder**: `AI_Conversations/{platform}/` in Obsidian vault
- **UID-based task files**: Glob pattern `f"Tasks/**/{uid}*.md"` for discovery
- **Content ID format**: `CAP-{YYYYMMDD}-{HASH}` in frontmatter
- **Platform sanitization**: `r'[<>:"|?*\x00-\x1f]'` before folder creation

## Auto-Fallback Behaviors
- **Mock mode**: Auto-switches when Neo4j connection fails
- **Embedding worker**: Polls every 10 seconds for pending embeddings
- **Session scheduler**: Batch percolation runs every 5 minutes via APScheduler
- **APScheduler fallback**: Dummy class when APScheduler unavailable

## Database Connection Patterns
- **Neo4j async driver**: Use `AsyncGraphDriver` from `omega_kg.database.graph`
- **Context managers REQUIRED**: Neo4j sessions must use async context managers
- **Dual database sync**: Tasks stored in BOTH Neo4j AND Obsidian with frontmatter sync
- **Health validation**: Connection checks use `RETURN 1` query pattern

## Task Lifecycle Automation
- **Draft → Archived**: 14 days (automatic), 10 days (warning) unless pinned
- **Active → Blocked**: 30 days without commits
- **Completed → Archived**: 90 days

## CRITICAL GOTCHAS ⚠️
1. **Encoding**: ALWAYS use `encoding="utf-8"` for file operations
2. **Vector embedding**: ChatSession nodes queue via `store_pending()` then async process
3. **JWT exchange**: Chrome extension exchanges static API key for JWT tokens
4. **Context leaks**: Neo4j sessions MUST use async context managers - NO EXCEPTIONS
5. **Global singletons**: `graph_driver = AsyncGraphDriver()` and `settings = Settings()` - use these, don't instantiate
6. **Testcontainers**: Critical filter warnings for Python 3.12+ - see pytest.ini:144-152
7. **Coverage target**: 80%+ required, currently ~46% (81 tests)
8. **Async mandatory**: All Neo4j/database operations must be async with context managers

## Key Implementation Patterns
- Follow three-tier error handling pattern
- Use snake_case for functions, PascalCase for classes
- Always include type hints and docstrings
- Use async context managers for all resource management
- Ensure UTF-8 encoding for all file operations
