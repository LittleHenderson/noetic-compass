# Diagram-Loop Honest Two-Pass Eval — Proposal

**Branch**: `team/diagloop-honest-eval`
**Date**: 2026-05-03
**Status**: Proposal — corrective alternative to the leaky reference

---

## 1. The Leak in the Existing Reference

The `evaluate_diagram_loop_invariance.py` file (created by the sibling solution-architect
routine) contains a `diagram_loop_records()` function that compiles the **ground-truth CAS
expression** directly into the `prior_diagram` field given to the model at eval time:

```python
# ANTI-PATTERN — oracle leak (evaluate_diagram_loop_invariance.py, diagram_loop_records())
for record in eval_records:
    for variant in paraphrase_variants:
        variant["prior_diagram"] = compile_to_graph(str(record.get("cas_expression", "")))
```

The `compile_to_graph` call encodes the ground-truth answer into a graph structure that the
model then uses as prior context. The model is subsequently evaluated on whether it predicts
the same CAS expression that was embedded into the prior. This is an **oracle**: the model
has access to the answer before it answers.

The accompanying docstring states:
> "tells the model exactly what structure the expression encodes."

That sentence is a candid admission of the leak. Rather than measuring whether the
diagram-loop lever produces a generalizable prior, the experiment measures whether the model
can exploit a directly injected oracle.

**Why this wasn't obvious at code review time**: the `compile_to_graph` call appears inside a
helper function (`diagram_loop_records`) that is one level removed from the eval loop. The
leak is not in the scoring logic — it is in the data preparation step that feeds the eval.

---

## 2. Why the Leak Invalidates Prior Smoke Evidence

The K9_DiagLoop smoke test reported:

| Metric | Value |
|---|---|
| Canonical accuracy | 65.5% |
| Paraphrase lift vs text-only | +34.8 pp |
| Per-head Noetic lift | +13.7 pp |
| Per-head Drive lift | +5.0 pp |

All four numbers are contaminated by the oracle. Specifically:

- **Canonical 65.5%** may be inflated if the canonical eval also used the leaky prior path
  (canonical record's own `cas_expression` compiled into its prior — circular).
- **+34.8 pp paraphrase lift** is the primary artifact: each paraphrase variant received the
  ground-truth graph as context, then was scored on whether it matched that same ground truth.
  The model did not have to generalize across surface forms; it only had to decode the graph it
  was given. A lookup table would achieve 100% under this protocol.
- **+13.7 pp Noetic / +5 pp Drive** follow directly from the paraphrase inflation — they are
  per-head slices of the same contaminated signal.

The correct baseline for comparison is the text-only paraphrase invariance eval in
`evaluate_paraphrase_invariance.py`, which is clean (no graph input, no oracle).

---

## 3. The Honest Two-Pass Protocol

### Invariant — enforced in code

> **`compile_to_graph` must NEVER be called on the eval record's ground-truth `cas_expression`
> field in the evaluation path.** Every call to `compile_to_graph` during eval must receive a
> string that originated from the model's own structured-head predictions.

### Data flow

```
Eval records (held-out)
       │
       ▼
┌─────────────────────────────────┐
│  PASS 1 — text-only inference   │
│  model(batch, graph_batch=None) │
│  → prediction dicts per record  │
│  → convert predictions to CAS  │
│    expression strings           │
└─────────────────────────────────┘
       │
       │  canonical_predictions: {record_id → predicted_expr_string}
       │
       ▼
┌───────────────────────────────────────────┐
│  compile_self_prediction_priors()         │
│  For each record:                         │
│    prior_graph = compile_to_graph(        │
│      canonical_predictions[record_id]    │  ← model's OWN prediction
│    )                                      │  ← NEVER the ground-truth
│    attach prior_graph to paraphrase       │
│    variants for this record               │
└───────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  PASS 2 — paraphrase eval with self-prior   │
│  For each paraphrase variant:               │
│    model(batch, graph_batch=prior_graph)    │
│  Score against ground truth                 │
└─────────────────────────────────────────────┘
```

### Worked example

Record `r42`:
- Ground truth: `^2^C_{F4}|f`
- User prompt: "Turn this formal natural-language CAS reading into the exact expression: ..."

**Pass 1**: model runs text-only on `r42`'s prompt. Suppose it predicts `expression_family =
"register_state"`, `noetic = 2`, `domain = "C"`, `drive = "F4"`, `register_mode = "affective"`.
We convert this to a CAS expression string: `^2^C_{F4}|f` (correct in this example). Call
`compile_to_graph("^2^C_{F4}|f")` → `prior_graph_r42`.

**Pass 2**: generate paraphrases of `r42`'s prompt. For each paraphrase, call
`model(paraphrase_batch, graph_batch=prior_graph_r42)`. Score against ground truth `^2^C_{F4}|f`.

Now suppose instead pass 1 predicted `^3^C_{F4}|f` (wrong — Negative instead of Positive).
Then `prior_graph_r42 = compile_to_graph("^3^C_{F4}|f")`, which encodes the **wrong** structure.
Pass 2 must recover from this noisy prior. That recovery (or failure to recover) is exactly
what we want to measure: does the diagram-loop lever help in honest production conditions?

---

## 4. What the Honest Eval Measures That the Leaky One Cannot

**(a) Whether the graph encoder helps in production.**
In production, the model never has access to ground-truth graph context. The honest eval uses
the same prior the model would generate at inference time. A real lift in this eval is
causally attributable to the graph encoder making better use of the model's own prior
predictions.

**(b) Whether the model recovers from wrong canonical predictions.**
When pass-1 canonical accuracy is <100%, some self-prediction priors will be wrong. Pass 2
measures whether the model can still predict correctly despite the noisy prior. This tests
robustness of the graph encoder to realistic noise levels.

**(c) The actual paraphrase-invariance lift attributable to the lever.**
Comparison: `paraphrase_with_self_prior` vs `paraphrase_text_only`. The difference isolates
the graph encoder's contribution under honest conditions. If the +34.8 pp from K9 shrinks to
near zero, the lever has no real effect; if it remains positive, the effect is genuine.

**(d) Diagnostic decomposition: four metrics.**
The honest report breaks out all four conditions:
- `canonical_text_only` — text-only on canonical prompts (pass-1 accuracy)
- `canonical_with_self_prior` — canonical prompts with self-prediction graph (sanity check)
- `paraphrase_text_only` — text-only on paraphrase variants (existing paraphrase eval)
- `paraphrase_with_self_prior` — paraphrase variants with self-prediction prior (the honest lever test)

The leaky eval could only report `canonical_with_oracle_prior` and
`paraphrase_with_oracle_prior` — conflating oracle access with graph-encoder utility.

---

## 5. Risk Analysis

**Risk A: canonical accuracy is low (<50% on pass 1).**
If the model's canonical text-only accuracy is low, the majority of self-prediction priors
will be wrong or empty. Pass 2 paraphrase accuracy will then be bounded by how well the model
recovers from noisy priors. This is a real architectural constraint, not an eval artifact: if
the lever can only help where pass-1 was already right, the lever has limited production value.
The honest eval makes this constraint visible; the leaky eval hid it.

**Mitigation**: report pass-1 canonical accuracy prominently. If it is below a threshold (e.g.
50%), flag in the report that self-prediction priors are predominantly wrong and that lever
benefit estimates may be pessimistic for a better-trained model.

**Risk B: `compile_to_graph` of a wrong expression is not a valid empty graph.**
If `compile_to_graph` on an invalid/wrong expression raises an exception or returns a
structurally broken graph, pass 2 could crash rather than degrade gracefully. Mitigation: wrap
`compile_to_graph` in the prior-building step so that any exception or empty result falls back
to an empty graph (zero-attention behavior), and log the fallback count.

**Risk C: Paraphrase template overlap with training set.**
This eval uses `EVAL_PARAPHRASE_TEMPLATES` (held-out from training). The disjointness
invariant is already tested in `test_paraphrase_templates.py`. No additional risk introduced.

**Risk D: The self-prediction prior for the canonical prompt (pass 2, canonical variant).**
If we also evaluate canonical prompts with self-prediction priors (for the
`canonical_with_self_prior` metric), the prior is compiled from the same pass-1 prediction for
that record. This is not circular — the prior encodes what the model predicted, not the ground
truth — but it is a form of self-consistency measurement. Document this clearly in the report.

---

## 6. Relationship to Sibling Agents

This proposal and implementation are the **corrective alternative** to the leaky path produced
by the `team/diagloop-solution-architect` routine. The user should treat these as two options:

- **`team/diagloop-solution-architect`**: may mirror the oracle leak from `evaluate_diagram_loop_invariance.py`. Produces inflated numbers. Not representative of production performance.
- **`team/diagloop-honest-eval`** (this branch): honest two-pass protocol, self-prediction priors only, conservative numbers. Representative of production performance.

The recommendation is to ship the honest eval and deprecate `evaluate_diagram_loop_invariance.py` in place (not delete — its commit history documents the anti-pattern for the record).
