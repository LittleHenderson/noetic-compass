# Path C Draft: Non-Transformer Simplex Encoder/Decoder

Date: 2026-05-06
Status: Future build draft. Do not implement before Path B conversational v0 ships.
Search tags: CAS-Native, Path C, non-transformer decoder, non-transformer encoder, Delta^o_39, Fisher-Rao, RPM, meta-logic, native NL generation, simplex language model.

## 1. Purpose

This note preserves a future research/build direction:

> Can CAS-Native eventually replace a transformer reasoning backbone with a Simplex Delta^o_39 + Fisher-Rao state engine, while still generating fluent conversational English?

**The "Agent Team" Verdict (Session 56, defensible form):**

Yes as a research direction, with one important boundary: the simplex can replace the opaque reasoning substrate, but not the whole language-generation mechanism by itself. The preferred future architecture is the **Simplex Core + SSM Decoder** hybrid.

- **The Mind (Simplex Core):** Uses Mirror Descent on Delta^o_39 to map intent. The Fisher-Rao metric provides boundary-aware geometry: as probability mass approaches the simplex boundary, the geometric distance grows sharply. In implementation this must be paired with a positive `simplex_floor`, finite-gradient safeguards, and explicit RPM/meta-logic gates. This can make collapse measurable and penalizable; it does not magically make unsafe states impossible.
- **The Voice (SSM Decoder):** Uses a State-Space Model (for example an RWKV-style recurrent mixer or a Mamba-style selective SSM) conditioned on the Simplex state. This may offer linear-time generation and strong CAS conditioning, but fluency must be proven against the transformer baseline by blind review and generation metrics.

This architecture moves from "learning a fully opaque hidden space" toward "learning to map English onto a known cognitive geometry, then speaking from that geometry."

```text
NL prompt
  -> Simplex Mirror Descent Encoder (The Mind)
  -> RPM/Meta-logic Valve (The Gate)
  -> SSM Autoregressive Decoder (The Voice)
  -> Fluent reply + Trace
```

## 2. Non-Goals

This is not the v0 path. Path B remains:

```text
K=9 classifier + CASNativeModel + NLGenerationHead + Tier 3 dialogue corpus
```

This draft should not block:

- the 50K Claude Tier 3 corpus
- B-3 native generation smoke
- B-4 two-stage inference wiring
- any current K=9 production classifier usage

This draft also does not claim that a 39-dimensional simplex alone can speak English. It cannot. The simplex is the state geometry. The decoder is the speech mechanism.

## 3. Core Idea

Replace the opaque hidden-state reasoning middle with a structured CAS state:

```text
p_t in Delta^o_39
```

where `p_t` is an open-simplex distribution over the 40 Cognitive States. Every component is positive and the total sums to 1.

The Fisher-Rao metric supplies the natural distance/learning geometry for this space. RPM supplies prerequisite gating over the state trajectory. Meta-logic supplies inspectable proof/explanation objects above the gate.

The model should maintain:

- `p_state`: 40-state simplex distribution
- `domain`: P/C/E/O distribution or constrained projection
- `drive`: F1-F7 distribution
- `register`: T/A/f/E distribution or register-set distribution
- `rpm_status`: prerequisite pass/fail and broken-node evidence
- `meta_proof`: optional relation/proof object for set/relation expressions
- `dialogue_state`: compact turn memory

## 3.1. Refined CAS state space — typed product of simplexes (Session 57 refinement)

The `p_t in Delta^o_39` framing in Section 3 is the right *primary* state but not the *full* state space. CAS has four orthogonal axes (Noetic, Domain, Drive, Register) plus operations and meta-relations. The architecturally clean decomposition is **a typed product of simplexes for the categorical axes, plus structured layers for relations and constraints**.

### 3.1.1 Reading A correction (Cognitive State, not Noetic)

`Delta^o_39` is the open simplex over **40 Cognitive States** — the joint Noetic × Domain primitive. Atoms are `^0^P, ^0^C, ^0^E, ^0^O, ^1^P, ..., ^9^O`. This is the patent-named primitive (USPTO #64/037,173) and must NOT be split into independent Noetic Δ°9 + Domain Δ°3 — the cross-product IS the unit. The framework treats `^3^P` (principled Negative) as functionally distinct from `^3^O` (operational Negative); splitting loses that.

Noetic and Domain are **derived diagnostics** (marginals), not primary axes:

```
P(Noetic = ^5) = Σ over domains: P(^5, domain)
P(Domain = C) = Σ over noetics: P(noetic, C)
```

### 3.1.2 The six-component CAS state stack

The geometric metaphor is **base manifold + typed fibers + typed constraints**. Cognitive State is the ground; Drive and Register modulate the ground; Operations / Meta-logic / RPM regulate which transitions on the ground are admissible.

| # | Component | Geometry | Atoms / structure | Role |
|---|---|---|---|---|
| 1 | Cognitive State | open simplex Δ°39 — **base manifold** | 40 atoms = (Noetic × Domain) | "What state is the mind in?" |
| 2 | Drive | 7-dim non-negative intensity vector — **fiber, NOT simplex** (see §3.1.3a) | 7 dims = F1..F7 | "What motive is active? At what intensity?" |
| 3 | Register | 4-dim Bernoulli activation — **fiber, NOT simplex** (see §3.1.3b) | 4 gates = T / A / f / E | "How should this surface in language?" |
| 4 | Operation / transition | discrete head — **fiber** | `+`, `→`, `×`, `∘`, `Ω`, ... | "What operation is being performed?" |
| 5 | Meta-logic proof | typed relational module — **constraint** (NOT a simplex — see §3.2) | relation / operand / truth-status | "What relation holds between which states?" |
| 6 | RPM gate | typed gate over state transitions — **constraint** | prerequisite chain over (state, drive) | "Is this transition admissible?" |

The asymmetry is load-bearing: state is the ground; everything else modulates or constrains it. Capturing this asymmetry geometrically is what prevents the silhouette-without-content failure mode the v0 audit revealed.

### 3.1.3a Drive: non-negative intensity vector, not a simplex (drives co-present)

A simplex Δ°6 over F1..F7 forces exactly one drive active at full intensity (with mass distributed across the 7 atoms summing to 1). But drives genuinely co-present in real cognition — F1 Unity AND F5 Agency simultaneously is not a 60/40 split between mutually exclusive options; it's two motives both active at high intensity. A simplex distorts this by forcing the model to give up F1 mass to give F5 mass.

The right structure is a **7-dim non-negative intensity vector**:

```python
drive_intensity: torch.Tensor  # shape (7,), values in [0, +inf) (typically softplus or relu output)
# Single-dominant case: drive_intensity = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3]  → F7 dominant
# Co-present case:      drive_intensity = [2.5, 0.0, 0.0, 0.0, 2.1, 0.0, 0.1]  → F1 + F5 both active
```

A softmax projection (normalize to sum-1) is computable as a derived "which drive dominates" marginal but is NOT the primary representation. The intensity vector's load-bearing semantics is *how strong each drive is*, not *which drive among mutually exclusive options*.

### 3.1.3b Register: Bernoulli gates, not a simplex (CAS v7.7 multiplicity)

A simplex Δ°3 over T/A/f/E forces exactly one register active. CAS v7.7 supports three notations:

- `|R` — single register (Δ°3 sufficient)
- `|⟨R1,R2,R3⟩` — register-set (multiple simultaneously active; cannot be a simplex)
- `(R1 × R2 × R3) = Ω` — cross-register integration into a fused emergent state (separate generative operation)

The right structure is **4 independent Bernoulli gates** (one per register), not a 4-atom simplex:

```python
g_register: torch.Tensor  # shape (4,), values in [0, 1]
# Single-register case: g_register = [0, 0, 1, 0] → only |f active
# Multi-register case:  g_register = [1, 1, 0, 0] → |⟨T, A⟩ active
```

A simplex projection of `g_register` (normalize to sum-1) is computable as a derived single-register marginal but is NOT the primary representation.

### 3.1.3c General principle: simplex iff mutual exclusivity holds

The decision rule is uniform across all CAS axes:

- **Use a simplex** when atoms are mutually exclusive at any instant (Cognitive State: the mind is in one cognitive state at a time, even if smoothly transitioning).
- **Use independent intensity / Bernoulli gates** when atoms can co-present (Drive: motives co-active; Register: CAS v7.7 multi-register notation).

Forcing a simplex on a non-mutually-exclusive axis is exactly the geometric mistake that v0's flat-vocab transformer made implicitly via softmax classification heads. Path C corrects it explicitly per axis.

### 3.1.4 Why this beats one-giant-joint-simplex AND four-independent-axis-simplexes

**One giant joint over Noetic × Domain × Drive × Register**: 10 × 4 × 7 × 4 = 1,120 atoms. Most combinations are sparse in real data; learning a 1,120-state Δ°1119 is hard; loses the framework's natural decomposition.

**Four independent simplexes (Noetic Δ°9 + Domain Δ°3 + Drive Δ°6 + Register Δ°3)**: 14 dims total, but breaks the 40-Cognitive-State patent primitive AND violates mutual-exclusivity for Drive and Register. Cannot represent "70% on `^3^P`, 20% on `^6^O`" — must approximate as separate Noetic and Domain marginals, losing correlation. Also forces F1+F5 co-presence to compete on the Drive simplex incorrectly.

**Three structures with mixed geometry (Cognitive State Δ°39 base manifold + Drive 7-dim intensity vector + Register 4-dim Bernoulli)**: 40 + 7 + 4 = 51 dims. Preserves the 40-state patent primitive (cognitive states are mutually exclusive — simplex correct). Drive and Register decouple from the base via independent intensity / Bernoulli structures (atoms co-present — simplex incorrect). Multi-register expressivity preserved via Bernoulli gates. Drive co-presence preserved via independent intensities. Geometric structure matches the framework's actual semantics axis-by-axis.

## 3.2. Meta-logic is a verb, not a noun (do NOT make it a simplex)

Simplexes answer **noun** questions: "Which state is active? Which drive? Which register?" They're distributions over finite sets.

Meta-logic answers **verb** questions: "Is this state IN that cluster? Does this transition PRESERVE the domain? Is this claim LICENSED by the prior CAS objects?" Relations have arguments and truth values; they're not distributions over a fixed set of state-atoms.

The mistake to avoid: treating "meta-logic" as another flat categorical axis like Drive or Register. There's no meaningful "meta-logic distribution" because the act of inference about relations isn't picking from a finite set — it's running typed-truth checks over arguments.

### 3.2.1 But small typed distributions can live INSIDE the meta-logic module

The module itself isn't a simplex, but it can use tactical mini-distributions for its sub-questions:

- **Relation type**: Δ over `{membership, subset, cover, pullback, product, partition, authority, evidence, ...}` — given a meta-relation is being asserted, which type is it?
- **Operand role**: distribution over candidate source/target state sets — which prior CAS objects are the relation's arguments?
- **Truth status**: Δ over `{asserted, inferred, contradicted, unknown}` — what's the epistemic standing of this relation?

These mini-distributions live INSIDE the meta-logic layer's reasoning, not as the layer's primary representation.

### 3.2.2 Meta-logic connects directly to the existing CAS notation compiler

The project already has `api/notation/compiler.py` validating CAS expressions for syntactic and semantic correctness at compile-time. The meta-logic module is the **runtime extension** of that compiler:

- **Compile-time** (existing): is `^3^P ∈ NoeticCluster{^3^P, ^6^P}` syntactically and semantically valid?
- **Runtime (meta-logic)**: given the model's current `p_state` distribution, do the relations the model is implicitly asserting actually hold over THIS state's mass distribution? Is the next predicted transition admissible?

So at runtime, meta-logic is a **typed-truth-tracking checker over states**, not state itself. RPM uses meta-logic's verdicts as evidence for its prerequisite-chain gate.

### 3.2.3 Pre-generation vs post-generation meta-logic

Two modes with different value:

- **Pre-generation**: meta-logic runs DURING decoding. Inadmissible state transitions get masked from the next-token logits. This is **constraint** — prevents invalid output. Cheap admissibility checks per token.
- **Post-generation**: meta-logic runs AFTER the reply is produced. Evaluates whether `(prompt, predicted state, generated reply)` triple is admissible. Constructs a full proof object. This is **explanation** — produces auditable proofs for Mode 7 / Mode 3 trace.

**Production target: both, in sequence.** Pre-gen for safety (RPM-with-proofs needs it). Post-gen for traceability (the audit surface needs it). Pre-gen is cheaper and lighter; post-gen is heavier but only fires once per reply.

## 3.3. Refined Path C phasing (axis-by-axis prototype)

The original Section 8 prototype phasing is correct but doesn't fully sequence the simplex decomposition. Refined axis-by-axis order:

| Phase | Build | Falsification gate |
|---|---|---|
| **C1** | Cognitive State Δ°39 encoder + Fisher-Rao loss + RPM stub. Keep transformer decoder. | Within 5-10pp of K=9 on CAS prediction; better trace quality than K=9; no Drive/Domain collapse worse than K=9. |
| **C2** | Add Drive 7-dim non-negative intensity vector (NOT Δ°6 simplex; drives co-present per §3.1.3a). Joint state = (p_state, drive_intensity). | Drive head accuracy improves vs K=9 baseline. Drive co-presence (e.g., F1+F5 simultaneously high) representable. No regression on Cognitive State. |
| **C3** | Add Register Bernoulli gates. Test single-register backward-compat AND multi-register `|⟨...⟩` expressivity. | Single-register accuracy holds; multi-register expressions decode without forcing onto a single register. |
| **C4** | Add meta-logic proof module. Surface verdicts as TRACE only (Mode 7), not as gate evidence yet. | Held-out `(state, transition, expected_admissibility)` test set ≥90% accuracy. If <90%, do NOT advance to C5. |
| **C5** | RPM uses meta-logic proofs as gate evidence (instead of scalar gate). | RPM admissibility decisions match expert annotations on a held-out adversarial set. Generation refusals/repairs become inspectable. |

C4-before-C5 is a **hard gate**. If meta-logic in C4 produces noisy or wrong proofs, RPM-with-proof-evidence in C5 is downstream of broken evidence — strictly worse than scalar RPM. Soft-rollout: meta-logic ships as observation first, gates second.

## 3.4. Compiler-fluency framing → see Path D

The compiler-fluency framing — what CAS-Native should eventually become, the six-task curriculum, the five operational requirements, the contrastive readout supervision pattern — moved to its own runbook on 2026-05-07 when the v1 plan locked into a paired Path C / Path D structure.

→ **`docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md`**

Path C focuses on the simplex-native architecture (Sections 3.1–3.3 and 4 onward). Path D specifies the curriculum, corpus, and compiler-in-the-loop training that the architecture consumes. They ship together as v1.

Headline preserved here for cross-reference:

> *Compiler = law. Model = fluent speaker. Together = traceable conversational reasoning.*
>
> The model knows everything the compiler can SAY. The compiler decides whether what the model said is TRUE.

## 4. Proposed Architecture

### 4.1 Simplex Encoder

Goal:

Turn English prompt tokens into a CAS state trajectory without transformer self-attention.

Proposed module:

```text
SimplexStateEncoder
```

Input:

- token ids from the existing native tokenizer
- optional CAS prefix tokens
- speaker/turn metadata
- prior dialogue state

Output:

- `p_state_final`: final 40-state open-simplex distribution
- `p_state_trace`: compressed per-step simplex trajectory
- `axis_logits`: noetic/domain/drive/register/register_set projections
- `rpm_trace`: prerequisite gate trace
- `meta_logic_trace`: optional set/relation proof trace

Candidate update rule:

```text
p_{t+1} = normalize_eps(p_t * exp(eta * g(x_t, p_t, m_t)))
```

Plain meaning:

Each token applies a small multiplicative update to the current CAS distribution. Normalization keeps the result inside the open simplex. This is closer to mirror descent/natural-gradient behavior than a free Euclidean hidden-state update.

Where:

- `x_t` = token embedding
- `p_t` = current CAS simplex state
- `m_t` = compact dialogue memory
- `g(...)` = learned update network
- `eta` = learned or scheduled update size
- `normalize_eps` = floor every coordinate at `simplex_floor`, then renormalize

Implementation candidates:

1. Gated recurrent cell over simplex coordinates.
2. State-space model cell conditioned on CAS axes.
3. Small causal convolution feeding a simplex update.
4. Mixture of learned CAS operators: plus, pair, production, omega, meta-relation.

No transformer attention is used in this encoder.

### 4.2 Dialogue Memory Without Attention

A non-transformer conversational model still needs memory. Proposed memory:

```text
DialogueStateMemory
```

Fields:

- last `k` CAS simplex states
- current topic embedding
- speaker profile / demographic / tone metadata
- unresolved question flag
- prior assistant stance
- RPM broken-node history

Memory update can be recurrent:

```text
m_{t+1} = GRU_or_SSM(m_t, [p_state_t, token_summary_t, turn_features])
```

This memory is not the CAS state itself. It is the short-term conversational workspace used to keep replies coherent across turns.

### 4.3 RPM Gate

Current scalar RPM behavior should become a structured gate:

```text
RPMGate(p_state, drive, dialogue_memory) -> rpm_status
```

The gate checks whether prerequisite mass exists in the right order:

```text
A0 -> Dn -> Wn -> Pn
```

For Path C, RPM should operate continuously:

- thresholded mass on prerequisite nodes
- Fisher-Rao distance to the nearest valid prerequisite chain
- broken-node explanation when a chain fails
- repair proposal when a reply would speak from an invalid chain

Training signal:

- penalize replies whose generated CAS state violates RPM
- reward correct refusal/qualification when RPM is incomplete
- log all pass/fail decisions in the generation trace

### 4.4 Meta-Logic Proof Layer

Meta-logic should sit above RPM, not replace it.

Role:

- RPM decides whether a prerequisite chain is structurally valid.
- Meta-logic explains or proves why the chain passed/failed using explicit relations.

Examples:

- `state in NoeticCluster{...}`
- `CoverOf(...)`
- `PartitionOf(...)`
- `Pullback(...)`
- `Product(...)`
- evidence relation between Wn and Pn

Future behavior:

```text
RPMGate says: fail at Wn -> Pn
MetaLogicProof says: no evidence relation covers the required Wn node
Trace says: reply softened/refused because execution authority was unsupported
```

This is a v1.5+ feature, not a v0 blocker.

### 4.5 Non-Transformer NL Decoder

Goal:

Generate fluent English from the CAS state without transformer self-attention.

Proposed module:

```text
SimplexConditionedNLDecoder
```

Inputs:

- `p_state_final`
- `domain`, `drive`, `register`
- `rpm_status`
- `meta_proof_summary`
- `dialogue_memory`
- previous output token

Output:

- next-token distribution over native English/CAS vocabulary
- optional per-token CAS grounding trace

Candidate decoder cell:

```text
h_{t+1} = SSM_or_GRU(h_t, token_embed(y_t), cas_condition, dialogue_memory)
logits_t = vocab_projection(h_{t+1}, cas_condition)
```

Conditioning path:

```text
cas_condition = Project([
  p_state_final,
  domain_dist,
  drive_dist,
  register_dist,
  rpm_status,
  dialogue_memory
])
```

Possible sequence mechanisms:

1. GRU/LSTM baseline: easiest to build and falsify.
2. RWKV-style recurrent mixing: stronger long-context candidate.
3. Mamba/SSM-style selective state-space decoder: best long-context non-transformer candidate, but more engineering.
4. Causal convolution + recurrent state: simple, inspectable, maybe enough for short replies.

The first prototype should use the simplest cell that can pass the fluency gate. Do not jump straight to a complex SSM unless the GRU baseline fails for reasons clearly tied to memory length.

## 5. Training Objective

Minimum loss:

```text
L = L_lm
  + alpha * L_cas_grounding
  + beta  * L_fisher_rao
  + gamma * L_rpm
  + delta * L_trace
```

Where:

- `L_lm`: next-token cross entropy over assistant reply only
- `L_cas_grounding`: generated reply must reclassify to the target CAS state
- `L_fisher_rao`: keep predicted simplex near target simplex under Fisher-Rao distance
- `L_rpm`: penalize invalid prerequisite-chain activation
- `L_trace`: require trace fields to match record provenance and CAS fields

Curriculum:

1. Train encoder only on CAS prediction.
2. Freeze or softly anchor encoder; train decoder on fluent replies.
3. Joint fine-tune with low `alpha/beta/gamma`.
4. Increase structural losses only after replies are fluent enough.

Reason:

If structural losses dominate too early, the model may become CAS-correct but conversationally stiff.

## 6. Data Requirements

Minimum data:

- 50K Tier 3 dialogue records for first serious smoke
- 100K+ for useful comparison against transformer decoder
- explicit meta-logic slice later, not in v0

Record fields needed:

- prompt/reply
- CAS expression
- noetic/domain/drive/register/register_set
- demographic/tone
- conversation_id and turn_index
- trace_id/source/generator_model
- optional RPM/meta-logic annotations when available

The existing 50K Claude Tier 3 run is useful for this future model, but it is not enough to prove the non-transformer path alone. It is enough for first falsification.

## 7. Evaluation Gates

Do not compare this model only by training loss. It must pass practical gates.

### 7.1 Fluency

- blind review: cannot be reliably distinguished from the transformer decoder baseline
- no repetitive loops
- no clipped/telegraphic style
- reply length within 20% of the Tier 3 reference distribution

### 7.2 CAS Grounding

- generated reply reclassifies to intended CAS state at high rate
- no CAS notation leakage unless explicitly requested
- register behavior matches target register

### 7.3 Traceability

Every generated reply must emit:

- final simplex distribution or top-k compressed state
- CAS expression
- RPM pass/fail
- any broken prerequisite node
- generation trace id
- tokenizer/model/checkpoint provenance

### 7.4 RPM

- invalid RPM chains are blocked, softened, or repaired
- RPM failure explanation is stable across paraphrases
- no "Power without Wisdom" pattern in controlled tests

### 7.5 Meta-Logic

For the future meta-logic slice:

- relation operators correctly identified
- proof/explanation is faithful to the relation
- no false proof when relation is absent

## 8. Prototype Phases

### Phase 0: Paper Design Only

This document. No implementation.

Exit:

- Path B v0 conversational model exists
- 50K+ Tier 3 corpus validated
- transformer baseline metrics available

### Phase A: Encoder-Only Simplex Smoke

Build:

- `SimplexStateEncoder`
- Fisher-Rao distance/loss
- RPM trace stub

Train:

- prompt -> CAS labels

Compare against:

- K=9 classifier
- structured-token classifier

Pass:

- within 5-10 pp of K=9 on canonical eval after matched data
- better trace quality than K=9
- no Drive collapse worse than known K=9 baseline

Fail:

- cannot learn CAS state prediction
- Drive/domain/register collapse
- unstable simplex boundary behavior

### Phase B: Decoder-Only Conditioning Smoke

Build:

- `SimplexConditionedNLDecoder`
- teacher-forced reply generation

Use:

- gold CAS state from dataset, not predicted encoder state

Pass:

- fluent short replies
- no CAS notation leakage
- reply-only loss decreases cleanly

Fail:

- repetitive loops
- flat/telegraphic replies
- cannot maintain sentence-level grammar

### Phase C: End-to-End Non-Transformer v0.1

Connect:

```text
SimplexStateEncoder -> RPMGate -> SimplexConditionedNLDecoder
```

Pass:

- generated replies remain fluent
- CAS grounding remains above baseline threshold
- trace is complete

Fail:

- encoder noise destabilizes decoder
- RPM gating causes evasive or stiff language

### Phase D: Head-to-Head Against Transformer Baseline

Compare:

- current transformer decoder baseline from Path B
- non-transformer simplex decoder
- hybrid transformer decoder conditioned on simplex state

Metrics:

- fluency blind review
- CAS grounding
- trace completeness
- inference cost
- train stability
- parameter count

Only promote if it wins on traceability and does not materially lose fluency.

## 9. Likely File Targets When Implemented

Potential new files:

```text
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_state_encoder.py
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_nl_decoder.py
noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_rpm_gate.py
noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_native_nl.py
noetic-compass-scaffold/noetic-compass/cas-native/training/simplex_losses.py
noetic-compass-scaffold/noetic-compass/cas-native/tests/model/test_simplex_state_encoder.py
noetic-compass-scaffold/noetic-compass/cas-native/tests/model/test_simplex_nl_decoder.py
```

Potential reused files:

```text
noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/native_nl_collator.py
noetic-compass-scaffold/noetic-compass/cas-native/training/masked_ce_loss.py
noetic-compass-scaffold/noetic-compass/cas-native/trace/generation_trace.py
docs/working/path_B2_native_nl_collator_design_2026_05_06.md
docs/working/native_nl_sdg_strategy_2026_05_04.md
```

## 10. Hard Rules

- No foreign pretrained weights in production.
- Do not use the 48-dimensional photonics/TKS coincidence as model dimension.
- Keep 40-state simplex / 39-dimensional open-simplex geometry as the structural base unless the formal framework changes.
- Do not replace the Path B transformer/generation work until a working v0 exists.
- Do not promote any non-transformer result without blind fluency review.
- Every generated reply must remain traceable.

## 11. Open Questions

1. Should the first decoder be GRU-based for simplicity or SSM-based for longer context?
2. Should `p_state` be token-updated at every input token or only at phrase/span boundaries?
3. Should RPM gating be hard during generation or soft during early training?
4. How much dialogue memory can remain non-transformer before fluency suffers?
5. Should meta-logic proof objects be generated by rules first, then learned later?
6. What is the minimum corpus size where a from-scratch non-transformer decoder stops sounding flat?

## 12. Recommended Future Execution Order

After Path B v0:

1. Freeze current transformer-based conversational baseline metrics.
2. Implement encoder-only `SimplexStateEncoder`.
3. Train/evaluate it on CAS prediction before touching generation.
4. Implement decoder-only `SimplexConditionedNLDecoder` using gold CAS state.
5. Run short-response generation smoke on 50K Tier 3.
6. Connect encoder + RPM + decoder end to end.
7. Add meta-logic proof layer only after RPM behavior is stable.
8. Compare against transformer baseline and decide whether this becomes Path C mainline.
