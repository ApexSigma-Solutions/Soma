---
created: Thu, 29th January 2026 23:44
modified: Thu, 29th January 2026 23:47
---

# Spec: ApexSigma Naming & Ontology Conventions

## 1. File UIDs

- **Task Notes**: `TN-{CODE}-{SEQ}` (e.g., `TN-DEV-101`)
- **Task Note Plans**: `TNP-{CODE}-{SEQ}` (e.g., `TNP-OPS-100`)
- **Domain Codes**:
    - `SOMA`: Ecosystem/Body
    - `CTX`: Cortex/Dashboard
    - `ING`: Ingress/Senses
    - `MEM`: memOS/Bridge
    - `OMG`: OmegaKG/Brain

## 2. Codebase Structure

- **Python**: Use `snake_case` for files and variables.
- **React**: Use `PascalCase` for components, `camelCase` for hooks.
- **Environment**: All secrets must be prefixed with `SOMA_` or `OMEGA_`.

## 3. The Organism Taxonomy

- Use biological analogies in documentation:
    - Ingress = Senses
    - InGest-LLM = Stomach/Digester
    - memOS = Bridge/Working Memory
    - OmegaKG = Brain/Long-term Memory -
