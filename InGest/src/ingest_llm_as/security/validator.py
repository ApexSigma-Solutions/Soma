"""
Secrets validation module for InGest-LLM.as.

This module provides functions to validate that no plain-text secrets
are present when Bitwarden mode is enabled.
"""

import os
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# Regex patterns for common secret formats
SECRET_PATTERNS = {
    "api_key": re.compile(
        r"^(api[_-]?key|apikey)[\s=:]+[\"']?[a-zA-Z0-9]{20,}[\"']?", re.IGNORECASE
    ),
    "password": re.compile(
        r"^(password|passwd|pwd)[\s=:]+[\"']?[^\s\"']{8,}[\"']?", re.IGNORECASE
    ),
    "secret": re.compile(
        r"^(secret|token|jwt)[\s=:]+[\"']?[^\s\"']{10,}[\"']?", re.IGNORECASE
    ),
    "aws_key": re.compile(r"^AKIA[0-9A-Z]{16}", re.IGNORECASE),
    "github_token": re.compile(r"^gh[pousr]_[a-zA-Z0-9]{36}", re.IGNORECASE),
    "private_key": re.compile(r"-----BEGIN[^\n]+PRIVATE KEY-----", re.IGNORECASE),
    "database_url": re.compile(r"^[a-z]+://[^\s:]+:[^\s@]+[^\s/]+", re.IGNORECASE),
}


def is_secret_variable(var_name: str) -> bool:
    """
    Check if an environment variable name suggests it contains a secret.

    Args:
        var_name: Environment variable name

    Returns:
        bool: True if variable likely contains a secret
    """
    secret_keywords = [
        "secret",
        "password",
        "token",
        "key",
        "api_key",
        "api_key",
        "jwt",
        "private",
        "credential",
        "auth",
    ]
    var_lower = var_name.lower()
    return any(keyword in var_lower for keyword in secret_keywords)


def has_plain_text_secret(value: str) -> bool:
    """
    Check if a value looks like a plain-text secret.

    Args:
        value: Environment variable value to check

    Returns:
        bool: True if value appears to be a plain-text secret
    """
    if not value or value in ["", "none", "null", "false"]:
        return False

    # Check against known secret patterns
    for pattern_name, pattern in SECRET_PATTERNS.items():
        if pattern.search(value):
            logger.debug(f"Secret pattern matched: {pattern_name}")
            return True

    # Check for common secret indicators
    value_lower = value.lower()
    secret_indicators = [
        "sk-or-v1-",  # OpenRouter
        "pk_",  # Private keys
        "api_key=",  # API keys
        "password=",  # Passwords
        "secret=",  # Secrets
        "token=",  # Tokens
        "jwt=",  # JWT tokens
    ]

    for indicator in secret_indicators:
        if indicator in value_lower:
            logger.debug(f"Secret indicator found: {indicator}")
            return True

    return False


def get_secret_patterns() -> dict:
    """
    Get all secret patterns for documentation purposes.

    Returns:
        dict: Dictionary of pattern names and their regex patterns
    """
    return {name: pattern.pattern for name, pattern in SECRET_PATTERNS.items()}


def validate_no_plain_text_secrets(
    zero_trust_required: bool,
    bws_access_token: Optional[str] = None,
) -> List[str]:
    """
    Validate that no plain-text secrets are present when Bitwarden mode is enabled.

    Args:
        zero_trust_required: Whether zero-trust mode is required
        bws_access_token: Bitwarden access token (if set, Bitwarden is enabled)

    Returns:
        List[str]: List of validation violations (empty if none)
    """
    violations = []

    # If Bitwarden is enabled, check for plain-text secrets
    if zero_trust_required and bws_access_token:
        logger.info("Bitwarden mode enabled - validating for plain-text secrets")

        for var_name, var_value in os.environ.items():
            # Skip Bitwarden configuration variables
            if var_name in ["BWS_ACCESS_TOKEN", "ZERO_TRUST_REQUIRED"]:
                continue

            # Check if this is a secret variable
            if is_secret_variable(var_name):
                # Check if value looks like a plain-text secret
                if has_plain_text_secret(var_value):
                    violations.append(
                        f"Plain-text secret found in environment variable: {var_name}"
                    )
                    logger.warning(f"Security violation: {var_name}")

    return violations


def is_bitwarden_enabled(bws_access_token: Optional[str]) -> bool:
    """
    Check if Bitwarden Secrets Manager is enabled.

    Args:
        bws_access_token: Bitwarden access token from environment

    Returns:
        bool: True if Bitwarden is configured and enabled
    """
    return bool(bws_access_token and bws_access_token.strip())
