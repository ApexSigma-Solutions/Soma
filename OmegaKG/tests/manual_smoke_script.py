#!/usr/bin/env python3
"""Smoke test for Phase 3 & 4 vector embedding pipeline"""

import json
import sys
import time

import requests

# Prepare test payload
payload = {
    "session_id": "SMOKE_TEST_001",
    "message": "Phase 3 verification test: The eagle has landed.",
    "platform": "Terminal",
    "node_label": "ChatMessage",
}

print("=" * 70)
print("SMOKE TEST: Phase 3 & 4 Vector Embedding Pipeline")
print("=" * 70)

# Give server a moment to fully bind
print("\n[STEP 1/4] Waiting for server to be ready...")
time.sleep(2)

try:
    # Send capture request
    print("[STEP 2/4] Sending capture request...")
    start = time.time()
    response = requests.post(
        "http://localhost:8765/v1/capture", json=payload, timeout=10
    )
    elapsed = time.time() - start

    # Check response
    if response.status_code == 200:
        print(f"✓ Request succeeded in {elapsed * 1000:.0f}ms")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)}")

        if "vector_id" in data:
            vector_id = data["vector_id"]
            print(f"  ✓ Vector ID: {vector_id}")
        else:
            print("✗ Missing vector_id in response")
            sys.exit(1)
    else:
        print(f"✗ Request failed with status {response.status_code}")
        print(f"  Response: {response.text}")
        sys.exit(1)

    # Wait for worker to process
    print("\n[STEP 3/4] Waiting for worker to process embedding (10s)...")
    time.sleep(10)

    # Query PostgreSQL
    print("[STEP 4/4] Querying PostgreSQL for embedding status...")
    import asyncio

    import asyncpg

    from omega_kg.config import (
        POSTGRES_DB,
        POSTGRES_PASSWORD,
        POSTGRES_PORT,
        POSTGRES_SERVER,
        POSTGRES_USER,
        VECTOR_TABLE_NAME,
    )

    async def check_embedding():
        try:
            conn = await asyncpg.connect(
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                host=POSTGRES_SERVER,
                port=POSTGRES_PORT,
            )

            result = await conn.fetchrow(
                f"SELECT id, message_id, status, retry_count, created_at, updated_at FROM {VECTOR_TABLE_NAME} ORDER BY id DESC LIMIT 1"
            )

            await conn.close()
            return result
        except Exception as e:
            print(f"✗ Database error: {e}")
            return None

    record = asyncio.run(check_embedding())

    if record:
        print("✓ Found embedding record:")
        print(f"  ID: {record['id']}")
        print(f"  Message ID: {record['message_id']}")
        print(f"  Status: {record['status']}")
        print(f"  Retry count: {record['retry_count']}")
        print(f"  Created: {record['created_at']}")
        print(f"  Updated: {record['updated_at']}")

        if record["status"] == "ready":
            print("\n" + "=" * 70)
            print("✅ SMOKE TEST PASSED - Vector embedding pipeline is operational!")
            print("=" * 70)
        else:
            print(f"\n⚠ Embedding status is '{record['status']}', not 'ready'")
    else:
        print("✗ No embedding record found in database")
        sys.exit(1)

except requests.exceptions.ConnectionError as e:
    print(f"✗ Cannot connect to server: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
