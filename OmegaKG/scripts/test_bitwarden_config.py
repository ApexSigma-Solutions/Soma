#!/usr/bin/env python3
"""
Test script to verify Bitwarden Secrets Manager integration.
Usage: poetry run python scripts/test_bitwarden_config.py
"""

import os
import sys


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask a secret value, showing only first few characters."""
    if not value or len(value) <= visible_chars:
        return "****"
    return f"{value[:visible_chars]}{'*' * (len(value) - visible_chars)}"


def main():
    print("=" * 60)
    print("Omega_KG Bitwarden Integration Test")
    print("=" * 60)

    # Check if Bitwarden is configured
    bws_token = os.getenv("BWS_ACCESS_TOKEN")
    if not bws_token:
        print("\n❌ BWS_ACCESS_TOKEN not found")
        print("   Bitwarden integration is DISABLED")
        print("   System will use .env file values\n")
    else:
        print(f"\n✓ BWS_ACCESS_TOKEN found: {mask_secret(bws_token, 8)}")
        print("  Bitwarden integration is ENABLED\n")

    # Try to import settings
    try:
        print("Importing settings...")
        from omega_kg.settings import settings

        print("✓ Settings loaded successfully\n")

        # Test some values (masked)
        print("Configuration values (masked):")
        print(f"  neo4j_password: {mask_secret(settings.neo4j_password)}")
        print(f"  extension_api_key: {mask_secret(settings.extension_api_key)}")
        print(f"  linear_webhook_secret: {mask_secret(settings.linear_webhook_secret)}")
        print(f"  jwt_secret_key: {mask_secret(settings.jwt_secret_key)}")

        # Check if values look like they came from Bitwarden (longer, more complex)
        if bws_token and len(settings.neo4j_password) > 20:
            print("\n✓ Values appear to be loaded from Bitwarden")
        else:
            print("\n⚠ Using .env file values")

        print("\n" + "=" * 60)
        print("✓ Test completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Error loading settings: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
