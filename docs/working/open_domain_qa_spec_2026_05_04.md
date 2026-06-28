# Open-Domain Q&A Capability for CAS-Native — Path Specification

**Date:** 2026-05-04
**Author:** Research agent (design pass; READ-ONLY, no code changes)
**Status:** v0 path-spec for ratification
**Scope:** A single document describing exactly what architectural changes, SDG extensions, and training are needed for CAS-Native to handle open-domain Q&A prompts ("what's the capital of France?") in a CAS-coherent way.
**Companion docs:** `docs/working/phase2_dst_spec_2026_05_04.md`, `docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md`, `noetic-compass-scaffold/noetic-compass/docs/working/version_b_phase1_sdg_plan.md`, `docs/working/level3_conversational_sdg_spec.md`.
**Memory anchors:** `feedback_eval_file_slip_recurrent.md`, `feedback_gpu_vs_cpu_for_real_training_runs.md`, `project_cas_transformer_modality_mismatch_pivot.md`, `project_cas_transformer_nl_front_door_architecture.md`, `project_version_b_conversational_plan.md`, `feedback_real_metric_is_samples.md`, `feedback_parallelize_sdg_with_training.md`.

---

## 1. Motivation

The framework's value claim is not "we score CAS structure"; it is "CAS structure is the right reasoning substrate for an aligned AI." A discriminative-only CAS-Native — the v1 K=9 baseline at 86.8% all-heads-exact / 93.2% canonical-exact (commit 3232f05) — can classify the cognitive architecture *of* a prompt; it cannot answer it. The user's question — *when can we have a CAS-Native model that answers "what's the capital of France?" in a CAS-coherent way?* — is on the critical path for three reasons:

1. **The framework's promise is generative, not classificatory.** Noetic Compass wraps and produces outputs (Wrap pipeline: 8 stages including Base LLM Call and Output Gate). A discriminative-only model cannot replace the Base LLM Call stage; it can only audit another model's output.
2. **CAS coherence is only testable end-to-end on generation.** Discriminative scoring tells us whether the *input* parses into CAS; it does not tell us whether the *answer* is itself CAS-classifiable, structurally admissible (Correction 1), and coherent with the input's CAS state.
3. **The user explicitly raised it.** "When can we have it?" has two answers depending on path: 1–2 weeks (commercial-LLM-wrapping) versus 6–12 months (pure CAS-Native generative). This document picks one.

Q&A is **additive**, not replacement. The v1 12-axis classifier becomes the input-classifier and answer-classifier of the Q&A pipeline; it is not retired.

---

## 2. The architectural delta

What changes from v1 (12-head structured-prediction classifier) to a Q&A-capable v3?

### 2.1 NL Generation Head (already scaffolded)

`noetic-compass-scaffold/noetic-compass/cas-native/dst/nl_generation_head.py` ships today as a stub. Its public entry point is:

```python
def generate(req: GenerationRequest) -> GenerationResult: ...
```

`GenerationRequest` carries `turn_type: TurnType`, `cas_state: str`, `user_text: str`, and a metadata bag. The current implementation dispatches by `TurnType` to canned templates (`ACK`, `CLARIFY`, `EMPATHIZE`, `REFUSE`, `CLOSE`) or a soft-imported CAS renderer (`cas_native.inference.cas_renderer.render_cas_prediction`) for `ANSWER` / `MIRROR` / `REFUSE_CLAIM` / `PLAN`.

The interface is intentionally narrow so the implementation can be swapped without changing call sites. For Q&A v3 this is the seam where a real generator gets wired in. Three swap candidates are evaluated in §4 (Options A / B / C).

### 2.2 CAS-coherent decoding

Generation must respect admissibility (Correction 1: each operator CO-k has admissibility relation Dk ⊆ I × I; transitions outside Dk are illegal). Three places to bake admissibility into decoding: pre-decoding hint (cheap, coarse), in-decoding token-level constrained sampling (expensive, precise; `cas-native/inference/constrained_sampling.py` exists for the discriminative path and needs extension), and post-decoding filter (classify the output with the v1 discriminative head, reject-and-resample on inadmissibility). Practical v3 choice: post-decoding filter plus a pre-decoding hint in the system prompt. In-decoding constraints deferred to v4.

### 2.3 Memory / context

Q&A often needs prior conversation. The plumbing exists in `noetic-compass-scaffold/noetic-compass/cas-native/dst/state_tracker.py` — a frozen + immutable `DialogState` carrying `turn_history`, `current_cas_state`, `cas_state_history` (walk-back stack as cache, per Correction 2), and `admissible_next_moves`. Q&A inherits DST as-is; the generator reads `state.current_cas_state` and `state.turn_history` as input context and writes back via `apply_turn`. DST already solves the four naive-stitching failures (repair amnesia, move-type drift, admissibility violation, coherence loss) per `phase2_dst_spec_2026_05_04.md`; Q&A piggybacks rather than re-solving them.

### 2.4 Backbone choice — train from scratch vs foundation model

This is the crux. Two coherent positions:

- **Pure CAS-Native generative (Version B continuation).** Train a generative head on top of the K=9 backbone. Pros: fully owned, CAS-coherent by construction, defensible IP. Cons: K=9 is 128-dim with vocab≈293, far too small to memorize world knowledge; vocab regen needed; matching foundation-model fluency is a multi-year capacity problem.
- **Foundation model wrapped in CAS-coherent constraints.** Use Claude/Llama as the generator; wrap with CAS-Native as pre-classifier (input → CAS state) and post-classifier (output → CAS state); enforce admissibility between them. Pros: fluency is free; capability in 1–2 weeks; each piece runs in its competence zone. Cons: third-party-API dependence; brand becomes "CAS-wrapped" not "CAS-Native."

The lesson from `project_cas_transformer_modality_mismatch_pivot.md` is load-bearing: a frozen CAS-CLM backbone underperformed hash features ~100x on a structured wedge — the architecture is right for *classification*, wrong for *open-domain generation*. The recommended v3 (§5) routes around the constraint by giving CAS-Native its shaped role (structural classifier on both ends) and outsourcing world-knowledge generation to a foundation model.

---

## 3. The SDG extension

### 3.1 What today's SDG produces

Level 3 conversational SDG (`docs/working/level3_conversational_sdg_spec.md`) produces single-turn records: `user_prompt → assistant_response` paired with `cas_expression`, soft operator/domain targets, and provenance. ~19,454 records in `level3_recoverable_full.jsonl`, ~29,181 in `level3_pilot_full.jsonl`. `assistant_response` is constrained (no diagnosis, no prediction, no certainty claims; plain-language; at most one CAS expression). Volume is enough for K=9 classifier training, nowhere near enough for open-domain generation.

### 3.2 New record type: Level 4 Q&A

For Q&A capability, SDG needs a new schema (proposed: `cas-synthetic/schemas/level4_qa.schema.json`) layered on top of Level 3:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `l4qa_…` prefix |
| `qa_kind` | enum | `factual` \| `definitional` \| `procedural` \| `opinion` \| `scenario_reasoning` |
| `user_prompt` | string | The question (verbatim, free-form English) |
| `gold_answer` | string | The reference answer (short — one sentence to one paragraph) |
| `prompt_cas_expression` | string | CAS classification of the question |
| `answer_cas_expression` | string | CAS classification of the gold answer |
| `admissibility` | object | `{ source_state, target_state, admissible: bool }` |
| `soft_operator_targets_prompt` | array[10] number | Distribution for the question |
| `soft_operator_targets_answer` | array[10] number | Distribution for the answer |
| `soft_domain_targets_prompt` | array[4] number | P/C/E/O for question |
| `soft_domain_targets_answer` | array[4] number | P/C/E/O for answer |
| `register_pair` | object | `{prompt_register: T\|A\|f\|E, answer_register: …}` |
| `provenance` | object | Same shape as Level 3 |

`prompt_cas_expression → answer_cas_expression` must satisfy the admissibility relation (Correction 1). For factual recall, the canonical pattern is `^9^O|A` on both sides — question is the trigger, answer is the retrieved Idea brought to Mind. For definitional, `^6^C|A → ^6^C|A` (compositional decomposition). For opinion, `^E|f` register on both sides with Noetic depending on stance. Mapping is rule-driven, not LLM-judged.

### 3.3 Coverage axes

Five Q&A kinds × four registers × four domains = 80 cells; uneven by design (factual+|A+O dense; opinion+|f+P sparse but load-bearing). Target ≥100 records per non-empty cell, ~3,000 in dense cells. Canonical CAS patterns per kind:

- **factual** ("what's the capital of France?") — `^9^O|A → ^9^O|A`. World-knowledge recall.
- **definitional** ("what is gradient descent?") — `^6^C|A → ^6^C|A`. Compositional unpacking.
- **procedural** ("how do I reverse a string in Python?") — `^7^O|A → ^7^O|A`. Rhythm-domain step sequence.
- **opinion** ("what do you think of capital punishment?") — `|f` register required; Noetic depends on stance.
- **scenario_reasoning** ("trolley problem variant") — `^P` domain, often compound `(^2^P|A × ^3^P|A) = ^Ω` per Clarification 10.

Demographic-tonal axes (per `version_b_phase1_sdg_plan.md` T2/T3) carry over: `demographic_profile` and `tonal_profile` paraphrase surface form without touching CAS labels. CAS-invariance under those axes is a v1 property the Q&A head must inherit, re-tested on the new Level 4 eval set.

### 3.4 Volume target

- **Demo capability** (basic Q&A on canonical questions): 10K–25K Level 4 records, 1 Q&A kind × 4 registers, dominantly factual.
- **Functional capability** (handles all 5 kinds with reasonable coverage): 50K records, all kinds × all registers, with demographic axis sampling at ~6 combos per source per Phase-1 plan.
- **Robust capability** (handles open-domain reasoning, edge cases, ethics scenarios): 200K+ records, scenario_reasoning over-sampled, tonal axes fully populated.

### 3.5 Cost envelope (Claude Sonnet API at current pricing)

Per Lever-3 cost model in `cas_native_conversational_broadening_proposal_2026_05_04.md` §3 Lever 3: ~$3/M output tokens, ~150 output tokens per record. Plus Claude generates *both* `gold_answer` and the CAS classifications for prompt and answer, so output ~400 tokens/record.

| Volume | Output tokens | API cost | Wall-clock (modest concurrency) |
|---|---|---|---|
| 10K records | 4M | ~$12 | ~3 hr |
| 50K records | 20M | ~$60 | ~12 hr |
| 200K records | 80M | ~$240 | ~36 hr |

These are rough but match the user's $50–200 estimate for a 50K batch. Cost is bounded; this is not a budget-buster.

### 3.6 Quality gates

Reuse Level 3 review machinery, extended: `gold_answer` honors the same prohibitions as `assistant_response`; `answer_cas_expression` must compile through `api/notation/compiler.py`; `(prompt_cas_expression, answer_cas_expression)` must pass the admissibility check; factual records cross-check `gold_answer` against a structured knowledge source (Wikidata) at SDG time; opinion records must hedge. The recurring eval-file-slip failure (`memory/feedback_eval_file_slip_recurrent.md`) applies — held-out and train files MUST have visibly distinct names (proposed: `level4_qa_eval_2k.jsonl` vs `level4_qa_train_50k.jsonl`); train/eval scripts must `grep` for the suffix before launching.

---

## 4. Three sequencing options

| | Time | Cost | Approach |
|---|---|---|---|
| Option A — Pure CAS-Native generative | 6–12 months | ~$200–500 in API + RunPod | Generative head from scratch, trained on extended SDG corpus |
| Option B — Hybrid: CAS-Native classifier + Claude/Llama generator | 4–8 weeks | ~$50–100/month inference | CAS-Native classifies on both ends; commercial LLM generates with CAS pre/post-constraints |
| Option C — Constrained decoder over commercial LLM | 1–3 months | ~$30/month inference | Foundation model with CAS admissibility baked into decoding via grammar / logit-bias |

### 4.1 Option A — Pure CAS-Native generative

*Today:* K=9 backbone exists (commit 3232f05, 93.2% canonical-exact); admissibility scoring path works; adding a generative head is mechanically feasible (vocab regen → small Transformer decoder → cross-entropy on Level 4 corpus).
*Blockers:* (1) **Capacity.** A 128-dim, 293-token model cannot memorize world knowledge; "Paris" must be in the tokenizer to be produced. Vocab expansion to ≥30K BPE is a fresh-run, not a continued-fine-tune (same lesson as `cas_native_conversational_broadening_proposal_2026_05_04.md` Lever 1). (2) **Modality mismatch.** `project_cas_transformer_modality_mismatch_pivot.md` already documented this gap; reapplied to generation, the K=9 architecture cannot produce English at fluency.
*Pros.* Defensible IP, CAS-coherent by construction, the long-arc answer to "what does a CAS-Native AI look like?"
*Cons.* Multi-year capacity problem; foundation-model fluency unattainable at our scale; wrong place to spend pre-revenue runway.
*Verdict.* Right destination, wrong starting point. Schedule for v4+.

### 4.2 Option B — Hybrid: CAS-Native classifier + Claude/Llama generator

*Today:* Anthropic connector exists at `noetic-compass-scaffold/noetic-compass/api/llm_connectors/anthropic_connector.py` (50 lines, working). The Wrap pipeline (CLAUDE.md §"Wrap Pipeline") *already is* this architecture — Input Analyzer (pre-classifier) → Base LLM Call (foundation model) → Operator Scoring + Inversion Scan + Output Gate (post-classifier). We are not inventing; we are completing.
*Blockers:* Connection wiring. Input Analyzer needs a thin adapter feeding free-form English to the K=9 K9_DiagLoop checkpoint; Output Gate needs the same adapter wired in reverse. ~1–2 days each.
*Pros.* Demo capability in 1–2 weeks, production in 4–8 weeks. Cost is the foundation-model API bill (~$50–100/month at modest volume). Each component runs in its competence zone.
*Cons.* Third-party-API dependence; brand becomes "CAS-wrapped"; per-Q&A latency 500ms–2s; cost scales with usage.
*Verdict.* Right v3.

### 4.3 Option C — Constrained decoder over commercial LLM

*Today:* Foundation models support logit bias / JSON schema / structured output; CAS compiler (`api/notation/compiler.py`) is importable and ~ms-latency.
*Blocker.* Constrained decoders constrain *form*, not *coherence*. Forcing the model to *emit* `^9^O|A` does not force the *English* to realize it. CAS coherence still requires a post-classifier — which is just Option B.
*Verdict.* Not a v3 option. Possibly a v3.5 optimization on top of B (logit-bias the foundation model toward outputs the post-classifier accepts, reducing reject rate).

---

## 5. Recommendation

**Option B — Hybrid: CAS-Native classifier + Claude/Llama generator.**

Reasoning from first principles:

1. **Use each piece for what it is good at.** v1 is a 93.2%-canonical-exact structural classifier. Foundation models are trillion-parameter open-domain generators. Pairing them puts each in its competence zone. Forcing a 128-dim, 293-vocab model to produce "Paris" is using a screwdriver to drive a nail.
2. **The Wrap pipeline already specifies this.** CLAUDE.md §"Wrap Pipeline" *is* Option B: Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call → Operator Scoring → Domain Coherence → Inversion Scan → Output Gate. We complete it, not invent it.
3. **CAS coherence is enforced at the boundaries.** Pre-classifier reads the prompt's CAS state; post-classifier reads the answer's; admissibility (Correction 1) gates the transition. The framework's coherence claim does not require the generator itself to be CAS-Native.
4. **Defensible against capacity arguments.** "Your CAS-Native model can't generate fluent English" — correct, and the answer is "it isn't supposed to. It classifies, validates, admits." The framework's claim is structural admissibility, not raw generation.
5. **Composes with Option A as the long arc.** When Version B Phase 1–6 lands a real CAS-Native generative head, it slots into the Base LLM Call stage and Option B becomes Option A.

This is **not** "abandon Version B." Version B continues; from-scratch generative is the long-arc destination. Option B ships in 4–8 weeks while Version B plays out over 12–18 months.

---

## 6. CAS-coherence at generation time

A Q&A answer must respect CAS structural invariants: real-time CAS classification + admissibility from the question's state. This is where the **network tracer (Mode 7)** becomes load-bearing — it logs `(prompt_state, answer_state, admissibility, register_match, drive_consistency, domain_coherence)` for every turn and flags drift (e.g., factual `^9^O|A` answered with value-laden `^2^E|f`) before render.

Three coherence checks at generation time:

1. **Admissibility check.** `is_admissible(prompt_state, answer_state)` per Correction 1. If false, regenerate or fall back to `REFUSE`.
2. **Register coherence.** Register-pair table enumerable; pre-compute legal register transitions per Q&A kind. Some mismatches are legal (an `|A` question can have an `|E` answer if the user asks how something feels); most are not.
3. **Domain coherence.** Domain Descent (P → C → E → O) constrains question→answer domain transitions. P-question should not be answered in O without explicit cascade. Already a Wrap pipeline stage.

When a check fails, the tracer records *which* failed, *what* the states were, and *what* the model did (regenerate, refuse, caveat-render). This is the v3 debug data and the dashboard's Q&A-view data.

---

## 7. The capital-of-France example — full v3 trace

Given user input: `"what's the capital of France?"`

1. **CAS-Native classifier on input (v1 K=9 head).** A knowledge-recall question classifies as: Noetic `^9` Below/Effect (the Idea brought to Mind by a trigger), Domain `O` Operational (knowledge-retrieval), Register `|A` Analytical, Drive `F2` Wisdom. Compound: `^9^O_{F2}|A`.
2. **Route to Q&A head with structural context.** The Conversation Engine checks `admissible_next_moves`. For a fresh `OPEN` user turn, admissible assistant moves are `{ACK, MIRROR, EMPATHIZE, CLARIFY, ANSWER, REFUSE, REFUSE_CLAIM}`. A short well-anchored factual prompt routes to `ANSWER`. The NL Generation Head receives `GenerationRequest(turn_type=ANSWER, cas_state="^9^O_{F2}|A", user_text=...)`. Under Option B the head wraps this as a foundation-model call with system context: *"You are answering a question whose CAS classification is `^9^O_{F2}|A`. Produce a short factual answer. The answer's CAS classification must itself be `^9^O_{F2}|A` or in the admissibility neighborhood."*
3. **Foundation model generates.** `"The capital of France is Paris."`
4. **CAS-Native classifier on the ANSWER.** Same v1 K=9 head: Noetic `^9` (the Idea brought to Mind — completes the recall), Domain `O`, Register `|A`, compound `^9^O|A` (drive may underspecify on a short answer; acceptable).
5. **Admissibility check.** `is_admissible(prompt="^9^O_{F2}|A", answer="^9^O|A")` → True. `^9 → ^9` is admissible per Correction 1 (the question raises the trigger; the answer lands the effect; same Noetic on both sides under register-set occupancy `|⟨A⟩`).
6. **Apply turn → DialogState.** `apply_turn(state, Turn(role="assistant", text="The capital of France is Paris.", turn_type=ANSWER, cas_state_after="^9^O|A", cas_transition="recall_complete"))`.
7. **Render.** Plain answer, optionally with CAS metadata trace: `"The capital of France is Paris. [^9^O_{F2}|A → ^9^O|A, admissible, register-coherent]"`.

The full trace round-trips: question's CAS structure → admissibility-bounded generation → answer's CAS structure → admissibility check → DST update → render. Every step is observable via the network tracer; every step is auditable. Achievable on the 4–8 week timeline because every component exists in some form — needs wiring, not invention.

---

## 8. Open questions

1. **Can v1's 12-axis head share parameters with a generative head?** Probably yes via a shared backbone (same encoder, two heads). K=9's 64-dim bottleneck is likely too small to support meaningful fluency; this is a Version B v4 question, not a v3 question. For Option B v3, the generator is the foundation model and the question doesn't apply.
2. **How much SDG corpus for "open" vs "closed-domain" Q&A?** Closed-domain (Q&A within the framework, e.g. "what's `^9^O|A`?") might work at 10K records — small answer space. Open-domain (anything a user might ask) is genuinely unbounded; 200K is a sample, not coverage. Argues directly for Option B: foundation models have already absorbed the open-domain corpus we cannot afford to re-absorb.
3. **Does the demographic-tonal axis carry over?** Yes — v1 demographic-tonal robustness is a property the Q&A head must inherit. Eval gate: same Q&A prompt under multiple demographic-tonal axis values must yield same CAS classification.
4. **Hallucination on factual recall.** Foundation model will confidently generate wrong facts. Post-classifier catches CAS-*incoherent* answers; it does NOT catch *factually wrong but CAS-coherent* ones ("capital of France is Lyon" classifies to `^9^O|A` as cleanly as the correct answer). Needs retrieval grounding or hedged-answer mode for low-confidence questions.
5. **Latency budget.** Two foundation-model calls (generate + optional regenerate-on-reject) push p50 to 1–3s. CLAUDE.md performance target of <500ms is for classification, not generation; Q&A needs its own latency target.
6. **Refusal vs hedge.** When admissible but uncertain, hedge or refuse? DST has `REFUSE` and `REFUSE_CLAIM`; the uncertainty-policy for Q&A is undefined.
7. **Inversion-axis monitoring.** Seven-axis inversion scanner (CLAUDE.md §"Inversion Axes") applies to the Output Gate; conversational inversions look different from prompt-classification inversions and need tuning.

---

## 9. Honest timeline

| Milestone | When | Path |
|---|---|---|
| Path-spec ratified (this doc) | This week | — |
| Phase 2 DST + NL Generation Head full implementation | 6–10 days post-v1 | Already Phase-2 plan |
| Q&A training corpus generation (Lever 3-style, ~50K records) | 1–2 weeks parallel | SDG track (CPU-bound; per `feedback_parallelize_sdg_with_training.md` runs concurrently with any GPU work) |
| First Q&A retrain (Option A pure-CAS-Native head; experimental) | ~3–4 weeks | RunPod, fresh-run with vocab regeneration |
| First Q&A demo (Option B foundation-model wrapping) | ~5–6 weeks | Production-grade wiring, latency tuning, monitoring |

**Faster path: Option B with commercial LLM wrapping — basic capability in 1–2 weeks** by wiring v1 K=9 as a pre-classifier to Claude, generating through the existing Anthropic connector, and post-classifying with the same K=9 head. Scoped as a 7–10 day spike:

- Day 1–2: extend `nl_generation_head.py` to route `ANSWER` turns through Anthropic via the existing connector.
- Day 3–4: pre-classifier wiring — feed the K=9 output into the system prompt.
- Day 5–6: post-classifier wiring — K=9 on the LLM output; admissibility check; reject-and-retry (cap 3).
- Day 7: integration test on curated Q&A set (factual, definitional, opinion, scenario). Wire trace into DST.
- Day 8–10: latency tuning, error handling, monitoring.

The 4–8 week path is the production-hardening pass: full Level 4 SDG corpus (50K records), demographic-tonal eval, network tracer integration, Q&A-specific inversion-axis tuning. 1–2 weeks delivers a *demo*; 4–8 weeks delivers a *product*.

---

## 10. Summary of choices baked into this spec

- **Option B (hybrid) is the v3 recommendation.** Option A is the v4+ destination, scheduled but not blocking. Option C is degenerate.
- **Q&A is additive, not replacement.** v1 K=9 stays — it moves from "the model" to "the input/output classifier of the wrap pipeline."
- **The Wrap pipeline (CLAUDE.md §"Wrap Pipeline") is the architectural target.** We complete, not invent.
- **CAS-coherence is enforced at the boundaries** (pre-classifier + post-classifier + admissibility), not inside the generator. The framework's claim cashes out at the boundary, not the generator.
- **DST + NL Generation Head are the seam.** Scaffolds at `cas-native/dst/state_tracker.py` and `nl_generation_head.py`; they get wired to foundation model and K=9 classifier.
- **Level 4 Q&A SDG is the data work.** Schema on top of Level 3, ~50K records, ~$60 API, runs parallel to GPU training (per `feedback_parallelize_sdg_with_training.md`).
- **The network tracer (Mode 7) is load-bearing for diagnostics.** Records every step (admissibility, register coherence, domain coherence). It is the data layer for the dashboard's Q&A view.
- **Answer to the user's question:** two weeks for a demo, eight weeks for a product.

---

## Appendix A — Files to touch (enumeration; no code in this design pass)

**Wiring (Option B v3 spike).** `cas-native/dst/nl_generation_head.py` (extend `ANSWER` branch to route to foundation-model connector); `api/llm_connectors/anthropic_connector.py` (confirm/extend streaming + system prompt); `cas-native/inference/predict_cas.py` (expose K=9 head as pre/post-classifier callable); `api/pipeline/` (wire the Q&A turn into existing Wrap stages); `cas-native/dst/state_tracker.py` and `dialog_grammar.py` (consume as-is, no change).

**Data (Level 4 SDG).** `cas-synthetic/schemas/level4_qa.schema.json`; `cas-synthetic/generator/qa.py`; `cas-synthetic/templates/level4_qa_templates.yaml`; `cas-synthetic/scripts/generate_level4_qa.py` (analogue of `generate_level3_conversations.py`); `cas-synthetic/validation/level4_qa_validator.py` (extends Level 3 review gate with admissibility check).

**Tracing / observability.** `cas-native/trace/` — Mode 7 network tracer (designed in parallel).

**Documentation.** `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`; `docs/working/` completion doc per standard cadence.
