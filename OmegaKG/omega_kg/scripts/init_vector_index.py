"""
Neo4j Vector Index Initialization

Creates the 1024-dimension cosine similarity index for LinearIssue embeddings.
This script is idempotent - safe to run multiple times.

Phase 7: TN-LINEAR-07 - The Enrichment (Embeddings)

Usage:
    python -m omega_kg.scripts.init_vector_index
"""

import logging
import os

from neo4j import GraphDatabase
from neo4j.exceptions import ClientError

logger = logging.getLogger(__name__)

# Index configuration
INDEX_NAME = "linear_issue_embeddings"
NODE_LABEL = "LinearIssue"
EMBEDDING_PROPERTY = "embedding"
VECTOR_DIMENSIONS = 1024
SIMILARITY_FUNCTION = "cosine"


def ensure_vector_index() -> bool:
    """
    Create the vector index for LinearIssue embeddings if it doesn't exist.

    The index is created with:
    - 1024 dimensions (matches BAAI bge-m3 output)
    - Cosine similarity function

    Returns:
        True if index was created or already exists, False on failure

    Raises:
        RuntimeError: If NEO4J_PASSWORD is not set
    """
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD environment variable is required")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Neo4j 5.x vector index creation syntax
    cypher = f"""
    CREATE VECTOR INDEX {INDEX_NAME} IF NOT EXISTS
    FOR (n:{NODE_LABEL}) ON (n.{EMBEDDING_PROPERTY})
    OPTIONS {{
        indexConfig: {{
            `vector.dimensions`: {VECTOR_DIMENSIONS},
            `vector.similarity_function`: '{SIMILARITY_FUNCTION}'
        }}
    }}
    """

    try:
        with driver.session() as session:
            logger.info(
                f"Ensuring Neo4j vector index '{INDEX_NAME}' exists "
                f"({VECTOR_DIMENSIONS}-dim, {SIMILARITY_FUNCTION})..."
            )
            session.run(cypher)
            logger.info(f"Vector index '{INDEX_NAME}' is ready")
            return True
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in str(e):
            logger.info(f"Vector index '{INDEX_NAME}' already exists")
            return True
        logger.error(f"Failed to create vector index: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating vector index: {e}")
        return False
    finally:
        driver.close()


def verify_index_status() -> dict:
    """
    Check the status of the vector index.

    Returns:
        Dict with index status info or empty dict if index not found
    """
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_password:
        return {"error": "NEO4J_PASSWORD not set"}

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        with driver.session() as session:
            result = session.run(
                """
                SHOW INDEXES
                WHERE name = $index_name
                RETURN name, state, type, labelsOrTypes, properties
                """,
                {"index_name": INDEX_NAME},
            )
            record = result.single()
            if record:
                return {
                    "name": record["name"],
                    "state": record["state"],
                    "type": record["type"],
                    "labels": record["labelsOrTypes"],
                    "properties": record["properties"],
                }
            return {"error": f"Index '{INDEX_NAME}' not found"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TN-LINEAR-07: Neo4j Vector Index Initialization")
    print("=" * 60)

    success = ensure_vector_index()

    if success:
        status = verify_index_status()
        print(f"\nIndex Status: {status}")
        print("\n✅ Vector index setup complete!")
    else:
        print("\n❌ Failed to create vector index. Check logs for details.")
        exit(1)
