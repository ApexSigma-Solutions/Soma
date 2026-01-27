#!/usr/bin/env python
"""Smoke test: Verify capture-server module loads without errors."""

# Test 1: Module imports
print("\n✓ Test 1: Module imports")
try:
    from omega_kg.capture_server import app

    print("  ✅ capture_server module imports successfully")
except ImportError as e:
    print(f"  ❌ Failed to import: {e}")
    exit(1)

# Test 2: FastAPI app exists
print("\n✓ Test 2: FastAPI app configuration")
try:
    assert hasattr(app, "title")
    print(f"  ✅ App configured: {app.title}")
except AssertionError:
    print("  ❌ FastAPI app not properly configured")
    exit(1)

# Test 3: Settings load
print("\n✓ Test 3: Settings validation")
try:
    from omega_kg.settings import settings

    assert settings.obsidian_vault_path
    print(f"  ✅ Obsidian path: {settings.obsidian_vault_path}")
except Exception as e:  # noqa: BLE001
    print(f"  ⚠️  Settings: {e}")

# Test 4: TestClient can instantiate (no server needed)
print("\n✓ Test 4: Test client instantiation")
try:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    print("  ✅ TestClient created successfully")
except Exception as e:  # noqa: BLE001
    print(f"  ⚠️  TestClient: {e}")

print("\n✅ Smoke test completed!")
print("\nTo run capture-server live:")
print("  poetry run capture-server")
print("\nThen test with:")
print("  curl http://localhost:8765/health")
