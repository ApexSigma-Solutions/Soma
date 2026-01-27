"""
Neo4j Schema Initialization
Creates constraints and indexes with connection recovery
"""

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from omega_kg.settings import settings


class ConnectionError(Exception):
    """Raised when Neo4j connection cannot be established"""

    pass


class KnowledgeGraphSchema:
    """Initialize Neo4j schema with connection health checks"""

    def __init__(self, mock_mode: bool = False) -> None:
        """
        Create a KnowledgeGraphSchema and, unless mock_mode is True, attempt to establish and verify a Neo4j driver connection.

        Parameters:
            mock_mode (bool): If True, skip creating a Neo4j driver and leave the instance in mock mode.

        Details:
            When mock_mode is False, the initializer attempts to create a Neo4j driver using configured settings and runs a health check. On successful connection the driver is stored on the instance. If connection or authentication fails, the instance switches to mock mode and the driver is set to None.
        """
        self.driver = None
        self.mock_mode = mock_mode

        if not mock_mode:
            try:
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                # Test the connection
                self._check_connection()
                print("✓ Neo4j connection established")
            except (ServiceUnavailable, AuthError, ConnectionError) as e:
                print(f"✗ Failed to connect to Neo4j: {e}")
                print("⚠ Schema initialization skipped (mock mode)")
                self.mock_mode = True
                self.driver = None

    def _check_connection(self) -> bool:
        """
        Verify that the configured Neo4j driver can run a simple test query.

        Returns:
            `true` if the driver executed the test query successfully.

        Raises:
            ConnectionError: If no driver is initialized or the test query fails; includes underlying error details.
        """
        if not self.driver:
            raise ConnectionError("Driver not initialized")

        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as status")
                _ = result.single()
                return True
        except Exception as e:
            raise ConnectionError(f"Connection health check failed: {e}")

    def get_connection_status(self) -> dict[str, bool | str]:
        """
        Report the current Neo4j connection state and related metadata.

        Returns:
            dict: Mapping with connection details:
                - "connected": `True` if a live driver exists and mock mode is not active, `False` otherwise.
                - "mock_mode": `True` if the instance is operating in mock mode, `False` otherwise.
                - "uri": The Neo4j URI when not in mock mode, or the string "mock://local" when in mock mode.
        """
        return {
            "connected": self.driver is not None and not self.mock_mode,
            "mock_mode": self.mock_mode,
            "uri": (settings.neo4j_uri if not self.mock_mode else "mock://local"),
        }

    def initialize_schema(self) -> None:
        """
        Create the required Neo4j schema for the knowledge graph.

        When a live Neo4j driver is available, this creates database constraints and indexes:
        - Constraint: Task.uid is unique
        - Constraint: Plan.id is unique
        - Index: Task.status
        - Index: Task.created

        TNP-High Velocity Sprint Raw Data Lake Schema Extensions:
        - Constraint: CodeBlock.hash IS UNIQUE
        - Constraint: ErrorLog (error_type, timestamp) NODE KEY
        - Constraint: Concept.normalized_name IS UNIQUE
        - Constraint: File.path IS UNIQUE
        - Constraint: LinearIssue.id IS UNIQUE
        - Relationship: LinearIssue-[:TRIGGERS]->ErrorLog
        - Relationship: CodeBlock-[:BELONGS_TO]->File

        If running in mock mode or no driver is available, the method makes no changes.
        """
        if self.mock_mode:
            print("⚠ Schema initialization skipped (mock mode)")
            return

        if not self.driver:
            print("✗ No database connection available")
            return

        try:
            with self.driver.session() as session:
                # Drop old constraints that reference uid-based schema
                session.run("DROP CONSTRAINT task_uid IF EXISTS")
                session.run("DROP CONSTRAINT plan_id IF EXISTS")

                # Create new UNIQUE constraints on the new Golden Schema 'id' property
                labels = ["Task", "TaskPlan", "ADR", "BacklogPlan", "Plan"]
                for label in labels:
                    name = f"{label.lower()}_id"
                    session.run(
                        f"""
                        CREATE CONSTRAINT {name} IF NOT EXISTS
                        FOR (n:{label}) REQUIRE n.id IS UNIQUE
                    """
                    )

                # Intelligence Layer constraints
                session.run(
                    """
                    CREATE CONSTRAINT constraint_id IF NOT EXISTS
                    FOR (n:Constraint) REQUIRE n.id IS UNIQUE
                """
                )

                session.run(
                    """
                    CREATE CONSTRAINT context_name IF NOT EXISTS
                    FOR (n:Context) REQUIRE n.name IS UNIQUE
                """
                )

                session.run(
                    """
                    CREATE CONSTRAINT incident_id IF NOT EXISTS
                    FOR (n:Incident) REQUIRE n.id IS UNIQUE
                """
                )

                # High-Fidelity Context Extraction constraints (TN-301)
                # CodeBlock: unique by hash for deduplication
                session.run(
                    """
                    CREATE CONSTRAINT codeblock_hash IF NOT EXISTS
                    FOR (n:CodeBlock) REQUIRE n.hash IS UNIQUE
                """
                )

                # ErrorLog: unique by id (id should be constructed from error_type + timestamp)
                session.run(
                    """
                    CREATE CONSTRAINT errorlog_id IF NOT EXISTS
                    FOR (n:ErrorLog) REQUIRE n.id IS UNIQUE
                """
                )

                # Concept: unique by normalized name
                session.run(
                    """
                    CREATE CONSTRAINT concept_name IF NOT EXISTS
                    FOR (n:Concept) REQUIRE n.name IS UNIQUE
                """
                )

                # File: unique by path
                session.run(
                    """
                    CREATE CONSTRAINT file_path IF NOT EXISTS
                    FOR (n:File) REQUIRE n.path IS UNIQUE
                """
                )

                # LinearIssue: unique by id
                session.run(
                    """
                    CREATE CONSTRAINT linearissue_id IF NOT EXISTS
                    FOR (n:LinearIssue) REQUIRE n.id IS UNIQUE
                """
                )

                # ===== TNP-High Velocity Sprint Raw Data Lake Schema =====
                #
                # Node Types for High-Fidelity Context Extraction:
                # - CodeBlock: Source code blocks with content hash for deduplication
                # - ErrorLog: Structured error entries with composite key (error_type, timestamp)
                # - Concept: Normalized concept names for semantic linking
                # - File: Source files with path as unique identifier
                # - LinearIssue: Issue tracker nodes (already exists, adding constraint)

                # CodeBlock: Unique constraint on content hash
                session.run(
                    """
                    CREATE CONSTRAINT codeblock_hash IF NOT EXISTS
                    FOR (n:CodeBlock) REQUIRE n.hash IS UNIQUE
                """
                )

                # ErrorLog: Composite unique constraint using composite_id (error_type + timestamp hash)
                # Note: NODE KEY requires Enterprise Edition. Using composite string key as workaround.
                session.run(
                    """
                    CREATE CONSTRAINT errorlog_composite IF NOT EXISTS
                    FOR (n:ErrorLog) REQUIRE n.composite_id IS UNIQUE
                """
                )

                # Concept: Unique constraint on normalized name
                session.run(
                    """
                    CREATE CONSTRAINT concept_name IF NOT EXISTS
                    FOR (n:Concept) REQUIRE n.normalized_name IS UNIQUE
                """
                )

                # File: Unique constraint on file path
                session.run(
                    """
                    CREATE CONSTRAINT file_path IF NOT EXISTS
                    FOR (n:File) REQUIRE n.path IS UNIQUE
                """
                )

                # LinearIssue: Unique constraint on id (already referenced in task)
                session.run(
                    """
                    CREATE CONSTRAINT linearissue_id IF NOT EXISTS
                    FOR (n:LinearIssue) REQUIRE n.id IS UNIQUE
                """
                )

                # Indexes for common query patterns
                session.run(
                    """
                    CREATE INDEX errorlog_type IF NOT EXISTS
                    FOR (e:ErrorLog) ON (e.error_type)
                """
                )

                session.run(
                    """
                    CREATE INDEX errorlog_timestamp IF NOT EXISTS
                    FOR (e:ErrorLog) ON (e.timestamp)
                """
                )

                session.run(
                    """
                    CREATE INDEX concept_category IF NOT EXISTS
                    FOR (c:Concept) ON (c.category)
                """
                )

                session.run(
                    """
                    CREATE INDEX codeblock_language IF NOT EXISTS
                    FOR (c:CodeBlock) ON (c.language)
                """
                )

                # ===== Relationship Type Definitions =====
                # Note: Relationship type indexes are not supported in Neo4j Community Edition
                # The following relationship types are defined for semantic integrity:
                # - TRIGGERS: LinearIssue -> ErrorLog (error causation tracking)
                # - BELONGS_TO: CodeBlock -> File (code location tracking)

                # Indexes - keep commonly used indexes for Task
                session.run(
                    """
                    CREATE INDEX task_status IF NOT EXISTS
                    FOR (t:Task) ON (t.status)
                """
                )

                # Support both older 'created' and new 'created_at' fields during migration
                session.run(
                    """
                    CREATE INDEX task_created IF NOT EXISTS
                    FOR (t:Task) ON (t.created)
                """
                )

                session.run(
                    """
                    CREATE INDEX task_created_at IF NOT EXISTS
                    FOR (t:Task) ON (t.created_at)
                """
                )

                # Indexes for new high-fidelity nodes (TN-301)
                session.run(
                    """
                    CREATE INDEX errorlog_error_type IF NOT EXISTS
                    FOR (e:ErrorLog) ON (e.error_type)
                """
                )

                session.run(
                    """
                    CREATE INDEX errorlog_timestamp IF NOT EXISTS
                    FOR (e:ErrorLog) ON (e.timestamp)
                """
                )

                print(
                    "✓ Schema initialized successfully (TNP-High Velocity Sprint extensions included)"
                )

        except ServiceUnavailable as e:
            print(f"✗ Database connection lost: {e}")
            print(f"💡 Tip: Ensure Neo4j is running on {settings.neo4j_uri}")
        except Exception as e:
            print(f"✗ Schema initialization failed: {e}")

    def create_sample_relationships(self) -> None:
        """
        Create a small set of example nodes & relationships for demo / onboarding.

        This is intentionally lightweight: if running in mock mode the method is
        a no-op; if a live driver is available we create a minimal sample graph.

        Includes examples of new high-fidelity relationships (TN-301):
        - (:LinearIssue)-[:TRIGGERS]->(:ErrorLog)
        - (:CodeBlock)-[:BELONGS_TO]->(:File)
        """
        if self.mock_mode or not self.driver:
            print("⚠ create_sample_relationships skipped (mock mode or no driver)")
            return

        try:
            with self.driver.session() as session:
                # Create example Task and ADR nodes with a relationship for demos
                session.run(
                    """
                    MERGE (t:Task {id: 'SAMPLE-TASK-1'})
                    SET t.title = 'Sample Task', t.status = 'active'
                    MERGE (a:ADR {id: 'SAMPLE-ADR-1'})
                    SET a.title = 'Sample ADR'
                    MERGE (t)-[:RELATED_TO]->(a)
                """
                )

                # TN-301: Example high-fidelity context relationships
                session.run(
                    """
                    MERGE (li:LinearIssue {id: 'SAMPLE-ISSUE-1'})
                    SET li.title = 'Sample Linear Issue', li.description = 'Example issue'
                    MERGE (el:ErrorLog {id: 'ERROR-001'})
                    SET el.error_type = 'RuntimeError', 
                        el.timestamp = datetime(),
                        el.message = 'Sample error message'
                    MERGE (li)-[:TRIGGERS]->(el)
                """
                )

                session.run(
                    """
                    MERGE (f:File {path: '/src/example.py'})
                    SET f.name = 'example.py', f.extension = 'py'
                    MERGE (cb:CodeBlock {hash: 'abc123def456'})
                    SET cb.content = 'def example(): pass',
                        cb.language = 'python',
                        cb.start_line = 1,
                        cb.end_line = 1
                    MERGE (cb)-[:BELONGS_TO]->(f)
                """
                )
            print("✓ Sample relationships created (demo data)")
        except Exception as e:
            print(f"✗ Failed to create sample relationships: {e}")

    def visualize_schema(self) -> str:
        """
        Generate a text-based visualization of the Neo4j schema.

        Returns:
            str: A formatted string representation of the schema including
                 node labels with their constraints and key relationships.
        """
        if self.mock_mode or not self.driver:
            return "⚠ Schema visualization unavailable (mock mode or no driver)"

        try:
            with self.driver.session() as session:
                # Get all constraints
                constraints_result = session.run("SHOW CONSTRAINTS")
                constraints = list(constraints_result)

                # Get all indexes
                indexes_result = session.run("SHOW INDEXES")
                indexes = list(indexes_result)

                # Build visualization
                viz = ["=" * 80]
                viz.append("Neo4j Schema Visualization")
                viz.append("=" * 80)
                viz.append("")

                # Group constraints by label
                # Note: This assumes constraint names follow the pattern "{label}_{property}"
                # where label is lowercase. This matches the naming convention used in initialize_schema()
                constraint_map = {}
                for c in constraints:
                    # Extract label from constraint details
                    name = c.get("name", "")
                    label = name.split("_")[0].title() if "_" in name else "Unknown"
                    if label not in constraint_map:
                        constraint_map[label] = []
                    constraint_map[label].append(c)

                # Display nodes with constraints
                viz.append("NODE LABELS WITH CONSTRAINTS:")
                viz.append("-" * 80)
                for label in sorted(constraint_map.keys()):
                    viz.append(f"\n({label})")
                    for constraint in constraint_map[label]:
                        constraint_name = constraint.get("name", "N/A")
                        viz.append(f"  ├─ CONSTRAINT: {constraint_name}")

                viz.append("")
                viz.append("-" * 80)
                viz.append("KEY RELATIONSHIPS:")
                viz.append("-" * 80)

                # Document the key relationships
                relationships = [
                    "(:Task)-[:RELATED_TO]->(:ADR)",
                    "(:LinearIssue)-[:TRIGGERS]->(:ErrorLog)  [TN-301]",
                    "(:CodeBlock)-[:BELONGS_TO]->(:File)  [TN-301]",
                ]

                for rel in relationships:
                    viz.append(f"  • {rel}")

                viz.append("")
                viz.append("-" * 80)
                viz.append("INDEXES:")
                viz.append("-" * 80)

                # Display indexes
                for idx in indexes:
                    idx_name = idx.get("name", "N/A")
                    viz.append(f"  • {idx_name}")

                viz.append("")
                viz.append("=" * 80)

                return "\n".join(viz)

        except Exception as e:
            return f"✗ Failed to generate schema visualization: {e}"

    def close(self) -> None:
        """
        Close the Neo4j driver if one is open.

        Does nothing when running in mock mode or if the driver is already None/closed.
        """
        if self.driver:
            self.driver.close()


def main() -> None:
    """
    CLI entry point to initialize the Neo4j schema and report connection status.

    Creates a KnowledgeGraphSchema, performs schema initialization according to command-line options, prints whether a real Neo4j connection or mock mode is in use, and ensures the driver is closed on exit.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Neo4j schema")
    parser.add_argument(
        "--skip-on-error",
        action="store_true",
        help="Skip if database unavailable",
    )
    parser.parse_args()

    schema = KnowledgeGraphSchema()

    # Print connection status
    status = schema.get_connection_status()
    if status["connected"]:
        print(f"✓ Connected to Neo4j: {status['uri']}")
    else:
        print("⚠ Running in mock mode (no Neo4j connection)")

    try:
        schema.initialize_schema()
    finally:
        schema.close()


if __name__ == "__main__":
    main()
