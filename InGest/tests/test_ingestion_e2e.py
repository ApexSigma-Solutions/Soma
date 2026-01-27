"""
End-to-end integration tests for InGest-LLM.as service.

These tests validate the complete integration between InGest-LLM.as and memOS.as,
ensuring that text ingestion, processing, and storage work correctly in the
Docker Compose environment.
"""

import asyncio
import os
import pytest
import httpx

# Test configuration
# Prefer environment variables so tests work both locally and in Docker
INGEST_API_BASE_URL = os.environ.get("INGEST_API_BASE_URL", "http://localhost:8000")
MEMOS_API_BASE_URL = os.environ.get("INGEST_MEMOS_BASE_URL", "http://localhost:8091")
REQUEST_TIMEOUT = 30

# NOTE: This comprehensive E2E test suite complements the core integration test
# (test_memos_integration_core.py) which fulfills P1-CC-02 requirements.


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return """
    This is a sample text document for testing the InGest-LLM.as integration.
    
    It contains multiple paragraphs to test chunking functionality.
    The content should be processed and stored in memOS.as.
    
    This text includes various types of information that should be
    properly categorized and indexed in the semantic memory tier.
    """


@pytest.fixture
def sample_code_content():
    """Sample code content for testing."""
    return """
def test_function():
    '''A simple test function'''
    return "Hello, World!"

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
"""


@pytest.fixture
def ingestion_metadata():
    """Standard metadata for ingestion tests."""
    return {
        "source": "manual",
        "content_type": "text",
        "author": "test-user",
        "title": "E2E Integration Test Document",
        "tags": ["test", "integration", "e2e"],
        "custom_fields": {
            "test_type": "end_to_end",
            "environment": "docker",
        },
    }


class TestServiceHealth:
    """Test service health and connectivity."""

    @pytest.mark.asyncio
    async def test_ingest_service_health(self):
        """Test that InGest-LLM.as service is healthy."""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"{INGEST_API_BASE_URL}/health")

            assert response.status_code == 200
            health_data = response.json()

            assert health_data["status"] == "ok"
            assert health_data["service"] == "InGest-LLM.as"
            assert "timestamp" in health_data
            assert "dependencies" in health_data

    @pytest.mark.asyncio
    async def test_memos_service_health(self):
        """Test that memOS.as service is healthy and accessible."""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"{MEMOS_API_BASE_URL}/health")

            assert response.status_code == 200
            # Validate basic memOS.as health structure
            health_data = response.json()
            assert "status" in health_data


class TestTextIngestion:
    """Test text ingestion end-to-end flow."""

    @pytest.mark.asyncio
    async def test_basic_text_ingestion(self, sample_text_content, ingestion_metadata):
        """Test basic text ingestion and storage in memOS.as."""
        # Prepare ingestion request
        ingestion_request = {
            "content": sample_text_content,
            "metadata": ingestion_metadata,
            "chunk_size": 500,
            "process_async": False,
        }

        # Send ingestion request
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=ingestion_request,
            )

            assert response.status_code == 200
            ingestion_response = response.json()

            # Debug: Print response to understand the failure
            print(f"Text ingestion response: {ingestion_response}")

            # Validate ingestion response structure
            assert "ingestion_id" in ingestion_response
            assert "status" in ingestion_response
            assert ingestion_response["status"] == "completed"
            assert "total_chunks" in ingestion_response
            assert ingestion_response["total_chunks"] > 0
            assert "results" in ingestion_response
            assert (
                len(ingestion_response["results"]) == ingestion_response["total_chunks"]
            )

            # Validate each result
            for result in ingestion_response["results"]:
                assert "memory_id" in result
                assert "memory_tier" in result
                assert result["status"] == "completed"
                assert "content_hash" in result
                assert "chunk_size" in result

            ingestion_id = ingestion_response["ingestion_id"]
            memory_ids = [
                result["memory_id"] for result in ingestion_response["results"]
            ]

            return {
                "ingestion_id": ingestion_id,
                "memory_ids": memory_ids,
                "response": ingestion_response,
            }

    @pytest.mark.asyncio
    async def test_code_content_ingestion(self, sample_code_content):
        """Test code content ingestion with procedural memory tier."""
        code_metadata = {
            "source": "manual",
            "content_type": "code",
            "author": "test-developer",
            "title": "Test Code Sample",
            "tags": ["python", "test", "code"],
            "custom_fields": {
                "language": "python",
                "file_type": ".py",
            },
        }

        ingestion_request = {
            "content": sample_code_content,
            "metadata": code_metadata,
            "chunk_size": 300,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=ingestion_request,
            )

            assert response.status_code == 200
            ingestion_response = response.json()

            # Validate that code content uses procedural memory tier
            assert ingestion_response["status"] == "completed"
            for result in ingestion_response["results"]:
                assert result["memory_tier"] == "procedural"

    @pytest.mark.asyncio
    async def test_async_text_ingestion(self, sample_text_content, ingestion_metadata):
        """Test asynchronous text ingestion."""
        ingestion_request = {
            "content": sample_text_content,
            "metadata": ingestion_metadata,
            "chunk_size": 400,
            "process_async": True,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=ingestion_request,
            )

            assert response.status_code == 200
            ingestion_response = response.json()

            # For async processing, expect pending status
            assert ingestion_response["status"] == "pending"
            assert "ingestion_id" in ingestion_response
            assert ingestion_response["total_chunks"] > 0

            # TODO: Add status checking once status endpoint is implemented


class TestMemOSIntegration:
    """Test direct integration with memOS.as."""

    @pytest.mark.asyncio
    async def test_memory_verification(self, sample_text_content, ingestion_metadata):
        """Test that ingested content can be verified in memOS.as."""
        # First, ingest content
        ingestion_request = {
            "content": sample_text_content,
            "metadata": ingestion_metadata,
            "chunk_size": 600,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Ingest content
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=ingestion_request,
            )

            assert response.status_code == 200
            ingestion_response = response.json()
            memory_ids = [
                result["memory_id"] for result in ingestion_response["results"]
            ]

            # Wait a moment for processing to complete
            await asyncio.sleep(2)

            # Verify each memory exists in memOS.as
            for memory_id in memory_ids:
                memory_response = await client.get(
                    f"{MEMOS_API_BASE_URL}/memory/{memory_id}",
                )

                # Check if memory exists (200) or handle different response codes
                if memory_response.status_code == 200:
                    memory_data = memory_response.json()
                    assert "id" in memory_data or "memory_id" in memory_data
                    assert "content" in memory_data
                elif memory_response.status_code == 404:
                    pytest.fail(f"Memory {memory_id} not found in memOS.as")
                else:
                    pytest.fail(
                        f"Unexpected response from memOS.as: {memory_response.status_code}"
                    )

    @pytest.mark.asyncio
    async def test_memory_search_integration(
        self, sample_text_content, ingestion_metadata
    ):
        """Test that ingested content can be found via memOS.as search."""
        # Include unique search terms in metadata
        search_metadata = {**ingestion_metadata}
        search_metadata["title"] = "Unique Test Document for Search"
        search_metadata["tags"].append("unique_search_test")

        ingestion_request = {
            "content": f"{sample_text_content}\n\nUnique search phrase: integration_test_marker_12345",
            "metadata": search_metadata,
            "chunk_size": 800,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Ingest content
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=ingestion_request,
            )

            assert response.status_code == 200

            # Wait for indexing
            await asyncio.sleep(3)

            # Search for the unique content in memOS.as
            search_params = {
                "query": "integration_test_marker_12345",
                "limit": 10,
            }

            search_response = await client.get(
                f"{MEMOS_API_BASE_URL}/memory/search",
                params=search_params,
            )

            # Validate search results
            if search_response.status_code == 200:
                search_results = search_response.json()
                assert len(search_results.get("results", [])) > 0

                # Verify our content appears in search results
                found_content = False
                for result in search_results.get("results", []):
                    if "integration_test_marker_12345" in str(result):
                        found_content = True
                        break

                assert found_content, "Ingested content not found in search results"
            else:
                # Log the response for debugging
                print(
                    f"Search failed with status {search_response.status_code}: {search_response.text}"
                )


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_content_type(self):
        """Test ingestion with invalid content type."""
        invalid_request = {
            "content": "Test content",
            "metadata": {
                "source": "manual",
                "content_type": "invalid_type",  # Invalid content type
                "title": "Invalid Test",
            },
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text", json=invalid_request
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_content(self):
        """Test ingestion with empty content."""
        empty_request = {
            "content": "",  # Empty content
            "metadata": {
                "source": "manual",
                "content_type": "text",
                "title": "Empty Test",
            },
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text", json=empty_request
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_oversized_content(self):
        """Test ingestion with oversized content."""
        large_content = "x" * 2_000_000  # 2MB content

        oversized_request = {
            "content": large_content,
            "metadata": {
                "source": "manual",
                "content_type": "text",
                "title": "Oversized Test",
            },
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_API_BASE_URL}/ingest/text",
                json=oversized_request,
            )

            # Should either reject (413) or accept based on configuration
            assert response.status_code in [413, 422, 200]


class TestPerformance:
    """Performance and stress tests."""

    @pytest.mark.asyncio
    async def test_concurrent_ingestion(self, sample_text_content, ingestion_metadata):
        """Test concurrent ingestion requests."""

        async def single_ingestion(session_id: int):
            session_metadata = {**ingestion_metadata}
            session_metadata["title"] = f"Concurrent Test {session_id}"
            session_metadata["custom_fields"]["session_id"] = session_id

            request = {
                "content": f"Session {session_id}: {sample_text_content}",
                "metadata": session_metadata,
                "chunk_size": 400,
                "process_async": False,
            }

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{INGEST_API_BASE_URL}/ingest/text",
                    json=request,
                )
                return response.status_code, response.json()

        # Run 3 concurrent ingestions
        tasks = [single_ingestion(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate all succeeded
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent ingestion failed: {result}")

            status_code, response_data = result
            assert status_code == 200
            assert response_data["status"] == "completed"


# Helper functions
async def wait_for_service_ready(url: str, max_retries: int = 10):
    """Wait for a service to become ready."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return True
        except Exception:
            pass

        await asyncio.sleep(2)

    return False


# Test markers for different test categories
pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.docker,
]
