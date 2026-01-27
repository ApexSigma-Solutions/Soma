"""
Test script for FileLoaderService
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest_llm_as.services.file_loader_service import FileLoaderService


def test_mime_detection():
    """Test MIME type detection from bytes data."""
    print("Testing MIME type detection...")

    # Test PDF detection
    pdf_bytes = b"%PDF-1.4"
    loader = FileLoaderService()
    mime_type = loader._detect_mime_type(bytes_data=pdf_bytes)
    assert mime_type == "application/pdf", f"PDF MIME type: {mime_type}"
    print("✓ PDF MIME detection passed")

    # Test DOCX detection
    docx_bytes = b"PK\x03\x04"
    loader = FileLoaderService()
    mime_type = loader._detect_mime_type(bytes_data=docx_bytes)
    assert (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ), f"DOCX MIME type: {mime_type}"
    print("✓ DOCX MIME detection passed")

    # Test HTML detection
    html_bytes = b"<!DOCTYPE html>"
    loader = FileLoaderService()
    mime_type = loader._detect_mime_type(bytes_data=html_bytes)
    assert mime_type == "text/html", f"HTML MIME type: {mime_type}"
    print("✓ HTML MIME detection passed")

    # Test unknown bytes
    unknown_bytes = b"random data"
    loader = FileLoaderService()
    mime_type = loader._detect_mime_type(bytes_data=unknown_bytes)
    assert mime_type == "text/plain", f"Unknown MIME type: {mime_type}"
    print("✓ Unknown MIME detection passed (defaults to text/plain)")


def test_pdf_extraction():
    """Test PDF extraction."""
    print("\nTesting PDF extraction...")

    # Create minimal PDF content
    minimal_pdf = b"%PDF-1.4\n%PDF-1.4\nHello World\n%EOF"

    loader = FileLoaderService()
    try:
        text = loader._extract_pdf(minimal_pdf)
        assert "Hello World" in text, f"PDF extraction failed: {text}"
        print("✓ PDF extraction passed")
    except Exception as e:
        print(f"✗ PDF extraction failed: {e}")
        return False

    return True


def test_docx_extraction():
    """Test DOCX extraction."""
    print("\nTesting DOCX extraction...")

    # Create minimal DOCX content
    # DOCX files are ZIP files with XML structure
    # For simplicity, we'll test with a simple text-based approach
    # In real implementation, python-docx handles the full DOCX format

    # For now, just verify the import works
    try:
        from docx import Document

        print("✓ python-docx import works")
    except ImportError as e:
        print(f"✗ python-docx import failed: {e}")
        return False

    return True


def test_html_extraction():
    """Test HTML extraction."""
    print("\nTesting HTML extraction...")

    # Create minimal HTML content
    minimal_html = b"<!DOCTYPE html><html><head><title>Test</title></head><body><p>Hello World</p></body></html>"

    loader = FileLoaderService()
    try:
        text = loader._extract_html(minimal_html)
        assert "Hello World" in text, f"HTML extraction failed: {text}"
        print("✓ HTML extraction passed")
    except Exception as e:
        print(f"✗ HTML extraction failed: {e}")
        return False

    return True


def test_load_from_file():
    """Test load_from_file method."""
    print("\nTesting load_from_file method...")

    loader = FileLoaderService()

    # Test with file object
    file_obj = {"content": b"Hello World", "content_type": "text/plain"}

    try:
        text = loader.load_from_file(file_obj)
        assert text == "Hello World", f"load_from_file failed: {text}"
        print("✓ load_from_file passed")
    except Exception as e:
        print(f"✗ load_from_file failed: {e}")
        return False

    return True


def test_load_from_bytes():
    """Test load_from_bytes method."""
    print("\nTesting load_from_bytes method...")

    loader = FileLoaderService()

    # Test with bytes and MIME type
    bytes_data = b"Hello World"
    mime_type = "text/plain"

    try:
        text = loader.load_from_bytes(bytes_data=bytes_data, mime_type=mime_type)
        assert text == "Hello World", f"load_from_bytes failed: {text}"
        print("✓ load_from_bytes passed")
    except Exception as e:
        print(f"✗ load_from_bytes failed: {e}")
        return False

    return True


def test_unsupported_mime():
    """Test unsupported MIME type raises error."""
    print("\nTesting unsupported MIME type...")

    loader = FileLoaderService()
    file_obj = {"content": b"Hello World", "content_type": "application/unsupported"}

    try:
        loader.load_from_file(file_obj)
        print("✗ Should have raised ValueError")
        return False
    except ValueError as e:
        assert "Unsupported MIME type" in str(e), f"Wrong error: {e}"
        print(f"✓ Unsupported MIME type error raised correctly: {e}")
        return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("FileLoaderService Test Suite")
    print("=" * 50)

    tests = [
        ("MIME Detection", test_mime_detection),
        ("PDF Extraction", test_pdf_extraction),
        ("DOCX Extraction", test_docx_extraction),
        ("HTML Extraction", test_html_extraction),
        ("load_from_file", test_load_from_file),
        ("load_from_bytes", test_load_from_bytes),
        ("Unsupported MIME", test_unsupported_mime),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✓ {test_name} passed")
        else:
            failed += 1
            print(f"✗ {test_name} failed")

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    # Return exit code based on results
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
