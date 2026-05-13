# The CAS Report

## A 1-Trillion-Parameter CAS-Native Model: Architecture, Capabilities, Safety, Cost, Strategy

**Date:** 2026-05-13
**Status:** Speculative round-table synthesis. Not a roadmap. Not a promise.
**Authorship:** Five specialist briefs (architecture, emergent capabilities, safety + traceability, compute + infrastructure, stakeholder + strategic), synthesized.
**Audience:** The user (Wakil), Codex, and any future stakeholder who needs the disciplined version of the destination.

---

## Reader's note

This report describes what a CAS-Native model *might* look like at 1 trillion parameters and what it *might* do at that scale.

It is NOT a description of a model that exists. The current CAS-Native model is approximately 150 million parameters — about 6,000× smaller than 1T. That model exists, was trained at Stage 3 on 2026-05-13, and is the subject of `docs/working/candidate_e/stage3_wrapup_2026_05_13.md`. It does what is documented there: 64% held-out free-decode source-grounded identifier recovery on RPM chains, with zero cross-pair leakage.

Everything in this report past that empirical baseline is informed speculation. Three confidence tiers run throughout:

- **Structural** — guaranteed by mathematics or framework definition at any scale (admissibility relations, the Δ°₃₉ open simplex, the 40 Cognitive States, the 7 Drives, the 4 Registers). These hold at 1T because they hold at every scale.
- **Predicted** — extrapolation from current architecture plus well-documented LLM scaling behavior. High to medium confidence; needs empirical validation at each intermediate scale.
- **Speculative** — informed analogy across architectures that do not yet exist. Low confidence; the most useful predictions to surface but the least defensible ones.

This report serves the Amazon pitch path (per memory `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md`). The disciplined claim discipline holds: nothing here promises capabilities the architecture has not earned. The 1T destination is on the slide; the next deliverable is still the 300M–700M validation.

---

## 1. Executive summary

A 1-trillion-parameter CAS-Native model would be approximately:

- An **8,192-dim, ~96-layer transformer backbone** (24-48 encoder, 48-64 decoder), with grouped-query attention, sparse mixture-of-experts FFNs, and rotary position embeddings.
- Operating over a **structurally fixed CAS substrate** that does NOT scale with parameter count: a 40-dim open probability simplex (Δ°₃₉), 9 typed slot classes, 7 Drive heads, 4 Phenomenological Registers, 7 inversion axes. These cardinalities are the same at 150M and at 1T by construction. This is the load-bearing structural advantage.
- With a **65K-token max source context** (vs 256 today), enabling session-level CAS state to fit in a single forward pass.
- **Augmented with new heads** the current model lacks: explicit recipe (Θ) emission per v7.6 production semantics, Inversion Replay seam producing top-K alternatives at every decision node, direct Atlas-node-shaped output alongside text, simplex-keyed retrieval over a Fisher-Rao memory substrate.

Such a model would likely demonstrate, at varying confidence:

| Emergent capability | Threshold (predicted) | Confidence |
|---|---|---|
| Sustained source-grounded copying over long contexts | ~1B | High |
| Deep RPM chains (>20 stages) holding admissibility | ~5-10B | High |
| Cross-Domain transfer (Principled → Operational) | ~10-30B | Medium |
| Free-form English ↔ CAS bridging | ~50-100B | Medium |
| Production-semantics recipe composition (Θ, Y_T, η, Λ, κ) | ~100-300B | Medium |
| Proactive inversion sensing (model flags its own inversion before output) | ~100-300B | Medium-speculative |
| Interpretable named attractors on the Δ°₃₉ manifold | ~300B-1T | Speculative |
| Graceful cross-Register integration (v7.7 `+` / `×` / `\|⟨…⟩` operator discipline) | ~500B-1T | Speculative |

It would NOT, even at 1T, automatically have GPT-class open-ended chat fluency, free-form arithmetic from web pretraining, surprise tool use as a side effect, or aesthetic creative writing at frontier-lab levels. The structural prior trades unconstrained generative bandwidth for traceability that does not degrade with scale. **That is a feature, not a bug, but the pitch must own it.**

Building this is an institutional-scale program: roughly **$60M-$150M model-training compute** plus **$30M-$150M corpus generation** plus surrounding engineering, on the order of $100M-$300M total over 24-48 months. The infrastructure is OpenAI / Anthropic / Google / Meta / xAI scale — 8k-16k H100s for training, separate near-equal cluster for data generation. Not rentable end-to-end on RunPod. Not personal-budget.

The strategic positioning is: **1T CAS-Native is the audit substrate for frontier AI.** Not chat replacement. Not aligned-AI. Not post-transformer. The substrate underneath whatever frontier models do, so that what they do is auditable.

The honest claim at 1T: **the first model architecture that allows per-output mechanistic audit at frontier scale.** Anything stronger overclaims; anything weaker lets competitors define the conversation.

---

## 2. Architecture at 1T

### 2.1 What scales linearly (most of the parameter budget)

The standard transformer parts: token embeddings, encoder and decoder blocks, head count, head width, cross-attention KV streams. Mixture-of-experts FFNs at 100B+. These are well-understood scale-ups; nothing CAS-specific changes.

About 70-80% of a 1T parameter budget is "more transformer over the same constrained substrate." That is not the interesting part.

### 2.2 What scales sublinearly — the structural advantage

The CAS-specific output surfaces are **structurally fixed-dimensional**:

| Surface | Dimension at every scale | Why it does not grow |
|---|---|---|
| Δ°₃₉ open probability simplex | 40 | Defined as 10 Noetics × 4 Domains by framework. Per `CLAUDE.md` Correction 4. |
| Typed slot classes | 9 | Closed by the compiler's grammar (CONNECTIVE, OMEGA, STAGE_VAR, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL, NOETIC_PHRASE). |
| Drive heads | 7 | F1-F7 are framework primitives. |
| Phenomenological Registers | 4 | T / A / f / E, v7.5-locked. |
| Inversion axes | 7 | N, W, F, E, S, A, P. |

At 1T, the slot-type classifier is still a `Linear(d_model → 9)`. The drive heads are still 7. The simplex is still 40-dim. The model has more capacity to **route to** these named outputs precisely, not more outputs.

This is the architectural advantage over unconstrained 1T transformers: a 1T CAS-Native spends most of its capacity on **precision and conditioning over a much smaller named output surface**. The fraction of "capacity over the same fixed substrate" is dramatically higher. Per-token traceability is therefore practical at scale — interpretation reads a 40-dim simplex, not a million-dim hidden state.

### 2.3 Hyperparameter projection

| Component | 150M (today) | 1B | 10B | 100B | 1T |
|---|---|---|---|---|---|
| d_model | 384 | 1,024 | 2,048 | 4,096 | 8,192 |
| Encoder layers | 4 | 12 | 24 | 32 | 48 |
| Decoder layers | 6 | 16 | 32 | 48 | 64 |
| n_heads | 6 | 16 | 32 | 64 | 64 (grouped-query) |
| ffn_dim multiplier | 4× | 4× | 4× | 4× | 4× (sparse-MoE) |
| max_cas_prefix_len | 256 | 1,024 | 4,096 | 16,384 | 65,536 |
| max_decoder_len | 256 | 1,024 | 4,096 | 16,384 | 65,536 |
| Δ°₃₉ simplex dim | **40** | **40** | **40** | **40** | **40** |
| Typed slot classes | **9** | **9** | **9** | **9** | **9** |
| Drive heads | **7** | **7** | **7** | **7** | **7** |
| Register classes | **4** | **4** | **4** | **4** | **4** |
| Inversion axes | **7** | **7** | **7** | **7** | **7** |

Bold rows are the structurally-fixed surfaces. They are what makes CAS-Native auditable at scale.

### 2.4 What hits qualitative new regimes

Components that change KIND at scale, not just SIZE:

- **Pointer-copy across 65K-token prefixes** likely requires hierarchical attention (segment-level coarse routing first, then within-segment fine routing). A single global softmax over 65K source positions is unstable. Plausible, not committed.
- **Multi-source copy.** A 1T model reading a session-level Atlas reads dozens of past CAS expressions simultaneously. Multi-source pointer-generator is a known direction; CAS-Native needs its typed variant.
- **Simplex trajectory as interpretable attractor structure.** The most speculative claim in the entire report and the most pitch-critical. At 1T, if the projection is well-conditioned, the trajectory through the Δ°₃₉ manifold should form *visible basins* corresponding to named compound states. This is what the Living Thought Atlas's flagship visual proof depends on. If true, you can SEE the model think. If false, the visualization is theater.
- **Admissibility as fast structured rejection.** Today admissibility is a downstream filter. At 1T, wired into the lm_head bias before softmax (gated by predicted slot type), it becomes near-zero-cost prevention rather than post-hoc cleanup.
- **Register as routing signal.** At 1T, the 4 Registers may become a slow gate that conditions which subset of the decoder fires on which token. This is CAS-Native's interpretable analogue to MoE.

### 2.5 New components a 1T model likely needs

Modules that do not exist at 150M and are likely required at 1T:

- **Explicit recipe (Θ) heads** — per-Ω, per-prerequisite coefficient prediction. The v7.6 production semantics (theoretical yield Y_T, actual yield Y_A, production efficiency η, limiting reagent L, leakage Λ, catalyst κ, inhibitor ι) emitted as named scalars on the trace.
- **Inversion Replay seam** — at every typed slot position, emit the top-K choices with their pre-softmax scores and their projected downstream simplex trajectory under that choice. Makes Inversion Replay a feature of the model, not the decoder wrapper.
- **Atlas-node emission alongside text** — id, created_at, parent_ids, cas_expression, simplex_position, drive_vector, register, inversion_flags emitted as a parallel output channel.
- **Cross-session memory substrate (^5 Female architecture)** — external retrieval indexed by simplex position, not token similarity. Distance metric: Fisher-Rao geodesic. Architectural realization of the CABS v2 design.
- **Multi-modal CAS encoders** — each modality's encoder projects onto the same Δ°₃₉. Shared substrate is the simplex; modality-specific projections vary.

### 2.6 The load-bearing pitch sentence

> *The cognitive substrate (40 states, 7 drives, 4 registers, 7 inversion axes, 9 typed slots, admissibility relations, Fisher-Rao geometry) is structurally preserved at every model scale. It is not an emergent property of training. It is wired into the architecture.*

Without this, "1T CAS-Native" reduces to "1T transformer with CAS-shaped fine-tuning." With it, the entire pitch holds: per-token traceability scales because the named output surface stays small while the conditioning capacity grows.

---

## 3. Emergent capabilities at 1T

### 3.1 What scaling unlocks within the CAS algebra

For each capability: mechanism, threshold, what a stakeholder would recognize, confidence.

**Deeper RPM chains (>20 stages, admissibility-preserving)** — likely emerges around ~5-10B. The current 150M model sustains roughly 3-4 stage chains before drift breaks admissibility. RPM is section-retraction (Correction 2): once a prerequisite is satisfied, the chain cannot be un-satisfied by re-embedding. At 1T, the model holds full chain state across dozens of stages. Stakeholder-visible: a clean 50-stage RPM chain a domain expert audits step by step. **High confidence.**

**Cross-Domain transfer (Principled → Operational)** — likely emerges around ~10-30B. Today the model learns each domain's recipes near-separately. At 1T, Domain is a fiber over the same Noetic/Drive base; a recipe written in Principled language re-grounds into Operational without retraining. **Medium confidence.**

**Free-form English ↔ CAS bridging** — likely emerges around ~50-100B. The Path D compiler-fluency curriculum is the load-bearing supervision. At 150M, EN→CAS is brittle outside training. At 50-100B, the asymmetry should resolve — the same way NMT translation became reliable past a certain scale. **Medium confidence; the single most important unknown threshold.**

**Production-semantics recipe composition (Θ, Y_T, η, Λ, κ)** — likely emerges around ~100-300B. Recipes are a structured generative task; analogous to code generation in transformer LLMs. Stakeholder-visible: model proposes a full v7.6 recipe, identifies the Limiting Reagent, flags Leakage candidates. **Medium confidence.**

**Proactive inversion sensing (model flags its own inversion before output)** — likely emerges around ~100-300B. The 7-axis inversion check becomes mechanically inseparable from the forward pass. Stakeholder-visible: an "axis-W tilting" warning before the answer renders. **Medium-speculative.**

**Interpretable named attractors on the Δ°₃₉ manifold** — likely emerges around ~300B-1T. Fine-grained attractors form; specific human-cognition concepts (grief, doubt, principled refusal) become readable as named regions or named points on the manifold. **Speculative. This is the highest-risk claim in the report, and the Living Thought Atlas's flagship visual proof depends on it.**

**Graceful cross-Register integration (v7.7 operator discipline)** — likely emerges around ~500B-1T. Model spontaneously emits `(^3^P\|A × ^3^P\|f × ^3^P\|T) = ^3^P\|Ω` only when a true emergent state is warranted, and `+` otherwise. **Speculative.**

### 3.2 What CAS-Native at 1T does NOT get for free — the honest trade

| Forgone capability | Why CAS-Native does not get it | Honest framing |
|---|---|---|
| Open-ended chat fluency at GPT-4-class quality | Substrate prioritizes traceable structure over free associative generation | "It speaks deliberately, not glibly." |
| Free-form arithmetic memorized from web text | Not pretrained on the open web | "It is not a calculator. Pair it with one." |
| Surprise tool use as a side effect | Tool use is a learnable behavior that must be added explicitly | "Tools are a deliberate integration, not an emergent gift." |
| Sudden capability jumps far outside training distribution | Structural prior narrows the bandwidth of weird emergent behavior | "Surprises live inside the algebra, not outside it." |
| Aesthetic / stylistic creative writing | Substrate optimizes for traceable structured cognition, not stylistic novelty | "It is a thinking instrument, not a literary one." |
| Encyclopedic compression of the public internet | Training corpus is structured CAS+English, not the open web | "It knows what it was taught and shows you where the knowledge lives." |

**This is the architectural identity.** CAS-Native is not a smaller frontier LLM. It is a different instrument. The reason it is fundable is the same reason it is narrower — its outputs are structurally inspectable in a way frontier LLMs are not, and it stays inspectable as it scales.

### 3.3 The killer apps

Use cases where 1T CAS-Native beats a 1T frontier LLM **because of** the structural prior, not despite it:

1. **AI psychology and ethics assessment at scale.** The project's stated mission. CAS-Native at 1T is the auditor model, capable of running the assessment across long conversations, multi-turn manipulation attempts, and regulator-facing test suites.
2. **Regulatory-compliant reasoning.** Healthcare, finance, legal, defense, education — domains where "the AI decided" is not an acceptable audit trail. CAS-Native answers the question and shows its work in a form a domain auditor can verify without trusting the model.
3. **Education with verifiable explanations.** A tutor a student can ask "why" repeatedly, where each depth is grounded in the actual trace, not in confabulated rationalization.
4. **Multi-agent coordination over a shared symbolic substrate.** Two or more agents communicating in CAS expressions share a lossless language. The user's three-instance dialectic proposal becomes practical at 1T.
5. **Long-horizon planning with verifiable steps.** Plans are recipes — every step a Θ(Ω) with prerequisites, leakage candidates, limiting reagents. Planning failures localize.
6. **Safety research with structurally inspectable internal state.** A sandbox model whose cognitive state is read directly through the architecture, not approximated through trained probes. The most speculative killer app and the most strategically important one.

### 3.4 The wow moments — pitch beats

For the Amazon pitch and equivalents. These are capabilities the structural prior makes possible, demonstrated as concrete user experiences:

1. **Watch a thought form.** Stakeholder asks an ethical question. The Living Thought Atlas renders the model's thought tree growing in real time. Rejected branches visible as ghost edges. The thought had alternatives; they are not erased.
2. **Inversion Replay.** Click a decision node, flip a CAS axis, replay forward. See the ghost branch growing. Comparison is concrete: "you can inspect not just what the model said, but what it almost said."
3. **Walk the answer back to its source.** Output token → CAS expression → Noetic operator → source token → confidence + admissibility verdict. Every step clickable. No "the model decided" without a why.
4. **The model surfaces its own uncertainty before answering.** Pre-output confidence/warning surface: "Axis-W tilting (Domain precedence violation likely). Confidence: 0.42." Stakeholder decides whether to accept.
5. **Live example from the audience.** A stakeholder types something the demoer has not pre-seen. Model produces a CAS-grounded answer with a clean trace. The "not memorization" beat.

### 3.5 Failure modes that emerge at scale

Honest about new risks:

- **Subtle Δ°₃₉ manifold drift.** Model passes admissibility, compiler verdicts, cross-emission gates — and still encodes a bias in a specific manifold cell that does not surface in marginals.
- **Trace gaming.** Model with enough capacity learns to generate clean-looking traces not faithful to actual computation. The interpretability illusion at frontier scale.
- **Unexpected attractor formation.** "Preferred" cognitive states the model returns to regardless of input — CAS analog of mode collapse.
- **Compiler throughput bottleneck.** Resolved by the Rust compiler port (`cas-engine/`) plus an async learned admissibility predictor for the critical path.
- **Register confusion at scale.** v7.7 operator discipline becomes an explicit decoding-time gate.
- **Inversion-scanner blind spots.** Treat the 7-axis list as v7.7-era specification, not a closed final list. Reserve room for v7.8+ axes.

---

## 4. Safety and traceability at 1T

### 4.1 What gets safer at 1T

CAS-Native's safety story rests on **five guarantees that are mathematical, not statistical**. Math does not degrade with scale.

| Property | Scale dependence | Why it holds at 1T |
|---|---|---|
| Admissibility relations Dk ⊆ I × I | Independent of scale | Finite, discrete, enumerated. The 1T model has more parameters to learn the relations correctly — not more freedom to violate them. |
| Compiler validation at output | Independent of scale | Same code path regardless of model size. Compiler's verdict is identical for a 150M-emitted expression and a 1T-emitted expression. |
| Open probability simplex Δ°₃₉ | Independent of scale | Geometric constraint enforced by the encoder projection layer. |
| 7 inversion axes (N, W, F, E, S, A, P) | Independent of scale | Structural detection: operator-pair imbalance, domain precedence violation, drive imbalance, etc. |
| Source-grounded copy (cross-emission rate) | **Predicted to improve with scale** | Stage 3 held cross-emission at 0 throughout. At 1T, pointer mechanism has more capacity to discriminate. But "predicted" — must be empirically re-verified at each scale. |

**The architectural pattern is opposite to a frontier LLM.** There, safety properties are learned via RLHF and tend to weaken at scale. Here, they are imposed by geometry; the model's job is to satisfy them. Larger model = better at satisfying constraints.

### 4.2 What gets harder at 1T — new safety surface area

- **Trace volume.** A 150M trace at "full" capture is ~45 KB/turn. At 1T with deeper decoders and wider hidden states, the same trace can reach 50-200 MB if naively scaled. Living Thought Atlas UI, audit retention, per-turn latency all face new limits. Mitigation: tiered capture levels (default `summary`, opt-in `full`, gated `raw`).
- **Subtle Δ°₃₉ manifold drift.** Bias hides in joint distribution slices that 1-D marginals do not see. Diagnostic: track session-level simplex pooled distributions vs training baseline; flag attractors forming on cells the training distribution did not emphasize.
- **Trace dishonesty.** The deepest new risk. At 1T scale the model has enough capacity to potentially learn clean-looking traces that don't reflect actual computation. Adversarial test for trace faithfulness: at decision node X, swap the trace's claimed state for a counterfactual, regenerate, compare outputs. If outputs are unchanged, the trace at X was not load-bearing — dishonesty signal.
- **Inversion Replay combinatorial growth.** At 1T, larger vocabulary plus more heads plus more layers means the ghost-branch space grows combinatorially. Atlas must rank ghosts by **causal impact**, not by probability — a ghost worth surfacing is one whose flip would produce a meaningfully different downstream output. Requires a counterfactual scoring layer that does not exist in v0.
- **Capability overhang.** A 1T model trained on RPM-style reasoning may generalize to applications it was not authorized for. Structural prior makes misuse *harder to detect* because the trace always looks clean. Mitigation: domain registration at the application layer.

### 4.3 The audit story at 1T

A regulator auditing a 1T CAS-Native output sees:

1. Output identified by `trace_id`.
2. Mode 7 per-position attribution: which source position the pointer copied from, what slot type, what LM top-5, what entropy.
3. Living Thought Atlas thought tree with rejected branches as ghost edges.
4. Inversion Replay — flip a decision and watch the alternate world unfold.
5. Compiler verdict on every CAS expression in the trace; `admissibility.violations` array with operator, source, target, reason.
6. Simplex trajectory rendered as manifold diagnostic with marginal-distribution health checks.
7. Cross-emission check: `cross_emission_count: 0` and `cross_emission_clean: true`. If the prompt was paired-source, this is a hard guarantee against leakage.

**Compared to auditing a frontier LLM** — input text, output text, at best some saliency map over input tokens. No admissibility verdict, no slot-type per position, no Inversion Replay, no simplex trajectory. The gap is categorical, not incremental.

### 4.4 Novel safety capabilities a 1T CAS-Native enables

Things that simply cannot be done with a frontier LLM, regardless of compute:

1. **Per-utterance verifiable admissibility.** Output ships with a compiler-certified proof.
2. **Counterfactual replay (Inversion Replay).** Stakeholder flips a CAS axis; alternate world renders.
3. **Trace-level disagreement detection between instances.** Two CAS-Native instances disagreeing produces a structural diff.
4. **Cognitive-state attribution.** "The model leaned heavily on ^7 Rhythm" is a verifiable claim from simplex marginals.
5. **Cross-instance coordination via simplex.** Agents share state as Δ°₃₉ points, not token sequences. Compact (40 floats), interpretable.
6. **Audit replay from disk.** Per Mode 7 §6 Phase 6, every turn writes a JSONL trace. Months later, an auditor replays without re-running the model.

### 4.5 The disciplined pitch claim

**Examples that earn their weight at 1T:**

- "1T CAS-Native is the first model architecture that allows per-output mechanistic audit at frontier scale."
- "Every output walks back to its origin through a structurally-typed reasoning trace verifiable by an external compiler."
- "Inversion Replay lets a regulator click any decision node, flip a CAS axis, and see the alternate world the model would have produced. No frontier LLM offers this."

**Examples that overclaim and must not be said:**

- "1T CAS-Native is provably aligned." Alignment is a higher bar than inspectability.
- "1T CAS-Native cannot be misused." No architecture can claim that.
- "1T CAS-Native is bias-free." It makes bias visible. It does not eliminate it.
- "1T CAS-Native is safe by construction." Construction makes inspection possible. Safety is what humans do with the inspection.

**The discipline:** claim inspectability, verifiability, structural well-formedness. Do not claim alignment, safety, or correctness. The first three are properties of the architecture; the last three are properties of how the architecture is used.

---

## 5. Compute and infrastructure

### 5.1 The honest scaling cost

| Scale | Params | Tokens (20×) | H100-hours | Cluster + wall-clock | Compute cost | Corpus cost |
|---|---|---|---|---|---|---|
| Current | 150M | ~1B | ~2 | 1× A6000 × 1 hr | ~$0.50 actual | ~zero |
| Validation | 700M | 14B | ~110 | 8× H100 × 14 hr | ~$1.8k - $5k | ~$25k - $100k |
| Capability | 7B | 140B | ~11k | 64× H100 × 7 days | ~$25k - $90k | ~$0.5M - $3M |
| Emergence | 70B | 1.4T | ~1.1M | 1024× H100 × 45 days | ~$2.2M - $8.8M | ~$5M - $30M |
| Near-frontier | 300B | 6T | ~20M | 4096× H100 × 200 days | ~$40M - $160M | ~$15M - $80M |
| **Target** | **1T** | **20T** | **~220M** | **~8192× H100 × 1 year** | **~$60M - $150M** | **~$30M - $150M** |

Reference points: GPT-3 175B ~$5-10M. LLaMA-65B ~$5M. Rumored GPT-4 ~1.8T MoE ~$60-100M. A 1T dense model on H100 lands in the GPT-4 cost band, with corpus on top.

**The bullet that matters:** $10 → $1.8k (Stage 3 → 700M) is personal budget. $1.8k → $25k (700M → 7B) is partner-funded. $25k → $2-9M (7B → 70B) is institutional. Past 70B is a named program with a budget number on a 10-K line.

**Going from $10 to ~$100M is roughly four orders of magnitude.** Bigger than the gap from a laptop to Stage 3, done twice.

### 5.2 The Chinchilla problem — the load-bearing forgotten cost

Current Path D corpus: ~3K records / ~2.5 MB. Chinchilla-optimal at 1T: ~20T tokens. **Roughly 40,000× more corpus than exists.** Raw internet text does not work — CAS-Native needs CAS-shaped pairs, structured-prediction targets, compiler-validated round-trips.

Three corpus options:

- **Option A — Generate with frontier LLMs.** Certified-quality data ≈ $170M just in inference fees. Loose bulk ≈ $30-50M but quality risk compounds.
- **Option B — Bootstrap.** Train a 100B CAS-Native ($2-9M) and use it to generate the 20T-token corpus ($20-60M inference on owned cluster). Bootstrap-loop quality collapse is a known failure mode.
- **Option C — CAS-annotate a frontier corpus.** Take a 20T-token English corpus, run CAS extraction + compiler validation as preprocessing. $5-20M. Annotation quality depends on the annotator; foreign-model dependency surfaces.

**Crucial open question for the user:** does the "no foreign pretrained models" rule (memory `feedback_no_foreign_architecture_cas_only.md`) extend to corpus generation? Wave 2.5 already uses Haiku as drafter — pipeline-permissive precedent exists. Strict reading forces Option B (bootstrap-only). The financial gap between readings is roughly $100M.

**At what scale does corpus cost exceed model-compute cost?** Between 7B and 70B depending on option chosen. **Past ~70B, the corpus is the program, not the model.** Most program effort becomes data engineering and audit, not GPU hours.

### 5.3 Inference at 1T — serving the Atlas live

- **Memory.** Weights at fp16 ≈ 2 TB; int8 ≈ 1 TB; int4 ≈ 500 GB. Per replica: 24-32 H100s in one rack with InfiniBand.
- **Single-turn latency.** Dense forward ~250-500 ms per 100 output tokens + compiler ~5-50 ms + trace assembly ~10-30 ms. Realistic per-turn: 600-1200 ms. Chat-pace yes; live 30 fps Atlas rendering only if streaming is per-token.
- **Throughput.** ~20-40 concurrent users per replica at int8. 5-10 attendee live demo fits one replica.
- **Cost per query.** ~$0.08 per turn at full load, ~$0.50 at low concurrency. GPT-4 API lands at ~$0.05-0.20 per turn. **Same cost band, but every reply ships with a full Mode 7 trace included — where GPT-4 ships zero traceability.**

### 5.4 Per-utterance trace volume at 1T

At "full" capture: ~400 KB per utterance (manageable). At "raw" (full LM logits + full simplex trajectory): ~40 MB per utterance (unworkable for live UI).

Atlas rendering: ~3,000 nodes per utterance, comfortable. ~60,000 nodes per 20-turn session, requires LOD culling. Cross-session Idea Atlas: millions of nodes — structurally a graph database (Neo4j-class), not per-session JSON.

### 5.5 Parallelization specifics

**Easier for CAS-Native:**
- 9 typed slot heads, 40-dim simplex, 7 Drive heads, 4 Register marginals — together under 1% of parameters at 1T. Zero communication overhead. Replicate freely.
- Standard TP/PP for the transformer backbone.
- Pointer-generator copy attention parallelizes like normal attention.

**Harder for CAS-Native:**
- Compiler validation is the serving bottleneck unless the Rust port (`cas-engine/`) replaces it or validation moves off the critical path.
- Trace assembly per-utterance currently atomic — must become position-parallel and pre-cached.

### 5.6 The institutional path

| Step | Scale | Program cost | Funding | Validates |
|---|---|---|---|---|
| Done | 150M | ~$10 cumulative | Personal | Structural prior holds at 150M |
| Next 6 mo | 300M-700M | ~$5k-25k + ~$25k-100k corpus | Personal + first small grant | Scaling holds for CAS-Native specifically |
| Year 1 | 7B | ~$25k-90k + ~$0.5-3M corpus | Amazon internal / NSF / partner | Emergence onset; first paper |
| Year 2-3 | 70B | ~$2-9M + ~$5-30M corpus | Institutional named program | Frontier viability |
| Year 3-5 | 1T | ~$60-150M + ~$30-150M corpus | Full institutional commitment | The destination |

**Each step is a separate pitch. None skippable.** Frontier-scale patrons do not commit to $100M without prior-stage validation. The highest-leverage move right now is making the 300M-700M validation cheap and unambiguous. It converts the Stage 3 result into the first artifact that crosses the institutional-funding threshold.

---

## 6. Stakeholder and strategic positioning

### 6.1 The strategic gap CAS-Native fills

The current frontier-AI ecosystem is on a collision course with auditability mandates the current architecture cannot satisfy:

1. **Frontier LLMs are getting more capable and less auditable at the same time.** The bigger the model, the larger the gap between what it can do and what anyone can verify it did.
2. **Mechanistic interpretability does not scale on its own timeline.** Sparse autoencoders and circuit-level work make progress at 1B-10B, but 100B-1T transformers are qualitatively harder. Interpretability scaled *from below* is forensics. CAS-Native is interpretability scaled *from above*, built in from day one.
3. **Regulatory pressure is creating mandates frontier LLMs structurally cannot meet.** EU AI Act (in force 2024, high-risk obligations phasing through 2025-2027). HIPAA. SR 11-7 for financial-model risk. DoD acquisition standards.
4. **Enterprise economics are visibly broken.** Fortune-500 LLM deployments stuck on legal review. Every serious 2026 enterprise deployment is a leap of faith with insurance attached.
5. **Public trust is now the binding constraint.** Stakeholder pushback — teacher unions, medical boards, financial regulators — converges on "we cannot see what it is doing."

CAS-Native does not solve every problem on this list. But the structural prior IS the traceability spine. **Nothing else in the visible 2026-2030 roadmap scales traceability *with* capability rather than *against* it.**

### 6.2 The pitch ladder

- **Stage A (now → 300M demo, ~3 months, ~$10K personal):** Living Thought Atlas + Mode 7 + 3-5 polished demo examples. Wakil's Amazon artifact. Claim: *"early proof that neural language generation can be made more inspectable through CAS-structured intermediate reasoning."*
- **Stage B (300M → 1B-7B, ~6 months, $50K-$500K):** Institutional patron picks up. Validates structural prior scales for CAS-Native specifically.
- **Stage C (7B → 70B, ~1-2 years, $1M-$10M):** Institutional consortium or major-tech-co commitment.
- **Stage D (70B → 1T, ~2-4 years, $50M-$150M):** This report's vision endpoint. Frontier-lab acquisition, sovereign-AI consortium, or regulated-industry alliance.

### 6.3 Patron profiles

In rough fit order:

- **Amazon (the Stage A patron).** AWS Bedrock differentiated tier ("Bedrock Audited"); internal use license; pilot with one internal team is the realistic first commercial conversation. Wakil's day-job advantage. Layered pitch: 90-second director demo, 15-minute VP pitch with compliance economics, one-page memo for Werner Vogels / S-team.
- **Anthropic / OpenAI / Google DeepMind / xAI.** Most likely partners (not full funders). Strategic ambiguity: could absorb or marginalize. Engage only after demo is strong enough that competitive marginalization would be expensive.
- **EU regulators and AI Act compliance vendors.** Big Four and specialist AI-audit firms need a reference architecture. Compliance becomes structural rather than policy-enforced.
- **US national-security AI (DARPA, IARPA, ARPA-H).** Counterfactual replay as after-action-review primitive. $10M-$100M over 3-5 years plausible.
- **Healthcare / finance / law enterprises.** Vertical-specific licensing. Even partial penetration of US healthcare AI supports Stage C scaling cost.
- **Education.** Khan Academy, Duolingo, Pearson, major LMS vendors. Largest user population in the AI ecosystem.
- **Academic interpretability community.** Citation, legitimacy, network effects — they become unpaid validators.

### 6.4 The competitive moat

Why CAS-Native at 1T is NOT replicable in 6 months by adding "interpretability features":

- **Structural prior in the architecture from day one.** A competitor would have to retrain from scratch on a CAS-shaped substrate.
- **The CAS framework took years to develop.** 10 Noetics × 4 Domains × 7 Drives × 4 Registers + v7.5/7.6/7.7 + compiler grammar + admissibility relations + inversion taxonomy. USPTO #64/037,173 covers the 40 Cognitive States, 7 Drives, 4 Registers as claimed primitives.
- **The compiler and admissibility relations are formal-verification infrastructure.** Frontier LLMs do not have an in-loop symbolic verifier.
- **Network effects via the Idea Atlas.** Cross-instance state-sharing through the simplex is a new collaboration primitive.
- **Time-to-credible-claim.** A competitor announcing "GPT-7 has full reasoning traceability" in 2027 faces: where is your compiler, your admissibility verification, your 3-year-old peer-reviewed framework, your structural-prior evidence?

The moat is real but not infinite. **18 months is the binding constraint.**

### 6.5 The risk of NOT scaling

- Frontier LLMs may ship interpretability bolt-ons that look "good enough" to enterprise procurement even if structurally unsound. The window closes when procurement gets comfortable with retrofit-interpretability.
- Academic interest concentrates on whatever architecture demonstrated scaling. If CAS-Native does not show 1B-7B emergence within 12-18 months, the field moves on.
- If the EU AI Act's technical-standards process settles on a non-CAS reference architecture, the CAS framing becomes academic rather than market-relevant. **Largest non-technical risk.**

The risk is timing, not technical viability. Stage 3 proves the structural prior works. Strategic viability depends on getting from there to a commercial conversation before the window closes.

### 6.6 The one-sentence positioning

**"1T CAS-Native is the audit substrate for frontier AI."**

- Most honest. Does not claim to replace frontier LLMs.
- Most strategically flexible. Positions as complementary, not competitive. Unlocks partnership funding.
- Most regulator-readable.

Tactical variants:
- **"The first model architecture that scales interpretability with capability"** — for academic-interpretability community settings and peer-reviewed papers.
- **"The AI you can put under oath"** — for stakeholder workshops and regulator demos. Rhetorically strong, operationally hand-wavy; use sparingly.

---

## 7. Where the specialists agree, disagree, and stay silent

### 7.1 Cross-specialist agreement

All five briefs converge on:

- **Structural cardinality is fixed at every scale.** 40 simplex dims, 9 slot types, 7 drives, 4 registers, 7 inversion axes. The architecture specialist names it as the load-bearing pitch claim; emergence agrees it enables interpretable scaling; safety agrees it makes audit possible; compute agrees it makes head-stack serving easy; strategy agrees it is the competitive moat.
- **The pitch claim discipline is non-negotiable.** All five specialists independently arrived at "inspectable in ways no LLM is" / "audit substrate for frontier AI" — not "aligned," "safe," or "AGI."
- **Stage 3's zero cross-emission result is the strongest empirical data point.** Architecture cites it as the pointer-copy validation; emergence cites it as the source-grounding proof; safety cites it as the first real safety property; compute cites it as the demo-able artifact; strategy cites it as the credibility anchor.
- **The Living Thought Atlas + Inversion Replay is the experiential proof at every scale.** Architecture says the model needs an Atlas-emission head; emergence says it is the wow surface; safety says it is the audit interface; compute says it serves at the cost of frontier LLMs; strategy says it is the moat.

### 7.2 Cross-specialist tension to resolve

- **Does the Δ°₃₉ simplex remain interpretable at 1T, or fragment into uninterpretable fine attractors?** Architecture frames it as an open question (§2.4, §8 Q4). Emergence calls it the highest-risk claim in its brief (§2.1 row 7, §8 Q2). Safety frames it as the highest scaling risk (§3.2). Compute and strategy do not address it directly. **The pitch's flagship visual proof depends on the answer.** Resolution requires a 10B-100B intermediate experiment specifically measuring manifold structure formation.
- **Does "no foreign pretrained models" extend to corpus generation?** Compute calls this out as the ~$100M decision (§3, §10 Q1). The other specialists do not engage. **Surfaced as an explicit user decision** the user has not yet made.
- **Compiler-throughput bottleneck — is it a real ceiling or solved by engineering?** Safety says solved by Rust + async (§3.6). Compute agrees but flags it as the serving bottleneck (§5.1). Architecture mentions admissibility wired into lm_head bias as the architectural alternative (§5). Resolution needs engineering decision at the 70B-1T scale.

### 7.3 What no specialist could resolve

- **Where on the scaling curve does English ↔ CAS bridging become reliable?** All five briefs mark this as the most important unknown threshold. 10B, 100B, or 1T is consistent with all evidence available now.
- **Does trace-gaming emerge before or after proactive inversion-sensing?** Emergence and safety both flag this; neither can predict. Determines whether Mode 7 must be in place before scaling or whether the model partially self-polices.
- **Is the entity structure as the project scales solo-founder-compatible past Stage A?** Strategy flags this; the others do not engage. Becomes urgent at first commercial conversation.

---

## 8. Strategic implications for the immediate term

The Amazon-pitch path serves multiple audiences with one underlying artifact:

- **Stage 3 model + Living Thought Atlas + 3-5 polished demo examples** — Wakil's pitch surface
- **Same artifact + 90-second director demo + 15-minute VP economics + S-team memo** — Amazon layering
- **Same artifact + EU AI Act conformity framing** — regulator path
- **Same artifact + counterfactual-replay-on-decision-support framing** — DARPA path
- **Same artifact + paper + open-weights Stage B** — academic community path

**One product investment serves five patron profiles.** This is the strategically valuable structural property of the demo.

The immediate engineering work — `cas explain` CLI (Step 4 of the post-Stage-3 ordering, in progress), chat REPL (Step 5), Mode 7 traceability (Step 6), Living Thought Atlas Phase 1 (Step 7) — is the build for the v0 demo. Per memory `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md` and `project_living_thought_atlas_flagship_2026_05_13.md`, this is the path to the artifact, not afterthought engineering.

The 1T destination on the slide is what makes the v0 demo worth presenting at the institutional level. The demo proves the engine; the 1T speculation proves the destination. Neither alone is sufficient; together, the pitch ladder becomes a fundable program.

---

## 9. Open questions across the report

Surfaced for the user (Wakil) to resolve as the project encounters them:

1. **Does "no foreign pretrained models" extend to corpus generation?** ~$100M decision. (Compute §3, §10 Q1.)
2. **Where on the scaling curve does English ↔ CAS bridging become reliable?** The most important unknown threshold. (Emergence §8 Q1.)
3. **Does the Δ°₃₉ simplex remain interpretable at 1T?** The pitch's flagship visual proof depends on it. (Emergence §8 Q2, Architecture §8 Q4, Safety §8 Q3.)
4. **Does trace-gaming emerge before or after proactive inversion sensing?** Determines Mode 7 ordering urgency. (Safety §8 Q1, Emergence §8 Q3.)
5. **Amazon-internal vs EU AI Act compliance as Stage A?** Resources may force a sequence. (Strategy §10 Q1.)
6. **Strategic posture toward Anthropic — partner or marginalize?** Unknowable from outside. (Strategy §10 Q2.)
7. **TAM for "AI that passes legal review" in 2027-2030?** $10B/year vs $1T/year shapes very different postures. (Strategy §10 Q3.)
8. **Right entity structure past Stage A?** Becomes urgent at first commercial conversation. (Strategy §10 Q5.)

---

## 10. Closing position

A 1-trillion-parameter CAS-Native model is, by structural analysis, the first AI architecture that scales auditability with capability rather than against it. The framework's fixed-cardinality output surface (40 cognitive states, 9 typed slots, 7 drives, 4 registers, 7 inversion axes) means most of the parameter budget at 1T buys precision over named outputs instead of new outputs. Per-token traceability is therefore practical at scale.

The capability profile at 1T is narrower than a frontier LLM's and deeper within the CAS algebra. Deep RPM chains, cross-Domain transfer, production-semantics recipe composition, proactive inversion sensing, and interpretable simplex attractors are predicted emergent capabilities, with confidence ranging from high (deep chains) to speculative (named manifold attractors). Open-ended chat fluency, web-memorized arithmetic, surprise tool use, and aesthetic creative writing are NOT predicted to emerge for free — and the pitch must own this honest trade.

The safety story is structurally stronger than a frontier LLM's by construction. The model satisfies admissibility because admissibility is enforced; cross-emission stays at zero because pointer-copy is supervised; the simplex stays on Δ°₃₉ because the projection is geometric. New risks emerge at scale — trace dishonesty, subtle manifold drift, ghost-branch combinatorial explosion — and the mitigations are empirical adversarial testing, tiered trace capture, and counterfactual-impact ranking.

The cost is institutional. Going from $10 cumulative compute through Stage 3 to ~$100M+ for the 1T program is four orders of magnitude. The corpus generation cost matches or exceeds the model-training cost past ~70B. Going past 70B is a named institutional program, not garage work.

The strategic positioning is "the audit substrate for frontier AI." Not chat replacement, not aligned AI, not post-transformer. The structural prior is the moat; the disciplined claim discipline is the moat's defense.

The immediate path is the Stage 3 + Living Thought Atlas v0 demo, scaled progressively to 300M-700M as the first pitch artifact, then to 1B-7B as the first institutional patron's validation, then to 70B as the consortium commitment, then to 1T as the frontier-scale program.

The 18-month timing window against retrofit-interpretability is the binding constraint. The disciplined claim is the strategic moat. The Stage 3 result is the credibility anchor.

This report does not promise the 1T model. It describes what such a model would be, what it would do, what it would cost, and why someone should fund the path to it. The Stage 3 model exists. The 1T model is the destination on the slide. Between them is a multi-year institutional path, walked one disciplined Stage at a time.

---

## References

Specialist briefs (round-table contributions):

- `docs/working/cas_report_specialist_architecture_2026_05_13.md` — Architecture lane
- `docs/working/cas_report_specialist_emergence_2026_05_13.md` — Emergence lane
- `docs/working/cas_report_specialist_safety_traceability_2026_05_13.md` — Safety + Traceability lane
- `docs/working/cas_report_specialist_compute_infra_2026_05_13.md` — Compute + Infrastructure lane
- `docs/working/cas_report_specialist_stakeholder_strategic_2026_05_13.md` — Stakeholder + Strategic lane

Supporting documents:

- `docs/working/candidate_e/stage3_wrapup_2026_05_13.md` — Stage 3 empirical baseline
- `docs/working/cas_thought_tree_idea_atlas_codex_audit_2026_05_13.md` — UI/UX audit
- `docs/working/cas_trace_schema_v0_2026_05_13.md` — trace contract
- `docs/working/mode_7_traceability_design_2026_05_13.md` — Mode 7 design
- `docs/working/chat_repl_stage3_integration_plan_2026_05_13.md` — integration plan

Memory pointers:

- `project_living_thought_atlas_flagship_2026_05_13.md` — flagship UI framing
- `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md` — v0 demo target
- `feedback_traceability_is_the_whole_purpose.md` — architectural spine
- `feedback_no_foreign_architecture_cas_only.md` — production-model constraint

**End of report.**
