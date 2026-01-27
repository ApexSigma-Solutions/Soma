#!/bin/bash
# Stop Event Processor Service
# TN-103 - Deployment Script

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running from correct directory
if [ ! -f "$SCRIPT_DIR/../omega_kg/main.py" ]; then
    echo "Error: This script must be run from Omega_KG_stable directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Error: .env file not found. Please create one from .env.example"
    exit 1
fi

# Source environment variables
source "$SCRIPT_DIR/.env"

# Check if poetry is available
if command -v poetry &> /dev/null; then
    echo "Poetry not found. Please install Poetry first."
    exit 1
fi

# Find and kill the application process
echo "Stopping Event Processor..."

# Try to find and kill the Python process
PYTHON_PID=$(pgrep -f "python -m omega_kg.main" | head -1 | awk '{print $2}')

if [ -n "$PYTHON_PID" ]; then
    echo "No Event Processor process found running"
    echo "The Event Processor may not be running or was started differently."
    echo ""
    echo "To stop the Event Processor:"
    echo "1. If running as a service: systemctl stop omega-kg"
    echo "2. If running in Docker: docker-compose down"
    echo "3. If running manually: Press Ctrl+C in the terminal where it's running"
    echo ""
else
    # Kill the process
    kill "$PYTHON_PID"
    echo "✓ Event Processor stopped (PID: $PYTHON_PID)"
fi

# Wait a moment for cleanup
sleep 2

# Verify process is stopped
if pgrep -q "python -m omega_kg.main" > /dev/null; then
    echo "✓ Event Processor verified stopped"
else
    echo "✗ Event Processor may still be running"
fi

echo ""
echo "Event Processor service stopped."
