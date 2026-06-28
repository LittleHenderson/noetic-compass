# Mode 7 Network Tracer / Mechanistic Interpretability Surface — Specification

**Author**: Claude Code agent (background scaffold task)
**Date**: 2026-05-04
**Status**: Scaffold spec; v0 stubs landed in `cas-native/trace/`. Real implementations are follow-on.
**User ratification**: "load-bearing not optional" (memory `feedback_user_ratifications_2026_05_04.md`).
**Related memory**: `project_exposure_button_traceability.md` (7 traceability modes; Mode 7 is the strongest single differentiator).

---

## 1. Motivation

CAS-Native predictions are produced by a multi-headed structured-prediction transformer
(`cas_native.model.structured_prediction.StructuredPredictionHead`). Each prediction is a
12-key tuple (turn type, expression family, transition kind, Noetic, Domain, Drive,
register set, register mode, meta-relations, authority, has_omega, has_meta_logic) emitted
from a shared 64-dim bottleneck via 12 linear heads.

When a prediction is wrong, surprising, or merely interesting, an operator must be able to
ask: **"Why did the model arrive at this answer?"** That is the mechanistic question. The
existing v7.5/v7.6/v7.7 conformance reports answer the **what** (which axis was right,
which was wrong) but never the **why**.

User framing:

> "Mode 7 would have caught the diagloop capacity-stealing on smoke if it existed."

Concretely, the diagram-encoder PR-#6 K9_DiagLoop work
(`project_pr6_diagloop_smoke_2026_05_03`, `project_deepseek_revised_diagnosis_2026_05_03`)
demonstrated that a graph-channel addition can simultaneously lift one head (Noetic +13.7pp)
while hammering another (canonical −14pp). That is *capacity stealing* — bottleneck dimensions
get re-purposed in ways that benefit one head at the expense of others. With Mode 7, this
shows up as a visible head-agreement matrix asymmetry and a re-distribution of the bottleneck
top-K activated dimensions across heads. Without Mode 7, it shows up only as a
post-hoc per-head metrics regression on a downstream eval — by which point the run is already
spent.

The Mode 7 thesis: a per-prediction mechanistic trace, computable in O(forward pass +
hooks), surfaced as a JSON record and human-readable markdown, would change the failure
mode from "spent run, retroactive diagnosis" to "single smoke prediction, immediate
diagnosis."

This is the same reason mechanistic interpretability has become load-bearing for frontier
labs: opacity at scale is not an inconvenience, it is a regulatory and product risk. Noetic
Compass markets itself on the inverse: every prediction is auditable, every axis traceable,
every disagreement visible. Mode 7 is where that promise grounds.

## 2. Data model

### 2.1 The `MechanisticTrace` record

```python
@dataclass(frozen=True)
class MechanisticTrace:
    prediction: dict           # The 12-key structured prediction
    per_token_attribution: dict[str, list[float]]
                               # head_name -> per-input-token contribution, sums to 1.0
    per_head_confidence: dict[str, float]
                               # head_name -> softmax max (scalar) or
                               # mean(sigmoid) (multi-label)
    head_agreement_matrix: dict[tuple[str, str], float]
                               # (head_a, head_b) -> agreement score in [0, 1]
    bottleneck_top_k: list[tuple[int, float]]
                               # top-K (dim_index, activation) pairs from the 64-dim
                               # shared backbone output (the post-LayerNorm "z" vector)
    capacity_allocation: dict[str, float]
                               # head_name -> share of bottleneck capacity used by
                               # this head, in [0, 1], sums to 1.0 across heads
    metadata: dict             # capture_level, model_id, input_text, token_count,
                               # timing, schema_version, hook_status,
                               # diagnostics (warnings)
```

### 2.2 Field-by-field semantics

**`prediction`** — the same 12-key dictionary that
`StructuredPredictionHead.propose()` returns, JSON-rendered. This is the *what*. The other
fields explain it.

**`per_token_attribution`** — for each of the 12 heads, a list of length `token_count`
giving the relative contribution each input token made to that head's argmax/threshold
decision. Stored normalized to sum to 1.0 per head (so heads are comparable). Computation
strategy in §4. The dashboard renders this as a small heatmap: rows = heads, columns =
tokens.

**`per_head_confidence`** — for scalar heads (turn_type, noetic, domain, drive,
register_mode, authority, has_omega, has_meta_logic, meta_relation argmax,
expression_family, transition_kind), softmax max. For multi-label heads (registers,
meta_relations), mean of the sigmoid scores for active labels (or 0.0 if none). One float
per head, in [0.0, 1.0]. Dashboard renders as a small bar chart.

**`head_agreement_matrix`** — pairwise agreement between heads on shared CAS axes. Two
heads "agree" when their predictions are consistent under the v7.7 ontology. Examples:

- (`noetic`, `expression_family`): a noetic-3 prediction with `expression_family=production`
  is fine (productions can have any noetic); but `expression_family=meta_logic` with
  `noetic=2` is mildly suspect (meta-logic constructs typically anchor on `^0` or `^1`).
- (`register_mode`, `registers`): if `register_mode=integration` then `len(registers) >= 2`
  is required; else this is a structural disagreement.
- (`has_omega`, `expression_family`): `has_omega=True` is consistent with
  `expression_family in {production, omega}` and inconsistent otherwise.

The matrix entry is a continuous score in [0.0, 1.0] computed by a rule table (v0 stub)
or learned from the training distribution (follow-on). Diagonal entries are always 1.0. The
matrix is symmetric. The dashboard renders as a small upper-triangle heatmap; cells with
score < 0.5 are flagged.

**`bottleneck_top_k`** — the top-K activated dimensions of the shared 64-dim post-backbone
hidden state `z` (the output of `self.backbone(pooled)`). For v0, K=8. Each entry is
`(dim_index, activation_value)`. This surfaces *which subspace* of the bottleneck this
prediction lives in. Capacity-stealing detection: track which dimensions consistently
activate for each head's correct predictions, then flag when those dimensions go silent on
a wrong prediction.

**`capacity_allocation`** — per-head capacity share. Computed as the L2-norm of the per-head
linear weight projection of the current `z` vector, normalized across heads. Interpretation:
"how much of this prediction's bottleneck activation is being read by each head?" If one
head dominates capacity (>50% share), other heads are likely under-supported and may be
producing low-confidence guesses. Sums to 1.0. The dashboard renders as a small donut chart.

**`metadata`** — provenance and observability:

- `schema_version`: `"mechanistic_trace.v1"`
- `model_id`: opaque string; `"stub-v0"` when the trace is generated without a real model
- `input_text`: original input string
- `token_count`: number of tokens in `per_token_attribution[*]`
- `capture_level`: one of `{"summary", "full", "raw"}` (see §3)
- `timing`: `{"forward_ms": float, "attribution_ms": float, "total_ms": float}`
- `hook_status`: `{"pre_bottleneck_captured": bool, "post_bottleneck_captured": bool, ...}`
- `diagnostics`: list[str] of human-readable warnings (e.g.
  "stub_attribution_uniform: real integrated gradients not run")

### 2.3 Schema version

`mechanistic_trace.v1`. Bump on any breaking change to the data model. Dashboard consumers
must check `schema_version` and tolerate forward-compatible additions.

## 3. Public API

```python
# cas_native.trace.mechanistic
@dataclass(frozen=True)
class MechanisticTrace: ...

# cas_native.trace.mechanistic
def trace_prediction(
    model: Any,                # nn.Module with structured-prediction head, OR None for stub
    input_text: str,
    *,
    capture_level: str = "full",   # "summary" | "full" | "raw"
    top_k: int = 8,
    tokenizer: Any | None = None,  # callable: str -> list[str]
) -> MechanisticTrace:
    """Run the model, capture activations, compute a mechanistic trace."""

# cas_native.trace.mechanistic
def render_trace_markdown(trace: MechanisticTrace) -> str:
    """Human-readable markdown rendering for the audit log / report."""

# cas_native.trace.mechanistic
def render_trace_json(trace: MechanisticTrace) -> dict:
    """JSON-serializable dict for the dashboard / API consumer."""
```

**Capture levels:**

- **`summary`** — top-K bottleneck only, capacity allocation only, no per-token
  attribution; cheapest. Used in production endpoints when latency budget is tight.
- **`full`** — everything in §2.1. Default. The level the dashboard renders.
- **`raw`** — `full` plus `metadata["raw_activations"]`: a numpy-encoded copy of the
  pre- and post-bottleneck activation tensors. Used only by interpretability researchers;
  significantly inflates trace size.

## 4. Compute strategy

### 4.1 Activation capture

Use `torch.nn.Module.register_forward_hook` to attach hooks at three points:

1. **Pre-bottleneck**: on the model's last hidden-state-producing module (the layer
   immediately before the structured-prediction head). Captures the
   `(B, seq_len, d_model)` tensor that gets pooled.
2. **Post-pool, pre-backbone**: on the structured-prediction head's `_pool` boundary.
   Captures the `(B, d_model)` mean-pooled vector.
3. **Post-backbone**: on `head.backbone` (the `Sequential(Linear, GELU, LayerNorm)`).
   Captures the `(B, bottleneck_dim)` `z` vector that feeds all 12 heads.

Hooks are attached, the forward pass runs, the captured tensors are detached and stashed,
and the hooks are removed. `attribution.py::compute_with_hooks()` is the helper that does
this lifecycle.

### 4.2 Per-token attribution

**Choice for v1: attention rollout.** Attention rollout is cheap (no extra forward passes,
no gradient computation), is well-understood, and works without retraining. The trade-off:
attention rollout is a known imperfect proxy for true causal attribution
(Abnar & Zuidema 2020); it answers "which tokens did the model attend to?" not "which
tokens caused this output?"

**Why not integrated gradients**: integrated gradients (Sundararajan et al. 2017) are more
faithful but require N forward passes (N=20-50 typical) per trace. At our latency targets
(<500ms single assessment), this is borderline; we'd need to either accept a 10-50x latency
hit or compute IG asynchronously. For v1, attention rollout is the right pragmatic choice.

**Attribution upgrade path**: when latency budget allows or for offline batch tracing,
swap attention rollout for IG. The function `attribution.compute_per_token_attribution()`
takes a `method: str = "rollout"` argument that future versions can extend with `"ig"` and
`"shap"`.

For multi-head attribution: rollout produces a `(seq_len, seq_len)` attention matrix per
layer per head; we collapse across attention heads (mean), across layers (matrix product —
the rollout), and then take row 0 (or the position of the [CLS]/[POOL] token) to get
per-token contribution to the pooled representation. We then re-weight per structured-head
by the structured-head's gradient w.r.t. `z` (single backward pass; this is the only
backward pass we run).

**v0 stub**: `compute_per_token_attribution()` returns a uniform distribution
(`1.0 / token_count` for each token). This is correctly-shaped and lets the dashboard
develop against the schema before real attribution lands. The `metadata["diagnostics"]`
list flags `"stub_attribution_uniform"` so consumers know it's not real.

### 4.3 Per-head confidence

For each scalar head, `softmax(logits).max()`. For multi-label heads, mean of `sigmoid(logits)`
across the active labels (those above the threshold) or `sigmoid(logits).max()` if no labels
are active. Direct from `head.forward()` outputs; no extra computation.

### 4.4 Head agreement matrix

A rule table over the 12-key prediction. v0 implements 9 hand-coded rules (see
`mechanistic.py::_build_agreement_matrix()`), each producing a [0.0, 1.0] score for one
head pair. Rules:

- (`register_mode`, `registers`): mode-set consistency (e.g. `single` requires len==1).
- (`expression_family`, `has_omega`): omega-bind requires `production` or `omega` family.
- (`expression_family`, `has_meta_logic`): meta_logic family ↔ has_meta_logic.
- (`transition_kind`, `expression_family`): meta_logic_move requires meta_logic family.
- (`turn_type`, `transition_kind`): REFUSE turns shouldn't surface_act = ANSWER.
- (`authority`, `turn_type`): REFUSE_CLAIM should be admitted=blocked.
- (`noetic`, `domain`): all combinations allowed (40 states); 1.0.
- (`drive`, `domain`): all combinations allowed (28 domain-drives); 1.0.
- (`registers`, `register_mode`): integration requires len>=2.

Pairs not in the rule table get score 1.0 (no judgment). Diagonal is always 1.0.

The matrix is symmetric; we store only the (a, b) where `a < b` and rebuild on access.
Follow-on: replace rule table with a learned consistency model trained on the training
distribution.

### 4.5 Bottleneck top-K

Direct: `torch.topk(z.abs(), k=top_k)` over the 64-dim `z` vector. Return as
`list[tuple[int, float]]` sorted by `|activation|` descending, where the float is the
*signed* activation (so consumers can see polarity).

### 4.6 Capacity allocation

For each head's linear layer `head_h: Linear(bottleneck_dim, num_classes)`, compute
`||head_h.weight @ z||_2` and normalize across the 12 heads. Interpretation: "how much
signal is being read by each head from the current bottleneck activation?" Sums to 1.0.

In the v0 stub (no model), this is computed from a fixed mock weight matrix so the smoke
test exercises the same shape.

## 5. UI / dashboard handoff

### 5.1 Render targets

The dashboard `cas-native trace inspector` view consumes `render_trace_json()` output and
renders four widgets:

1. **Per-token attribution heatmap** — y-axis: 12 head names; x-axis: input tokens;
   cell color: attribution value (0.0 white → 1.0 dark). Tooltip: exact value + token
   string.
2. **Head confidence bar chart** — bar per head, height = confidence, color-coded:
   green ≥0.7, yellow 0.4–0.7, red <0.4.
3. **Head agreement matrix** — upper-triangle heatmap, 12×12, cell color: agreement
   score (1.0 green → 0.0 red). Cells <0.5 flagged with an icon.
4. **Bottleneck top-K bar chart** — bar per top-K dim, height = `|activation|`,
   color = sign (positive blue, negative orange).
5. **Capacity allocation donut** — donut chart, slice per head, slice size =
   capacity share.

### 5.2 JSON schema for dashboard consumption

```json
{
  "schema_version": "mechanistic_trace.v1",
  "prediction": { /* 12-key structured prediction */ },
  "per_token_attribution": {
    "turn_type": [0.12, 0.34, 0.18, 0.36],
    "noetic":    [0.05, 0.40, 0.45, 0.10],
    /* ...12 heads total... */
  },
  "per_head_confidence": {
    "turn_type": 0.91,
    "noetic":    0.74,
    /* ...12 heads total... */
  },
  "head_agreement_matrix": [
    {"a": "register_mode", "b": "registers", "score": 0.95},
    {"a": "expression_family", "b": "has_omega", "score": 1.0},
    /* ...all pairs the rule table judges... */
  ],
  "bottleneck_top_k": [
    {"dim": 17, "activation": 2.13},
    {"dim": 42, "activation": -1.87},
    /* ...top-K total... */
  ],
  "capacity_allocation": {
    "turn_type": 0.11,
    "noetic":    0.18,
    /* ...12 heads total, sums to 1.0... */
  },
  "metadata": {
    "schema_version": "mechanistic_trace.v1",
    "model_id": "stub-v0",
    "input_text": "...",
    "token_count": 4,
    "capture_level": "full",
    "timing": {"forward_ms": 0.0, "attribution_ms": 0.0, "total_ms": 0.0},
    "hook_status": {"pre_bottleneck_captured": false, "post_bottleneck_captured": false},
    "diagnostics": ["stub_attribution_uniform"]
  }
}
```

### 5.3 Dashboard wire-up (out of scope for v0)

The dashboard component lives at `dashboard/src/components/MechanisticTraceInspector.tsx`
(to be created in follow-on). It is a pure consumer of the JSON schema above; it does not
call into Python.

## 6. Stub vs Real

| Component                  | v0 stub status                              | Real implementation owner |
|----------------------------|----------------------------------------------|---------------------------|
| `MechanisticTrace` model   | **Real** — final shape locked              | n/a                       |
| `trace_prediction(model, ...)` | **Stub** — returns deterministic mock if model is None; real path runs hooks and computes per-head outputs | follow-on PR              |
| `compute_per_token_attribution` | **Stub** — uniform 1/n                  | follow-on PR (rollout)    |
| `compute_with_hooks`       | **Stub** — captures shapes only             | follow-on PR              |
| `summarize_activations`    | **Real** — pure-stdlib summarizer; works on stub or real activations | n/a                       |
| `_build_agreement_matrix`  | **Real** — 9-rule table                    | follow-on (learned model) |
| `compute_capacity_allocation` | **Real on mock weights, real-ready**     | n/a — will work on a live model when `model.named_modules()` exposes the heads |
| `render_trace_markdown`    | **Real**                                    | n/a                       |
| `render_trace_json`        | **Real**                                    | n/a                       |
| Smoke tests                | **Real**, exercise stub end-to-end          | n/a                       |
| Dashboard component        | **Out of scope**                            | follow-on PR              |

The stub flag set on every stubbed call:
`metadata["diagnostics"]` accumulates `"stub_<reason>"` strings. Production callers that
require real traces should fail-fast on any `stub_` prefix in diagnostics.

## 7. Test plan

### 7.1 Smoke tests (this PR)

`tests/test_trace_smoke.py`:

1. `test_trace_prediction_returns_full_shape` — call with `model=None`,
   `input_text="hello world"`, assert all required fields present.
2. `test_render_trace_markdown_nonempty` — assert returned markdown is non-empty,
   contains the prediction summary, and contains a section for each widget.
3. `test_render_trace_json_serializable` — assert `json.dumps(render_trace_json(t))`
   succeeds.
4. `test_stub_attribution_normalized` — assert per-token attribution sums to 1.0 ± 1e-6
   for each head.
5. `test_empty_input_handled` — `input_text=""` returns a trace with `token_count=0`,
   empty per-token-attribution lists, and `"empty_input"` diagnostic.
6. `test_capacity_allocation_normalized` — sum to 1.0 ± 1e-6.
7. `test_head_agreement_matrix_symmetric_and_diagonal_one` — diagonal == 1.0; (a,b) ==
   (b,a) when both are populated.
8. `test_bottleneck_top_k_descending` — top-K returned descending by `|activation|`.
9. `test_capture_level_summary_omits_per_token` — summary level returns empty per-token
   attribution but populated bottleneck top-K and capacity allocation.

### 7.2 Integration tests (follow-on)

To land with the real implementation:

- Construct a `StructuredPredictionHead` directly, run `trace_prediction(head, ...)`,
  verify shapes match the head's output.
- Smoke a known-misaligned prediction (deliberately mis-train one head) and verify
  the agreement matrix flags the disagreement and the bottleneck top-K shifts.
- Compare attention-rollout attribution against integrated-gradients on a small fixture;
  expect Spearman correlation > 0.5 (rough sanity bound).

## 8. Performance

Latency budget (single assessment, capture_level=full):

- Forward pass: model-dependent, target <100ms (already within existing budget).
- Hook overhead: <2ms.
- Attention rollout: <5ms (matrix multiplies over precomputed attentions).
- Per-head capacity: <1ms.
- Markdown render: <5ms.
- **Total trace overhead vs untraced prediction: target <15ms.**

For batch traces (1000 predictions), use `capture_level=summary` and emit a single
aggregated trace per batch with summary statistics. Per-prediction full traces are an
opt-in flag.

## 9. Compatibility & legal

Mode 7 is a *capture and rendering* layer over existing CAS-Native model outputs. It
introduces no new CAS primitives — the 40 Cognitive States, 7 Drives, 4 Registers, and
5 Generative Operations remain unchanged. The trace surface exposes information about how
the model arrives at predictions; it does not redefine what those predictions mean. No IP
attorney consultation flagged for v0; if Mode 7 grows to expose internal weight inspection
or model-card style disclosures, route through standard legal review at that point.

The trace data model is designed for downstream regulator consumption (EU AI Act
Article 13 transparency obligations, NIST AI RMF MEASURE function): per-prediction
traceability of which inputs influenced which outputs is exactly the artifact that surface
satisfies.

## 10. Follow-on tasks

These three blocks of work move Mode 7 from scaffold to real:

### Follow-on 1: Real activation capture & attention rollout (effort: 1–2 days)

- Wire `compute_with_hooks` to attach forward hooks on the structured-prediction head
  backbone and collect pre/post-bottleneck activations.
- Implement attention-rollout in `attribution.py` (collapse across attention heads, take
  matrix product across layers, extract row corresponding to pool position).
- Wire per-head re-weighting via a single backward pass on each head's loss.
- Smoke against a freshly-initialized `StructuredPredictionHead` instance + a tiny mock
  encoder; verify shapes match and per-token sums == 1.0.

### Follow-on 2: Dashboard inspector component (effort: 2–3 days)

- React/TypeScript component `MechanisticTraceInspector.tsx` rendering the 5 widgets.
- API endpoint `POST /api/v1/trace_prediction` taking input_text + capture_level,
  returning `render_trace_json()` output.
- E2E test: send a known input, verify the returned JSON matches the schema, render the
  component in storybook.

### Follow-on 3: Capacity-stealing detector (effort: 3–5 days)

- Track bottleneck top-K activated dimensions per head's *correct* predictions across an
  eval set; persist to a "head fingerprint."
- During smoke / regression runs, compare per-prediction traces against the head
  fingerprint and flag predictions where the dimensions a head usually relies on are
  silent. This is the diagnostic that would have caught the diagloop regression at smoke
  time.
- Surface the flag in CHANGELOG entries and the run report as
  `capacity_stealing_alerts: list[{run, head, missing_dims, predictions_affected}]`.

## 11. References

- `cas_native/model/structured_prediction.py` — the head Mode 7 traces.
- `cas_native/runtime/runtime_frame.py` — sister concept for runtime salience tracing;
  Mode 7 is the *neural* sibling of `TransitionTraceRecord`.
- Memory `project_exposure_button_traceability.md` — full 7-mode framework.
- Memory `feedback_user_ratifications_2026_05_04.md` — user explicit ratification.
- Memory `project_pr6_diagloop_smoke_2026_05_03.md` — failure mode Mode 7 catches.
- Memory `project_deepseek_revised_diagnosis_2026_05_03.md` — three-bottleneck framing.
