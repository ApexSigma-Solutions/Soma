import asyncio
from memos_mcp.config import Settings
from memos_mcp.logic import MemosLogic
from memos_mcp.tools.context import retrieve_context, get_concepts


async def verify():
    settings = Settings()
    logic = MemosLogic(settings)
    await logic.initialize()

    print("\n🔍 Verifying Vector Search (retrieve_context)...")
    context = await retrieve_context(query="What is the Mimir Protocol?", limit=2)
    for res in context["long_term_memory"]:
        print(f"[{res['relevance']:.2f}] {res['content'][:100]}...")

    print("\n🔍 Verifying Graph Search (get_concepts)...")
    concepts = await get_concepts(concept_id="OmegaKG")
    if "error" in concepts:
        print(f"Error: {concepts['error']}")
    else:
        print(
            f"Found {concepts['node_count']} nodes and {len(concepts['relationships'])} relationships."
        )
        for rel in concepts["relationships"][:3]:
            print(f"  {rel['start']} -[:{rel['type']}]-> {rel['end']}")


if __name__ == "__main__":
    asyncio.run(verify())
