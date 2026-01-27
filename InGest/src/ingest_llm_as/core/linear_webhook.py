"""
Linear Webhook Signature Verification

Validates Linear webhook payloads using HMAC-SHA256 signatures.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
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
    Verify Linear webhook signature using HMAC-SHA256.

    Computes HMAC-SHA256 hash of payload using shared secret and
    compares with provided signature. Linear sends signature in
    'Linear-Signature' header.

    Args:
        payload: Raw request body bytes
        signature: Signature from 'Linear-Signature' header
        secret: Shared secret for webhook verification

    Returns:
        bool: True if signature is valid, False otherwise

    Raises:
        ValueError: If signature format is invalid
    """
    if not signature:
        logger.warning("Missing Linear-Signature header")
        return False

    if not secret:
        logger.error("LINEAR_WEBHOOK_SECRET not configured")
        return False

    try:
        # Linear signature format: raw hex digest OR sha256=<hex_digest> (legacy compatibility)
        if signature.startswith("sha256="):
            expected_signature = signature[7:]  # Remove 'sha256=' prefix
        else:
            # Linear sends raw hex digest (64 characters for SHA256)
            expected_signature = signature

        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(computed_hash, expected_signature)

        if is_valid:
            logger.info("Webhook signature verified successfully")
        else:
            # Enhanced debugging - show full details
            logger.warning(
                "Webhook signature verification failed",
                extra={
                    "received_signature": signature,
                    "expected_signature": expected_signature,
                    "computed_hash": computed_hash,
                    "secret_length": len(secret),
                    "payload_length": len(payload),
                    "payload_preview": payload[:100].decode("utf-8", errors="ignore"),
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
    Retrieve Linear webhook secret from environment.

    Returns:
        Optional[str]: Secret value or None if not configured
    """
    from ..config import get_settings

    settings = get_settings()
    secret = settings.linear_webhook_secret
    if not secret:
        # Fallback to os.getenv just in case
        secret = os.getenv("LINEAR_WEBHOOK_SECRET")

    if not secret:
        logger.warning("LINEAR_WEBHOOK_SECRET environment variable not set")
    return secret
