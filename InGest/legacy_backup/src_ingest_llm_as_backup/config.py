"""ingest_llm_as configuration.

Settings are loaded via Pydantic BaseSettings from environment variables.

Important project convention:
- Settings are intentionally non-cached. Prefer calling :func:`get_settings` inside
    request-scoped code / constructors.
- ``.env`` is host-local and must not be committed; use ``.env.example``.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    app_name: str = Field(default="InGest-LLM.as", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    app_env: str = Field(
        default="development",
        description="Application environment (development|staging|production)",
    )
    debug: bool = Field(default=False, description="Debug mode")
    hello: Optional[str] = Field(default=None, description="Development setting")

    # Security configuration
    zero_trust_required: bool = Field(
        default=False,
        description="Enforce Bitwarden-only secret storage (zero-trust mode)",
    )
    bws_access_token: Optional[str] = Field(
        default=None, description="Bitwarden Secrets Manager access token"
    )

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
    memos_enabled: bool = Field(default=True, description="Enable memOS integration")

    # Processing limits
    max_content_size: int = Field(
        default=1_000_000, description="Max content size in bytes (1MB)"
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

    # Ollama embedding service
    ollama_base_url: str = Field(
        default="http://0.0.0.0:11434", description="Ollama API base URL"
    )
    ollama_api_key: Optional[str] = Field(default=None, description="Ollama API key")
    ollama_timeout: int = Field(default=30, description="Ollama timeout in seconds")
    ollama_enabled: bool = Field(default=True, description="Enable Ollama integration")
    ollama_host_url: str = Field(
        default="http://localhost:11434", description="Ollama host URL for heartbeat"
    )

    # QuiPU monitoring
    heartbeat_interval_sec: int = Field(
        default=60, description="Heartbeat check interval in seconds"
    )
    quipu_service_name: str = Field(
        default="ollama-server-01",
        description="Service identifier for heartbeat records",
    )

    # PostgreSQL configuration
    postgres_dsn: Optional[str] = Field(
        default=None, description="PostgreSQL connection string"
    )
    postgres_user: str = Field(default="ingest_user", description="PostgreSQL user")
    postgres_db: str = Field(
        default="ingest_db", description="PostgreSQL database name"
    )
    postgres_server: str = Field(
        default="127.0.0.1", description="PostgreSQL server address"
    )
    postgres_port: int = Field(default=5800, description="PostgreSQL port")
    pg_conn: Optional[str] = Field(
        default=None, description="Legacy PostgreSQL connection string"
    )

    # Neo4j configuration
    neo4j_uri: str = Field(
        default="bolt://localhost:7687", description="Neo4j connection URI"
    )
    neo4j_bolt_port: int = Field(default=7687, description="Neo4j Bolt port")
    neo4j_http_port: int = Field(default=7474, description="Neo4j HTTP port")
    neo4j_user: str = Field(default="neo4j", description="Neo4j user")
    neo4j_heap_size: str = Field(default="512M", description="Neo4j heap size")
    neo4j_host_data_path: str = Field(
        default="D:/docker-data/omega_kg_stable/neo4j", description="Neo4j data path"
    )

    # Linear integration
    linear_webhook_secret: Optional[str] = Field(
        default=None, description="Linear webhook secret"
    )
    linear_team_id: str = Field(default="ALPHA", description="Linear team ID")
    linear_workspace_id: str = Field(
        default="ApexSigma-Solutions", description="Linear workspace ID"
    )
    linear_project_id: str = Field(
        default="InGest-LLM", description="Linear project ID"
    )

    # AI Services API keys
    nanogpt_api_key: Optional[str] = Field(default=None, description="NanoGPT API key")
    openrouter_api_key: Optional[str] = Field(
        default=None, description="OpenRouter API key"
    )
    perplexity_api_key_prd: Optional[str] = Field(
        default=None, description="Perplexity API key (production)"
    )
    gemini_api_key_prd: Optional[str] = Field(
        default=None, description="Gemini API key (production)"
    )

    # Omnisearch - Search Providers
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")
    brave_api_key: Optional[str] = Field(
        default=None, description="Brave Search API key"
    )
    kagi_api_key: Optional[str] = Field(default=None, description="Kagi Search API key")
    exa_api_key: Optional[str] = Field(default=None, description="Exa AI API key")
    github_api_key: Optional[str] = Field(default=None, description="GitHub API key")

    # Omnisearch - AI Response Providers
    perplexity_ai_api_key: Optional[str] = Field(
        default=None, description="Perplexity AI API key"
    )

    # Omnisearch - Content Processing
    jina_ai_api_key: Optional[str] = Field(default=None, description="Jina AI API key")
    firecrawl_api_key: Optional[str] = Field(
        default=None, description="Firecrawl API key"
    )
    firecrawl_base_url: Optional[str] = Field(
        default=None, description="Firecrawl base URL"
    )

    # Apidog configuration
    apidog_access_token: Optional[str] = Field(
        default=None, description="Apidog access token"
    )
    apidog_project_id: str = Field(default="", description="Apidog project ID")

    # Paths
    obsidian_vault_path: str = Field(
        default="./vault", description="Path to Obsidian vault"
    )
    ai_conversations_path: str = Field(
        default="./vault/AI_Conversations", description="Path to AI conversations"
    )
    obsidian_vault_scan_folders: str = Field(
        default="", description="Comma-separated list of folders to scan"
    )

    # Bitwarden Secret IDs
    linear_webhook_secret_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Linear webhook secret"
    )
    github_webhook_secret_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for GitHub webhook secret"
    )
    postgres_password_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for PostgreSQL password"
    )
    neo4j_password_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Neo4j password"
    )
    extension_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for extension API key"
    )
    linear_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Linear API key"
    )
    perplexity_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Perplexity API key"
    )
    gemini_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Gemini API key"
    )
    nanogpt_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for NanoGPT API key"
    )
    ollama_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Ollama API key"
    )
    hookdeck_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Hookdeck API key"
    )
    jwt_secret_key_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for JWT secret"
    )
    tavily_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Tavily API key"
    )
    brave_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Brave API key"
    )
    kagi_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Kagi API key"
    )
    exa_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Exa API key"
    )
    github_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for GitHub API key"
    )
    jina_ai_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Jina AI API key"
    )
    firecrawl_api_key_prd_id: Optional[str] = Field(
        default=None, description="Bitwarden secret ID for Firecrawl API key"
    )

    # Logging (observability stack removed; keep basic log level control)
    log_level: str = Field(default="INFO", description="Log level")

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
