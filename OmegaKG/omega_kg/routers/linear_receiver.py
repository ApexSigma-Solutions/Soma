import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from omega_kg.database.session import get_db
from omega_kg.settings import settings
from omega_kg.models.webhook import RawWebhookEvent

# Setup Logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_signature(request: Request):
    # Check for standard and alternate headers
    signature = request.headers.get("Linear-Signature") or request.headers.get(
        "X-Linear-Signature"
    )

    if not signature:
        logger.warning(f"Missing Linear-Signature. Headers: {request.headers.keys()}")
        raise HTTPException(status_code=400, detail="Missing Linear-Signature header")

    body_bytes = await request.body()

    expected_signature = hmac.new(
        settings.linear_webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    return body_bytes, signature


@router.post("/linear", status_code=200)
async def receive_linear_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    verification: tuple = Depends(verify_signature),
):
    """
    Dumb and fast webhook endpoint.

    Workflow:
    1. Verify signature (via dependency)
    2. Parse JSON payload
    3. Persist raw payload to RawWebhookEvent
    4. Return 200 OK immediately

    No business logic in hot path - processing happens in background.
    """
    payload_bytes, signature = verification

    # Parse JSON payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse Linear webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Create RawWebhookEvent (dumb and fast)
    db_event = RawWebhookEvent(
        source="linear",
        headers=dict(request.headers),
        payload=payload_bytes,  # Store raw bytes for byte-for-byte comparison
        processed_status=False,
    )

    db.add(db_event)
    await db.commit()

    # Log event ID for debugging
    logger.info(f"Received Linear webhook event ID: {db_event.id}")

    return {"status": "persisted", "id": db_event.id}
