"""
OmegaClient - HTTP client for OmegaKG Guardian API.

Handles communication between InGest-LLM and OmegaKG for persisting
processed intelligence via /api/v1/guardian/commit endpoint.
"""

import logging
from typing import Dict, Any, Optional

import httpx


logger = logging.getLogger(__name__)


class OmegaClient:
    """
    HTTP client for OmegaKG Guardian API.

    Handles POST requests to /api/v1/guardian/commit endpoint
    to persist processed intelligence.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize OmegaClient.

        Args:
            base_url: Base URL for OmegaKG API (default: localhost:8765)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Configure httpx client
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

        # Set API key header if provided
        if self.api_key:
            self._client.headers.update({"X-API-Key": self.api_key})

        logger.info(
            f"OmegaClient initialized: base_url={self.base_url}, "
            f"api_key={'configured' if self.api_key else 'none'}, "
            f"timeout={self.timeout}s"
        )

    async def commit_data(
        self,
        raw_id: str,
        digest: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Commit processed intelligence to OmegaKG Guardian API.

        Args:
            raw_id: Unique identifier for data ('conversation' or 'terminal')
            digest: KnowledgeDigest containing title, summary, entities, concepts, decisions, outcomes, tags
            metadata: Optional metadata dictionary (e.g., platform, command)

        Returns:
            Dict with 'success' (bool), 'message' (str), and 'storage_results' (Dict)

        Raises:
            httpx.HTTPStatusError: For HTTP errors (4xx, 5xx)
            httpx.TimeoutException: For request timeout
            httpx.NetworkError: For network connectivity issues
            Exception: For unexpected errors
        """
        url = f"{self.base_url}/api/v1/guardian/commit"

        # Build request payload
        payload = {
            "raw_id": raw_id,
            "digest": digest,
        }

        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata

        logger.info(f"Committing data to OmegaKG: raw_id={raw_id}")

        try:
            response = await self._client.post(
                url, json=payload, headers=self._client.headers
            )

            # Handle successful response
            if response.status_code == 200:
                result = await response.json()
                logger.info(
                    f"Successfully committed data: raw_id={raw_id}, "
                    f"success={result.get('success', False)}, "
                    f"message={result.get('message', '')}"
                )
                return {
                    "success": True,
                    "message": result.get(
                        "message", "Knowledge committed successfully"
                    ),
                    "storage_results": result.get("storage_results", {}),
                }

            # Handle HTTP errors (4xx)
            elif 400 <= response.status_code < 500:
                error_data = await response.json()
                error_msg = error_data.get(
                    "error", f"Client error: HTTP {response.status_code}"
                )
                logger.error(error_msg)
                return {"success": False, "message": error_msg, "storage_results": {}}

            # Handle server errors (5xx)
            elif response.status_code >= 500:
                error_data = await response.json()
                error_msg = error_data.get(
                    "error", f"Server error: HTTP {response.status_code}"
                )
                logger.error(error_msg)
                return {"success": False, "message": error_msg, "storage_results": {}}

            # Handle other status codes
            else:
                error_msg = f"Unexpected status code: HTTP {response.status_code}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg, "storage_results": {}}

        except httpx.TimeoutException:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "storage_results": {}}

        except httpx.NetworkError as e:
            error_msg = str(e)
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "storage_results": {}}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg, "storage_results": {}}

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self._client.aclose()
        logger.info("OmegaClient closed")

    async def __aenter__(self):
        """Async context manager for resource cleanup."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Ensure client is closed on context exit."""
        await self.close()
