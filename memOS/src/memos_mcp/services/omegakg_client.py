"""OmegaKG Client for memOS.

TN-SOMA-304: Handshake Protocol implementation.
Provides read-only access to the Brain (OmegaKG) via the Guardian API.
This replaces direct Neo4j drivers in memOS.
"""

import os
import httpx
import logging
from typing import Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger("memos.omegakg")

OMEGAKG_URL = os.getenv("OMEGA_KG_URL", "http://localhost:8765")
SOMA_INTERNAL_KEY = os.getenv("SOMA_INTERNAL_KEY", "")


class QueryResponse(BaseModel):
    status: str
    count: int
    results: List[Dict[str, Any]]


class OmegaKGClient:
    """HTTP Client for interacting with OmegaKG Guardian API."""

    def __init__(self, base_url: str = OMEGAKG_URL, api_key: str = SOMA_INTERNAL_KEY):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "X-Soma-Key": api_key,
            "User-Agent": "memOS/Mimir-Protocol-v1",
        }

    async def query(self, cypher: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Execute a read-only Cypher query via Guardian.

        Args:
            cypher: The Cypher query string (must be read-only).
            limit: Max results to return.

        Returns:
            List of result records.

        Raises:
            httpx.HTTPError: If the request fails.
            ValueError: If the query is rejected (e.g. write attempt).
        """
        endpoint = f"{self.base_url}/guardian/query"
        payload = {"cypher": cypher, "limit": limit}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    endpoint, json=payload, headers=self.headers
                )
                response.raise_for_status()

                data = response.json()

                if data.get("status") == "rejected":
                    raise ValueError(
                        f"Query rejected by Guardian: {data.get('results')}"
                    )

                if data.get("status") == "error":
                    raise RuntimeError(f"Guardian error: {data.get('results')}")

                return data.get("results", [])

            except httpx.HTTPError as e:
                logger.error(f"OmegaKG query failed: {e}")
                raise

    async def check_health(self) -> Dict[str, Any]:
        """Check if OmegaKG is alive."""
        endpoint = f"{self.base_url}/guardian/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(endpoint)
            return response.json()
