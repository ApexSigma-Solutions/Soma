"""
Integration Tests - Graph Sync (TN-LINEAR-06)

Validates that LinearIssue models are correctly projected to Neo4j topology.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from neo4j.exceptions import Neo4jError

from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.domain.linear.graph_writer import GraphWriter
from omega_kg.domain.linear.models import LinearIssue, LinearState, LinearUser


@pytest_asyncio.fixture
async def graph_driver():
    """Create a fresh Neo4j driver for each test to avoid event loop issues."""
    driver = AsyncGraphDriver()
    try:
        await driver.connect()
    except (Neo4jError, OSError, TimeoutError) as e:
        pytest.skip(f"Neo4j unavailable: {e}")
    yield driver
    await driver.close()


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_graph_connectivity(graph_driver):
    """Verify we can talk to the Neo4j container."""
    assert await graph_driver.verify_connectivity() is True


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_upsert_issue_topology(graph_driver):
    """
    Test that an Issue + Assignee are correctly merged into the graph.

    Validates:
    - 1 LinearIssue node created
    - 1 LinearUser node created
    - 1 ASSIGNED_TO relationship (Issue -> User)
    """
    # 1. Setup Data - Casting UUIDs to strings explicitly
    user_id = str(uuid.uuid4())
    issue_id = str(uuid.uuid4())
    # Use unique identifiers to ensure test isolation
    issue_identifier = f"LIN-{uuid.uuid4().hex[:6].upper()}"
    user_email = f"test-{uuid.uuid4().hex[:6]}@example.com"

    assignee = LinearUser(
        id=user_id,
        name="Test User",
        email=user_email,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        active=True,
    )

    state = LinearState(
        id=str(uuid.uuid4()), name="In Progress", color="#F00", type="started"
    )

    issue = LinearIssue(
        id=issue_id,
        identifier=issue_identifier,
        title="Integration Test Issue",
        priority=1,
        state=state,
        assignee=assignee,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        url=f"http://linear.app/issue/{issue_identifier}",
    )

    # 2. Execute Graph Writer
    writer = GraphWriter(graph_driver)
    await writer.upsert_issue(issue)

    # 3. Verify in Neo4j (Read back)
    # Query Direction: (Issue)-[:ASSIGNED_TO]->(User)
    query = """
    MATCH (i:LinearIssue {identifier: $identifier})
    MATCH (u:LinearUser {email: $email})
    MATCH (i)-[r:ASSIGNED_TO]->(u)
    RETURN i, u, r
    """

    async with graph_driver.session() as session:
        result = await session.run(
            query, {"identifier": issue_identifier, "email": user_email}
        )
        record = await result.single()

        assert record is not None, "No matching Issue+User+Relationship found in graph"
        assert record["i"]["title"] == "Integration Test Issue"
        assert record["u"]["name"] == "Test User"
        assert record["r"] is not None

    # 4. Cleanup (ephemeral container usually handles this)
    async with graph_driver.session() as session:
        # Use a more memory-efficient way to clear the database if it's large,
        # though for tests we usually just delete what we created.
        await session.run(
            "MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS"
        )
