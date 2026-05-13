# CAS Report — Specialist Brief: Architecture

**Date:** 2026-05-13
**Specialist lane:** Architecture (what the model itself becomes at scale)
**Status:** Speculative round-table input. Not an implementation plan.
**Audience:** Round-table synthesis. Plain-language where possible; jargon defined inline.

---

## 1. TL;DR

- **Most of the transformer stack scales linearly.** Token embeddings, encoder and decoder blocks, head count, head width — these are well-understood scale-ups. A 1T CAS-Native is mostly "deeper and wider over the same constrained substrate."
- **The CAS-specific surfaces scale sublinearly or not at all.** The Δ°₃₉ open simplex (the 40-dim "where in CAS space is this state right now" vector) stays 40-dim by construction. The 9 typed slot heads, the 7 Drive primitives, the 4 Registers, and the 7 inversion axes do not grow. This is structural — not a budget choice. It is the load-bearing claim that distinguishes 1T CAS-Native from 1T unconstrained transformers.
- **A few components hit qualitative new regimes.** Pointer-copy across long compositional recipes, the simplex trajectory as an interpretable attractor manifold, and admissibility relations as fast structured rejection are likely to shift from "scaled-up versions of current behavior" to "behaviors that don't exist at 150M."
- **At 1T the model probably needs additions that don't exist today.** Explicit recipe (Θ) heads, production-semantics outputs (yield, efficiency, limiting reagent), per-utterance Atlas-node emission alongside text, and the Inversion Replay seam emitting top-K alternatives at every decision node are the architecture-side enablers for the flagship UI.

---

## 2. Concrete hyperparameter projection

Current Stage 3 is 150M parameters. The encoder config in `noetic-compass-scaffold/noetic-compass/cas-native/model/simplex_encoder.py:38-51` and the decoder in `typed_fiber_decoder.py:51-74` give the locked starting point.

| Component | 150M (today) | 1B | 10B | 100B | 1T |
|---|---|---|---|---|---|
| d_model | 384 | 1,024 | 2,048 | 4,096 | 8,192 |
| Encoder layers | 4 | 12 | 24 | 32 | 48 |
| Decoder layers | 6 | 16 | 32 | 48 | 64 |
| n_heads | 6 | 16 | 32 | 64 | 64 (grouped-query, ~8 KV groups) |
| head_dim | 64 | 64 | 64 | 64 | 128 |
| ffn_dim multiplier | 4× | 4× | 4× | 4× | 4× (sparse-MoE expert FFN) |
| CAS source vocab | 38,685 | 38,685 | ~50K | ~50K | ~50K (frozen on grammar) |
| English BPE vocab | 50,000 | 64,000 | 100,000 | 128,000 | 200,000 (multilingual) |
| max_cas_prefix_len | 256 | 1,024 | 4,096 | 16,384 | 65,536 |
| max_decoder_len | 256 | 1,024 | 4,096 | 16,384 | 65,536 |
| Δ° simplex dim | 40 | 40 | 40 | 40 | 40 (see §4) |
| Typed slot classes | 9 | 9 | 9 | 9 | 9 (see §4) |
| Drive heads | 7 | 7 | 7 | 7 | 7 |
| Register classes | 4 | 4 | 4 | 4 | 4 |
| Inversion axes | 7 | 7 | 7 | 7 | 7 |
| Trace dict / utterance | ~30 keys | ~60 | ~120 | ~300 | ~600 (recipes, ghost branches, multi-domain) |

Notes on the projection:

- The CAS source-token vocab is frozen by the compiler's grammar (`api/notation/compiler.py`). It does not need to grow proportionally to model size. The current 38,685 reflects the v1c VALIDTOK tokenizer; growth to ~50K reflects future grammar admissions (more meta-logic constructors, more fractal-k literals, more named Ω targets), not size scaling.
- English BPE growth reflects multilingual coverage — speculative, since CAS-Native does not yet pretrain on multilingual text.
- max_cas_prefix_len growth is the harder claim. A 1T model that takes 64K-token CAS prefixes lets a single forward consume a multi-page CAS expression — a full recipe trace with hundreds of compound terms, or a full session's compiled state. At today's 256 max-source-len, the model literally cannot see a session.
- The simplex dim claim (stays 40) is in §4. The trace-dict growth reflects how many distinct interpretable outputs an utterance produces at scale, not internal capacity.

---

## 3. What scales linearly (the easy part)

The standard parts:

- **Token embeddings.** Vocab × d_model. At 1T with d_model=8192 and English vocab 200K, that is ~1.6B parameters in the embedding alone. Standard scaling.
- **Encoder and decoder transformer blocks.** Pre-norm Transformer blocks with rotary positional embedding (`simplex_encoder.py:54-103`) and bidirectional self-attention scale the same way they always have. Increase d_model, increase layers, increase n_heads. Nothing CAS-specific changes.
- **Cross-attention KV streams.** The decoder has two cross-attention paths — one over the simplex trajectory, one over the source-hidden states (`typed_fiber_decoder.py:164-197`). Both scale linearly.
- **Mixture-of-experts FFNs.** At 100B+ the FFN almost certainly becomes sparse-MoE. Each expert is a standard FFN. This is well-understood scaling; nothing about CAS forces it or prevents it.

The first 70-80% of a 1T parameter budget is "more transformer." That is not the interesting part of CAS-Native at scale.

---

## 4. What scales sublinearly (the interesting part)

The CAS-specific surfaces are structurally fixed-dimensional. This is the architectural advantage.

**The Δ°₃₉ simplex stays 40-dim by construction.** The state space is defined as the open probability simplex over 10 Noetics × 4 Domains = 40 cognitive states (CLAUDE.md, Correction 4). This is not a representational bottleneck waiting to be relaxed — it is the framework's identity. At 1T parameters, the encoder's mirror-descent tail (`simplex_encoder.py:186-241`) still projects to 40-dim. What changes is the *quality* of that 40-dim point. At 150M it is a noisy classifier output. At 1T it should be a high-fidelity continuous trajectory through a structured manifold (see §5).

**The 9 typed slot heads do not grow.** `typed_fiber_decoder.py:31-41` defines them: CONNECTIVE, OMEGA, STAGE_VAR, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL, NOETIC_PHRASE. That set is closed by the compiler's grammar. At 1T the slot-type classifier head is still a Linear(d_model → 9). The router gets smarter; the output cardinality does not.

**The 7 Drive heads do not grow.** F1-F7 are framework primitives. They get sharper, more calibrated, better-conditioned on context. They do not become F1-F1000.

**The 4 Registers do not grow.** T / A / f / E. v7.5-locked. Same argument.

**The 7 inversion axes do not grow.** Same argument.

Why this matters for the pitch: a 1T unconstrained transformer spends most of its capacity on internal representations whose meaning is implicit. A 1T CAS-Native spends most of its capacity on a much smaller named output surface. The fraction of "capacity over the same fixed substrate" is dramatically higher. Loosely: most of the extra parameters are buying *precision and conditioning over named outputs* rather than *new outputs*. That is the structural advantage. It is also the thing that makes per-token traceability practical at scale — you don't have to interpret a million-dim hidden state, you read the 40-dim simplex.

Important caveat: this is the speculative claim. Whether the empirical 1T-vs-1T comparison actually plays out this way is unknown. The structural argument is clean; the empirical confirmation requires the run.

---

## 5. What hits qualitative new regimes

Components that change *kind* at scale, not just *size*.

**Pointer-copy across long compositional recipes.** Today the copy mechanism is the cross-attention head's pre-softmax scores in the final decoder block (`typed_fiber_decoder.py:308-319`). At Stage 3 (150M) it sustains ~64% held-out source-grounded copy on 4-stage RPM chains. At 1T with max_cas_prefix_len=65,536, the model has to sustain copy fidelity across recipes with dozens or hundreds of stage variables, multiple Ω targets, and cross-domain ingredient lists. Two things probably need to change:

- **Hierarchical copy.** A single global softmax over 65K source positions is unstable. The natural scale-up is hierarchical pointer attention — segment-level coarse routing first, then within-segment fine routing. This is a *kind* change, not a *size* change. Plausible, not committed.
- **Multi-source copy.** Today copy reads one source. A 1T model talking about a session-level Atlas reads dozens of past CAS expressions simultaneously. Multi-source pointer-generator is a known direction in summarization; CAS-Native would need its typed variant.

**Simplex trajectory as interpretable attractor structure.** At 150M the simplex trajectory is the sequence of 40-dim points produced by the mirror-descent tail. It is meaningful but noisy. At 1T, if the projection is well-conditioned, the trajectory should form *interpretable attractor structure* — visible basins in the Δ°₃₉ manifold corresponding to known compound states (`^3^P|A`, `^7^O|f`, etc.). This is speculative but testable: the Living Thought Atlas's flagship visual proof depends on it. If the manifold structure is real, you can SEE the model think — basins, transitions, residence times. If it's not, the visualization is theater.

**Admissibility-driven structured rejection.** The compiler's admissibility relations (CLAUDE.md, Correction 1) are framework-defined: each operator CO-k has Dk ⊆ I × I. At 150M these are downstream filters that catch invalid model output. At 1T, with the simplex trajectory landing precisely, admissibility should function as a *fast structured rejection path* — invalid (source, target) pairs become zero-probability events at the logit level, not post-hoc filters. The architecture change is wiring admissibility into the lm_head bias before softmax, gated by predicted slot type. Architecturally small, behaviorally large.

**Per-token cognitive register routing.** At 150M, register is mostly a classifier output. At 1T, register may need to become a *routing signal* — a slow gate that conditions which subset of the decoder pathway fires on which token. This is the closest CAS-Native gets to MoE-style conditional compute, and the routing variable is interpretable by construction (4 named registers, not 64 anonymous experts).

---

## 6. Architecture additions a 1T model probably needs

Modules that do not exist at 150M and are likely required at 1T.

- **Explicit recipe (Θ) heads.** CAS v7.6 introduces recipes as proportional weightings: `Θ(Ω) = a₁·X₁ + a₂·X₂ + … + aₙ·Xₙ → Ω` (CLAUDE.md v7.6 section). The current decoder represents recipes only implicitly through copy from the source. At 1T this should be a first-class head: per-Ω, per-prerequisite coefficient prediction, with the production-semantics outputs (theoretical yield Y_T, actual yield Y_A, production efficiency η, limiting reagent L) emitted as named scalars on the trace. Modest parameter cost; high interpretability gain.
- **Inversion Replay seam.** The flagship UI feature (`project_living_thought_atlas_flagship_2026_05_13.md`) requires that at every decision node the model can emit *top-K alternatives*, not just the chosen path. At 150M the decoder produces one greedy decode; alternates come from temperature sampling or beam search. At 1T, an explicit "decision-node alternates head" is probably necessary — at each typed slot position, emit the top-K choices with their pre-softmax scores AND their projected downstream simplex trajectory under that choice. This is the architectural commitment that makes Inversion Replay a feature of the model, not the decoder wrapper.
- **Atlas-node emission alongside text.** The Living Thought Atlas consumes a structured trace dict (`docs/working/mode_7_traceability_design_2026_05_13.md`). At 1T the model should directly produce Atlas-node-shaped output — id, created_at, parent_ids, cas_expression, simplex_position, drive_vector, register, inversion_flags — as a parallel output channel to the lm_logits. This is a side-head, similar in spirit to slot_type_head but with much richer output. The user's "object traceability is load-bearing" rule (memory `feedback_object_traceability_required.md`) becomes architectural at 1T.
- **Cross-session memory substrate (^5 Female architecture).** CAS analog: `^5` (the Mind impregnated with Ideas) corresponds to training data + accumulated context. At 1T, the model needs an external retrieval layer indexed by simplex position and drive vector — not by token similarity. This is the geodesic memory substrate the CABS v2 design doc gestures at. Architecture: simplex-keyed retrieval over a vector store whose keys are 40-dim points and whose distance metric is Fisher-Rao geodesic distance (`d(p,q) = 2·arccos(Σ√(pk·qk))`, CLAUDE.md Correction 4).
- **Multi-modal CAS encoders.** A 1T frontier system reads images, code, documents. Each modality needs its own encoder whose output lands on Δ°₃₉. The shared substrate is the 40-dim simplex; the modality-specific projections vary. This is the cleanest place where CAS structure beats unconstrained multimodal models: every modality maps to the same named cognitive state space.

---

## 7. The "what stays fixed" claim — load-bearing for the pitch

The pitch needs one sentence the stakeholder can verify across every scale of CAS-Native:

> The cognitive substrate (40 states, 7 drives, 4 registers, 7 inversion axes, 9 typed slots, admissibility relations, Fisher-Rao geometry) is structurally preserved at every model scale. It is not an emergent property of training. It is wired into the architecture.

What this gives the pitch:

- **Auditability.** The same Δ°₃₉ vector means the same thing at 150M and at 1T. Stakeholders learning the framework at 150M do not have to re-learn it at 1T.
- **Regulatory framing.** "Show me how this AI represents principled aversion" has a stable answer across scales: index 30-39 of the simplex (the P domain), Noetic axis 3.
- **IP integrity.** USPTO #64/037,173 names the primitives. The 1T model uses the same primitives. The patent claim does not have to be re-filed for each scale.
- **Traceability survives scaling.** The reason 1T CAS-Native can claim per-token traceability while 1T unconstrained transformers cannot is that the named output surface has fixed cardinality. Probing 1T anonymous activations is hopeless; reading a 1T model's 40-dim cognitive state is not.

This is the architectural lock-in. Without it, "1T CAS-Native" reduces to "1T transformer with CAS-shaped fine-tuning."

---

## 8. Open architectural questions

Things I cannot resolve from the current code alone. Other specialists will surface their own; these are mine.

1. **Does the Δ°₃₉ open simplex remain stable as the encoder grows, or does the ε-floor blow up?** The current encoder uses ε=1e-6 with softmax + ε-floor + renorm (`simplex_encoder.py:217-222`). At 1T the logit scale shifts dramatically and floor violations may dominate. Open question: does the simplex projection need to switch to a learned exponential-family parameterization to stay numerically clean at scale?
2. **Does pointer-copy across 65K-position prefixes actually work without hierarchical routing?** The current copy is a single global softmax over source positions. The empirical question is whether dense full-attention copy survives the scale, or whether hierarchical/segmented copy becomes mandatory. This determines whether the decoder block in `typed_fiber_decoder.py:164-197` needs a new variant.
3. **What is the right MoE routing variable at 1T — a learned gate, or the predicted register?** Standard MoE uses a learned anonymous gate over N experts. CAS-Native could use the 4 registers as a 4-expert gate (interpretable but small) or layer register-conditioning on top of standard MoE (interpretable + capacity). Both are plausible; the trade-off is not obvious from current evidence.
4. **At what scale does the simplex trajectory become genuinely interpretable as an attractor manifold?** The Living Thought Atlas's visual proof depends on this. At 150M the trajectory is suggestive but noisy. The question is whether the regime transition happens at 1B, 10B, 100B, or 1T — and whether there is a known training intervention that brings it forward. If basins do not form, the flagship UI loses its main empirical anchor.
5. **How does scheduled sampling generalize to multi-source decoding?** Stage 3 closed the teacher-forcing-to-free-decode gap with one-step scheduled sampling over a single source (`scheduled_sampling.py:1-71`). At 1T with multi-source copy (Atlas-keyed retrieval + current source + recipe ledger), the exposure-bias problem becomes multi-headed. Open question: is one-step still sufficient, or does the full autoregressive rollout become non-optional?

---

**End of brief.** Word count: approximately 1,750.
