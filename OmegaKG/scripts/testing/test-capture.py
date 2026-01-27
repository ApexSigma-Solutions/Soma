import requests
import json

# CONFIGURATION
BASE_URL = "http://localhost:8002"
API_KEY = "test-api-key-for-testing-only"


def test_capture():
    print(f"=== Testing Capture Server ({BASE_URL}) ===\n")

    # 1. AUTHENTICATE
    try:
        auth_resp = requests.post(
            f"{BASE_URL}/auth/token", headers={"x-api-key": API_KEY}
        )
    except requests.exceptions.ConnectionError:
        print("❌ Connection Refused. Is the server running?")
        return

    if auth_resp.status_code != 200:
        print(f"❌ Auth Failed: {auth_resp.status_code}")
        return

    token = auth_resp.json().get("access_token")
    print("✅ Auth Success! Token acquired.")

    # 2. SEND CAPTURE (CORRECTED SCHEMA)
    print("2. Sending Capture Payload...")

    payload = {
        "user_id": "SigmaDev11",
        "source": "python_test_script",
        "url": "http://localhost/test-conversation",
        "platform": "windows",
        "title": "Golden Schema Test Conversation",
        # FIXED: Sending 'messages' list instead of flat 'content'
        "messages": [
            {"role": "user", "content": "Hello, this is a test for the Golden Schema."},
            {
                "role": "assistant",
                "content": "Understood. I will verify the frontmatter contains 'id' and 'type'.",
            },
        ],
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(f"{BASE_URL}/capture", json=payload, headers=headers)

    if response.status_code == 200:
        print("✅ Capture Successful!")
        print(json.dumps(response.json(), indent=2))
        print("\n--> CHECK VAULT NOW: Look for the new .md file inside 'test_vault'.")
        print("    Verify it contains:")
        print("    id: CAP-...")
        print("    type: Conversation")
    elif response.status_code == 422:
        print("❌ Validation Error (422):")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    test_capture()
