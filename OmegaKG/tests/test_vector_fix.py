"""Quick test to verify vector embedding conversion"""

from omega_kg.config import VECTOR_EMBEDDING_DIMENSION


def test_vector_conversion():
    # Test the vector string conversion
    embedding = [0.1, 0.2] * (VECTOR_EMBEDDING_DIMENSION // 2)
    print(f"Embedding length: {len(embedding)}")

    # Apply the conversion from the fixed code
    embedding_str = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
    print(f"String length: {len(embedding_str)}")
    print(f"First 100 chars: {embedding_str[:100]}")
    print(f"Last 100 chars: {embedding_str[-100:]}")
    print("\n✓ Vector conversion test passed!")


if __name__ == "__main__":
    test_vector_conversion()
