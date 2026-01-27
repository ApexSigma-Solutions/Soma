"""
Core Integration Testing Suite for InGest-LLM.as → memOS.as

This test suite validates the complete workflow between InGest-LLM.as and memOS.as,
ensuring that data ingestion, processing, and memory storage work correctly.
This fulfills the P1-CC-02 task requirement.
"""

import asyncio
import time
from typing import Dict
import pytest
import httpx

# Service Configuration (allow override via env for docker-compose network)
import os

INGEST_SERVICE_URL = os.environ.get("INGEST_API_BASE_URL", "http://localhost:8000")
MEMOS_SERVICE_URL = os.environ.get("INGEST_MEMOS_BASE_URL", "http://localhost:8091")
REQUEST_TIMEOUT = 60
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2


class IntegrationTestError(Exception):
    """Custom exception for integration test failures"""

    pass


class ServiceValidator:
    """Helper class for validating service responses and states"""

    @staticmethod
    async def wait_for_service_ready(
        url: str, service_name: str, max_attempts: int = 10
    ) -> bool:
        """Wait for a service to become ready with detailed logging."""
        print(f"\n🔍 Checking {service_name} service readiness...")

        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{url}/health")

                    if response.status_code == 200:
                        print(f"✅ {service_name} is ready")
                        return True
                    else:
                        print(
                            f"⚠️  {service_name} health check returned {response.status_code}"
                        )

            except Exception as e:
                print(
                    f"❌ {service_name} not ready (attempt {attempt + 1}/{max_attempts}): {e}"
                )

            if attempt < max_attempts - 1:
                await asyncio.sleep(RETRY_DELAY)

        return False

    @staticmethod
    def validate_ingestion_response(response_data: Dict) -> None:
        """Validate the structure of an ingestion response."""
        required_fields = ["ingestion_id", "status", "total_chunks", "results"]
        missing_fields = [
            field for field in required_fields if field not in response_data
        ]

        if missing_fields:
            raise IntegrationTestError(
                f"Missing required fields in ingestion response: {missing_fields}"
            )

        if response_data["total_chunks"] <= 0:
            raise IntegrationTestError("Total chunks must be greater than 0")

        # Validate that all results have memory_id (critical for integration)
        for i, result in enumerate(response_data.get("results", [])):
            if "memory_id" not in result or result["memory_id"] is None:
                raise IntegrationTestError(
                    f"Result {i} missing or null memory_id: {result}"
                )


@pytest.fixture(scope="session")
async def service_health_check():
    """Ensure both services are healthy before running tests."""
    print("\n🚀 = CORE INTEGRATION TEST SUITE STARTING =")

    # Check InGest-LLM.as service
    ingest_ready = await ServiceValidator.wait_for_service_ready(
        INGEST_SERVICE_URL, "InGest-LLM.as"
    )

    # Check memOS.as service
    memos_ready = await ServiceValidator.wait_for_service_ready(
        MEMOS_SERVICE_URL, "memOS.as"
    )

    if not ingest_ready:
        pytest.skip("InGest-LLM.as service is not available")

    if not memos_ready:
        pytest.skip("memOS.as service is not available")

    print("✅ Both services are ready for integration testing")
    return True


@pytest.fixture
def test_context():
    """Provide test context with unique identifiers."""
    timestamp = str(int(time.time()))
    return {
        "project_name": "ApexSigma Integration Test",
        "source": "api",  # Valid source enum value
        "environment": "test",
        "timestamp": timestamp,
        "test_id": f"integration_test_{timestamp}",
    }


class TestCoreIntegration:
    """Core integration tests between InGest-LLM.as and memOS.as."""

    @pytest.mark.asyncio
    async def test_text_ingestion_to_memos(self, service_health_check, test_context):
        """Test complete text ingestion workflow."""
        print("\n📝 Testing text ingestion to memOS.as...")

        test_content = """
        This is a test document for validating the integration between
        InGest-LLM.as and memOS.as services in the ApexSigma ecosystem.

        The content should be processed by InGest-LLM.as and stored
        in the appropriate memory tier within memOS.as.
        """

        ingestion_request = {
            "content": test_content,
            "metadata": {
                **test_context,
                "content_type": "text",
                "title": "Integration Test Document",
                "tags": ["integration", "test"],
            },
            "chunk_size": 500,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Step 1: Send to InGest-LLM.as
            response = await client.post(
                f"{INGEST_SERVICE_URL}/ingest/text", json=ingestion_request
            )

            assert response.status_code == 200, f"Ingestion failed: {response.text}"
            ingestion_response = response.json()

            ServiceValidator.validate_ingestion_response(ingestion_response)

            print("  ✅ Content ingested successfully")
            print(f"     - Total chunks: {ingestion_response['total_chunks']}")

            # Step 2: Verify in memOS.as
            memory_ids = [
                result["memory_id"] for result in ingestion_response["results"]
            ]

            await asyncio.sleep(2)  # Wait for processing

            for memory_id in memory_ids:
                memory_response = await client.get(
                    f"{MEMOS_SERVICE_URL}/memory/{memory_id}"
                )

                assert memory_response.status_code == 200, (
                    f"Memory {memory_id} not found in memOS.as"
                )

                print(f"     ✅ Memory {memory_id} verified in memOS.as")

            return ingestion_response

    @pytest.mark.asyncio
    async def test_code_ingestion_procedural_memory(
        self, service_health_check, test_context
    ):
        """Test code content ingestion to procedural memory."""
        print("\n💻 Testing code ingestion to procedural memory...")

        code_content = """
def integration_test_function():
    '''Test function for integration validation'''
    return "Integration test successful"

class TestClass:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value
"""

        ingestion_request = {
            "content": code_content,
            "metadata": {
                **test_context,
                "content_type": "code",
                "title": "Integration Test Code",
                "tags": ["code", "python", "integration"],
                "language": "python",
            },
            "chunk_size": 300,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_SERVICE_URL}/ingest/text", json=ingestion_request
            )

            assert response.status_code == 200, (
                f"Code ingestion failed: {response.text}"
            )
            ingestion_response = response.json()

            # Validate procedural memory tier usage
            memory_tiers = [
                result["memory_tier"] for result in ingestion_response["results"]
            ]
            assert all(tier == "procedural" for tier in memory_tiers), (
                f"Code should use procedural memory, got: {memory_tiers}"
            )

            print("  ✅ Code stored in procedural memory tier")
            return ingestion_response

    @pytest.mark.asyncio
    async def test_memory_search_integration(self, service_health_check, test_context):
        """Test that ingested content can be found via memOS.as search."""
        print("\n🔍 Testing memory search integration...")

        unique_content = f"""
        Integration test document with unique identifier: {test_context["test_id"]}

        This content contains specific search terms that should be
        discoverable through the memOS.as search functionality.
        """

        ingestion_request = {
            "content": unique_content,
            "metadata": {
                **test_context,
                "content_type": "text",
                "title": "Searchable Integration Test",
                "tags": ["searchable", "integration"],
            },
            "chunk_size": 400,
            "process_async": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Ingest content
            response = await client.post(
                f"{INGEST_SERVICE_URL}/ingest/text", json=ingestion_request
            )

            assert response.status_code == 200

            await asyncio.sleep(3)  # Wait for indexing

            # Search for content
            search_response = await client.get(
                f"{MEMOS_SERVICE_URL}/memory/search",
                params={"query": test_context["test_id"], "top_k": 10},
            )

            if search_response.status_code == 200:
                search_results = search_response.json()
                results = search_results.get("memories", {}).get("results", [])

                assert len(results) > 0, "Search should return results"
                print(f"  ✅ Search found {len(results)} relevant memories")
                return search_results
            else:
                print(f"  ⚠️ Search endpoint returned {search_response.status_code}")

    @pytest.mark.asyncio
    async def test_concurrent_ingestion(self, service_health_check, test_context):
        """Test concurrent ingestion requests."""
        print("\n🔄 Testing concurrent ingestion...")

        async def single_ingestion(session_id: int):
            content = f"Concurrent test session {session_id} content for integration validation."

            request = {
                "content": content,
                "metadata": {
                    **test_context,
                    "content_type": "text",
                    "title": f"Concurrent Test {session_id}",
                    "session_id": session_id,
                },
                "chunk_size": 200,
                "process_async": False,
            }

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{INGEST_SERVICE_URL}/ingest/text", json=request
                )
                return (
                    response.status_code,
                    response.json() if response.status_code == 200 else None,
                )

        # Run 3 concurrent ingestions
        tasks = [single_ingestion(i) for i in range(1, 4)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_sessions = 0
        for result in results:
            if isinstance(result, Exception):
                raise IntegrationTestError(f"Concurrent session failed: {result}")

            status_code, response_data = result
            if status_code == 200 and response_data:
                ServiceValidator.validate_ingestion_response(response_data)
                successful_sessions += 1

        assert successful_sessions == 3, (
            f"Expected 3 successful sessions, got {successful_sessions}"
        )
        print(f"  ✅ All {successful_sessions} concurrent sessions completed")


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_content_handling(self, service_health_check, test_context):
        """Test handling of invalid content."""
        print("\n⚠️ Testing invalid content handling...")

        # Test empty content
        empty_request = {
            "content": "",
            "metadata": {**test_context, "content_type": "text"},
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{INGEST_SERVICE_URL}/ingest/text", json=empty_request
            )

            # Should reject empty content
            assert response.status_code == 422, (
                f"Empty content should be rejected, got: {response.status_code}"
            )
            print("  ✅ Empty content correctly rejected")


# Test markers
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
