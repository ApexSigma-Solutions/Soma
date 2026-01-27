#!/bin/bash
# Quick Ngrok Test for OmegaKG

echo "=================================="
echo "OmegaKG Ngrok Tunnel Test"
echo "=================================="
echo ""
echo "Which environment to test?"
echo "1) Dev     (./omega_kg_temp)"
echo "2) Stable  (./Omega_KG_stable)  [RECOMMENDED]"
echo "3) Temp    (./omega_kg_temp)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1) ENV_DIR="Omega_KG_dev";;
    2) ENV_DIR="Omega_KG_stable";;
    3) ENV_DIR="omega_kg_temp";;
    *) echo "Invalid choice"; exit 1;;
esac

echo ""
echo "Starting $ENV_DIR..."
cd "D:/projects/OmegaKG/$ENV_DIR"

# Activate virtual environment
if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠️ Virtual environment not found"
fi

# Check if server is already running
echo ""
echo "Checking if server is already running on port 8765..."
if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "✓ Server already running on port 8765"
else
    echo "⚠️ Server not running. Please start it first:"
    echo "   python -m omega_kg.capture_server"
    echo ""
    read -p "Press Enter after starting the server..."
fi

echo ""
echo "=================================="
echo "Starting ngrok tunnel..."
echo "=================================="
echo ""
echo "⚠️ IMPORTANT: Keep this terminal open!"
echo "⚠️ Don't close it until testing is complete"
echo ""
echo "Your webhook URL will be:"
echo "   https://<random>.ngrok.io/webhook/linear"
echo ""
echo "Press Ctrl+C to stop ngrok when done testing"
echo ""
sleep 2

# Start ngrok
ngrok http 8765
