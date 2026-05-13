# Atlas v0 — Thought Tree Viewer Design

**Date:** 2026-05-13
**Author:** Agent A (Atlas v0 Architect)
**Status:** Design handoff. No code. Implementation split across Agents B/C/D.
**Sibling docs:**
- `docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md` (Codex audit — substrate-first ordering)
- `docs/working/cas_trace_schema_v0_2026_05_13.md` (Mode 7 full schema spec)
- `docs/working/mode_7_traceability_design_2026_05_13.md` (Mode 7 traceability)
- `inference/traceability_v0.py` + `inference/thought_tree.py` (live producer)

---

## 1. One-paragraph plain-English summary

Atlas v0 is the **visible Thought Tree viewer** for the Noetic Compass dashboard. The Stage-3 REPL now writes a structured `traceability_v0` JSON blob for every CAS reply and every NL-bridge match. Today that blob lives in `.tmp/cas_explain_*.json`; nothing visual consumes it. Atlas v0 closes that gap: a stakeholder loads a trace file in the browser and sees the user's prompt as the root of a tree, with branches for the model's English answer, the identifiers it copied or missed, the slot pattern, and the confidence band. Click any node and a panel on the right shows the full trace JSON for that node. We are building this **now** because the Amazon-pitch PoC needs one screen that shows non-ML stakeholders — in under five seconds — that every CAS reply walks back to its origin (input → CAS → copy → output). v0 is the smallest UI that proves the trace exists and is real. v1 will add the cinematic flair (3D spin, ghost branches, replay slider).

---

## 2. What exists vs what's missing — file-by-file audit

### 2.1 `dashboard/src/pages/IdeaAtlasPage.tsx` (705 lines)

**What it does today:** owns the Idea-Atlas REPL surface — capture a free-text idea, POST to `/idea_atlas/ideas`, render the resulting `{id, text, cas_expression, ast, …}` list. Has a `ViewMode = 'list' | 'graph'` toggle in the header. Tracks `selectedId`, lazy-fetches edges on graph-mode entry, owns the inversion modal lifecycle.

**Reusable for v0:**
- Page chrome (header band, accent-teal title, dark `#0d1117` shell) — copy-paste pattern.
- The `ViewMode` toggle is the right primitive to extend.
- `selectedId` / `setSelectedId` state — reusable for selecting a Thought Tree node.
- Backend-availability handling (`isBackendMissingError`) — Atlas v0 should fail gracefully too.
- `useRippleAnimation` hook — useful for highlighting "just-loaded" trace.

**NOT reusable for v0:**
- The `Idea` shape (it's about persisted captured ideas, not loaded traces) — Atlas v0 traces are loaded from disk/URL, not from `/idea_atlas/ideas`.
- The speech-capture UI — irrelevant to trace viewing.
- The `apiFetch('/idea_atlas/edges')` lazy-loader — Atlas v0 reads a single trace JSON, not a global edge set.
- The Capture textarea — Atlas v0 has no input form.

**Recommendation:** Atlas v0 extends `ViewMode` to `'list' | 'graph' | 'trace'`. The `trace` view is a third sibling, not a replacement. Existing list + graph stay untouched.

### 2.2 `dashboard/src/components/idea-atlas/GraphView.tsx` (413 lines)

**What it does today:** hand-rolled SVG force simulation (charge + link + center, ~220 ticks), deterministic golden-angle initial layout, golden-angle seed for stability across renders. Colors nodes by CAS-expression heuristic (Ω → violet, Θ → pink, compound `^N^D` → sky, drive → amber, …). Renders nodes as circles with inner dot, hover tooltip via `foreignObject`, animated pulse for `pulseId`, click → `onSelectIdea(id)`.

**Reusable for v0:**
- `colorFromCas()` — directly reusable for Thought Tree node coloring (user_prompt/model_generation nodes carry CAS strings).
- Hand-rolled force simulation logic — **partially reusable**. The Thought Tree has structural parent→child edges, not similarity edges. A force simulation would push siblings apart but ignore the tree depth. For v0, **prefer a top-down or radial dendrogram layout** (deterministic from parent→child traversal); reserve force-directed for v0.5 when ghost branches appear.
- Pulse circle pattern — directly reusable for "just-loaded trace" emphasis.
- Hover tooltip pattern — directly reusable.

**NOT reusable for v0:**
- The force-simulation body itself — wrong layout for a tree.
- The `Idea` / `Edge` interfaces — Thought Tree uses `ThoughtTreeNode` / `ThoughtTreeEdge` from `traceability_v0`.
- Similarity-score edge styling (stroke width ∝ score) — tree edges are uniform.

**Recommendation:** Agent C **writes a new** `ThoughtTreeView.tsx`. It copies the SVG scaffold and color heuristic from `GraphView.tsx` but uses a **deterministic top-down dendrogram** (root at top, children fanned below, depth → y, sibling-spread → x). Force simulation is deferred to v0.5.

### 2.3 `dashboard/src/components/idea-atlas/NodeDetailPanel.tsx` (262 lines)

**What it does today:** right-side slide-in panel (fixed, 360px, animated `translate-x`). Renders an `Idea`: original text, CAS expression (syntax-highlighted), captured timestamp, compiler-fetched structure diagram via `apiFetch('/notation/compile')`, AST in a `<details>` block. Footer has Invert + Delete buttons.

**Reusable for v0 — yes, with caveats:**
- The chrome (slide-in, header, scrollable body, close button) is exactly right.
- The section-based layout (label → content) maps cleanly to trace-node sections.
- The compile-fetch logic should be **suppressed when displaying a trace node** — the trace already carries the structure, no need to re-compile.

**NOT reusable as-is:**
- `Idea` shape — Atlas v0 panel shows a **trace node** (`ThoughtTreeNode`), not an `Idea`.
- Invert + Delete footer — irrelevant for trace viewing (the trace is immutable). Replace footer with a "Copy node JSON" button.

**Recommendation:** Make `NodeDetailPanel` discriminated on its input. Two options:
- **(A) Reuse + extend** — add an optional `traceNode?: ThoughtTreeNode` prop; when present, override the body to render trace fields.
- **(B) Parallel component** — Agent A specs `TraceNodeDetailPanel.tsx` as a sibling; chrome copy-pasted, body trace-specific.

**Choose (B)** for v0 — keeps `NodeDetailPanel` untouched (less merge risk with concurrent Atlas/Inversion work) and the trace node panel can iterate independently. Filed under Agent C's scope (companion to `ThoughtTreeView.tsx`).

### 2.4 `dashboard/src/components/idea-atlas/InversionModal.tsx` (260 lines)

**What it does today:** modal picker for the 7 inversion axes (N, W, F, E, S, A, P); POSTs `/idea_atlas/invert`, previews `inverted_cas`, commits via `onConfirm`.

**Reusable for v0 — no.** Inversion Replay is explicitly v0.5/v1 scope (ghost branches). v0 does not invert traces.

**Recommendation:** Leave untouched. Reference design only — when v0.5 wires Inversion Replay, the axis-picker palette + result-region pattern transfers directly.

### 2.5 `dashboard/src/components/idea-atlas/useRippleAnimation.ts` (97 lines)

**What it does today:** injects a keyframe stylesheet, exposes `rippleClass(id)` that returns an `idea-atlas-ripple-active` class for 700ms after `triggerIdeaId` changes.

**Reusable for v0 — yes, directly.** When a trace finishes loading, ripple the root node. No changes needed.

---

## 3. Atlas v0 scope — IN vs OUT (strict)

### v0 IN (must ship)

1. **Load a `traceability_v0` JSON** from a local file picker (browser `<input type="file">`). MIME-validated; schema-version-checked against `traceability_v0`.
2. **Render the Thought Tree** as an SVG dendrogram (top-down or left-right). Each node is a circle + label; edges are parent→child lines.
3. **Node color by `kind`** — `user_prompt` (slate), `model_generation` (accent-teal), `slot_pattern` (sky), `confidence_marker` (band-dependent: green/amber/red), `identifier_attempt` (emerald = copied, rose = missed).
4. **Click a node** → `selectedNodeId` updates → `TraceNodeDetailPanel` slides in with that node's full JSON record (`id`, `node_key`, `kind`, `role`, `label`, `text`, `axis_attrs`).
5. **Side panel with full trace JSON** — a "Show raw trace" toggle in the header opens a scrollable `<pre>` with the entire trace dict. Mode 7 transparency. Copy-to-clipboard button.
6. **Header strip with trace metadata** — `trace_id` (first 8 chars), `created_at`, `schema_version`, node_count, edge_count. Always visible. NL-bridge badge when `input.input_kind === 'nl_bridge'` showing matched pattern + confidence.
7. **Bundled demo trace** — one canned `traceability_v0.json` shipped in `dashboard/public/demo_traces/` so the page works offline with a "Load demo trace" button. Generated once via `cas chat-stage3` + the Agent-D `atlas-save` subcommand; committed to repo.
8. **Warning-flag badges** — render `confidence.warning_flags[]` as colored chips above the tree (info=slate, warning=amber, error=rose).
9. **Empty state** — page loads with no trace; shows a "Load a trace file" CTA and "Load demo trace" button.
10. **Plain English labels** — section headers, button text, empty-state copy use plain English. No "axis_attrs", no "node_key", no "schema_version" jargon in the chrome (those live inside the raw-trace panel where they belong).

### v0 OUT (deferred — design notes only)

| Feature | Defer to | Why |
|---|---|---|
| Omnidirectional spin / 3D pan | v1 (Three.js track) | Stakeholder demo wants legible-in-2D first |
| Ghost branches (Inversion Replay) | v0.5 | Needs the 7 inversion axes; backend route exists but compose UX is real work |
| Slow-motion replay slider | v0.5 | Needs per-step trace (Mode 7 full), not v0 summary |
| Multi-trace timeline / session view | v0.5 | Needs persistence; v0 is single-trace |
| Three.js / WebGL renderer | v1 | SVG is enough for ≤50-node tree; ship demo this sprint |
| Live WebSocket from REPL | v1 | File loader covers the demo; WS adds infra |
| Edit/annotate trace | never | Traces are immutable observational records |
| Token→atlas zoom | v1 | Needs per-token logits (Mode 7 full) |
| Mechanistic / activation overlay | v1 | Needs hooks + storage |

### Hard-line rejections (any agent proposing these to be redirected)

- No new backend route. v0 reads from disk/URL only.
- No persistence inside the browser (no localStorage of traces). User picks file every time.
- No editing affordances on trace nodes.
- No CAS compile call from inside the Atlas — the trace already has everything.

---

## 4. File structure for v0 — exact paths per agent

```
noetic-compass-scaffold/noetic-compass/
├── cas-native/inference/
│   └── cas_cli.py                                  # Agent D — extend with `atlas-save`
├── dashboard/
│   ├── public/demo_traces/
│   │   └── demo_thought_becoming_action.json       # Agent D commits; Agent B references
│   └── src/
│       ├── lib/
│       │   └── trace.ts                            # Agent B — TS types from traceability_v0 schema
│       ├── components/idea-atlas/
│       │   ├── TraceLoader.tsx                     # Agent B — file picker + URL loader + demo button
│       │   ├── ThoughtTreeView.tsx                 # Agent C — SVG dendrogram renderer
│       │   ├── TraceNodeDetailPanel.tsx            # Agent C — slide-in panel (sibling to NodeDetailPanel)
│       │   └── TraceHeader.tsx                     # Agent C — metadata strip + warning chips
│       └── pages/
│           └── IdeaAtlasPage.tsx                   # Agent C — extend ViewMode to include 'trace'
└── docs/working/
    └── atlas_v0_thought_tree_viewer_design_2026_05_13.md   # this file (Agent A)
```

### Agent split — is it right?

The proposed 4-agent split is good but **needs one tightening**: `TraceHeader.tsx` and `TraceNodeDetailPanel.tsx` were not previously called out — they sit naturally under Agent C (same author as `ThoughtTreeView.tsx`, share trace-rendering vocabulary, all read from `lib/trace.ts`). Confirmed scope:

- **Agent A (this agent):** design doc only.
- **Agent B:** `lib/trace.ts` (Zod- or hand-rolled TS types matching `traceability_v0` schema) + `TraceLoader.tsx` (file picker + optional URL fetch + "Load demo trace" button + schema-version validation + parse-error surface).
- **Agent C:** `ThoughtTreeView.tsx` + `TraceNodeDetailPanel.tsx` + `TraceHeader.tsx` + the `IdeaAtlasPage.tsx` ViewMode extension wiring. Agent C consumes types from Agent B.
- **Agent D:** `cas_cli.py atlas-save` subcommand + the bundled demo trace JSON at `dashboard/public/demo_traces/demo_thought_becoming_action.json`.

**No file-scope overlap.** `IdeaAtlasPage.tsx` is shared territory only in the sense that Agent C adds the third tab — but Agent C's edits are additive (new tab, new viewMode case), not modifications to existing list/graph code.

---

## 5. TraceView mode integration — page composition

`ViewMode = 'list' | 'graph' | 'trace'`. The header tab strip gets a third button labeled `TRACE` between existing LIST and GRAPH (or at the right end — recommend right end so existing muscle memory holds).

### Layout when `viewMode === 'trace'`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Idea Atlas                                  [LIST] [GRAPH] [TRACE]      │
│ Your personal cognitive map.                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ <TraceLoader />                                                         │
│   [Choose trace file]  [Load demo trace]  [Clear]                       │
├─────────────────────────────────────────────────────────────────────────┤
│ <TraceHeader />                                                         │
│   trace_id: a1b2c3d4 | created: 2026-05-13 14:22 UTC | 8 nodes | 7 edges│
│   [NL bridge: pattern_thought_becomes_action (conf 0.86)]               │
│   ⚠ low_coverage  ⓘ slow_decode                                         │
├──────────────────────────────────────────────────┬──────────────────────┤
│                                                  │                      │
│  <ThoughtTreeView />                             │  <TraceNodeDetail    │
│                                                  │      Panel />        │
│    ●  user_prompt                                │                      │
│    │  "^3^P|A"                                   │  (slides in from     │
│    │                                             │   right when a node  │
│    └─● model_generation                          │   is selected)       │
│      │  "principled aversion ..."                │                      │
│      ├─● identifier (copied) "^3^P"              │  Original text       │
│      ├─● identifier (missed) "|A"                │  Kind / Role         │
│      ├─● slot_pattern                            │  Label               │
│      └─● confidence_marker (strong)              │  axis_attrs (JSON)   │
│                                                  │  text (if any)       │
│                                                  │                      │
│                                                  │  [Copy node JSON]    │
└──────────────────────────────────────────────────┴──────────────────────┘
                                          [Show raw trace] (toggle bottom-right)
```

### Behavior

- Empty state when no trace loaded: a single centered card with "Load a trace file" message and the two CTA buttons surfaced from `TraceLoader`.
- The detail panel reuses the slide-in pattern from `NodeDetailPanel.tsx` (proven UX). New component because Idea ≠ trace node — see §2.3 rationale.
- "Show raw trace" toggle reveals a bottom drawer (or full-page overlay) with the JSON pretty-printed. Mode 7 transparency surfaced explicitly.
- When trace loads, the root node gets a ripple pulse (reuse `useRippleAnimation`).

### Why not reuse the existing `NodeDetailPanel.tsx`?

Two reasons (per §2.3): the Idea contract (text/cas_expression/AST/compile_error) and the trace-node contract (kind/role/label/axis_attrs) overlap by ~30% only; forcing them through one component introduces optional-everything noise. Second, `NodeDetailPanel` calls `/notation/compile` on mount — irrelevant for trace nodes and adds a network dep we don't need. Cheaper to write a 180-line sibling than to refactor 262 lines into a discriminated component while three other agents are touching the area.

---

## 6. CLI → Atlas pipeline — how a trace reaches the dashboard

### Two candidate paths

**(a) File upload in browser.** User runs `cas chat-stage3`, types prompt, types `/trace`, copies output to a file, browser file-picker loads it.
- Pros: zero new infra; works on any machine; perfect for the Amazon-pitch laptop demo.
- Cons: a copy step (open `.tmp/cas_explain_*.json`, drag to browser).

**(b) `cas atlas-save` writes to a watched directory; dashboard reads via dev-server endpoint or static mount.** Vite dev server serves `dashboard/public/` statically. If `atlas-save` writes to `dashboard/public/saved_traces/<trace_id>.json` and also updates a `dashboard/public/saved_traces/index.json` listing, the dashboard can fetch the list and let the user click any saved trace.
- Pros: one-click in the browser; matches "live demo" feel.
- Cons: dev-server-only (production has no writable `public/`); needs an index file refresh; "stale list" UX if the file is added while the page is open.

### Recommended v0 path: **(a) primary, (b) secondary**

- **Primary:** `TraceLoader.tsx` ships with a file picker. User runs `cas chat-stage3 --save-trace ~/Desktop/`, drops the produced JSON onto the browser. **Works offline. Works on a stage demo laptop. Works on any reviewer's machine.**
- **Secondary (nice-to-have, same sprint):** Agent D's `atlas-save` defaults to writing to `dashboard/public/demo_traces/saved/<trace_id>.json` AND appending to `dashboard/public/demo_traces/saved/index.json`. `TraceLoader.tsx` adds a "Recent traces" list that fetches `/demo_traces/saved/index.json` when present, falls back silently when not.
- **Tertiary:** URL loader — `TraceLoader.tsx` accepts a `?trace_url=` query param and fetches; useful for sharing specific traces in Slack/issues. Cheap to add (~15 LOC).

### `cas atlas-save` subcommand spec (Agent D's scope)

```
cas atlas-save EXPRESSION_OR_TEXT [--out PATH] [--copy-to-clipboard] [--nl]

Synthesizes a Stage-3 reply, builds the traceability_v0 trace, writes JSON
to disk, and prints the absolute path. With --nl, runs the NL bridge first;
otherwise treats input as a CAS expression for cas-explain.

Default --out:
  - If $CAS_ATLAS_TRACES env var set: $CAS_ATLAS_TRACES/<trace_id>.json
  - Else if dashboard/public/demo_traces/saved/ exists: write there + update index.json
  - Else: ~/.cas_atlas/traces/<trace_id>.json (created on first use)

Examples:
  cas atlas-save "^3^P|A"
  cas atlas-save --nl "explain a thought becoming action"
  cas atlas-save --nl "..." --out ./demo.json --copy-to-clipboard
```

The demo trace at `dashboard/public/demo_traces/demo_thought_becoming_action.json` is generated **once** via `cas atlas-save --nl "explain a thought becoming action" --out dashboard/public/demo_traces/demo_thought_becoming_action.json` and **committed to the repo** so the "Load demo trace" button works on a fresh clone.

---

## 7. Test plan

### Unit tests (this sprint — required for promotion)

| Component | Test file | Coverage target |
|---|---|---|
| `lib/trace.ts` | `lib/__tests__/trace.test.ts` | parses 3 fixture traces (CAS-only, NL-bridge, warning-flagged); rejects malformed schemas; surfaces partial-record errors |
| `TraceLoader.tsx` | `components/idea-atlas/__tests__/TraceLoader.test.tsx` | file picker accepts JSON, rejects non-JSON; demo button fetches `/demo_traces/demo_thought_becoming_action.json`; URL-param loader fires once |
| `ThoughtTreeView.tsx` | `components/idea-atlas/__tests__/ThoughtTreeView.test.tsx` | layout is deterministic from input (snapshot); click fires `onSelectNode(id)`; empty-tree state; coloring matches `kind` |
| `TraceNodeDetailPanel.tsx` | same dir | renders all 4 node kinds; copy-JSON button calls `navigator.clipboard.writeText` |
| `TraceHeader.tsx` | same dir | shows warning chips by severity; truncates trace_id to 8 chars; NL-bridge badge shows pattern when present |
| `cas atlas-save` | `cas-native/tests/test_atlas_save.py` | produces JSON parseable by `lib/trace.ts` types; respects `--out` and env var; round-trip with `build_v0_trace` |

### Integration / Playwright (deferred — v0.5 OK)

- End-to-end: open Idea Atlas, click TRACE tab, click "Load demo trace", verify root + 4-6 child nodes rendered, click model_generation node, verify panel shows generated English. **Skip for v0 promotion; spec for v0.5.**
- Cross-browser: Chromium-only for v0. Firefox + WebKit deferred.

### What's **not** covered

- Real Stage-3 inference invocation in tests (heavy, GPU-only). Use checked-in JSON fixtures instead.
- Network failures on URL loader path (low priority — file-picker is the primary path).

---

## 8. Promotion gates — what "demo-ready" means

Atlas v0 is **demo-ready** when ALL of the following are true:

1. **`cas atlas-save --nl "explain a thought becoming action"`** produces a JSON that loads in the browser without parse errors. (Round-trip works on the demo path.)
2. **All 5 unit-test suites pass** with ≥85% line coverage on each new file.
3. **Cold load → first interactive click is <2 seconds** on a stock laptop (no GPU, no network). SVG dendrogram of ≤50 nodes renders in <100ms.
4. **A human reviewer (Wakil)** loads the demo trace and reports: (a) the tree is legible without explanation; (b) clicking a node always shows useful detail; (c) the warning chips and NL-bridge badge are clear; (d) the "Show raw trace" toggle answers the "where did this come from" question for any node.
5. **No jargon leaks in the chrome.** Per `feedback_plain_language_no_jargon.md`: "node_key", "axis_attrs", "schema_version" appear only inside the raw-JSON drawer, never in tab labels, section headers, or empty states.
6. **The bundled demo trace is committed** and the page is functional with the dev server alone (no API call, no Stage-3 model loaded, no network).
7. **Object traceability holds end-to-end** — every visible piece of information walks back to a field in the JSON. Per `feedback_traceability_is_the_whole_purpose.md`: if a label appears with no source field, it's a bug.

**Soft gates (nice but not blocking v0 promotion):**

- 8. URL-param loader works for at least one shared trace.
- 9. Recent-traces sidebar loads from `index.json` when present.
- 10. Keyboard navigation: arrow keys move selection through siblings/parent/children.

---

## 9. 3-month roadmap — v0.5 and v1

### v0.5 — "the replay lever" (target: +2 weeks after v0 ships)

- **Inversion Replay (ghost branches).** Click a node, pick an inversion axis (N/W/F), the panel POSTs `/idea_atlas/invert`, a ghost branch fades in alongside the original branch showing what the tree would look like with that axis flipped. The original branch dims; user can toggle between original and ghost. UX maps to the existing `InversionModal.tsx` axis picker.
- **Replay slider.** Linear timeline below the tree; dragging it reveals nodes in order of construction (root → user_prompt → model_generation → identifier_attempts in input-position order → slot_pattern → confidence_marker). Drives stakeholder "look, every output has a trace" intuition. Requires per-step ordering, which the v0 trace already provides via flat `nodes[]` order.
- **Multi-trace timeline.** Recent-traces sidebar becomes a session timeline; user steps through 5+ traces with arrow keys. Demonstrates session-level cognitive consistency.
- **Better layout.** If trees grow >50 nodes (real Mode-7-full traces), v0's static dendrogram won't scale. Adopt either (a) collapsible subtrees with default-collapsed beyond depth N, or (b) a real force-directed simulation with structural constraints.

### v1 — "the cinematic atlas" (target: +6-10 weeks)

- **Three.js / WebGL renderer.** Replace SVG with WebGL scene graph. Nodes as spheres, edges as cylinders or splines. Camera orbit + pan + zoom (mouse + touch). Same canonical node identity (`node_key`); v0's color heuristic ports unchanged.
- **Omnidirectional spin.** Free-rotate the tree in 3D space; ghost branches occupy parallel planes, original-vs-ghost is spatial not just visual.
- **Token→atlas zoom.** Scroll-wheel zoom into a single node reveals its sub-trace (per-token positions, slot dynamics, alternates). Requires Mode 7 full schema (per-position lm_logits, p_copy tensors) — explicitly out of v0 scope.
- **Mechanistic / activation overlay.** Per `project_exposure_button_traceability.md` Mode 7: attribution heatmap on each node showing which input tokens / which model layers / which CAS primitives drove the output. Requires activation hooks during inference — Phase 4-class work.
- **Live WebSocket from REPL.** Stage-3 REPL pushes traces to the browser in real time; user sees the tree assembling as the model decodes. Showmanship-level demo. Needs a small websocket server, can ride alongside the FastAPI gateway.
- **SGGS integration.** Once the SGGS spec (`sggs_v2_v3_product_feature_backlog_2026_05_06.md`) lands, the Living Atlas accepts gesture-driven navigation. Out of scope until v1 is solid; the canonical `node_key` makes this drop-in.

### What stays stable across v0 → v1

- The `traceability_v0` schema. v1 adds fields; v0 fields never break.
- The canonical `node_key` / `edge_key` from `thought_tree.py`. Identity carries across renderers.
- The 4-axis CAS color heuristic from `GraphView.colorFromCas`.
- The "every visible label walks back to a trace field" invariant.

---

## 10. Open questions / known risks

1. **Tree layout choice — top-down vs radial vs left-right?** v0 traces have ~5-12 nodes (depth ≤3). Top-down dendrogram is the most legible default. Left-right works better for long English labels. Recommendation: top-down with horizontal label offset; revisit at first ≥30-node real trace.
2. **What happens when a trace has 0 expected identifiers (bare-state expression)?** The thought tree omits `identifier_attempt` children; tree degenerates to root → model_generation → slot_pattern → confidence_marker. Renderer must handle a 4-node tree gracefully. Verified-doable via the schema's `len(expected) > 0` gating.
3. **What if the user loads a non-`traceability_v0` JSON?** `lib/trace.ts` (Agent B) must validate `schema_version === "traceability_v0"` and surface a clear error. Future-schema traces (e.g., `traceability_v1`) should be rejected, not best-effort-parsed.
4. **Where does the demo trace come from on a fresh clone?** Agent D commits it. **This is a real dependency between Agents D and B/C** — if Agent D ships late, B/C can mock with an inline fixture in `TraceLoader.tsx`. Flagged in §11.

---

## 11. Blockers / cross-agent dependencies

- **Agent C blocks on Agent B's `lib/trace.ts`.** Types are needed before rendering. Sequencing: Agent B ships types within 24h; Agent C starts on `TraceHeader.tsx` (lightest of the three components) while waiting.
- **Agent B's "Load demo trace" button blocks on Agent D's committed demo JSON.** Workaround: Agent B ships an inline JSON fixture initially; Agent D replaces it with a real-inference-generated JSON when `atlas-save` lands. Fixture lives in `lib/trace.ts` exports for unit-test reuse anyway.
- **No conflict on `IdeaAtlasPage.tsx`** — Agent C's edits are purely additive (new tab + new viewMode case + new view conditional block). List + graph paths untouched.
- **`InversionModal` and `NodeDetailPanel` stay out of v0.** Any agent proposing edits to them for Atlas v0 work should be redirected — these are Idea-Atlas (Sprint 3) concerns, not trace-viewer concerns.
- **Schema drift risk.** If `traceability_v0.py` evolves while Agent B is mid-task, types go stale. Mitigation: Agent B reads `traceability_v0.py` AND `thought_tree.py` directly and mirrors fields; freeze the schema for the duration of the sprint (no changes to those two files until Atlas v0 ships).

---

## 12. Definition of done — Agent A

- [x] Design doc written at `docs/working/atlas_v0_thought_tree_viewer_design_2026_05_13.md`.
- [x] File-by-file audit of 5 existing components.
- [x] v0 scope IN/OUT enumerated.
- [x] File ownership per agent confirmed.
- [x] CLI → Atlas pipeline specified with primary + secondary paths.
- [x] Test plan and promotion gates laid out.
- [x] 3-month roadmap to v0.5 and v1.
- [x] Cross-agent dependencies and blockers flagged.
- [ ] Commit + report.

End of design doc.
