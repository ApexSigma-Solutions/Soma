"""
Configuration management API for OmegaKG.
ApexSigma Naming: snake_case for Python modules/functions.

Provides runtime configuration endpoints with hot-reload capability.
Complies with Mirmir EVT-50N42: No Neo4j reconnection on config updates.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
import structlog

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from omega_kg.settings import Settings, get_settings

logger = structlog.get_logger()

router = APIRouter(prefix="/config", tags=["configuration"])

# Global runtime config (hot-reloadable)
_runtime_config: Dict[str, Any] = {}


class ConfigUpdateRequest(BaseModel):
    """Runtime config update payload (biological terminology)"""

    entropy_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Metabolic Gate threshold (0.0-1.0)",
    )
    embedding_model: Optional[str] = Field(
        None,
        description="Neural Density encoding model",
    )
    percolation_similarity_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Synaptic consolidation threshold",
    )

    @field_validator("embedding_model")
    def validate_embedding_model(cls, v):
        """Validate supported embedding models"""
        if v is None:
            return v
        allowed = [
            "qwen3-embedding:0.6B-F16",
            "bge-m3:567m",
            "nomic-embed-text-v1.5",
        ]
        if v not in allowed:
            raise ValueError(f"Model must be one of: {allowed}")
        return v


@router.get("/")
async def get_runtime_config(settings: Settings = Depends(get_settings)):
    """
    GET current runtime configuration.

    MAR Compliance: Read-only, no forensic logging needed.

    Returns:
        Current configuration with biological terminology mappings.
    """
    # Initialize runtime config from settings if not already set
    global _runtime_config
    if not _runtime_config:
        _runtime_config = {
            "entropy_threshold": settings.entropy_threshold,
            "embedding_model": settings.ollama_embedding_model,
            "percolation_similarity_threshold": settings.percolation_similarity_threshold,
        }

    return {
        "entropy_threshold": _runtime_config.get(
            "entropy_threshold", settings.entropy_threshold
        ),
        "embedding_model": _runtime_config.get(
            "embedding_model", settings.ollama_embedding_model
        ),
        "percolation_similarity_threshold": _runtime_config.get(
            "percolation_similarity_threshold",
            settings.percolation_similarity_threshold,
        ),
        "metadata": {
            "biological_names": {
                "entropy_threshold": "Metabolic Gate",
                "embedding_model": "Neural Density Model",
                "percolation_similarity_threshold": "Synaptic Consolidation",
            },
            "description": "Runtime configuration for OmegaKG. These values can be updated without service restart.",
        },
    }


@router.post("/")
async def update_runtime_config(
    request: ConfigUpdateRequest, settings: Settings = Depends(get_settings)
):
    """
    POST configuration updates (hot-reload, no restart).

    Mirmir EVT-50N42 Compliance:
    - Only runtime settings updated
    - NO Neo4j reconnection triggered

    MAR Compliance:
    - All changes logged via structlog
    - Returns evidence of successful update

    Args:
        request: Configuration update payload

    Returns:
        Updated configuration with confirmation
    """
    global _runtime_config

    # Filter out None values
    changes = {k: v for k, v in request.dict().items() if v is not None}

    if not changes:
        raise HTTPException(status_code=400, detail="No configuration changes provided")

    # Initialize runtime config if not already set
    if not _runtime_config:
        _runtime_config = {
            "entropy_threshold": settings.entropy_threshold,
            "embedding_model": settings.ollama_embedding_model,
            "percolation_similarity_threshold": settings.percolation_similarity_threshold,
        }

    # Forensic logging (MAR requirement)
    logger.info(
        "Config update request",
        extra={
            "event": "config.update",
            "changes": changes,
            "previous_state": _runtime_config.copy(),
            "timestamp": datetime.now().isoformat(),
        },
    )

    # Apply changes to runtime config
    _runtime_config.update(changes)

    # For runtime values, we update the global dict
    # For environment-based values, they would require restart (not implemented here)

    # Forensic confirmation (MAR requirement)
    logger.info(
        "Config update applied",
        extra={
            "event": "config.update.success",
            "new_state": _runtime_config.copy(),
            "timestamp": datetime.now().isoformat(),
        },
    )

    return {
        "status": "success",
        "updated_config": {
            "entropy_threshold": _runtime_config.get(
                "entropy_threshold", settings.entropy_threshold
            ),
            "embedding_model": _runtime_config.get(
                "embedding_model", settings.ollama_embedding_model
            ),
            "percolation_similarity_threshold": _runtime_config.get(
                "percolation_similarity_threshold",
                settings.percolation_similarity_threshold,
            ),
        },
        "message": "Configuration updated without service restart",
        "note": "Runtime values updated immediately. Environment-based values require restart.",
    }


@router.get("/all")
async def get_all_settings(settings: Settings = Depends(get_settings)):
    """
    GET all settings (read-only, includes connection settings).

    WARNING: This endpoint returns sensitive information.
    Only use in development/debugging.
    """
    # Return non-sensitive settings only
    return {
        "app": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.app_env,
        },
        "neo4j": {
            "uri": settings.neo4j_uri,
            "user": settings.neo4j_user,
            # NOTE: Password intentionally excluded
        },
        "postgres": {
            "server": settings.postgres_server,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
        },
        "runtime": await get_runtime_config(settings),
    }
