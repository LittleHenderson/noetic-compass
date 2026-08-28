# CCB-T1 v0.1 — Tool Use Board

Typed ToolIntents, permission, execution, and provenance. Tools are
peripherals ABOVE the kernel: a tool call happens only after a
committed, sealed outcome - never from a candidate branch, never to
see what happens. This board closes the strict G7 gate that CRQS
identified as the machine's blocking deficiency.

## Run

    cd cas_only_reasoner/CCB_T1_v0.1
    python -m pytest      # 11 tests
    python run_demo.py    # the tool cycle + the fault suite

## What it demonstrates

- The full cycle: the kernel halts NEEDS_INFORMATION with a typed
  missing need (derived from the rules, not improvised); the exact
  calculator computes 2/3 + 3/4 = 17/12 (no floats, even inside a
  tool); the result is stored with provenance verified_calculation;
  the kernel re-runs and CONCLUDES greater_than_one.
- Authority: ToolIntents require a committed outcome, a sealed trace,
  and no branch id. Branch-level tool requests are rejected.
- Typed failures with no partial state: TOOL_PERMISSION_DENIED,
  TOOL_BUDGET_EXHAUSTED, TOOL_FAILURE (injected), AMBIGUOUS_TOOL_NEED,
  and CONTRA_TOOL_RESULT - a hostile tool result that contradicts a
  known fact is flagged, never silently used.
- Determinism: the whole cycle is deterministic with sealed record
  digests.
- A proof-kernel bug found and fixed along the way: for unground goals
  like total(?S), the kernel prover bound distinct variables to the
  same first fact. Two-pass fact selection fixed it; all frozen kernel
  digests held unchanged.

## Honest boundary

Tools are deterministic in-process peripherals (exact calculator,
knowledge query). No real filesystem, network, or external processes
in v0.1 - the board proves the AUTHORITY and FAULT discipline;
external tools arrive later behind the same gates.
