# CAS-Native v2 Training Data Format

This document specifies the schema consumed by `CASTrainer` (v2) and produced
by the forthcoming Synthetic Data Generator. It extends the v7.4 dataset
shape handled by `cas_native.training.data_pipeline.CASDataset` with four
optional label streams wired to the v2 components (ADR-01 / ADR-02 / ADR-04
/ ADR-06 in `docs/architecture/cas_native_v2_adrs.md`).

## Per-example schema

Each training example is a `dict` with the following fields. Only `prompt` /
`response` are required; every other field is optional and independently
contributes (or does not contribute) to the corresponding v2 loss term.

```jsonc
{
  // --- v7.4 fields (required for LM supervision) ---
  "prompt": "string",                // input text
  "response": "string",              // target completion

  // --- v7.4 CAS labels (optional, scalar supervision) ---
  "scores": {
    "operator_scores": [0.0, ..., 0.0],   // length 10
    "domain_scores":   [0.0, ..., 0.0]    // length 4
  },

  // --- ADR-01: Phenomenological Register labels ---
  "register_labels": [
    {"position": 0, "register": "T"},
    {"position": 3, "register": "A"},
    {"position": 5, "register": "f"},     // lowercase authoritative
    {"position": 7, "register": "E"}
  ],

  // --- ADR-02/03: Emergent register labels ---
  "omega_labels": [
    {"position": 0, "omega_name": "Omega_presence"},
    {"position": 4, "omega_name": "Omega_refusal"}
  ],

  // --- ADR-04: Production semantics target ---
  "production_target": {
    "prereqs": [
      [3, 1.0],                       // [state_id, coefficient]
      [5, 2.0],
      [7, 0.5]
    ],
    "leakages": [
      [9, 0.1]                        // optional side-reactions
    ],
    "observed_yield": 1.2             // Y_A
  },

  // --- CAS meta-logic / diagram-capable construct metadata ---
  "cas_expression": "NoeticCluster{^2, ^7} ∩ NoeticCluster{^7}",
  "construct_metadata": {
    "expression_kind": "set_operation",
    "construct_tokens": ["NoeticCluster", "∩"]
  }
}
```

### Field semantics

- `register_labels` — list of position-scoped annotations. Each entry names a
  canonical register (`T`, `A`, `f`, `E`; `|f` is lowercase per CAS v7.5
  Clarification 8). When present, the example contributes to:
  - Register-prediction accuracy (evaluation)
  - Rule 4 compliance loss (when at least two registers at the same Noetic /
    Domain appear without a named emergent result)
- `omega_labels` — list of emergent-register annotations matching names in
  `cas-native/config/omega_registry.yaml` (Appendix I synchronized). The
  first valid entry per example drives the emergent-register CE loss.
- `production_target` — proportional recipe per CAS v7.6 Clarification 9.
  `prereqs` is a list of `[state_id, coefficient]` pairs with state_id in
  `[0, 40)` (40 register-neutral cognitive states) and coefficient > 0.
  `leakages` is an optional list of `[state_id, magnitude]` side-reactions.
  `observed_yield` is the observed actual yield Y_A (scalar).
- `construct_metadata` — optional symbolic metadata for compiler-admitted
  meta-logic constructs. Supported `expression_kind` labels include
  `noetic_cluster`, `state_cluster`, `state_variant_cluster`,
  `relation_cluster`, `set_operation`, `typed_membership`, `typed_subset`,
  `coordinate`, `product`, `pullback_finite_meet`, `cover`, and `partition`.
  This is representation support only; it does not imply trained weights.
  `Pullback(...)` is represented strictly as a finite subobject
  meet/intersection, not as a general categorical pullback.

### Masking semantics

The training loop applies per-example masking driven by the presence/absence
of each label stream:

1. No v2 labels -> example contributes only to v7.4 loss terms.
2. `register_labels` present -> example contributes to Rule 4 compliance
   loss (when applicable).
3. `omega_labels` present -> example contributes to emergent-register
   cross-entropy loss (ADR-02/03).
4. `production_target` present -> example contributes to production-yield
   loss (ADR-04).

Examples are mixed within a batch; each loss term aggregates only over
examples where its labels are present, then averages.

## Synthetic Data Generator target distribution

Per ADR cross-cutting Design Ledger:

- 60% cross-register integration examples — carry `register_labels` and
  (where applicable) `omega_labels`, with some carrying valid Rule 4 emergent
  results and others deliberately violating to exercise the compliance loss.
- 40% production semantics examples — carry `production_target` with
  well-specified recipes, including labeled leakages and observed yields.

Both subsets MAY carry overlapping `scores` supervision (v7.4 operator /
domain labels) when available. Examples without any v2 labels remain valid
v7.4 training examples.

## DataLoader collation

The existing `cas_collate_fn` in `data_pipeline.py` preserves `cas_scores`
as a list-of-dicts per batch. The v2 trainer expects the additional label
streams to appear as list-of-lists / list-of-optional-dicts in the collated
batch:

```python
batch = {
    "input_ids":          Tensor[B, T],
    "targets":            Tensor[B, T],
    "attention_mask":     Tensor[B, T],
    "cas_scores":         list[dict],                # length B
    "register_labels":    list[list[dict]],          # length B
    "omega_labels":       list[list[dict]],          # length B
    "production_target":  list[dict | None],         # length B
}
```

When any v2 field is absent from the upstream data dict, the collate
function emits an empty list / ``None`` for that example so the trainer's
per-example masking logic still applies.

## Invariants (Synthetic Data Generator must preserve)

1. Every `register` value is in `{"T", "A", "f", "E"}` with `|f` lowercase.
2. Every `omega_name` is an admitted entry in
   `cas-native/config/omega_registry.yaml` (synchronized with Appendix I).
3. Every `prereqs` / `leakages` `state_id` is in `[0, 40)`.
4. Every `coefficient` is a strictly positive float.
5. `observed_yield` is a non-negative float.
6. Invariants 1–5 are enforced by `validate_cas_item` (to be extended) and
   any generator-level sanity checks.
7. `construct_metadata.expression_kind`, when present, must match the shared
   CAS-Native construct vocabulary and the `cas_expression` classifier.
