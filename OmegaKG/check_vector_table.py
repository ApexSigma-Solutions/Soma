import asyncio
import asyncpg
from omega_kg.settings import settings
from omega_kg.config import VECTOR_TABLE_NAME


async def check_vector_status():
    print(
        f"Connecting to DB: {settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )
    try:
        conn = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            host=settings.postgres_server,
            port=settings.postgres_port,
        )

        # Check for the specific Task UID as message_id
        # Note: The percolation engine usually uses the Neo4j ElementId or UID as message_id.
        # Let's check both if possible, or just exact match on UID first if that's how it stores it.
        # Actually, looking at capture_server.py:
        # vector_id = await vector_store.store_pending(message_id=session_id, node_label="ChatSession")
        # It seems it stores Neo4j Element ID (session_id).
        # For Tasks, we need to know how they are percolated.
        # percolation.py doesn't seem to have explicit "store_pending" calls for Tasks in the code I read earlier!

        # Let's check percolation.py again (step 10).
        # percolation.py methods: _percolate_task, _percolate_commits, _percolate_session.
        # _percolate_task runs a MERGE query. It does NOT seem to call vector_store.store_pending!

        # Checking percolation.py again...
        # Lines 139-205 (_percolate_task):
        # MERGE (t:Task {uid: $uid}) ... SET ...
        # No call to vector_store.

        # This might be the issue! The percolation engine creates the nodes but doesn't queue them for embedding?
        # Or maybe there's a trigger in Neo4j? Or another process?
        # The user's prompt says "The embedding worker is polling... Once the path bug is fixed... retrievable via RAG".
        # This implies it *should* work.

        # Let's check the DB for ANY 'Task' entries.

        print(f"Checking {VECTOR_TABLE_NAME}...")
        rows = await conn.fetch(f"SELECT * FROM {VECTOR_TABLE_NAME}")
        print(f"Total rows: {len(rows)}")
        for r in rows:
            print(
                f"ID: {r['id']}, MsgID: {r['message_id']}, Label: {r['node_label']}, Status: {r['status']}"
            )

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_vector_status())
