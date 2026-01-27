# Code Style & Conventions

## Import Organization
Order: Standard library → Third-party → Local (with blank lines between groups)

```python
# Standard library
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Third-party
from fastapi import FastAPI, HTTPException
from neo4j import AsyncDriver
from pydantic import BaseModel, Field

# Local imports
from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.models.capture import ConversationData
```

## Type Annotations
- Full type hints on ALL function signatures
- Return types explicitly declared (even when `None`)

```python
async def connect(self) -> None:
    """Initialize connection."""
    pass

def _transition_task(session: Any, uid: str, rule: LifecycleRule) -> None:
    """Transition task state."""
    pass
```

## Naming Conventions
- **Functions**: `snake_case` → `percolate_to_neo4j()`, `_check_ollama_ready()`
- **Classes**: `PascalCase` → `AsyncGraphDriver`, `TaskLifecycle`
- **Private members**: `_prefix` → `_check_connection()`, `_driver`
- **Constants**: `UPPER_CASE` → `MAX_HTML_SIZE = 10 * 1024 * 1024`

## Error Handling (Three-Tier Pattern)
1. Specific exception catching with logging
2. Generic exceptions for expected failures
3. HTTP exceptions for API endpoints

```python
try:
    driver = GraphDatabase.driver(uri, auth=auth)
except (ServiceUnavailable, AuthError) as e:
    logger.error("Failed to connect: %s: %s", type(e).__name__, e)
    raise
```

## Async/Await Patterns
- Neo4j sessions MUST use async context managers to prevent connection leaks
- Async lifespan for FastAPI with proper cleanup

```python
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n LIMIT 1")
    record = await result.single()
```

## File Operations
- **ALWAYS** use `encoding="utf-8"` for file operations

## Docstrings
- Use docstrings for all public functions and classes
- Follow Google-style or NumPy-style docstring format
