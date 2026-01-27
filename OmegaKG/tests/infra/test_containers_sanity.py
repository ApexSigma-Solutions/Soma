import pytest
import os
from sqlalchemy import text


@pytest.mark.integration
def test_postgres_container_is_alive(db_engine):
    """
    Verifies that the Postgres container is running, accessible,
    and has the pgvector extension enabled.
    """
    with db_engine.connect() as conn:
        # 1. Connection Check
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1, "Failed to execute simple SELECT 1 on Postgres"

        # 2. Extension Check
        # pg_extension catalog stores installed extensions
        ext_check = conn.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
        assert ext_check == 1, (
            "pgvector extension is NOT installed/enabled in the container!"
        )


@pytest.mark.integration
def test_neo4j_container_is_alive(graph_driver):
    """
    Verifies that the Neo4j container is running and writable.
    """
    with graph_driver.session() as session:
        # 1. Create a node
        session.run("CREATE (n:SanityCheck {status: 'alive'})")

        # 2. Read it back
        result = session.run("MATCH (n:SanityCheck) RETURN n.status AS status").single()

        assert result is not None, "Failed to retrieve node from Neo4j"
        assert result["status"] == "alive", "Neo4j node data mismatch"


@pytest.mark.integration
def test_environment_injection(postgres_container, db_engine):
    """
    Verifies that os.environ was updated by fixtures to point to the container
    instead of localhost.

    NOTE: We request `db_engine` here to ensure the fixture runs and patches
    the environment variables before we assert on them.
    """
    # The fixture should have updated global env vars
    assert os.environ["DATABASE_URL"] == postgres_container.get_connection_url()
    # The port should NOT be 5433 (your local dev port), but a random high port
    # Cast to str to match os.environ type
    assert os.environ["POSTGRES_PORT"] == str(postgres_container.get_exposed_port(5432))
