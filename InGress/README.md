# Senses: InGress

## Overview
InGress is the sensory layer of the Soma organism. It provides a thin FastAPI interface to receive external signals (JSON/Text) and store them in the `raw_lake` (PostgreSQL) for later metabolism.

## Role in Soma
- **Function**: signal_capture
- **Port**: 8000
- **Storage**: `soma_sensory_lake.records`
- **Next Stage**: [InGest](../InGest/README.md)

## Key Endpoints
- `POST /ingest`: Receive and store raw signals.
- `GET /health`: Sensory health status.

## Documentation
See the central Soma documentation for detailed architecture:
- [Soma Root AGENTS.md](../AGENTS.md)
- [Soma Root README.md](../README.md)
