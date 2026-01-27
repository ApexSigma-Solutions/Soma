#!/bin/bash
# Source this file to load OmegaKG environment
# Usage: source ./source_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.omega_env"

if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "Error: .omega_env not found at $ENV_FILE"
    return 1
fi
