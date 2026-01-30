# Brain: OmegaKG (Persistence)

## Overview
OmegaKG is the reasoning and persistence layer of the Soma organism. It consumes knowledge digests from the nervous system (Redis) and MERGEs them into the long-term Brain (Neo4j) as AtomicFacts with vector embeddings.

## Role in Soma
- **Function**: signal_persistence
- **Input**: Redis Stream `soma_working_memory`
- **Output**: Neo4j Graph (`AtomicFact` nodes)
- **Vector Space**: Qwen3-Embedding (768-dim)

## Operational Control
- **Executive**: Managed via [orchestrator.py](../orchestrator.py).
- **Verification**: Verifiable via `verify-meal-trace.py`.

## Documentation
- [Soma Root AGENTS.md](../AGENTS.md)
- [Soma Root README.md](../README.md)
- [Brain Architecture Docs](../OmegaVault/ApexSigma/Development/Projects/Soma/Architecture/)
