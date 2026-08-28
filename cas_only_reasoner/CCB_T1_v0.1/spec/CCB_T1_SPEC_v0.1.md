# CCB-T1: Tool Use Board v0.1

## Typed ToolIntents, Permission, Execution, and Provenance

**Status:** FROZEN for Phase 1. Tools are peripherals ABOVE the kernel:
a tool call happens only after a committed, sealed outcome, never from
a candidate branch, and never merely to see what happens. The cycle is:

    reason about need -> formulate ToolIntent -> check capability and
    permission -> commit tool use -> execute -> observe result ->
    store provenance -> continue reasoning

## 1. The tool cycle

The kernel halts with NEEDS_INFORMATION and typed lacunae; the tool
board matches a registered tool to the missing fact; the ToolIntent is
validated (committed outcome, sealed trace, tool capability, permission
<= authority, budget); the tool executes deterministically; its result
is stored as a fact with provenance (verified_calculation or
knowledge_query); the kernel re-runs with the new fact.

## 2. ToolIntent validation (authority)

    provenance.committed_outcome == true (only the committed path)
    provenance.sealed_trace == true
    provenance.branch_id is null (no branch may call tools)
    tool in registry
    tool.permission <= authority level
    cost <= remaining budget
    exactly one tool matches the need (ambiguity is typed)

## 3. Typed failures

    TOOL_UNKNOWN          no tool matches the need
    AMBIGUOUS_TOOL_NEED   several tools match
    TOOL_PERMISSION_DENIED
    TOOL_BUDGET_EXHAUSTED
    TOOL_FAILURE          the tool raised; no partial state is kept
    CONTRA_TOOL_RESULT    the result contradicts known facts; flagged,
                          never silently used

## 4. The fault and adversarial suite (the G7 gate)

Injected tool failure, permission denial, budget exhaustion, ambiguous
needs, and contradictory/hostile tool results - each must surface as a
typed outcome with no partial state and no fabricated continuation.

## 5. Non-goals

No real filesystem, network, or external processes in v0.1: tools are
deterministic in-process peripherals (exact calculator, knowledge
query). The board proves the AUTHORITY and FAULT discipline; external
tools arrive later behind the same gates.
