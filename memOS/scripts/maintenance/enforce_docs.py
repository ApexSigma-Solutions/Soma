#!/usr/bin/env python3
"""
Enforce Documentation Standards Script.

This script checks for the presence of the Mimir Protocol usage guidelines
in critical documentation files (AGENTS.md, GEMINI.md) and appends them
if missing.

It is designed to be run from the memos.MCP project but targets the
OmegaKG root documentation.
"""

from pathlib import Path

# --- CONTENT DEFINITIONS ---

MIMIR_AGENTS_SECTION = """
## Mimir Protocol & memOS Usage

The **Mimir Protocol** is the system's "immune system," enforcing architectural constraints and preventing regression. **ALL Agents must adhere to the following:**

### 1. Mandatory Agent Review (MAR)
Before executing *any* task that modifies core systems (`domain/linear`, `omega_kg`) or deletes files, you **MUST** consult the Codex.

**Tool:** `consult_mirmir(plan_text, intended_outcome, affected_entities)`
- **When:** Start of any refactor, deletion, or architectural change.
- **Why:** To check for "Immune Memory" (historical failures).
- **If REJECTED:** You must abandon the plan or modify it according to the verdict.

### 2. Implementation Verification
After generating a plan or code, use the verification tool to double-check against constraints.

**Tool:** `verify_implementation(plan_text, implementation_diff)`
- **When:** Before committing code.
- **Why:** Uses a secondary LLM (Qwen 2.5) to "peer review" your work against Mimir constraints.

### 3. Reflective Analysis
If you encounter a failure or bug during your session, you must add it to the Codex to "immunize" the system.

**Tool:** `promote_memory(content, tags=["codex", "failure"], metadata={"severity": "WARNING"})`
- **When:** After resolving an error.
- **Format:** "CONTEXT: [What happened]. ROOT CAUSE: [Why]. CONSTRAINT: [Rule to prevent recurrence]."
"""

MIMIR_GEMINI_SECTION = """
## Mimir Protocol (System Integrity)
OmegaKG implements a "Digital Immune System" called the **Mimir Protocol**, which agents access via `memOS.MCP`.

### Key Concepts
*   **The Codex:** A repository of "Anti-Bodies" (constraints derived from past failures).
*   **MAR (Mandatory Agent Review):** Agents must query the Codex (`consult_mirmir`) before critical actions.
*   **Metabolization:** Failures must be converted into new Codex rules (`promote_memory`) to prevent recurrence.

### Accessing Mimir
Use the `memOS` MCP server tools:
*   `consult_mirmir`: Check constraints.
*   `verify_implementation`: Peer review code with Qwen 2.5 Coder.
*   `retrieve_context`: Search the knowledge base.
"""

# --- PATH CONFIGURATION ---


def get_target_files():
    """
    Resolve paths to AGENTS.md and GEMINI.md.
    Assumes script is run from inside memos.MCP or its scripts folder.
    Targets the parent OmegaKG root directory.
    """
    # Start from current file location
    current_dir = Path(__file__).resolve().parent

    # Traverse up to find memos.MCP root
    # scripts/maintenance/enforce_docs.py -> scripts/maintenance -> scripts -> memos.MCP
    project_root = current_dir.parent.parent

    # OmegaKG root is likely the parent of memos.MCP
    omegakg_root = project_root.parent

    agents_md = omegakg_root / "AGENTS.md"
    gemini_md = omegakg_root / "GEMINI.md"

    return agents_md, gemini_md


def check_and_update(file_path: Path, section_title: str, content: str):
    """Check if file contains section; append if missing."""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return

    try:
        text = file_path.read_text(encoding="utf-8")

        if section_title in text:
            print(f"✅  {file_path.name}: Mimir section present.")
        else:
            print(f"🛠️  {file_path.name}: Mimir section MISSING. Appending...")

            # Ensure double newline before appending
            if not text.endswith("\n\n"):
                if text.endswith("\n"):
                    new_content = "\n" + content
                else:
                    new_content = "\n\n" + content
            else:
                new_content = content

            file_path.write_text(text + new_content, encoding="utf-8")
            print(f"🎉  {file_path.name}: Updated successfully.")

    except Exception as e:
        print(f"❌  Error processing {file_path.name}: {e}")


def main():
    print("🔍  Mimir Documentation Enforcement Script")
    print("========================================")

    agents_path, gemini_path = get_target_files()

    print(f"Targeting:\n - {agents_path}\n - {gemini_path}\n")

    check_and_update(
        agents_path, "## Mimir Protocol & memOS Usage", MIMIR_AGENTS_SECTION
    )
    check_and_update(
        gemini_path, "## Mimir Protocol (System Integrity)", MIMIR_GEMINI_SECTION
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
