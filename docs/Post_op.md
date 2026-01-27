# SOMA: Surgical Verification Protocol (SVP-001)

Auditor: [[../../memos.MCP/01_Overview/CLAUDE|Claude]] Opus
Subject: SOMA_MONOREPO (Genesis Refactor)
Date: 2026-01-21
Objective: Confirm system stability, zero regression, and resolution of historical pathologies.

## 1. Environmental Integrity (The Body)

_Objective: Confirm the physical container host and volumes are mounted correctly on Windows._

**PRE-FLIGHT STATUS: VALIDATED ✅**
- docker-compose.yml v3.9 validated via `docker-compose config`
- LanceDB mount configured: `D:\docker-data\LanceDB:/opt/soma/memory/lancedb`
- Network `soma-nervous-system` defined in compose

- [x] **Docker Compose Configuration**
  - Validated: `docker-compose config --quiet` passes
  - **Verified:** All 5 services defined (`soma-brain`, `soma-stomach-daemon`, `soma-stomach-ui`, `soma-hands`, `soma-hippocampus`)
- [ ] **Docker Service Health** (Run after `docker-compose up -d`)
  - Run `docker-compose ps`.
  - **Verify:** All services show `Status: Up`.
  - **Constraint:** Zero `Exit 1` or `Restarting` states allowed.
- [ ] **Volume Persistence (LTM Check)**
  - Inspect `ingest-daemon` mounts: `docker inspect soma-stomach-daemon`.
  - **Verify:** Host path `D:\docker-data\LanceDB` is successfully mapped to `/opt/soma/memory/lancedb`.
  - **Rationale:** Without this, Long-Term Memory (Vectors) is ephemeral (Amnesia Risk).
- [ ] **Windows Networking (The Nervous System)**
  - **Verify:** `soma-nervous-system` bridge network exists.
  - **Verify:** Containers can resolve each other by name (e.g., `ping soma-hippocampus` from inside `soma-stomach-daemon`).

## 2. Neural Calibration (The Subconscious)

_Objective: Verify the Windows Native Model Runner is accessible from within the Linux containers._

- [x] **Host Model Availability**
  - Run `docker model ls` on the Host (PowerShell).
  - **Verified:** `qwen3-embedding:0.6B-F16` is present and ready (1.11GiB, MOSTLY_F16).
- [ ] **Internal Neural Link** (Run after `docker-compose up -d`)
  - Exec into the Stomach: `docker exec -it soma-stomach-daemon /bin/bash`.
  - Run `curl http://model-runner.docker.internal:11434/api/tags`.
  - **Verify:** Response includes the Qwen3 model JSON.
  - **Success Criteria:** `InGest` can "see" the host's brain.

## 3. Metabolic Function (The Stomach / InGest)

_Objective: Confirm Dagster is operational and "Poison Pill" immunity is active._

- [ ] **Telemetry Interface**
  - Open `http://localhost:3000` in browser.
  - **Verify:** Dagster UI loads without errors.
  - **Verify:** `code_location` "[[../../OmegaKG/governance/04-SERVICES/INGEST_LLM_AS|ingest_llm_as]]" is loaded (Green [[../../InGest-LLM/00_History/STATUS|status]]).
- [ ] **Poison Pill Test (EVT-LOOP-589 Regression Test)**
  - **Action:** Drop a binary file (e.g., `test.exe` renamed to `test.log`) into the [[../../InGest-LLM/03_Implementation/reference/ingestion|ingestion]] bucket.
  - **Expectation:** Pipeline runs. `raw_file_ingest` asset result is `SKIPPED` or `IGNORED`.
  - **Critical Failure:** Pipeline crashes (Red) or enters infinite retry loop.
  - **Success Criteria:** System metabolizes the error without halting.

- [ ] **Standard Digestion Test**
  - **Action:** Drop a clean text file (`hello_soma.txt`) into the [[../../InGest-LLM/03_Implementation/reference/ingestion|ingestion]] bucket.
  - Expectation:
        1. raw_file_ingest -> Success.
        2. text_extractor -> Success.
        3. vectorizer -> Success (Embeddings generated via Qwen3).

  - **Verify:** Vectors appear in `D:\docker-data\LanceDB`.

## 4. Immune Response (The Brain / OmegaKG)

_Objective: Confirm the Guardian Router prevents Auth Rate Limits._

- [ ] **Guardian Gatekeeper Check**
  - **Action:** Send a POST request to `http://localhost:8000/guardian/validate` with an invalid `SOMA_INTERNAL_KEY`.
  - **Verify:** Response is `403 Forbidden` or `401 Unauthorized`.
- [ ] **Neo4j Connectivity (EVT-50N42 Regression Test)**
  - **Action:** Trigger a write via the Guardian endpoint.
  - **Verify:** Write succeeds in Neo4j Browser (`http://localhost:7474`).
  - **Verify:** No `Neo.ClientError.Security.AuthenticationRateLimit` logs in `soma-hippocampus`.

## 5. Functional Parity (Zero Degradation)

_Objective: Ensure no features were lost during the transplant._

- [ ] **Reasoning Capability**
  - **Verify:** `InGest` can successfully call the external LLM API (Nano-GPT/Zai) for summarization if triggered.
  - **Check:** `NANO_GPT_API_KEY` is correctly injected into the container env.

- [ ] **Working Memory**
  - **Verify:** Redis (`localhost:6379`) is accepting connections from `memOS`.

## 6. Final Sign-Off

[[../../InGest-LLM/00_History/STATUS|Status]]: [ PASS / FAIL ]

Notes: **************\*\*\*\***************\_\_**************\*\*\*\***************

Signature: [[../../memos.MCP/01_Overview/CLAUDE|Claude]] Opus
