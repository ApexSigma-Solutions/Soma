import re
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.ingest_session import get_ingest_db, ingest_engine
from omega_kg.models.terminal import (
    TerminalCommandData,
    TerminalCaptureResponse,
    TerminalEvent,
    Base,
)
from omega_kg.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture/terminal", tags=["terminal"])

# Compile noise patterns once
NOISE_REGEX = []
if settings.terminal_noise_patterns:
    patterns = [p.strip() for p in settings.terminal_noise_patterns.split(",")]
    for p in patterns:
        try:
            NOISE_REGEX.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            logger.error(
                f"Invalid regex pattern in TERMINAL_NOISE_PATTERNS: '{p}' - {e}"
            )


async def ensure_terminal_table_exists():
    """Ensure the terminal_events table exists in the Ingest DB."""
    async with ingest_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@router.on_event("startup")
async def startup_event():
    try:
        await ensure_terminal_table_exists()
    except Exception as e:
        logger.warning(
            f"Failed to ensure terminal table exists on startup: {e}. Terminal capture may fail."
        )


def is_noise(command: str) -> bool:
    """Check if the command matches any noise patterns."""
    return any(pattern.search(command) for pattern in NOISE_REGEX)


@router.post("/", response_model=TerminalCaptureResponse)
async def capture_terminal_command(
    data: TerminalCommandData,
    db: AsyncSession = Depends(get_ingest_db),
):
    """
    Receive a terminal command, filter noise, and store raw event.
    Processing happens asynchronously via InGest Dagster Pipeline (terminal_processor).
    """
    if is_noise(data.command):
        # Log strictly as debug/trace to avoid clutter
        # logic: we return success but don't store it
        # strictly speaking we return a dummy ID or None?
        # For client compatibility, let's return a success response with a generic ID or skip persistence.
        # But wait, if we don't persist, we can't return a valid UUID that exists.
        # We'll just generate a UUID and claim it's processed.
        from uuid import uuid4

        return TerminalCaptureResponse(
            status="ignored", event_id=uuid4(), processed=True
        )

    # Persistence
    new_event = TerminalEvent(
        command=data.command,
        cwd=data.cwd,
        captured_at=data.timestamp,
        exit_code=data.exit_code,
        output=data.output,
        user=data.user,
        host=data.host,
        session_id=data.session_id,
        raw_payload=data.model_dump(mode="json"),
        processed=False,  # InGest Worker will pick this up
    )

    try:
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
    except Exception as e:
        logger.error(f"Error capturing terminal command: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )

    # Background processing now handled by InGest (Dagster) polling
    # background_tasks.add_task(process_terminal_event_background, new_event.event_id)

    return TerminalCaptureResponse(
        status="captured", event_id=new_event.event_id, processed=False
    )
