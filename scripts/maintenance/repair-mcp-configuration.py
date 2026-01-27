import json
import os

config_path = r"C:\Users\steyn\.gemini\antigravity\mcp_config.json"

# Reconstructing from salvaged data and standards
config = {
    "mcpServers": {
        "linear-mcp-server": {
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://mcp.linear.app/sse"],
            "env": {
                "LINEAR_PERSONAL_ACCESS_TOKEN": os.getenv(
                    "LINEAR_PERSONAL_ACCESS_TOKEN", "placeholder_key"
                )
            },
            "disabled": False,
        },
        "github-mcp-server": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv(
                    "GITHUB_PERSONAL_ACCESS_TOKEN", "placeholder_key"
                )
            },
            "disabled": False,
        },
        "perplexity-ask": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-perplexity"],
            "env": {
                "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY", "placeholder_key")
            },
            "disabled": False,
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "disabled": False,
        },
        "redis": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-redis",
                "redis://localhost:6379/0",
            ],
            "disabled": False,
        },
        "memOS": {
            "command": r"D:\projects\OmegaKG\memos.MCP\.venv\Scripts\python.exe",
            "args": ["src/memos_mcp/server.py"],
            "cwd": "D:/projects/OmegaKG/memos.MCP",
            "env": {
                "PYTHONUTF8": "1",
                "OMEGA_ENV": "dev",
                "POSTGRES_PORT": "6000",
                "POSTGRES_PASSWORD": os.getenv(
                    "POSTGRES_PASSWORD", "omega_dev_password"
                ),
            },
            "disabled": False,
        },
    }
}

print(f"Repairing config at: {config_path}")

try:
    # Ensure directory exists (though it should)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Write atomatically to a temp file first then rename to avoid corruption
    temp_path = config_path + ".tmp"
    with open(temp_path, "w") as f:
        json.dump(config, f, indent=2)

    # Replace the old file
    if os.path.exists(config_path):
        os.remove(config_path)
    os.rename(temp_path, config_path)

    print("✅ Configuration repaired and saved successfully.")

except Exception as e:
    print(f"❌ Repair failed: {e}")

# Also repair the backup file
backup_path = r"C:\Users\steyn\.gemini\antigravity\mcp.json"
try:
    with open(backup_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Backup repaired at: {backup_path}")
except Exception as e:
    print(f"❌ Backup repair failed: {e}")
