# Stomach: InGest (Metabolism)

## Overview
InGest is the metabolic engine of the Soma organism. It implements **SimpleMem Stage 1**, digesting raw sensory signals from the lake into synthesized Atomic Facts.

## Role in Soma
- **Function**: signal_metabolism
- **Input**: PostgreSQL `raw_lake`
- **Pipeline**:
  1. **Entropy Gate**: Filters low-information noise.
  2. **Coreference Resolution**: Resolves pronouns and references (via spaCy/coreferee).
  3. **Temporal Anchoring**: Anchors relative time to absolute UTC (via dateparser).
- **Output**: Redis Stream `soma_working_memory` (Knowledge Digests)

## Operational Control
- **Executive**: Managed via [orchestrator.py](../orchestrator.py).
- **Verification**: Execute `.\scripts\operations\trace-meal.ps1`.

## Documentation
- [Soma Root AGENTS.md](../AGENTS.md)
- [Soma Root README.md](../README.md)
