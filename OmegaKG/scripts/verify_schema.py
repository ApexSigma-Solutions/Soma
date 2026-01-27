#!/usr/bin/env python
"""Verify Neo4j schema constraints and indexes."""

from neo4j import GraphDatabase

from omega_kg.settings import settings


def main():
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        # List all constraints
        result = session.run(
            "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties"
        )
        print("=== TNP-HIGH VELOCITY SPRINT CONSTRAINTS ===")
        constraints = list(result)
        if not constraints:
            print("  No constraints found")
        for record in constraints:
            print(
                f"  {record['name']}: {record['type']} on {record['labelsOrTypes']} ({record['properties']})"
            )
        print()

        # List all indexes
        result = session.run("SHOW INDEXES YIELD name, labelsOrTypes, properties")
        print("=== ALL INDEXES ===")
        indexes = list(result)
        if not indexes:
            print("  No indexes found")
        for record in indexes:
            print(
                f"  {record['name']}: ON {record['labelsOrTypes']} ({record['properties']})"
            )
        print()

        # Test relationship creation
        print("=== TESTING RELATIONSHIP QUERIES ===")
        try:
            session.run("""
                MATCH ()-[r:TRIGGERS]->()
                RETURN count(r) as trigger_count
            """)
            print("  ✓ TRIGGERS relationship query: OK")
        except Exception as e:
            print(f"  ✗ TRIGGERS relationship query: {e}")

        try:
            session.run("""
                MATCH ()-[r:BELONGS_TO]->()
                RETURN count(r) as belongs_count
            """)
            print("  ✓ BELONGS_TO relationship query: OK")
        except Exception as e:
            print(f"  ✗ BELONGS_TO relationship query: {e}")

    driver.close()
    print("\n✓ Schema verification complete")


if __name__ == "__main__":
    main()
