import asyncio
from neo4j import GraphDatabase
from omega_kg.settings import settings


async def verify_vector():
    print(f"Connecting to Neo4j at {settings.neo4j_uri}")
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )

    target_uid = "TN-INF-005"

    try:
        with driver.session() as session:
            # 1. Check if node exists and has embedding
            print(f"Checking for Task {target_uid}...")
            result = session.run(
                """
                MATCH (t:Task {uid: $uid})
                RETURN t.uid, t.title, t.embedding IS NOT NULL as has_embedding, t.embedding as embedding
            """,
                uid=target_uid,
            )

            record = result.single()

            if not record:
                print(f"[ERROR] Task {target_uid} NOT FOUND in Neo4j.")
                return

            print(f"[OK] Task Found: {record['t.uid']} - {record['t.title']}")

            if not record["has_embedding"]:
                print(f"[ERROR] Task {target_uid} does not have an embedding.")
                return
            else:
                embedding = record["embedding"]
                print(f"[OK] Embedding found (length: {len(embedding)})")

            # 2. Run a similarity search using this embedding
            print("Running self-similarity search (should find itself)...")
            search_result = session.run(
                """
                MATCH (t:Task)
                WHERE t.embedding IS NOT NULL
                WITH t, vector.similarity(t.embedding, $vec) as sim
                WHERE sim > 0.9
                RETURN t.uid, t.title, sim
                ORDER BY sim DESC
                LIMIT 5
            """,
                vec=embedding,
            )

            found_self = False
            for r in search_result:
                print(f"Match: {r['t.uid']} (Score: {r['sim']:.4f}) - {r['t.title']}")
                if r["t.uid"] == target_uid:
                    found_self = True

            if found_self:
                print(
                    "[SUCCESS] RAG verification passed: Task is retrievable via vector search."
                )
            else:
                print(
                    "[WARNING] Task was not found in top 5 similarity results (unexpected for self-search)."
                )

    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        driver.close()


if __name__ == "__main__":
    asyncio.run(verify_vector())
