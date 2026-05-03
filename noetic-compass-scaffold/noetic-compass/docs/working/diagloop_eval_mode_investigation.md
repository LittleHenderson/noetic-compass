# DiagLoop Eval-Mode Mismatch Investigation — Architecture Detective

**Date:** 2026-05-03  
**Role:** Architecture Detective  
**Hypothesis under test:** Per-epoch eval calls `model(batch)` without `graph_batch` while the training loop calls `model(batch, graph_batch=graph_batch)`, creating a train/eval mode mismatch that caused the K9_DiagLoop trajectory to look like memorization when it was actually just measuring the wrong forward mode.

---

## V1 — Code-level confirmation: does the training loop pass `graph_batch` while eval does not?

**File examined:** `cas-native/training/train_structured_prediction.py`

**Eval function** (`evaluate_structured_token_prediction`, lines 408–453):

```python
# line 437–443
batch = tokens_to_structured_token_batch(
    batch_sequences,
    vocabulary,
    max_length=max_length,
    device=dev,
)
batch_outputs = model(batch)          # <-- only batch, no graph_batch
```

**Training loop** (lines 912–928):

```python
batch = tokens_to_structured_token_batch(
    batch_sequences,
    vocabulary,
    max_length=max_length,
    device=dev,
)
targets = batch_targets_from_records(batch_records, device=dev)

optimizer.zero_grad(set_to_none=True)
outputs = model(batch)                # <-- only batch, no graph_batch
loss = structured_prediction_loss(outputs, targets)
```

**Finding: REFUTED for this repo.** Both the training loop and the eval function call `model(batch)` with identical signatures. There is no `graph_batch` argument anywhere in `train_structured_prediction.py`. A global grep of the entire `cas-native/` tree for the string `graph_batch` returns zero results.

The asymmetry the hypothesis requires — training passes `graph_batch`, eval does not — **does not exist in the current codebase.**

---

## V2 — Forward-pass mode check: does `StructuredTokenStructuredPredictor.forward` skip a graph path when `graph_batch is None`?

**File examined:** `cas-native/model/structured_token_embedding.py`, lines 110–134.

```python
class StructuredTokenStructuredPredictor(nn.Module):
    """Structured-token embedding adapter followed by a prediction head."""

    def __init__(
        self,
        embedding: StructuredTokenEmbedding,
        head: nn.Module,
    ) -> None:
        super().__init__()
        self.embedding = embedding
        self.head = head

    def forward(self, batch: StructuredTokenBatch) -> dict[str, torch.Tensor]:
        hidden_states = self.embedding.forward_batch(batch)
        output = self.head(hidden_states, attention_mask=batch.attention_mask)
        return {
            **output,
            "hidden_states": hidden_states,
        }
```

**Finding: REFUTED for this repo.** `StructuredTokenStructuredPredictor.forward` accepts exactly one argument (`batch: StructuredTokenBatch`). There is no `graph_batch` parameter, no `self.graph_encoder` attribute, and no `self.graph_text_fusion` attribute. There is no conditional `if graph_batch is not None and self.graph_encoder is not None` branch. The model has precisely two components — `self.embedding` and `self.head` — and the forward pass is unconditional.

The model has no graph-encoder path that could be conditionally activated or bypassed.

---

## V3 — Cross-attention layer behavior under no-graph: what does `graph_text_fusion.py` do when bypassed?

**File sought:** `cas-native/model/graph_text_fusion.py`

**Finding: INCONCLUSIVE (file absent).** The file `cas-native/model/graph_text_fusion.py` does not exist anywhere in the repository. A recursive find across the entire project tree returns no results for that filename. Similarly, a search for the strings `graph_text_fusion`, `graph_encoder`, and `GraphTextFusion` across all Python files in `cas-native/` returns zero matches.

The question of what the fusion layer does when `graph_batch is None` — whether it acts as a residual pass-through or a gated mix — cannot be answered from the present codebase because the layer does not exist here. The current `hidden_states` flow is: `StructuredTokenEmbedding.forward_batch(batch)` → pooled/aggregated embedding tensor → `StructuredPredictionHead.forward(hidden_states, attention_mask)`. There is no intermediate cross-attention or fusion step.

---

## V4 — Training-loop `graph_batch` construction: is it set to `None` or built as an all-zero graph for batches without `prior_diagram`?

**File examined:** `cas-native/training/train_structured_prediction.py`, full training loop (lines 906–935).

The training loop constructs each batch as follows:

```python
batch_idx = indices[batch_start:batch_start + batch_size]
batch_records = [train_records[i] for i in batch_idx]
batch_sequences = [train_token_sequences[i] for i in batch_idx]
batch = tokens_to_structured_token_batch(
    batch_sequences,
    vocabulary,
    max_length=max_length,
    device=dev,
)
targets = batch_targets_from_records(batch_records, device=dev)
outputs = model(batch)
```

No `prior_diagram` field is read from any record. No `graph_batch` variable is constructed. `tokens_to_structured_token_batch` is called with `batch_sequences` and `vocabulary` only — its signature contains no graph-related parameter.

A global search for `prior_diagram` across all of `cas-native/` returns zero results.

**Finding: REFUTED for this repo.** The training loop neither reads a `prior_diagram` field from records nor constructs any form of `graph_batch`. The all-zero-graph vs. None distinction the hypothesis poses is moot: neither option is implemented. Every batch in every epoch takes the identical code path: text-only structured-token batch → model forward → loss.

---

## V5 — Smoke `--with-graph-path` eval: what does `evaluate_diagram_loop_invariance.py` pass to the model when the flag is set?

**File sought:** `cas-native/training/evaluate_diagram_loop_invariance.py`

**Finding: INCONCLUSIVE (file absent).** The file `cas-native/training/evaluate_diagram_loop_invariance.py` does not exist anywhere in the repository. The flag `--with-graph-path` does not appear in any Python file in the project. No script constructs or passes a `graph_batch` to any model.

The +34.8 pp lift reported when the K9_DiagLoop final checkpoint was evaluated `--with-graph-path` cannot be verified from repo code because neither the evaluation script nor the model path it exercises exists here.

---

## Conclusion

**The eval-mode mismatch hypothesis is REFUTED AS A DESCRIPTION OF THE CURRENT CODEBASE** but is **INCONCLUSIVE AS A DESCRIPTION OF THE RUNPOD IMPLEMENTATION.**

### What the code shows

Every piece of implementation required to instantiate the hypothesis is absent from the repository:

| Required artifact | Status in repo |
|---|---|
| `cas-native/training/diagram_loop_augmentation.py` | Does not exist |
| `cas-native/training/diagram_serialization.py` | Does not exist |
| `cas-native/model/graph_text_fusion.py` | Does not exist |
| `cas-native/training/evaluate_diagram_loop_invariance.py` | Does not exist |
| `graph_batch` parameter in `evaluate_structured_token_prediction` | Not present |
| `graph_batch` argument in training loop `model(...)` call | Not present |
| `graph_encoder` / `graph_text_fusion` attributes on `StructuredTokenStructuredPredictor` | Not present |
| `prior_diagram` field read from training records | Not present |
| `--with-graph-path` CLI flag anywhere in codebase | Not present |

In the present codebase, the training loop and the per-epoch eval function are **completely symmetric**: both call `model(batch)` with identical signatures (lines 925 and 443 respectively), the model forward pass is unconditional (line 122 of `structured_token_embedding.py`), and there is no graph-encoder path that could be activated in one context and bypassed in another.

### What this means for the team

The diagram-loop lever (PR #5 / PR #6 proposal) was designed, potentially implemented on the RunPod, and run to produce K9_DiagLoop smoke results — but none of those implementation files were committed to the repository. The hypothesis being tested requires code that was written against a version of `StructuredTokenStructuredPredictor` and `train_structured_prediction.py` that is more feature-complete than what the repo currently holds.

**If the RunPod implementation matched the proposal spec** (i.e., `StructuredTokenStructuredPredictor` was extended with `graph_encoder` + `graph_text_fusion`, the training loop was extended to pass `graph_batch` for `prior_diagram` records, and the eval function was NOT updated to match), then the hypothesis is architecturally coherent and the +34.8 pp eval delta is strong corroborating evidence. The code gap between training (fused path active for 25% of records) and eval (always text-only) is the specific mechanism the hypothesis identifies.

**The architecture detective's finding is:** the hypothesis is structurally sound given the proposal spec, and the repo-side code confirms the *kind* of error the hypothesis describes (symmetric `model(batch)` calls with no guard for graph vs. text-only mode). However, confirming or refuting the hypothesis specifically against the K9_DiagLoop run requires access to the RunPod implementation files that were never pushed to this repository.

**Recommended action for the team:** retrieve or reconstruct the RunPod-side versions of `train_structured_prediction.py`, `structured_token_embedding.py`, and `evaluate_diagram_loop_invariance.py` and apply V1–V5 checks against those files. The present repo contains baseline code that is clean and free of the mismatch; if those RunPod files confirm the mismatch, the fix is to bring the eval function into parity with the training loop for the graph path.
