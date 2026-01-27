#!/usr/bin/env python3
"""Minimal smoke test - just send a capture request and check response"""

import json
import time

import pytest
import requests


def test_capture_smoke():
    """Minimal smoke test - just send a capture request and check response"""
    print("=" * 70)
    print("MINIMAL SMOKE TEST: Capture Request Only")
    print("=" * 70)

    # Use port 8765 as default in settings.py
    port = 8765
    base_url = f"http://localhost:{port}"

    # Get JWT token by exchanging API key
    print("[1/2] Getting JWT token...")
    api_key = "N7F6JKUecfl69WTC83rN7qJTMr2H6cylDyIDNM6Npu8y5KczFaAXQoPFYovlQQAP"
    try:
        auth_response = requests.post(
            f"{base_url}/auth/token", headers={"X-API-Key": api_key}, timeout=5
        )

        if auth_response.status_code == 200:
            token = auth_response.json()["access_token"]
            print("✓ Got JWT token")
        else:
            pytest.fail(
                f"Auth failed ({auth_response.status_code}): {auth_response.text}"
            )
    except Exception as e:
        pytest.fail(f"Auth error: {e}")

    # Send capture request with JWT token
    print("[2/2] Sending capture request...")
    try:
        payload = {
            "platform": "Terminal",
            "url": f"http://localhost/smoke-test-{time.time()}",
            "title": f"Phase 3 Verification Test {time.time()}",
            "messages": [
                {
                    "role": "user",
                    "content": f"Phase 3 verification test at {time.time()}: The eagle has landed.",
                }
            ],
        }

        start = time.time()
        # Use JWT Bearer token for authentication
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{base_url}/capture", json=payload, headers=headers, timeout=10
        )
        elapsed = time.time() - start

        print(f"\n✓ Response received in {elapsed * 1000:.0f}ms")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response:\n{json.dumps(data, indent=2)}")
            print("\n" + "=" * 70)
            print("✅ SMOKE TEST PASSED - Capture request successful!")
            print("=" * 70)
        else:
            pytest.fail(f"Request failed: {response.text}")

    except requests.exceptions.ConnectionError:
        pytest.fail(
            f"Cannot connect to server at {base_url}. Make sure the capture server is running"
        )
    except Exception as e:
        pytest.fail(f"Error: {e}")
