import hashlib
import hmac
import json

import requests

# Configuration
# EXTRACTED SECRET: lin_wh_R35AOOhJfSHuZdk8tG6zCdDPkwHNcTfpuhlrKXCCfrYl
SECRET = "lin_wh_R35AOOhJfSHuZdk8tG6zCdDPkwHNcTfpuhlrKXCCfrYl"
ENDPOINT = "https://b5d68f1c48f9.ngrok-free.app/webhook/linear"

payload = {
    "action": "update",
    "data": {
        "id": "diag-001-id",
        "identifier": "DIAG-001",
        "state": {"name": "Done"},
        "priority": 1,
        "updatedAt": "2025-12-21T05:00:00.000Z",
    },
}

# Linear sends compact JSON
body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
signature = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()

headers = {"Content-Type": "application/json", "X-Linear-Signature": signature}


def test_webhook_live():
    print(f"Sending test webhook to {ENDPOINT}...")
    try:
        response = requests.post(ENDPOINT, data=body, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_webhook_live()
