"""
Omega_KG Master Test Configuration

Combines:
1. Testcontainers (Infrastructure for Integration Tests)
2. Mocks & Fixtures (Data for Unit Tests)
3. Performance Monitoring (Benchmarks & Slow Test detection)

Usage:
- Unit Tests: Use 'mock_neo4j_driver', 'mock_fs'
- Integration Tests: Use 'postgres_container', 'neo4j_container', 'db_session'
"""

import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest

# CRITICAL FIX: Neo4j Driver 6.x requires explicit Auth object or helper
from neo4j import GraphDatabase, basic_auth
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.neo4j import Neo4jContainer

# --- Infrastructure Imports ---
from testcontainers.postgres import PostgresContainer

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Path Setup ---
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Constants ---
POSTGRES_IMAGE = "pgvector/pgvector:pg16"
NEO4J_IMAGE = "neo4j:5-community"


# =============================================================================
# 1. PYTEST CONFIGURATION & HOOKS
# =============================================================================


def pytest_addoption(parser):
    """Add custom CLI options."""
    parser.addoption(
        "--skip-slow", action="store_true", default=False, help="Skip slow tests"
    )
    parser.addoption(
        "--performance-threshold",
        action="store",
        default=1.0,
        type=float,
        help="Max duration (s) for perf tests",
    )
    parser.addoption(
        "--use-containers",
        action="store_true",
        default=True,
        help="Use Docker containers for integration tests",
    )


def pytest_configure(config):
    """Register markers and load env vars."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line(
        "markers", "integration: marks tests requiring DB containers"
    )
    config.addinivalue_line("markers", "unit: marks isolated unit tests")
    config.addinivalue_line("markers", "performance: marks benchmark tests")

    # Load dotenv if needed (Testcontainers usually overrides these, but good for defaults)
    try:
        from dotenv import load_dotenv

        load_dotenv(".env.test", override=True)
    except ImportError:
        pass

    # CRITICAL: Create test_vault proactively because VaultUtils checks existence at import time
    test_vault = Path("./test_vault")
    test_vault.mkdir(parents=True, exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Skip slow tests if requested."""
    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="--skip-slow specified")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# =============================================================================
# 2. GLOBAL ENVIRONMENT FIXTURES
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Sets global test environment variables.
    These are defaults; Testcontainers will override DB ports dynamically.
    """
    os.environ["APP_ENV"] = "test"
    os.environ["ZERO_TRUST_REQUIRED"] = "false"
    os.environ["LINEAR_API_KEY"] = "mock_linear_key"
    os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_key"
    os.environ["STATIC_SERVICE_TOKEN"] = "test-token-12345"

    # CRITICAL: Disable Bitwarden to prevent overwriting container creds
    if "BWS_ACCESS_TOKEN" in os.environ:
        del os.environ["BWS_ACCESS_TOKEN"]

    # Create test vault directory
    test_vault = Path("./test_vault")
    if test_vault.exists():
        shutil.rmtree(test_vault)
    test_vault.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup
    if test_vault.exists():
        shutil.rmtree(test_vault)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Classic mock fixture for Unit Tests that don't need real containers.
    """
    env_vars = {
        "APP_ENV": "test",
        "NEO4J_URI": "bolt://localhost:7687",
        "POSTGRES_SERVER": "127.0.0.1",
        "EMBEDDING_PROVIDER": "ollama",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# =============================================================================
# 3. TESTCONTAINERS (INTEGRATION INFRASTRUCTURE)
# =============================================================================


@pytest.fixture(scope="session")
def postgres_container():
    """Spins up ephemeral Postgres with pgvector."""
    logger.info(f"🐳 Starting Postgres: {POSTGRES_IMAGE}")
    # Using psycopg2 driver
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg2") as postgres:
        engine = create_engine(postgres.get_connection_url())
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        yield postgres


@pytest.fixture(scope="session")
def neo4j_container():
    """Spins up ephemeral Neo4j."""
    logger.info(f"🐳 Starting Neo4j: {NEO4J_IMAGE}")
    # Let Testcontainers handle auth configuration automatically.
    with Neo4jContainer(NEO4J_IMAGE) as neo4j:
        # The default is 'neo4j/password' which is fine for testing.
        # The driver fixture will correctly read credentials from the container.
        yield neo4j


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """
    SQLAlchemy Engine connected to the container.
    Injects connection details into os.environ for the app to pick up.
    """
    url = postgres_container.get_connection_url()

    # Dynamic Environment Injection
    os.environ["DATABASE_URL"] = url
    os.environ["POSTGRES_SERVER"] = postgres_container.get_container_host_ip()
    # CRITICAL FIX: Cast port to string because os.environ requires strings
    os.environ["POSTGRES_PORT"] = str(postgres_container.get_exposed_port(5432))

    # CRITICAL FIX: Use correct testcontainers properties (.username, .dbname, .password)
    # The 'POSTGRES_USER' attribute does not exist on the container object directly.
    os.environ["POSTGRES_USER"] = postgres_container.username
    os.environ["POSTGRES_DB"] = postgres_container.dbname
    os.environ["POSTGRES_PASSWORD"] = postgres_container.password

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def graph_driver(neo4j_container):
    """
    Neo4j Driver connected to the container.
    Injects connection details into os.environ.
    """
    # Use helper methods to get connection details
    host = neo4j_container.get_container_host_ip()
    port = neo4j_container.get_exposed_port(7687)
    url = f"bolt://{host}:{port}"

    # READ credentials directly from the container object to ensure match
    # 'testcontainers-python' sets these internal properties after start.
    # If not exposed (older versions), fall back to default 'neo4j'/'password'
    # BUT since we removed the manual override in 'neo4j_container' fixture,
    # we should rely on what the object tells us.
    username = "neo4j"
    # Note: If .password is missing on the object, it usually defaults to 'password'
    # for the python library unless configured otherwise.
    password = getattr(neo4j_container, "password", "password")

    # Update Env Vars for application code
    os.environ["NEO4J_URI"] = url
    os.environ["NEO4J_PASSWORD"] = password
    os.environ["NEO4J_USER"] = username

    logger.info(f"Connecting to Neo4j at {url} with user '{username}'")

    # CRITICAL FIX: Neo4j Driver 6.x requires explicit Auth object via basic_auth
    driver = GraphDatabase.driver(url, auth=basic_auth(username, password))

    # AUTH WARM-UP LOOP with EXPONENTIAL BACKOFF
    start_time = time.time()
    retry_delay = 2  # Start slower
    logger.info("⏳ Waiting for Neo4j Connectivity (Max 60s)...")

    # Initial sleep to let container actually boot services before we hammer it
    time.sleep(3)

    while time.time() - start_time < 60:
        try:
            driver.verify_connectivity()
            logger.info("✅ Neo4j Connection Verified!")
            break
        except Exception as e:
            # Handle Rate Limiting specifically
            if "AuthenticationRateLimit" in str(e):
                logger.warning("Rate limit hit. Waiting 5s...")
                time.sleep(5)
                continue

            if int(time.time() - start_time) % 5 == 0:
                logger.warning(f"Neo4j connection pending: {e}")

            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 5)
    else:
        driver.close()
        raise RuntimeError(f"Timed out waiting for Neo4j to be ready at {url}")

    yield driver
    driver.close()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Transactional Postgres session. Rolls back after test."""
    from sqlalchemy.orm import sessionmaker

    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def graph_session(graph_driver):
    """Neo4j session. Wipes graph BEFORE usage."""
    with graph_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        yield session


@pytest.fixture(scope="function")
async def async_db_engine(postgres_container):
    """
    Async SQLAlchemy AsyncEngine for integration tests.
    Manually constructs asyncpg URL from postgres_container details.
    Creates all tables once at session setup.
    """
    from omega_kg.models import Base

    # Extract connection details from the container
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    # Construct async URL with asyncpg driver (not psycopg2)
    async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"

    engine = create_async_engine(async_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_db_session(async_db_engine) -> AsyncGenerator:
    """
    Async database session for async integration tests.
    Tables created once at session setup in async_db_engine.
    This fixture just provides a fresh session per test.
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        async_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        # Session is cleaned up automatically


# =============================================================================
# 4. MOCK FIXTURES (UNIT TESTS)
# =============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """Mock driver for unit tests (no container needed)."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver


@pytest.fixture
def mock_file_system(tmp_path):
    """Comprehensive mock file system."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    (test_dir / "Tasks").mkdir()

    return {
        "test_dir": test_dir,
        "tasks_dir": test_dir / "Tasks",
        "write": lambda name, content: (test_dir / name).write_text(
            content, encoding="utf-8"
        ),
    }


@pytest.fixture
def mock_bitwarden_client():
    client = MagicMock()
    client.get_secret.return_value = "test-secret"
    return client


# =============================================================================
# 5. DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_task_data():
    return {
        "uid": "task-001",
        "title": "Test Task",
        "status": "draft",
        "filepath": "Tasks/Test_Task.md",
    }


@pytest.fixture
def sample_vector_data():
    """Standard embedding vectors for testing."""
    return {"similar": [0.1] * 1024, "dissimilar": [0.9] * 1024}


@pytest.fixture
def sample_frontmatter_data():
    return {
        "valid": {"content": "---\nuid: 1\n---\n# H1", "expected": {"uid": 1}},
        "invalid": {"content": "Just text", "expected": None},
    }


@pytest.fixture
def sample_lifecycle_rule_data():
    """Sample lifecycle rule data for tests that need rule examples."""
    return {
        "from_status": "draft",
        "to_status": "archived",
        "days_threshold": 14,
        "condition": "NOT t.pinned = true",
        "action": "auto",
    }


# =============================================================================
# 6. PERFORMANCE MONITORING
# =============================================================================


@pytest.fixture(autouse=True)
def performance_monitor(request):
    """Tracks test duration and warns on slow tests."""
    start_time = time.time()
    yield
    duration = time.time() - start_time

    # Check threshold for performance marked tests
    if request.node.get_closest_marker("performance"):
        threshold = request.config.getoption("--performance-threshold")
        if duration > threshold:
            pytest.fail(f"Performance test exceeded {threshold}s: {duration:.4f}s")

    # Warn on general slow tests
    if duration > 1.0 and "container" not in request.node.name:
        print(f"\nWARNING  Slow test: {request.node.name} ({duration:.2f}s)")
