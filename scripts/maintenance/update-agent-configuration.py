import json
import os
import sys

# Path to the agent's MCP config
config_path = r"C:\Users\steyn\.gemini\antigravity\mcp_config.json"

print(f"Reading config from: {config_path}")

try:
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)
    else:
        print("Config file not found, creating new one.")
        data = {"mcpServers": {}}

    # Ensure mcpServers key exists
    if "mcpServers" not in data:
        data["mcpServers"] = {}

    # Define memOS configuration
    memos_config = {
        "command": "poetry",
        "args": ["run", "python", "src/memos_mcp/server.py"],
        "cwd": "D:/projects/OmegaKG/memos.MCP",
        "env": {
            "PYTHONUTF8": "1",
            "OMEGA_ENV": "dev",
            # Add other necessary env vars if not picked up from system
        },
        "disabled": False,
        "autoApprove": [],
    }

    # update or add memOS
    data["mcpServers"]["memOS"] = memos_config
    print("Added/Updated 'memOS' configuration.")

    # Write back
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    print("✅ Configuration saved successfully.")

except Exception as e:
    print(f"❌ Failed to update config: {e}")
    sys.exit(1)
