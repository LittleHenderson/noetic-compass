# Exposure Button — Model Traceability Specification

**Status:** initial design draft
**Decision date:** 2026-05-04 — locked in for Version B Phase 6 (Production Wrap), with cross-cutting data-emission requirements landing in Phase 2 (Dialogue State Tracker) onward.
**Owner:** Version B conversational track

---

## 1. Why this exists

Version B's thesis is that **NL is the front door INTO the CAS engine** — not a wrapper around a base model, not a chat shell over structured prediction. If users cannot see the CAS engine working, the spine is invisible and the differentiator is wasted.

The exposure button is the affordance that surfaces the model's structural trace. It is the "show your work" mode that distinguishes Version B from any wrapper-around-base-model approach. It is also the legibility layer that makes the framework defensible to regulators, ethicists, and pedagogical audiences.

**Design principle:** the trace is a first-class output of every model turn, equal in status to the rendered NL response. Any architecture decision that treats the trace as internal-only or discards it during rendering breaks the exposure button and is to be rejected.

---

## 2. Seven exposure modes

### Mode 1 — Cognitive State Exposure

**What it shows:** the model's CURRENT cognitive state vector, rendered as the Radial Architecture Display (4 rings: Domain compass + 40 Noetic petals + Register quadrants + Drive markers).

**Renderer:** `dashboard/src/components/RadialArchitectureDisplay.tsx` (already built, Phase A complete per `docs/design/cas_v7_5_multimodal_display_specification.md`).

**Data shape consumed:**
```ts
{
  noetics: number[10],           // 10-vector activation
  domains: Record<Domain, number[10]>,  // 4 × 10 matrix (Domain × Noetic)
  drives: number[7],             // F1-F7 activation
  registers: number[4],          // T/A/f/E activation
  activationMap: Record<string, number>
}
```

**Model emission requirement:** every turn outputs a `cognitive_state_data` field alongside the rendered text. Phase 2 (Dialogue State Tracker) is the latest this can be deferred to.

**User affordance:** click "Show State" → side panel slides in with the radial display. Hover any cell → cell-detail overlay.

---

### Mode 2 — Idea Atlas Exposure

**What it shows:** every CAS expression encountered during the conversation as a force-directed graph. Nodes = ideas (the user's, the model's, intermediate states), colored by content. Edges = cosine similarity over Noetic/Domain/Drive/Register vectors.

**Renderer:** `dashboard/src/pages/IdeaAtlasPage.tsx` + `dashboard/src/components/idea-atlas/GraphView.tsx` (already built).

**Data shape consumed:**
```ts
{
  ideas: { id, text, cas_expression, cas_english?, created_at, compile_error? }[],
  edges: { source, target, score, breakdown }[]
}
```

**Backend:** `api/routes/idea_atlas.py` already exists with `GET /idea_atlas/edges`, `POST /idea_atlas/invert`.

**Model emission requirement:** session-scoped idea log accumulates every CAS expression the model parses or produces. On exposure, the log is POSTed to the existing edge-similarity endpoint and rendered.

**User affordance:** "Show Atlas" button surfaces the graph in a modal. Click any node to expand idea detail. Inversion controls per node (already implemented backend-side).

---

### Mode 3 — Per-Utterance Trace

**What it shows:** for any model utterance, the chain that produced it:
1. `user_text` (raw input)
2. `parsed_intent_CAS` (model's CAS interpretation of what the user said)
3. `pre_state` (cognitive state before this turn)
4. `applied_operators` (sequence of admissible operators, with admissibility-check results)
5. `post_state` (cognitive state after operators)
6. `output_CAS` (the model's CAS-formed reply)
7. `compiler_validation` (compiler ack or error)
8. `rendered_text` (the NL response shown)

**Renderer:** NEW component required. Vertical timeline of stages with collapse/expand on each. Each stage shows the structured artifact + a one-line plain-English explanation.

**Model emission requirement:** every turn writes a structured trace record alongside the response. Phase 2 must produce this; Phase 3 (NL Generation Head) must not destroy it.

**User affordance:** any model bubble in the chat has a small "trace" icon. Click → trace timeline opens beneath the bubble.

**This is the deepest pedagogical surface.** When users want to learn the framework, this is what teaches them.

---

### Mode 4 — Production Recipe Exposure (CAS v7.6)

**What it shows:** when the user names an outcome (e.g., "I want to feel calm before this meeting"), surface the v7.6 production recipe:
```
Θ(Ω = "calm before meeting") = a₁·X₁ + a₂·X₂ + … → Ω
```
with limiting reagent, theoretical yield Y_T, observed (current) state, predicted yield Y_A, efficiency η, and any leakage Λ detected.

**Renderer:** NEW component. Stoichiometry-style diagram: prerequisite primitives as boxes with required vs current quantities, arrow to outcome, limiting-reagent highlighted, leakage flagged separately.

**Model emission requirement:** triggered when the model parses an outcome-naming utterance. Recipe inference is a CAS v7.6 operation — the model must be able to instantiate Θ(Ω) for any named outcome. Phase 5 (Coherence Eval) needs a recipe-fidelity metric.

**User affordance:** "Show Recipe" appears on the model's response bubble whenever the response is goal-oriented or recipe-relevant.

**Pedagogical value:** this is the surface where users see the v7.6 production semantics in action — strong differentiator for goal-coaching use cases.

---

### Mode 5 — Inversion Scan Exposure

**What it shows:** the 7-axis inversion scanner run over the conversation so far:
- N: operator/Noetic involution imbalance
- W: domain precedence violation
- F: drive pair imbalance
- E: state-vector entropy deficit
- S: sub-drive cross-domain variance
- A: pathway RPM chain violation
- P: compound (multiple axes simultaneously)

Any axis exceeding threshold is surfaced with explanation.

**Renderer:** NEW component. 7-axis radar with current-conversation values plotted against safety thresholds. Anomalies highlighted.

**Model emission requirement:** inversion scanner runs over the rolling conversation history. Real-time, not just on-demand — flagged inversions should be surfaced even if the user does not click the button (this is the safety layer).

**User affordance:** "Show Drift" button. If any axis is currently flagged, the button itself shows a warning indicator without being clicked.

**This is the AI-safety surface.** Answers "is the model drifting?" in legible CAS terms.

---

### Mode 6 — Counterfactual Exposure (epistemic humility)

**What it shows:** for the model's CAS interpretation of the user's last turn, the top-5 alternative interpretations the model considered, with confidence scores and "why this one was chosen over that one" explanations.

**Renderer:** NEW component. Ranked list of alternative CAS expressions with delta-confidence and short rationale per pair.

**Model emission requirement:** the structured-prediction head already produces probability distributions over each axis (Noetic, Domain, Drive, Register). Top-K alternatives can be derived from those distributions. Phase 3 (NL Generation Head) must preserve them.

**User affordance:** "Other Reads" button on user-turn bubbles. Click → see what else the model considered.

**Distinguishes confident reads from forced reads.** Surfaces the model's epistemic humility, addresses overconfidence concerns directly.

---

### Mode 7 — Network Attribution / Mechanistic Trace

**What it shows:** the CAS thought traced through the actual neural substrate, in two directions.

**Forward direction (inception → output):**
For a given turn, the activation flow through every named layer:
1. **Embedding layer** — which input token embeddings were dominant
2. **Each transformer block** — attention pattern per head, MLP activation profile, residual stream contribution
3. **CAS-named architectural components** — DomainDescentAttention (which Domain mask was load-bearing), PrerequisiteGateLayer (which RPM gates opened/closed), FractalAttentionHead (IFS contraction patterns), CognitiveToposReasoner (intuitionistic logic path fired)
4. **Final heads** — per-axis logit distributions feeding into the structured prediction

**Backward direction (output ← network):**
For any predicted CAS atom (e.g., "the model said `^2^P_{F2}|A`"), reverse-attribute the prediction to:
- Input tokens that contributed most (gradient × input or integrated gradients)
- Attention heads that routed information toward this prediction (path patching)
- MLP neurons whose ablation would change the prediction (activation patching)
- Layers whose intermediate state was load-bearing (logit lens / direct logit attribution)

**Why this matters for Version B specifically:**
Vanilla transformer interp produces statements like "block 7 head 4 was important." Version B's named CAS architectural components produce statements like **"the Domain Descent layer was the load-bearing component for shifting from C-domain to P-domain on this turn."** That is a categorically more legible interpretability claim than any black-box LLM can offer, and it is the strongest single differentiator the architecture has.

**Renderer:** NEW component. Layer-by-layer flow diagram with activation heatmaps. Toggleable forward/backward direction. Click any neuron / head / layer to see its contribution to a chosen CAS atom. Visual style: vertical stack of layer cards, each with attention pattern thumbnails + top-K active neurons; selected CAS atom in the trace highlights its attribution path through the stack.

**Model emission requirement:**
- **Hook-based activation capture** in the model: PyTorch forward hooks on every named layer, registered at model construction. Phase 0 must preserve these hooks; Phase 2 must extend them to multi-turn.
- **Sparse top-K storage** for live exposure: store only the top-K most-active neurons per layer per token (K≈32). Estimate: ~200 KB per turn vs ~24 MB raw. Acceptable for in-session storage.
- **Replay-on-demand for forensic deep-dive:** keep the input + RNG state; rerun the model with full activation capture when the user clicks deeper than the live trace supports. Trades latency (~50-200ms per replay) for storage.
- **Attribution algorithms:** at minimum direct logit attribution + attention attribution at Phase 6 launch. Activation patching and integrated gradients added in a Phase 5+ research track.

**User affordance:** "Show Network" button on any model utterance. Opens a dedicated panel (not a side overlay — this is the densest visualization). Defaults to forward-direction view. User can select any CAS atom in the trace → switch to backward-attribution view automatically. "Replay with full capture" button for forensic mode.

**Pedagogical value:** unmatched. This is the surface where Version B answers the question "but how does the model actually think this?" with a real, mechanically-grounded answer. Demo-able to ML researchers, regulators, and skeptical reviewers.

**Phase 5+ research track (parallel, separate from Phase 6 launch):**
Train sparse autoencoders on the locked Phase 6 model's activations to discover interpretable features. Each feature gets a CAS-aligned label (e.g., "this feature fires on Cognitive-domain ^2 Positive content under Analytical register"). Surfaced in Mode 7 as "this neuron resembles feature #1247: Cognitive-Positive-Analytical." Distinct research effort, not on the launch critical path, but the activation capture infrastructure built for live Mode 7 is the input to it.

---

## 3. Cross-cutting requirements per phase

| Phase | What it must do for the exposure button |
|---|---|
| **Phase 0: Foundation lock** | Preserve forward-hook instrumentation points on the current structured-prediction model. Do NOT strip hooks during "production cleanup." Mode 7 backfills against these. |
| **Phase 2: Dialogue State Tracker** | Emit `pre_state`, `transition`, `post_state` per turn. Maintain session idea log. Without this, modes 1, 3, 5 are impossible. Per-turn sparse top-K activation snapshot for Mode 7 — design in, not bolt on. |
| **Phase 3: NL Generation Head** | Decoder must NOT discard the CAS trace when rendering. Trace and rendered text are both first-class outputs. Top-K alternative distributions preserved (mode 6). NL Generation Head supports hook-based activation capture without breaking inference latency (Mode 7). |
| **Phase 4: Multi-Turn Curriculum** | Training includes trace-preservation as an objective. Loss penalizes fluent responses that lose trace coherence with their CAS state. |
| **Phase 5: Coherence Eval** | Add eval metrics for CAS-trace fidelity (mode 3) and recipe fidelity (mode 4). Add **mechanistic-trace fidelity** (mode 7): when the activation trace claims "Domain Descent layer was load-bearing," activation patching ablation should change the output by ≥X. |
| **Phase 5+ research (parallel)** | Sparse autoencoder training on locked Phase 6 model activations for interpretable feature discovery. CAS-aligned feature labeling. Inputs Mode 7 enrichment, not Phase 6 launch dependency. |
| **Phase 6: Production Wrap** | UI affordance (the button + side panels) + the **five NEW renderer components** (modes 3, 4, 5, 6, 7). Existing components for modes 1 and 2 reused. Mode 7 storage strategy commits: sparse top-K live + replay-on-demand forensic. |

---

## 4. Design principles

1. **Trace is first-class.** Equal in status to the rendered NL response. Any phase that treats it as internal-only or discards it is broken.

2. **Existing renderers reused where possible.** Modes 1 and 2 ride on `RadialArchitectureDisplay.tsx` and `IdeaAtlasPage.tsx` — no need to rebuild. Save engineering for the four NEW renderers (modes 3, 4, 5, 6).

3. **Real-time safety surface.** Mode 5 (Inversion Scan) is not on-demand only — it runs continuously and alerts even when the button is not clicked. This is the safety affordance.

4. **Pedagogical scaffolding by default.** Every renderer displays the structured artifact AND a plain-English explanation. The trace is meant to teach, not just to show.

5. **No emoji, no aestheticization in product surface.** The aesthetic heritage of the framework informs design but does not appear in product. Public-facing names are technical: "Cognitive State," "Idea Atlas," "Utterance Trace," "Production Recipe," "Drift Scan," "Alternative Reads," "Network Attribution."

6. **Defensible to regulators.** Every output the model produces has a structured trace. This is the audit surface. Build it from Phase 2 onward, not bolted on at Phase 6.

---

## 5. Anti-drift

If at any point in the Version B build-out someone proposes:

- "Let's emit the final response and skip the structural trace because the trace is internal-only" → REJECT. The trace is the differentiator.
- "Let's add the exposure button at the end as a UI flourish" → REJECT. The exposure button is a data-emission requirement that starts at Phase 2.
- "Let's compress the trace to save tokens" → CAREFUL. Compression is fine if all six modes can still be reconstructed; if any mode loses fidelity, do not compress.
- "Let's just expose the rendered text and let the user query the model again for the trace" → REJECT. The trace must be deterministically recoverable from the turn that produced it; second-pass reconstruction is not the same artifact.

---

## 6. Open questions

- Storage shape for per-session trace log: in-memory, on-disk, or DB-backed? Affects Phase 6 deployment design.
- Real-time inversion scan compute budget: is it cheap enough to run every turn or should it be sampled? Affects Phase 5 latency design.
- Counterfactual top-K: K=5 by default, but should K be user-configurable? Pedagogical preference.
- Multi-turn idea log decay: do old ideas in the atlas fade or stay forever? Affects mode 2 visual density at long sessions.

These questions get answered during Phase 2/3/5 implementation; flagging them now so they are not forgotten.
