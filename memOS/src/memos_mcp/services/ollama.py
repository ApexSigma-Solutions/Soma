"""
Ollama Service for memOS.

Provides interface for Embedding generation and Chat completions.
"""

import httpx
import logging
from typing import List, Dict, Optional

from memos_mcp.config import settings

logger = logging.getLogger("memos.mcp.services.ollama")


class OllamaService:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.timeout = settings.ollama_request_timeout
        self.embedding_model = settings.embedding_model

    async def get_embedding(
        self, text: str, model: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for text using Ollama.
        """
        model = model or self.embedding_model

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text,
                        "options": {"num_ctx": 4096},  # Ensure enough context
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["embedding"]

        except Exception as e:
            logger.error(f"Failed to generate embedding with {model}: {e}")
            # Fallback for dev/testing if model missing, but ideally we should fail hard in prod
            # For robustness, we re-raise
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen2.5-coder",
        temperature: float = 0.7,
    ) -> str:
        """
        Get chat completion from Ollama.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": temperature},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

        except Exception as e:
            logger.error(f"Failed to get chat completion from {model}: {e}")
            raise


# Global instance
ollama_service = OllamaService()
