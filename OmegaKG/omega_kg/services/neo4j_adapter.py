from neo4j import GraphDatabase
import logging
from omega_kg.settings import settings

logger = logging.getLogger("omega.services.neo4j")


class Neo4jAdapter:
    """
    Adapter for interacting with the Neo4j Graph Database.
    Uses the official neo4j python driver.
    """

    def __init__(self):
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self._driver = None

        try:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j Driver: {e}")

    def close(self):
        if self._driver:
            self._driver.close()

    def run(self, query: str, parameters: dict = None):
        """
        Executes a Cypher query.
        """
        if not self._driver:
            logger.error("Neo4j Driver is not initialized.")
            return

        with self._driver.session() as session:
            try:
                result = session.run(query, parameters)
                # Consume result to ensure execution
                summary = result.consume()
                return summary
            except Exception as e:
                logger.error(f"Neo4j Query Failed: {e}")
                raise e
