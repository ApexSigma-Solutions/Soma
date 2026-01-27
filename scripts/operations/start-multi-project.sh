#!/bin/bash
# =============================================================================
# OmegaKG Multi-Project Run Script
# =============================================================================
# Runs the full OmegaKG stack including capture server and memos.MCP.
#
# Usage:
#   ./scripts/run-multi-project.sh              # Start all services
#   ./scripts/run-multi-project.sh stop         # Stop all services
#   ./scripts/run-multi-project.sh memos-mcp    # Start only memos.MCP
#   ./scripts/run-multi-project.sh capture      # Start only capture server
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

case "${1:-all}" in
  all|start)
    echo "Starting OmegaKG multi-project stack..."
    docker-compose up -d
    echo ""
    echo "✓ Services started:"
    echo "  - OmegaKG Capture: http://localhost:8765"
    echo "  - MemOS MCP:      http://localhost:8768"
    echo ""
    echo "View logs: docker-compose logs -f"
    echo "Stop: ./scripts/run-multi-project.sh stop"
    ;;
  stop)
    echo "Stopping OmegaKG multi-project stack..."
    docker-compose down
    echo "✓ All services stopped"
    ;;
  restart)
    echo "Restarting OmegaKG multi-project stack..."
    docker-compose restart
    echo "✓ All services restarted"
    ;;
  memos-mcp)
    echo "Starting memos.MCP only..."
    docker-compose up -d memos-mcp
    echo "✓ MemOS MCP started on http://localhost:8768"
    ;;
  omega-capture|capture)
    echo "Starting OmegaKG capture server only..."
    docker-compose up -d omega-capture
    echo "✓ OmegaKG Capture started on http://localhost:8765"
    ;;
  logs)
    if [ -n "${2:-}" ]; then
      docker-compose logs -f "$2"
    else
      docker-compose logs -f
    fi
    ;;
  status)
    docker-compose ps
    ;;
  *)
    echo "Usage: $0 {all|stop|restart|memos-mcp|capture|logs|status}"
    echo ""
    echo "Commands:"
    echo "  all, start     - Start all services (default)"
    echo "  stop           - Stop all services"
    echo "  restart        - Restart all services"
    echo "  memos-mcp      - Start only memos.MCP"
    echo "  capture        - Start only capture server"
    echo "  logs [service] - View logs (optionally for specific service)"
    echo "  status         - Show service status"
    exit 1
    ;;
esac
