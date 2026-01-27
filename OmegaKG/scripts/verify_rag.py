import asyncio
import httpx
import os
import sys

# Force local import of omega_kg from current directory
sys.path.insert(0, os.getcwd())

from omega_kg.vector_store import VectorStore
import inspect

print(f"DEBUG: VectorStore loaded from: {inspect.getfile(VectorStore)}")

# --- Config (Extracted from your logs) ---
DB_URL = (
    "postgresql+asyncpg://omega_user:omega_dev_password@127.0.0.1:5800/omega_kg_stable"
)
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "bge-m3:567m"


# --- Standalone Embedding Function ---
async def get_embedding_standalone(text: str):
    """Directly calls Ollama to get embeddings."""
    payload = {"model": MODEL_NAME, "prompt": text}
    async with httpx.AsyncClient() as client:
        try:
            print(f"   [DEBUG] Requesting embedding for model: {MODEL_NAME}")
            response = await client.post(OLLAMA_URL, json=payload, timeout=30.0)

            if response.status_code == 404:
                print(f"❌ Error: Model '{MODEL_NAME}' not found in Ollama.")
                return None

            response.raise_for_status()
            data = response.json()
            return data.get("embedding")
        except Exception as e:
            print(f"❌ Error talking to Ollama: {e}")
            return None


async def test_retrieval():
    print("\n--- 🧠 ALPHA-100 RAG VERIFICATION ---")

    # 1. Initialize DB Connection
    print("1. Connecting to Database (asyncpg)...")
    try:
        # Create asyncpg pool explicitly (VectorStore expects asyncpg.Pool, not SQLAlchemy Engine)
        import asyncpg
        from urllib.parse import urlparse

        # Parse DB_URL: postgresql+asyncpg://user:pass@host:port/db
        # We need raw params for asyncpg
        url = urlparse(DB_URL.replace("+asyncpg", ""))
        username = url.username
        password = url.password
        hostname = url.hostname
        port = url.port
        database = url.path[1:]

        pool = await asyncpg.create_pool(
            user=username,
            password=password,
            host=hostname,
            port=port,
            database=database,
        )

        # Inject the pool into the VectorStore
        store = VectorStore(pool=pool)

        print(f"   [OK] Connected to {database} at {hostname}:{port}")
    except Exception as e:
        print(f"❌ DB Init Failed: {e}")
        return

    # 2. Define the query
    query = "How do I setup the capture server permissions?"
    print(f"\n2. 🔎 Querying: '{query}'")

    # 3. Generate Embedding
    print("3. Generating query vector...")
    query_vec = await get_embedding_standalone(query)

    if not query_vec:
        print("❌ ABORT: Could not generate embedding vector.")
        return

    # 4. Search Postgres
    print(f"\n4. Searching with {len(query_vec)}d vector...")
    try:
        results = await store.search(query_vec, limit=5, threshold=0.4)
    except Exception as e:
        print(f"❌ Search Query Failed: {e}")
        return

    # 5. Report
    if results:
        print(f"\n✅ SUCCESS: Found {len(results)} relevant memories.")
        print("=" * 60)
        for idx, res in enumerate(results):
            # Safe access to metadata fields
            meta = res.get("metadata", {}) or {}
            source = meta.get("source", "Unknown Source")
            score = res.get("score", 0.0)
            content = res.get("content", "")

            print(f"{idx + 1}. [Score: {score:.4f}] 📄 {source}")
            print(
                f"   Context: {content[:150].replace(chr(10), ' ')}..."
            )  # Flatten newlines
            print("-" * 60)
    else:
        print("\n⚠️  FAILURE: No results found.")
        print(
            "   - Check if vectors were written (SQL: SELECT count(*) FROM omega_vectors_1024)"
        )


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(test_retrieval())
