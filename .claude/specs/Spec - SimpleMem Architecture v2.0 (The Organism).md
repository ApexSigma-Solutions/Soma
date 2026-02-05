---
uid: SPEC-ARCH-002
title: SimpleMem Architecture v2.0 (The Organism)
status: active
created: 2026-02-03T00:30:00+02:00
pinned: true
tags:
  - architecture
  - soma
  - simplemem
  - organism
modified: Tue, 3rd February 2026 00:29
---

# Spec: SimpleMem Architecture v2.0 (The Organism)

## 1. Philosophy & Metaphor

The **SimpleMem** architecture defines how the Soma ecosystem perceives, processes, stores, and retrieves information. It rejects the "Monolithic Agent" model in favor of a biological "Organism" model, where specific organs handle specific stages of memory formation to ensure resilience, scalability, and strict separation of concerns.

### The Biological Mapping

|               |                    |              |                                                                                                        |
| ------------- | ------------------ | ------------ | ------------------------------------------------------------------------------------------------------ |
| **Component** | **Organ**          | **Function** | **Responsibility**                                                                                     |
| **InGress**   | **The Senses**     | Perception   | Receives raw stimuli (events, chat, webhooks). Validates inputs and "feels" the environment.           |
| **InGest**    | **The Stomach**    | Digestion    | Breaks down raw inputs (chunking), extracts nutrients (embedding), and prepares data for assimilation. |
| **Redis**     | **Nervous System** | Transport    | The high-speed signal pathways (Streams) connecting organs.                                            |
| **OmegaKG**   | **The Brain**      | Assimilation | Long-term storage, pattern recognition, and knowledge graph formation (Neo4j).                         |
| **memOS**     | **The Hands**      | Action       | Working memory, tool execution (MCP), and retrieving context to interact with the world.               |
| **Cortex**    | **The Face**       | Expression   | User interface and telemetry visualization.                                                            |

## 2. The Digestion Pipeline (Memory Formation)

Memory formation is a **linear, asynchronous, and idempotent** process. It flows in one direction: from Senses to Brain.

### Stage 1: Sensation (InGress)

- **Input:** HTTP/WebSocket Payload (e.g., User Chat, File Upload).
- **Action:**
    1. Validate Payload Schema.
    2. **IMMEDIATE WRITE** to `soma_sensory_lake` (Postgres).
    3. Set `processing_status = 'PENDING'`.
- **Constraint:** The Senses **DO NOT** think. They do not call the LLM. They do not check Neo4j. They only record the event.

### Stage 2: Digestion (InGest / Dagster)

- **Trigger:** Dagster Polls `soma_sensory_lake` for `PENDING` records.
- **Action:**
    1. **Chunking:** Split text into manageable tokens.
    2. **Enzyme Action (Embedding):** Send text to `Qwen3-Embed-0.6B-F16` (Docker Service).
    3. **Nutrient Transport:** Push `{mem_hash, vector, metadata}` to `soma:digestion:stream` (Redis).
    4. **Mark Complete:** Update Postgres to `DIGESTED` only upon successful stream ack.
- **Constraint:** The Stomach is the **ONLY** service allowed to generate embeddings.

### Stage 3: Assimilation (OmegaKG)

- **Trigger:** Async Worker (`vector_index_worker`) reads from Redis Stream.
- **Action:**
    1. **Idempotency Check:** Verify if `(n:AtomicMem {mem_hash: $hash})` exists.
    2. **Merge:**
        - If New: `CREATE` node, set vector and timestamp.
        - If Existing: Update `last_accessed` and `reinforcement_count`.

    3. **Acknowledge:** Send `XACK` to Redis to clear the signal.

## 3. The Retrieval Loop (Working Memory)

Retrieval is an **on-demand** process initiated by the Agent's need to act.

### The Hands (memOS)

- **Input:** "I need context on X."
- **Action:**
    1. **Query Brain:** Send vector search or Cypher query to OmegaKG.
    2. **Load Context:** Populate local "Working Memory" (Redis Cache) for the immediate session.
    3. **Execute Tool:** Use the context to perform an MCP action (e.g., `write_file`).

- **Constraint:** memOS **NEVER** writes directly to the Long-Term Memory (Neo4j). It only reads.

## 4. Immutable Laws (Mirmir Constraints)

1. **Law of Idempotency:**
    - Every piece of information must have a deterministic `mem_hash`.
    - Ingesting the same file 100 times must result in **1 Node** in the Graph.

2. **Law of Zero Blocking:**
    - The "Senses" (InGress) must never be blocked by the "Stomach" or "Brain."
    - All handoffs must be asynchronous (Postgres Queue or Redis Stream).

3. **Law of Organ Isolation:**
    - **InGress** cannot talk to **OmegaKG**.
    - **memOS** cannot talk to **InGest**.
    - Communication must flow through the defined nervous pathways (API contracts).

## 5. Technology Mapping

|                      |                     |                          |
| -------------------- | ------------------- | ------------------------ |
| **Component**        | **Technology**      | **Version/Spec**         |
| **Sensory Lake**     | Postgres (PGVector) | 16+                      |
| **Nervous System**   | Redis Streams       | 7.x                      |
| **Long-Term Memory** | Neo4j               | 5.x (Bolt)               |
| **Autonomic System** | Dagster             | 1.9+                     |
| **Embedding Model**  | Qwen3-Embed         | 0.6B F16 (Ollama/Docker) |

## 6. Framework Alignment (SimpleMem Mapping)

This architecture strictly adheres to the **SimpleMem** (Aiming Lab) separation of concerns.

|                         |                               |                                                                                                                        |
| ----------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **SimpleMem Component** | **Soma Organ Implementation** | **Notes**                                                                                                              |
| **MemoStorage**         | **The Digestion Pipeline**    | `InGress` (Capture) + `InGest` (Embedding) + `OmegaKG` (Persistence). Fully decoupled from the agent's reasoning loop. |
| **MemoRetrieval**       | **memOS (The Hands)**         | Dedicated service for querying the store based on current context constraints.                                         |
| **MemoManager**         | **Dagster (Autonomic)**       | Orchestrates the lifecycle of memory (creation, deduplication, archival) without blocking the primary agent.           |
