"""
Omega Ingest Contract Validators.

This module contains the contract definition for the Omega ingestion pipeline,
which defines the interface between raw webhook events (Postgres) and
structured events (Neo4j).
"""

from .omega_ingest_contract import (
    OMEGA_INGEST_CONTRACT,
    CONTRACT_VERSION,
    validate_contract,
)

__all__ = [
    "OMEGA_INGEST_CONTRACT",
    "CONTRACT_VERSION",
    "validate_contract",
]
