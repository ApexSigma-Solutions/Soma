#!/bin/bash
# Start Event Processor Service
# TN-103 - Deployment Script

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running from correct directory
if [ ! -f "$SCRIPT_DIR/../omega_kg/main.py" ]; then
    echo "Error: This script must be run from the Omega_KG_stable directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Error: .env file not found. Please create one from .env.example"
    exit 1
fi

# Source environment variables
source "$SCRIPT_DIR/.env"

# Validate required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL is not set"
    exit 1
fi

if [ -z "$NEO4J_URI" ]; then
    echo "Error: NEO4J_URI is not set"
    exit 1
fi

if [ -z "$NEO4J_USER" ]; then
    echo "Error: NEO4J_USER is not set"
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    echo "Error: NEO4J_PASSWORD is not set"
    exit 1
fi

# Display configuration
echo "=========================================="
echo "Event Processor Configuration"
echo "=========================================="
echo "DATABASE_URL: ${DATABASE_URL:0:50}"
echo "NEO4J_URI: ${NEO4J_URI:0:50}"
echo "NEO4J_USER: ${NEO4J_USER:0:20}"
echo "WEBHOOK_POLL_INTERVAL: ${WEBHOOK_POLL_INTERVAL:-5.0} seconds"
echo "WEBHOOK_BATCH_SIZE: ${WEBHOOK_BATCH_SIZE:-10} events"
echo "=========================================="
echo ""

# Check if poetry is available
if command -v poetry &> /dev/null; then
    echo "Poetry not found. Please install Poetry first."
    exit 1
fi

# Start the application
echo "Starting Event Processor..."
echo ""

# Run the application with poetry
cd "$SCRIPT_DIR" && poetry run python -m omega_kg.main

# Wait a moment for startup
sleep 3

# Check if process is running
if pgrep -q "Event Processor started" logs/omega_kg.log 2>/dev/null; then
    echo "✓ Event Processor started successfully"
else
    echo "✗ Event Processor failed to start"
    echo "Check logs in logs/omega_kg.log"
    exit 1
fi

echo ""
echo "Event Processor is running in the background."
echo "Use 'scripts/stop-event-processor.sh' to stop it."
echo ""
