"""
API module for InGest-LLM.as endpoints.
"""

from ingest_llm_as.api.omega_ingest import router as omega_router
from ingest_llm_as.api.graph_parser import router as graph_router

__all__ = ["omega_router", "graph_router"]
