# Idea Atlas Scaffold — Completion Report

**Date:** 2026-05-04
**Author:** scaffold pass (Claude Opus 4.7, 1M context)
**Spec:** `docs/working/idea_atlas_spec_2026_05_04.md`
**Mode:** background, ~3-5 hours of agent compute (actual: under 1 hour;
scaffold scope was tight enough to land in one pass)
**Commit policy:** scaffold did NOT commit per user constraint.

---

## 1. Files written + LOC breakdown

### Python — `cas-native/atlas/`

| File | LOC | Purpose |
| --- | --- | --- |
| `__init__.py` | 52 | Package surface, re-exports |
| `idea_atlas.py` | 520 | `IdeaNode` / `IdeaEdge` / `IdeaAtlas` data model + ontology constants + `new_generation_id` |
| `prediction_to_atlas.py` | 494 | `prediction_to_atlas` — derive atlas from CAS prediction dict |
| `trace_mapping.py` | 258 | `GenerationTrace` + `correspond_atlas_to_diagram` |
| `tests/__init__.py` | 0 | empty package marker |
| `tests/conftest.py` | 25 | minimal sys.path plumbing (avoids torch import) |
| `tests/test_atlas_smoke.py` | 475 | 31 tests covering construction, validation, JSON round-trip, prediction → atlas, trace mapping |
| **Python subtotal** | **1,824** | |

### TypeScript — `dashboard/src/components/IdeaAtlas/`

| File | LOC | Purpose |
| --- | --- | --- |
| `types.ts` | 268 | TS types matching `idea_atlas.py` schema; ontology constants; type guards |
| `InfiniteCanvas.tsx` | 124 | Reactflow wrapper (skeleton; library choice documented) |
| `ViewToggle.tsx` | 145 | Atlas ↔ Diagram toggle component (working buttons, ARIA tabs, generation_id breadcrumb) |
| `IdeaAtlasView.tsx` | 221 | Atlas-side render (skeleton; renders node summaries inside InfiniteCanvas) |
| `DiagramView.tsx` | 200 | Diagram-side render (skeleton; mirrors atlas API for drop-in toggling) |
| `index.ts` | 63 | Barrel re-exports |
| `stubs.ts` | 127 | `STUB_ATLAS` / `STUB_DIAGRAM` / `STUB_TRACE` for backend-less UI testing |
| **TS subtotal** | **1,148** | |

### Docs — `docs/working/`

| File | Purpose |
| --- | --- |
| `idea_atlas_spec_2026_05_04.md` | The spec (motivation, data model, mapping, UX, compound handling, cas-chat surface). |
| `idea_atlas_completion_2026_05_04.md` | This file. |

**Total scaffold LOC: 2,972** (within the requested 1,500-2,500 envelope —
slightly over because the prediction → atlas walker carries thorough docstrings
explaining the per-step semantics; happy to trim if the user wants tighter
modules).

---

## 2. Python pytest output (PASS confirmed)

```
$ python -m pytest cas-native/atlas/tests/ -v --tb=short
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
rootdir: noetic-compass-scaffold/noetic-compass
configfile: pyproject.toml
plugins: anyio-4.12.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False
collecting ... collected 31 items

cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_basic_construction PASSED [  3%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_round_trip PASSED [  6%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs0-ValueError] PASSED [  9%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs1-ValueError] PASSED [ 12%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs2-ValueError] PASSED [ 16%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs3-ValueError] PASSED [ 19%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs4-ValueError] PASSED [ 22%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_node_validation_errors[kwargs5-TypeError] PASSED [ 25%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_edge_self_loop_rejected PASSED [ 29%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_edge_unknown_kind_rejected PASSED [ 32%]
cas-native/atlas/tests/test_atlas_smoke.py::test_idea_edge_round_trip PASSED [ 35%]
cas-native/atlas/tests/test_atlas_smoke.py::test_atlas_validates_edge_endpoints PASSED [ 38%]
cas-native/atlas/tests/test_atlas_smoke.py::test_atlas_rejects_duplicate_ids PASSED [ 41%]
cas-native/atlas/tests/test_atlas_smoke.py::test_atlas_round_trip PASSED [ 45%]
cas-native/atlas/tests/test_atlas_smoke.py::test_atlas_node_lookup PASSED [ 48%]
cas-native/atlas/tests/test_atlas_smoke.py::test_new_generation_id_is_canonical_hex PASSED [ 51%]
cas-native/atlas/tests/test_atlas_smoke.py::test_is_generation_id_rejects_non_uuid PASSED [ 54%]
cas-native/atlas/tests/test_atlas_smoke.py::test_constants_match_authoritative_ontology PASSED [ 58%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_emits_involution_shadow PASSED [ 61%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_self_dual_no_shadow PASSED [ 64%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_renders_canonical_expression PASSED [ 67%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_rejects_bad_noetic PASSED [ 70%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_register_co_presence PASSED [ 74%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_register_integration PASSED [ 77%]
cas-native/atlas/tests/test_atlas_smoke.py::test_prediction_to_atlas_meta_logic_stub PASSED [ 80%]
cas-native/atlas/tests/test_atlas_smoke.py::test_generation_trace_round_trip PASSED [ 83%]
cas-native/atlas/tests/test_atlas_smoke.py::test_generation_trace_with_diagram PASSED [ 87%]
cas-native/atlas/tests/test_atlas_smoke.py::test_generation_trace_uses_atlas_generation_id PASSED [ 90%]
cas-native/atlas/tests/test_atlas_smoke.py::test_correspond_atlas_to_diagram_keyed_match PASSED [ 93%]
cas-native/atlas/tests/test_atlas_smoke.py::test_correspond_atlas_to_diagram_handles_no_match PASSED [ 96%]
cas-native/atlas/tests/test_atlas_smoke.py::test_end_to_end_predict_to_dashboard_payload PASSED [100%]

============================= 31 passed in 0.05s ==============================
```

All 31 tests pass in 0.05 s. Well under the 30-second budget.

TypeScript typecheck: `npx tsc --noEmit -p tsconfig.app.json` returns clean
(no errors, no warnings) on the new IdeaAtlas/ files. (Reactflow library is
not installed; the InfiniteCanvas wrapper is a structural skeleton that
compiles without it. Library install is part of Phase B.)

---

## 3. Sample atlas: `^3^E_{F2}|A`

Source prediction (matches a real entry in `level3_recoverable_full.jsonl`,
id `l3conv-4e7436fcc654`):

```json
{
  "turn_type": "ANSWER",
  "expression_family": "register_state",
  "transition_kind": "state",
  "noetic": 3,
  "domain": "E",
  "drive": "F2",
  "register_mode": "single",
  "registers": ["A"],
  "authority": "admitted",
  "has_omega": false,
  "has_meta_logic": false,
  "meta_relations": []
}
```

`prediction_to_atlas(pred, generation_id="b2f4a1e9c0d34d6c9e2f8a7b1d6e3f04").to_json()`:

```json
{
  "cas_expression": "^3^E_{F2}|A",
  "edges": [
    {
      "edge_kind": "involution_pair",
      "label": "^3↔^2",
      "metadata": {
        "involution_kind": "noetic"
      },
      "source_id": "^3^E_{F2}|A",
      "target_id": "^2^E_{F2}|A:negspace"
    }
  ],
  "generation_id": "b2f4a1e9c0d34d6c9e2f8a7b1d6e3f04",
  "metadata": {
    "prediction": {
      "authority": "admitted",
      "domain": "E",
      "drive": "F2",
      "expression_family": "register_state",
      "has_meta_logic": false,
      "has_omega": false,
      "meta_relations": [],
      "noetic": 3,
      "register_mode": "single",
      "registers": ["A"],
      "transition_kind": "state",
      "turn_type": "ANSWER"
    },
    "schema_version": "idea_atlas_v0.1"
  },
  "nodes": [
    {
      "domain": "E",
      "drive": "F2",
      "id": "^3^E_{F2}|A",
      "intensity": 1.0,
      "is_positive_space": true,
      "label": "^3 Negative ^E _{F2} |A",
      "metadata": {
        "authority": "admitted",
        "domain_descent_position": 2,
        "drive_inversion_partner": "F6",
        "expression_family": "register_state",
        "noetic_name": "Negative",
        "register_mode": "single",
        "turn_type": "ANSWER"
      },
      "noetic": "^3",
      "register": "A"
    },
    {
      "domain": "E",
      "drive": "F2",
      "id": "^2^E_{F2}|A:negspace",
      "intensity": 0.18,
      "is_positive_space": false,
      "label": "(absent) ^2 Positive ^E _{F2} |A",
      "metadata": {
        "involution_kind": "noetic",
        "noetic_name": "Positive",
        "shadow_of": "^3^E_{F2}|A"
      },
      "noetic": "^2",
      "register": "A"
    }
  ]
}
```

Two nodes (primary `^3^E_{F2}|A` lit; involution shadow `^2^E_{F2}|A:negspace`
absent), one `involution_pair` edge between them. The shadow node's
`metadata.shadow_of` field points back to its primary. The dashboard renders
the primary in solid red (`^3` = Negative), the shadow with low opacity and
a dashed border in cyan (`^2` = Positive's color, dimmed).

---

## 4. Sample TypeScript skeleton — ViewToggle component

Verbatim from `dashboard/src/components/IdeaAtlas/ViewToggle.tsx`:

```tsx
/**
 * ViewToggle — switch between the IdeaAtlas view and the notation/diagram view.
 *
 * The toggle is the central UX affordance the user requested: two natural
 * representations of the same prediction, switchable in-place, with state
 * preserved across the toggle (selection, viewport, expand-collapse).
 *
 * State preservation contract (enforced by the parent IdeaAtlasView, not by
 * this component):
 *
 *   1. Viewport transform survives the toggle. If the user has zoomed into
 *      the upper-right of the atlas, switching to diagram view re-fits to
 *      bounds; switching back restores the prior atlas viewport.
 *   2. Selection survives the toggle. If the user has clicked an atlas node
 *      with id "^3^E_{F2}|A", toggling to diagram view highlights the
 *      corresponding diagram node(s) (looked up via
 *      `correspondence[atlas_id]`).
 *   3. The generation_id never changes during a toggle — both views are
 *      *of the same prediction*.
 */

import type { AtlasViewMode } from './types';

export interface ViewToggleProps {
  mode: AtlasViewMode;
  on_change: (mode: AtlasViewMode) => void;
  disabled?: boolean;
  className?: string;
  generation_id?: string | null;
}

const ATLAS_LABEL = 'Idea Atlas';
const DIAGRAM_LABEL = 'Notation / Diagram';

// (BUTTON_BASE / BUTTON_ACTIVE / BUTTON_LEFT / BUTTON_RIGHT styles omitted for brevity)

export function ViewToggle(props: ViewToggleProps) {
  const { mode, on_change, disabled = false, className, generation_id } = props;

  const handle_atlas = () => {
    if (disabled || mode === 'atlas') return;
    on_change('atlas');
  };

  const handle_diagram = () => {
    if (disabled || mode === 'diagram') return;
    on_change('diagram');
  };

  return (
    <div
      className={className ?? 'idea-atlas-view-toggle'}
      role="tablist"
      aria-label="Switch between Idea Atlas and Notation Diagram views"
      style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}
    >
      <div style={{ display: 'inline-flex' }}>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'atlas'}
          aria-controls="idea-atlas-view"
          tabIndex={mode === 'atlas' ? 0 : -1}
          onClick={handle_atlas}
          disabled={disabled}
          style={{ ...BUTTON_BASE, ...BUTTON_LEFT, ...(mode === 'atlas' ? BUTTON_ACTIVE : {}) }}
          data-testid="view-toggle-atlas"
        >
          {ATLAS_LABEL}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'diagram'}
          aria-controls="diagram-view"
          tabIndex={mode === 'diagram' ? 0 : -1}
          onClick={handle_diagram}
          disabled={disabled}
          style={{ ...BUTTON_BASE, ...BUTTON_RIGHT, ...(mode === 'diagram' ? BUTTON_ACTIVE : {}) }}
          data-testid="view-toggle-diagram"
        >
          {DIAGRAM_LABEL}
        </button>
      </div>

      {generation_id ? (
        <span
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            color: 'var(--toggle-trace-fg, #64748b)',
          }}
          title="generation_id (1:1 mapping to the prediction that produced this view)"
          data-testid="view-toggle-generation-id"
        >
          gen={generation_id.slice(0, 8)}
        </span>
      ) : null}
    </div>
  );
}

export default ViewToggle;
```

The toggle:

* Renders two buttons, ARIA `role="tablist"` / `role="tab"`.
* Disables the active button (no-op click on the active view).
* Surfaces the first 8 chars of `generation_id` (e.g. `gen=b2f4a1e9`) as a
  monospaced breadcrumb — the title attribute carries the full UUID.
* `data-testid` attributes for downstream e2e tests.
* No external CSS dependency; all styles inlined with CSS variables for
  themeing.

---

## 5. Three follow-on tasks to make this real

1. **Real reactflow rendering.** Install `reactflow` and replace the
   skeleton bodies of `InfiniteCanvas`, `IdeaAtlasView`, `DiagramView` with
   actual `<ReactFlow>` graphs. Map `IdeaNode` → reactflow `Node` and
   `IdeaEdge` → reactflow `Edge` with custom node/edge types per
   `EDGE_KINDS` (involution_pair = dashed neutral, rpm_chain = solid green,
   register_co_presence = solid pink with `+` label, register_integration =
   diamond-head magenta with `×` label, …). Add layout: radial-by-Noetic
   for atlas, dependency / radial / containment for diagram per the
   compiler's `layout_hint`. ETA: 1-2 days for a competent React engineer.

2. **Dashboard integration — route + context.** Add
   `dashboard/src/pages/AtlasPage.tsx` mounted at `/atlas/:generation_id`.
   The page fetches `GET /trace/<gid>` (server-side lookup), constructs the
   `IdeaAtlasContext`, manages toggle state + viewport per-view + selection +
   correspondence, and feeds props down to the new components. Reuses the
   existing `idea-atlas/NodeDetailPanel.tsx` for the per-node detail
   sidebar (or rebuilds in `IdeaAtlas/NodeDetailPanel.tsx` for cleaner
   separation). ETA: 1 day.

3. **generation_id wiring throughout the inference path.** See section 6 of
   the spec. The change is mechanically small (~30 LOC across `predict_cas.py`,
   `chat.py`, `cas_cli.py`) plus a server-side trace store
   (Redis or sqlite). The trace store needs:
   * `POST /trace` — accept a `GenerationTrace.to_dict()` payload, return 201.
   * `GET /trace/<gid>` — return the trace + atlas + diagram (compiler runs
     server-side on demand, or trace is pre-populated with both).
   * `DELETE /trace/<gid>` — for retention. Default TTL = 7 days.

   ETA: 1-2 days. The biggest risk is back-compat for existing callers (see
   section 6 below).

---

## 6. Honest assessment — does v1 cas-chat (PR #32) need to change?

**Short answer: yes, but the change is small and backwards-compatible.**

### Current state (verified by reading `predict_cas.py`, `chat.py`, `cas_cli.py`)

* `Predictor.__call__(text: str) -> dict` returns the 12-key prediction dict.
  No `generation_id`. No trace.
* `chat.py` prints the rendered English + a `RawCAS` panel with the prediction
  dict. No gid.
* `cas_cli.py` `_cmd_predict` prints either the prediction dict (with
  `--raw`) or the rendered English. No gid.

### Required changes

Three small surfaces:

1. **`predict_cas.py`:** Add an optional `with_trace: bool = False` parameter
   to `Predictor.__call__`. When True, return `(prediction, GenerationTrace,
   IdeaAtlas)`. When False (default), preserve the existing single-dict
   return for back-compat. ~10 LOC.

2. **`chat.py`:** Add a single line printing `gen=<gid8>` beneath the
   rendered-English panel. Optionally add `dashboard:
   /atlas/<full_gid>` as a clickable URL using `rich.console`'s link
   support. ~10 LOC.

3. **`cas_cli.py` `_cmd_predict`:** When `--raw` is passed, wrap the
   prediction dict as `{"generation_id": "...", "prediction": {...},
   "atlas": {...}}`. When `--raw` is not passed, prepend `gen=<gid8>` to
   the rendered English. ~10 LOC.

### Backwards compatibility

* `Predictor("text")` (no `with_trace`) keeps the v1 contract: returns a
  single dict. **No existing caller breaks.**
* `cas predict TEXT` without flags keeps printing rendered English. The
  `gen=<gid8>` prefix is additive and visually subordinate.
* `cas predict TEXT --raw` would change shape (the wrapped form). This is
  technically a v0 → v1 break for `--raw` consumers. Risk assessment: the
  user's smoke harness in `cas-native/inference/eval_semantic_reranker_on_heldout.py`
  and `demo_prompts.py` consume the unwrapped dict directly. **They would
  need a one-line update to read `result["prediction"]` instead of
  `result`.** Acceptable tradeoff — both files are internal.
* The `generation_id` field is additive in JSON — old parsers that don't
  know about it ignore it.

### What does NOT need to change

* The `cas_renderer.render_cas_prediction(prediction)` surface. Atlas does
  not gate rendering.
* The structured-token vocabulary persistence
  (`structured_token_vocab.json`).
* The training loop, eval harness, or checkpoint format. Atlas operates
  strictly post-hoc on prediction outputs.
* Any tests in the broader `cas-native/tests/` suite. The atlas/ package
  is pure stdlib, separately importable, and does not perturb the
  existing torch / transformer modules.

### Net call

The change is **not** a Version A retreat (per memory
`project_version_b_conversational_plan.md`). It's a small additive surface
on top of the existing v1 chat that enables the dashboard to deep-link into
predictions. Effort: ~30 LOC + the trace-store backend (~150 LOC FastAPI
route + sqlite migration). The data model is the load-bearing piece; the
wiring is mechanical.

If the user wants to defer the wiring and keep the scaffold strictly
post-hoc (i.e. the dashboard runs `prediction_to_atlas` on whatever
prediction it has, with a fresh `new_generation_id()` each time, no
trace store), the data model still works — the trace mapping just doesn't
persist across page reloads. That is a legitimate Phase A → Phase B → Phase C
ordering and matches the user's stated preference for parallelization.

---

## 7. Open questions / non-goals flagged for follow-up

* **Multi-turn atlas history.** When `cas chat` accumulates multiple
  predictions in one session, the dashboard's atlas view needs a history
  axis (timeline at the bottom, click to jump). This is a Phase D task — not
  in scope here. The data model already supports it: each turn produces its
  own `GenerationTrace` with its own `generation_id`; the history is just a
  list of traces keyed by `session_id` (which would need to be added to
  `GenerationTrace.metadata`).

* **Atlas vs CAS-Native model output drift.** The atlas is a *deterministic
  function* of the prediction dict. If the model gets better, the atlas
  gets richer automatically (more registers, more meta-relations, more Ω
  bindings). No re-train or schema migration needed.

* **Render perf at scale.** Reactflow handles ~1000 nodes well. A single
  prediction's atlas is small (≤ 10 nodes typically; ≤ 50 even for
  recipe-heavy meta_logic predictions). Multi-turn history with 100 turns
  is potentially ~1000 nodes — still under reactflow's comfort zone, but
  worth measuring before launch.

* **Older `dashboard/src/components/idea-atlas/` directory.** This was
  shipped earlier (see memory `cas_diagram_and_clusters.md` and the older
  `GraphView.tsx` / `NodeDetailPanel.tsx` already present). The new
  `IdeaAtlas/` (uppercase) directory is the toggle home; we did NOT modify
  the older directory per the constraint. Phase B should fold the older
  directory's `NodeDetailPanel.tsx` and `useRippleAnimation.ts` into the
  new structure, then delete the old directory.
