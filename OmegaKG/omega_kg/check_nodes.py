from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(
    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
)
session = driver.session()

# Check all Task nodes
result = session.run("MATCH (t:Task) RETURN count(t) as count")
record = result.single()
if record:
    print(f"Total Task nodes: {record['count']}")
    if record["count"] > 0:
        # Fetch only first 5 tasks
        sample_result = session.run("MATCH (t:Task) RETURN t LIMIT 5")
        for record in sample_result:
            print(f"Task: {dict(record['t'])}")

# Check ALL nodes
query = "MATCH (n) RETURN count(n) as count, labels(n) as labels ORDER BY count DESC LIMIT 10"
result = session.run(query)
for record in result:
    print(f"Nodes with labels {record['labels']}: {record['count']}")

driver.close()
