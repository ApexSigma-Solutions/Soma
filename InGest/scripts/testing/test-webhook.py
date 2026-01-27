#!/usr/bin/env python3
"""
Manual webhook testing script.

This script can be used to test the webhook endpoint locally without
requiring Linear to send actual webhook events.

Usage:
    python scripts/test_webhook.py [--url URL] [--secret SECRET]

Examples:
    # Test local service
    python scripts/test_webhook.py

    # Test production service
    python scripts/test_webhook.py --url https://ingest.apexsigmasolutions.co.za/webhook/linear

    # Test with custom secret
    python scripts/test_webhook.py --secret "your-webhook-secret"
"""

import argparse
import hashlib
import hmac
import json
import sys
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


def generate_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON payload as string
        secret: Webhook secret

    Returns:
        Signature in format "sha256=<hex_digest>"
    """
    signature = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def create_test_payload() -> Dict[str, Any]:
    """
    Create a test Linear webhook payload.

    Returns:
        Test payload dictionary
    """
    from datetime import datetime

    return {
        "type": "Issue",
        "action": "create",
        "data": {
            "id": "TEST-123",
            "title": "Test Issue from webhook testing script",
            "description": "This is a test webhook event",
            "state": {"name": "Todo"},
            "team": {"name": "Engineering"},
        },
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "organizationId": "test-org-123",
        "webhookId": "test-webhook-id",
    }


def test_webhook(
    url: str = "http://localhost:8000/webhook/linear",
    secret: str = "test-secret",
    verbose: bool = True,
) -> bool:
    """
    Test the webhook endpoint.

    Args:
        url: Webhook endpoint URL
        secret: Webhook secret for signature generation
        verbose: Print detailed output

    Returns:
        True if test passed, False otherwise
    """
    if verbose:
        print("=" * 70)
        print("WEBHOOK ENDPOINT TEST")
        print("=" * 70)
        print()
        print(f"Target URL: {url}")
        print(f"Secret: {'*' * len(secret)}")
        print()

    # Create test payload
    payload = create_test_payload()
    payload_str = json.dumps(payload)

    if verbose:
        print("Test Payload:")
        print(json.dumps(payload, indent=2))
        print()

    # Generate signature
    signature = generate_signature(payload_str, secret)

    if verbose:
        print(f"Generated Signature: {signature}")
        print()

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Linear-Signature": signature,
        "X-Correlation-ID": "test-correlation-id-123",
    }

    # Send request
    if verbose:
        print("Sending webhook request...")
        print()

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, content=payload_str, headers=headers)

        if verbose:
            print(f"Response Status: {response.status_code}")
            print("Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            print()
            print("Response Body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
            print()

        # Check response
        if response.status_code in [200, 202]:
            if verbose:
                print("✓ TEST PASSED")
                print("  Webhook was accepted successfully")
            return True
        elif response.status_code == 503:
            if verbose:
                print("⚠ TEST WARNING")
                print("  Webhook forwarder is up but ingest-llm service is unavailable")
                print("  This is expected if ingest-llm is not running")
            return True
        elif response.status_code == 401:
            if verbose:
                print("✗ TEST FAILED")
                print("  Invalid webhook signature")
                print(
                    "  Make sure LINEAR_WEBHOOK_SECRET matches the secret used for testing"
                )
            return False
        else:
            if verbose:
                print("✗ TEST FAILED")
                print(f"  Unexpected status code: {response.status_code}")
            return False

    except httpx.ConnectError as e:
        if verbose:
            print("✗ TEST FAILED")
            print(f"  Connection error: {e}")
            print("  Make sure the service is running")
        return False

    except Exception as e:
        if verbose:
            print("✗ TEST FAILED")
            print(f"  Error: {e}")
        return False


def test_health(
    url: str = "http://localhost:8000/webhook/health", verbose: bool = True
) -> bool:
    """
    Test the webhook health endpoint.

    Args:
        url: Health endpoint URL
        verbose: Print detailed output

    Returns:
        True if healthy, False otherwise
    """
    if verbose:
        print("=" * 70)
        print("HEALTH CHECK TEST")
        print("=" * 70)
        print()
        print(f"Target URL: {url}")
        print()

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)

        if verbose:
            print(f"Response Status: {response.status_code}")
            print()
            print("Response Body:")
            print(json.dumps(response.json(), indent=2))
            print()

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                if verbose:
                    print("✓ HEALTH CHECK PASSED")
                    print("  Webhook forwarder is healthy")
                return True

        if verbose:
            print("✗ HEALTH CHECK FAILED")
        return False

    except Exception as e:
        if verbose:
            print("✗ HEALTH CHECK FAILED")
            print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test webhook endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the service (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--secret",
        default="test-secret",
        help="Webhook secret for signature generation (default: test-secret)",
    )
    parser.add_argument(
        "--skip-health", action="store_true", help="Skip health check test"
    )
    parser.add_argument("--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    # Normalize URL
    base_url = args.url.rstrip("/")
    webhook_url = f"{base_url}/webhook/linear"
    health_url = f"{base_url}/webhook/health"

    verbose = not args.quiet

    # Run tests
    health_passed = True
    webhook_passed = True

    if not args.skip_health:
        health_passed = test_health(health_url, verbose)
        if verbose:
            print()

    webhook_passed = test_webhook(webhook_url, args.secret, verbose)

    # Summary
    if verbose:
        print()
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        if not args.skip_health:
            print(f"  Health Check: {'✓ PASSED' if health_passed else '✗ FAILED'}")
        print(f"  Webhook Test: {'✓ PASSED' if webhook_passed else '✗ FAILED'}")
        print()

    # Exit code
    if health_passed and webhook_passed:
        if verbose:
            print("✓ All tests passed!")
        sys.exit(0)
    else:
        if verbose:
            print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
