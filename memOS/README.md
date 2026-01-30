# Hands: memOS (Interaction)

## Overview
memOS (formerly memos.MCP) is the motor control layer of the Soma organism. It provides a FastMCP 2.0 interface for agents to retrieve context from the Brain and promote working memories into the long-term Codex.

## Role in Soma
- **Function**: agentic_interface
- **Port**: 8768
- **Brain Connection**: Neo4j (Read-only for retrieval, Write via promote_memory).
- **Memory Tiers**:
  - **Tier 1 (Working)**: Redis-backed ephemeral memory.
  - **Tier 2 (Brain)**: Neo4j/Vector-backed retrieval.

## Operational Control
- **Executive**: Managed via [orchestrator.py](../orchestrator.py).
- **Verification**: Confirm tool availability via MCP client.

## Documentation
- [Soma Root AGENTS.md](../AGENTS.md)
- [Soma Root README.md](../README.md)
- [memOS Setup Guide](./docs/configuration.md)
