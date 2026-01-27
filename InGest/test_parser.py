"""
Quick test script to verify DocumentParser works with installed dependencies.
"""

import sys

sys.path.insert(0, "src")

from ingest_llm_as.parsers.document_parser import DocumentParser


def main():
    print("=" * 60)
    print("Testing DocumentParser Initialization")
    print("=" * 60)

    try:
        print("\n1. Initializing DocumentParser...")
        parser = DocumentParser()
        print("   ✅ Parser initialized successfully!")
        print(
            f"   Model: {parser.model_name if hasattr(parser, 'model_name') else 'Unknown'}"
        )

        print("\n2. Testing parse() method...")
        test_text = "This is a test document. The OmegaKG system uses Neo4j for knowledge graphs."
        result = parser.parse(test_text)

        print("   ✅ Parsing successful!")
        print(f"   Metadata: {result['metadata']}")
        print(f"   Nodes extracted: {len(result['nodes'])}")
        print(f"   Edges extracted: {len(result['edges'])}")

        if result["nodes"]:
            print("\n   Sample nodes:")
            for node in result["nodes"][:3]:
                print(f"     - {node}")

        if result["edges"]:
            print("\n   Sample edges:")
            for edge in result["edges"][:3]:
                print(f"     - {edge}")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
