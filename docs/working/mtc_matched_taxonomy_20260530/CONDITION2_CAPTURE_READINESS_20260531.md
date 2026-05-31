# Condition-2 capture readiness — assessment (2026-05-31)

## Short version

Condition-2 passed BOTH local $0 gates:

1. Surface Gate — full-label text recovery 50% -> 6.9% (real meaning kept, copy
   shortcut killed).
2. Meaning-Preservation Gate — a reader using only the definition sheet recovers
   the element at 100% (80/80). PASS.

That makes it ready for ONE kind of capture but not the other:

- **READY:** a hidden-vs-text readout. "Does the model encode the CAS element
  label better than the prompt wording does?" The probe must beat 6.9%. This
  supports the *weaker* claim ("the model linearly encodes CAS distinctions").
- **NOT READY:** the full matched-taxonomy specificity gate (MTC.1). This is the
  *stronger* claim the project actually wants — "CAS is cleaner than serious,
  same-size non-CAS opponents." Condition-2 cannot earn it, for a concrete
  reason below.

## Why Condition-2 blocks the comparative gate

The pre-registration
(`docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md`,
Section 5, "Fixture Eligibility Gate") says a fixture is
`BLOCKED_FIXTURE_NOT_ELIGIBLE` when it has:

> abstract CAS/TKS role-bound prose but insufficient ordinary semantic
> topic/event content.

The required opponents are:

- **Control B** `NC40_TOPIC_FRAME_V1` — 8 ordinary topic sectors x 5 ordinary
  communication/event frames (a coherent non-CAS 40-way taxonomy).
- **Control C** `NC28_TOPIC_FUNCTION_NESTED_V1` — 7 topical settings x 4
  discourse functions (the nested opponent, the strongest discriminator).

Both must be assigned using ONLY non-CAS text/metadata — never CAS fields.

Condition-2 prompts are exactly:

> "A is the role where {noetic dynamic}, within {domain setting}; B is the role
> where {…}. Focus: A."

There is no ordinary topic (cooking, finance, weather, travel…) and no ordinary
event frame (complaint, announcement, instruction…) to carve. Every scrap of
meaning in the prompt IS the CAS element. So Controls B and C cannot be
materialized without reading CAS fields — which the prereg forbids. Per
Section 5, that is a BLOCK, not a CAS failure, but it means a capture run on
Condition-2 would land `BLOCKED_FIXTURE_NOT_ELIGIBLE` on the comparative gate.

The auto-generated scrambled-CAS control and shuffled-label null (Control A,
Control D) DO work on Condition-2 — but those alone only test the permutation
floor (H-MTC-4), not the "beats coherent non-CAS opponents" claim (H-MTC-1/2/3).

## The two honest paths

### Path 1 — capture the hidden-vs-text readout on Condition-2 now (GPU spend)

- Answers: does hidden recovery beat the 6.9% text baseline (and the scrambled
  floor)?
- Earns: the weaker "model encodes CAS distinctions, cleanly, above surface
  text" claim — a real, publishable result, and a clean one now that leakage is
  6.9% not 50%.
- Does NOT earn: comparative specificity vs coherent non-CAS opponents.
- Cost: one GPU capture + probe run. Authorization + dollar sign-off required.

### Path 2 — build Condition-3 (recommended) then capture once

Condition-3 = the SAME real CAS element meaning, but instantiated inside concrete
everyday scenarios that also carry ordinary topic + event-frame content. Goal:
a single prompt that simultaneously satisfies

- real CAS meaning recoverable (keeps the 95.6% mechanism),
- surface leakage near chance (Surface Gate),
- reader-recoverable meaning (Meaning-Preservation Gate),
- AND enough ordinary topic/event content that Controls B and C can be
  materialized from non-CAS fields (Fixture Eligibility Gate passes).

That makes the fixture eligible for the FULL MTC.1 gate, which is the claim the
project is actually chasing ("CAS-specific, not relabeled ordinary semantics").
All of Condition-3's build + the three local gates are $0 CPU. Only after all
gates are green does any GPU money get spent — and that one capture then answers
the real question instead of landing BLOCKED.

## Recommendation

Path 2. Condition-2 is a finished, honest artifact and a valid input to a
hidden-vs-text readout, but it is structurally incapable of earning the
comparative-specificity claim. Spending capture dollars on Condition-2's
comparative gate would return BLOCKED. Build Condition-3 (real meaning embedded
in ordinary topical scenarios), pass the same three local gates for $0, then
spend once on a capture that can actually PASS/FAIL the prereg.

## Status

- Condition-2: local gates GREEN. Eligible for hidden-vs-text readout. BLOCKED
  for MTC comparative gate (insufficient non-CAS content).
- Condition-3: not yet built. Design above. No GPU spend until its Surface,
  Meaning-Preservation, AND Fixture-Eligibility gates are all green locally.
- No capture dollars spent. Awaiting path decision.
