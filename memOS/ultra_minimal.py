#!/usr/bin/env python3
"""
Ultra minimal memOS.MCP server - bypasses all Unicode issues
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
    """Start the minimal memOS.MCP server"""
    try:
        logger.info("Starting minimal memOS.MCP server on port 8768...")

        # Create FastMCP instance with minimal configuration
        mcp = FastMCP(name="memOS", version="1.0.0")

        logger.info("FastMCP instance created successfully")

        # Start the server
        logger.info("Starting server on port 8768...")
        await mcp.run(port=8768, host="0.0.0.0")

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
