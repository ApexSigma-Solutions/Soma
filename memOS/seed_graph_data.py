from neo4j import GraphDatabase
from memos_mcp.config import settings


def seed_graph():
    uri = settings.neo4j_uri
    user = settings.neo4j_user
    password = settings.neo4j_password

    # Override shell-injected password if it doesn't match the container's known pwd
    if password == "neo4j_dev_password" or not password:
        password = "aDQUU5$@1dpuj5"

    print(f"🔗 Connecting to Neo4j at {uri} with user {user}...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))

        with driver.session() as session:
            # Create core system nodes
            print("📁 Creating core nodes...")
            session.run("""
                MERGE (o:System {name: 'OmegaKG', description: 'Agentic Knowledge Graph Ecosystem'})
                MERGE (m:Layer {name: 'memOS.MCP', description: 'Memory Operating System and Tool Bridge'})
                MERGE (p:Protocol {name: 'Mimir Protocol', description: 'Architectural Governance and Constraint Enforcement'})
                MERGE (c:Database {name: 'Codex of Consequences', description: 'Repository of historical failures and architectural constraints'})
                MERGE (i:Service {name: 'InGest-LLM', description: 'Microservice for data ingestion and memory promotion'})
                
                MERGE (o)-[:HAS_LAYER]->(m)
                MERGE (m)-[:IMPLEMENTS]->(p)
                MERGE (p)-[:USES_CODEX]->(c)
                MERGE (i)-[:PROMOTES_TO]->(m)
                MERGE (o)-[:HAS_SERVICE]->(i)
            """)

            # Create relationship to baseline technologies
            print("🛠️ Adding technology relationships...")
            session.run("""
                MATCH (o:System {name: 'OmegaKG'})
                MERGE (pg:Technology {name: 'PostgreSQL', feature: 'PGVector'})
                MERGE (n4j:Technology {name: 'Neo4j', feature: 'Labeled Property Graph'})
                MERGE (rd:Technology {name: 'Redis', feature: 'Ephemeral Memory'})
                MERGE (ol:Technology {name: 'Ollama', feature: 'Local Embeddings'})
                
                MERGE (o)-[:RUNS_ON]->(pg)
                MERGE (o)-[:RUNS_ON]->(n4j)
                MERGE (o)-[:RUNS_ON]->(rd)
                MERGE (o)-[:USES]->(ol)
            """)

        driver.close()
        print("✅ Neo4j foundational seeding complete.")
    except Exception as e:
        print(f"❌ Neo4j seeding failed: {e}")


if __name__ == "__main__":
    seed_graph()
