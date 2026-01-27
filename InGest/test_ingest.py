import requests
import os
import argparse

# Configuration
BASE_URL = "http://localhost:8766"  # InGest-LLM Port (Check launch script, usually 8766 or 8000 depending on config)
# Getting port from standardized ports if possible, default to 8766 as per dashboard
DIGEST_ENDPOINT = f"{BASE_URL}/graph/upload/digest"
PARSE_FILE_ENDPOINT = f"{BASE_URL}/graph/parse/file"


def test_health():
    url = f"{BASE_URL}/graph/health"  # Note: health is under /graph prefix or root? graph_parser.py has router prefix /graph.
    # But often main.py mounts it. Let's try both or check standard.
    # In graph_parser.py: router = APIRouter(prefix="/graph"...)
    # So it is /graph/health

    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Health Check Passed")
            print(response.json())
            return True
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Service not running at {BASE_URL}")
        return False


def test_digest(filepath):
    print(f"\n🧪 Testing Digest Endpoint with {filepath}...")
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    with open(filepath, "rb") as f:
        files = {
            "file": (os.path.basename(filepath), f, "application/octet-stream")
        }  # Let auto-detect
        try:
            response = requests.post(DIGEST_ENDPOINT, files=files)
            if response.status_code == 200:
                print("✅ Digest Successful")
                data = response.json()
                print(f"   Status: {data.get('status')}")
                print(f"   Chars: {data.get('character_count')}")
                print(f"   System Vitals: {data.get('system_vitals')}")
            else:
                print(f"❌ Digest Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Request Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test InGest-LLM endpoints")
    parser.add_argument("file", nargs="?", help="Path to file to digest")
    parser.add_argument("--port", default="8766", help="Service port")
    args = parser.parse_args()

    BASE_URL = f"http://localhost:{args.port}"
    DIGEST_ENDPOINT = f"{BASE_URL}/graph/upload/digest"

    print("=" * 60)
    print(f"InGest-LLM Verification Tool (Target: {BASE_URL})")
    print("=" * 60)

    if test_health():
        if args.file:
            test_digest(args.file)
        else:
            print("\nUsage: python test_ingest.py <path_to_file>")
    else:
        print(
            "\n⚠️ Ensure the service is running: 'poetry run uvicorn src.ingest_llm_as.main:app --port 8766'"
        )
