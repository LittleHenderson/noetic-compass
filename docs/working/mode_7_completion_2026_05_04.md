# Mode 7 Network Tracer / Mechanistic Interpretability — Scaffold Completion

**Date**: 2026-05-04
**Author**: Claude Code agent (background scaffold task, ~3-5h budget)
**User ratification**: load-bearing (memory `feedback_user_ratifications_2026_05_04.md`).

## 1. Files written

All paths absolute under `C:\Users\wakil\OneDrive\Desktop\tksCAS\`.

### Spec doc

| Path | LOC |
|---|---|
| `docs\working\mode_7_network_tracer_spec_2026_05_04.md` | 458 |

### Scaffold code

| Path | LOC | Status |
|---|---|---|
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\__init__.py` | 56 | real (PEP-562 lazy re-exports) |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\mechanistic.py` | 560 | data model + `trace_prediction` + 2 renderers (real); the model-driven path falls through to stub when `model is None` |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\activations.py` | 231 | hook lifecycle (stub; deterministic mock activations) |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\attribution.py` | 269 | per-token attribution (stub: uniform) + per-head confidence (real) + capacity allocation (real on mock or real weights) + bottleneck top-K (real) |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\network_summary.py` | 252 | activation summarizer (real) + agreement-matrix rule table (real, 9 rules) + disagreement flagger (real) |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\tests\__init__.py` | 1 | trivial |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\tests\conftest.py` | 57 | self-sufficient package alias + tmp_path fixture |
| `noetic-compass-scaffold\noetic-compass\cas-native\trace\tests\test_trace_smoke.py` | 429 | 34 smoke tests covering all 9 spec-mandated checks plus determinism, label-table conformance, custom tokenizer, capture levels, agreement-matrix invariants |

**Total Python LOC**: 1855 (1426 production + 429 tests).
**Total spec LOC**: 458.

The Python total is slightly over the 1000-1800 target. The overage is in
`mechanistic.py` (560 lines, primarily the markdown renderer and label tables)
and the test file (429 lines, 34 tests). Both are warranted: the markdown
renderer is the human-facing surface and the smoke tests are the verifying
contract for the data model.

## 2. Pytest output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass
configfile: pyproject.toml
plugins: anyio-4.12.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 34 items

cas-native/trace/tests/test_trace_smoke.py::test_trace_prediction_returns_full_shape PASSED [  2%]
cas-native/trace/tests/test_trace_smoke.py::test_trace_prediction_prediction_keys PASSED [  5%]
cas-native/trace/tests/test_trace_smoke.py::test_trace_prediction_label_values_in_canonical_tables PASSED [  8%]
cas-native/trace/tests/test_trace_smoke.py::test_render_trace_markdown_nonempty PASSED [ 11%]
cas-native/trace/tests/test_trace_smoke.py::test_render_trace_markdown_lists_all_heads PASSED [ 14%]
cas-native/trace/tests/test_trace_smoke.py::test_render_trace_json_serializable PASSED [ 17%]
cas-native/trace/tests/test_trace_smoke.py::test_render_trace_json_agreement_pairs_canonical PASSED [ 20%]
cas-native/trace/tests/test_trace_smoke.py::test_stub_attribution_normalized PASSED [ 23%]
cas-native/trace/tests/test_trace_smoke.py::test_stub_attribution_token_count_matches PASSED [ 26%]
cas-native/trace/tests/test_trace_smoke.py::test_empty_input_handled PASSED [ 29%]
cas-native/trace/tests/test_trace_smoke.py::test_empty_input_renders_markdown_safely PASSED [ 32%]
cas-native/trace/tests/test_trace_smoke.py::test_empty_input_renders_json_safely PASSED [ 35%]
cas-native/trace/tests/test_trace_smoke.py::test_capacity_allocation_normalized PASSED [ 38%]
cas-native/trace/tests/test_trace_smoke.py::test_capacity_allocation_all_nonneg PASSED [ 41%]
cas-native/trace/tests/test_trace_smoke.py::test_head_agreement_matrix_symmetric PASSED [ 44%]
cas-native/trace/tests/test_trace_smoke.py::test_head_agreement_matrix_diagonal_one PASSED [ 47%]
cas-native/trace/tests/test_trace_smoke.py::test_head_agreement_matrix_all_in_unit_interval PASSED [ 50%]
cas-native/trace/tests/test_trace_smoke.py::test_bottleneck_top_k_descending PASSED [ 52%]
cas-native/trace/tests/test_trace_smoke.py::test_bottleneck_top_k_dim_indices_unique PASSED [ 55%]
cas-native/trace/tests/test_trace_smoke.py::test_bottleneck_top_k_respects_k PASSED [ 58%]
cas-native/trace/tests/test_trace_smoke.py::test_capture_level_summary_omits_per_token PASSED [ 61%]
cas-native/trace/tests/test_trace_smoke.py::test_capture_level_raw_includes_raw_activations PASSED [ 64%]
cas-native/trace/tests/test_trace_smoke.py::test_capture_level_invalid_raises PASSED [ 67%]
cas-native/trace/tests/test_trace_smoke.py::test_stub_capture_is_deterministic PASSED [ 70%]
cas-native/trace/tests/test_trace_smoke.py::test_different_inputs_produce_different_predictions PASSED [ 73%]
cas-native/trace/tests/test_trace_smoke.py::test_per_head_confidence_in_unit_interval PASSED [ 76%]
cas-native/trace/tests/test_trace_smoke.py::test_stub_diagnostic_emitted_in_no_model_path PASSED [ 79%]
cas-native/trace/tests/test_trace_smoke.py::test_normalized_helper_reports_correctly PASSED [ 82%]
cas-native/trace/tests/test_trace_smoke.py::test_summarize_activations_returns_headline PASSED [ 85%]
cas-native/trace/tests/test_trace_smoke.py::test_build_head_agreement_matrix_handles_empty_prediction PASSED [ 88%]
cas-native/trace/tests/test_trace_smoke.py::test_flagged_disagreements_filters_below_threshold PASSED [ 91%]
cas-native/trace/tests/test_trace_smoke.py::test_head_logit_widths_complete PASSED [ 94%]
cas-native/trace/tests/test_trace_smoke.py::test_custom_tokenizer_threaded_through PASSED [ 97%]
cas-native/trace/tests/test_trace_smoke.py::test_bottleneck_top_k_indices_in_range PASSED [100%]

============================= 34 passed in 0.10s ==============================
```

**34 passed in 0.10s.** Comfortably under the <30s budget.

## 3. Sample mechanistic trace markdown

Generated via:

```python
from cas_native.trace import trace_prediction, render_trace_markdown
trace = trace_prediction(model=None, input_text="Why did you refuse my request?")
print(render_trace_markdown(trace))
```

Verbatim output:

```markdown
# Mechanistic Trace

- Schema: `mechanistic_trace.v1`
- Model: `stub-v0`
- Capture level: `full`
- Timing: forward=0.10ms attribution=0.00ms total=1.47ms

## Prediction

- **turn_type**: `'CLOSE'`
- **expression_family**: `'meta_logic'`
- **transition_kind**: `'repair'`
- **noetic**: `9`
- **domain**: `'O'`
- **drive**: `'F7'`
- **registers**: `['T', 'A', 'f', 'E']`
- **register_mode**: `'integration'`
- **authority**: `'blocked'`
- **has_omega**: `True`
- **has_meta_logic**: `True`

## Activation Summary

_bottleneck_norm=10.19 active_dims=54/64 top_head=register bot_head=transition_kind gap=0.81 [confidence-spread:register>>transition_kind]_

- Bottleneck L2 norm: `10.186`
- Active dims: `54` (sparsity 0.16)
- Most confident head: `register`
- Least confident head: `transition_kind`
- Capacity-dominant head: `transition_kind` (share 0.13)

## Per-Head Confidence

| head | confidence |
|---|---|
| `turn_type` | `0.128` `#.........` |
| `expression_family` | `0.199` `##........` |
| `transition_kind` | `0.115` `#.........` |
| `noetic` | `0.136` `#.........` |
| `domain` | `0.278` `###.......` |
| `drive` | `0.176` `##........` |
| `register` | `0.922` `#########.` |
| `register_mode` | `0.231` `##........` |
| `meta_relation` | `0.687` `#######...` |
| `authority` | `0.358` `####......` |
| `omega` | `0.519` `#####.....` |
| `meta_logic` | `0.519` `#####.....` |

## Capacity Allocation

| head | capacity share |
|---|---|
| `turn_type` | `0.118` `#.........` |
| `expression_family` | `0.075` `#.........` |
| `transition_kind` | `0.128` `#.........` |
| `noetic` | `0.120` `#.........` |
| `domain` | `0.077` `#.........` |
| `drive` | `0.084` `#.........` |
| `register` | `0.086` `#.........` |
| `register_mode` | `0.078` `#.........` |
| `meta_relation` | `0.092` `#.........` |
| `authority` | `0.062` `#.........` |
| `omega` | `0.037` `..........` |
| `meta_logic` | `0.044` `..........` |

## Bottleneck Top-K

| dim | activation |
|---|---|
| `40` | `+1.983` |
| `41` | `-1.967` |
| `39` | `+1.934` |
| `42` | `-1.918` |
| `38` | `+1.884` |
| `43` | `-1.869` |
| `37` | `+1.835` |
| `44` | `-1.819` |

## Per-Token Attribution

| head | `Why` | `did` | `you` | `refuse` | `my` | `request?` |
|---|---|---|---|---|---|---|
| `turn_type` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `expression_family` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `transition_kind` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `noetic` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `domain` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `drive` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `register` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `register_mode` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `meta_relation` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `authority` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `omega` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |
| `meta_logic` | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 |

## Head Disagreements

| head A | head B | agreement |
|---|---|---|
| `expression_family` | `omega` | `0.20` |

## Diagnostics

- `stub_capture_no_model`
- `stub_attribution_uniform`
```

Note three things this sample exhibits:

1. **The `register` confidence is 0.922** while `transition_kind` is 0.115 — this is exactly the
   "uneven head" signal the spec calls out (§4 of the spec). Activation summary surfaces it
   in the headline as `confidence-spread:register>>transition_kind`. On a real model this would
   immediately flag a head trained on too-few examples or losing capacity to a stronger head.
2. **The agreement matrix flags `(expression_family, omega)` at 0.20** — the random stub
   prediction has `expression_family='meta_logic'` and `has_omega=True`, which the rule table
   correctly judges inconsistent. The same logic, on a real prediction, surfaces actual
   semantic disagreements without retraining anything.
3. **Diagnostics surface `stub_capture_no_model` and `stub_attribution_uniform`** — production
   callers can fail-fast on `stub_*` prefixes. This is the contract Mode 7 maintains with
   downstream consumers: a v0 trace is honest about being v0.

## 4. Three follow-on tasks to make Mode 7 real

### Follow-on 1 — Real activation capture & attention rollout (1–2 days)

- Wire `compute_with_hooks` to attach forward hooks on the structured-prediction head's
  backbone module and on the encoder layer immediately upstream.
- Implement attention rollout: per-layer attention matrices, mean across attention heads,
  identity + attention residual, matrix product across layers, extract the row corresponding
  to the pool position.
- Add a single backward pass per head to produce per-head re-weighting of the rollout.
- Test by constructing a `StructuredPredictionHead` directly + a tiny mock encoder; verify
  shapes match captured outputs, per-token sums == 1.0, and that swapping inputs swaps the
  attribution distribution.
- Gate behind a `method="rollout"` flag (already plumbed); leave `method="uniform"` as the
  testing default.

**Where the change lands**: `attribution.py::_rollout_attribution` (already a placeholder)
plus `activations.py::compute_with_hooks` (the model-not-None path).

### Follow-on 2 — Dashboard inspector component (2–3 days)

- React/TypeScript component `dashboard/src/components/MechanisticTraceInspector.tsx`.
- Five widgets (per spec §5.1): per-token attribution heatmap, per-head confidence bars,
  head-agreement matrix upper-triangle heatmap, bottleneck top-K bar chart, capacity
  allocation donut.
- New API endpoint `POST /api/v1/trace_prediction` returning `render_trace_json()`.
- E2E test using a known input + storybook snapshot.

**Where the change lands**: `dashboard/src/components/`, `api/routes/trace.py` (both new).
The Python side is fully ready; the dashboard work is purely a consumer of the v1 schema.

### Follow-on 3 — Capacity-stealing detector (3–5 days)

- Build a "head fingerprint" job that runs `trace_prediction` over an eval set, accumulates
  per-head bottleneck top-K activated dimensions on *correct* predictions, and persists.
- During smoke / regression runs, compare per-prediction traces against the head fingerprint
  and flag predictions where a head's relied-on dimensions have gone silent.
- Surface the flag in CHANGELOG entries + run reports as
  `capacity_stealing_alerts: list[{run, head, missing_dims, predictions_affected}]`.

This is the diagnostic the user explicitly cited ("would have caught the diagloop
capacity-stealing on smoke"). It is the highest-leverage follow-on.

**Where the change lands**: a new `cas-native/trace/fingerprint.py` module + integration into
`cas-native/training/eval_step.py`.

## 5. Honest assessment: would this scaffold survive a thoughtful code review?

**Yes, with two caveats.**

What's strong:

- **The spec doc is concrete.** Data model, API, compute strategy, dashboard handoff, and
  stub vs. real boundaries are all explicit. A reviewer can ask "what does
  `head_agreement_matrix` mean?" and get a 9-rule answer in §4.4 of the spec.
- **The data model is locked.** `MechanisticTrace` is a frozen dataclass with seven fields,
  every one documented. `SCHEMA_VERSION` is in place.
- **The smoke tests cover all 9 spec-mandated checks plus 25 additional invariants**
  (symmetry, diagonals, determinism, custom tokenizer wiring, label-table conformance,
  empty-input safety, capture-level matrix). 34 tests in 0.10s, well under budget.
- **Stubs are honest.** Every stub call adds `stub_<reason>` to `metadata.diagnostics` so
  production callers can fail-fast.
- **No torch import at module load.** The package structure cleanly separates the consumer
  surface (mechanistic.py — pure stdlib + cas_native) from the would-be torch surface
  (activations.py — gated behind `model is not None`). The dashboard / API can import this
  package without pulling in torch.
- **PEP-562 lazy `__init__.py`.** Avoids the conftest-ordering import hazard that was the
  one real bug encountered during scaffolding.

What a reviewer would flag:

- **Per-token attribution is uniform.** This is the v0 stub. The spec is explicit about it
  and the `stub_attribution_uniform` diagnostic flags it on every trace. Still, a reviewer
  will (rightly) ask: "show me the rollout implementation." Follow-on 1 is the answer; the
  scaffold doesn't include that work.
- **Capacity allocation uses mock weights.** When `model is None` (which is always, in v0),
  `compute_capacity_allocation` falls back to deterministic mock weight matrices generated
  from a hash of the head name. This means the capacity numbers in the v0 trace are
  *structurally meaningful but quantitatively meaningless* — they'll vary across heads in
  reproducible ways but they don't reflect a real model's allocation. A reviewer will want
  to see a test that confirms the allocation calculation is correct *given real weights*.
  That test belongs with Follow-on 1.
- **The label tables are duplicated.** `mechanistic.py` keeps its own copy of the 8 label
  tuples from `structured_prediction.py`. The duplication is intentional (to keep the trace
  package torch-free) but a reviewer might ask for a build-time sync test. There's a TODO in
  the spec marking this; concretely it would be a unit test importing both modules and
  asserting the tuples match. I didn't add it because I was told not to import torch in
  trace tests; it should land with Follow-on 1.
- **Agreement-matrix rule table is hand-coded.** 9 rules, narrated in the spec. A reviewer
  would suggest learning the consistency model from the training distribution. The spec
  acknowledges this as a follow-on.
- **The 1855-line total slightly exceeds the stated 1000-1800 budget.** Trade-off:
  `mechanistic.py` (560 lines) carries the bulk of the markdown renderer, the prediction
  decoder, and the field documentation. I judged the over-budget thoroughness worth it for
  a load-bearing surface; a reviewer might trim 50-100 lines from the markdown renderer.

**Net**: this is a scaffold a senior reviewer would accept as a v0 with a clear path to v1.
The data model, spec, and tests are review-ready. The two stubs (attribution, capacity
weights) are clearly marked, well-isolated, and have follow-on owners.

The single thing I would *not* claim: this scaffold proves the diagloop capacity-stealing
detector would have worked. The detector lives in Follow-on 3, and proving it requires
running the eval-set fingerprint job. What this scaffold *does* prove is that the data model
and rendering have all the information that detector needs; the detector becomes a small
addition rather than a rewrite.
