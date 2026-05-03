# DiagLoop Eval-Mode Fix — Proposal

**Author:** Solution Architect agent (DiagLoop Investigation Team)
**Date:** 2026-05-03
**Conditional status:** This proposal ASSUMES the eval-mode-mismatch hypothesis is correct. Sibling agents are independently verifying; proceed with implementation only if their verification returns positive.
**Run name for full retrain (if smoke validates):** `K9_DiagLoop_full_v2_fixed_eval`

---

## 1. Bug Summary

### The asymmetry

`evaluate_structured_token_prediction` (file: `cas-native/training/train_structured_prediction.py`, line 443) calls:

```python
batch_outputs = model(batch)
```

The training loop in `train_structured_token_prediction_local` (same file, PR #6 version with `--diagram-loop-pairs K`) calls:

```python
outputs = model(batch, graph_batch=graph_batch)
```

for every mini-batch that contains diagram-loop augmented records. At `--diagram-loop-pairs 1`, roughly 50% of training records are diagram-loop variants. Because these variants are shuffled into mini-batches uniformly, approximately 25-50% of training mini-batches include at least one diagram-loop record and therefore call `model(batch, graph_batch=graph_batch)`.

When `graph_batch` is not None and the model has `graph_encoder` + `graph_text_fusion`, the text hidden states are enriched with per-node graph context via cross-attention before being passed to the prediction head. This is the mode the model is supervised to excel at.

The per-epoch eval call (`_maybe_eval` → `evaluate_structured_token_prediction`) uses `model(batch)` unconditionally — `graph_batch=None`, fusion skipped. So per-epoch eval measures performance in a mode the model was partially NOT trained on. The per-epoch trajectory therefore appears to regress (the model improves on graph-fused inputs but the eval measures text-only inputs), and the checkpoint selector penalizes the best checkpoints.

Evidence of the asymmetry magnitude: +34.8 pp lift (30.7% → 65.5%) observed on the same K9_DiagLoop checkpoint when re-evaluated with `graph_batch` passed (smoke evidence from `evaluate_diagram_loop_invariance.py`). This matches the expected scale of an eval-mode-mismatch, not a training failure.

### Exact code locus

```
cas-native/training/train_structured_prediction.py
  function: evaluate_structured_token_prediction
  line ~443:  batch_outputs = model(batch)   ← BUG: no graph_batch
```

vs.

```
  function: train_structured_token_prediction_local (PR #6)
  training loop:  outputs = model(batch, graph_batch=graph_batch)   ← correct
```

---

## 2. Fix Mechanism

The fix lives entirely inside `evaluate_structured_token_prediction`, in the per-batch loop. After the `batch = tokens_to_structured_token_batch(...)` call, add logic that:

1. Checks whether the model has `graph_encoder` and `graph_text_fusion` set to non-None values. This distinguishes graph-fusion models (PR #6) from text-only models (master) without requiring an isinstance check or import of the graph encoder class.

2. If the model has graph components, compile each eval record's `cas_expression` into a `prior_diagram` graph dict via `compile_to_graph`. This mirrors what the training loop does for diagram-loop augmented records.

3. If at least one record in the mini-batch yields a non-empty graph (`n_nodes > 0`), pack all graph dicts (filling empty ones with `compile_to_graph("")` for uniform batch shape) into `graph_batch` via `serialize_diagram_for_batch`, then call `model(batch, graph_batch=graph_batch)`.

4. If no records yield valid graphs (all `n_nodes == 0`), or if `diagram_serialization` cannot be imported, or if the model lacks graph components: fall back to `model(batch)` unchanged.

This is the same pattern used by the working reference evaluator `evaluate_diagram_loop_invariance.py`'s `_eval_pass` function (with `use_graph_path=True`). The only structural difference is that eval records may not have `prior_diagram` pre-populated, so we compile from `cas_expression` on-the-fly rather than reading a stored field.

### Pseudocode

```python
# After: batch = tokens_to_structured_token_batch(...)
batch_records = records[start:start + batch_size]
graph_batch: dict | None = None
if (
    getattr(model, "graph_encoder", None) is not None
    and getattr(model, "graph_text_fusion", None) is not None
):
    try:
        from cas_native.training.diagram_serialization import (
            compile_to_graph as _ctg,
            serialize_diagram_for_batch as _sdfb,
        )
        prior_diagrams = [
            _ctg(str(r.get("cas_expression") or ""))
            for r in batch_records
        ]
        if any(g.get("n_nodes", 0) > 0 for g in prior_diagrams):
            filled = [g if g.get("n_nodes", 0) > 0 else _ctg("") for g in prior_diagrams]
            graph_batch = _sdfb(filled, device=dev)
    except Exception:
        pass  # diagram_serialization unavailable → text-only fallback

if getattr(model, "graph_encoder", None) is not None and getattr(model, "graph_text_fusion", None) is not None:
    batch_outputs = model(batch, graph_batch=graph_batch)
else:
    batch_outputs = model(batch)
```

Approximately 25 net lines of additive code. The existing `model(batch)` call becomes the else-branch.

---

## 3. Backward Compatibility

**Text-only models (master `StructuredTokenStructuredPredictor`) are unaffected:**
- `getattr(model, "graph_encoder", None)` returns `None` (attribute does not exist on master model)
- Code takes the `model(batch)` branch — identical to pre-fix behavior
- No import of `diagram_serialization` is attempted
- No CAS expression compilation is performed

**Graph-fusion models with records that have no CAS expression:**
- `cas_expression` is `None` or `""` → `compile_to_graph("")` returns an empty graph dict (`n_nodes=0`)
- If all records in the batch yield empty graphs, `graph_batch` stays `None` → `model(batch, graph_batch=None)` is called
- PR #6's `StructuredTokenStructuredPredictor.forward` handles `graph_batch=None` as a pass-through (fusion skipped) — no crash

**Records with unparseable CAS expressions:**
- `compile_to_graph` catches all exceptions internally and returns an empty graph dict — no propagation
- The outer `try/except` in the eval code provides an additional fallback layer
- Single records that fail to compile do not break the eval pass

**Import guard:**
- `diagram_serialization` is imported lazily inside the try/except block
- If the module is absent (e.g., running master without PR #6 files), the import raises `ImportError` which is silently caught, and `graph_batch` stays `None`

---

## 4. Test Plan

### Smoke test (5K records, 5 epochs, fixed eval)

1. Construct a 5K-record slice of Level 3 training data with valid `cas_expression` fields
2. Held-out eval: 500-record slice (disjoint from training)
3. Initialize `StructuredTokenStructuredPredictor` with `GraphEncoder` + `GraphTextFusion` (same architecture as K9_DiagLoop)
4. Train with `--diagram-loop-pairs 1` (50% diagram-loop augmented training records) for 5 epochs
5. Observe per-epoch `all_heads_exact_rate` trajectory from `_maybe_eval`

**Expected outcome with the fix:**
- Per-epoch trajectory climbs monotonically, matching the pattern from K9_SC3 (self-conditioning run)
- No regression between epoch 2 and epoch 5
- `all_heads_exact_rate` at epoch 5 materially above epoch 0 baseline

**Failure mode if hypothesis is wrong:**
- Trajectory still regresses or fails to climb despite the fix → one of the alternative explanations in section 6 is operative

### Automated unit tests (see Phase 3)

Four tests cover: backward compat (text-only model), graph propagation (model with graph_encoder + compilable records), mixed records (some compilable, some not), and empty-graph fallback (all fail to compile).

---

## 5. Full Retrain Plan

**Precondition:** smoke test at 5K records / 5 epochs validates monotonically climbing per-epoch trajectory.

**Run name:** `K9_DiagLoop_full_v2_fixed_eval`

**Hyperparameters:** identical to K9_DiagLoop_full_v1 (failed run):
- Dataset: full Level 3 training corpus
- `--diagram-loop-pairs 1`
- `d_model`, `bottleneck_dim`, `lr`, `weight_decay`, `batch_size`, `epochs`: same as K9_DiagLoop_full_v1
- `--eval-input`: same held-out 1K eval set (`level3_recoverable_eval_1000.jsonl`)
- Device: same GPU setup

**Single change from v1:** `evaluate_structured_token_prediction` now passes `graph_batch` for graph-fusion models.

**Checkpoint selection:** The fixed eval trajectory should identify a better best checkpoint — one that reflects graph-fused performance rather than text-only performance. Final report should compare K9_DiagLoop_full_v2_fixed_eval at best checkpoint against:
- K9_DiagLoop_full_v1 at best checkpoint (text-only eval selected)
- K9_SC3 (linear self-reference, paraphrase lever) as structural comparison
- Hash-feature baseline (48.7% all_heads_exact_rate) as floor

**Go / no-go criterion:** `all_heads_exact_rate` on held-out 1K eval ≥ 60% with the fixed eval trajectory monotonically climbing across all epochs.

---

## 6. Risk Analysis

The fix addresses the eval-mode mismatch hypothesis. Three alternative explanations for the trajectory regression would cause the fix to NOT address the underlying problem:

### R1 — Gradient path entanglement

Even when `graph_batch=None` and graph fusion is skipped, the text-path parameters (LayerNorms, linear projections) trained in the presence of the cross-attention block learn different weight statistics than a text-only model. The query projections and downstream norms co-adapt to the graph-fused path during training. Eval on text-only inputs then measures a model whose text-path parameters are partially specialized for a mixed-mode regime, not pure text generalization.

**Why the fix might not help:** The fix makes eval mode-symmetric (graph-fused eval for a graph-fused model). But if the model's text-path weights have entangled with the graph path such that text-only eval AND graph-fused eval both underperform a clean text-only baseline, the fundamental issue is cross-path entanglement, not eval mode selection. The only fix is separate training runs (text-only vs graph-fused, no mixing).

**Diagnostic:** Compare K9_DiagLoop_full_v2_fixed_eval against a text-only retrain on the same data without `--diagram-loop-pairs`. If the text-only run outperforms even with fixed eval, entanglement is the culprit.

### R2 — Oracle leak in eval

`compile_to_graph` is called on the ground-truth `cas_expression` label at eval time. The model's `graph_encoder` receives node features encoding the exact noetic, domain, drive, and register values that are simultaneously the prediction targets. This is a structural oracle leak: the correct answer is encoded in the input.

**Why the fix might not help:** The per-epoch eval numbers with the fix may be artificially inflated by oracle access, not reflecting production performance. The +34.8 pp lift observed on the same checkpoint may partly reflect oracle leak rather than genuine model improvement. If the model learns to read the answer from `graph_batch` during training (when diagram-loop records carry the ground-truth CAS expression as `prior_diagram`), it performs well on eval with oracle `graph_batch` but degrades on unseen inputs without a reliable prior.

**Diagnostic:** Run `evaluate_diagram_loop_invariance.py` with Pass 1 (no prior diagram, text-only) and Pass 2 (prior from oracle `cas_expression`). If Pass 2 >> Pass 1 by a large margin, oracle dependency is high. Production deployment cannot rely on oracle priors; the model must generalize from its own prior predictions, not ground-truth labels.

**Note:** This is counter-skeptic agent C2's central objection. The fix is still correct for eval consistency, but interpreting the resulting numbers requires acknowledging the oracle signal.

### R3 — Training instability independent of eval mode

K9_DiagLoop's 4.7× train-loss collapse (2.19 → 0.47) is consistent with the model learning a near-bijective graph-topology → label shortcut, not genuine text generalization. Even if the eval mode mismatch is fixed:
- The model may have overfitted to the graph topology of training-set expressions
- Eval records' `cas_expression` values may have overlapping structural patterns with training records (violating the spirit of disjointness even if literal IDs are disjoint)
- The fixed eval trajectory might still plateau or regress after epoch 2-3 if overfitting is the primary issue

**Why the fix might not help:** If the loss collapse reflects structural memorization of training graph topologies, the eval-mode fix makes the eval path more sensitive to exactly the feature (graph topology) the model memorized. The per-epoch trajectory may appear to improve (because the eval now rewards what the model learned) while paraphrase generalization (measured by `evaluate_paraphrase_invariance.py`) remains flat.

**Diagnostic:** Compare `all_heads_exact_rate` on held-out eval against paraphrase consistency rate from `evaluate_paraphrase_invariance.py`. Genuine generalization shows both rising. Memorization shows held-out exact rising while paraphrase consistency stays flat.

---

## Appendix: Reference Implementation Pattern

The working reference is `evaluate_diagram_loop_invariance.py`'s `_eval_pass` function, specifically the `use_graph_path=True` branch:

```python
graph_batch = None
if use_graph_path and model.graph_encoder is not None:
    prior_diagrams = [
        r.get("prior_diagram") or compile_to_graph("")
        for r in batch_recs
    ]
    graph_batch = serialize_diagram_for_batch(prior_diagrams, device=dev)
outputs = model(batch, graph_batch=graph_batch)
```

The key difference in our fix: eval records don't have `prior_diagram` pre-populated (they're canonical eval records, not diagram-loop augmented variants). We compile from `cas_expression` on-the-fly, with the same fallback to `compile_to_graph("")` for records without a valid expression.
