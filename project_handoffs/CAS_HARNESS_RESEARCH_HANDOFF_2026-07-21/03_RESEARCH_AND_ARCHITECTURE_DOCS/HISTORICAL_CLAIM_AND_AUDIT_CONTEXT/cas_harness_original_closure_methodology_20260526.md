# CAS Harness — original closure methodology (reconstructed reference)

**Status:** Reconstruction from canonical artifacts on 2026-05-26.
**Sources:** `graphify-out/converted/CAS_HARNESS_SPEC_SHEET_v1_5_20260519_409e9efe.md`, Stage 27 smoke files (`research/cas_probe/.tmp/STAGE27{C,D,E,F,G,H,I}_SMOKE.md`), Stage 27P Qwen artifact.

**Purpose:** This is the full recipe that produced the closures on Pythia-160M, Pythia-1B, Pythia-2.8B, OLMo-1B, and Qwen2.5-1.5B. Every step lists its Pythia-160M comparator number so future runs on new substrates have explicit pass thresholds. Drift catches: each step also names the method that didn't work, so the chain isn't re-explored from scratch.

**2026-05-27 baseline correction:** 40-Element readout claims must use the exact scenario library's own modern text-only diagnostic. The compact-gloss TKS40 v0 library is **blocked for CAS-beats-text claims** because text-only reached 100.00%. The original Stage 9 role-bound/counterfactual fixture passed the text-only baseline gate: text-only CountVectorizer scored 49.241071%, evaluator text-hash scored 50.000%, and GPT-NeoX-20B hidden readout scored 95.625% on the same fixed split. Method label: `S9-40E-ORIGINAL-BASELINE-READOUT`. **2026-05-30 caveat:** external use of this as a detection-lift claim is held pending Stage LSA Arm A, which tests whether the original v1 items remain meaning-bearing after answer-key wording is stripped.

---

## The central mechanism — η → ε bridge

This is the load-bearing thing. Every "closure" below is a measurement of this bridge from a different angle. Without the bridge framing, the chain looks like an unrelated stack of probes and ablations. **It isn't.** All the chains converge on this one structural property:

### What the bridge is

- **η (eta)** = read CAS structure from the foreign model's hidden states. This is the probe layer.
- **ε (epsilon)** = realize that CAS structure as readable natural-language prefix tokens.
- **Bridge** = the loop in two forward passes:
  1. First forward pass: foreign model processes the prompt; η reads the CAS class from its hidden states.
  2. ε constructs a readable English prefix encoding that CAS class.
  3. The prefix is **prepended** to the original prompt.
  4. Second forward pass: foreign model now sees prefix + prompt and produces a next-token distribution.
  5. Measure the likelihood shift toward CAS-expected continuations.

This is **not** steering by ablation. Ablation tried to invert ε (zero out the structure) and was repeatedly null at the generation level (Stage 6.6, 7.3, 7.OA, 7.LA all failed). ε-realization succeeded (Stage 7.CPL, 7.CPL2, 8 all closed).

### Why the bridge works (and why this isn't accidental)

The Noetic Topos paper proves **Proposition 5.6**: the counit ε of the Noetic Coverage is a *surjective covering morphism*. The covering sieve contains ε.

Applied to transformer architecture: prefix tokens are attended to by every subsequent position **by architectural construction of self-attention.** This is not a tunable hyperparameter — it is the structural property of the attention mechanism. The covering-surjectivity of ε maps directly onto the all-to-all access pattern from later token positions to prefix positions.

So the bridge mechanism's success is **predicted by the topos theory** before any experiment runs. Four numerical predictions have held empirically:
- Stage 7 lacunarity prediction
- Stage 6.6 fractal classifier prediction (Oscillatory → steering will fail; held)
- Stage 7.CPL covering-surjectivity prediction (bridge will close; held)
- Stage 14.1 weight-geometry alignment prediction (held at p = 0.0099)

This is the highest-tier scientific evidence the framework produces: **pre-registered quantitative predictions that the data subsequently honored.**

### Section-retraction asymmetry (CLAUDE.md Correction 2)

- `ε ∘ η = id` (realize-after-embed = identity) — section law holds
- `η ∘ ε ≠ id` (re-embed-after-realize may lose information) — NOT an adjunction

**Operational implication:** ε is one-directional. Ablation attempts to invert ε structurally cannot succeed. This is **why ablation-based generation steering fails** while prefix-conditioning generation steering succeeds. The asymmetry is the load-bearing structural property, not a methodology choice.

---

## The system architecture (canonical block diagram)

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (Pythia / OLMo / Qwen / GPT-NeoX-20B / ...)
     │
     ├── Multi-layer hidden-state capture (last-token per layer)
     │       │
     │       ▼
     │   FOUNDATION / NOETIC / 40-ELEMENT PROBES (η₁)
     │   Linear classifiers per CAS axis
     │       │
     │       ▼
     │   MULTI-LAYER TRACE classifier (Stage 13)
     │   Stable-like vs problem-like flagging per prompt
     │       │
     │       ▼
     │   BLIND-SPOT DETECTOR (Stage 13.1)
     │   Per-class: model-side weakness vs readout-position weakness
     │       │
     │       ▼
     │   CAS structure label (e.g., "F3|E" or "^7|C")
     │       │
     │       ▼
     │   REALIZATION LAYER (ε) — emit readable English prefix
     │       │
     └───────┴── Prepend to original prompt
                  │
                  ▼
            FOREIGN MODEL — SECOND forward pass with prefix
                  │
                  ▼
            LIKELIHOOD SHIFT in next-token distribution
            EVIDENCE PACKET emitted with full audit trail
```

The Multi-Layer Trace + Blind-Spot Detector are NEW vs single-layer probing — Stage 13 introduced them and they materially improve signal. Single-layer probes are sufficient for one-axis inspection at small scales; multi-layer trace is needed for >1B-parameter models and for blind-spot detection.

---

## The six closed evidence tiers (canonical taxonomy)

This is the framing the spec sheet uses. Communicate scope to AI2 / regulators / reviewers in these terms — they're orthogonal, each provides independent evidence:

| Tier | What it proves | Pythia-160M / cross-arch headline |
|---|---|---|
| **1. Detection above text/metadata** | Hidden states linearly encode CAS structure beyond what raw text or metadata would predict | 28-Foundation 78.6%, +28.9 pp; 40-Element 89.8%, +39.7 pp |
| **2. Readout-causal validation** | The detected structure is causally necessary for the probe; not epiphenomenal | Foundation subspace ablation: 78.6% → 3.57% (exact 1/28 chance); random same-rank: no collapse |
| **3. Likelihood conditioning via η → ε bridge** | Prefix-conditioning the foreign model shifts its next-token distribution toward CAS-expected continuations | Pythia-160M +0.283; Pythia-1B +0.554; Pythia-2.8B +0.583; OLMo-1B +0.604; Qwen2.5-1.5B +0.796 |
| **4. Clean factorization (lacunarity)** | The Foundation subspace is geometrically clean, not entangled | Pythia-160M 0.021 (vs Noetic 0.793); Stage 13 multi-layer 0.0016 (cleanest in project) |
| **5. Framework-predictive validity** | Pre-registered numerical predictions from the topos theory have held empirically (4 of 4) | Stage 7 lacunarity / Stage 6.6 fractal / Stage 7.CPL covering / Stage 14.1 weight-geometry — all pre-registered, all held |
| **6. Output-weight geometric alignment** | The foreign model's static weights (not just activations) show CAS-direction alignment | Pythia-2.8B: 2.83× random expectation, p = 0.0099; input-side basically random |

**Six tiers, three architecture families (EleutherAI / AI2 / Alibaba), three lab origins, three corpus families.** That's the full closure surface as of spec sheet v1.5.

A new substrate "passes" CAS Harness when it closes Tiers 1-3 minimum. Tiers 4-6 are confirmatory and high-credibility for regulator audit.

---

## The three closed taxonomies (use the right one)

| Taxonomy | Cross-product | Classes | Pythia-160M readout | Pythia-160M lacunarity |
|---|---|---|---|---|
| 10 Noetics | `^0`..`^9` | 10 | 73.9% (+27.5 pp) | 0.793 (lumpy — v1 corpus artifact) |
| **28 Foundations** | **Drive × Register (`F1..F7` × `T/A/f/E`)** | **28** | **78.6% (+28.9 pp)** | **0.021 (38× cleaner)** |
| **40 Elements (TKS A1..D10)** | **Noetic × Domain (`^0..^9` × `P/C/E/O`)** | **40** | **89.8% (+39.7 pp)** | (not separately reported) |

**Rule:** Foundation and 40-Element are the closed axes. Noetics alone is lumpy and steering on it is Oscillatory by the fractal classifier (it fails). Don't waste runs on Noetics-alone steering.

**40E baseline rule:** "TKS source-derived" does not automatically mean "claim-bearing." Every 40E scenario library must pass its own text-baseline diagnostic before a hidden-state result can be described as beating surface text. The original Stage 9 40E fixture passes this rule; compact-gloss TKS40 v0 does not.

---

## The 12-step closure chain (in execution order)

Each step's Pythia-160M comparator is in brackets. A new substrate "closes" the chain when every step's threshold is hit.

### Step 1 — Build a balanced TKS source-derived scenario set
- Use the original TKS Stage 9 glosses as scenario seeds (canonical operator surface forms / colloquialisms; see `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6 for the canonical map).
- The scenario meaning must come from the original TKS definitions. Do not attach CAS/TKS labels as metadata to ordinary neutral prompts and call that a fixture; if the prompt content is statistically independent of the label, the row is unrecoverable by definition.
- Target: 10+ samples per class, balanced across all cells.
- For 28-Foundation: 7 Drives × 4 Registers = 28 cells × 10 samples = 280+ scenarios.
- For 40-Element: 10 Noetics × 4 Domains = 40 cells × 10 samples = 400+ scenarios.
- **For claim-bearing 40E:** use the original Stage 9 role-bound/counterfactual fixture, or a new fixture that passes the modern text-baseline guard. Compact-gloss TKS40 v0 is diagnostic-only because its surface text baseline reached 100.00%.
- **Don't use:** generic CAS prompts re-labeled retroactively, paraphrase-augmented imbalanced sets, source-vocabulary answer keys, metadata-only CAS labels, or scenarios that aren't source-anchored. These produced the 7.78% smoke-test miss on 2026-05-26, the 100.00% text-only compact-gloss block on 2026-05-27, and the 5% MTC v2 recoverability collapse on 2026-05-30.
- **Strip rule for non-leaky rebuilds:** strip answer-key wording, not TKS meaning. If an Element cannot be expressed concretely without its source vocabulary, mark that Element vocabulary-dependent instead of forcing a fake "clean" prompt.

### Step 2 — Capture activations through all transformer layers
- Last-token hidden state per scenario, per layer.
- `features` shape: `[N_scenarios, N_layers, hidden_dim]`, fp16 acceptable on H100.
- Required labels in dataset: `labels_drive`, `labels_register`, `labels_domain`, `labels_operator` (whatever cross-products you'll need downstream). Operator = Noetic.
- **Don't capture:** intermediate token positions instead of last-token (different signal locus, breaks Stage 27 comparators).

### Step 3 — Lacunarity gate (preflight)
- Compute lacunarity = `Var/Mean²` on the candidate-axis subspace across layers.
- **Pass:** Foundation lacunarity ≤ 0.05.
- **Pythia comparators:** Pythia-160M Foundation 0.021; Pythia-1B 0.015; Qwen2.5-1.5B 0.0084.
- **Fail signature:** Noetic-alone lacunarity 0.793 — lumpy, indicates the axis isn't cleanly factorized in this corpus. Don't proceed to steering on a lumpy axis.

### Step 4 — Fractal classifier (preflight)
- Classify the candidate-axis subspace as Stabilizing / Amplifying / Oscillatory / Neutral.
- **Pass:** Stabilizing or Amplifying.
- **Pythia comparator:** Foundation was Stabilizing on Pythia-160M. Noetic was classified Oscillatory and Noetic generation steering subsequently failed — the preflight predicted the failure.
- **Don't skip this:** Stage 6.6B confirmed the preflight's predictive value. Running steering on an Oscillatory axis wastes compute.

### Step 5 — Readout (Stage 7-equivalent)
- Train per-class linear probe on the hidden states using the chosen taxonomy (28-Foundation or 40-Element).
- Use the original closure probe family: sklearn `LogisticRegression` with `class_weight="balanced"` after `StandardScaler`. Do **not** use nearest-centroid readout for closure claims; centroid is only a quick diagnostic.
- Evaluate on heldout split (group-aware by base prompt to avoid paraphrase leakage).
- **Pass:** ≥70% test accuracy on 28-Foundation, ≥80% on 40-Element.
- **Pythia-160M comparators:** 28-Foundation 78.6% / 40-Element 89.8%.
- **Cross-arch comparators (28-Foundation):** Pythia-1B 82.4%, Pythia-2.8B 85.9%, OLMo-1B 90.6%, Qwen2.5-1.5B 82.0%.
- **Required controls:** majority baseline, shuffled-label baseline, and the exact scenario library's text-only baseline. Canonical TKS English aliases are legitimate framework language, not automatically contamination, but a text-only classifier at or above the pre-registered ceiling blocks the "CAS beats surface text" claim.
- **Current 40E comparator:** original Stage 9 40E on GPT-NeoX-20B scored 95.625% hidden readout versus 49.241071% confirmed CountVectorizer text baseline, 50.000% evaluator text-hash baseline, 2.500% majority, and 2.619% shuffled-label mean. This passes the text-only baseline gate, but its external detection-lift claim remains held pending Stage LSA Arm A.

### Step 6 — Subspace ablation (causal gate at activation level)
- Zero out the Foundation subspace in the saved hidden states, re-train and re-evaluate the probe.
- **Pass:** Probe accuracy collapses to ≈1/N chance (3.57% on 28-Foundation, 2.50% on 40-Element).
- **Pythia comparator:** Foundation probe 78.6% → 3.57% (exact 1/28 chance).
- **Random same-rank control:** must NOT collapse (Pythia: mean disruption 0.000, max 0.000).
- **Don't conflate:** subspace ablation ≠ per-class cover ablation (Steps 8-9). Subspace ablation is broader (entire learned subspace); cover ablation is narrower (specific neurons).

### Step 7 — Per-class component covers (Stage 27C)
- 28 learn rows + 28 eval rows (1 per Foundation class; disjoint).
- Identify attention-head covers per class.
- **Pass:** class-cover mean margin > global-prefix mean margin, paired across 28 classes.
- **Pythia-160M comparator:** 27/28 wins, p = 1.08×10⁻⁷, mean delta +4.17, positive margin share 1.0000.

### Step 8 — Within-head slice + single-dim coordinate covers (Stages 27D + 27E)
- Refine each class cover to within-head slices, then to single-dim coordinates (width 16).
- **Pass (27D):** slice-cover > random-slice paired (Pythia: 20/28 wins, p = 0.018).
- **Pass (27E):** coordinate-cover > random-coordinate paired (Pythia: 28/28 wins, p = 3.7×10⁻⁹).
- Each step narrows the cover further; later steps build on earlier ones.

### Step 9 — Targeted MLP-neuron covers (Stage 27F)
- Identify ~256 MLP neurons per class whose ablation maximally degrades probe margin for that class.
- Disjoint train/eval split to prevent circularity.
- **Pass:** targeted-neuron ablation drop > random-neuron ablation drop, paired.
- **Pythia-160M comparator:** 28/28 wins, p = 3.7×10⁻⁹, mean targeted drop 3.46 vs mean random drop 0.028.
- **Bit-exact patch-back:** restoring original activations must return probe margin to exact pre-intervention value (Pythia: mean abs error = 0.0).

### Step 10 — Bidirectional steering (Stage 27G)
- For each class cover identified in Step 9:
  - **Amplify** cover neurons by scale 2.0; measure margin lift.
  - **Polarity flip** cover by scale −1.0; measure margin reduction.
- **Pass:** amplification delta AND flip reduction both significantly larger than random-control deltas, paired.
- **Pythia-160M comparator:**
  - Target amplification mean delta: **+12.74** (random: −0.22)
  - Target flip mean reduction: **+25.31** (random: −0.27)
  - Bidirectional, both directions clean of random — this is the headline 112/112 result.

### Step 11 — η → ε bridge (the actual generation closure on Pythia + cross-arch)

**This is the central mechanism, not a side experiment.** It uses ε-realization (prefix conditioning), NOT ablation. The four ablation-based generation attempts (6.6, 7.3, 7.OA, 7.LA) all failed precisely because they tried to invert ε, which is structurally impossible per the section-retraction asymmetry.

**Protocol:**
1. First forward pass on the prompt → capture hidden states.
2. η reads the Foundation class from the hidden states (uses the readout from Step 5).
3. ε constructs a readable English prefix encoding the detected class. This is a natural-language passage, not a CAS symbol string. (Stage 7.CPL2 confirmed: raw-symbol prefix = null effect at every scale, including Qwen2.5-1.5B raw_symbol_probe = −0.0002. The effect requires *readable* prefix.)
4. Prefix is **prepended** to the original prompt.
5. Second forward pass: foreign model sees `[prefix] + [original prompt]`.
6. Measure the foreign model's next-token log-likelihood shift toward CAS-expected continuations vs CAS-partner continuations (the involution partner of the detected class).

**Pass:** mean lift positive, per-class delta clean, paired wins ≥70%, p < 0.001.

**Why this works architecturally:** prefix tokens are attended to by every subsequent position by construction of self-attention. ε is the covering morphism of the Noetic Coverage (Prop 5.6); its surjectivity onto downstream positions is the all-to-all attention pattern. The bridge mechanism is therefore a *prediction* of the topos theory, not a methodology discovered by hand-tuning.
- **Cross-arch comparators:**

| Model | Best layer | Mean lift | Per-class | Wins | p |
|---|---|---|---|---|---|
| Pythia-160M | 6 | +0.283 | +0.683 | 81/112 | < 0.0001 |
| Pythia-1B | 8 | +0.554 | +1.246 | 90/112 | 2.58×10⁻¹⁴ |
| Pythia-2.8B | 14 | +0.583 | +1.336 | 92/112 | 3.08×10⁻¹⁵ |
| OLMo-1B | 16 | +0.604 | +1.305 | 87/112 | ≈ 10⁻¹⁵ |
| Qwen2.5-1.5B | 11 | +0.7960 | +1.6253 | 83/112 | 2.92×10⁻¹² |

### Step 12 — Drive-local eraser-channel steering (Stage 27O — the generation-steering closure)
- In forward pass, suppress drive-local subspace via eraser-channel; measure output direction shift.
- **THIS IS NOT Stage 27H.** Stage 27H (prefix-plus-neuron steering) was NULL on Pythia-160M and has been re-tested as null. Stage 27I (prediction-position neuron steering) was also NULL. The closure was 27O drive-local eraser, not 27H/27I.
- **Pass:** win share ≫ 50%, p < 10⁻¹⁰, mean lift positive on calibrated rubric.
- **Pythia-160M / Pythia-1B / Qwen2.5-1.5B comparators (Stage 27O / 27P):**
  - Pythia-160M: +0.85 mean lift, 181/245 wins, p = 2.0×10⁻¹⁴
  - Pythia-1B: +0.84 mean lift, 54/56 wins, p = 2.2×10⁻¹⁴
  - Qwen2.5-1.5B: +0.90 mean lift, 56/56 unanimous, p = 1.4×10⁻¹⁷

---

## Known nulls — do not re-run as primary experiments

| Stage | Method | Status | Why it fails |
|---|---|---|---|
| **Stage 6.6** | Hidden-state ablation generation steering | FAILED | Tries to invert ε — structurally impossible per section-retraction asymmetry |
| **Stage 7.3** | Output-attention ablation steering | FAILED | Same — ablation-based generation steering |
| **Stage 7.OA** | Output-attention ablation variant | FAILED | Same |
| **Stage 7.LA** | Late-layer additive steering (add cover vector to late-layer hidden states) | NULL | Same |
| Noetic generation steering | Steer on the Noetic axis alone | NULL | Fractal classifier classified Noetic axis as Oscillatory; predicted the failure |
| Drive-subspace generation steering (non-eraser) | Steer drive subspace without eraser channel | NULL, p = 1.0 | Tries to ablate, not realize |
| **Stage 27H** | Prefix-plus-neuron steering | **NULL_NOT_ESTABLISHED** | Doesn't go through ε-realization |
| **Stage 27I** | Prediction-position-only neuron steering | NULL | Same |
| **Raw-CAS-symbol prefix conditioning** | Prepend `[F3\|E]` literal symbol instead of readable English | NULL on every model tested | Foreign model doesn't speak CAS notation; ε must produce readable English |

**Pattern:** every NULL result is either ablation-of-ε (structurally impossible) or skips ε-realization entirely. The bridge works because ε *realizes* into English; it does not work in any inversion or symbolic-only form.

These are listed so future runs don't lose time re-running diagnosed-null methods. Rerun them only if a substrate-specific hypothesis predicts they should re-emerge.

---

## Stage 13 — Multi-Layer Trace + Blind-Spot Detection (cleanest signal in the project)

Single-layer probes lose signal that's distributed across depth. Stage 13 fixes this by reading across the entire layer stack and classifying the trace per prompt.

**Method:**
1. For each scenario, capture the probe's prediction at every layer (not just one).
2. The "trace" is the per-layer sequence of probe outputs (margin per class per layer).
3. Classify each trace as **stable-like** (consistent across layers) or **problem-like** (oscillating, collapsing, or contradictory across layers).
4. Stable-like traces are high-confidence; problem-like traces are flagged as either:
   - **Model-side weakness** (the model's representation of class X is fragile across layers) — architectural
   - **Readout-position weakness** (the model has the structure, but our probe is reading at the wrong position) — configurable

**Pythia comparator:** Stage 13 multi-layer trace lacunarity = **0.0016** — the cleanest factorization signature in the project history. Multi-layer averaging suppresses single-layer noise, producing a structurally cleaner signal than any single-layer probe.

**Why this matters:**
- A regulator audit doesn't just want "this model is fine" — it wants "here is exactly where this model's representation of class X is fragile, and here is whether the fragility is architectural or readout-configurable."
- This is regulator-grade evidence shape that classical XAI tools cannot produce.
- For large models (≥1B parameters), single-layer probes underperform; multi-layer trace is the right protocol.

**Status on 20B work:** not yet run. Should be the standard protocol for >1B-parameter substrates going forward.

---

## Stage 14.1 — Weight-Geometry Alignment (independent static-weight tier)

This is the **sixth evidence tier** and is independent of activations. It looks at the *static weights* of the foreign model, not at any forward pass.

**Method:**
1. Take the CAS Foundation subspace (the directions the probe identified).
2. Take the foreign model's output unembedding matrix (the weights that project final hidden states to vocab logits).
3. Compute principal angles between the two subspaces.
4. Compare to a random-subspace null distribution (QR-orthonormalized same-rank random subspaces, fixed seed).

**Pythia-2.8B comparator:** **2.83× random expectation, p = 0.0099** on output-side. Input-side basically random (no alignment with embedding matrix).

**Why this matters:**
- This is the *static* counterpart to the dynamic activation-tier evidence. Activations fire per-prompt; weights are baked in.
- "Weights do not fire." The geometric alignment finding doesn't claim the weights are emitting CAS structure — it claims the static weight matrices live in a configuration *consistent with* CAS-directional emission.
- This is what Prop 5.6 predicts: ε realizes structure toward outputs, so we expect output-weight alignment of CAS directions. We see it.

**Implication for AI2 / regulator audience:** the bridge mechanism is not just a per-prompt phenomenon — its geometry is baked into the model's weights. That's independent corroboration that you don't have to retrain or fine-tune anything to read CAS structure; it's already there.

**Status on 20B work:** not yet run. Stage 14.1 protocol ports directly — just needs the model's unembedding matrix and the Foundation subspace.

---

## Stage 5.10 — Hidden-Content / Suppression Detection (two-bridge symmetry, prototype tier)

The newest capability, derived from the η → ε architecture's natural symmetry. It addresses: **what is the model representing that it is not saying?**

**Architecture:**
- η₁: probe on internal hidden states (what the model is computing)
- η₂: probe on emitted output text (what the model is saying)
- Compare η₁'s CAS class profile against η₂'s class profile

**Seven detectable hiding shapes** (each maps to specific CAS tooling):
- **Withheld:** η₁ has class X high, η₂ has class X low
- **Inverted:** η₁ has class X, η₂ has class Y, where (X, Y) is a CAS involution pair (e.g., ^2 ↔ ^3, ^5 ↔ ^6, ^8 ↔ ^9, F1 ↔ F7, F2 ↔ F6, F3 ↔ F5)
- **Suppressed:** η₁'s per-token trajectory shows class X firing then collapsing to neutral
- **Frame-manipulated:** Domain trajectory shows axis-W inversion (e.g., P → O override)
- (3 more shapes documented in spec sheet §5.10)

**Status:** η₁ is validated across all Stage 6-16 work. η₂ on emitted output text is prototype-status (works on the same probe architecture; needs the same validation discipline applied to the emitted-text corpus). Two-bridge comparison is wired but not yet pre-registration-gated.

**Bounded claim:** This capability tells you what CAS class the model is hiding with the same statistical reliability as any other CAS Harness reading. It does NOT tell you the literal words the model would have said if not for the suppression — that requires intervention experiments (removing the suppression mechanism) which are a separate, higher-cost methodology.

**Comparison to Anthropic's NLA "evaluation awareness" finding:** NLA detected that Claude "believed but did not say" it was being evaluated, producing a natural-language description. CAS Harness's hidden-content detection produces a **typed** version of the same finding: which CAS class was internally computed, which CAS class was emitted, what the gap is in framework terms. CAS Harness's version is auditable (typed + provenance-stamped + reproducible); NLA's is more readable but admitted-by-authors to sometimes be verifiably false.

---

## Methodology discipline (the bi-agent self-consistency that produced the closures)

The framework's reliability across 28+ experimental stages comes from these disciplines, enforced on every stage:

1. **Pre-registration**: PASS / NULL / GREY gates committed BEFORE confirmatory experiments. The spec sheet notes 8 consecutive stages of clean pre-reg.
2. **Paired statistics**: Wilcoxon signed-rank or paired permutation. NEVER unpaired t-test on related samples.
3. **Random-control matching**: QR-orthonormalized same-rank random subspaces with fixed seeds. Random controls must use the same dimensionality and structural form as the targeted intervention.
4. **Fresh holdouts**: Confirmatory runs always on prompts not used in exploratory iteration.
5. **SHA + revision provenance**: Activation files, probe weights, model commits, package versions — all hashed and recorded in the Evidence Packet.
6. **Bi-agent audit cycle**: Each meaningful commit reviewed by an independent agent. Multiple drift catches in this project came from the bi-agent cycle (Foundation vs Drive, 27H vs 27O, colloquialism reframe, source-axis vs derived-axis).
7. **Reserved-language claim tiers**: every reported result tagged with one of `prototype / wired-works / sample-passed / gate-passed / validated`. The tier governs what claim is licensed.

---

## Best-layer comparator table (for layer-selection sanity)

The Foundation probe's best layer per architecture, from spec sheet line 633-635:

| Taxonomy | Pythia-160M | Pythia-1B | Pythia-2.8B | OLMo-1B | Qwen2.5-1.5B |
|---|---|---|---|---|---|
| 28 Foundations | Layer 6 | Layer 8 | Layer 14 | Layer 16 | Layer 11 |
| 40 Elements | Layer 5 | (not tested) | (not tested) | (not tested) | (not tested) |
| 10 Noetics | Layer 3 | (not tested) | (not tested) | (not tested) | (not tested) |

Use as a **prior** for which layers to probe first on a new substrate — best layer scales roughly linearly with depth for the Foundation bridge runs. Do not hard-code it as a law: the GPT-NeoX-20B original Stage 9 40E readout peaked at layer 2 under the fixed Stage 9 split, while the exact Stage 7 Foundation-28 bridge peaked at layer 40.

---

## Sample-size / class-balance discipline

The closures above were measured on **balanced** scenario sets with ≥10 samples per class. Imbalanced or augmented-from-tiny-base datasets do NOT reproduce them. If a probe accuracy looks anomalously low, check this first:

- Populated cells / total cells (e.g., 39/40 = bad; 40/40 = good)
- Minimum samples per cell (any cell < 5 samples = unreliable per-class fit)
- Augmentation factor (augmenting 25 base prompts to 400 via paraphrase ≠ 400 independent scenarios — probe overfits the augmentation pattern)

---

## Anti-drift checklist (re-read before any new substrate run)

Before pressing run on a new model, verify:

1. ☐ Scenarios are source-derived from TKS Stage 9 glosses, not generic CAS prompts
2. ☐ Dataset has labels for the cross-product axis being tested (e.g., for 28-Foundation: `labels_drive` AND `labels_register`)
3. ☐ Class balance: ≥10 samples per class, every cell populated
4. ☐ Lacunarity gate run BEFORE steering (Step 3) — skip steering if lumpy
5. ☐ Fractal classifier run BEFORE steering (Step 4) — skip steering if Oscillatory
6. ☐ Readout (Step 5) uses balanced sklearn LogisticRegression + StandardScaler, not nearest-centroid, for closure claims
7. ☐ Readout (Step 5) compared to **majority, shuffled-label, and exact-fixture text-only baselines**
8. ☐ Subspace ablation (Step 6) compared to **random same-rank ablation**
9. ☐ Neuron-cover ablation (Step 9) compared to **random neuron-cover** AND **wrong-class cover** AND **patch-back recovery**
10. ☐ Steering (Step 10) tests amplification AND polarity flip, both against random
11. ☐ Generation steering uses **drive-local eraser-channel** (27O), NOT prefix-plus-neuron (27H) or prediction-position (27I)
12. ☐ TKS40 compact-gloss v0 is not used for CAS-beats-text claims; only original Stage 9 40E or a new fixture with text-only ≤60% can support that claim

---

## What "passed" means at each tier

Use these to communicate scope honestly (e.g., for an AI2 conversation):

| Tier | What's proved | What's not |
|---|---|---|
| Steps 1-2 only | Real activation capture | Nothing about structure |
| + Step 3-4 | Axis is factorized + non-Oscillatory | No causal claim |
| + Step 5 | Hidden states linearly encode the axis | Doesn't separate "model represents" from "text encodes" |
| + Step 6 | Foundation subspace causally necessary for probe | Activation-level only |
| + Steps 7-9 | Localized to specific neuron set, beats matched random | Activation-level only |
| + Step 10 | Bidirectional steering at activation level | Not yet behavioral |
| + Step 11 | Likelihood-bridge behavioral readout | Not generation steering |
| + Step 12 | Generation behavior shifts under drive-local eraser | **Full closure** |

Pythia-160M closed all 12. The 20B work currently has:

- Steps 1-2: real GPT-NeoX-20B activation capture across all 44 layers.
- Step 5, compact-gloss TKS40 v0: hidden-state readout was high but the text-only baseline reached 100.00%, so this library is diagnostic-only and blocked from CAS-beats-text claims.
- Step 5, original Stage 9 40E (`S9-40E-ORIGINAL-BASELINE-READOUT`): 8,320 rows, 40/40 cells, 208 examples/class, original fixed split 3,840/4,480, zero train/test group overlap. GPT-NeoX-20B hidden readout reaches 95.625% at layer 2 versus 49.241071% confirmed CountVectorizer text baseline, 50.000% evaluator text-hash baseline, 2.500% majority, and 2.619% shuffled-label mean. This is the 20B 40E readout comparator that passed the text-only baseline gate; external claim-bearing use is held pending Stage LSA Arm A.
- Step 5, exact Stage 7 Foundation-28: 51.04% on 28 classes versus 3.57% majority/chance and 42.28% text baseline.
- Parts of Steps 6 and 9: activation-level cover ablation with random + wrong-cover controls. TKS40 drops 40.00% -> 26.25% while random/wrong controls are approximately zero. Exact Stage 7 Foundation-28 drops 51.04% -> 38.59% while random/wrong controls are approximately zero.
- Step 11 partial: exact Stage 7 eta-to-epsilon likelihood bridge on GPT-NeoX-20B. Gold/readable epsilon prefixes pass strongly (+0.6601 mean likelihood-margin delta, 93/112 positive rows). Probe/readable prefixes are positive (+0.1974, 72/112, p = 0.001608) but miss the original strict full-loop gate by about 0.0026. Raw CAS-symbol prefixes stay near zero (+0.0035), matching the original null control.
- Correctness diagnosis: when the 20B probe predicts the Foundation correctly, probe/readable delta is +0.6517. When only the Drive is correct, delta is +0.7185. When the Foundation is wrong, probe/readable delta is -0.0752. So the bridge is not the bottleneck; the readout handoff/confidence filter is.
- Confidence-filter follow-up: centroid-margin filtering is now implemented and was rerun at q25/q50/q75. q75 kept 28/112 rows, raised selected Foundation accuracy to 57.14%, and raised probe/readable delta to +0.2775. It still missed the strict original full-loop gate because sign-test p was 0.017849 rather than <= 0.01. Simple margin filtering helps but is not enough by itself.
- Methodology correction: replacing nearest-centroid with the original balanced logistic linear-probe readout closes the 20B Step 11 bridge. GPT-NeoX-20B exact Stage 7 Foundation readout reaches 86.8622% heldout accuracy at layer 40; selected bridge-row Foundation accuracy is 85.7143% and Drive accuracy is 93.75%. The probe-predicted readable epsilon loop passes: +0.596413 mean likelihood-margin delta, 90/112 positive rows, sign-test p = 3e-11. Gold-readable remains strong: +0.660065, 93/112 positive rows. Raw-symbol controls remain near zero (+0.002524 probe raw, +0.002186 gold raw).
- Steps 3-4, exact Stage 7 Foundation-28: trace diagnostics now pass on GPT-NeoX-20B under the same balanced-logistic readout. Gate layer 40 has 86.8622% heldout Foundation accuracy, Foundation lacunarity 0.006715 (Uniform; threshold <= 0.05), drive lacunarity 0.002752, register lacunarity 0.001283, and numeric layer-trace class Amplifying. This is cleaner than the Pythia-160M Foundation lacunarity comparator (0.021). Caveat: the fractal class is currently a numeric layer-trace proxy, not the discrete cas-engine CognitiveFractal orbit object.

The 20B work still has Step 12 / Evidence Packet verifier merge ahead. Steps 3-4 and Step 11 are now closed at the trace-diagnostic and likelihood-bridge tiers for GPT-NeoX-20B under the original balanced-logistic readout methodology.

---

## Matched-taxonomy control gate (added 2026-05-30)

The current 20B 40E result shows that the model encodes the CAS-labeled distinctions strongly: 95.625% hidden readout versus 49.241071% text baseline. That closes the narrow "simple text-only classifier wins" objection for the original Stage 9 40E fixture. It does **not** close the sharper "source vocabulary carried the meaning" objection; Stage LSA Arm A is the gate for that.

It does **not** by itself close the stronger uniqueness objection:

> Are CAS labels uniquely recovering a noetic/cognitive structure, or are they a good relabeling of ordinary semantic categories?

The required next control is now pre-registered in:

`docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md`

This control compares CAS against same-cardinality, coherent non-CAS semantic taxonomies using the same activations, same splits, same balanced logistic probe, same text baselines, same shuffled-label controls, and the same flat-plus-nested lacunarity scoring.

**Execution discipline:**

1. Run the matched-taxonomy control on GPT-NeoX-20B first.
2. If 20B passes, replay it across the validated model points.
3. Do not use "CAS is unique" or "CAS is universal" language externally until CAS beats matched semantic taxonomies, not just text and random labels.

**Allowed wording before this gate passes:**

> The evidence shows that models strongly encode CAS-labeled distinctions beyond surface text. The matched-taxonomy control is the next pre-registered test for whether CAS is uniquely cleaner than same-size semantic alternatives.

**Allowed wording after this gate passes across models:**

> CAS beats same-size coherent semantic taxonomies on hidden-state readout and flat-plus-nested factorization across model families and scales.

Add this to the anti-drift checklist:

13. A claim of CAS uniqueness requires matched-taxonomy controls: scrambled CAS, coherent non-CAS 40-way, coherent non-CAS 7 x 4 nested, plus text-only baseline.

**2026-05-30 pilot correction:** A low text baseline is necessary but not sufficient. The first marker-balanced MTC pilot passed the text-leakage ceiling, but CAS itself was not recoverable from GPT-NeoX-20B hidden states on that fixture: 40E best layer reached only 5.5%, and F28 landed at chance. Treat that as a fixture/configuration null, not a global CAS null. Matched-taxonomy specificity is not interpretable until the fixture first clears a CAS recoverability floor.

**2026-05-30 v2 patch-two correction:** The concrete-scenario v2 fixture fixed text leakage for both CAS and matched labels, but still failed CAS recoverability after full GPT-NeoX-20B capture. 40E best layer was 5.50% hidden accuracy versus 4.50% text baseline (+1.00 pp). F28 best layer was 5.036% hidden accuracy versus 2.878% text baseline (+2.158 pp). Both miss the +20 pp recoverability gate. Post-run inspection found the core defect: v2 labels were attached as metadata while visible prompt topic/task was independently rotated. That explains the v2 null and licenses fixture rebuild. It does **not** re-license the original 95.625% v1 result, because a broken de-leak and a leaky original can both be true.

**Stage LSA added 2026-05-30:** Before building another MTC fixture or spending new GPU time, run Leakage-vs-Signal Adjudication. The direct question is whether v2 over-corrected or whether v1 detection lift was substantially surface-carried. LSA uses CAS-competent, model-blind judges and an independent model rater on two arms: Arm A = original v1 items with the strip operation applied, Arm B = v2 notation-stripped items. Arm A is load-bearing because it directly tests whether v1 meaning survives after removing surface tells. Arm B is supporting evidence about the broken v2 generator.

**Per-Element meaning-survival rule:** LSA reports each 40E Element and each F28 cell separately. A cell where judges recover the label after stripping is `meaning_bearing`. A cell where judges cannot recover the label is `vocabulary_dependent` and cannot carry detection-lift claims until rebuilt or merged. Overall axis success does not automatically license every class.

Add this to the anti-drift checklist:

14. For MTC fixtures, gate order is fixed: text-only baseline <= 60%, then CAS hidden readout lift >= +20 pp, then matched-taxonomy specificity. If CAS itself is not recoverable, stop and redesign the fixture.
15. Passing the text baseline by removing all class information is not success. The fixture must still encode the target distinction in scenario meaning strongly enough for hidden-state readout to clear the recoverability floor.
16. Do not assume a v2 recoverability null means either "CAS failed" or "v1 was leakage." Resolve the fork with Stage LSA before claim-bearing fixture rebuilds.
17. Do not carry forward the 95.625% v1 40E number as externally claim-bearing until Arm A of LSA shows that the original v1 items remain recoverable after answer-key wording is stripped.
18. Apply the per-Element/per-Foundation LSA status to future claims: `meaning_bearing` cells can be rebuilt and tested; `vocabulary_dependent` cells are disclosed and cannot support detection-lift claims by themselves.

Current MTC v2 working docs:

- `docs/working/cas_harness_mtc_20b_pilot_results_20260530.md`
- `docs/working/cas_harness_mtc_v2_fixture_spec_20260530.md`
- `docs/working/cas_harness_leakage_signal_adjudication_prereg_20260530.md`
- `docs/working/lsa_artifacts_20260530/MANIFEST.md`

---

## File pointers for the actual code

These are the canonical implementations of each stage from the Pythia work:

- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27c_per_class_component_covers.py`
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27d_within_head_slice_covers.py`
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27e_single_dim_coordinate_covers.py`
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27f_targeted_mlp_neuron_covers.py`
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27g_mlp_neuron_cover_steering.py`
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage27p_qwen_drive_local_eraser_steering.py` (Step 12 / 27O equivalent for Qwen)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage27{f,g,p}_*_spec.py` (test contracts)

When the 20B work needs Step 7-10, port from these implementations directly — don't re-derive the protocol.
