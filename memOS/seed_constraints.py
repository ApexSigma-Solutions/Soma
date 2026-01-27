import asyncio
from memos_mcp.config import Settings
from memos_mcp.logic import MemosLogic


async def seed_constraints():
    settings = Settings()
    logic = MemosLogic(settings)
    await logic.initialize()

    print("🛡️ Seeding Mimir Constraints...")

    constraints = [
        {
            "content": "CONSTRAINT-001: Never modify .env files without verifying the service port mapping against start_ecosystem.ps1. Improper mapping causes ecosystem-wide communication failure.",
            "tags": ["constraint", "mimir", "config"],
            "metadata": {"priority": "critical", "type": "codex_entry"},
        },
        {
            "content": "CONSTRAINT-002: Always use encoding='utf-8' for file operations to prevent Windows-specific CP1252/Unicode errors in agentic runners.",
            "tags": ["constraint", "mimir", "encoding"],
            "metadata": {"priority": "high", "type": "codex_entry"},
        },
        {
            "content": "CONSTRAINT-003: When integrating local Python logic with memOS.MCP, ensure the correct schema is used. memOS uses 'memos' schema by default to avoid clashing with the 'public' schema used by OmegaKG Core.",
            "tags": ["constraint", "mimir", "database"],
            "metadata": {"priority": "high", "type": "codex_entry"},
        },
        {
            "content": "CONSTRAINT-004: All high-risk changes (deletions, refactors, DB migrations) must be preceded by a call to 'consult_mirmir' to check for architectural impacts.",
            "tags": ["constraint", "mimir", "governance"],
            "metadata": {"priority": "critical", "type": "codex_entry"},
        },
    ]

    for mem in constraints:
        result = await logic.store(
            content=mem["content"], tags=mem["tags"], metadata=mem["metadata"]
        )
        print(f"Result: {result}")

    print("✅ Constraints seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_constraints())
