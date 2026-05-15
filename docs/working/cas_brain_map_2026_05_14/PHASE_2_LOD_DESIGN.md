# CAS Brain Map — Phase 2 LOD Design

Date: 2026-05-15
Branch: `codex/mode7-neural-activity-map`
Status: Phase 2 spec (locks the visual language for Agent D's renderer build)
Companion to: `ARCHITECTURE_AND_DESIGN.md` (Phase 1 — far-view sphere graph + MOCK FLOW)

This document specifies how the CAS Brain Map deepens past the v1 "single colored sphere per layer" view into a multi-resolution renderer. Three Level-Of-Detail (LOD) tiers — **far**, **medium**, **close** — let a viewer zoom from the whole-pipeline graph all the way into a single matrix's downsampled weight grid and watch a mechanically-accurate matrix-vector animation. The honest-labeling discipline from Phase 1 is preserved at every level: MOCK FLOW where the flow is scripted, real-weight provenance shown wherever real weights are rendered.

Agent D builds against this spec. The integrator agent stitches it into the existing far-view scene. The wording for the close-view info panel is locked verbatim so different agents converge on the same text.

---

## 1. The LOD pattern + camera-distance triggers

### Primitive

Three.js ships a built-in `THREE.LOD` object (a `Group`-like container that swaps which child is rendered based on camera distance). It is the right primitive for this job. Each layer in the brain map becomes a single `LOD` instance with three children attached at three distance bands:

```js
const layerLOD = new THREE.LOD();
layerLOD.addLevel(farMesh,    250);   // shown when camera is >= 250 units away
layerLOD.addLevel(mediumMesh,  80);   // shown when camera is 80..250 units away
layerLOD.addLevel(closeMesh,    0);   // shown when camera is <  80 units away
layerLOD.position.set(x, y, z);       // layer's anchor in scene space
scene.add(layerLOD);
```

`THREE.LOD` does the swap silently on every `updateMatrixWorld()` pass; no event listeners, no manual visibility flips. The OrbitControls instance keeps its existing camera control behavior — the user just zooms, and the renderer chooses which detail level to draw.

### Distance thresholds (initial values — tune in QA)

| Level | Camera distance to layer | Visual |
|---|---|---|
| **Far** | >= 250 units | One colored sphere + halo per layer (current Phase 1 view) |
| **Medium** | 80 - 250 units | The sphere "opens" into 1-4 family-colored sub-structure plates |
| **Close** | < 80 units | The layer fills the viewport; sub-matrices render as instanced sphere grids |

These thresholds are the starting point. Agent D tunes them empirically during integration so transitions feel natural at the default camera framing in the dashboard. The numbers are stored as named constants in the renderer (`FAR_THRESHOLD`, `MEDIUM_THRESHOLD`) — not magic numbers scattered across the code.

### Boundary behavior

- Crossing a threshold: the `LOD` object swaps which child is rendered. The swap is single-frame; there is no fade. (A future enhancement can add a 200ms crossfade — out of scope for Phase 2.)
- OrbitControls is unchanged. The camera-control state (pan, orbit, zoom) survives the swap because the `LOD` object's `position` is fixed; only the rendered child changes.
- The user does not see a click target change. A `Raycaster` against the `LOD` parent picks whichever child is currently visible.

### Reset view

In the viewport's top-right corner, a small text button labeled **Reset view** flies the camera back to its default far-distance framing over ~1 second using an `easeInOutCubic` tween. Default framing is the one Phase 1 ships with (whole pipeline visible, gentle 3/4 isometric angle). After the tween completes, the LOD level is automatically `far` because the camera is now distant.

The Reset view button is always visible regardless of LOD level. It is the "I got lost" escape hatch.

---

## 2. Visual language per level

The visual language is consistent across families: every level uses the same family-color palette from Phase 1 (encoder_attn = blue, encoder_ffn = green, decoder_attn = purple, decoder_ffn = teal, special_branch = amber, embedding = gray, output = gold). LOD changes *what* is rendered, not *which colors*.

### 2.1 Far view (unchanged from Phase 1)

- One sphere per layer, family-colored, with a soft halo.
- Bouncing-ball thought packet animates between spheres along the pipeline edges. Evidence label on the packet: `MOCK FLOW`.
- This is the Phase 1 product. Phase 2 does not modify it.

### 2.2 Medium view — sub-structure plates

When the camera enters the medium band, the layer's single sphere is replaced by a small cluster of flat sub-structure plates arranged around the layer's anchor position. Each plate is family-colored, faintly emissive, and labeled with the sub-matrix name plus its tensor dimensions (e.g. `Q [512, 512]`).

Plates are flat rectangular `PlaneGeometry` panels (~2 units wide x ~1.5 units tall) facing the camera (or billboarded if the user orbits). They render with a thin glowing outline so they read as "panels of substructure" rather than free-floating quads.

Plate count and arrangement per family:

| Family | Plate count | Arrangement | Plates |
|---|---|---|---|
| `embedding` | 1 | single large plate at anchor | `weight [rows x cols]` |
| `encoder_attn` | 4 | 2x2 grid around anchor | top-left `Q [d, d]`; top-right `K [d, d]`; bottom-left `V [d, d]`; bottom-right `O [d, d]` |
| `encoder_gate` | 2 | side by side | `gate [d, d]`; `projection [d, d]` |
| `encoder_ffn` | 2 | stacked vertically | top `up-proj [d, 4d]`; bottom `down-proj [4d, d]` |
| `decoder_attn` | 4 | 2x2 grid around anchor (same layout as encoder_attn, distinguished by purple family color) | `Q`, `K`, `V`, `O` |
| `decoder_ffn` | 2 | stacked vertically | top `up-proj [d, 4d]`; bottom `down-proj [4d, d]` |
| `special_branch` | 1-3 (branch-dependent) | radial fan from anchor | Topos Reasoner: 1 plate `proposition_head [d, 3*P]`. Inversion Detector: 1 plate `axis_head [d, 7]`. Typed Fiber Decoder: 3 plates `simplex_proj [40, d]`, `src_token_proj [d, d]`, `slot_type_head [d, 9]`. RegisterFiLM: 1 plate `film [R, 2d]` (gamma/beta). LacunarityGate / LacunarityHead: 1 plate each. |
| `decoder_head` / `output` | 1 | single large plate at anchor | `lm_head [d, V]` |

Dimensions (`[rows x cols]`) are read from `cas_brain_weights.json` (Agent B's deliverable). Each plate label shows the actual shape from the trained v0.2 checkpoint. If a plate's shape is unavailable in the JSON, the label falls back to `[?, ?]` and the renderer logs a warning to the console.

Hovering over a plate in the medium view shows a tooltip with the sub-matrix name, dimensions, and parameter count.

### 2.3 Close view — instanced sphere grids

When the camera enters the close band, the focused layer fills most of the viewport. Each plate from the medium view is replaced by a **32 x 32 grid of instanced spheres** rendered through `THREE.InstancedMesh`. Each sphere's position corresponds to one cell of the downsampled weight matrix; each sphere's color encodes the weight value at that cell.

Color mapping (perceptual diverging palette):

- Negative weights → blue. The more negative, the deeper the blue.
- Near zero → white (and slightly translucent so the grid reads as "quiet" in that cell).
- Positive weights → red. The more positive, the deeper the red.

Concretely, weight value `w` (normalized to `[-1, +1]` against the per-matrix max-absolute value provided in `cas_brain_weights.json`) maps through a continuous lerp:

```
w <  0: lerp(white, blue, |w|)
w >= 0: lerp(white, red,  |w|)
```

This is the standard "RdBu_r" diverging palette used in mechanistic interpretability visualizations. Familiar to anyone who has seen an attention head visualization.

When the camera is *very* close to a grid (camera-to-grid distance < 30 units), a small floating numeric label appears above each sphere showing its weight value to 2 decimal places. The labels render as `THREE.Sprite` instances so they always face the camera. At default close-view distance the labels are hidden (would be too cluttered); they only appear on extreme zoom-in.

### 2.4 Multi-matrix close-view layout

For multi-plate layers (e.g. `encoder_attn` with Q/K/V/O), the close view places all four sphere grids in the same 2x2 arrangement the medium view used — same anchor positions, same relative offsets — so the transition from medium to close reads as "the plates filled in with their grids" rather than "the layer rearranged itself."

For single-plate layers (`embedding`, `decoder_head`, etc.) the close view is a single grid centered on the anchor.

---

## 3. Matrix-vector animation in close view

Each grid in close view animates a **matrix-vector multiplication** that mirrors what a real forward pass does mechanically. This is the load-bearing pedagogical animation of Phase 2 and the bridge to future Mode 7 wiring.

### 3.1 Single-matrix sequence (~1.5s)

When the thought packet "enters" this layer in the global far-view timeline, the close view plays the following animation on the focused grid:

1. **Input vector enters from the left** (~300ms). A 1 x 32 row of 32 glowing dots slides in from outside the grid's left edge and parks one column-width to the left of the matrix's leftmost column. The dots glow at family-color intensity. They represent the input row vector being multiplied against the matrix.
2. **Column-by-column dot product** (~900ms). Each column of the matrix brightens for ~25ms in left-to-right sweep order. As each column brightens, the corresponding cell of the *output* vector (which is forming to the right of the matrix) appears with brightness proportional to the dot product of that column with the input vector. This is the literal mechanical computation: column `j` of the output = sum over `i` of `input[i] * matrix[i, j]`.
3. **Output vector emerges from the right** (~300ms). The fully-formed 1 x 32 output row slides out to the right, taking the matrix's brightness with it (the matrix dims back to its resting color over ~200ms).

Total animation length: ~1.5s. It loops on the active layer until the user navigates away (changes layer focus, exits close view via ESC, or hits Reset view).

### 3.2 Multi-matrix chain (attention layers)

For multi-sub-matrix layers (Q / K / V / O for attention), the animations chain in sequence to reflect the real attention computation:

1. Input vector enters the layer (from the left of the Q grid).
2. Q grid fires (~1.5s): input -> Q -> query vector emerges.
3. K grid fires (~1.5s, in parallel a clone of the input slides up to it): input -> K -> key vector emerges.
4. V grid fires (~1.5s, in parallel): input -> V -> value vector emerges.
5. **Combine step** (~500ms): the query, key, and value vectors converge at a small visual junction between the four grids. A faint connecting line lights up between Q -> K (the attention scores) and that line fires the value vector through.
6. O grid fires (~1.5s): the combined attended-value vector enters O from the left -> O -> final output emerges from the right.

Total animation length per attention layer: ~6.5s. The Q/K/V phase plays in parallel (steps 2-4 overlap), so wall-clock is closer to ~3.5s. Loops until the user navigates away.

This sequence is mechanically accurate to what a real multi-head attention layer does. **Document it that way in the info panel.** The viewer is watching a slowed-down, visualized forward pass — not a metaphor for one.

### 3.3 FFN chain

For FFN layers with `up-proj` + `down-proj`:

1. Input vector enters up-proj from the left (~300ms).
2. up-proj fires (~900ms): input -> expanded 4d vector emerges from the right.
3. The expanded vector slides down to the down-proj grid (~200ms).
4. down-proj fires (~900ms): expanded vector -> compressed d-dim output emerges from the right.

Total: ~2.3s. Loops until the user navigates away.

### 3.4 Gate / single-plate layers

For single-plate layers (gate, embedding, lm_head, special branches with one plate): the standard 1.5s single-matrix sequence from Section 3.1.

---

## 4. Honest-labeling discipline at each level

The honest-labeling discipline from Phase 1 is preserved at every LOD level. The exact wording is locked below; Agent D copy-pastes it verbatim.

### 4.1 Far / Medium view — evidence label

Unchanged from Phase 1. The bouncing-ball thought packet displays evidence label:

```
MOCK FLOW
```

The packet is still scripted in v1. Real Mode 7 wiring is a follow-up scope item; until then, the label stays.

### 4.2 Close view — side info panel

When the camera enters the close band, a side info panel appears in the right ~30% of the viewport (or as a draggable floating panel — Agent D picks layout based on existing dashboard chrome). The panel renders the following content, with the curly-brace placeholders filled from the focused layer's metadata + `cas_brain_weights.json`:

```
{Layer Label}
{family} · {paramCount} parameters

Weight grid: Showing {downsampled_grid x downsampled_grid} of
{full_param_count} weights. Each cell averages
{full_param_count / (downsampled_grid * downsampled_grid)} real
weights from the trained v0.2 checkpoint (checkpoint id
30019a89-f75a-42f1-816b-f29f2df7fe4b, sha256 prefix
{first_8_chars_of_sha256}).

Activation pulses: Illustrative — labeled MOCK until Mode 7 live
capture is wired through. The animation shows what a real forward
pass would do mechanically: input vector multiplied across rows,
output emerges.

What this layer does: {family-specific 2-sentence explanation
from Section 4.3 below}
```

Title size: ~18pt sans-serif, family color. Sub-title: ~12pt, muted gray. Body: ~13pt regular weight, white-on-dark, line-height 1.5. The three labeled blocks are visually separated by ~12px vertical spacing and each label is bolded.

The checkpoint id `30019a89-f75a-42f1-816b-f29f2df7fe4b` is the trained v0.2 checkpoint that Agent B's `cas_brain_weights.json` was extracted from. The sha256 prefix is the first 8 hex characters of the checkpoint file's sha256 sum, read from `cas_brain_weights.json`'s `meta.checkpoint_sha256` field at render time.

If `cas_brain_weights.json` reports `meta.source = "FALLBACK_SYNTHETIC"` (Agent B's fallback path triggered), the **Weight grid** line is replaced verbatim with:

```
Weight grid: Showing {downsampled_grid x downsampled_grid}
SYNTHETIC weights. Pod checkpoint extraction failed; this grid is
illustrative, not derived from the trained v0.2 checkpoint. Re-run
extraction to see real weights.
```

and a yellow banner stripe (~4px tall, full panel width) renders at the top of the panel reading: `SYNTHETIC WEIGHTS — illustrative only`.

### 4.3 Plain-English "what this layer does" lines (one per family)

These are the exact strings the info panel uses. Plain language, no jargon, two sentences each.

**`embedding`** (token_embedding + cognitive_state_embedding + positional_encoding):
"This layer turns input tokens into numbers the model can work with. Each token gets a unique vector; position information and CAS state information get added in on parallel branches."

**`encoder_attn`** (DomainDescentAttention):
"This layer decides which CAS Domain (P / C / E / O) your thought belongs to. The Q / K / V projections build a query-key-value space; the output projection blends the attended values back into the model's main stream."

**`encoder_gate`** (PrerequisiteGateLayer):
"This layer enforces RPM — the rule that a thought can't 'fire' unless its prerequisites have already been satisfied. The gate decides whether downstream layers see the signal."

**`encoder_ffn`** (encoder feed-forward block):
"A two-layer MLP that mixes the dimensions of whatever the attention layer just attended to. This is where most of the model's 'pattern memory' lives — the FFN weights store what kinds of features go with what."

**`special_branch`** (Topos Reasoner / Inversion Detector / Lacunarity / Expression Proposer / Typed Fiber side branch — branch identity shown in the sub-title):
"This is a parallel head that reads the encoder's final state and produces its own structured output — truth values, inversion scores, lacunarity scores, or typed CAS tokens. It runs alongside the main pipeline rather than in series."

**`decoder_attn`** (decoder self-attention + cross-attention):
"This layer mixes the partially-generated output with the encoded input. The self-attention block looks at what's been generated so far; the cross-attention block looks back at the encoded source so the next token stays grounded."

**`decoder_ffn`** (decoder feed-forward block):
"A two-layer MLP on the decoder side, mirroring the encoder FFN. It refines the cross-attended representation before the next decoder block sees it."

**`decoder_head`** (RegisterFiLM modulation):
"This is the Phenomenological Register modulator. It multiplies the decoder hidden state by a register-specific gamma/beta pair, steering the same content into transcendent, analytical, affective, or embodied operational character."

**`output`** (lm_head):
"The final projection from the model's hidden dimension to the English vocabulary. Each output position becomes a probability distribution over all possible next tokens; the highest-scoring token gets generated."

These strings live in a single `LAYER_EXPLANATIONS` constants module in the renderer so Agent D imports them once and a future copy edit lands in one place.

---

## 5. Reset view + Tour mode controls

Close view can disorient a user — at 1024 spheres per grid, it is easy to lose the overall pipeline frame. The Phase 2 viewport adds three UI affordances to recover orientation.

### 5.1 Reset view button

- **Location**: top-right of the viewport, ~16px inset from the corner.
- **Visual**: small text button, dark background, white sans-serif "Reset view" label, soft border.
- **Behavior**: on click, tweens the camera from its current position back to the Phase 1 default far framing over ~1 second using `easeInOutCubic`. After the tween, the LOD level is automatically `far` because the camera is now distant.
- **Always visible**, regardless of current LOD level.

### 5.2 Tour mode toggle

- **Location**: directly below Reset view in the top-right cluster.
- **Visual**: text toggle reading "Tour mode: off" / "Tour mode: on". When on, the toggle is family-color-tinted.
- **Behavior**: when enabled, the camera automatically orbits and slowly zooms into the layer that the current thought packet is firing through, so the viewer sees the close view of each layer in sequence as the MOCK FLOW packet walks the pipeline. After the packet exits a layer the camera tweens to the next active layer. After the packet exits the model the camera tweens back to far framing.
- This is the cinematic mode for stakeholder demos and screen recordings. Hands-free.
- Tour mode is mutually exclusive with manual OrbitControls: while Tour mode is on, manual orbit / zoom is disabled. Clicking Tour mode off restores manual controls.

### 5.3 ESC key

- Pressing **ESC** at any time cancels close view and resets the camera to far framing (same tween as Reset view). If Tour mode is on, ESC also disables Tour mode.

These controls live in the existing dashboard chrome overlay so they survive scene re-renders.

---

## 6. Performance + perf budget

The close-view sphere grids are the heaviest geometry in the scene. Phase 2 commits to the following performance envelope.

### 6.1 Instancing

Each 32 x 32 sphere grid is a single `THREE.InstancedMesh` of 1024 sphere instances. A multi-plate close-view layer with 4 grids (attention with Q/K/V/O) is 4 InstancedMeshes = 4096 instances total. This is cheap on any GPU released in the last decade. Per-instance color is set through the instanced color buffer, not per-instance materials.

### 6.2 Focus pattern: dim and cull non-focused layers

When close view is active on layer L, every other layer in the scene drops to:

- Material alpha = 0.2 (rendered as a faint ghost).
- All animations paused (no halo pulse, no bouncing thought packet on those layers' edges).
- LOD frozen at the `far` level regardless of camera distance, so distant layers do not accidentally render their own close-view grids when the camera happens to swing close to them while focused elsewhere.

This is the "focus" pattern. It cuts both the visual and the perf cost of close view dramatically — only the focused layer's full grid renders, everything else is one cheap sphere.

### 6.3 Frame budget

Total scene budget: **<= 16ms per frame (60fps)** on a mid-tier laptop GPU (think Intel Iris or M1 base). Agent D measures this with `stats.js` during integration and adjusts.

If frame time creeps above 16ms during close view:

- First reduction: downsample non-focused layers' grids from 32 x 32 to 16 x 16 (4x fewer instances per non-focused layer). Phase 2 already downsamples grids dramatically (1024 cells per matrix vs hundreds of thousands of real weights); a further 4x reduction on dimmed layers is invisible to the viewer.
- Second reduction (if still over budget): in the focused layer, drop the per-sphere floating numeric labels (Section 2.3 — they only render at extreme zoom-in anyway).
- Third reduction (rarely needed): drop the matrix-vector animation's per-column brightening pass to a single combined glow on the full matrix.

These reductions are conditional optimizations, not defaults. Default Phase 2 runs at full 32 x 32 grids with column-by-column animation.

### 6.4 Memory

`cas_brain_weights.json` is loaded once at scene init and held in memory as a parsed `Map<layerId, downsampled grid>`. Expected file size: a few MB (single-precision floats for ~33 layers x ~4 plates x 1024 cells = ~135k floats = ~540KB raw, plus JSON overhead). Negligible.

---

## 7. Failure modes + fallbacks

The renderer assumes `cas_brain_weights.json` is present and well-formed. Phase 2 handles the two realistic failure modes explicitly.

### 7.1 JSON load failure

If `cas_brain_weights.json` fails to load (404, network error, parse error):

- Close view still renders, but every grid shows **random uniform-distributed weights** in `[-1, +1]`.
- A warning banner appears at the top of the viewport (full width, ~24px tall, red background, white text):
  ```
  Real weights unavailable. Showing illustrative random grid. Reload to retry.
  ```
- A "Reload" text button on the right side of the banner re-attempts the JSON fetch.
- The close-view info panel's **Weight grid** line is replaced with:
  ```
  Weight grid: Real weights failed to load. Showing illustrative
  random values. The model architecture and layer connectivity above
  are still accurate; only the per-cell color encoding is placeholder.
  ```
- The MOCK FLOW evidence label on the bouncing thought packet stays unchanged.

### 7.2 Synthetic-fallback shape

If `cas_brain_weights.json` loads successfully but `meta.source` reads `FALLBACK_SYNTHETIC` (Agent B's fallback path triggered — pod checkpoint extraction failed and Agent B emitted a deterministic synthetic dataset of the correct shape):

- Close view renders the synthetic grids (they have the correct shapes, just not real-checkpoint values).
- A **yellow** banner appears at the top of the viewport (full width, ~24px tall, yellow background, dark text):
  ```
  Showing SYNTHETIC weights — pod checkpoint extraction failed.
  Re-run extraction to see real v0.2 weights.
  ```
- The close-view info panel's **Weight grid** line is replaced with the synthetic-weights wording from Section 4.2 above, and the panel renders its own ~4px yellow banner stripe at the top reading `SYNTHETIC WEIGHTS — illustrative only`.

Both banners (red for load failure, yellow for synthetic fallback) are non-dismissable while the failure condition holds. The viewer cannot accidentally forget that what they are looking at is not real-checkpoint data.

---

## 8. Acceptance criteria for the full Phase 2

Phase 2 is complete when all nine items below verify against the integrated build. Agent D self-checks; the parent integrator confirms; the user signs off.

1. **LOD swap works**: Three.js `LOD` objects swap children at the camera-distance thresholds in Section 1. Crossing 250 units (far <-> medium) and 80 units (medium <-> close) triggers the right child render with no manual visibility flipping in the calling code.
2. **Medium view structure**: every layer renders the correct number of plates per Section 2.2 (embedding: 1, encoder_attn: 4 in 2x2, encoder_gate: 2, encoder_ffn: 2 stacked, decoder_attn: 4 in 2x2, decoder_ffn: 2 stacked, special_branch: 1-3 depending on branch, decoder_head/output: 1), each labeled with the correct sub-matrix name and dimensions read from `cas_brain_weights.json`.
3. **Close view grids**: each plate's close-view replacement is a 32 x 32 `THREE.InstancedMesh` of 1024 spheres, with per-cell color following the RdBu_r diverging palette in Section 2.3 against real (or fallback-synthetic) downsampled weight values from `cas_brain_weights.json`.
4. **Matrix-vector animation**: close view runs the input-enters / column-by-column-fires / output-emerges sequence from Section 3 on the focused layer; multi-matrix layers chain (attention: Q || K || V -> combine -> O; FFN: up-proj -> down-proj); the animation loops until the viewer navigates away.
5. **Info panel wording locked**: close-view info panel renders the exact text from Section 4.2, with the family-specific "what this layer does" sentence from Section 4.3 selected by the focused layer's family. Checkpoint id `30019a89-f75a-42f1-816b-f29f2df7fe4b` and the sha256 prefix appear verbatim.
6. **UI controls**: Reset view button flies the camera back to far framing over ~1s; Tour mode toggle auto-orbits through layers in sync with the MOCK FLOW packet; ESC cancels close view.
7. **Focus dim**: while close view is active on a layer, every other layer drops to alpha 0.2, animations paused, LOD frozen at far.
8. **60fps on mid laptop**: scene runs at <= 16ms per frame in close view on a baseline mid-tier laptop GPU (Intel Iris / M1 base / equivalent).
9. **Honest labeling preserved**: `MOCK FLOW` evidence label still on the bouncing thought packet at far/medium; close-view info panel labels weight grids as downsampled real values with checkpoint provenance OR as synthetic with the synthetic banner; activation pulses labeled as illustrative pending Mode 7 wiring; banners render correctly for both JSON failure modes.

When all nine items pass, Phase 2 ships and the close-view LOD becomes the primary "show your work" interpretability surface in the dashboard — the place a non-ML stakeholder can zoom into and watch a real (downsampled) matrix do a real (mechanically-accurate) forward pass while the labeling discipline keeps the honesty boundary visible at every level.
