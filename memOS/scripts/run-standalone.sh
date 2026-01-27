#!/bin/bash
# =============================================================================
# MemOS MCP Standalone Run Script
# =============================================================================
# Runs memos.MCP as a standalone Docker service with SQLite.
#
# Usage:
#   ./scripts/run-standalone.sh        # Start
#   ./scripts/run-standalone.sh stop   # Stop
#   ./scripts/run-standalone.sh logs   # View logs
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

case "${1:-start}" in
  start)
    echo "Starting memos.MCP standalone..."
    docker-compose -f docker/docker-compose.yml up -d
    echo "✓ memos.MCP started on http://localhost:8768"
    echo ""
    echo "View logs: docker-compose -f docker/docker-compose.yml logs -f"
    echo "Stop: ./scripts/run-standalone.sh stop"
    ;;
  stop)
    echo "Stopping memos.MCP standalone..."
    docker-compose -f docker/docker-compose.yml down
    echo "✓ memos.MCP stopped"
    ;;
  restart)
    echo "Restarting memos.MCP standalone..."
    docker-compose -f docker/docker-compose.yml restart
    echo "✓ memos.MCP restarted"
    ;;
  logs)
    docker-compose -f docker/docker-compose.yml logs -f
    ;;
  status)
    docker-compose -f docker/docker-compose.yml ps
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs|status}"
    exit 1
    ;;
esac
