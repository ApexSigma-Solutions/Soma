"""HTTP Client for OmegaKG Validation API.

Handles authentication and structured knowledge digest submission.
"""

import httpx
import logging
import asyncio
from typing import Dict, Any
from urllib.parse import urlparse
from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)


class OmegaKGClient:
    """
    HTTP client for OmegaKG validation API.

    Handles authentication, retries, and error handling for
    structured knowledge digest submission.
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.omegakg_api_url
        self.token = (
            self.settings.bws_access_token or self.settings.static_service_token
        )
        self.timeout = httpx.Timeout(30.0, connect=5.0)

        # SECURITY: Validate HTTPS usage when token authentication is enabled
        if self.token and self.base_url:
            parsed = urlparse(self.base_url)
            scheme = parsed.scheme.lower()
            hostname = parsed.hostname or ""

            # Check if using HTTP (not HTTPS) with non-localhost hostname
            is_localhost = hostname in ("localhost", "127.0.0.1", "::1")
            is_insecure_http = (scheme == "http") and not is_localhost

            if is_insecure_http:
                # Using HTTP with authentication outside of localhost is a security risk
                logger.warning(
                    "SECURITY WARNING: OmegaKG API URL uses HTTP (not HTTPS) with authentication. "
                    f"Token transmission is vulnerable to interception: {self.base_url}"
                )
                # In production environments, we should enforce HTTPS
                if self.settings.debug is False:
                    raise ValueError(
                        "SECURITY ERROR: Cannot use HTTP (non-HTTPS) URL for OmegaKG API "
                        "with authentication in production. Use HTTPS to protect bearer tokens."
                    )

        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=headers
        )

    async def validate_and_store(
        self, digest: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Submit knowledge digest to OmegaKG validation API.

        Implements exponential backoff retry logic for transient failures.

        Args:
            digest: Structured knowledge digest (serialized dict)
            max_retries: Maximum retry attempts (default 3)

        Returns:
            ValidationResponse dict with status and node IDs

        Raises:
            httpx.HTTPError: On non-retryable errors (401, 403, 422)
            Exception: After max retries exhausted
        """
        attempt = 0
        backoff = 1  # Initial backoff 1 second

        while attempt <= max_retries:
            try:
                response = await self.client.post(
                    "/validate/validate-and-store", json=digest
                )

                # Success or validation rejection (don't retry)
                # 200: Handled success/rejection/duplicate
                # 409: Conflict/Duplicate (if the API chooses to return 409 instead of 200)
                if response.status_code in [200, 409]:
                    return response.json()

                # Authentication error (don't retry)
                if response.status_code == 401:
                    logger.error(f"OmegaKG API authentication failed: {response.text}")
                    raise httpx.HTTPError(f"Authentication failed: {response.text}")

                # Validation error (don't retry if it's a structural 422)
                if response.status_code == 422:
                    logger.error(
                        f"OmegaKG API structural validation error: {response.text}"
                    )
                    raise httpx.HTTPError(f"Validation error: {response.text}")

                # Server error (retry)
                if response.status_code >= 500:
                    if attempt < max_retries:
                        logger.warning(
                            f"OmegaKG API error {response.status_code}, "
                            f"retrying in {backoff}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        attempt += 1
                        continue
                    else:
                        raise Exception(
                            f"OmegaKG API failed after {max_retries} retries: "
                            f"{response.status_code} {response.text}"
                        )

                # Unexpected status code
                raise httpx.HTTPError(
                    f"Unexpected response from OmegaKG: {response.status_code} {response.text}"
                )

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Connection to OmegaKG failed/timed out, retrying in {backoff}s: {str(e)}"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    attempt += 1
                else:
                    raise Exception(
                        f"Failed to connect to OmegaKG after {max_retries} retries"
                    ) from e
            except Exception as e:
                if isinstance(e, httpx.HTTPError):
                    raise
                logger.error(f"Unexpected error calling OmegaKG API: {str(e)}")
                raise

        return {"status": "error", "message": "Max retries exceeded"}

    async def close(self):
        """Close HTTP client connection pool."""
        await self.client.aclose()
