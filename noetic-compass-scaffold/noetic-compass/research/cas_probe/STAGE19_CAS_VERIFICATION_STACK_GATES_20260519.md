# Stage 19 CAS Verification Stack Gates

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `PRE_REGISTERED_NOT_RUN`

## Purpose

Stage 19 tests whether CAS Harness can improve usable prediction quality by
combining multiple existing verification signals:

1. multi-readout probe agreement,
2. factor decomposition consistency,
3. deterministic structural checks, and
4. trace stability confidence.

This is a verification-stack experiment, not a new model family run.

## Why This Is Needed

The current packet proves strong readout and likelihood-conditioning evidence.
It does not yet prove that a stacked verifier can push accepted prediction
quality toward 97%.

The proposed `~95-97%` number is therefore a hypothesis until Stage 19 runs.

## Critical Boundary

The candidate architecture mixes evidence from multiple prior fixtures:

- Stage 13 formula-family trace audit: three readout positions over 10 formula
  families, best `focus_token` layer 12 test accuracy `0.9540`.
- Stage 7.2 Foundation factor check: Drive, Register, and 28-way interaction
  over the original-TKS Foundation fixture.
- Stage 15/16 cross-architecture readouts: OLMo and Qwen Foundation CPL2
  evidence.

Those cannot be treated as one already-proven 97% stack. Stage 19 must test the
stack on a single locked fixture at a time.

## Stage 19A: Formula-Family Verification Stack

Fixture:

- `stage12_equations_formulas_full_20260517.jsonl`

Artifacts:

- `stage13_multilayer_formula_trace_audit_20260518.json`
- `STAGE13_MULTILAYER_FORMULA_TRACE_AUDIT_20260518.md`

Allowed components:

1. **Multi-readout ensemble**
   - `focus_token`, validation-selected layer 12.
   - `final_token`, validation-selected layer 7.
   - `mean_over_seq_len`, validation-selected layer 5.
   - Majority vote if at least two readouts agree.
   - If all three disagree, emit `CONFLICTED`.

2. **Trace stability confidence**
   - Runtime trace classes must not use gold labels.
   - `stable`: majority label covers at least 70% of layers and the longest
     run is at least 5 layers.
   - `uncertain`: at least half of layers are low-confidence or high-entropy.
   - `conflicted`: at least 5 switches or no majority over half the layers.
   - `drifting`: neither stable nor conflicted, but label changes over depth.
   - Accept high confidence only when the ensemble candidate matches the
     `focus_token` stable trace label.
   - Accept medium confidence only when at least two readout traces are stable
     and agree with the ensemble candidate.
   - Suppress all other cases.

Evaluation may additionally report oracle labels such as `stable_correct` and
`stable_wrong`, but those labels must not drive runtime acceptance.

3. **Structural checks**
   - Only checks that are concretely computable from Stage 12 metadata are
     allowed.
   - Compiler validity may be used as provenance because Stage 12 rows store
     compiler-valid formulas in metadata.
   - Do not claim Dk admissibility, involution suppression, or RPM
     section-retraction filtering unless the implementation loads an explicit
     validator and records the rule hit.

Disallowed in Stage 19A:

- Drive/Register recomposition, because Stage 12 formula-family labels are not
  Foundation labels.
- Cross-model OLMo/Qwen accuracy numbers, because Stage 19A is Pythia-160M
  formula-family verification.

Primary metrics:

- coverage: fraction of test examples accepted by the stack.
- accepted accuracy: accuracy over accepted examples only.
- suppressed rate: fraction suppressed as conflicted/unstable/invalid.
- error detection rate: fraction of single-probe wrong predictions that are
  suppressed or corrected.
- silent error rate: fraction of accepted predictions that remain wrong.
- oracle trace breakdown: `stable_correct`, `stable_wrong`,
  `early_correct_then_drift`, `late_emerging_correct`, `conflicted`,
  `uncertain`; report-only, not used for acceptance.

Pre-registered pass tiers:

| Tier | Accepted accuracy | Coverage | Silent error rate | Meaning |
|---|---:|---:|---:|---|
| `PASS_STRONG` | `>= 0.970` | `>= 0.850` | `<= 0.030` | Verification stack reaches the proposed quality target without suppressing too much. |
| `PASS_BOUNDED` | `>= 0.960` | `>= 0.800` | `<= 0.040` | Stack materially improves accepted predictions but misses the 97% target. |
| `DIAGNOSTIC_ONLY` | any | `< 0.800` | any | Stack works mainly as a flagger, not a high-coverage verifier. |
| `NULL` | `< single-probe baseline` | any | any | Stack does not improve usable quality. |

Reference baseline:

- Stage 13 best single readout: `focus_token` layer 12, test accuracy `0.9540`.

## Stage 19B: Foundation Factor Verification Stack

Fixture:

- Stage 7 original-TKS 28-Foundation fixture.

Allowed components:

1. 28-way Foundation prediction.
2. Drive prediction.
3. Register prediction.
4. Drive/Register recomposition.

Important caveat:

- Register is readout-causal but text-explained in Stage 7.2. Therefore,
  Register may be used as an internal consistency check, but not as a fresh
  beyond-text claim.

Conflict rule:

- If 28-way prediction disagrees with Drive/Register recomposition, choose the
  candidate with higher calibrated confidence only if the confidence margin is
  pre-registered.
- Otherwise suppress as `FACTOR_CONFLICTED`.

Pass metrics:

- accepted 28-way accuracy.
- accepted Drive accuracy.
- accepted Register accuracy.
- conflict suppression rate.
- silent conflict rate.

Do not project Stage 19B gains onto Stage 19A unless tested.

## Stage 19C: Structural Admissibility Filter

Structural gates are valuable only when they are implemented as deterministic
validators with explicit rule IDs.

Allowed rule classes:

- compiler-valid formula provenance, when a row stores a validated formula.
- register multiplicity / named emergent register checks, if the row contains
  same-Noetic multi-register structure and the validator is loaded.
- domain-order checks, if the expression explicitly encodes a domain chain.
- Dk admissibility, only if an explicit Dk table is loaded for the relevant
  source/target/operator tuple.

Disallowed phrasing before implementation:

- "Provably wrong" without a rule ID and validator output.
- "Nearest admissible prediction" without a deterministic distance metric.
- "RPM section-retraction failed" without a computed eta/epsilon chain check.

Every structural filter output must include:

```json
{
  "rule_id": "string",
  "status": "pass|fail|not_applicable",
  "evidence": "string",
  "replacement_label": "string|null"
}
```

## Evidence Packet Integration

If Stage 19 passes, each CAS Harness Evidence Packet should add:

- `verification_stack_version`
- `component_votes`
- `factor_consistency`
- `structural_gate_results`
- `trace_stability_class`
- `accepted`
- `confidence_tier`
- `suppression_reason`
- `silent_error_audit` for evaluation packets

## Stakeholder-Safe Language Before Run

Use this:

> CAS Harness has enough independent verification signals to test a stacked
> verifier. The hypothesis is that accepted predictions can approach 97%
> accuracy while conflicted cases are suppressed and surfaced as blind spots.

Do not use this yet:

> CAS Harness already gets 97%.

Do not use this yet:

> CAS can provably identify the remaining 3% it cannot get.

Use this after a passing Stage 19A run:

> On the locked Stage 12 formula-family fixture, the CAS Verification Stack
> accepted X% of examples at Y% accuracy and suppressed Z% as conflicted or
> structurally unsupported. The remaining silent error rate was S%.
