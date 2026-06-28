# Idea Atlas Spec — Atlas ↔ Diagram Toggle for CAS-Native

**Date:** 2026-05-04
**Author:** scaffold pass (Claude Opus 4.7, 1M context)
**Status:** Draft / scaffold shipped (data model + dashboard skeleton only)
**Implementation tier:** Phase A — data model lock + dashboard scaffold; Phase B
(real reactflow rendering) and Phase C (generation_id wiring through inference)
are downstream.

---

## 1. Motivation

The CAS framework produces structured cognitive predictions. There are two
natural visual representations of one prediction:

1. **Notation / expression diagram** — the compiler-produced typed graph
   (`NoeticCluster`, `StateSet`, `RelationCluster`, recipe graph, RPM chain).
   Already shipped per memory `cas_diagram_and_clusters.md` (Codex
   2026-04-26). Rendered by the existing dashboard at
   `dashboard/src/pages/CompilerPage.tsx` ≈ line 456.

2. **Idea Atlas** — a navigable map of the *Ideas* (per CLAUDE.md authoritative
   `^0` Idea / `^5` Female substrate definitions) the prediction lit up. Not
   yet defined. **This document specifies it.**

The user's vision (verbatim from the task brief): users of the system should be
able to **toggle between two views, both in infinite zoomable space, clickable,
expandable, with 1:1 mapping back to the specific generation that produced
them.**

The two views answer different questions:

* The **diagram** answers *"what compiles from this CAS expression?"* — the
  typed graph the compiler can verify, rendered with set-membership boxes,
  recipe-prerequisite arrows, and RPM chain links.
* The **atlas** answers *"what Ideas did this prediction *light up* — and which
  did it *explicitly not*?"* — the substrate map. Positive space = lit Ideas.
  Negative space = involution-pair shadows of the lit Ideas. The point is to
  surface both the present and the absent.

The toggle is the core UX affordance: same prediction, two complementary
views, switchable in place.

## 2. Atlas data model — IdeaNode, IdeaEdge, IdeaAtlas

Source: `cas-native/atlas/idea_atlas.py`. Pure stdlib, frozen dataclasses,
JSON round-trippable.

### 2.1 IdeaNode

```python
@dataclass(frozen=True)
class IdeaNode:
    id: str                     # unique within the atlas
    label: str                  # human-readable
    noetic: str                 # "^0".."^9"
    domain: str | None          # "P" / "C" / "E" / "O" or None
    drive: str | None           # "F1".."F7" or None
    register: str | None        # "T" / "A" / "f" / "E" or None
    intensity: float            # [0, 1] activation
    is_positive_space: bool     # True = lit; False = involution shadow
    metadata: dict[str, Any]
```

Validation (enforced at construction):

* `noetic` matches `^[0-9]`.
* `domain`, `drive`, `register` either `None` or in their authoritative tuples
  from CLAUDE.md.
* `intensity` ∈ `[0, 1]`.
* `is_positive_space` is exactly `bool` (not truthy str).

Convenience accessors: `noetic_index` (0..9), `noetic_name` (authoritative
`Idea`/`Mind`/.../`Below/Effect`), `is_compound_state` (= domain and drive
both present).

### 2.2 IdeaEdge

```python
@dataclass(frozen=True)
class IdeaEdge:
    source_id: str
    target_id: str
    edge_kind: str
    label: str | None
    metadata: dict[str, Any]
```

`edge_kind` is one of (closed enum, exposed as `EDGE_KINDS`):

| edge_kind | Meaning |
| --- | --- |
| `involution_pair` | `^2↔^3`, `^5↔^6`, `^8↔^9` shadow link |
| `domain_descent` | `P → C → E → O` causation arrow |
| `domain_feedback` | `O → P` feedback signal path |
| `drive_inversion` | `F1↔F7`, `F2↔F6`, `F3↔F5` |
| `rpm_chain` | `A0 → Dn → Wn → Pn` Capability Pathway link |
| `cluster_member` | Set / cluster membership (compiler-derived) |
| `register_co_presence` | `+` operator (Clarification 10) |
| `register_integration` | `×` with explicit emergent (Clarification 10) |
| `recipe_prerequisite` | `Θ` recipe input feeding into `Ω` |
| `production_target` | edge into `Ω` target |
| `trace` | Generic compiler-diagram trace |

### 2.3 IdeaAtlas

```python
@dataclass(frozen=True)
class IdeaAtlas:
    nodes: tuple[IdeaNode, ...]
    edges: tuple[IdeaEdge, ...]
    generation_id: str            # 1:1 mapping to the prediction
    cas_expression: str           # canonical rendered form
    metadata: dict[str, Any]
```

Atlas-level invariants enforced at construction:

1. Every edge's `source_id` and `target_id` reference an existing node `id`.
2. Node `id`s are unique within an atlas.
3. `generation_id` is non-empty.

Helper accessors: `positive_space_nodes`, `negative_space_nodes`, `node_by_id`,
`edges_for_node`, `to_dict`/`to_json`/`from_dict`/`from_json`. `with_metadata`
returns a copy with merged metadata (immutability preserved).

### 2.4 prediction_to_atlas

`cas-native/atlas/prediction_to_atlas.py` walks a 12-key v77 prediction dict
and emits an `IdeaAtlas`. Walk-down semantics:

1. **Primary positive-space node(s).** Always emit the compound state node
   (or bare-Noetic if domain/drive absent). When `register_mode` ∈
   `{co_presence, set_spec, integration}` and `len(registers) > 1`, split into
   N nodes and wire them with `register_co_presence` (for `+` / `set_spec`)
   or `register_integration` (for `×`) edges. This honours CAS v7.7
   Clarification 10.
2. **Involution shadow.** If the lit Noetic is in `{2, 3, 5, 6, 8, 9}` (i.e.
   not a self-dual), emit a negative-space node for the involution partner at
   low intensity (0.18). Emit a single `involution_pair` edge between primary
   and shadow. Self-duals `{0, 1, 4, 7}` produce no shadow.
3. **Ω / production target stub.** When `has_omega` is true, emit an `Ω`
   node (carrier `^0`, since `^0` Idea is the canonical Idea-level emergent
   per CLAUDE.md authoritative definition) and a `production_target` edge
   from each primary node into `Ω`.
4. **Meta-logic stub.** When `has_meta_logic` is true and `meta_relations`
   is non-empty, emit one cluster-stub node per relation + a
   `cluster_member` edge from the primary node. Cluster nodes carry
   `metadata.kind == "cluster"` and `metadata.stub == True` so the
   downstream merger (`trace_mapping.merge_with_diagram`) can replace
   them with real compiler-derived structure.
5. **Domain Descent / Drive inversion** are surfaced as *node metadata*,
   not separate atlas nodes/edges, in v0. When the model later predicts
   multi-domain or multi-drive states, edges will fill in.

Defaults / tuning constants (in `prediction_to_atlas.py`):

```
_PRIMARY_NODE_INTENSITY      = 1.0
_INVOLUTION_SHADOW_INTENSITY = 0.18
_REGISTER_NODE_INTENSITY     = 0.7
_OMEGA_NODE_INTENSITY        = 0.85
```

These are not load-bearing — they're rendering hints, tuned during scaffold
review.

## 3. Diagram data model (referenced)

Source: `api/notation/compiler.py` ≈ line 5045 (`build_diagram`); response
shape includes a `diagram` field exposed at `api/routes/notation.py` ≈
line 37. See `cas_diagram_and_clusters.md` (memory) for the canonical
CAS-expression → geometric-form mapping table.

For the IdeaAtlas toggle, only the parts of the diagram needed for
correspondence-keyed highlighting are typed in the dashboard:

```ts
interface DiagramNode {
  id: string;
  label: string;
  noetic?: NoeticToken;
  domain?: DomainLabel;
  drive?: DriveLabel;
  register?: RegisterLabel;
  kind?: string;
  metadata?: Record<string, unknown>;
}
```

The full compiler-side `DiagramNode` is wider; the atlas toggle ignores the
extra fields.

## 4. The 1:1 mapping — GenerationTrace plumbing

Source: `cas-native/atlas/trace_mapping.py`.

```python
@dataclass(frozen=True)
class GenerationTrace:
    generation_id: str
    timestamp_ms: int
    user_input: str
    prediction: dict[str, Any]
    cas_expression: str
    atlas_node_ids: tuple[str, ...]
    diagram_node_ids: tuple[str, ...]
    metadata: dict[str, Any]
```

Every prediction emits exactly one trace. Both the atlas and the diagram
reference the same `generation_id` (UUID4 hex, 32 chars, no dashes — see
`new_generation_id()`). The trace travels with the prediction:

* The Python predictor returns `(prediction, GenerationTrace)`.
* `cas chat` and `cas predict` print the `generation_id` so the user can
  look up the dashboard entry later.
* The dashboard fetches `GET /trace/<generation_id>` to get the atlas +
  diagram bundle.

Two helpers on top of `GenerationTrace`:

* `trace_from_atlas(atlas, user_input, ...)` — convenience constructor
  used at the boundary between predictor and trace store.
* `correspond_atlas_to_diagram(atlas, diagram_nodes)` — builds the
  `atlas_id → diagram_id[]` correspondence map by keying on
  `(noetic, domain, drive, register)`. Atlas-only nodes (involution
  shadows, `Ω` targets, cluster stubs) end up with empty correspondence
  lists and are surfaced as "atlas-only" in the dashboard tooltip.

## 5. Dashboard toggle UX

Source: `dashboard/src/components/IdeaAtlas/`.

```
IdeaAtlas/
├── InfiniteCanvas.tsx   — reactflow wrapper (skeleton)
├── ViewToggle.tsx       — toggle button group
├── IdeaAtlasView.tsx    — atlas-side render
├── DiagramView.tsx      — diagram-side render
├── types.ts             — TS types matching idea_atlas.py
├── stubs.ts             — STUB_ATLAS / STUB_DIAGRAM / STUB_TRACE
└── index.ts             — barrel re-exports
```

### When does a user toggle?

* The user has a default-view preference (atlas or diagram). New prompts open
  in the preferred view.
* Toggling is one click — toggle button group at the top of the panel,
  beneath the breadcrumb showing the current `generation_id`.
* Keyboard: `T` to toggle when the panel has focus.

### What's preserved across the toggle?

| State | Preserved? | Notes |
| --- | --- | --- |
| `generation_id` | Yes (always) | Both views are *of the same prediction*. |
| Selection | Yes | If atlas node `^3^E_{F2}\|A` is selected, toggling to diagram highlights its corresponding diagram node(s) via `correspondence`. |
| Viewport | Yes (per-view) | atlas viewport stored separately from diagram viewport; switching back restores. |
| Expand/collapse | Yes (per-view) | atlas expand-state and diagram cluster-collapse state are independent. |
| Hover | No | Hover is ephemeral. |

### Click handlers

`AtlasNodeClickEvent` is the canonical click payload, surfaced to the parent
context:

```ts
interface AtlasNodeClickEvent {
  source_view: 'atlas' | 'diagram';
  node_id: string;
  generation_id: string;
}
```

The parent uses this to drill into the prediction: `GET /trace/<generation_id>`
gives the full prediction dict, the user input, and timestamps. The detail
panel surfaces the prediction breakdown (turn_type, expression_family,
transition_kind, register_mode, meta_relations) — the same content as the
existing `idea-atlas/NodeDetailPanel.tsx` (note: lowercase `idea-atlas/`
directory predates this scaffold; the new uppercase `IdeaAtlas/` directory is
the toggle home, and the older `NodeDetailPanel.tsx` may be folded in during
real-rendering Phase B).

## 6. Positive vs negative space rendering

Positive-space nodes (lit by the prediction):

* Full opacity.
* Solid border, color-coded by Noetic (cyan ^2, red ^3, green ^5, etc.; see
  `IdeaAtlasView.tsx` `NOETIC_COLORS` table).
* `intensity` controls glow / size (real renderer).

Negative-space nodes (involution shadows):

* Reduced opacity (~55%).
* Dashed border (signals "absent / could be").
* Same color as their positive-space partner (preserves Noetic identity).
* Tooltip prefix `(absent)` and the `:negspace` suffix on the id.

Edges between positive and negative space carry `edge_kind: involution_pair`
and a label of the form `^N↔^M` (e.g. `^3↔^2`). The renderer draws these as
dashed neutral arrows.

## 7. Compound expression handling

The atlas's data model handles four compound forms:

### 7.1 `+` Register co-presence (Clarification 10)

Prediction: `register_mode = "co_presence"`, `registers = ["A", "f", "T"]`.
Atlas: 3 separate primary nodes, one per register, wired by 2
`register_co_presence` edges (chain layout). Each carries the same
`(noetic, domain, drive)` triple but a distinct `register`. Expression:
`^3^P|A + ^3^P|f + ^3^P|T`.

### 7.2 `×` Cross-register integration (Clarification 10)

Prediction: `register_mode = "integration"`, `registers = ["A", "f", "T"]`,
`has_omega = True`. Atlas: 3 register nodes wired by `register_integration`
edges + an `Ω` emergent node receiving `production_target` edges from each.
Expression: `(^3^P|A × ^3^P|f × ^3^P|T) = Ω`.

### 7.3 Recipe `Θ → Ω`

Prediction stub: `has_omega = True`, prerequisite weights live in
`metadata.recipe`. Atlas: prerequisite nodes feeding into `Ω` via
`recipe_prerequisite` edges (carries `metadata.weight`). v0 wiring is a stub —
real recipe parsing piggybacks on the compiler diagram via
`merge_with_diagram` in a follow-on pass.

### 7.4 Set / cluster constructors (`NoeticCluster`, `StateSet`, …)

Prediction: `has_meta_logic = True`, `meta_relations = ["membership", …]`.
Atlas: cluster-stub nodes with `metadata.kind = "cluster"` and `metadata.stub
= True`. Real cluster nodes are populated by merging with the compiler
diagram (which already supports these per `cas_diagram_and_clusters.md`).

## 8. How this surfaces in `cas chat`

The v1 cas-chat surface (`cas-native/inference/chat.py` and the
`cas predict` CLI in `cas-native/inference/cas_cli.py`) currently emits
predictions but **does not emit a `generation_id`**.

Required wiring (the real change is small, ~30 LOC):

1. In `predict_cas.Predictor.__call__`, after producing the prediction dict,
   call `new_generation_id()` and attach it to the returned bundle:

   ```python
   gid = new_generation_id()
   atlas = prediction_to_atlas(prediction, generation_id=gid)
   trace = trace_from_atlas(atlas=atlas, user_input=text)
   return prediction, trace, atlas
   ```

2. In `chat.py`, print the gid alongside the rendered English:

   ```
   ›  ^3^E_{F2}|A
       Negative · evaluative · F2 · analytical
       gen=b2f4a1e9 · open in dashboard: /atlas/b2f4a1e9c0d34d6c9e2f8a7b1d6e3f04
   ```

   The short prefix (`gen=b2f4a1e9`) is for visual scanning; the full UUID is
   underneath as a clickable URL.

3. In `cas_cli.py` `_cmd_predict`, surface the gid in the JSON output:
   `{"generation_id": "...", "prediction": {...}, "atlas": {...}}`.

4. The dashboard route `/atlas/:generation_id` reads the gid out of the URL,
   fetches `GET /trace/<gid>`, and renders `<IdeaAtlasView atlas={atlas}>` or
   `<DiagramView diagram={diagram}>` keyed on the user's preferred view.

Backwards compatibility: the v1 surface returns `prediction: dict`. The new
surface returns `(prediction, trace)` (or a single dict with a top-level
`generation_id` and an `atlas` sub-dict). To avoid breaking existing callers
(`demo_prompts.py` smoke tests, `eval_semantic_reranker_on_heldout.py`,
etc.), the predictor exposes a parameter `with_trace: bool = False` that
preserves the old shape when False. Only `cas chat` and the dashboard
backend pass `with_trace=True`. See `idea_atlas_completion_2026_05_04.md`
for the assessment.

## 9. Out of scope for this scaffold

* Real reactflow rendering (the components are skeletons that compile but
  don't draw nodes/edges with the library).
* Layout algorithms — atlas layout will likely be radial-by-Noetic with
  involution shadows mirrored, but tuning is a Phase B task.
* The dashboard backend route `/atlas/:generation_id` and `/trace/:gid` —
  these need a server-side trace store (Redis or sqlite). The
  `GenerationTrace.to_dict()` / `from_dict()` JSON shape is the wire
  format.
* generation_id wiring throughout the inference path. See completion doc.
* Persistent atlas history — multi-turn conversation atlases that diff
  against prior turns.

## 10. Integrity / IP framing

Per CLAUDE.md, the atlas does **not** introduce new CAS primitives. The 10
Noetics, 4 Domains, 7 Drives, 4 Registers, 5 Generative Operations remain
unchanged. The atlas is a *visualization* of the existing primitives in their
authoritative form. The Noetic names and definitions used in atlas labels
and tooltips are verbatim from CLAUDE.md / `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
Clarification 1. No public-facing renaming or softening occurs in the atlas
data model or UI scaffold.
