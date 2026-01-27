# Proposed Codex Constraint: MCP-MEM-001

## Constraint: Mandatory memOS.MCP Usage for Significant Work

**Rule ID**: MCP-MEM-001  
**Severity**: WARNING  
**Status**: PROPOSED (2026-01-10)

## Statement
Agents MUST use memOS.MCP tools (mark_significant, promote_memory, scratch_write) to record significant architectural decisions, infrastructure changes, bug fixes, and lessons learned when memOS.MCP is available.

## Origin
Discovered during MCP configuration (2026-01-10) when agent successfully configured entire MCP integration system but forgot to use the memory tools until reminded by user. Self-referential irony: built memory system, didn't use it for the work of building it.

## Rationale
- Organizational learning requires recording significant work
- Patterns must persist beyond individual sessions
- Future agents need context for decisions
- "Codex of Consequences" must grow from experience
- Without recording, institutional knowledge is lost

## Significance Criteria

**MUST Record (High)**:
- Architectural decisions
- Infrastructure changes
- New constraints/rules
- Bug fixes with root cause
- Security implementations
- Integration configurations
- Failed approaches (to prevent recurrence)

**SHOULD Record (Medium)**:
- Non-obvious implementation patterns
- Workarounds and justifications
- Tool usage discoveries

**MAY Skip (Low)**:
- Routine code changes
- Trivial fixes
- Documentation formatting

## Implementation Workflow
1. Use scratch_write() during complex work to trace reasoning
2. Use mark_significant() after completion (relevance_score 0.8-1.0)
3. Use promote_memory() to persist to knowledge base

## Required Structure
```
CONTEXT: [Situation]
ACTION: [What was done]
OUTCOME: [Results]
LESSONS: [Learning]
CONSTRAINTS: [New rules to prevent issues]
```

## Mirmir Approval
- Consulted: 2026-01-10
- Verdict: ✅ APPROVED (risk_score: 0.0)
- Citation: WARN-CONN (connection unstable, infrastructure needs start)

## Exceptions
- memOS.MCP infrastructure unavailable (fallback to Serena memory or markdown)
- Emergency maintenance
- Genuinely insignificant work (guideline: "Will this matter in 3 months?")

## Integration Path
1. ✅ Documentation (current) - Proposal created
2. Infrastructure Activation - Start memOS.MCP services
3. Constraint Activation - Add to Codex, update Mirmir logic
4. Monitoring - Track compliance, refine criteria

## Files
- Proposal: docs/GOVERNANCE/07-MIRMIR_PROTOCOL/CODEX_CONSTRAINT_PROPOSAL_MCP-MEM-001.md
- Referenced in: AGENTS.md, MCP_CONFIGURATION.md

## Next Actions
1. Start memOS.MCP infrastructure: cd memos.MCP && .\start-memos.ps1
2. Record this proposal via promote_memory() to close the loop
3. Add to formal Codex after activation

## Meta-Note
This constraint proposal itself demonstrates the need for the constraint. We're recording it now to close the self-referential loop!