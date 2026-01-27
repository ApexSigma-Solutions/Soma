#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from omega_kg.neo4j_schema import KnowledgeGraphSchema  # noqa: E402


def main():
    """Initialize Neo4j schema"""
    print("Initializing Neo4j schema...")
    schema = KnowledgeGraphSchema()
    try:
        schema.initialize_schema()
        print("SUCCESS: Neo4j schema initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize Neo4j schema: {e}")
    finally:
        schema.close()


if __name__ == "__main__":
    main()
