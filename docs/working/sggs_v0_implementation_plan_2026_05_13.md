# SGGS v2/v3 — Implementation Plan (Phase 1 / Phase 2 / Phase 3)

**Date:** 2026-05-13
**Author:** SGGS Agent A (Implementation Architect)
**Status:** Implementation handoff. Companion to `sggs_v2_v3_product_feature_backlog_2026_05_06.md` (the canonical spec); this doc translates that spec into a 12-week-by-12-week schedule with named owners, deliverables, and gates.
**Sibling docs:**
- `docs/working/sggs_v2_v3_product_feature_backlog_2026_05_06.md` — canonical spec (libraries, gestures, risks, demo scenario)
- `docs/working/atlas_v0_thought_tree_viewer_design_2026_05_13.md` — Atlas v0 design (what shipped)
- `docs/working/sggs_stream_protocol_2026_05_13.md` — to be written by Agent D (Phase 2 streaming contract)

**Memory anchors:**
- `project_sggs_implementation_started_2026_05_13.md` — captures the deferral override.
- `sggs_v2_v3_backlog_pointer.md` — superseded as a "don't implement" gate, still authoritative on libraries/gestures/streaming granularity.

---

## 1. Why this exists now

User explicitly overrode the prior `DO NOT IMPLEMENT until v0 ships + paper landed + stakeholders ask + inference server decided` gate from the canonical spec (`sggs_v2_v3_product_feature_backlog_2026_05_06.md` lines 178-186) on 2026-05-13 after seeing the `teleclaudius.bles-software.com/spatial-gesture-graph` reference implementation cited at line 61 of the spec and saying "this is how I expect it to look like." User chose the full SGGS v2/v3 build path knowing it pushes Stage 4 / Mode 7 mechanistic attribution / Inversion Replay further back. The override is captured in memory at `project_sggs_implementation_started_2026_05_13.md`. Atlas v0 has shipped (commit `f5c053d` 2026-05-13) — the 2D SVG `ThoughtTreeView`, `TraceLoader`, `atlas-save` CLI, smooth pan/zoom, color-coded edges, fullscreen toggle, and 14-node Θ-recipe demo trace are all in. The Python side ships `traceability_v0` with NL bridge metadata. SGGS builds **on top of** that foundation — it does not replace it.

---

## 2. What ships at the end of Phase 1

A stakeholder loads a `traceability_v0` JSON file (the same file Atlas v0 consumes), clicks the new TRACE-3D tab in the dashboard, and gets:

1. **A 3D scene** of the thought tree — nodes as palette-colored spheres or rounded boxes, edges as splines or thin cylinders, deterministic layout from the existing `ThoughtTreeNode.id` → parent chain.
2. **Orbit camera with mouse drag** (left-button orbit, right-button pan, scroll-wheel zoom) — the keyboard/mouse parity path required by spec line 140.
3. **Click-to-select** with the existing `TraceNodeDetailPanel` (Atlas v0 component) sliding in unchanged from the right.
4. **Webcam-pinch zoom** (two-hand pinch-spread) via MediaPipe Hands. Opt-in — the page works with webcam off.
5. **Fist-spin rotation** of the scene's yaw via the same MediaPipe pipeline.
6. **One-hand pinch node-drag** as the third core gesture.
7. **Accessibility parity** — every gesture has a mouse + keyboard equivalent. Spec line 140 is a hard requirement, not aspirational.
8. **The same 14-node Θ-recipe `DEMO_TRACE_COMPLEX` fixture** as the smoke test. If the Atlas v0 demo trace renders correctly in 2D, the SGGS scene renders the same tree in 3D from the same JSON.

What does **not** ship in Phase 1: live streaming, rewind, slow-motion, timeline scrubber, IntentIR live parsing, Mode 6/Mode 7 overlays, or multi-trace timelines. Those are Phase 2 (live + rewind) and Phase 3 (counterfactuals + persistence + mobile + VR/AR).

---

## 3. File ownership map

### NEW — full ownership

| File | Owner | Purpose |
|---|---|---|
| `dashboard/src/components/idea-atlas/SggsScene.tsx` | **Agent B** | Three.js scene component. Consumes `AtlasTrace` from `lib/trace.ts`, renders 3D thought tree, exposes `onNodeClick`, `selectedNodeId`. Mirrors `ThoughtTreeView` API so swapping is one-line in `IdeaAtlasPage.tsx`. |
| `dashboard/src/components/idea-atlas/SggsScene.test.tsx` | **Agent B** | Jest + @testing-library/react smoke: renders without crashing, calls `onNodeClick` when a node is clicked (programmatically), respects `selectedNodeId` prop. WebGL is mocked via `vi.mock('three')` or jsdom-compatible stub. |
| `dashboard/src/lib/sggs_hands.ts` | **Agent C** | MediaPipe Hands wrapper. Exposes a single `createHandTracker({ video, onGesture })` factory. Emits typed gesture events: `{ kind: 'pinch' \| 'fist_spin' \| 'two_hand_zoom', value: number, hand: 'left' \| 'right' }`. Privacy-preserving — runs on local `<video>` element only. |
| `dashboard/src/components/idea-atlas/HandsPanel.tsx` | **Agent C** | UI surface for the webcam stream: small live-preview thumbnail (top-right of `SggsScene`), permission prompt copy, on/off toggle, "gesture detected" overlay. Calls `sggs_hands.ts`. |
| `dashboard/src/lib/sggs_gestures.ts` | **Agent B** | Gesture → camera/scene mapping. Pure function: `(gestureEvent, currentCameraState) => nextCameraState`. Imported by `SggsScene` to keep camera math out of the React component. |
| `dashboard/src/lib/sggs_camera.ts` | **Agent B** | Three.js camera + orbit controls helpers. Keyboard handlers (`WASD` orbit, `+/-` zoom, `Tab` select-next-node, `Enter` activate, `Escape` deselect) live here. Keyboard parity per spec line 140. |
| `dashboard/src/lib/sggs_layout.ts` | **Agent B** | Deterministic 3D layout from `ThoughtTreeRootNode`. Reuses leaf-count slot-allocation pattern from `ThoughtTreeView::buildLayout` but emits `{x,y,z}` with depth → y, sibling spread → x, force-stabilized z. |
| `dashboard/src/lib/sggs_palette.ts` | **Agent B** | Extracts `KIND_PALETTE` from `ThoughtTreeView.tsx` into a shared module. ThoughtTreeView refactored to import from here (one-line change, no semantic difference) — see §5. |
| `dashboard/src/components/idea-atlas/SggsScene.lazy.tsx` | **Agent B** | `React.lazy()` wrapper. The three.js + @mediapipe bundle is ~600KB gzipped; lazy-load means non-SGGS users never download it. |
| `cas-native/inference/sggs_stream.py` | **Agent D** (Phase 2 only) | Inference-server WebSocket producer. Pushes head-level (12 updates per turn) structural commits as the model decodes. Not in Phase 1 scope. |
| `dashboard/src/lib/sggs_stream.ts` | **Agent D** (Phase 2 only) | WebSocket consumer on the dashboard side. Reducer pattern: `(currentTrace, streamEvent) => nextTrace`. Not in Phase 1 scope. |
| `docs/working/sggs_stream_protocol_2026_05_13.md` | **Agent D** (Phase 2 only) | The wire format. Both sides reference this doc. Not in Phase 1 scope. |

### MODIFIED — small additive

| File | Owner | Change |
|---|---|---|
| `dashboard/src/pages/IdeaAtlasPage.tsx` | **Agent B** | (a) Extend `ViewMode = 'list' \| 'graph' \| 'trace' \| 'sggs'`. (b) Add a fourth tab labeled `TRACE 3D` next to the existing `TRACE` tab. (c) Add a `{viewMode === 'sggs' && <SggsScene tree={loadedTrace.thought_tree} … />}` conditional, mirroring the existing `'trace'` case. No edits to the `'list'`, `'graph'`, or `'trace'` branches. |
| `dashboard/package.json` | **Agent B** (three deps), **Agent C** (mediapipe deps) | Add: `three`, `@types/three`, `@react-three/fiber`, `@react-three/drei`. Add: `@mediapipe/hands`, `@mediapipe/camera_utils`, `@mediapipe/drawing_utils`. Bundle impact mitigated by `SggsScene.lazy.tsx` (see §8). |
| `dashboard/src/components/idea-atlas/ThoughtTreeView.tsx` | **Agent B** | One-line refactor: import `KIND_PALETTE` from `lib/sggs_palette.ts` instead of defining it inline. Semantic no-op. Done in the same PR that introduces `sggs_palette.ts`. |

### UNTOUCHED — coexists, no edits

Per spec lines 125-130 ("SVG static rendering stays … both paths serve different purposes"):

- `dashboard/src/components/idea-atlas/ThoughtTreeView.tsx` (other than the palette refactor above)
- `dashboard/src/components/idea-atlas/TraceLoader.tsx` (file picker, drag, URL — reused unchanged)
- `dashboard/src/components/idea-atlas/TraceNodeDetailPanel.tsx` (the slide-in detail panel — reused unchanged)
- `dashboard/src/components/idea-atlas/TraceHeader.tsx` (metadata strip — reused unchanged)
- `dashboard/src/lib/trace.ts` (AtlasTrace types + validator — consumed read-only)
- `dashboard/src/components/idea-atlas/GraphView.tsx` (Idea-Atlas graph — unrelated)
- `dashboard/src/components/idea-atlas/NodeDetailPanel.tsx` (Idea-Atlas panel — unrelated)
- `dashboard/src/components/idea-atlas/InversionModal.tsx` (Idea-Atlas inversion picker — unrelated)
- `cas-native/inference/traceability_v0.py` (Python trace producer — Phase 1 reads its output unchanged)

---

## 4. Week-by-week schedule

Two paths offered. The default recommended path is the **12-week Phase 1** (full accessibility, gesture vocabulary, performance work, tests). The aggressive path is the **4-6 week MVP** (spec line 87): basic gestures, smaller node count, minimal accessibility. Recommendation in §11.

### Phase 1 — Baseline 3D Visualization (12 weeks)

Week numbering starts 2026-05-13. Weeks are calendar weeks; each owner is full-time on their column.

| Week | Agent B (Scene) | Agent C (Hands) | Agent D (idle in Phase 1) | Gate |
|---|---|---|---|---|
| **W1** (05-13) | Add `three` + `@types/three` + `@react-three/fiber` deps. Bootstrap empty `SggsScene.tsx` that renders one sphere from a hardcoded `AtlasTrace`. Lazy-load wrapper. | Add `@mediapipe/hands` + `@mediapipe/camera_utils` deps. Bootstrap `HandsPanel.tsx` that requests webcam permission and shows the live `<video>` element. No gesture detection yet. | — | `npm run dev` shows a single sphere on the new TRACE-3D tab. Webcam permission prompt fires. |
| **W2** (05-20) | Write `sggs_layout.ts`: deterministic 3D positions from `ThoughtTreeRootNode`. Port leaf-count slot allocation from `ThoughtTreeView::buildLayout` with `z=0`. Render all nodes from `DEMO_TRACE_COMPLEX` as spheres at correct positions. | First gesture: one-hand pinch detection in `sggs_hands.ts`. Emit `{kind: 'pinch', value: 0..1}` events. Log to console. | — | 14-node demo renders in 3D. Console shows pinch values 0..1 as user pinches. |
| **W3** (05-27) | Extract `KIND_PALETTE` → `lib/sggs_palette.ts`; refactor `ThoughtTreeView.tsx` to consume it. Color sphere `material.color` by `kind` palette. Add edge cylinders/splines between parent/child. | Two-hand pinch-spread detection. Emit `{kind: 'two_hand_zoom', value: delta}`. | — | Demo renders colored nodes + edges. Two-hand zoom events fire when both hands visible. |
| **W4** (06-03) | `sggs_camera.ts`: orbit controls (mouse drag), wheel zoom, pan (right-button). Match Atlas v0 ergonomics where possible. | Fist detection (closed-fist + rotation around z-axis of palm). Emit `{kind: 'fist_spin', value: angle_delta}`. | — | Stakeholder can orbit + zoom + pan with mouse. Fist gesture detected reliably for ≥1 second hold. |
| **W5** (06-10) | `sggs_gestures.ts`: pure mapping `(gestureEvent, cameraState) => nextCameraState`. Wire all three gestures to camera. | Stabilize gesture noise — running-average smoothing, hysteresis on enter/exit. Document false-positive rate. | — | Webcam-on: pinch zoom, two-hand spread zoom, fist spin all move the camera. <5% false-trigger rate on idle hand. |
| **W6** (06-17) | Click-to-select: raycast on click → emit `onNodeClick`. Wire `selectedNodeId` prop: selected node gets a brighter material + outline pass. Side panel reuses Atlas v0 `TraceNodeDetailPanel` unchanged. | Selection-gesture: one-hand pinch on a node = select. Distinct from background pinch (which is camera zoom — disambiguate by raycast hit). | — | Click any node in 3D → existing detail panel slides in (the Atlas v0 component, reused). Webcam pinch on a node selects it. |
| **W7** (06-24) | **Keyboard parity** (spec line 140): `WASD` orbit, `+/-` zoom, `Tab`/`Shift+Tab` cycle selection, `Enter` activate, `Escape` deselect, `R` reset camera. ARIA labels on the canvas. Focus ring on selected node. | Mouse-only fallback: when webcam off (or denied), `HandsPanel` hides; all gestures available via mouse + keyboard only. No SGGS feature is gated on webcam. | — | Manual a11y audit (Wakil): operate the scene with keyboard only. No feature unreachable. |
| **W8** (07-01) | Pinch node-drag: while pinched and pointed-at, node follows hand position. Position is local-cache only — does NOT mutate the trace. Releasing pinch snaps back OR holds, per UX preference (default: snap back). | Refine pinch confidence threshold; add per-hand state machine to avoid stutter. | — | Drag-and-release works; trace JSON unchanged. |
| **W9** (07-08) | Performance pass — instanced meshes for nodes (`THREE.InstancedMesh`), edges batched into single `BufferGeometry`. Frustum culling sanity check. | Performance pass — profile MediaPipe inference; verify ≤25ms/frame on stock laptop (camera input is 30fps; we can target 20fps inference). | — | 50-node tree holds 60 FPS during sustained pan/orbit on a stock 13" laptop (Intel Iris-class GPU). Profiled, not just observed. |
| **W10** (07-15) | Visual polish: drop shadows, ambient occlusion (cheap SSAO from `@react-three/drei`), gradient skybox, depth fog for legibility. Match Atlas v0 dark-mode chrome (`#0d1117`). | "Live gesture" affordance — small overlay shows which gesture is currently active + a thumbnail of the webcam frame (privacy reassurance: "this video never leaves your machine"). | — | Wakil reviews on the demo trace. Reports: legible at first glance, no jargon in chrome, gesture preview makes the local-only property obvious. |
| **W11** (07-22) | Test suite: `SggsScene.test.tsx` (renders, click fires, prop-driven selection), `sggs_layout.test.ts` (deterministic output), `sggs_gestures.test.ts` (gesture → camera math). Target 85% line coverage on new files. | Test suite: `sggs_hands.test.ts` (mocked MediaPipe stream, gesture state machine, smoothing). Webcam permission flow is manual-tested (jsdom cannot simulate). | — | `npm test` green. |
| **W12** (07-29) | Cross-browser smoke: Chromium, Firefox, Safari. Fall back to keyboard-only on Safari if MediaPipe doesn't run. Ship Phase 1. | Documentation: `dashboard/README.md` adds an SGGS section with a screenshot, the privacy guarantee, and the keyboard shortcuts. | — | Phase 1 demo-ready (see §7 for full gate). |

**Phase 1 deliverable:** stakeholder loads `dashboard/public/demo_traces/demo_thought_becoming_action.json` (or the 14-node Θ-recipe demo), opens the TRACE-3D tab, orbits with mouse + zooms with scroll + selects with click. Webcam optional. Keyboard works for everything.

### Phase 2 — Live Generation Witnessing + Rewind (12 weeks)

Begins **after** Phase 1 ships and survives a real stakeholder demo. Phase 2 is gated on inference-server architecture being decided (per spec line 183) — that decision was deferred during Phase 1 and must land before W1 of Phase 2.

| Week | Agent B (Scene) | Agent C (Hands) | Agent D (Streaming) | Gate |
|---|---|---|---|---|
| **W13** | Wire `loadedTrace` as React state subscribable from a stream reducer. Trace becomes mutable across time. | Idle (Phase 2 has no new gesture work; reserved for animation-mode toggle UX). | Write `docs/working/sggs_stream_protocol_2026_05_13.md` — the wire format. Head-level granularity (12 updates/turn) per spec line 105. JSON-over-WebSocket. Schema: `{trace_id, step_index, event_kind, partial_tree}`. | Protocol doc reviewed by Agent B + Wakil. |
| **W14** | Animation system: when a new node arrives via stream, it fades + scales in (Apple-easing, ~300ms). Same easing as Atlas v0's `thought-tree-node-anim`. | Idle. | `cas-native/inference/sggs_stream.py` — WebSocket server. Hooks into Stage-3 REPL after each head fires. Emits a partial-tree event. | Manual: run `cas chat-stage3 --sggs-stream :8765` + open dashboard → tree assembles live. |
| **W15** | Smooth-vs-discrete animation toggle (spec line 149: "prototype both modes"). Smooth = physics-based settle; discrete = pop-in with pause. | Idle. | `dashboard/src/lib/sggs_stream.ts` — WebSocket client. Reducer: `(currentTrace, streamEvent) => nextTrace`. Reconnect logic. | Both animation modes work end-to-end. |
| **W16** | Timeline scrubber UI at bottom of scene. Drag to a step index, scene snaps to that historical state. Reuses Atlas v0 dark-mode style. | Idle. | Trace history accumulator — every stream event is appended to an in-memory log. Step-to-state is deterministic replay from log + initial trace. | Drag the scrubber → tree morphs to that moment. |
| **W17** | Playback controls: play / pause / 0.25x / 0.5x / 1x / 2x. Frame-step (←/→). | Idle. | Bookmarking — `bookmark(step_index, name)`. Persisted to localStorage (per-trace_id key). | Stakeholder can replay a turn at 0.25x and bookmark the noetic-resolution moment. |
| **W18** | Interpolation: between two recorded steps, render the tween. Edge sprouts animate in. | Idle. | Stream resilience — out-of-order events buffered, missed events flagged with warning chip. | Scrubbing through arbitrary moments is smooth, not jumpy. |
| **W19** | IntentIR node integration — user query renders as a parsed-CAS node alongside model output (spec line 99-152). Requires NL front door to be live (Step 5B). | Idle. | Stream protocol v0.2: add `intent_ir` event kind. | User query → parsed-intent node visible before model output starts assembling. |
| **W20** | Branching note (spec line 107): make it explicit in UI whether viewing structural-growth (default) or alternative-consideration (Phase 3 / Mode 6). | Idle. | Multi-turn streaming: traces concatenate by session. | Multi-turn session replays as a sequence. |
| **W21** | Performance for multi-turn live: virtualized rendering of historical nodes (older turns fade + collapse). | Idle. | Server-side trace log compaction — old turns drop raw trace, keep summary. | 5-turn session at 60 FPS, no GC stalls. |
| **W22** | Visual polish for the live-witnessing UX: pulse + glow on the just-arrived node. | Idle. | Integration tests: spin up inference + dashboard + scrub a real turn. | E2E test green. |
| **W23** | Test suite + a11y check on timeline + playback controls (keyboard parity: `Space` play/pause, `←/→` frame-step, `,/.` 0.25x/2x). | Idle. | Test suite for stream reducer. | `npm test` + `pytest` green. |
| **W24** | Ship Phase 2 demo. | Idle. | Update spec backlog doc with Phase 3 entry. | Phase 2 audit-ready (see §7). |

**Phase 2 deliverable:** the spec's target demo scenario at line 158 — stakeholder asks a question, the structure assembles live in ~8 seconds, stakeholder rewinds to a specific structural moment, watches at 0.25x, bookmarks it.

### Aggressive MVP path (4-6 weeks, only if requested)

Compresses Phase 1 W1-W12 into W1-W6 with explicit cuts:

- **Cut:** keyboard-parity refinement (W7), pinch node-drag (W8), visual polish (W10), cross-browser (W12). Webcam-only path with mouse fallback for users without one. Spec line 87 acknowledges this is "rough-edges-acceptable."
- **Keep:** the three core gestures, click-to-select, the 14-node demo, basic tests, lazy-load.
- **Defers:** the accessibility-parity requirement formally documented at spec line 140 — which is a real liability for any public-facing demo. **MVP is internal-demo-only, not stakeholder-pitch.**

Recommendation in §11.

### Phase 3 — Deferred

Per spec lines 111-119, Phase 3 stays backlog: counterfactual exploration during rewind (Mode 6 ghost nodes), live next-token preview, persistent multi-session storage, mobile/tablet touch + stylus, VR/AR via WebXR. Defer until Phase 1+2 ship AND get stakeholder validation. See §9.

---

## 5. Reuse from Atlas v0

The SGGS scene consumes Atlas v0 outputs unchanged. No re-research, no schema rework, no parallel maintenance:

| Atlas v0 asset | Where it lives | How SGGS consumes |
|---|---|---|
| `AtlasTrace` TypeScript types | `dashboard/src/lib/trace.ts` | `SggsScene` props type: `{ tree: AtlasTraceThoughtTree; trace: AtlasTrace; onNodeClick?; selectedNodeId?; … }`. Same shape that flows into `ThoughtTreeView`. |
| `validateAtlasTrace` | `dashboard/src/lib/trace.ts` | Used by `TraceLoader.tsx` (unchanged). SGGS receives only validated traces. |
| `KIND_PALETTE` | currently inline in `ThoughtTreeView.tsx` | **Refactored** to `dashboard/src/lib/sggs_palette.ts` in W3. Both 2D and 3D paths import from the shared module. One-line change to `ThoughtTreeView.tsx`. |
| `DEMO_TRACE` (6-node "thought becomes action") | `dashboard/src/components/idea-atlas/TraceLoader.tsx` | The basic smoke fixture for SGGS scene tests. |
| `DEMO_TRACE_COMPLEX` (14-node Θ-recipe) | same file | The stakeholder-demo fixture. The 14-node tree is the recommended SGGS demo target — large enough to feel structural in 3D, small enough that 60 FPS is trivial. |
| `TraceLoader.tsx` (file picker + drag + URL) | `dashboard/src/components/idea-atlas/TraceLoader.tsx` | Unchanged. Sits **above** the SGGS canvas in the page layout, the same way it sits above `ThoughtTreeView` in the existing TRACE tab. The loader panel stays 2D React even when the canvas below is WebGL — no need to render UI chrome in 3D. |
| `TraceHeader.tsx` (metadata strip + warning chips) | same dir | Unchanged. Same role above the SGGS canvas. |
| `TraceNodeDetailPanel.tsx` (slide-in detail) | same dir | Unchanged. Reused for click-to-select detail. The 3D scene calls `setSelectedNodeId(id)`; the existing 2D panel does its thing. |
| BFS-staggered animation pattern from `ThoughtTreeView` | same file | Port the timing curve (`Math.min(idx * 75, 900)`) to the SGGS node-fade-in. Visual consistency between 2D and 3D. |
| Apple-easing cubic-bezier `(0.4, 0, 0.2, 1)` | same file | Reused for camera transitions in `sggs_camera.ts`. |
| `cas atlas-save` CLI | `cas-native/inference/cas_cli.py` | Unchanged. SGGS reads the same JSON output. |

**The invariant:** anything the 2D path renders correctly, the 3D path renders correctly from the same JSON. If the 14-node Θ-recipe demo looks right in `ThoughtTreeView`, it looks right in `SggsScene`. This is the smoke test.

---

## 6. Integration plan — how SGGS coexists with the current TRACE tab

Per Atlas v0 design doc §5, the current tab strip is `ViewMode = 'list' | 'graph' | 'trace'`. SGGS extends it to:

```typescript
type ViewMode = 'list' | 'graph' | 'trace' | 'sggs';
```

The tab strip in `IdeaAtlasPage.tsx` gets a fourth button labeled `TRACE 3D` (or `ATLAS 3D` — pick one in W1; Wakil decides). The page layout below the tab strip becomes:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Idea Atlas                  [LIST] [GRAPH] [TRACE] [TRACE 3D]        │
├──────────────────────────────────────────────────────────────────────┤
│ <TraceLoader />            (reused unchanged — same as TRACE tab)    │
├──────────────────────────────────────────────────────────────────────┤
│ <TraceHeader />            (reused unchanged)                        │
├─────────────────────────────────────────┬────────────────────────────┤
│                                         │                            │
│  <SggsScene />  (Three.js canvas)       │  <TraceNodeDetailPanel />  │
│                                         │  (reused unchanged)        │
│  ┌────────────────────────┐             │                            │
│  │   3D thought tree       │             │                            │
│  │   ●─────●                │             │                            │
│  │       │                  │             │                            │
│  │       ●─●─●               │             │                            │
│  └────────────────────────┘             │                            │
│  <HandsPanel /> ◄─── opt-in webcam      │                            │
│  thumbnail, top-right of the canvas      │                            │
└─────────────────────────────────────────┴────────────────────────────┘
```

Both `'trace'` and `'sggs'` consume the same `loadedTrace: AtlasTrace` state already managed by `IdeaAtlasPage` for the TRACE tab. No duplicate state, no duplicate loader, no duplicate validator. Switching tabs is one render — the trace stays loaded across tab switches.

Edits to `IdeaAtlasPage.tsx`: ~25 lines (new tab button, new `viewMode === 'sggs'` block, lazy-import). No changes to `'list'`, `'graph'`, or `'trace'` branches.

---

## 7. Gate criteria per phase

Per `feedback_separate_evidence_levels_in_status.md`, do not conflate "wired" with "passes gates." Each gate is a checkbox; partial pass is failure.

### Phase 1 — demo-ready

- [ ] `npm run dev` boots the dashboard, the TRACE 3D tab is visible, and clicking it renders the 3D scene with `DEMO_TRACE_COMPLEX` loaded.
- [ ] Mouse-orbit, scroll-zoom, click-to-select all work on the 14-node demo.
- [ ] All three gestures (pinch zoom, two-hand spread, fist-spin) functional with webcam on. False-trigger rate <5% on a one-minute idle test.
- [ ] **Keyboard parity** — every gesture and every mouse action has a keyboard equivalent that does the same thing. Verified manually.
- [ ] **60 FPS during sustained pan/orbit on a 50-node tree** on a stock 13" laptop without dedicated GPU. Profiled in the browser dev tools, not just observed.
- [ ] All unit-test suites pass with ≥85% line coverage on new files (`SggsScene`, `sggs_layout`, `sggs_gestures`, `sggs_camera`, `sggs_hands`).
- [ ] No jargon leaks in chrome (per `feedback_plain_language_no_jargon.md`). Tab label is `TRACE 3D` or `ATLAS 3D`; gesture help text is plain English.
- [ ] **Object traceability holds** — every visible 3D node walks back to a `ThoughtTreeNode.id` in the trace JSON. Per `feedback_object_traceability_required.md`: if a label appears with no source field, it's a bug.
- [ ] Webcam-off works completely — every SGGS feature except gesture input remains functional. No fatal error, no scary message.
- [ ] Wakil loads the demo trace and reports: (a) the 3D tree is legible without explanation; (b) clicking any node shows the same detail the 2D tab shows; (c) gestures feel responsive; (d) it looks at least as polished as the teleclaudius reference.
- [ ] Bundle-size check: the SGGS lazy chunk is <800KB gzipped (three + drei + mediapipe combined). Lazy-load verified: opening the LIST tab does not download SGGS deps.

### Phase 2 — audit-ready

- [ ] `cas chat-stage3 --sggs-stream :8765` plus the dashboard renders the tree assembling in real time. Latency from head emission to visible node <300ms.
- [ ] Timeline scrubber works: dragging snaps the scene to that historical moment.
- [ ] Playback at 0.25x, 0.5x, 1x, 2x is smooth — no skipped frames, no jumpy snaps.
- [ ] Bookmark a moment, refresh the page, bookmark persists.
- [ ] Both animation modes (smooth + discrete) work; toggle in UI.
- [ ] IntentIR node renders as the parsed user query, distinct from model-output nodes.
- [ ] Multi-turn session of 5 turns at 60 FPS, no GC stalls visible in dev tools.
- [ ] Wakil performs the spec line 158 demo scenario end-to-end and reports it works as described.
- [ ] **Patent review** — Wakil's IP attorney has been notified about Phase 2 patentable scope (live witnessing + rewind + slow-motion). Filing decision made before public demo. See §10.

---

## 8. Risks + mitigations

Drawn from spec lines 134-153 plus new risks specific to this implementation:

| Risk | Source | Mitigation |
|---|---|---|
| Three.js handles thousands of nodes, but tens of thousands needs instancing/LOD/culling. | Spec line 137 | Phase 1 targets ≤50 nodes (matches Atlas v0). Performance gate at W9. Defer LOD/culling work to Phase 3 if real Mode-7 traces exceed 500 nodes. |
| Gesture-only excludes users without webcam, motor disabilities, gesture-vocabulary unfamiliarity. | Spec line 140 | **Keyboard + mouse parity is a hard Phase 1 gate.** Not a nice-to-have. W7 is dedicated to this. |
| Mobile / tablet — webcam gestures aren't natural on touchscreens. | Spec line 143 | Out of scope for Phase 1+2. Phase 3 backlog. Phase 1 desktop-only. |
| Real-time streaming latency vs richness tradeoff. | Spec line 146 | Phase 2 head-level granularity (12 events/turn, not token-level). Spec line 105. |
| Smooth vs discrete animation comprehensibility. | Spec line 149 | Phase 2 W15 ships both modes with a UI toggle. Stakeholder picks. |
| User query representation — raw text node vs parsed IntentIR. | Spec line 151 | Phase 2 W19 requires NL front door to be live. If Step 5B hasn't landed, Phase 2 W19 fallback is raw-text node; upgrade when IntentIR lands. |
| **NEW: Dependency bundle size.** `three` + `@react-three/fiber` + `@react-three/drei` + `@mediapipe/hands` + `@mediapipe/camera_utils` is ~600-800KB gzipped — the dashboard has not previously shipped that much WebGL/CV code. | Implementation risk | `dashboard/src/components/idea-atlas/SggsScene.lazy.tsx` uses `React.lazy()` so SGGS deps only download when the user clicks the TRACE 3D tab. Bundle-size gate at Phase 1 §7. |
| **NEW: WebGL context loss / driver crashes.** Some integrated GPUs (older Intel, locked-down corporate laptops) will fail or perform terribly. | Implementation risk | Detect `WEBGL_lose_context`; show a friendly "your browser/GPU doesn't support 3D — switch to TRACE tab for 2D view" with a one-click switch. Done in W12. |
| **NEW: MediaPipe browser compat.** Safari historically lags; mediapipe-hands.js requires WASM SIMD. | Implementation risk | Feature-detect on load; if MediaPipe fails to initialize, `HandsPanel` shows "Webcam gestures unavailable in this browser — use mouse + keyboard." No SGGS feature blocks on this. |
| **NEW: Camera permission UX traps.** Users denying webcam mid-session, OS-level camera lock. | Implementation risk | `HandsPanel` surfaces permission state explicitly; "Webcam off" is a first-class mode, not an error state. Done in W4 + W7. |
| **NEW: Privacy concerns at demo time.** "Is my video going somewhere?" | Implementation risk | Visible "local-only" badge near the webcam preview thumbnail. Inspect-element-friendly: zero network requests with webcam data. Privacy claim is auditable. |
| **NEW: Bundle test flakiness.** WebGL in jsdom is a known pain point. | Implementation risk | `SggsScene.test.tsx` mocks `three` and tests only the React/JSX logic; render-pixels assertions reserved for manual a11y/visual review. Documented in W11. |
| **NEW: Three.js + react upgrade churn.** Major version bumps mid-project. | Implementation risk | Pin to `three@^0.180` (or current LTS-ish) and `@react-three/fiber@^9` at W1. Document the floor in `package.json` comment. |

---

## 9. What stays deferred even now

Per spec lines 111-119, Phase 3 stays backlog. Be explicit about why:

| Phase 3 feature | Why still deferred |
|---|---|
| Counterfactual exploration during rewind (Mode 6 ghost nodes when scrubbing) | Requires Mode 6 inference-time top-k alternatives, which doesn't exist yet. Out of scope until the model produces alternatives. Inversion Replay (a v0.5 sibling concept) is closer but different — it flips a CAS axis on a node and re-runs; that's offline, not live counterfactuals. |
| Live next-token preview (top-k upcoming structural commitment) | Requires per-token logits + token-level streaming, which spec line 105 explicitly rejects as a Phase 2 granularity (gets jittery). Different feature; different infra. |
| Persistent multi-session storage (Idea Atlas accumulates across sessions) | Needs a backend service for trace storage with multi-user identity. Atlas v0 reads from disk. Adding a real persistent service is product engineering at backend scale; out of scope. |
| Mobile/tablet touch + stylus | Phase 1+2 desktop-only. Touch gesture vocabulary is a different design problem; defer until desktop product gets stakeholder validation. |
| VR/AR via WebXR | Three.js → WebXR is straightforward but the audience demand is unproven. Defer. |

The discipline (per spec line 184-185): capture, defer, ship the critical path. The user override gets us to Phase 1 + Phase 2; it does NOT get us to Phase 3.

---

## 10. Patent + IP framing

Per spec lines 169-170: Phase 2 (live witnessing + rewind/slow-motion structural cognition) is patentable on its own. Phase 1 alone is not novel enough to need IP review — 3D graph viewers and webcam-gesture-driven scenes are both well-established prior art.

**Action required before Phase 2 public demo:**
- Raise Phase 2 patentable scope with the IP attorney who handled USPTO #64/037,173.
- Document the specific claim surface: live witnessing of structural CAS assembly + rewind + slow-motion + bookmark + structural-vs-alternative branching distinction.
- Combined with Phase 1 spatial gesture surface, this becomes a multi-component patent portfolio. Spec line 170: "Worth raising in deferred IP attorney conversation."
- Decision should land **before** the first Phase 2 stakeholder demo (target W24). Filing can happen in parallel with W22-W24 polish work.

**Action for Phase 1:**
- No IP review required for Phase 1 itself.
- However: the SGGS-Atlas combination (3D structural trace viewer fed by `traceability_v0` schema) inherits any patentability the underlying CAS-Native traceability architecture has. That existing patent envelope covers Phase 1 by extension; no new claims needed.

---

## 11. Recommendation — which path

**Recommended: full 12-week Phase 1 path.** Reasons:

1. Accessibility parity (spec line 140) is a hard requirement; the MVP path explicitly cuts W7. The user has been clear that traceability and accessibility are first-class concerns, not nice-to-haves (per `feedback_object_traceability_required.md`, `feedback_traceability_is_the_whole_purpose.md`).
2. The 4-6 week MVP path produces a demo, not a product. The user override (per memory `project_sggs_implementation_started_2026_05_13.md`) was triggered by seeing a reference implementation and saying "this is how I expect it to look like" — the teleclaudius reference has polish, not rough edges. Shipping rough-edged means not matching what the user signed off on.
3. Bundle size and WebGL fallback work (W12) is mandatory for any public-facing demo. Cutting cross-browser is an "internal demo only" decision.
4. The +6 weeks of polish is small compared to the +12 weeks of Phase 2 that follows. The aggressive path saves 6 weeks now to spend equivalent time later patching issues that should have been caught in Phase 1.

**When to consider MVP path:** if a hard external deadline (investor demo, conference talk, regulator meeting) forces a 4-6 week ship date and Wakil is willing to accept "internal-demo-only" framing for that window. Otherwise, full path.

---

## 12. Memory references

- `project_sggs_implementation_started_2026_05_13.md` — captures the deferral override and commit to start. Read this before any session involving SGGS work; it's the load-bearing context for why this plan exists at all.
- `sggs_v2_v3_backlog_pointer.md` — superseded as a "don't implement" gate (the override above invalidates it), still authoritative on the technical specifics: libraries (MediaPipe Hands + Three.js), gestures (fist-spin / pinch / two-hand pinch-spread), streaming granularity (head-level, 12/turn), privacy property (local-only browser inference).
- `feedback_separate_evidence_levels_in_status.md` — every status report on SGGS work distinguishes wired / works / sample-looked-good / gate-passed / prototype / validated. No conflation.
- `feedback_object_traceability_required.md` — every visible 3D node walks back to a `ThoughtTreeNode.id`. Non-negotiable.
- `feedback_plain_language_no_jargon.md` — tab labels and gesture-help text in plain English. "Camera orbit," not "azimuthal rotation."
- `feedback_audit_only_after_automated_checks.md` — Phase 1 gate checks (test coverage, FPS, bundle size, traceability) run before Wakil's manual demo review. Don't waste user time on issues that automated checks would catch.

---

## 13. Definition of done — SGGS Agent A

- [x] Implementation plan written at `docs/working/sggs_v0_implementation_plan_2026_05_13.md`.
- [x] File ownership map per agent specified.
- [x] 12-week schedule for Phase 1 with weekly deliverables and gates.
- [x] 12-week schedule for Phase 2 with weekly deliverables and gates.
- [x] Phase 3 explicit deferral list.
- [x] Reuse map from Atlas v0 enumerated.
- [x] Risks (spec + new) with mitigations.
- [x] Patent / IP framing surfaced.
- [x] Recommendation between aggressive MVP and full Phase 1.
- [x] Memory anchors listed.
- [ ] Commit + report.

End of implementation plan.
