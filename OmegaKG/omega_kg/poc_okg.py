# proof_of_concept.py

from neo4j import GraphDatabase, exceptions

# --- CONFIGURATION ---
# This URI points to the Bolt port of your Docker container.
URI = "bolt://localhost:7687"
# This is the password you set in your docker-compose.yml file.
AUTH = ("neo4j", "please-change-this-password")

# --- DATA ---
# This is a manual transcription of key decisions from our recent conversations.
# This simulates the data we will eventually automate.
sessions = [
    {
        "date": "2025-10-19",
        "topic": "Initial Monorepo Stabilization",
        "decisions": [
            "Eliminate wildcard dependencies in tools.as",
            "Remediate 17 Dependabot security vulnerabilities",
        ],
        "implements": [
            "wildcard_version_elimination",
            "security_vulnerability_remediation",
        ],
    },
    {
        "date": "2025-10-20",
        "topic": "Vault Integration Blocking",
        "decisions": [
            "Migrate InGest-LLM to Python 3.13",
            "Eliminate hardcoded postgres_password anti-pattern",
        ],
        "implements": ["python_migration_313", "hardcoded_secret_anti_pattern"],
    },
    {
        "date": "2025-10-21",
        "topic": "Unified Knowledge Architecture",
        "decisions": [
            "Pivot to a Unified OKG, halting parallel work",
            "Prioritize Obsidian -> Neo4j bridge over chat parsing",
            "Adopt Helheim Protocol for all new plans",
        ],
        "implements": ["okg_first_mandate", "helheim_protocol"],
    },
]


# --- SCRIPT LOGIC ---
def run_poc():
    """Connects to Neo4j, clears old data, loads new data, and runs a validation query."""
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            # Verify connection
            driver.verify_connectivity()
            print("✅ Connection to Neo4j successful.")

            with driver.session() as session:
                # 1. Clean Slate: Wipe the database to ensure a fresh start.
                print("🧹 Clearing existing database...")
                session.run("MATCH (n) DETACH DELETE n")

                # 2. Ingest Data: Create nodes and relationships from our manual data.
                print("🧠 Ingesting manually transcribed knowledge...")
                for chat in sessions:
                    session.run(
                        """
                        // Create the ChatSession node
                        CREATE (s:ChatSession {date: date($date), topic: $topic})
                        WITH s
                        // Loop through the decisions from this session
                        UNWIND $decisions as decision_text
                        // Create a Decision node for each
                        CREATE (d:Decision {content: decision_text})
                        // Link the session to the decision it contains
                        CREATE (s)-[:CONTAINS]->(d)
                    """,
                        date=chat["date"],
                        topic=chat["topic"],
                        decisions=chat["decisions"],
                    )
                print(f"   - Ingested {len(sessions)} chat sessions.")

                # 3. Validate with a Query: Ask the graph a meaningful question.
                print(
                    "❓ Running validation query: 'What decisions were made since Oct 20th?'"
                )
                result = session.run(
                    """
                    MATCH (s:ChatSession)-[:CONTAINS]->(d:Decision)
                    WHERE s.date >= date('2025-10-20')
                    RETURN s.topic AS topic, s.date AS date, collect(d.content) AS decisions
                    ORDER BY date
                """
                )

                # 4. Display Results: Print the answer from the graph.
                print("\n--- QUERY RESULTS ---")
                for record in result:
                    print(f"📌 Topic: {record['topic']}")
                    for decision in record["decisions"]:
                        print(f"   - {decision}")
                print("---------------------\n")
                print(
                    "✅ Proof-of-Concept complete. The graph is queryable and provides value."
                )

    except exceptions.AuthError as e:
        print(
            f"❌ Authentication Error: {e}. Check your password in the script and docker-compose.yml."
        )
    except exceptions.ServiceUnavailable as e:
        print(
            f"❌ Connection Error: {e}. Is the Neo4j container running? Check 'docker ps'."
        )
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    run_poc()
