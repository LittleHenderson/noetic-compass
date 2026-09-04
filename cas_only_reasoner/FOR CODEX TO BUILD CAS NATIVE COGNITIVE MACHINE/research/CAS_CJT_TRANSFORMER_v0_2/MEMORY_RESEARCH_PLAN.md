# Memory research plan: chain tags before pulsation

Status: `ACCEPTED AS A POST-v0.2 RESEARCH PLAN; NOT IMPLEMENTED IN v0.2`

This plan records the useful design decisions from the owner-supplied
`CASFORMER_V02_PULSATION_AND_CHAIN_TAG_ADDENDUM.md`. The addendum is design
input, not runtime authority.

Source identity:

- bytes: `16201`
- SHA-256: `A3EBF653927139C812B71F8B2ABB95D3CAF1794C4D3D1E37797505493569CFF8`

Companion owner-supplied synopsis:

- bytes: `8682`
- SHA-256: `BAEFB13680E915A4FA92AFBA4CB88855F31AAD9F7FE9D9D8433775F0F3372564`

## What v0.2 adopts now

The addendum reinforces four release requirements already inside the v0.2
authority boundary:

1. A claimed memory read must have been requested, permitted, retained in the
   durable store, digest-valid, and within the exact compute ceiling.
2. Realized memory use must be zero when realized CAS-Ohm total current is
   zero, even when a pre-execution plan allowed a nonzero maximum.
3. Reconstruction must return the exact prior memory records and tensor
   artifacts consumed by a transition, separately from records written by the
   transition.
4. The stored trace must validate against the published strict top-level and
   phase-specific schema and bind the realized routing and memory evidence.
   Embedded typed records are also checked against their durable copies and
   their own contracts during reconstruction.

These checks harden the existing deterministic retrieval path. They do not
implement graph propagation, oscillation, or a branch manager.

## Why pulsation is not inserted into v0.2

The current contract freezes exactly eleven phases. Adding a twelfth
`MEMORY REQUEST` phase would silently change that contract. A future version
must either represent a memory request inside the existing `READ` and `EMIT`
records or deliberately publish a new tick-contract and trace-schema version.

The current prototype also has no authoritative branch manager. Therefore it
cannot honestly issue authoritative chain IDs. Pulses, graph edges,
`IdeaGeometry`, per-chain budgets, and chain join/split events belong in a
separately versioned subsystem.

The addendum's short description of `R` “closing” a repair is not the v0.2
commit protocol. Here, the distinct repair CJT publishes its accepted repair
Effect at `t+1`; the exact Effect-derived parent Cause resumes and seals the
`RepairOutcome` at `t+2`. A future memory strategy must preserve that boundary
unless a new repair contract is deliberately versioned.

## Required common interface

The first post-v0.2 step is to place the current deterministic retrieval behind
one proposal-only interface:

```text
MemoryStrategy.retrieve(
    query,
    authorized_snapshot,
    chain_context,
    compute_plan,
) -> MemoryReadProposal
```

Every implementation must receive the same immutable snapshot and ceiling.
It returns candidate evidence only. It cannot write Bias, memory, model
parameters, publication state, or CNCM state.

The comparison order is:

```text
M0  deterministic/static retrieval (current behavior)
M3  explicit chain-tagged activation (audit baseline)
M1  bounded scalar relevance propagation
M2  two-state phase/frequency oscillation
M4  trajectory-history readout
M5  explicit tags plus bounded pulsation
M6  matched generic or random control
M7  oracle chain identity (ceiling analysis only)
```

Explicit chain tags come before pulsation because identity and provenance must
be exact and replayable. Phase may rank or coordinate candidates within a
chain; it must never be the sole source of chain identity.

## Stability and accounting rules

For bounded scalar propagation, use a nonnegative normalized edge operator and
a fixed number of update steps:

```text
a(t+1) = clip((1-d) * a(t) + u(t) + k * W_norm * a(t) - h(t), 0, A_max)
```

Clipping alone is not a stability argument. The registered strategy contract
must state the edge normalization, coupling bound, damping range, maximum
steps, candidate limit, and exact compute-accounting rule.

A true oscillator needs at least two state dimensions, such as amplitude and
phase or an equivalent real pair. Frequency, phase, time step, pulse width,
and quality factor must have declared units or exact discrete semantics.
Transient activation, phase, inhibition, and refractory counters do not
survive restart unless a separate verified intent explicitly commits them.

## Authority rules

- The branch manager, not similarity or phase, issues a `chain_id`.
- A chain join or split needs its own typed, verified intent.
- A memory may participate in several chains with separate activation state.
- Repeated items with one provenance root do not count as independent
  corroboration.
- CAS-Ohm may allocate retrieval flow and compute. It cannot make a memory
  true, grant access, publish an Effect, authorize learning, or commit state.
- Retrieved material reaches neural weights only through the existing
  plasticity proposal, qualification, and atomic-commit path.

## Evidence needed before choosing a default

All strategies must use the same corpus, queries, graph, seeds, verifier,
provenance rules, top-k, step limit, and compute ceiling. Report retrieval
accuracy, chain attribution, false chain merges, pattern completion,
provenance diversity, false-memory admission, repair recovery, latency,
memory use, compute use, restart behavior, and trace completeness separately.

No result from the present v0.2 mechanism prototype establishes that
pulsation, chain tags, CAS-Ohm memory routing, or CAS improves learning or
reasoning.
