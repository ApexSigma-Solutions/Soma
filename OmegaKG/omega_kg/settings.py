import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# CRITICAL: Load .env file BEFORE any Settings class instantiation
# This ensures environment variables override any shell/system values
from dotenv import load_dotenv

load_dotenv(override=True)

from bitwarden_sdk import BitwardenClient
from bitwarden_sdk.schemas import ClientSettings, DeviceType
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Omega Ingest Contract
# =============================================================================
# Path to the contract JSON (relative to this file's parent directory)
_CONTRACT_PATH = (
    Path(__file__).parent.parent.parent
    / "InGest-LLM.as"
    / "validators"
    / "omega_ingest_contract.json"
)


def load_ingest_contract() -> Dict[str, Any]:
    """Load the Omega ingest contract definition.

    Returns:
        The contract dict if available, empty dict otherwise.
    """
    if _CONTRACT_PATH.exists():
        try:
            with open(_CONTRACT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load Omega ingest contract: {e}")
    else:
        logger.debug(f"Omega ingest contract not found at: {_CONTRACT_PATH}")
    return {}


# Load contract at module import time
OMEGA_INGEST_CONTRACT = load_ingest_contract()
CONTRACT_VERSION = OMEGA_INGEST_CONTRACT.get("contract_version", "unknown")


class BitwardenSettingsSource(PydanticBaseSettingsSource):
    """
    Hybrid Source: Inject secrets from Bitwarden if BWS_ACCESS_TOKEN is present.
    """

    def get_field_value(self, _field: Any, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        bws_token = os.getenv("BWS_ACCESS_TOKEN")
        if not bws_token:
            logger.debug("BWS_ACCESS_TOKEN not set, skipping Bitwarden secrets")
            return {}

        logger.info("BWS_ACCESS_TOKEN found, attempting Bitwarden authentication")
        fetched_secrets = {}
        try:
            # Standard SDK Pattern
            client = BitwardenClient(
                settings=ClientSettings(
                    device_type=DeviceType.SDK, user_agent="OmegaKG/4.4.2"
                )
            )
            auth_result = client.auth().login_access_token(bws_token)
            logger.info(f"Bitwarden authentication successful: {auth_result}")

            # Map internal keys to Env Vars containing UUIDs
            secret_mappings = {
                "linear_webhook_secret": "LINEAR_WEBHOOK_SECRET_PRD_ID",
                "postgres_password": "POSTGRES_PASSWORD_PRD_ID",
                "neo4j_password": "NEO4J_PASSWORD_PRD_ID",
                "extension_api_key": "EXTENSION_API_KEY_PRD_ID",
                "linear_api_key": "LINEAR_API_KEY_PRD_ID",
                "perplexity_api_key": "PERPLEXITY_API_KEY_PRD_ID",
                "gemini_api_key": "GEMINI_API_KEY_PRD_ID",
                "nanogpt_api_key": "NANOGPT_OMEGAKG_API_KEY",
                "jwt_secret_key": "JWT_SECRET_KEY_ID",
                "ollama_okg_api_key": "OLLAMA_OKG_API_KEY_PRD_ID",
            }

            for config_key, env_var_id in secret_mappings.items():
                secret_uuid = os.getenv(env_var_id)
                if secret_uuid:
                    logger.debug(
                        f"Fetching secret {config_key} from UUID {secret_uuid}"
                    )
                    try:
                        response = client.secrets().get(uuid.UUID(secret_uuid))
                        # Bitwarden SDK uses response.data.value pattern
                        if hasattr(response, "data") and hasattr(
                            response.data, "value"
                        ):
                            fetched_secrets[config_key] = response.data.value
                            logger.debug(f"Successfully fetched {config_key}")
                        elif hasattr(response, "value"):
                            fetched_secrets[config_key] = response.value
                            logger.debug(
                                f"Successfully fetched {config_key} via response.value"
                            )
                        else:
                            logger.warning(
                                "Could not find 'value' attribute in response for '%s'. Response type: %s",
                                config_key,
                                type(response).__name__,
                            )
                    except Exception as e:
                        if "404" in str(e):
                            logger.warning(
                                "Secret not found in Bitwarden for key '%s' (UUID: %s) - will use fallback",
                                config_key,
                                secret_uuid,
                            )
                        else:
                            logger.warning(
                                "Failed to fetch secret for key '%s' from Bitwarden (UUID: %s): %s: %s",
                                config_key,
                                secret_uuid,
                                type(e).__name__,
                                e,
                            )
                else:
                    logger.debug(
                        f"Environment variable {env_var_id} not set for {config_key}"
                    )
        except Exception:
            logger.critical("Bitwarden SDK error", exc_info=True)
            return {}

        if fetched_secrets:
            logger.info(
                "Bitwarden secrets loaded for keys: %s",
                ", ".join(sorted(fetched_secrets.keys())),
            )

        return fetched_secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "Omega KG"
    VERSION: str = "4.4.2"

    # --- Server Settings ---
    app_env: str = Field("development", validation_alias="APP_ENV")
    app_host: str = Field("0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(8765, validation_alias="APP_PORT")

    # --- Ngrok / Tunneling ---
    enable_ngrok: bool = Field(False, validation_alias="ENABLE_NGROK")
    ngrok_api_key: Optional[str] = Field(None, validation_alias="NGROK_API_KEY")

    # --- Postgres Infrastructure (New) ---
    postgres_user: str = Field("omega_user", validation_alias="POSTGRES_USER")
    postgres_server: str = Field("127.0.0.1", validation_alias="POSTGRES_SERVER")
    postgres_port: int = Field(6000, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field("omegakg", validation_alias="POSTGRES_DB")
    postgres_password: str = Field(
        "omega_dev_password", validation_alias="POSTGRES_PASSWORD"
    )

    # --- Redis Infrastructure (For Production Rate Limiting) ---
    redis_url: Optional[str] = Field(
        None,
        validation_alias="REDIS_URL",
        description="Redis connection URL (e.g., redis://localhost:6379/0). If not set, uses in-memory rate limiting.",
    )
    neo4j_uri: str = Field("bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")
    neo4j_heap_size: str = Field("512M", validation_alias="NEO4J_HEAP_SIZE")
    neo4j_host_data_path: str = Field(
        "./data/neo4j", validation_alias="NEO4J_HOST_DATA_PATH"
    )

    # --- Security & Auth (Legacy Restored) ---
    jwt_secret_key: str = Field(
        "legacy_fallback_secret", validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(60, validation_alias="JWT_EXPIRATION_MINUTES")
    chrome_extension_id: Optional[str] = Field(
        None, validation_alias="CHROME_EXTENSION_ID"
    )
    extension_api_key: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("EXTENSION_API_KEY_PRD", "EXTENSION_API_KEY"),
    )

    # --- Validation API Authentication (TN-CORE-102) ---
    bws_access_token: Optional[str] = Field(
        None,
        validation_alias="BWS_ACCESS_TOKEN",
        description="Bitwarden Secrets Manager access token for service authentication",
    )
    static_service_token: Optional[str] = Field(
        None,
        validation_alias="STATIC_SERVICE_TOKEN",
        description="Static token for local development (fallback when BWS_ACCESS_TOKEN not available)",
    )

    # --- Email/SMTP (Legacy Restored) ---
    smtp_host: Optional[str] = Field(None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, validation_alias="SMTP_USER")
    smtp_password: Optional[str] = Field(None, validation_alias="SMTP_PASSWORD")
    email_to: Optional[str] = Field(None, validation_alias="EMAIL_TO")

    # --- Logic & Keywords (Legacy Restored) ---
    decision_keywords: str = Field(
        "decided to,chose to,agreed to", validation_alias="DECISION_KEYWORDS"
    )
    linear_status_map_json: str = Field(
        '{"draft": "c757066a-8d71-4612-be2b-b9cd6c7987c5", "ready": "b2a452c5-bec3-4ebc-a14a-b1d44d87b481", "active": "5c0c5400-2d67-4e64-b7ba-31019ab522f6", "completed": "2ab9b46e-21a3-47f4-8660-ab68093a99b4", "archived": "72d2560d-6de4-49f4-bde7-9a58e0849293"}',
        validation_alias="LINEAR_STATUS_MAP_JSON",
    )
    linear_user_map_json: str = Field("{}", validation_alias="LINEAR_USER_MAP_JSON")
    linear_label_map_json: str = Field(
        '{"bug": "c757066a-8d71-4612-be2b-b9cd6c7987c5", '
        '"feature": "b2a452c5-bec3-4ebc-a14a-b1d44d87b481", '
        '"improvement": "5c0c5400-2d67-4e64-b7ba-31019ab522f6", '
        '"documentation": "2ab9b46e-21a3-47f4-8660-ab68093a99b4", '
        '"question": "72d2560d-6de4-49f4-bde7-9a58e0849293"}',
        validation_alias="LINEAR_LABEL_MAP_JSON",
        description='JSON mapping of Linear label names to label IDs. Example: {"bug": "uuid", "feature": "uuid"}',
    )

    # --- Secrets & Keys ---
    linear_webhook_secret: str = Field(..., validation_alias="LINEAR_WEBHOOK_SECRET")

    # --- External Services ---
    linear_api_key: Optional[str] = Field(None, validation_alias="LINEAR_API_KEY")
    linear_team_id: Optional[str] = Field(None, validation_alias="LINEAR_TEAM_ID")
    linear_workspace_id: Optional[str] = Field(
        None, validation_alias="LINEAR_WORKSPACE_ID"
    )
    linear_project_id: Optional[str] = Field(None, validation_alias="LINEAR_PROJECT_ID")

    github_token: Optional[str] = Field(None, validation_alias="GITHUB_TOKEN")
    github_webhook_secret: Optional[str] = Field(
        None, validation_alias="GITHUB_WEBHOOK_SECRET"
    )
    linear_done_state_id: Optional[str] = Field(
        None, validation_alias="LINEAR_DONE_STATE_ID"
    )

    # --- AI Services ---
    nanogpt_api_key: Optional[str] = Field(
        None, validation_alias="NANOGPT_OMEGAKG_API_KEY"
    )
    openrouter_api_key: Optional[str] = Field(
        None, validation_alias="OPENROUTER_API_KEY"
    )
    perplexity_api_key: Optional[str] = Field(
        None, validation_alias="PERPLEXITY_API_KEY_PRD"
    )
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY_PRD")
    ollama_okg_api_key: Optional[str] = Field(
        None, validation_alias="OLLAMA_OKG_API_KEY_PRD_ID"
    )

    # --- Embedding Service Configuration (CRITICAL) ---
    embedding_provider: str = Field("ollama", validation_alias="EMBEDDING_PROVIDER")
    ollama_base_url: str = Field(
        "http://127.0.0.1:11434", validation_alias="OLLAMA_BASE_URL"
    )
    ollama_embedding_model: str = Field(
        "bge-m3:567m", validation_alias="OLLAMA_EMBEDDING_MODEL"
    )
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")

    # --- Hookdeck Configuration ---
    hookdeck_api_key: Optional[str] = Field(None, validation_alias="HOOKDECK_API_KEY")

    # --- Quipu Monitoring Configuration ---
    ollama_host_url: str = Field(
        "http://localhost:11434", validation_alias="OLLAMA_HOST_URL"
    )
    heartbeat_interval_sec: int = Field(60, validation_alias="HEARTBEAT_INTERVAL_SEC")
    quipu_service_name: str = Field(
        "ollama-server-01", validation_alias="QUIPU_SERVICE_NAME"
    )
    omega_pg_conn: Optional[str] = Field(None, validation_alias="OMEGA_PG_CONN")
    ingest_llm_url: str = Field(
        "http://localhost:8766", validation_alias="INGEST_LLM_URL"
    )

    # --- Percolation Engine Configuration ---
    percolation_similarity_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        validation_alias="PERCOLATION_SIMILARITY_THRESHOLD",
        description="Similarity threshold for creating relationships in the percolation engine (0.0-1.0)",
    )

    # --- Event Processor Configuration (TN-103) ---
    webhook_poll_interval: float = Field(
        5.0,
        ge=0.1,
        validation_alias="WEBHOOK_POLL_INTERVAL",
        description="Seconds between polling cycles for unprocessed webhook events (default: 5.0)",
    )
    webhook_batch_size: int = Field(
        10,
        ge=1,
        le=100,
        validation_alias="WEBHOOK_BATCH_SIZE",
        description="Number of events to fetch per batch (default: 10, max: 100)",
    )

    # --- Paths ---
    obsidian_vault_path: str = Field("./vault", validation_alias="OBSIDIAN_VAULT_PATH")
    ai_conversations_path: Optional[str] = Field(
        None, validation_alias="AI_CONVERSATIONS_PATH"
    )
    obsidian_vault_scan_folders: str = Field(
        "TN,TNP,Tasks,Workflow,Linear",
        validation_alias="OBSIDIAN_VAULT_SCAN_FOLDERS",
        description="Deprecated: Use OBSIDIAN_TASK_SCAN_FOLDERS or OBSIDIAN_SESSION_SCAN_FOLDERS",
    )
    obsidian_task_scan_folders: str = Field(
        "TN,TNP,Tasks,Workflow,Linear",
        validation_alias="OBSIDIAN_TASK_SCAN_FOLDERS",
        description="Comma-separated list of folder names to scan for Task Sync",
    )
    obsidian_session_scan_folders: str = Field(
        "Sessions",
        validation_alias="OBSIDIAN_SESSION_SCAN_FOLDERS",
        description="Comma-separated list of folder names to scan for Session Percolation",
    )

    # --- Terminal Capture Configuration ---
    terminal_noise_patterns: str = Field(
        r"^cd\s?,^ls,^dir,^cls,^clear,^echo\s?,^exit,^wsl,^powershell,^ipconfig,^whoami,^Get-Location,^Get-ChildItem",
        validation_alias="TERMINAL_NOISE_PATTERNS",
        description="Comma-separated list of regex patterns to ignore in terminal capture",
    )

    # --- Ingest Database Configuration ---
    ingest_postgres_user: Optional[str] = Field(
        None, validation_alias="INGEST_POSTGRES_USER"
    )
    ingest_postgres_password: Optional[str] = Field(
        None, validation_alias="INGEST_POSTGRES_PASSWORD"
    )
    ingest_postgres_server: Optional[str] = Field(
        None, validation_alias="INGEST_POSTGRES_SERVER"
    )
    ingest_postgres_port: Optional[int] = Field(
        None, validation_alias="INGEST_POSTGRES_PORT"
    )
    ingest_postgres_db: Optional[str] = Field(
        None, validation_alias="INGEST_POSTGRES_DB"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _enforce_zero_trust_in_stable(self) -> "Settings":
        omega_env = os.getenv("OMEGA_ENV", "dev").strip().lower()
        zero_trust_required = (
            os.getenv("ZERO_TRUST_REQUIRED", "true").strip().lower() == "true"
        )

        if not zero_trust_required:
            return self

        # Allow test runs to use local dummy values without Bitwarden.
        if self.app_env.strip().lower() == "test":
            return self

        if not os.getenv("BWS_ACCESS_TOKEN"):
            raise ValueError(
                "BWS_ACCESS_TOKEN is required to enforce zero_trust secret loading"
            )

        required_secret_id_envs = (
            "LINEAR_WEBHOOK_SECRET_PRD_ID",
            "POSTGRES_PASSWORD_PRD_ID",
            "NEO4J_PASSWORD_PRD_ID",
            "EXTENSION_API_KEY_PRD_ID",
            "JWT_SECRET_KEY_ID",
        )

        # In stable, treat missing secret IDs as a hard failure.
        if omega_env in {"stable", "prod", "production"}:
            missing = [k for k in required_secret_id_envs if not os.getenv(k)]
            if missing:
                raise ValueError(
                    "Missing required Bitwarden secret ID env vars for stable environment: "
                    + ", ".join(missing)
                )

        return self

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @property
    def sync_database_url(self) -> str:
        """Synchronous PostgreSQL connection string for psycopg2."""
        if self.omega_pg_conn:
            return self.omega_pg_conn
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @property
    def ingest_database_url(self) -> str:
        """Connection string for Ingest Database (fallback to main if not configured)."""
        user = self.ingest_postgres_user or self.postgres_user
        password = self.ingest_postgres_password or self.postgres_password
        server = self.ingest_postgres_server or self.postgres_server
        port = self.ingest_postgres_port or self.postgres_port
        db = self.ingest_postgres_db or self.postgres_db
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        *args: PydanticBaseSettingsSource,
        **kwargs: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            BitwardenSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            *args,
            *kwargs.values(),
        )


settings = Settings()  # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
