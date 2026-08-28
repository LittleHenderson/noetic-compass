# CAS-RRK v0.1 — Handoff Package

The CAS Reasoning Runtime Kernel, Phase 1: a single-threaded,
deterministic, typed, snapshot-based, intent-driven reasoning kernel with
an atomic authority contract. No LLM, no English, no network, no neural
model, no CAS-Ohm runtime authority.

## Layout

    AUTHORITY_MANIFEST.yaml   source precedence + frozen phase-1 rules
    NON_GOALS.md              what Phase 1 deliberately does not build
    OPEN_QUESTIONS.md         OPEN-SEMANTICS items, frozen as questions
    spec/                     the five frozen specifications
    schemas/                  machine-readable JSON schemas
    fixtures/                 six CAS-Sem problem packets (JSON)
    golden/                   expected results and expected failures
    kernel/                   the Stage-1 Python reference kernel
    tests/                    the 16-row conformance suite + fixture tests
    run_demo.py               one-command demonstration
    docs/                     gap analysis, boundaries, roadmap

## Run

    cd cas_only_reasoner/CAS_RRK_v0.1
    python -m pytest          # conformance suite
    python run_demo.py        # all six fixtures, one table

## The one rule that governs everything

No subsystem may directly mutate authoritative machine state. Every
subsystem emits a typed intent; the transaction coordinator validates,
resolves, and atomically commits. State commit (every tick) and decision
commit (one branch becomes the conclusion) are two different operations
and must never be collapsed.

## Read order (precedence)

    1. AUTHORITY_MANIFEST.yaml
    2. spec/CAS_RRK_SPEC_v0.1.md
    3. spec/CAS_SEM_MVP_v0.1.md
    4. spec/CAS_KERNEL_IR_v0.1.md
    5. spec/AUTHORITY_CONTRACT_v0.1.md
    6. spec/CONFORMANCE_PLAN_v0.1.md
