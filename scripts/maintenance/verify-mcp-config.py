"""
MCP Configuration Verification Script

Verifies that:
1. .mcp.json exists and is valid
2. Required environment variables are set
3. memOS.MCP infrastructure is running
4. MCP servers can be started

Usage:
    poetry run python scripts/maintenance/verify-mcp-config.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_status(message: str, status: str):
    """Print a status message with color."""
    if status == "OK":
        print(f"{GREEN}✓{RESET} {message}")
    elif status == "FAIL":
        print(f"{RED}✗{RESET} {message}")
    elif status == "WARN":
        print(f"{YELLOW}⚠{RESET} {message}")
    else:
        print(f"{BLUE}ℹ{RESET} {message}")


def check_mcp_json() -> Tuple[bool, Dict]:
    """Check if .mcp.json exists and is valid JSON."""
    mcp_path = Path(".mcp.json")

    if not mcp_path.exists():
        print_status(".mcp.json not found in workspace root", "FAIL")
        return False, {}

    try:
        with open(mcp_path) as f:
            config = json.load(f)
        print_status(".mcp.json found and valid", "OK")
        return True, config
    except json.JSONDecodeError as e:
        print_status(f".mcp.json has invalid JSON: {e}", "FAIL")
        return False, {}


def check_environment_variables(required_vars: List[str]) -> bool:
    """Check if required environment variables are set."""
    all_set = True
    for var in required_vars:
        if os.getenv(var):
            print_status(f"Environment variable {var} is set", "OK")
        else:
            print_status(f"Environment variable {var} is NOT set", "FAIL")
            all_set = False
    return all_set


def check_service(name: str, host: str, port: int, command: str) -> bool:
    """Check if a service is running."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, timeout=5)
        if result.returncode == 0:
            print_status(f"{name} is running on {host}:{port}", "OK")
            return True
        else:
            print_status(f"{name} is NOT running on {host}:{port}", "FAIL")
            return False
    except subprocess.TimeoutExpired:
        print_status(f"{name} check timed out", "FAIL")
        return False
    except Exception as e:
        print_status(f"{name} check failed: {e}", "FAIL")
        return False


def check_memos_infrastructure() -> bool:
    """Check if memOS.MCP infrastructure is running."""
    print(f"\n{BLUE}Checking memOS.MCP Infrastructure...{RESET}")

    services = [
        (
            "Redis",
            "localhost",
            6380,
            "docker exec memos-redis-mcp redis-cli ping > nul 2>&1",
        ),
        (
            "PostgreSQL",
            "localhost",
            6000,
            'docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable -c "SELECT 1" > nul 2>&1',
        ),
        (
            "Neo4j",
            "localhost",
            7687,
            'docker exec apexsigma.neo4j.stable cypher-shell -u neo4j -p aDQUU5$@1dpuj5 "RETURN 1" > nul 2>&1',
        ),
        (
            "Ollama",
            "localhost",
            11434,
            "curl -s http://localhost:11434/api/tags > nul 2>&1",
        ),
    ]

    all_running = True
    for name, host, port, command in services:
        if not check_service(name, host, port, command):
            all_running = False

    return all_running


def check_mcp_servers(config: Dict) -> bool:
    """Check if MCP servers can be located."""
    print(f"\n{BLUE}Checking MCP Server Configuration...{RESET}")

    servers = config.get("mcpServers", {})
    if not servers:
        print_status("No MCP servers configured", "WARN")
        return False

    all_ok = True
    for server_name, server_config in servers.items():
        print(f"\n  Server: {server_name}")

        # Check type
        server_type = server_config.get("type", "unknown")
        print_status(f"  Type: {server_type}", "INFO")

        # Check command exists
        command = server_config.get("command")
        if command:
            try:
                result = subprocess.run(
                    ["where" if os.name == "nt" else "which", command],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print_status(f"  Command '{command}' found", "OK")
                else:
                    print_status(f"  Command '{command}' NOT found", "FAIL")
                    all_ok = False
            except Exception as e:
                print_status(f"  Could not check command: {e}", "WARN")

        # Check cwd exists (if specified)
        cwd = server_config.get("cwd")
        if cwd:
            cwd_path = Path(cwd)
            if cwd_path.exists():
                print_status(f"  Working directory '{cwd}' exists", "OK")
            else:
                print_status(f"  Working directory '{cwd}' NOT found", "FAIL")
                all_ok = False

    return all_ok


def main():
    """Run all verification checks."""
    print(f"{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}MCP Configuration Verification{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    # Check .mcp.json
    print(f"{BLUE}Checking Configuration File...{RESET}")
    json_ok, config = check_mcp_json()

    if not json_ok:
        print(f"\n{RED}FAILED: .mcp.json is missing or invalid{RESET}")
        print(
            f"\n{YELLOW}Create .mcp.json in workspace root with MCP server configuration{RESET}"
        )
        print(f"{YELLOW}See docs/MCP_CONFIGURATION.md for details{RESET}")
        sys.exit(1)

    # Check environment variables
    print(f"\n{BLUE}Checking Environment Variables...{RESET}")
    required_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD", "NEO4J_PASSWORD"]
    env_ok = check_environment_variables(required_vars)

    if not env_ok:
        print(f"\n{YELLOW}WARNING: Some environment variables are not set{RESET}")
        print(f"{YELLOW}Set them in system environment or create .env file{RESET}")

    # Check infrastructure
    infra_ok = check_memos_infrastructure()

    if not infra_ok:
        print(f"\n{YELLOW}WARNING: Some infrastructure services are not running{RESET}")
        print(f"{YELLOW}Start them with: cd memos.MCP && .\\start-memos.ps1{RESET}")

    # Check MCP servers
    servers_ok = check_mcp_servers(config)

    # Final summary
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Summary{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    if json_ok and env_ok and infra_ok and servers_ok:
        print(f"{GREEN}✓ All checks passed!{RESET}")
        print(f"{GREEN}✓ MCP configuration is ready for Claude Code{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Open Claude Code in this workspace")
        print("  2. Ask: 'What MCP tools are available?'")
        print("  3. Approve MCP servers when prompted")
        print(f"\n{BLUE}Documentation:{RESET}")
        print("  - Full guide: docs/MCP_CONFIGURATION.md")
        print("  - Quick reference: docs/MCP_QUICK_REFERENCE.md")
        sys.exit(0)
    else:
        print(f"{YELLOW}⚠ Some checks failed or have warnings{RESET}")
        print(f"{YELLOW}⚠ MCP configuration may not work correctly{RESET}")
        print(f"\n{BLUE}Troubleshooting:{RESET}")
        print("  - See docs/MCP_CONFIGURATION.md for setup instructions")
        print("  - Verify all prerequisites are installed and running")
        print("  - Check environment variables are set correctly")
        sys.exit(1)


if __name__ == "__main__":
    main()
