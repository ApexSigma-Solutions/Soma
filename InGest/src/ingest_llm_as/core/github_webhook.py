"""
GitHub Webhook Signature Verification

Validates GitHub webhook payloads using HMAC-SHA256 signatures.
Phase: TN-GITHUB-01 - Webhook Ingestion Pipeline
"""

import hashlib
import hmac
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256.

    Computes HMAC-SHA256 hash of payload using shared secret and
    compares with provided signature. GitHub sends signature in
    'X-Hub-Signature-256' header.

    Args:
        payload: Raw request body bytes
        signature: Signature from 'X-Hub-Signature-256' header
        secret: Shared secret for webhook verification

    Returns:
        bool: True if signature is valid, False otherwise

    Raises:
        ValueError: If signature format is invalid
    """
    if not signature:
        logger.warning("Missing X-Hub-Signature-256 header")
        return False

    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        return False

    try:
        # GitHub signature format: sha256=<hex_digest>
        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format (must start with sha256=)")
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix

        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(computed_hash, expected_signature)

        if is_valid:
            logger.info("GitHub webhook signature verified successfully")
        else:
            logger.warning(
                "GitHub webhook signature verification failed",
                extra={
                    "received_signature": signature,
                    "expected_signature": expected_signature,
                    "computed_hash": computed_hash,
                },
            )

        return is_valid

    except Exception as e:
        logger.error(
            "Error verifying webhook signature",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        return False


def get_webhook_secret() -> Optional[str]:
    """
    Retrieve GitHub webhook secret from environment.

    Returns:
        Optional[str]: Secret value or None if not configured
    """
    from ..config import get_settings

    settings = get_settings()
    secret = settings.github_webhook_secret
    if not secret:
        # Fallback to os.getenv just in case, or for legacy support
        secret = os.getenv("GITHUB_WEBHOOK_SECRET")

    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET environment variable not set")
    return secret
