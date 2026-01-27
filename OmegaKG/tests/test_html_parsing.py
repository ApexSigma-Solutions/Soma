import json

import requests

# CONFIGURATION
BASE_URL = "http://localhost:8765"
# Ensure this matches your .env
API_KEY = "test-api-key-for-testing-only"


def test_html_parsing():
    print(f"=== Testing Server-Side HTML Parsing ({BASE_URL}) ===\n")

    # 1. AUTHENTICATE
    try:
        auth_resp = requests.post(
            f"{BASE_URL}/auth/token", headers={"x-api-key": API_KEY}
        )
    except requests.exceptions.ConnectionError:
        print("❌ Connection Refused. Server not running.")
        return

    if auth_resp.status_code != 200:
        print(f"❌ Auth Failed: {auth_resp.status_code}")
        return

    token = auth_resp.json().get("access_token")
    print("✅ Auth Success! Token acquired.")

    # 2. PREPARE DUMMY HTML (Simulating AI Studio)
    # This HTML structure triggers the AI Studio parser in parsers.py
    dummy_html = """
    <html>
        <body>
            <div class="message-user">Run: Create a python script for me.</div>
            <div class="message-model">Model: Sure! Here is the code...</div>
        </body>
    </html>
    """

    # 3. SEND CAPTURE
    print("2. Sending Raw HTML Payload...")

    payload = {
        "user_id": "SigmaDev11",
        "source": "python_test_script",
        "url": "https://aistudio.google.com/test",
        "platform": "web",
        "title": "AI Studio Parsing Test",
        "raw_html": dummy_html,
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(f"{BASE_URL}/capture", json=payload, headers=headers)

    # 4. REPORT RESULTS
    if response.status_code == 200:
        print("✅ Capture Successful!")
        print(json.dumps(response.json(), indent=2))
        print("\n--> CHECK VAULT: Look for a new file in AI_Conversations/web/")
    elif response.status_code == 422:
        print("❌ Validation Error (422):")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    test_html_parsing()
