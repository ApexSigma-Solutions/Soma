import logging
from typing import List, Optional
import openai
from omega_kg.settings import settings

logger = logging.getLogger("omega.services.embedding")

# --- CLIENT CONFIGURATION ---
# We configure the client once at module level to avoid overhead per request.
# Supports both OpenAI (Cloud) and Ollama (Local) via the OpenAI-compatible API.

client: Optional[openai.AsyncOpenAI] = None
DEFAULT_MODEL: Optional[str] = None

# Using lower() to be safe with string comparison
provider = settings.embedding_provider.lower()

if provider == "openai":
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    # Default OpenAI model (1536d)
    DEFAULT_MODEL = "text-embedding-3-small"

elif provider == "ollama":
    # Point to local Ollama instance
    # Default to standard Ollama port if not in settings
    # Accessing via getattr to fallback safely if not in settings model yet,
    # though it should be populated by the Settings class logic.
    ollama_url = getattr(settings, "ollama_base_url", "http://localhost:11434/v1")
    # Ensure URL ends with /v1 for OpenAI client compatibility if not present
    if not ollama_url.endswith("/v1"):
        ollama_url = f"{ollama_url.rstrip('/')}/v1"

    client = openai.AsyncOpenAI(
        base_url=ollama_url,
        api_key="ollama",  # Required string, but ignored by Ollama
    )

    # Default to bge-m3 (1024d) as per Mission Brief/Schema requirements.
    # We try to get OLLAMA_EMBEDDING_MODEL from settings, otherwise default.
    DEFAULT_MODEL = getattr(settings, "ollama_embedding_model", "bge-m3")

else:
    logger.warning(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")


async def generate_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for the given text.

    Providers:
    - 'openai': Uses text-embedding-3-small (1536d)
    - 'ollama': Uses local LLM (e.g., bge-m3 1024d or nomic-embed-text 768d)
    """
    if not text:
        return []

    if not client:
        logger.error("Embedding client not initialized. Check settings.")
        return []

    try:
        # Sanitize input (newlines can degrade performance of some embedding models)
        clean_text = text.replace("\n", " ")

        response = await client.embeddings.create(input=clean_text, model=DEFAULT_MODEL)

        # Check if response.data is populated
        if not response.data:
            logger.error("No embedding data returned from provider")
            return []

        embedding = response.data[0].embedding

        # Validation Log (Debug level recommended for production)
        # logger.debug(f"Generated embedding via {DEFAULT_MODEL}: {len(embedding)} dimensions")

        return embedding

    except openai.APIConnectionError:
        logger.error(
            f"Failed to connect to Embedding Provider ({settings.embedding_provider}). Is Ollama running?"
        )
        return []
    except Exception as e:
        logger.error(f"Embedding Generation Failed: {e}")
        return []
