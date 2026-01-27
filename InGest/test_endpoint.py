#!/usr/bin/env python3
"""Test script for InGest-LLM file upload endpoint."""

import sys
import httpx

# Create test content
test_content = b"This is a test document for NLP file ingestion verification."

# Test the endpoint
files = {"file": ("test_sample.txt", test_content, "text/plain")}
r = httpx.post("http://localhost:8000/ingest/file", files=files, timeout=30.0)
print(f"Status: {r.status_code}", file=sys.stderr)
print(f"Response: {r.text}", file=sys.stderr)
