import json

import requests

# CONFIGURATION
BASE_URL = "http://localhost:8765"
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
    # We use a div with class 'message' to trigger the parser logic we wrote
    dummy_html = """
    <html>
        <body>
            <div class="message-container">
                <div class="message-user">User: Create a python script for me.</div>
                <div class="message-model">Model: Sure! Here is the code...</div>
            </div>
        </body>
    </html>
    """

    # 3. SEND CAPTURE (Sending 'raw_html' instead of 'messages')
    print("2. Sending Raw HTML Payload...")

    payload = {
        "user_id": "SigmaDev11",
        "source": "python_test_script",
        "url": "https://aistudio.google.com/test",  # URL triggers the specific parser
        "platform": "web",
        "title": "AI Studio HTML Test",
        "raw_html": dummy_html,
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(f"{BASE_URL}/capture", json=payload, headers=headers)

    # 4. REPORT RESULTS
    if response.status_code == 200:
        print("✅ Capture Successful!")
        print(json.dumps(response.json(), indent=2))
        print("\n--> CHECK SERVER LOGS: Did it say 'Successfully parsed 2 messages'?")
    elif response.status_code == 422:
        print("❌ Validation Error (422):")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    test_html_parsing()
