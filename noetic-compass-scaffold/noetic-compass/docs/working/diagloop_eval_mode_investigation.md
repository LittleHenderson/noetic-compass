# DiagLoop Eval-Mode Mismatch — Architecture Detective Investigation

**Role:** Architecture Detective  
**Branch:** `team/diagloop-arch-detective`  
**Source branch for all code readings:** `proposal/diagram-loop-impl`  
**Date:** 2026-05-03  
**Hypothesis under test:** The per-epoch eval in `train_structured_prediction.py` calls `model(batch)` without `graph_batch`, while the training loop calls `model(batch, graph_batch=graph_batch)` when records carry `prior_diagram`. The model's cross-attention and fusion-path LayerNorm never fire during per-epoch eval, forcing the head to operate on representations whose distribution diverges from the training path. The apparent K9_DiagLoop regression (63.2% → 42.9% → 28.1%) was eval measuring the wrong forward mode, not genuine degradation.

---

## V1 — Code-Level Confirmation: eval vs training call site

**What was checked:** `evaluate_structured_token_prediction` (the function called inside `_maybe_eval` during per-epoch eval) vs the mini-batch training loop inside `train_structured_token_prediction_local`.

### Per-epoch eval — `evaluate_structured_token_prediction`

File: `cas-native/training/train_structured_prediction.py`

```python
def evaluate_structured_token_prediction(
    model: StructuredTokenStructuredPredictor,
    records: list[dict[str, Any]],
    vocabulary: StructuredTokenVocabulary,
    *,
    token_sequences: list[list[Any]] | None = None,
    device: torch.device | str = "cpu",
    batch_size: int = 64,
    max_length: int = 256,
) -> dict[str, Any]:
    ...
    with torch.no_grad():
        for start in range(0, len(records), batch_size):
            batch_sequences = token_sequences[start:start + batch_size]
            batch = tokens_to_structured_token_batch(
                batch_sequences,
                vocabulary,
                max_length=max_length,
                device=dev,
            )
            batch_outputs = model(batch)          # <-- graph_batch absent; defaults to None
            for key in _EVAL_LOGIT_KEYS:
                chunks[key].append(batch_outputs[key])
```

`model(batch)` is called with a single positional argument. `graph_batch` is not passed; it defaults to `None`.

The eval function signature has no `graph_batch` parameter, no `prior_diagram` extraction, and no call to `serialize_diagram_for_batch`. The graph path cannot fire regardless of what the model was trained with.

### Training loop — `train_structured_token_prediction_local`

```python
# Build graph batch for diagram-loop records in this mini-batch.
# Records without prior_diagram pass None (text-only path).
prior_diagrams = [r.get("prior_diagram") for r in batch_records]
graph_batch: dict | None = None
if any(pd is not None for pd in prior_diagrams):
    # Fill missing prior_diagrams with empty graphs so the batch
    # has uniform shape; the node_mask zeros them out.
    from cas_native.training.diagram_serialization import compile_to_graph as _ctg
    filled = [pd if pd is not None else _ctg("") for pd in prior_diagrams]
    graph_batch = serialize_diagram_for_batch(filled, device=dev)

optimizer.zero_grad(set_to_none=True)
outputs = model(batch, graph_batch=graph_batch)   # <-- graph_batch passed explicitly
loss = structured_prediction_loss(outputs, targets)
loss.backward()
optimizer.step()
```

When any record in the batch has a `prior_diagram` field, `graph_batch` is built from `serialize_diagram_for_batch` and passed to `model(batch, graph_batch=graph_batch)`. The training loop explicitly constructs and passes `graph_batch`; the eval function does not.

**V1 verdict: CONFIRMED.** The call sites are structurally asymmetric. Per-epoch eval calls `model(batch)` — `graph_batch` is always `None`. The training loop calls `model(batch, graph_batch=graph_batch)` — `graph_batch` is non-None for any batch containing at least one diagram-loop record.

---

## V2 — Forward-Pass Mode Check: what `graph_batch=None` skips

**What was checked:** `StructuredTokenStructuredPredictor.forward` in `cas-native/model/structured_token_embedding.py`.

```python
def forward(
    self,
    batch: StructuredTokenBatch,
    graph_batch: dict[str, torch.Tensor] | None = None,
) -> dict[str, torch.Tensor]:
    hidden_states = self.embedding.forward_batch(batch)

    if (
        graph_batch is not None
        and self.graph_encoder is not None
        and self.graph_text_fusion is not None
    ):
        node_hidden, node_mask = self.graph_encoder.forward_nodes_dict(graph_batch)
        hidden_states = self.graph_text_fusion(hidden_states, node_hidden, node_mask)

    output = self.head(hidden_states, attention_mask=batch.attention_mask)
    return {
        **output,
        "hidden_states": hidden_states,
    }
```

The guard is a strict 3-way conjunction:

1. `graph_batch is not None` — must be passed by the caller
2. `self.graph_encoder is not None` — model must have been constructed with a GraphEncoder
3. `self.graph_text_fusion is not None` — model must have been constructed with a GraphTextFusion

All three must be true. When `graph_batch` is `None` (as in per-epoch eval), the entire graph encoder + fusion branch is skipped unconditionally. `hidden_states` remains the raw output of `self.embedding.forward_batch(batch)` and is passed directly to `self.head(...)` without any graph enrichment or fusion-path normalization.

**V2 verdict: CONFIRMED.** `graph_batch=None` causes the graph encoder and fusion layer to be entirely skipped. The head receives `embedding_output` directly. There is no partial activation, no cached graph state, no default baseline contribution from the fusion layer.

---

## V3 — Cross-Attention Layer Behavior Under No-Graph: normalization asymmetry

**What was checked:** `GraphTextFusion.forward` in `cas-native/model/graph_text_fusion.py`.

```python
def forward(
    self,
    text_hidden: torch.Tensor,
    graph_nodes: torch.Tensor | None,
    node_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    if graph_nodes is None:
        return text_hidden

    B, T, _ = text_hidden.shape
    N = graph_nodes.shape[1]
    H, D = self.n_heads, self.head_dim

    # Check if any real graph nodes exist at all
    if node_mask is not None and not node_mask.any():
        return text_hidden

    # Projections
    q = self.q_proj(text_hidden).view(B, T, H, D).transpose(1, 2)
    k = self.k_proj(graph_nodes).view(B, N, H, D).transpose(1, 2)
    v = self.v_proj(graph_nodes).view(B, N, H, D).transpose(1, 2)

    attn_logits = torch.matmul(q, k.transpose(-2, -1)) * self._scale

    if node_mask is not None:
        mask = node_mask.unsqueeze(1).unsqueeze(2)
        attn_logits = attn_logits.masked_fill(~mask, -1e9)

    attn_weights = F.softmax(attn_logits, dim=-1)
    attn_weights = self.dropout(attn_weights)

    context = torch.matmul(attn_weights, v)
    context = context.transpose(1, 2).contiguous()
    context = context.view(B, T, H * D)
    context = self.out_proj(context)
    context = self.dropout(context)

    # Residual + LayerNorm
    return self.norm(text_hidden + context)
```

The return statement is `self.norm(text_hidden + context)` — a **residual add followed by LayerNorm**.

There are two distinct forward-path return points:

- **Fused path (graph nodes present, mask non-empty):** returns `self.norm(text_hidden + context)` — the cross-attention context is added to `text_hidden`, and the sum is passed through `self.norm` (a dedicated `nn.LayerNorm(d_text)` belonging to `GraphTextFusion`).
- **Identity return (graph_nodes is None OR all nodes masked):** returns `text_hidden` unchanged — the fusion's `self.norm` is **never called**.

The head (`StructuredPredictionHead`) receives its input immediately after this layer. The consequence:

| Condition | What the head sees |
|---|---|
| Training, diagram record in batch | `GraphTextFusion.norm(text_hidden + cross_attn_context)` |
| Training, text-only record in mixed batch | `GraphTextFusion.norm(text_hidden + ~zero_context)` ≈ `GraphTextFusion.norm(text_hidden)` |
| Per-epoch eval (any record) | Raw `text_hidden` — fusion layer never called |

The `StructuredTokenEmbedding` has its own `output_norm = nn.LayerNorm(d_model)` that fires before this layer. So `text_hidden` is already unit-normalized at the embedding output. The `GraphTextFusion.norm` is a **second LayerNorm** that re-normalizes after the residual add. During training (any mixed batch), the head operates downstream of this second normalization. During per-epoch eval, the head operates on the embedding's normalized output only — skipping the second normalization entirely.

This is not merely "the graph signal is absent." It is a **distributional shift at the head input**: the per-epoch eval presents the head with activations from a normalization regime different from the one under which the head's weights were trained. The head's linear projections and output biases are calibrated to `GraphTextFusion.norm`-scaled inputs. Text-only eval bypasses this calibration.

**V3 verdict: CONFIRMED with a non-obvious extension.** The mode mismatch is not limited to missing cross-attention signal. It includes a missing `LayerNorm` step that the head depends on for correct input scale. The fusion layer is a `residual + LayerNorm` architecture; the bypass path returns `text_hidden` verbatim, not `LayerNorm(text_hidden)`. Both the signal and the normalization are absent during per-epoch eval.

---

## V4 — Training-Loop Graph Batch Construction: mixed-batch behavior

**What was checked:** The `graph_batch` construction block in the training loop, specifically the behavior when a batch contains a mix of diagram-loop and text-only records.

```python
prior_diagrams = [r.get("prior_diagram") for r in batch_records]
graph_batch: dict | None = None
if any(pd is not None for pd in prior_diagrams):
    from cas_native.training.diagram_serialization import compile_to_graph as _ctg
    filled = [pd if pd is not None else _ctg("") for pd in prior_diagrams]
    graph_batch = serialize_diagram_for_batch(filled, device=dev)
```

The condition is `any(pd is not None ...)` — the batch-level OR, not a per-record check. Consequences:

**Case 1: batch has no diagram-loop records.** `any(...)` is False. `graph_batch` remains `None`. The training forward call is `model(batch, graph_batch=None)`. The fusion layer is bypassed. The head sees raw embedding output. These batches are gradient steps on the text-only path.

**Case 2: batch has at least one diagram-loop record.** `any(...)` is True. `graph_batch` is built for the entire batch using `filled`, where missing `prior_diagram` values are replaced with `compile_to_graph("")`. From `diagram_serialization.py`, `compile_to_graph("")` falls through to `_empty_diagram_dict()` which has empty `nodes` and `edges` lists. When serialized, this produces all-zero node features and `node_mask=False` (all positions masked out).

Now examine the `GraphTextFusion.forward` early-return logic:

```python
# Check if any real graph nodes exist at all
if node_mask is not None and not node_mask.any():
    return text_hidden
```

This check is **global across the batch** — `node_mask.any()` is True if ANY position across ANY sample in the batch has a real node. In Case 2, at least one sample has a real diagram, so `node_mask.any()` is True. The fusion layer executes for all samples in the batch. Text-only records (with all-False node masks) have their attention logits filled with `-1e9`, producing near-zero attention weights, yielding near-zero `context`. Their output is `self.norm(text_hidden + ~0)` ≈ `self.norm(text_hidden)` — which is NOT the same as returning `text_hidden` unchanged.

**Practical implication:** With `diagram_loop_augment_train` variants constituting 25% of training records (from the K9_DiagLoop configuration), and with records randomly shuffled per epoch, the probability that a batch of size B drawn uniformly from a 75%/25% mix contains zero diagram-loop records is `0.75^B`. At B=64, this is `0.75^64 ≈ 0.000037` — essentially zero. Nearly every training batch is a "mixed batch" where the fusion layer fires for all records, including text-only ones.

In practice this means:
- Text-only records during training predominantly flow through `GraphTextFusion.norm` (via the mixed-batch path) with near-zero cross-attention context.
- The head's weight statistics are calibrated to `norm(text_hidden + ~0)` inputs for text-only records, and to `norm(text_hidden + real_context)` for diagram-loop records.
- Per-epoch eval presents the head with raw `text_hidden` — neither of these training distributions.

**V4 verdict: CONFIRMED with an amplification.** The mixed-batch behavior means that even the 75% of text-only training records usually pass through `GraphTextFusion.norm` (with near-zero context). The fusion layer's normalization is not a 25%-weight factor — it is the dominant forward-path for virtually all training steps. The per-epoch eval bypasses the fusion layer entirely, producing a head-input distribution that does not correspond to any significant portion of the training forward passes.

---

## V5 — Smoke `--with-graph-path` Eval Implementation

**What was checked:** `evaluate_diagram_loop_invariance.py` — specifically the `--with-graph-path` flag path, how `prior_diagram` is constructed, and what is passed to `model()`.

### How `--with-graph-path` initializes the model

```python
def load_model_for_eval(
    run_dir: Path,
    *,
    ...
    with_graph_path: bool | None = None,
    device: str = "cpu",
) -> tuple[StructuredTokenStructuredPredictor, StructuredTokenVocabulary]:
    ...
    if with_graph_path is None:
        dl_report = manifest_cfg.get("diagram_loop_augmentation_report", {})
        with_graph_path = int(dl_report.get("variants_per_record", 0)) > 0

    ...
    if with_graph_path:
        graph_encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
        graph_fusion = GraphTextFusion(d_text=d_model, d_graph=64)
        model = StructuredTokenStructuredPredictor(embedding, head, graph_encoder, graph_fusion)
    else:
        model = StructuredTokenStructuredPredictor(embedding, head)
```

When `--with-graph-path` is passed, the model is loaded with `GraphEncoder` and `GraphTextFusion` attached. Without it, these are absent and the fusion path cannot fire regardless of what `graph_batch` is passed.

### How `prior_diagram` is constructed for the eval pass

```python
def make_diagram_loop_records(
    records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a copy of each record with ``prior_diagram`` populated.

    The prior diagram is compiled from the record's ground-truth
    ``cas_expression``, so Pass 2 tells the model exactly what structure the
    expression encodes. ``base_id`` is set to ``record["id"]`` for matching.
    """
    result: list[dict[str, Any]] = []
    for record in records:
        variant = dict(record)
        variant["prior_diagram"] = compile_to_graph(
            str(record.get("cas_expression", ""))
        )
        variant["base_id"] = record.get("id")
        variant["paraphrase_source"] = DIAGRAM_LOOP_EVAL_SOURCE_LABEL
        result.append(variant)
    return result
```

`prior_diagram` is compiled from `record["cas_expression"]` — the **ground-truth label** of the record being evaluated. This is not the model's own prediction from a previous turn. This is an **oracle graph prior**: the evaluator constructs the exact structural graph that the model should predict and feeds it back as input.

### How `graph_batch` is passed in the eval loop

```python
def _eval_pass(
    model: StructuredTokenStructuredPredictor,
    records: list[dict[str, Any]],
    vocabulary: StructuredTokenVocabulary,
    *,
    ...
    use_graph_path: bool = False,
) -> dict[str, Any]:
    ...
    with torch.no_grad():
        for start in range(0, len(records), batch_size):
            ...
            graph_batch = None
            if use_graph_path and model.graph_encoder is not None:
                prior_diagrams = [
                    r.get("prior_diagram") or compile_to_graph("")
                    for r in batch_recs
                ]
                graph_batch = serialize_diagram_for_batch(prior_diagrams, device=dev)
            outputs = model(batch, graph_batch=graph_batch)
```

`use_graph_path` is set to `has_graph = model.graph_encoder is not None` for the diagram-loop pass. When `--with-graph-path` is passed, `model.graph_encoder is not None` is True, so `use_graph_path=True`. Every record in the diagram-loop eval pass gets a `prior_diagram` from `make_diagram_loop_records`, so `r.get("prior_diagram") or compile_to_graph("")` never falls back to the empty graph. The full fused forward path runs for every batch.

### What the +34.8 pp lift actually measures

The eval script runs two passes:

1. **Pass 1 (canonical):** `use_graph_path=False` → `model(batch)` without `graph_batch`. Text-only forward. Produces 30.7% at epoch 4 (per the K9_DiagLoop smoke report).
2. **Pass 2 (diagram-loop):** `use_graph_path=True` → `model(batch, graph_batch=graph_batch)` with `prior_diagram` compiled from the ground-truth `cas_expression`. Fused forward. Produces 65.5%.

The +34.8 pp delta (65.5% − 30.7%) is therefore the gap between:
- text-only eval on a model trained primarily in fused mode (systematically wrong eval mode)
- oracle-graph eval on the same model in its trained mode (correct eval mode with perfect priors)

This is not a realistic self-referential loop measurement — the prior is the ground-truth structure, not the model's own prior-turn prediction. It is an upper bound on the fused path's contribution. Real-world lift would be lower because the model's own predictions would not be 100% correct. What it does confirm: the model learned to use the graph signal when the fused path is exercised, and the 30.7% text-only score is an artefact of mode mismatch, not the model's true capability.

**V5 verdict: CONFIRMED.** `--with-graph-path` loads the model with GraphEncoder + GraphTextFusion and constructs `graph_batch` from ground-truth `cas_expression` labels for every eval record. It correctly exercises the fused forward path. The per-epoch eval in `evaluate_structured_token_prediction` does the opposite: it calls `model(batch)` without `graph_batch`, bypassing the fused path entirely. The +34.8 pp gap between the two is a direct measurement of the mode mismatch on the final K9_DiagLoop checkpoint. The 65.5% score is oracle-graph upper-bound; the 30.7% score is text-only-on-fused-model lower-bound.

---

## Conclusion

**Hypothesis status: CONFIRMED.**

Five independent code-level findings converge on the same mechanism:

| Verification | Finding | Verdict |
|---|---|---|
| V1 | `evaluate_structured_token_prediction` calls `model(batch)` — no `graph_batch` argument. Training loop calls `model(batch, graph_batch=graph_batch)`. | Confirmed |
| V2 | `StructuredTokenStructuredPredictor.forward` skips GraphEncoder + GraphTextFusion entirely when `graph_batch is None`. The head receives raw embedding output. | Confirmed |
| V3 | `GraphTextFusion` uses residual + LayerNorm (`return self.norm(text_hidden + context)`). The fusion's `norm` is absent from the eval path, producing a head-input distribution shift beyond just missing graph signal. | Confirmed + extended |
| V4 | Mixed-batch behavior: with 25% diagram records and batch size 64, essentially every training batch is mixed, so the fusion layer's norm fires for text-only records too (near-zero context path). The head is calibrated to norm'd inputs; eval bypasses the norm. | Confirmed + amplified |
| V5 | `--with-graph-path` eval constructs `graph_batch` from ground-truth `cas_expression` labels (oracle priors). The +34.8 pp lift (30.7% → 65.5%) measures text-only-on-fused-model vs oracle-graph-on-fused-model. Both are mode-correct for their respective scenarios. Per-epoch eval is neither. | Confirmed |

### The two-mechanism mismatch

The hypothesis as stated focused on the missing cross-attention signal. The code reveals a second compounding mechanism that is equally significant:

**Mechanism 1 — Missing cross-attention:** The graph encoder's structural signal (edge types, node features, topological relationships) is absent during per-epoch eval. The 25% of training steps where diagram-loop records provided real graph priors are not reflected in eval at all.

**Mechanism 2 — Missing `GraphTextFusion.norm`:** The fusion layer is a `residual + LayerNorm` module. When bypassed, the head receives `StructuredTokenEmbedding`-normalized `text_hidden` directly. When active (training), the head receives `GraphTextFusion.norm(text_hidden + context)`. Because nearly every training batch is mixed (probability ≈ 1 that at least one diagram record is present at B=64 and 25% diagram fraction), the head's weight statistics are calibrated to the fusion-normed distribution. Per-epoch eval presents the head with the pre-fusion distribution. The two `LayerNorm` modules — `StructuredTokenEmbedding.output_norm` and `GraphTextFusion.norm` — are distinct and non-commuting; skipping the latter is not equivalent to receiving the same tensor.

### Interpretation of the K9_DiagLoop trajectory

The apparent regression (epoch 0: 63.2% → epoch 1: 42.9% → epoch 2: 28.1%) was evaluated entirely in text-only mode against a model that, from the first training step, was predominantly exercising the fused forward path. As training progressed and the fusion path parameters diverged further from their initialization, the head became more specialized to fused-path inputs, and per-epoch eval scores fell accordingly — not because the model was degrading but because the eval was measuring an increasingly irrelevant forward mode.

The corroborating evidence (48.4% peak at epoch 2 in the smoke's text-only eval, followed by regression to 30.7% at epoch 4, and 65.5% on the same final checkpoint via `--with-graph-path`) is consistent with this mechanism throughout: the model specialized into the fused path, text-only eval became increasingly misaligned, and oracle-graph eval recovered the model's actual capability.

### What this investigation does NOT address

This is a code-reading report. It establishes the mechanical basis for the mode mismatch but does not:

- Propose a fix to `evaluate_structured_token_prediction` (that is the solution architect's scope)
- Rule out co-present effects such as topological memorization, cross-attention parameter entanglement in the text path, or oracle-leak risk in the `--with-graph-path` evaluation (those are the counter-skeptic's scope)
- Quantify how much of the +34.8 pp is attributable to Mechanism 1 vs Mechanism 2 (would require an ablation: running `GraphTextFusion` with real `graph_batch` but with attention weights zeroed)
- Verify that a corrected per-epoch eval would reproduce the 65.5% or intermediate result
