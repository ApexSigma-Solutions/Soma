import asyncio
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ingest_llm_as.services.memos_client import MemOSClient


async def populate_graph():
    print("🚀 Starting Graph Population...")

    foundational_data = [
        {
            "title": "OmegaKG Ecosystem",
            "content": "OmegaKG is a knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits using a dual-agent architecture (Kilo Code & Roo Code). It consists of Omega_KG (Core), memos.MCP (Bridge), and InGest-LLM.as (Ingestion).",
            "tags": ["architecture", "overview", "definition"],
        },
        {
            "title": "Mimir Protocol",
            "content": "The Mimir Protocol is a Digital Immune System for OmegaKG. It prevents recursive failures by storing 'Anti-Bodies' (constraints) in the Codex. Agents must consult Mimir (MAR) before critical actions and metabolize failures into new constraints.",
            "tags": ["protocol", "security", "mimir"],
        },
        {
            "title": "Hybrid Architecture",
            "content": "Due to Windows Docker networking limitations, OmegaKG uses a Hybrid Architecture. Data Layer (Redis, Postgres, Neo4j) runs in Docker. Logic Layer (OmegaKG, memos.MCP, InGest-LLM) runs natively on Host. Containers map ports to localhost.",
            "tags": ["architecture", "windows", "docker"],
        },
        {
            "title": "Ingest-LLM Service",
            "content": "InGest-LLM.as is the ingestion microservice. It accepts text, files, and working experiences, chunking and embedding them before sending to memOS.MCP for storage in the Knowledge Graph.",
            "tags": ["service", "ingestion", "component"],
        },
    ]

    async with MemOSClient() as client:
        # Check health
        if not await client.health_check():
            print("❌ memOS Health Check Failed!")
            return

        print("✅ memOS Health Check Passed")

        for item in foundational_data:
            print(f"📥 Ingesting: {item['title']}...")
            try:
                response = await client.store_semantic_memory(
                    content=item["content"],
                    metadata={
                        "title": item["title"],
                        "source": "dogfooding_script",
                        "tags": item["tags"],
                        "content_type": "documentation",
                    },
                )
                if response.success:
                    print(f"  ✅ Stored (ID: {response.memory_id})")
                else:
                    print(f"  ❌ Failed: {response.message}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

    print("✨ Population Complete!")


if __name__ == "__main__":
    asyncio.run(populate_graph())
