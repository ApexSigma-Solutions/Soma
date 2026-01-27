#!/usr/bin/env python
"""
Seed the Codex with initial constraints for demonstration.
"""

from omega_kg.intelligence.codex import Codex
from omega_kg.intelligence.models import Constraint, SeverityLevel
from datetime import datetime


def main():
    """Seed the Codex with the venv constraint."""
    with Codex() as codex:
        # Create the "Missing venv package" constraint
        constraint = Constraint(
            id="ENV_VERN_MISSING",
            description="Virtual environment package not installed or not activated",
            severity=SeverityLevel.CRITICAL,
            created_at=datetime.now(),
        )

        # Insert into Neo4j
        with codex._driver.session() as session:
            session.run(
                """
                CREATE (c:Constraint {
                    id: $id,
                    description: $description,
                    severity: $severity,
                    created_at: datetime($created_at)
                })
                CREATE (ctx:Context {name: 'environment'})
                CREATE (c)-[:GOVERNS]->(ctx)
            """,
                id=constraint.id,
                description=constraint.description,
                severity=constraint.severity.value,
                created_at=constraint.created_at.isoformat(),
            )

        print(f"✅ Seeded constraint: {constraint.id}")
        print(f"   Description: {constraint.description}")
        print(f"   Severity: {constraint.severity.value}")


if __name__ == "__main__":
    main()
