"""
Startup validation module for InGest-LLM.as.

This module provides functions to validate application configuration at startup,
checking for plain-text secrets when Bitwarden mode is enabled.
"""

import logging
from typing import List

from ingest_llm_as.config import get_settings
from ingest_llm_as.security.validator import (
    validate_no_plain_text_secrets,
    is_bitwarden_enabled,
)

logger = logging.getLogger(__name__)


class SecurityValidationError(Exception):
    """Raised when security validation fails."""

    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(
            f"Security validation failed with {len(violations)} violation(s)"
        )


def validate_startup_config() -> None:
    """
    Validate application configuration at startup.

    Checks for plain-text secrets when Bitwarden mode is enabled.
    Raises SecurityValidationError in production mode, logs warnings in development.

    Raises:
        SecurityValidationError: If validation fails in production mode
    """
    settings = get_settings()

    # Check if Bitwarden mode is enabled
    if is_bitwarden_enabled(settings.bws_access_token):
        logger.info("Bitwarden mode enabled - validating for plain-text secrets")

        # Validate for plain-text secrets
        violations = validate_no_plain_text_secrets(
            zero_trust_required=settings.zero_trust_required,
            bws_access_token=settings.bws_access_token,
        )

        if violations:
            # Determine behavior based on environment
            app_env = settings.app_env.lower() if settings.app_env else "development"

            if app_env == "production":
                # Production: Raise exception to block startup
                error_msg = (
                    f"SECURITY ERROR: Plain-text secrets detected in production mode.\n"
                    f"Violations:\n"
                    f"{chr(10).join(f'  - {v}' for v in violations)}\n"
                    f"Action: Remove plain-text secrets and use Bitwarden Secrets Manager.\n"
                    f"Documentation: See docs/security/secrets-management.md"
                )
                logger.error(error_msg)
                raise SecurityValidationError(violations)

            elif app_env == "staging":
                # Staging: Log warning but allow startup
                warning_msg = (
                    f"SECURITY WARNING: Plain-text secrets detected in staging mode.\n"
                    f"Violations:\n"
                    f"{chr(10).join(f'  - {v}' for v in violations)}\n"
                    f"Recommendation: Use Bitwarden Secrets Manager for production."
                )
                logger.warning(warning_msg)

            else:
                # Development: Log warning but allow startup
                warning_msg = (
                    f"SECURITY WARNING: Plain-text secrets detected in development mode.\n"
                    f"Violations:\n"
                    f"{chr(10).join(f'  - {v}' for v in violations)}\n"
                    f"This is acceptable for development but not for production."
                )
                logger.warning(warning_msg)

        else:
            logger.info("Bitwarden mode not enabled - skipping secret validation")

    else:
        logger.info("Bitwarden access token not set - skipping secret validation")


def get_validation_summary() -> dict:
    """
    Get a summary of validation status for health checks.

    Returns:
        dict: Validation status summary
    """
    settings = get_settings()

    return {
        "bitwarden_enabled": is_bitwarden_enabled(settings.bws_access_token),
        "zero_trust_required": settings.zero_trust_required,
        "validation_performed": is_bitwarden_enabled(settings.bws_access_token),
    }
