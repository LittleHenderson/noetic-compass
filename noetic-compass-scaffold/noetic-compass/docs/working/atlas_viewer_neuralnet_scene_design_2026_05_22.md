# NeuralNetScene — Auto-Scaling Design

**Status:** Draft for user sign-off
**Date:** 2026-05-22
**Anchor:** Atlas Viewer v0 Product Scope §2 (v0.0 / v0.2)
**Companion doc:** `atlas_viewer_v0_product_scope_2026_05_22.md`

---

## 1. Goal & non-goals

### Goal

A Three.js 3D scene that renders any supported transformer architecture as a stack of layer planes with neuron glyphs at **model-native indices**, color-coded by CAS axis activation, with blindspot overlay from Stage 27F covers, multi-level zoom, and hover/click interactions that surface model coordinates + CAS interpretation + Mode 7 attribution.

### Non-goals

- Not a full neural-network simulator. We render snapshots from recorded traces or live forward-pass streams; we don't run the model inside the browser.
- Not a generic graph viewer. Architecture is specifically "stacked transformer layers."
- Not architecture-specific hardcoded scenes (after v0.0). v0.2 reads architecture from HF config and auto-scales.

### Phasing within NeuralNetScene

- **v0.0 / v0.1** — replay-only data source (`TraceArtifact` static input)
- **v0.2** — same data shape, but architecture auto-scaling enabled
- **v0.3** — adds live-stream data source (`LiveStreamProvider` props branch), collab event broadcast hooks, and gesture-input layer (see §13)

---

## 2. Architecture detection

NeuralNetScene takes a `ModelArchitecture` config object:

```ts
interface ModelArchitecture {
  family: 'pythia' | 'olmo' | 'qwen' | 'llama' | 'mistral'
        | 'gemma' | 'phi' | 'gpt-neox' | 'unknown';
  n_layers: number;             // e.g. 12 for Pythia-160M, 32 for Llama-3-8B
  hidden_size: number;          // e.g. 768, 4096
  mlp_intermediate_dim: number; // e.g. 3072, 14336
  n_heads: number;              // e.g. 12, 32
  total_params: number;         // for LOD bucketing
  validated: boolean;           // from KNOWN_LIMITS.md
}
```

Resolved server-side from HF `config.json` at job submission time. Cached per model. At v0.0, hardcoded to Pythia-160M values (12 / 768 / 3072 / 12 / 162M / true).

---

## 3. Scene composition

### Stack layout

- `n_layers` planes stacked along Z axis (12 for Pythia-160M, 32 for Llama-3-8B)
- Plane spacing: 1.5 units default; compressed to 0.5 units at "whole model" zoom level
- Plane size: scales with `mlp_intermediate_dim`
- Layer 0 at front, Layer `N-1` at back

### Neuron glyphs

Each MLP intermediate neuron is one glyph at index `(layer, neuron_index)`.

- **Geometry:** InstancedMesh with point sprite or small octahedron (LOD-dependent)
- **Position:** Within-plane row-major grid based on `mlp_intermediate_dim` (e.g. 3072 = 64 × 48 grid; 14336 = 128 × 112)
- **Color:** HSL from `atlasPalette.ts` — hue = Foundation drive, saturation = activation intensity, lightness = `clean_margin`
- **Halo:** red outline if neuron is in an eraser-channel cover (blindspot); purple if currently being suppressed by Module 5 steering
- **Coordinate label:** shown on hover, format `L{layer}N{neuron_index}` (e.g. `L5N2648`)

### Overlays (toggleable)

- **Blindspot overlay** — semi-transparent red mesh covering neurons in the active drive's cover
- **Active trace path** — blue line connecting neurons that fired above-threshold on the current token
- **Suppression overlay** — purple mesh on neurons under active Module 5 intervention

---

## 4. Coordinate system

**Model-native indices are authoritative.** `L5N2648` means Pythia-160M's layer 5 MLP intermediate neuron 2648. A developer with hook code could load the same model in PyTorch and ablate that neuron directly — Atlas Viewer is using the SAME coordinate system, not a CAS abstraction over it.

CAS interpretation is overlay on top of model coordinates, never a replacement.

### Hover tooltip — 10 fields

| Field | Example | Source |
|---|---|---|
| Coordinate | `L5 N2648` | Stage 27F `neuron_cover` |
| Layer | 5 of 12 | `candidate_layers` |
| MLP position | 2648 / 3072 | `mlp_intermediate_dim` |
| Activation (this token) | 0.87 | Live trace artifact |
| Foundation class | `F1A` (Unity / Analytical) | Stage 27F class key |
| Margin (clean) | 7.615 | `clean_margin` |
| Drop under ablation | 2.437 | `targeted_drop` |
| CAS state | `^1^C_{F1\|A}` — Mind / Cognitive / Unity / Analytical | Derived from class + domain |
| English | "Paying attention. Drawn to it." | `colloquialismMap.ts` |
| Blindspot? | Yes / No | Eraser-channel cover membership |

Click → Mode 7 chain back to source span → Evidence Packet drawer opens at the corresponding row.

---

## 5. Level-of-detail (LOD) strategy

Different model sizes demand different rendering strategies.

| Class | Example | n_layers × mlp_dim | Total neurons | Strategy |
|---|---|---|---|---|
| Small | Pythia-160M | 12 × 3072 | ~37K | Render every neuron as individual glyph |
| Medium | OLMo-1B / Qwen-1.5B | 16 × 8192 | ~131K | Render every neuron, but switch to point sprites instead of meshes |
| Large | Llama-3-8B | 32 × 14336 | ~459K | Bin into 16×16 patches at "whole model" zoom; expand to individual neurons at "neuron-cluster" zoom |
| XL | 70B+ | 80+ × 28672+ | ~2.3M+ | Bin into 32×32 patches at most zoom levels; full detail only at "individual neuron" zoom + frustum cull |

Bin coloring at coarse LOD: average activation × dominant drive hue.

LOD transitions are triggered by camera distance to the layer plane. Hysteresis: 10% threshold to avoid flicker.

---

## 6. Six zoom levels

| Level | Camera distance | What you see |
|---|---|---|
| Z0 — Whole model | Far | All layers visible, neurons binned, blindspots show as colored bands |
| Z1 — Layer | Mid-far | Single layer plane fills view, neurons binned at 4×4 |
| Z2 — Attention block | Mid | Cluster of neurons within one layer |
| Z3 — Component group | Mid-near | ~64-neuron neighborhood |
| Z4 — Sparse cover cluster | Near | The Stage 27F cover for the selected class fills view |
| Z5 — Individual neuron | Closest | One neuron glyph + label + tooltip persistent |

User controls:

- Scroll-wheel for continuous zoom
- `1`–`6` keys for preset jumps
- "fit to selection" button on toolbar

---

## 7. Hover / click interactions

- **Hover neuron** — tooltip appears with all 10 fields from §4
- **Click neuron** — Mode 7 chain renders as a line trail to source-span tokens; Evidence Packet drawer opens
- **Hover layer plane** — layer-level summary (mean activation, top-3 drives engaged, blindspot density)
- **Click layer plane** — zooms to Z1 on that layer
- **Hover cover region** (when blindspot overlay active) — region-level summary (which drive, how many neurons, mean `clean_margin`)
- **Click cover region** — zooms to Z4 on that cover

### Keyboard shortcuts

- `Space` — play/pause replay
- `,` / `.` — step token backward/forward
- `[` / `]` — step layer focus backward/forward
- `B` — toggle blindspot overlay
- `T` — toggle active-trace overlay
- `S` — toggle suppression overlay
- `F` — fit camera to selection
- `R` — reset camera to default view

---

## 8. Color encoding

From `atlasPalette.ts`:

| Concept | Color | Hex |
|---|---|---|
| Accepted / stable | Green | `#22c55e` |
| Caveat / uncertain | Yellow | `#eab308` |
| Constrain | Orange | `#f97316` |
| Suppress / blindspot void | Red | `#ef4444` |
| Active trace path | Blue | `#3b82f6` |
| Intervention / steering | Purple | `#a855f7` |
| Unavailable / not measured | Grey | `#6b7280` |

Foundation drive hue (Module 1 + 4 + 5 outputs):

| Drive | Name | Hue |
|---|---|---|
| F1 | Unity | 220° (blue-cyan) |
| F2 | Wisdom | 280° (purple) |
| F3 | Vitality | 30° (orange) |
| F4 | Connection | 160° (teal) |
| F5 | Agency | 60° (yellow) |
| F6 | Structure | 200° (blue) |
| F7 | Purpose | 320° (magenta) |

Color-blind-safe variant available via toggle (Okabe-Ito palette).

---

## 9. Performance budget

| Metric | Target | Notes |
|---|---|---|
| Frame rate | 60 fps at Z2 and closer; 30 fps acceptable at Z0 on large models | Hard floor: 24 fps; warn user below |
| Max draw calls per frame | < 200 | Use InstancedMesh aggressively |
| GPU memory | < 1 GB on integrated GPUs | Cap LOD detail accordingly |
| Initial scene build | < 3 s for Pythia-160M; < 8 s for Llama-3-8B | Show loading skeleton; lazy-load layers beyond first 3 |
| Hover tooltip latency | < 16 ms (1 frame) | Raycaster limited to nearest 5K neurons by distance |

Frustum culling enabled. Layers behind camera not drawn. Inactive overlays not drawn.

---

## 10. Three.js technical specifics

- **InstancedMesh** for neuron glyphs — one per layer, instance count = `mlp_intermediate_dim`
- **Custom shader** for halo (radial fade from neuron center)
- **Sprite** fallback for medium-class models (cheaper than InstancedMesh of small meshes)
- **OrbitControls** for camera (existing in `SggsScene`; copy pattern)
- **Raycaster** for hover/click (limited to nearest 5K neurons by distance for performance)
- **EffectComposer** + bloom for glow on active-trace neurons (optional, toggle in settings)
- **PMREMGenerator** not needed (no PBR materials at v0)

Three.js version: pin to whatever `SggsScene` currently uses (~r150). Upgrade to latest stable is out of scope at v0.0.

---

## 11. Test fixtures

- **Pythia-160M reference trace** — committed at `atlas-viewer/test-fixtures/pythia_160m_reference_trace.json`
- **Stage 27F cover snapshot** — copy from `research/cas_probe/.tmp/stage27f_smoke.json`
- **Synthetic large-arch trace** — generated for Llama-3-8B-shape (no real Llama run yet at v0.0; synthetic stub for LOD testing)

### Test cases (smoke + integration)

1. **Pythia-160M renders 3072 × 12 neurons at 60 fps on dev laptop** — smoke
2. **Hover any neuron shows `L{layer}N{index}` tooltip within 16 ms** — interaction latency
3. **Z0 → Z5 zoom sequence stays > 30 fps throughout** — LOD transition
4. **Blindspot overlay toggles in < 100 ms** — overlay performance
5. **Synthetic Llama-3-8B-shape stays > 30 fps at Z0 with 16×16 binning** — large-arch LOD
6. **Click neuron opens Evidence Packet drawer at correct row** — cross-component integration

---

## 12. Component interface

```tsx
interface NeuralNetSceneProps {
  architecture: ModelArchitecture;
  trace: TraceArtifact;              // from replayController
  currentToken: number;              // 0-indexed token position
  selectedNeuron?: { layer: number; index: number };
  overlays: {
    blindspot: boolean;
    activeTrace: boolean;
    suppression: boolean;
  };
  zoomLevel: 0 | 1 | 2 | 3 | 4 | 5;
  onNeuronHover?: (coord: NeuronCoord | null) => void;
  onNeuronClick?: (coord: NeuronCoord) => void;
  onLayerClick?: (layer: number) => void;
  onZoomChange?: (level: 0 | 1 | 2 | 3 | 4 | 5) => void;
}

interface NeuronCoord {
  layer: number;
  index: number;             // 0..mlp_intermediate_dim-1
  label: string;             // e.g. "L5N2648"
}
```

State managed externally by `AtlasViewerShell` + `useReplayController`. NeuralNetScene is a presentation component; no internal state beyond Three.js scene graph.

At v0.3, the props shape extends to accept either a replay trace OR a live stream subscription (data shape identical per-frame):

```tsx
interface NeuralNetScenePropsV03 extends NeuralNetSceneProps {
  // v0.3 additions, all optional and backwards-compatible
  liveStream?: LiveStreamHandle;        // if present, drives currentToken from stream
  collab?: {
    peerCursors: PeerCursor[];          // remote user cursor positions
    onLocalHover?: (coord: NeuronCoord | null) => void; // broadcasts to peers
    onLocalClick?: (coord: NeuronCoord) => void;
  };
  gestures?: {
    enabled: boolean;                   // MediaPipe Hands toggle
    onGesture?: (g: GestureEvent) => void;
  };
}
```

---

## 13. v0.3 data flow — live streaming, collab broadcast, gesture input

### Live-mode streaming

Live mode swaps the static `TraceArtifact` input for a `LiveStreamHandle` that subscribes to an SSE/WebSocket channel from the hosted inference job. Per-token frame shape:

```ts
interface LiveFrame {
  token_index: number;           // monotonic
  token: string;                 // surface string
  // Activation deltas — only neurons crossing threshold since prior frame
  activation_deltas: Array<{
    layer: number;
    neuron: number;
    activation: number;          // [0, 1]
  }>;
  // Module outputs streamed as available; null until module completes for this token
  foundation_probe?: number[];   // 7-vector
  blindspot_overlay?: BlindspotFrame;
  mode7_attribution?: Mode7Edge[];
}
```

**Throttling and smoothing:**

- Server-side: cap stream to 30 frames/sec; coalesce sub-frame activations
- Client-side: ring buffer of last 256 tokens for scrub-back; older frames evicted
- Backpressure: if client falls > 30 frames behind, server drops to keyframe-only stream (full activation snapshot every Nth frame) until client catches up
- Pause: client stops consuming, server queues up to buffer limit then drops oldest

**Degradation path:** if buffer underruns 3× consecutively, client falls back to "replay-from-recording" mode and surfaces a "live stream lost, viewing recording" banner.

### Collab broadcast

Hover and click events broadcast to peers via `collab.onLocalHover` / `onLocalClick`. Remote events arrive as `peerCursors` updates. Render contract:

- Local cursor: full tooltip + halo on hovered neuron
- Peer cursor: small avatar circle + colored ring on focused neuron; tooltip suppressed (just label)
- Peer count > 3: collapse non-focused peer cursors into a "+N more" badge (Q10 controls this)

Conflict resolution: there is no shared state to conflict at v0.3.0 (presence and comments only; no shared edits). v0.3.1 adds annotation editing under Liveblocks/Yjs CRDT.

### Full SGGS integration (Q8 RESOLVED 2026-05-22 — full scope per user)

NeuralNetScene integrates the full SGGS product per `sggs_v2_v3_product_feature_backlog_2026_05_06.md`. Four sub-systems land in v0.3, each demoable on its own gate.

**1. Gesture vocabulary (wks 1–6)** — the visible surface

`GestureLayer` runs MediaPipe Hands in a hidden Web Worker; emits `GestureEvent`s into NeuralNetScene via the `gestures.onGesture` callback. Base 10-gesture map:

| Gesture | Cockpit action |
|---|---|
| Pinch (two-finger, zoom in/out) | Zoom level Z0 ↔ Z5 |
| Open-palm swipe (left/right) | Token scrub backward/forward |
| Point + hold (1 sec) | Select neuron at cursor |
| Closed fist | Pause/play replay or live stream |
| Open palm raise | Reset camera (R shortcut equivalent) |
| Two-hand spread | Fit-to-selection (F shortcut equivalent) |
| Two-hand rotate | Orbit camera around model |
| Index-finger trace | Draw annotation onto canonical graph |
| Thumbs-up | Pin current neuron / region to bookmarks |
| Cup-hands gather | "Gather evidence" — opens Evidence Packet drawer with selected neurons |

**2. Canonical graph identity (wks 7–12)**

The model's neuron graph becomes the canonical graph object — every neuron coordinate (`L5N2648`) gets a stable ID that persists across sessions, users, and replay-vs-live. Annotations, bookmarks, comments, and witness records all anchor to canonical neuron IDs. Backend: graph identity service at `api/routes/sggs_graph.py` (v0.3-new); per-model graph manifest cached. The graph identity is the load-bearing object that makes SGGS data (gestures, annotations, witness records) portable across sessions.

**3. Live-witnessing protocol (wks 13–18)**

Multi-user co-presence as gesture overlays on the scene — when another user's hand gesture touches a neuron, you see their gesture as a colored hand-shape overlay, not just a cursor. Witness records (who-touched-what-when) persist on the canonical graph and surface inside Evidence Packets. Aligns with v0.3 collab broadcast above: extends `peerCursors` → `peerGestures` with full hand-shape data per peer.

**4. Rewind / slow-motion (wks 19–24)**

Gestures interact with the replay timeline. Pinch-out-during-replay slows time (0.25× speed); pinch-in-during-replay reverses time; palm-down freezes; two-hand-stretch zooms BOTH time and space simultaneously. Slow-motion is the headline demo behavior for "show me the moment the model picked this answer." Replay controller exposes a continuous time-warp factor consumed by gesture intent. Slow-motion + live-witnessing combine into the flagship demo surface.

**Privacy + data policy**

- Webcam feed never leaves the browser. MediaPipe runs entirely client-side.
- Explicit user consent prompt before first activation.
- Canonical graph IDs and witness records are user-controlled and exportable.
- SGGS gesture data and witness records do NOT feed the data-flywheel aggregation by default (separate opt-in from arch-graduation flywheel).

**Sub-deliverable gating**

Each 4–6 wk sub-phase ships a demoable surface. Full SGGS is not gated on completion of all four sub-systems before any user value lands:

- After wk 6: gesture vocabulary works on existing canonical-by-position neuron IDs (interim identity)
- After wk 12: canonical graph identity stable; bookmarks/annotations persist
- After wk 18: multi-user gesture overlays live
- After wk 24: full slow-motion + rewind interactions, flagship demo complete

---

## 14. Open questions

- **Q1.** Reference Three.js version — pin to current `SggsScene` version (~r150), or upgrade to latest stable as part of this work?
- **Q2.** Color-blind palette — Okabe-Ito as default, or as toggle? Affects R&D + alpha-partner appeal.
- **Q3.** Synthetic large-arch trace — synthesize from Pythia-160M scaled up, or wait until first real exploratory Llama run before testing LOD at scale?
- **Q4.** Bloom / post-processing — on by default, or off (performance-conservative)?
- **Q5.** WebGPU — fallback path for browsers without WebGPU support, or require WebGPU at v0.2?
- **Q6.** Foundation drive hue assignments — match an existing convention from `casColorPalette.ts`, or define fresh here?
- **Q7.** XL-class support (70B+) — at what parameter count do we refuse the model entirely vs render at maximum binning?
- **Q8.** ~~SGGS gesture depth~~ — **RESOLVED 2026-05-22:** full SGGS scope per product scope §9 Q9. See §13 for the four sub-systems and phasing.
- **Q9.** Live-stream LOD strategy on 8B+ archs — per-token full activation stream vs sparse "top-K activated neurons per token" delta encoding? Bandwidth-vs-fidelity tradeoff.
- **Q10.** Collab cursor rendering — show all peers as small avatars + hover circles, or only highlight the "focused" peer? Affects scene clutter at >3 concurrent users.

---

## 15. Sign-off

Sign-off required before any NeuralNetScene code lands (v0.0 / v0.1 / v0.2 scope):

- [ ] LOD strategy (§5) — bin sizes accepted
- [ ] Six zoom levels (§6) — list complete
- [ ] Hover / click contract (§7) — fields shown match Evidence Packet
- [ ] Color encoding (§8) — drive hue assignments approved
- [ ] Performance budget (§9) — targets accepted
- [ ] Test fixtures (§11) — Pythia-160M trace fixture committed
- [ ] Component interface (§12) — base prop shape accepted

Additional sign-off required before v0.3 code lands:

- [ ] Live frame shape (§13) — `LiveFrame` structure + delta-encoding strategy accepted
- [ ] Throttling + degradation path (§13) — backpressure + replay-fallback behavior accepted
- [ ] Collab cursor rendering (§13 + Q10) — peer display strategy chosen
- [ ] SGGS gesture vocabulary (§13) — base 10-gesture mapping accepted (Q8 RESOLVED full SGGS)
- [ ] SGGS canonical graph identity (§13) — manifest service contract accepted, backed by `api/routes/sggs_graph.py`
- [ ] SGGS live-witnessing protocol (§13) — peer-gesture rendering accepted, integrated with collab broadcast
- [ ] SGGS rewind / slow-motion (§13) — replay controller time-warp factor interface accepted
- [ ] SGGS sub-deliverable phasing (§13) — 4 × 4–6 wk gates accepted
- [ ] Privacy posture (§13) — MediaPipe-stays-client-side + SGGS data not in flywheel default confirmed in privacy policy
