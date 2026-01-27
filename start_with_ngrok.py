#!/usr/bin/env python3
"""
OmegaKG with Ngrok Tunnel - Start script for webhook testing
"""

import subprocess
import sys


def check_ngrok():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True, text=True)
        print(f"✓ Ngrok found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("✗ Ngrok not found!")
        print("\nPlease install ngrok:")
        print("1. Download from: https://ngrok.com/download")
        print("2. Add ngrok to your PATH")
        print("3. Run this script again")
        return False


def start_ngrok(port):
    """Start ngrok tunnel"""
    print(f"\n🚀 Starting ngrok tunnel on port {port}...")
    try:
        subprocess.run(["ngrok", "http", str(port)])
    except KeyboardInterrupt:
        print("\n🛑 Stopping ngrok...")
        sys.exit(0)


if __name__ == "__main__":
    PORT = 8765

    print("=" * 60)
    print("OmegaKG with Ngrok - Linear Webhook Tunnel")
    print("=" * 60)

    if not check_ngrok():
        sys.exit(1)

    print(f"\n📡 This will expose http://localhost:{PORT} to the internet")
    print("🔗 Linear webhook URL will be: https://<your-ngrok-domain>/webhook/linear")
    print("\n⚠️  Note: The ngrok URL changes each time you restart ngrok")
    print("   You'll need to update Linear webhook configuration accordingly")

    input("\nPress Enter to start ngrok...")
    start_ngrok(PORT)
