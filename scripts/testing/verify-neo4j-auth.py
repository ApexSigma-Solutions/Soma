from neo4j import GraphDatabase
import sys

uri = "bolt://localhost:7687"
user = "neo4j"
password = "LMKXBmMtMMRnAdeotR81FEIZ2UFnD0Ec"

try:
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
