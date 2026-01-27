"""
Direct API test - bypasses HTTP to test the endpoint logic directly.
"""

import sys
import asyncio

sys.path.insert(0, "src")

from ingest_llm_as.api.graph_parser import parse_text, ParseRequest


async def main():
    print("=" * 60)
    print("Testing Graph Parser API Endpoint (Direct)")
    print("=" * 60)

    try:
        # Create request
        request = ParseRequest(
            text="This is a test document. The OmegaKG system uses Neo4j for knowledge graphs."
        )

        print("\n1. Testing parse_text endpoint...")
        print(f"   Input text: {request.text[:50]}...")

        # Call the endpoint function directly
        result = await parse_text(request)

        print("\n✅ Endpoint executed successfully!")
        print(f"   Metadata: {result.metadata}")
        print(f"   Nodes: {len(result.nodes)}")
        print(f"   Edges: {len(result.edges)}")

        if result.nodes:
            print("\n   Sample nodes:")
            for node in result.nodes[:3]:
                print(f"     - {node}")

        if result.edges:
            print("\n   Sample edges:")
            for edge in result.edges[:3]:
                print(f"     - {edge}")

        print("\n" + "=" * 60)
        print("✅ Direct API test passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
