"""ingest_llm_as configuration.

Settings are loaded via Pydantic BaseSettings from environment variables.

Important project convention:
- Settings are intentionally non-cached. Prefer calling :func:`get_settings` inside
    request-scoped code / constructors.
- ``.env`` is host-local and must not be committed; use ``.env.example``.
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    app_name: str = Field(default="InGest-LLM.as", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    hello: Optional[str] = Field(default=None, description="Development setting")

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Service endpoints integration
    base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for this service",
    )
    memos_base_url: str = Field(
        default="http://memos:8090",
        description="memOS API base URL",
    )
    memos_api_key: Optional[str] = Field(default=None, description="memOS API key")
    memos_timeout: int = Field(default=30, description="memOS API timeout in seconds")

    # Webhook Secrets
    linear_webhook_secret: Optional[str] = Field(
        default=None,
        description="Linear Webhook Secret",
        validation_alias="LINEAR_WEBHOOK_SECRET",
    )
    github_webhook_secret: Optional[str] = Field(
        default=None,
        description="GitHub Webhook Secret",
        validation_alias="GITHUB_WEBHOOK_SECRET",
    )

    # Processing limits
    max_content_size: int = Field(
        default=1_000_000, description="Max content size in bytes (1MB)"
    )
    max_payload_size: int = Field(
        default=5_000_000,
        description="Max total payload size in bytes (5MB) for DoS protection",
        validation_alias="MAX_PAYLOAD_SIZE",
    )
    default_chunk_size: int = Field(default=1000, description="Default chunk size")
    max_chunks_per_request: int = Field(
        default=100, description="Max chunks per request"
    )

    # Async processing
    enable_async_processing: bool = Field(
        default=True, description="Enable async processing"
    )
    async_queue_max_size: int = Field(default=1000, description="Async queue max size")

    # LM Studio integration for embeddings
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1", description="LM Studio API base URL"
    )
    lm_studio_api_key: Optional[str] = Field(
        default=None, description="LM Studio API key"
    )
    lm_studio_timeout: int = Field(
        default=30, description="LM Studio timeout in seconds"
    )
    lm_studio_enabled: bool = Field(
        default=True, description="Enable LM Studio integration"
    )

    # Embedding configuration
    embedding_enabled: bool = Field(
        default=True, description="Enable embedding generation"
    )
    embedding_batch_size: int = Field(default=10, description="Embedding batch size")
    embedding_dimension: int = Field(
        default=768, description="Embedding dimension (default for nomic-embed)"
    )

    # --- Neo4j Config ---
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j User")
    neo4j_password: str = Field(default="aDQUU5$@1dpuj5", description="Neo4j Password")

    # --- Runtime Configuration (TN-CTX-203) ---
    # Hot-reloadable runtime settings for metabolic control
    entropy_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Minimum entropy for digestion (Metabolic Gate) - dynamically adjustable",
    )

    # Logging (observability stack removed; keep basic log level control)
    log_level: str = Field(default="INFO", description="Log level")

    # --- LLM Summarization Config ---
    llm_provider: str = Field(
        default="ollama", description="LLM provider: 'ollama', 'openai', or 'nanogpt'"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Ollama Base URL (OpenAI compatible)",
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key")
    nanogpt_api_key: Optional[str] = Field(default=None, description="NanoGPT API Key")
    nanogpt_base_url: str = Field(
        default="https://nano-gpt.com/api/v1", description="NanoGPT Base URL"
    )
    # For Ollama, the model might be 'llama3' or 'mistral'. For OpenAI, 'gpt-4o'.
    summarization_model: str = Field(
        default="llama3.1", description="Model used for summarization"
    )

    # --- Redis Config (Pulse/Nervous System) ---
    redis_host: str = Field(
        default="localhost", description="Redis host for Pulse emitter"
    )
    redis_port: int = Field(default=6380, description="Redis port for Pulse emitter")
    redis_key_prefix: str = Field(
        default="pulse:", description="Redis key prefix for pulse stream"
    )

    # --- Database Config ---
    # Connection string to the Ingest Database (where raw_ingestions table lives)
    # Defaulting to the known local value or override via env INGEST_RAW_DB_URL
    raw_db_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:6000/ingest_db",
        description="Connection string for Ingest Database",
    )

    # --- OmegaKG Integration (TN-CORE-103) ---
    omegakg_api_url: str = Field(
        default="http://localhost:8765", description="OmegaKG validation API base URL"
    )
    bws_access_token: Optional[str] = Field(
        None,
        validation_alias="BWS_ACCESS_TOKEN",
        description="Bitwarden Secrets Manager access token for service authentication",
    )
    static_service_token: Optional[str] = Field(
        None,
        validation_alias="STATIC_SERVICE_TOKEN",
        description="Static token for local development",
    )
    # Vault Path for writing summaries
    obsidian_vault_path: str = Field(
        default="C:/Users/steyn/Documents/Obsidian Vault",
        description="Path to Obsidian Vault",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INGEST_",
        extra="ignore",
        # CRITICAL: Force reload on every access to prevent caching
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


# CRITICAL: Dynamic settings loading function to prevent caching issues
def get_settings() -> Settings:
    """
    Get fresh settings instance with current environment variables.

    This function prevents the caching issues that occur when settings
    are loaded at module import time.
    """
    # Create a new instance which will reload from environment
    return Settings()


# For backward compatibility, provide a settings instance
# but use get_settings() for any new code
settings = get_settings()
