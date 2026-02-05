"""
TN-400 / TN-OA-006 / TN-SOMA-304: Intelligence Tool for memOS (Mirmir Logic Adapter)

Integrates the Mirmir Protocol into the memOS MCP Server.
TN-SOMA-304: Uses OmegaKGClient for graph queries instead of direct Neo4j access.
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..services import ollama_service
from ..services.omegakg_client import OmegaKGClient
from ..database.pgvector_store import get_pgvector_store

# Configure Logger
logger = logging.getLogger("memos.mcp.intelligence")


# --- DATA MODELS ---


class CodexCitation(BaseModel):
    """Represents a specific rule or constraint from the Codex."""

    rule_id: str = Field(
        ..., description="The Unique ID of the Codex rule (e.g., 'RULE-001')."
    )
    content: str = Field(..., description="The text of the constraint.")
    severity: str = Field(..., description="CRITICAL, WARNING, or INFO.")


class MirmirVerdict(BaseModel):
    """The formal judgment returned by the Intelligence Layer."""

    approved: bool = Field(..., description="Whether the plan is allowed to proceed.")
    risk_score: float = Field(..., description="0.0 (Safe) to 1.0 (Catastrophic).")
    reasoning: str = Field(..., description="Explanation of the verdict.")
    citations: List[CodexCitation] = Field(
        default_factory=list, description="Relevant Codex rules citation."
    )
    suggested_modifications: Optional[str] = Field(
        None, description="How to fix the plan if rejected."
    )


# --- CORE LOGIC ---


async def consult_mirmir(
    plan_text: str, intended_outcome: str, affected_entities: List[str] = []
) -> MirmirVerdict:
    """
    Consults the Omega KG 'Mirmir Protocol' to validate a proposed action plan.

    Use this tool BEFORE executing high-risk changes (deletions, refactors).
    It checks the live Codex for architectural constraints.

    Args:
        plan_text: The natural language description of the action.
        intended_outcome: The goal (e.g., "Clean up legacy code").
        affected_entities: List of filenames or node IDs.

    Returns:
        MirmirVerdict: Approval status and constraints.
    """
    logger.info(f"Consulting Mirmir on plan: {intended_outcome}")

    citations = []
    risk_score = 0.0
    rejection_reasons = []

    # 1. HARDCODED SAFETY NET (The "Prime Directives")
    if any("omega_kg" in e or "domain/linear" in e for e in affected_entities) and (
        "delete" in plan_text.lower() or "remove" in plan_text.lower()
    ):
        citations.append(
            CodexCitation(
                rule_id="SYS-LOCK-001",
                content="Stabilized Domains (Linear/Omega Core) are Read-Only for removal operations.",
                severity="CRITICAL",
            )
        )
        risk_score += 0.9
        rejection_reasons.append("Attempted modification of locked Omega domain.")

    # 2. DYNAMIC CODEX LOOKUP via OmegaKG Guardian (TN-SOMA-304)
    try:
        client = OmegaKGClient()
        query = """
        MATCH (r:CodexRule {status: 'ACTIVE'})
        RETURN r.id AS id, r.content AS content, r.severity AS severity, r.keywords AS keywords
        """
        records = await client.query(query, limit=50)

        for record in records:
            rule_keywords = record.get("keywords", []) or []
            if rule_keywords and any(
                k.lower() in plan_text.lower() for k in rule_keywords
            ):
                citations.append(
                    CodexCitation(
                        rule_id=record["id"],
                        content=record["content"],
                        severity=record["severity"],
                    )
                )
                if record["severity"] == "CRITICAL":
                    risk_score += 0.6
                    rejection_reasons.append(f"Violates {record['id']}")

    except Exception as e:
        logger.error(f"Failed to query Mirmir Cortex via Guardian: {e}")
        if risk_score == 0:
            citations.append(
                CodexCitation(
                    rule_id="WARN-CONN",
                    content="Intelligence Layer connection unstable. Proceed with caution.",
                    severity="WARNING",
                )
            )

    # 3. SEMANTIC CODEX LOOKUP (Vector Store)
    try:
        store = get_pgvector_store()
        query_embedding = await ollama_service.get_embedding(plan_text)

        vector_results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5,
            score_threshold=0.6,
            tags=["codex", "constraint"],
        )

        for r in vector_results:
            r_id = r.get("metadata", {}).get("rule_id", f"VEC-{r['id']}")
            if not any(c.rule_id == r_id for c in citations):
                citations.append(
                    CodexCitation(
                        rule_id=r_id,
                        content=r["content"],
                        severity=r.get("metadata", {}).get("severity", "WARNING"),
                    )
                )
                logger.info(f"Found semantic constraint: {r_id}")

    except Exception as e:
        logger.warning(f"Semantic Codex lookup failed: {e}")

    # 4. VERDICT SYNTHESIS
    is_approved = risk_score < 0.7

    reason = "Plan approved."
    if not is_approved:
        reason = "Plan REJECTED via Mirmir Protocol. " + " ".join(rejection_reasons)
    elif citations:
        reason = "Plan Approved with Cautions."

    return MirmirVerdict(
        approved=is_approved,
        risk_score=min(risk_score, 1.0),
        reasoning=reason,
        citations=citations,
        suggested_modifications="Review citations and adjust scope."
        if not is_approved
        else None,
    )


async def verify_implementation(
    plan_text: str, implementation_diff: str, file_paths: List[str] = []
) -> Dict[str, Any]:
    """
    Verify a code implementation against Mirmir constraints using Qwen 2.5 Coder.

    Args:
        plan_text: Original plan/intent
        implementation_diff: The code changes (diff or full content)
        file_paths: List of files modified

    Returns:
        Dict with review status and feedback
    """
    logger.info(f"Verifying implementation for: {plan_text[:50]}...")

    mirmir_verdict = await consult_mirmir(plan_text, "Verification", file_paths)

    if not mirmir_verdict.approved:
        return {
            "status": "REJECTED_BY_POLICY",
            "message": "Plan violates Core Mirmir Protocols.",
            "violations": [c.model_dump() for c in mirmir_verdict.citations],
            "reasoning": mirmir_verdict.reasoning,
        }

    constraints_text = "NO SPECIFIC CONSTRAINTS FOUND."
    if mirmir_verdict.citations:
        constraints_text = "\n".join(
            [f"- [{c.severity}] {c.content}" for c in mirmir_verdict.citations]
        )

    system_prompt = (
        "You are an expert code reviewer and guardian of the Mirmir Protocol.\n"
        "Your job is to verify that the implementation matches the plan AND adheres to the constraints.\n"
        "If there are security risks, logic errors, or violations of the constraints, REJECT it.\n"
        "Be concise and strict."
    )

    user_message = f"""
PLAN:
{plan_text}

MIRMIR CONSTRAINTS (MUST FOLLOW):
{constraints_text}

IMPLEMENTATION (Diff/Code):
{implementation_diff}

TASK:
Review the implementation. 
1. Does it fulfill the plan?
2. Does it violate any constraints?
3. Are there bugs or security issues?

Output Format:
STATUS: [PASS/FAIL/WARN]
FEEDBACK: [Concise explanation]
"""

    try:
        response = await ollama_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model="qwen2.5-coder",
            temperature=0.2,
        )

        return {
            "status": "REVIEW_COMPLETE",
            "mirmir_citations": [c.model_dump() for c in mirmir_verdict.citations],
            "qwen_feedback": response,
        }

    except Exception as e:
        logger.error(f"Qwen verification failed: {e}")
        return {"status": "ERROR", "message": f"Verification failed: {str(e)}"}
