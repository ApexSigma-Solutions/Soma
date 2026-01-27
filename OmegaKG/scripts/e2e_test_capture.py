import sys

import requests

from omega_kg.settings import settings

BASE_URL = "http://127.0.0.1:8002"


def run_test():
    print(f"--- Starting E2E Test against {BASE_URL} ---")

    # 1. Health Check
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code != 200:
            print(f"❌ Health check failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        print("✅ Health check passed")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        sys.exit(1)

    # 2. Authentication
    api_key = settings.extension_api_key
    if not api_key:
        print(
            "⚠️  Warning: EXTENSION_API_KEY_PRD is not set in settings. Trying default 'change_me_secure_api_key' just in case."
        )
        api_key = "change_me_secure_api_key"

    print(f"Using API Key: {api_key[:4]}***")

    try:
        auth_resp = requests.post(
            f"{BASE_URL}/auth/token", headers={"X-API-Key": api_key}
        )
        if auth_resp.status_code != 200:
            print(f"❌ Auth failed: {auth_resp.status_code} {auth_resp.text}")
            sys.exit(1)

        token_data = auth_resp.json()
        access_token = token_data["access_token"]
        print("✅ Authentication successful, received token")
    except Exception as e:
        print(f"❌ Auth Exception: {e}")
        sys.exit(1)

    # 3. Capture Data
    payload = {
        "platform": "E2E_Test_Platform",
        "url": "http://localhost/test",
        "title": "E2E Automated Test Capture",
        "messages": [
            {
                "role": "user",
                "content": "This is a test message to verify the capture flow.",
                "timestamp": "2024-01-01T10:00:00",
            },
            {
                "role": "assistant",
                "content": "I have decided to process this request successfully.",
                "timestamp": "2024-01-01T10:00:05",
            },
        ],
        "metadata": {"test_run": "true"},
    }

    print("\nSending capture payload...")
    try:
        cap_resp = requests.post(
            f"{BASE_URL}/capture",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

        if cap_resp.status_code != 200:
            print(f"❌ Capture failed: {cap_resp.status_code} {cap_resp.text}")
            sys.exit(1)

        data = cap_resp.json()
        if data.get("success"):
            print("✅ Capture SUCCESS")
            print(f"   File Path: {data.get('file_path')}")
            print(f"   Nodes Created: {data.get('nodes_created')}")
        else:
            print(f"❌ Capture returned success=False: {data}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Capture Exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_test()
