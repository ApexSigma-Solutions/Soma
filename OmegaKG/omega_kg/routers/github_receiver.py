"""
GitHub Webhook Receiver

Receives GitHub webhook events (PR merges, pushes, etc.) and persists them
to the database for background processing. Follows the same pattern as
linear_receiver.py for consistency.

 TN-103: The Refinery - Webhook Reception Layer
"""

import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.session import get_db
from omega_kg.models.webhook import RawWebhookEvent
from omega_kg.settings import settings

# Setup Logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_github_signature(request: Request) -> bytes:
    """
    Verify GitHub webhook signature (X-Hub-Signature-256).

    For local development with Hookdeck CLI, signature verification is skipped
    when the request comes from localhost (127.0.0.1), since Hookdeck validates
    the original signature but doesn't forward the X-Hub-Signature-256 header.

    Args:
        request: FastAPI request object

    Returns:
        Raw request body bytes

    Raises:
        HTTPException: If signature is missing or invalid (and not from localhost)
    """
    signature = request.headers.get("X-Hub-Signature-256")
    client_host = request.client.host if request.client else "unknown"

    # DIAGNOSTIC: Log the client host for debugging
    logger.info(
        f"[HOOKDECK_DEBUG] Client host: {client_host}, Signature present: {bool(signature)}"
    )

    # Skip signature verification for localhost (Hookdeck CLI local development)
    # Check multiple variations of localhost
    is_localhost = (
        client_host in ("127.0.0.1", "::1", "localhost")
        or client_host.startswith("127.0.0.")
        or client_host.startswith("192.168.")  # local network
        or client_host == "::ffff:127.0.0.1"  # IPv4-mapped IPv6
    )

    if is_localhost:
        logger.info(
            f"[HOOKDECK_DEBUG] Skipping signature verification for local request "
            f"(client={client_host}, Hookdeck CLI mode)"
        )
        return await request.body()

    if not signature:
        logger.warning(
            f"Missing X-Hub-Signature-256 header. Available headers: {list(request.headers.keys())}"
        )
        raise HTTPException(
            status_code=400, detail="Missing X-Hub-Signature-256 header"
        )

    body_bytes = await request.body()

    # DIAGNOSTIC: Check if webhook secret is configured
    if not settings.github_webhook_secret:
        logger.error(
            "[HOOKDECK_DEBUG] GITHUB_WEBHOOK_SECRET is not set! "
            "Webhook signature verification will fail."
        )

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    expected_header = f"sha256={expected_signature}"

    # DIAGNOSTIC: Log signature details (without exposing secret)
    logger.info(
        f"[HOOKDECK_DEBUG] Signature verification - "
        f"Received: {signature[:20]}... | Expected: {expected_header[:20]}..."
    )

    if not hmac.compare_digest(signature, expected_header):
        logger.warning("GitHub webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body_bytes


@router.post("/github", status_code=200)
async def receive_github_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    verification: bytes = Depends(verify_github_signature),
) -> dict:
    """
    Dumb and fast GitHub webhook endpoint.

    This endpoint follows the exact pattern from linear_receiver.py:
    1. Verify signature (via dependency injection)
    2. Persist raw payload to RawWebhookEvent table
    3. Return 200 OK immediately with event ID

    No business logic in hot path - all processing happens in background
    via EventProcessor.

    Args:
        request: FastAPI request object
        db: Database session
        verification: Verified request body bytes

    Returns:
        Dict with event status and ID
    """
    # DIAGNOSTIC: Log incoming request details
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"[HOOKDECK_DEBUG] Incoming GitHub webhook from {client_ip} - "
        f"Headers: {list(request.headers.keys())[:5]}... "
        f"Content-Type: {request.headers.get('content-type', 'missing')}"
    )
    # Parse JSON payload
    import json

    try:
        payload = json.loads(verification.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse GitHub webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Create RawWebhookEvent (dumb and fast)
    db_event = RawWebhookEvent(
        source="github",
        headers=dict(request.headers),
        payload=payload,
        processed_status=False,
    )

    db.add(db_event)
    await db.commit()

    # Log event ID for debugging
    logger.info(f"Received GitHub webhook event ID: {db_event.id}")

    return {"status": "persisted", "id": db_event.id}
