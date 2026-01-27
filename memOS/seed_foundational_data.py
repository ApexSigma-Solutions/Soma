import asyncio
import logging
from memos_mcp.config import Settings
from memos_mcp.logic import MemosLogic
from memos_mcp.database import get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_foundational")


async def seed():
    settings = Settings()
    logic = MemosLogic(settings)
    await logic.initialize()

    print("🌱 Seeding foundational memories...")

    foundational_memories = [
        {
            "content": "OmegaKG Ecosystem Architecture: A hybrid system where Data Layer (Postgres, Neo4j, Redis) runs in Docker, and Logic Layer (OmegaKG, memOS.MCP, InGest-LLM) runs natively on the host to overcome Windows networking limitations.",
            "tags": ["architecture", "baseline", "omega_kg"],
            "metadata": {"relevance": "high", "type": "system_definition"},
        },
        {
            "content": "Mimir Protocol: A 'Digital Immune System' for OmegaKG. It enforces constraints (The Codex) derived from past failures. Agents must consult Mirmir via 'consult_mirmir' before high-risk changes.",
            "tags": ["governance", "mimir", "protocol"],
            "metadata": {"relevance": "critical", "type": "protocol_definition"},
        },
        {
            "content": "Service Port Map 2026: memOS.MCP (8768), OmegaKG Capture (8765), InGest-LLM API (8766), Postgres (6000), Redis (6379), Neo4j (7687, 7474), Ollama (11434).",
            "tags": ["infrastructure", "ports"],
            "metadata": {"relevance": "high", "type": "config"},
        },
        {
            "content": "Database Schema Standard: The ecosystem uses 'omega_kg_stable' as the primary PostgreSQL database. Schema 'public' contains core tables: memories, registered_tools, raw_conversations, and omega_vectors_1024.",
            "tags": ["database", "schema", "postgres"],
            "metadata": {"relevance": "high", "type": "config"},
        },
    ]

    for mem in foundational_memories:
        result = await logic.store(
            content=mem["content"], tags=mem["tags"], metadata=mem["metadata"]
        )
        print(f"Result: {result}")

    # Now let's try to add some graph entities if Neo4j is ready
    try:
        neo4j = get_database()  # This returns Neo4jDatabase if configured, but currently MemosLogic doesn't use it much
        # For now, we focus on the Vector/Postgres store as it's the primary retrieval path for retrieve_context
    except Exception as e:
        print(f"Neo4j seeding skipped: {e}")

    print("✅ Foundational seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
