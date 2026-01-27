"""
Omega Ingest Contract Definition.

This module loads and provides access to the Omega ingest contract,
which defines the schema for data ingestion from raw webhook events
to structured graph events.
"""

import json
from pathlib import Path
from typing import Any, Dict

# Path to the contract JSON file
CONTRACT_PATH = Path(__file__).parent / "omega_ingest_contract.json"


def _load_contract() -> Dict[str, Any]:
    """Load the contract JSON from file."""
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found: {CONTRACT_PATH}")

    with open(CONTRACT_PATH) as f:
        return json.load(f)


# Load contract at module import time
OMEGA_INGEST_CONTRACT = _load_contract()
CONTRACT_VERSION = OMEGA_INGEST_CONTRACT.get("contract_version", "unknown")


def validate_contract() -> bool:
    """
    Validate the contract structure.

    Returns:
        True if contract has required fields, False otherwise.
    """
    required_keys = {
        "contract_version",
        "input_schema",
        "output_schema",
        "failure_handling",
    }
    return required_keys.issubset(OMEGA_INGEST_CONTRACT.keys())


def get_input_schema() -> Dict[str, Any]:
    """Get the input schema from the contract."""
    return OMEGA_INGEST_CONTRACT.get("input_schema", {})


def get_output_schema() -> Dict[str, Any]:
    """Get the output schema from the contract."""
    return OMEGA_INGEST_CONTRACT.get("output_schema", {})


def get_failure_handling() -> Dict[str, Any]:
    """Get the failure handling configuration from the contract."""
    return OMEGA_INGEST_CONTRACT.get("failure_handling", {})
