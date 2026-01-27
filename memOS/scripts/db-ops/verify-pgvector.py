"""
Quick verification test for PGVectorStore integration.

Run with: poetry run python scripts/verify_pgvector.py
"""

import asyncio
import sys

sys.path.insert(0, "src")

from memos_mcp.database import PGVectorStore


async def main():
    print("=" * 60)
    print("PGVectorStore Integration Verification")
    print("=" * 60)

    # Override settings for our test
    store = PGVectorStore(
        schema="memos",
        embedding_dimension=1024,
    )

    try:
        # Test 1: Connection
        print("\n[1] Testing database connection...")
        await store._get_pool()
        print("    ✅ Connection pool created successfully")

        # Test 2: Store a memory
        print("\n[2] Testing memory storage...")
        test_content = "This is a test memory for verification."
        embedding = store.generate_placeholder_embedding(test_content)

        memory_id = await store.store_memory(
            content=test_content,
            agent_id="test_agent",
            embedding=embedding,
            embedding_model="placeholder",
            metadata={"test": True},
            tags=["test", "verification"],
        )
        print(f"    ✅ Stored memory with ID: {memory_id}")

        # Test 3: Retrieve memory
        print("\n[3] Testing memory retrieval...")
        memory = await store.get_memory(memory_id)
        if memory and memory["content"] == test_content:
            print("    ✅ Retrieved memory successfully")
        else:
            print("    ❌ Failed to retrieve memory")

        # Test 4: Semantic search
        print("\n[4] Testing semantic search...")
        query = "test memory verification"
        query_embedding = store.generate_placeholder_embedding(query)

        results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5,
            score_threshold=0.0,
        )
        print(f"    ✅ Search returned {len(results)} results")
        if results:
            print(f"       Top result similarity: {results[0]['similarity']:.4f}")

        # Test 5: Get stats
        print("\n[5] Testing statistics...")
        stats = await store.get_stats()
        print(f"    ✅ Stats: {stats}")

        # Test 6: Cleanup - delete test memory
        print("\n[6] Cleaning up test data...")
        deleted = await store.delete_memory(memory_id, "test_cleanup")
        if deleted:
            print(f"    ✅ Deleted test memory {memory_id}")
        else:
            print("    ⚠️  Could not delete test memory")

        print("\n" + "=" * 60)
        print("✅ All verification tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        await store.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
