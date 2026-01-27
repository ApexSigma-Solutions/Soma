#!/bin/bash
# =============================================================================
# MemOS MCP Docker Build Script
# =============================================================================
# Builds the memos-mcp Docker image from the project root.
#
# Usage:
#   ./scripts/build.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Building memos-mcp Docker image..."
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

docker build \
  -f docker/Dockerfile \
  -t memos-mcp:latest \
  .

echo "✓ Build complete: memos-mcp:latest"
