#!/usr/bin/env python3
"""
Simple memOS.MCP server - bypasses tool registration issues
"""

import os
import sys
import asyncio
import logging
from fastmcp import FastMCP

# Force UTF-8 encoding for stdout/stderr
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Configure logging to avoid Unicode issues
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Set environment variable to avoid Unicode in FastMCP
os.environ["PYTHONIOENCODING"] = "utf-8"


async def main():
    """Start the simple memOS.MCP server"""
    try:
        logger.info("Starting simple memOS.MCP server on port 8768...")

        # Create FastMCP instance with minimal configuration
        mcp = FastMCP(name="memOS", version="1.0.0")

        logger.info("FastMCP instance created successfully")

        # Add a simple health check tool
        @mcp.tool()
        async def health_check() -> str:
            """Check the health of the memOS system"""
            return "memOS.MCP is running and healthy on port 8768"

        # Add a simple echo tool for testing
        @mcp.tool()
        async def echo_message(message: str) -> str:
            """Echo a message back"""
            return f"Echo: {message}"

        logger.info("Tools registered successfully")

        # Start the server
        logger.info("Starting server on port 8768...")
        await mcp.run(port=8768, host="0.0.0.0")

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
