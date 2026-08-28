# Stage 0 Gap Analysis — CAS-RRK v0.1

**Status:** audit produced in the same workspace the handoff package
targets. No implementation changes are proposed here; the Stage-1 kernel
already exists and is green (28 tests), so this analysis records the
boundary between what was reused, what was rebuilt, and what remains
open.

## Reusable modules (existing repository)

| Existing artifact | Reused? | Notes |
| --- | --- | --- |
| cas-rr/ (CAS-RR v0.1 prototype) | concept-level | The kernel re-derives the authority model from the frozen contract; the cas-rr pattern matcher and evidence logic were the reference behavior, rewritten self-contained in kernel/cas_sem.py. |
| TKS_V74_COMPILER_IMPL_MAP.md, TKS_V74_COMPILER_PIPELINE.md | not yet | Rust compiler pipeline (lexer/parser/types/effects/ANF/bytecode/VM) is the Stage-2 IR target. Not integrated in Phase 1, per the brief ("for the first experimental kernel: no, it is not strictly required"). |
| cas_only_reasoner/ source PDFs | sources | Book, two CAS-Ohm papers, 28 Foundations, TKS manual - used for grounding; not code. |

## Conflicts between the frozen spec and existing code

1. cas-rr uses RESOURCE_EXHAUSTED; the kernel contract names
   BUDGET_EXHAUSTED. The kernel follows the contract.
2. cas-rr mixes scheduling and mutation inside component code; the
   kernel enforces the sole-writer rule (components propose intents
   only). This is a deliberate rebuild, not drift.
3. cas-rr's Ohm-shaped attention budget is absent from the kernel:
   CAS-Ohm has no runtime authority (manifest, phase_1_runtime).

## Underspecified points (OPEN-SEMANTICS)

Recorded in OPEN_QUESTIONS.md: canonical operator set, A_root label,
28-channel provenance, breakdown involution, counterfactual branches,
numeric/probabilistic reasoning, durable learning layers, RPM depth
policy, CAS-Ohm instrumentation interface, compiler integration.

## Proposed implementation sequence (already executed)

Stage 0: this analysis. Stage 1: Python reference kernel (kernel/),
28 tests green. Stage 2: shared CAS Kernel IR (target: emit kernel
events from the Rust pipeline). Stage 3: differential execution -
Python vs Rust on authorized intents, branch states, RPM transitions,
terminal status, final state hash, trace digest.

## Existing tests that must continue to pass

cas-rr: 43 pytest tests (independent prototype, untouched). Kernel:
28 tests (16 conformance rows, 6 golden fixtures, 6 replay).

## New conformance tests required (all implemented)

The 16-row table from spec/CONFORMANCE_PLAN_v0.1.md, plus fixture
goldens and deterministic replay with per-tick hash comparison.

## Risks of integrating the Python testbench and Rust toolchain

The Rust pipeline is a full language implementation (TKS v7.3/v7.4
features) whose semantics are far wider than the kernel's Phase-1 IR.
Integration must go through a shared IR (Stage 2), not through direct
AST reuse, or the kernel inherits semantics it cannot execute.

## Recommendation for the Python reference architecture

Accepted as built: dataclass-typed MachineState with canonical hashing,
intent-only components, sole-writer transaction coordinator, sealed
per-tick TraceEvents, replay by re-applying authorized intents. Keep
Python as the normative oracle; derive the Rust port from its behavior
under differential testing, not from re-reading the prose.
