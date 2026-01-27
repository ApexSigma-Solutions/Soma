"""
Vitals Stream Endpoint - Server-Sent Events for Real-Time System Health.

Part of Phase 3.5 Nervous System - System Symbiosis.
Streams live CPU/RAM telemetry to CortexBridge via SSE.
"""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette import EventSourceResponse

from src.shared.system_health import SystemHealth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vitals", tags=["Vitals"])


import json


async def vitals_event_generator() -> AsyncGenerator[dict, None]:
    """
    Infinite generator that yields system vitals every second.

    Yields:
        dict: ServerSentEvent compatible dict with 'data' payload
    """
    while True:
        try:
            vitals = SystemHealth.check_vitals()
            yield {"data": json.dumps(vitals)}
        except Exception as e:
            logger.error(f"Error collecting vitals: {e}")
            yield {
                "data": json.dumps(
                    {"error": str(e), "cpu_percent": 0, "ram_percent": 0}
                )
            }
        await asyncio.sleep(1)


@router.get("/stream")
async def stream_vitals() -> EventSourceResponse:
    """
    SSE endpoint for streaming live system vitals.

    Connect to: http://localhost:8000/vitals/stream

    Returns:
        EventSourceResponse: Streaming JSON data with cpu_percent, ram_percent, etc.

    Example Client Usage:
        ```typescript
        const eventSource = new EventSource('http://localhost:8000/vitals/stream');
        eventSource.onmessage = (event) => {
            const vitals = JSON.parse(event.data);
            console.log(`CPU: ${vitals.cpu_percent}%, RAM: ${vitals.ram_percent}%`);
        };
        ```
    """
    return EventSourceResponse(vitals_event_generator())
