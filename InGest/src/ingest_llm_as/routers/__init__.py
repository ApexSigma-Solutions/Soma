"""
Routers package for InGest-LLM.as service.

Contains API routers for various endpoints including webhook forwarding.
"""

from .eod_logs import router as eod_logs_router
from .webhook_forwarder import router as webhook_forwarder_router

__all__ = ["eod_logs_router", "webhook_forwarder_router"]
