"""
Bitwarden Secrets Manager integration for ingest-llm service.

This module provides functionality to fetch secrets from Bitwarden
Secrets Manager and make them available as environment variables.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from bitwarden_sdk import BitwardenClient, BitwardenSettings

    BITWARDEN_SDK_AVAILABLE = True
except ImportError:
    BITWARDEN_SDK_AVAILABLE = False
    # Only log warning at debug level - Bitwarden is optional
    logger.debug("Bitwarden SDK not installed - Bitwarden integration disabled")


@dataclass
class SecretMapping:
    """Maps secret IDs to environment variable names."""

    secret_id: (
        str  # Bitwarden secret ID (e.g., from INGEST_LINEAR_WEBHOOK_SECRET_PRD_ID)
    )
    env_var: str  # Target environment variable name (e.g., LINEAR_WEBHOOK_SECRET)
    required: bool = True  # Whether failure to fetch should raise an error


class BitwardenSecretLoader:
    """
    Fetches secrets from Bitwarden Secrets Manager and sets environment variables.

    This loader supports a fallback mechanism:
    - If Bitwarden is configured (BWS_ACCESS_TOKEN set), fetch from Bitwarden
    - If Bitwarden fetch fails, fall back to existing environment variables
    - If neither is available, log warning for required secrets
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the Bitwarden secret loader.

        Args:
            access_token: Bitwarden Secrets Manager access token
        """
        self.access_token = (
            access_token
            or os.getenv("INGEST_BWS_ACCESS_TOKEN")
            or os.getenv("BWS_ACCESS_TOKEN")
        )
        self.client: Optional[BitwardenClient] = None
        self.enabled = BITWARDEN_SDK_AVAILABLE and bool(self.access_token)

        if self.enabled:
            try:
                settings = BitwardenSettings()
                self.client = BitwardenClient(settings)
                # Authenticate using access token
                self.client.authenticate_access_token(self.access_token)
                logger.info("Bitwarden Secrets Manager authentication successful")
            except Exception as e:
                logger.error(f"Failed to authenticate with Bitwarden: {e}")
                self.enabled = False

    def fetch_secret(self, secret_id: str) -> Optional[str]:
        """
        Fetch a secret value from Bitwarden by ID.

        Args:
            secret_id: Bitwarden secret ID (UUID)

        Returns:
            Secret value or None if fetch fails
        """
        if not self.enabled or not self.client:
            logger.debug("Bitwarden not enabled - skipping fetch")
            return None

        try:
            # Fetch secret from Bitwarden
            secret_response = self.client.secrets().get(secret_id)
            secret_value = secret_response.value
            logger.info(f"Successfully fetched secret: {secret_id[:8]}...")
            return secret_value
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_id[:8]}...: {e}")
            return None

    def load_all_secrets(self, mappings: List[SecretMapping]) -> Dict[str, str]:
        """
        Load all secrets based on provided mappings.

        For each mapping:
        1. Try to fetch from Bitwarden (if enabled)
        2. Fall back to existing environment variable
        3. Log warning if required secret is unavailable

        Args:
            mappings: List of SecretMapping objects

        Returns:
            Dictionary of environment variable names to values
        """
        loaded_secrets = {}

        for mapping in mappings:
            secret_value = None

            # Try Bitwarden first
            if self.enabled:
                secret_value = self.fetch_secret(mapping.secret_id)

            # Fall back to environment variable
            if secret_value is None:
                secret_value = os.getenv(mapping.env_var)
                if secret_value:
                    logger.debug(f"Using fallback env var for {mapping.env_var}")

            # Handle missing required secrets
            if secret_value is None and mapping.required:
                logger.error(f"Required secret not available: {mapping.env_var}")

            loaded_secrets[mapping.env_var] = secret_value

        return loaded_secrets

    def set_env_vars(self, secrets: Dict[str, str]) -> None:
        """
        Set environment variables from loaded secrets.

        Args:
            secrets: Dictionary of env var names to values
        """
        for env_var, value in secrets.items():
            if value:
                os.environ[env_var] = value
                logger.debug(f"Set environment variable: {env_var}")

    def load_and_set_secrets(self, mappings: List[SecretMapping]) -> None:
        """
        Convenience method to load secrets and set environment variables.

        Args:
            mappings: List of SecretMapping objects
        """
        secrets = self.load_all_secrets(mappings)
        self.set_env_vars(secrets)


def create_secret_mappings_from_env() -> List[SecretMapping]:
    """
    Create secret mappings from environment variables following naming convention.

    Looks for environment variables with _PRD_ID suffix (e.g., INGEST_LINEAR_WEBHOOK_SECRET_PRD_ID)
    and creates corresponding mappings to target variables (e.g., LINEAR_WEBHOOK_SECRET).

    Returns:
        List of SecretMapping objects
    """
    mappings = []

    # Define mappings manually for clarity
    mapping_definitions = [
        # Bitwarden Secret ID env var -> Target env var -> Required
        ("INGEST_LINEAR_WEBHOOK_SECRET_PRD_ID", "LINEAR_WEBHOOK_SECRET", True),
        ("INGEST_POSTGRES_PASSWORD_PRD_ID", "POSTGRES_PASSWORD", False),
        ("INGEST_LINEAR_API_KEY_PRD_ID", "LINEAR_API_KEY", False),
    ]

    for secret_id_var, target_var, required in mapping_definitions:
        secret_id = os.getenv(secret_id_var)
        if secret_id:
            mappings.append(
                SecretMapping(
                    secret_id=secret_id, env_var=target_var, required=required
                )
            )
            logger.info(f"Created mapping: {secret_id_var} -> {target_var}")

    return mappings


def load_bitwarden_secrets() -> None:
    """
    Load secrets from Bitwarden and set environment variables.

    This function should be called during application startup (after load_dotenv()).
    It will:
    1. Check if Bitwarden is configured (INGEST_BWS_ACCESS_TOKEN or BWS_ACCESS_TOKEN)
    2. Fetch secrets from Bitwarden using secret IDs from environment
    3. Set environment variables with fetched secret values
    4. Fall back to existing environment variables if Bitwarden fails

    Example usage in main.py:

        from dotenv import load_dotenv
        from ingest_llm_as.core.bitwarden_loader import load_bitwarden_secrets

        load_dotenv()  # Load .env file first
        load_bitwarden_secrets()  # Then fetch from Bitwarden
    """
    access_token = os.getenv("INGEST_BWS_ACCESS_TOKEN") or os.getenv("BWS_ACCESS_TOKEN")

    if not access_token:
        logger.info(
            "No Bitwarden access token found - skipping Bitwarden secret loading"
        )
        return

    logger.info("Bitwarden access token found - initializing secret loader")

    loader = BitwardenSecretLoader(access_token)

    if not loader.enabled:
        logger.warning(
            "Bitwarden loader not enabled - using environment variables only"
        )
        return

    # Create secret mappings from environment
    mappings = create_secret_mappings_from_env()

    if not mappings:
        logger.warning(
            "No secret mappings found - create INGEST_*_PRD_ID variables for Bitwarden secrets"
        )
        return

    # Load and set secrets
    loader.load_and_set_secrets(mappings)
    logger.info(f"Bitwarden secret loading completed for {len(mappings)} secret(s)")
