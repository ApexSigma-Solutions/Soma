#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema Visualization Script

Generates a text-based visualization of the Neo4j schema including
constraints, indexes, and key relationships (TN-301).

This script demonstrates the schema in mock mode if Neo4j is not available.
"""

import sys


def main():
    """Generate and display schema visualization"""
    print("Generating Neo4j Schema Visualization...")
    print()

    from omega_kg.neo4j_schema import KnowledgeGraphSchema

    schema = KnowledgeGraphSchema()

    try:
        # Check connection status
        status = schema.get_connection_status()
        if not status["connected"]:
            print("⚠ Warning: Not connected to Neo4j. Running in mock mode.")
            print("   The visualization will not show actual database schema.")
            print()

        # Generate visualization
        visualization = schema.visualize_schema()
        print(visualization)

        # Save to file
        output_file = "schema_visualization.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(visualization)

        print()
        print(f"✓ Schema visualization saved to: {output_file}")

    except Exception as e:
        print(f"✗ Failed to generate schema visualization: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        schema.close()


if __name__ == "__main__":
    main()
