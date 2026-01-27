from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env for compatibility
    )

    memos_db_type: str = "sqlite"
    memos_db_path: str = "/data/sqlite/memory.db"

    # PostgreSQL settings - aligned with shared OmegaKG infrastructure
    postgres_host: str = "localhost"
    postgres_port: int = 6000  # Shared apexsigma.postgres.stable container
    postgres_db: str = "omega_kg_stable"
    postgres_user: str = "omega_user"
    postgres_password: Optional[str] = None
    postgres_schema: str = "memos"

    # PGVector settings
    embedding_dimension: int = 1024
    embedding_model: str = "bge-m3"  # Default to bge-m3, matching OmegaKG

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_request_timeout: int = 60

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: Optional[str] = None

    fastmcp_server_port: int = 8768
    fastmcp_server_host: str = "0.0.0.0"
    fastmcp_server_log_level: str = "INFO"
    fastmcp_server_transport: str = "sse"

    memos_enable_tool_registry: bool = True
    memos_enable_graph_memory: bool = False
    memos_max_memory_size: int = 1000

    # Redis settings (ephemeral memory) - aligned with memos-redis-mcp container
    memos_redis_host: str = "localhost"
    memos_redis_port: int = 6380  # Using 6380 to avoid Windows Docker port conflicts
    memos_redis_password: Optional[str] = None
    memos_redis_db: int = 0

    # Janitor Worker settings (Pulse system)
    # Janitor can run on Windows with non-blocking reads (block_ms=None).
    # Override via JANITOR_ENABLED env var if needed.
    janitor_enabled: bool = True
    janitor_buffer_size: int = 10  # Events before consolidation
    janitor_timeout_seconds: int = 300  # 5 minutes
    janitor_stream_key: str = "pulse:stream"
    janitor_max_stream_len: int = 1000
    omegakg_validate_url: str = "http://localhost:8765/api/validate"

    # InGest-LLM settings (memory promotion) - aligned with running service
    ingest_llm_url: str = "http://localhost:8766"  # Actual InGest-LLM port
    ingest_llm_timeout: int = 30
    memory_promotion_threshold: float = 0.7  # Auto-promote if significance >= threshold

    # Better Web Service (BWS) API Configuration
    bws_access_token: Optional[str] = None
    bws_api_key: Optional[str] = None
    bws_api_secret: Optional[str] = None
    bws_base_url: str = "https://api.betterwebservice.com"
    bws_timeout: int = 30

    # BWS Secret IDs (for Bitwarden integration)
    linear_webhook_secret_prd_id: Optional[str] = None
    postgres_password_prd_id: Optional[str] = None
    neo4j_password_prd_id: Optional[str] = None
    linear_api_key_prd_id: Optional[str] = None
    perplexity_api_key_prd_id: Optional[str] = None
    gemini_api_key_prd_id: Optional[str] = None
    nanogpt_omegakg_api_key: Optional[str] = None
    jwt_secret_key_id: Optional[str] = None
    ollama_okg_api_key_prd_id: Optional[str] = None
    hookdeck_api_key_prd_id: Optional[str] = None
    bws_api_key_prd_id: Optional[str] = None
    bws_api_secret_prd_id: Optional[str] = None

    @model_validator(mode="after")
    def check_passwords(self) -> "Settings":
        if self.memos_db_type == "postgres" and not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD must be set when using PostgreSQL")
        if self.memos_enable_graph_memory and not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD must be set when graph memory is enabled")
        return self


settings = Settings()
