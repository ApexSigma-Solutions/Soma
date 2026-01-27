#!/usr/bin/env python3
"""
Phase 5: Ollama Service Check
Verifies Ollama is running and embedding generation works.
"""

import asyncio
import sys
import httpx
from pathlib import Path

# Add project root to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_kg.settings import settings
from omega_kg.domain.common.embedding_service import generate_embedding


async def check_ollama_service():
    """Check if Ollama service is running."""
    print("\n=== Ollama Service Health Check ===")

    ollama_url = settings.ollama_base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get version
            response = await client.get(f"{ollama_url}/api/version")

            if response.status_code == 200:
                data = response.json()
                print("[OK] Ollama service is running")
                print(f"  URL: {ollama_url}")
                print(f"  Version: {data.get('version', 'unknown')}")
                return True
            else:
                print(f"[FAIL] Ollama service returned status: {response.status_code}")
                return False

    except httpx.ConnectError:
        print(f"[FAIL] Cannot connect to Ollama at {ollama_url}")
        print("  Service may not be running")
        return False
    except httpx.TimeoutException:
        print(f"[FAIL] Timeout connecting to Ollama at {ollama_url}")
        return False
    except Exception as e:
        print(f"[FAIL] Error checking Ollama: {e}")
        return False


async def check_ollama_model():
    """Check if required bge-m3:567m model is available."""
    print("\n=== Ollama Model Check ===")

    ollama_url = settings.ollama_base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # List models
            response = await client.get(f"{ollama_url}/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                print(f"  Found {len(models)} model(s)")

                # Check for bge-m3:567m
                required_model = "bge-m3:567m"
                model_found = any(required_model in m.get("name", "") for m in models)

                if model_found:
                    print(f"  [OK] Required model found: {required_model}")

                    # Show available models
                    print("\n  Available models:")
                    for model in models:
                        name = model.get("name", "unknown")
                        size = model.get("size", 0)
                        size_gb = size / (1024**3) if size > 0 else 0
                        print(f"    - {name} ({size_gb:.2f} GB)")

                    return True
                else:
                    print(f"  [FAIL] Required model not found: {required_model}")
                    print("\n  Available models:")
                    for model in models:
                        print(f"    - {model.get('name', 'unknown')}")
                    return False
            else:
                print(f"  [FAIL] Failed to list models: {response.status_code}")
                return False

    except Exception as e:
        print(f"  [FAIL] Error checking models: {e}")
        return False


async def test_embedding_generation():
    """Test actual embedding generation."""
    print("\n=== Embedding Generation Test ===")

    test_text = "This is a diagnostic test for embedding generation."

    try:
        print(f"  Input text: {test_text}")
        print("  Generating embedding...")

        embedding = await generate_embedding(test_text)

        if embedding:
            print("[OK] Embedding generated successfully")
            print(f"  Dimensions: {len(embedding)}")
            print(f"  Sample values: {embedding[:5]}")

            # Verify dimensions
            if len(embedding) == 1024:
                print("  [OK] Correct dimension (1024)")
                return True
            else:
                print(f"  [FAIL] Wrong dimension: {len(embedding)} (expected 1024)")
                return False
        else:
            print("[FAIL] No embedding returned")
            return False

    except Exception as e:
        print(f"[FAIL] Embedding generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def provide_startup_instructions():
    """Provide instructions to start Ollama if not running."""
    print("\n" + "=" * 60)
    print("OLLAMA STARTUP INSTRUCTIONS")
    print("=" * 60)

    print("""
If Ollama is not running, start it with:

1. Windows (if installed via installer):
   - Start Ollama from Start Menu
   - Or run: ollama serve

2. Windows (manual binary):
   - Download from: https://ollama.ai/download
   - Extract and run: ollama.exe serve

3. Docker (if using container):
   docker run -d \\
     --name ollama \\
     -p 11434:11434 \\
     -v ollama:/root/.ollama \\
     -v ollama-models:/root/.ollama/models \\
     ollama/ollama

4. After starting Ollama, pull the required model:
   ollama pull bge-m3:567m

Expected output:
  pulling model: 567M / 567M
  success

5. Verify with:
   curl http://localhost:11434/api/tags
""")


async def main():
    """Run all Phase 5 checks."""
    print("=" * 60)
    print("PHASE 5: Ollama Service Check")
    print("=" * 60)

    results = {
        "service": await check_ollama_service(),
        "model": False,
        "embedding": False,
    }

    # If service is up, check model and embedding
    if results["service"]:
        results["model"] = await check_ollama_model()

        if results["model"]:
            results["embedding"] = await test_embedding_generation()
    else:
        await provide_startup_instructions()

    print("\n" + "=" * 60)
    print("PHASE 5 SUMMARY")
    print("=" * 60)

    for check, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{check:15s}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n[OK] Ollama service fully operational")
        print("  Embedding generation ready")
    elif results["service"]:
        print("\n[FAIL] Ollama is running but needs configuration")
        print("  Check model installation")
    else:
        print("\n[FAIL] Ollama service not available")
        print("  Please start Ollama service")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
