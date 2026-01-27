import json
import os

paths = [
    r"C:\Users\steyn\.gemini\antigravity\mcp_config.json",
    r"C:\Users\steyn\.gemini\antigravity\mcp.json",
]

config = {
    "mcpServers": {
        "linear-mcp-server": {
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://mcp.linear.app/sse"],
        },
        "memos": {
            "command": "d:/projects/OmegaKG/memos.MCP/.venv/Scripts/python.exe",
            "args": ["-u", "-m", "memos_mcp.server"],
            "cwd": "d:/projects/OmegaKG/memos.MCP",
            "env": {
                "Encoding": "utf-8",
                "PYTHONPATH": "d:/projects/OmegaKG/memos.MCP/src",
                "INGEST_LLM_URL": "http://localhost:8766",
                "POSTGRES_USER": "omega_user",
                "POSTGRES_DB": "omega_kg_stable",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5800",
                "POSTGRES_PASSWORD": "omega_dev_password",
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "aDQUU5$@1dpuj5",
                "OLLAMA_BASE_URL": "http://localhost:11434",
            },
        },
    }
}

for path in paths:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"{os.path.basename(path)} repaired successfully")
