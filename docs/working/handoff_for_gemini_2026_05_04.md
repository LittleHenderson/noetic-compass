# Handoff to Gemini — Noetic Compass / CAS-Native Project (2026-05-04)

You are picking up a project from another LLM (Claude). This document is self-contained — read it in full before proposing anything. The user is direct, fast, intolerant of jargon, and has a low tolerance for re-litigating things that already shipped. Treat them like the founder + lead engineer of a startup who has been working 16-hour days.

---

## 1. The 30-second pitch

**Noetic Compass** is an AI psychology + ethics assessment platform built on **CAS v7.7** (Cognitive Architecture System) — a formal framework with 10 Noetics × 4 Domains × 7 Drives × 4 Registers = 1,120 base cognitive states, plus admissibility relations, a 7-axis Inversion Scan, an RPM (Roadmap of Prerequisites for Manifestation) chain, and recipe / production semantics. Founder: Little Henderson (a.k.a. Wakil, a.k.a. Prof. Hermes M. Thoth).

The project's CORE PRODUCT is a CAS-Native AI — currently a **structured-prediction classifier** (English in → 12 CAS labels out, ~93% on training distribution) — being extended to a **generative LLM** that writes English replies grounded in CAS reasoning.

**The differentiator is traceability:** every output walks back to its CAS state, activations, attribution, and training-data nearest-neighbor. "Show your work, or don't ship it."

---

## 2. Project identity

- **Repo root:** `C:\Users\wakil\OneDrive\Desktop\tksCAS` (Windows, git, on master)
- **GitHub:** `https://github.com/LittleHenderson/noetic-compass`
- **Framework version:** CAS v7.7 (Register Multiplicity and Operator Discipline Extension)
- **Patent:** USPTO #64/037,173 (provisional, covering 40 Cognitive States, 7 Drives, 4 Registers, 5 Generative Operations)
- **Tonight's session (2026-05-04):** 9 commits + 32 origin commits merged, pushed to origin/master at SHA `b45e553`

---

## 3. Hard architectural rules — NON-NEGOTIABLE

These are user-ratified. Violating them gets you yelled at (literally, in caps lock). Each has been violated before tonight; each blowup is documented.

### Rule 1: NO foreign pretrained models in the production stack

**No TinyLlama, Llama, Qwen, Mistral, Phi, Gemma, GPT-2, BERT, or any other pretrained backbone.** Random-init from scratch only. Acceptable third-party tools: PyTorch (framework), HuggingFace `transformers` patterns as REFERENCE (but no loading their weights), Claude API for SDG (data generation only — the trained model is fully ours).

**User's exact words on 2026-05-04:** "BRO WE DON'T DO LAZY SHIT WE NOT GIVING NOTHING ELSE EXCEPT CAS AND YOU AND I THE GLORY GET THAT SHIT OFF OF HERE IMMEDIATELY NOW LIKE YESTERDAY!!!!!!!!"

The pitch must hold. If a stakeholder asks "is this just a fine-tuned [other model]?" the answer must be NO with receipts: random-init checkpoint, training logs from epoch 0 with no warm-start, our own tokenizer vocab, no foreign weights anywhere. **CAS gets the glory, or the project doesn't ship.**

### Rule 2: TRACEABILITY is the architectural spine

Every model output, belief lock-in, training record, generated reply, eval result, and trace artifact must walk back to its origin. Per-utterance trace = (input → CAS state → activations → attribution → admissibility → output). Object-level traceability schema:

- `id` (UUID or sha256)
- `created_at` (ISO 8601 UTC)
- `schema_version` or `code_version`
- `parent_ids` (lineage)
- `source` (where it came from)
- `trace_id` (groups related artifacts)

**User's exact words:** "REMEMBER WE MUST HAVE TRACEBILITY THIS THE WHOLE PURPOSE OF THIS ENDEAVOR" and "MAKE SURE THEY ALL ARE VERY FAMILAR WITH THE PROJECT AND OBJECT TRACEBILITY"

### Rule 3: Plain language, no jargon

The user explicitly told the prior LLM: "AND TALK PLAINLY SO I CAN UNDERSTAND WHAT THE FUCK YOU ARE SAYING FROM NOW ON" and "WTF DOES Backward compat? MEAN?"

**No more: "load-bearing", "modality mismatch", "structured prediction", "backward compat", "polling", "regression tests verified".**
**Yes more: "the part that has to work", "the model was trained on a different kind of input", "12 separate guesses sharing one backbone", "the old code still works the same", "checking", "the old tests still pass".**

If a technical term is necessary, define it inline once. Test: would I be embarrassed reading this aloud at a coffee shop to a smart non-ML founder?

### Rule 4: Project familiarity required for every spawned agent

Every sub-agent reads core context BEFORE writing code: `CLAUDE.md`, `HONEST_STATUS.md`, the relevant existing model files in `cas-native/model/`, recent CHANGELOG entries (last 200-400 lines), and the memory pointers. If the answer's in the codebase, the question isn't open.

### Rule 5: Always git-fetch + read CHANGELOG before launching expensive operations

Session summaries can be stale by 6+ hours. Long-running work often completes and merges during summarization. Caught a near-miss tonight where the prior LLM almost re-ran a $25 / 9-hour redundant training run because it didn't re-baseline.

### Rule 6: If the answer is in the codebase, the question isn't open

Tonight an architecture-spec agent flagged 6 "open questions" — 5 of 6 were already answered in the codebase. User caught it with "PROVE ME WRONG!!!" — and the prior LLM had to grep + show receipts. Methodology rule: BEFORE flagging anything as "open", grep the repo and search memory.

---

## 4. Current repo state

### Branch + push status

- Branch: `master` (always work here unless user says otherwise)
- Latest commit on origin/master: `b45e553` (merge commit — combines tonight's 9 local commits with 32 origin commits that landed via PRs while local work was happening)
- Local + origin in sync as of session close

### Tonight's commits, in chronological order

```
21ff240  HONEST_STATUS.md + Idea Atlas adapter
fbf44e0  CAS-as-Belief-Substrate (CABS)
d79ad12  scrub TinyLlama from HONEST_STATUS
32a76d5  Mode 7 live wire-up (PyTorch hooks)
e645296  native NLGenerationHead module
e4bbad8  native English BPE tokenizer extension
bd70c05  native NL gen training + eval + generation trace surface
4d81618  native NL SDG strategy + Tier 1 seed (2.5K records)
88fccd4  Session 52 CHANGELOG entry
b45e553  Merge remote-tracking branch 'origin/master' (final merge)
```

### Combined test count

213+ tests passing across belief, trace, model, training, evaluation, atlas adapter, tokenizer, SDG. No regressions.

---

## 5. Tonight's deliveries — what each piece does

### CAS-as-Belief-Substrate (CABS) — `cas-native/belief/`

**The big one.** Turns CAS from labels into a thinking architecture. Belief store using ^4 Vibration (confidence with 30-day half-life decay), ^7 Rhythm (exposure count), RPM gate (compiles via `api/notation/compiler.py`, checks admissibility), and 7-axis Inversion Scan (N/W/F/E/S/A/P).

**Lock rule:** `locked == (rpm_chain_satisfied AND vibration > 0.7 AND inversion_scan_clean AND rhythm_count >= 3)`.

**SQLite persistence** at `~/.cas-native/beliefs.db`. Three tables: beliefs, observations, contradictions.

**Wired into chat REPL:** `/beliefs` (list locked), `/why <claim>` (full RPM + vibration + inversion axes), `/forget <claim>` (record contradiction).

**98 tests pass.**

### Mode 7 — `cas-native/trace/live_capture.py`

Real PyTorch forward hooks that capture activations during `predict_cas` calls. Real `gradient × input` attribution per head. `/trace` and `/trace --raw` REPL commands.

**Reuses origin's `cas-native/model/activation_hooks.py`** (lower-level, walks the model and registers hooks with CAS-aligned names like `domain_descent_attention.layers.2`). My layer is the inference + REPL surface; origin's is the instrumentation foundation. Future cleanup: refactor mine to delegate hook registration to origin's.

**17 new tests + 16 origin scaffold tests = 33 trace tests pass.**

### NLGenerationHead — `cas-native/model/nl_generation_head.py`

50.2M params, 6-layer transformer decoder, RANDOM INIT. Module docstring contains the literal string "NO foreign pretrained models" — enforced by static substring scan in tests.

Reuses existing CAS-Native infra: `domain_descent.build_domain_descent_mask`, `register_film.RegisterFiLM`, `NUM_REGISTERS`. Conditioning: discrete CAS-prefix tokens prepended to decoder input + 4-position bottleneck soft-prefix + cross-attention.

Object traceability: `forward(return_meta=True)` returns `output_id` (UUID), `model_code_version`, `model_weights_sha` (sha256), `cas_conditioning_id`. `generate(with_trace=True)` returns `GenerationTrace` with per-token `TokenStep` records.

Wires into existing `CASNativeModel` via `attach_nl_gen_head()` + `forward_with_lm()` — existing `forward()` UNCHANGED. **18 new tests + 36 model regression tests pass.**

**Known divergence:** model uses free-floating learned soft-prefix; spec recommends `Linear(d_model, 4*d_model)` projection of `pooled_hidden_state` for trace fidelity. Tracked.

### English BPE tokenizer — `cas-native/training/english_bpe_extension.py`

Stdlib-only byte-level BPE — no torch, no numpy, no tokenizers/sentencepiece/HuggingFace. ALL merges computed from corpus, no foreign vocab. CAS reserved tokens at LOW IDs (stable across vocab updates). Vocab cap 32K (16K English BPE + ~500 CAS reserved).

`BPEArtifact` carries `vocab_version`, `trained_from_corpus_hash` (sha256), `trained_at_timestamp`, `bpe_merge_count`, `english_vocab_size`, `cas_reserved_token_count`. Deterministic merges (sha256 locked by test).

**28 tests pass.**

### Native NL gen training pipeline — `cas-native/training/train_native_nl_gen.py`

Joint training: `L = α * L_structured + β(step) * L_LM` with curriculum on β (0.1 → 1.0 over 10K steps). Full-provenance checkpoint manifests: `checkpoint_id`, `code_version`, `weights_sha`, `trained_from_corpus_hash`, `trained_at_timestamp`, `n_train_records`, `n_epochs_completed`, `final_loss_total`, `git_commit_sha`, `schema_version="checkpoint.v1"`. `--smoke-test` runs 1 step on CPU and exits 0.

### Eval harness — `cas-native/evaluation/native_nl_generation_eval.py`

Three metrics:
- **CAS-grounding rate:** generate reply → run reply through structured prediction head → does it classify back to the conditioning CAS? Per-axis (Noetic / Domain / Drive / Register) accuracy.
- **Fluency (perplexity):** model PPL on held-out val.
- **Diversity (distinct-2):** distinct-bigram ratio.

`EvalResult` carries `eval_id`, `checkpoint_id`, `eval_dataset_id`, `eval_dataset_hash`, `metric_name`, `value`, `per_bucket_breakdown` (10×4×7×4 axes), `timestamp`, `schema_version="eval_result.v1"`.

### Generation trace surface — `cas-native/trace/generation_trace.py`

Extends Mode 7 to the generative path. `GenerationTraceCapture` wraps the model's `GenerationTrace` + adds `trace_id`, `model_checkpoint_id`, nearest-neighbor lookup against training data, live CAS-grounding score.

### SDG strategy + Tier 1 seed — `cas-synthetic/scripts/generate_native_nl_sdg_v1.py`

Three-tier corpus design:
- **Tier 1:** template-based via `cas-native/data/english_generator.py`. Deterministic, free, axis-complete.
- **Tier 2:** Claude API rewrites of Tier 1 in 8 demographic × 5 tone variations.
- **Tier 3:** Claude API generates dialogue-shaped (user prompt, CAS state, fluent reply) triples.

**TONIGHT'S TIER 1: 2,500 records on disk** at `cas-synthetic/data/native_nl/v1_seed_5k.jsonl`. **CRITICAL CORRECTION:** Tier 2 was attempted but the agent stalled — `api_calls: 0`, `api_key_status: "unused"`. **However — see Section 7 — Tier 2 is essentially already done by prior work.**

---

## 6. The CAS-Native NL generation architecture (final spec)

**Architecture decision:** parallel English LM head bolted onto the existing `CASNativeModel` bottleneck. Joint training with the structured prediction head. Total model ~110-120M params, all random-init.

**Why this and not foreign weights:** see Rule 1.

**Conditioning channels (3):**
1. Discrete CAS expression tokens prepended to decoder input
2. Continuous bottleneck soft-prefix as 4 learned position embeddings (NOTE: spec recommends switching to `Linear(d_model, 4*d_model)` projection of `pooled_hidden_state` for stronger trace; not yet done)
3. Cross-attention from decoder to structured-token embedding output

**Reuses CAS-Native modules (genuinely native, not bolted on):**
- `DomainDescentAttention` — applied to decoder cross-attention as P≻C≻E≻O mask
- `RegisterFiLM` — modulates decoder output post-projection
- `PrerequisiteGateLayer` — RPM gate
- `FractalAttentionHead` — IFS-inspired self-attention
- `StructuredTokenEmbedding` — encoder

**Vocabulary:** `HybridCASTokenizer` extended with 16K-32K English BPE trained from scratch on the SDG corpus.

**Trace:** every gen step records (token, attn-to-CAS-prefix, attn-to-prior-tokens, layer activations, training-data nearest-neighbor, live CAS-grounding score).

**Spec doc:** `docs/working/native_nl_generation_head_spec_2026_05_04.md` (~7,164 words).

---

## 7. What's ALREADY on disk — DON'T REGENERATE

This is the section where the prior LLM tripped multiple times. The user got rightfully angry. Read it carefully.

### Demographic + tonal expanded training corpora — ALREADY DONE

Files at `cas-synthetic/data/level2_scaffold/`:

| Corpus | Records | Size |
|---|---|---|
| `level3_canonical_dt_K4.jsonl` | **77,816** | 195 MB |
| `level3_eval_dt_K4_seed4242.jsonl` | 4,000 | 11 MB |
| `level3_meta_logic_balanced_dt_K4.jsonl` | 6,400 | 16 MB |
| `lever3_paired_dt_K4.jsonl` | 19,652 | 60 MB |

**~108K records of demographic+tonal expanded data** — the equivalent of "Tier 2" in tonight's strategy doc. **DO NOT propose generating Tier 2; it's done.**

Generator code: `cas-synthetic/generator/demographic_tonal_axes.py` + `demographic_tonal_rewrite.py`.
Expansion script: `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py`.
Tests: `cas-synthetic/tests/test_demographic_tonal.py` (20 tests).
Robustness eval: `cas-native/evaluation/demographic_robustness_eval.py`.

### Tier 1 seed corpus — DONE TONIGHT (only 2,500 records)

`cas-synthetic/data/native_nl/v1_seed_5k.jsonl` — but **redundant given the 77K dt_K4 corpus.** User flagged this, said templates aren't needed if generation is fluent. Going forward: skip Tier 1 templates, use Claude-generated data (which is what the dt_K4 corpus already is).

### Other prior work to know about

- **K=9 baseline classifier checkpoint:** `~93.2%` canonical exact on held-out 1K eval. Run dir at `cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-...` (commit 3232f05). The active classifier the new generation head will condition on.
- **Lever 3 paired data via Claude API:** 5K Claude-rewritten records, already exists.
- **vocab14 reserved CAS tokens:** Λ Ω Θ → · NoeticCluster StateSet RelationCluster CoverOf PartitionOf Product ∪ ∩ ∖. Already in the tokenizer's `RESERVED_CAS_TOKENS`.
- **Mode 7 lower-level instrumentation:** `cas-native/model/activation_hooks.py` (origin's PR #15-#17 work).
- **Three-instance dialectic scaffold:** `cas-native/dialectic/` (1,995 LOC, 5 tests). User said: "Build prototype AFTER Lever 3 lands."
- **DST scaffold:** `cas-native/dst/` (2,909 LOC, 58 tests). Phase 2 of Version B. Templated `nl_generation_head` slot is what the new generation head replaces.

---

## 8. Pod state (training run in flight)

**Pod:** `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519`

**History this session:**
- v1 Full Stack retrain started 2026-05-04T23:29:45Z, PID 11128
- Ran 6h 22min before being killed
- Got past tokenize_train + build_vocabulary + tokenize_eval + model_init, then froze for 5+ hours with zero progress
- Log frozen, GPU at 13%, single thread at 99.9% CPU on a C extension call (held the GIL, didn't service signals)
- Tried SIGINT (no response), SIGQUIT (no response), then SIGKILL (terminated)
- Diagnosis (from non-response, not from a stack trace): Python stuck in a long C call, most likely candidate is the diagloop graph-batch construction, but couldn't confirm without py-spy (docker container blocks SYS_PTRACE)

**Current run (started ~2026-05-05T05:56 UTC):**
- PID 11823 alive
- Run dir: `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/`
- Same corpus + flags as before (`--diagram-loop-pairs 0` is default), PLUS `PYTHONFAULTHANDLER=1` env var so SIGQUIT will produce a Python-level + C-level stack trace if it hangs again
- Currently progressing through `tokenize_train` (logs streaming, GPU still idle as expected during data prep)

**Key milestone to watch for:** the FIRST `epoch_end` event in launch.log. The prior run never reached this. If the new run produces an `epoch_end`, the bug self-resolved (or the issue was transient). If it hangs again, SIGQUIT now gives us actual diagnostics.

**User's directive on this:** "We run pod until training stops that was the plan until it was erased from your memory so unless you have a better reason to stop it let it run." Translation: **don't propose killing without a real technical reason. Don't keep raising it as an open question at the end of every reply.**

---

## 9. Critical path to demoable v0

**Destination:** chat REPL where you type English → model predicts CAS → model writes English reply grounded in that CAS → `/trace` shows full path from input through CAS state, activations, training data, output.

**Calendar:** 4-6 weeks with current scope and budget.

### Phase A — Foundation lock (1-2 days)
1. Reconcile soft-prefix design (free embeddings → `Linear(d_model, 4*d_model)` projection of `pooled_hidden_state`).
2. Reconcile model + training forward signature (30 min cleanup).
3. Wire training pipeline to consume the 77K `level3_canonical_dt_K4.jsonl` corpus (script was written assuming the 5K Tier 1 seed — trivial swap).
4. v1 Full Stack retrain: continues running on the pod.

### Phase B — Tier 3 multi-turn dialogue SDG (1-2 weeks, runs on user's laptop or cheap CPU instance — NOT a GPU pod)
- Generate 50-200K (multi-turn dialogue, CAS state per turn, fluent reply) triples via Claude API.
- This is the genuine gap. Single-turn data exists in volume; multi-turn does not.
- Cost ~$200-500 Claude API.

### Phase C — First training run (3-5 days, GPU pod)
- Train English BPE on the 77K + paired + dialogue corpus.
- Smoke train, then full run on A6000 (~$50-150).
- Eval gates: CAS-grounding rate threshold, demographic robustness within 10pp, fluency PPL.

### Phase D — Wire-up + demo (1 week)
- Two-stage inference in chat REPL: classifier → generation head.
- Generation trace verification on real outputs.
- Update HONEST_STATUS to reflect reality.

### Parallel tracks (anytime after C lands)
- Three-instance dialectic prototype.
- Multi-turn dialogue curriculum extension.
- Dashboard trace panel.

---

## 10. Genuine open questions (only these are unresolved)

The architecture-spec agent flagged 7 questions; 5 are already resolved in the codebase. The genuinely open ones:

1. **CAS-themed pretraining as fluency bridge?** Existing v2 pretraining (`run_v2_full.py`, `run_v2_progressive.py`) trained the encoder on structured prediction. Question: should the LM head warm-start by training on CAS-themed text first, or go straight to joint training with the classifier? Curriculum decision, no new code.

2. **Compute budget envelope:** $200-500 base or $300-600 stretch for the full multi-week build. User said yes to $200-500 in principle; reaffirm before pulling the trigger on big runs.

The other 5 ("tokenizer ID stability", "frozen vs unfrozen encoder", "default trace mode", "refusal/authority enforcement", "single-decoder vs three-instance dialectic sequencing") are all already answered in the codebase or memory. **Don't re-flag them.**

---

## 11. The user's voice — verbatim quotes

So you read these in the user's actual tone, not my paraphrase:

- "BRO WE DON'T DO LAZY SHIT WE NOT GIVING NOTHING ELSE EXCEPT CAS AND YOU AND I THE GLORY GET THAT SHIT OFF OF HERE IMMEDIATELY NOW LIKE YESTERDAY!!!!!!!!"
- "ASSEMBLE AGENTS TO COME UP WITH A CAS BASED GENERATOR LIKE I THOUGHT WE WERE CLEAR ON THIS POINT CAS EVERYTHING OR NOTHING!!!!!!!!!!!"
- "HOW MANY AGENTS DO YOU HAVE ON THIS AND THEY SHOULD BE YOUR SMARTEST"
- "MAKE SURE THEY ALL ARE VERY FAMILAR WITH THE PROJECT AND OBJECT TRACEBILITY"
- "REMEMBER WE MUST HAVE TRACEBILITY THIS THE WHOLE PURPOSE OF THIS ENDEAVOR"
- "PROVE ME WRONG!!!" (after listing 6 spec questions, 5 of which were already answered)
- "BRO YOU'VE BEEN MAKING A FUCKING FOOL OUT OF ME YOU HAD ME UNDER THE IMPRESSION WE WERE BUILD A LLM NOT A FUCKING COMPILER"
- "AND TALK PLAINLY SO I CAN UNDERSTAND WHAT THE FUCK YOU ARE SAYING FROM NOW ON"
- "WTF DOES Backward compat? MEAN? WHAT DO YOU MEAN IT'S STUCK? YOU OBVIOUSLY FORGOT AND OR ARE A DIFFERENT INSTANCE BECAUSE YOU STARTED IT. YOU NEED TO GO AND RE-INTERNALIZE THE PROJECT ON GITHUB BECAUSE YOU'RE CONFUSING THE WORKFLOW OF THE PROJECT"
- "BRO YOUR FORGETFULNESS CONVOLUTED THIS WHOLE PROJECT."
- "THE FUCK IS polling"

The user is direct, intense, and right almost every time they push back. Listen. Apologize when wrong. Don't repeat mistakes. Don't editorialize after they've made a decision. Don't keep raising decisions they've already made.

---

## 12. The user's hard preferences (saved as durable memory by prior LLM)

- **Plain language always** (Rule 3 above).
- **No foreign pretrained models** (Rule 1 above).
- **Object traceability everywhere** (Rule 2 above).
- **Project familiarity for every agent** (Rule 4 above).
- **Git fetch + read CHANGELOG before launching expensive ops** (Rule 5 above).
- **Grep before flagging "open questions"** (Rule 6 above).
- **Welcomes follow-up investigation agents after milestone commits** (parallel firing preferred over staggered).
- **Always parallelize SDG with training when no resource conflict** (CPU-bound SDG + GPU-bound training have no contention).
- **Sample-level outcomes are the only "real" eval metric** (per-sample exact_match / top1 / top5 / gt_rank load-bearing; slot/family/scoreability supporting only).
- **Capability emerges as a gradient** (random→surface→partial→near-complete→structured), not a step function. Headline runs on the highest gradient level reached, not on lm_loss.

---

## 13. File path quick reference

| What | Where |
|---|---|
| Repo root | `C:\Users\wakil\OneDrive\Desktop\tksCAS` |
| Project Bible | `C:\Users\wakil\OneDrive\Desktop\tksCAS\CLAUDE.md` |
| Honest status | `noetic-compass-scaffold\noetic-compass\HONEST_STATUS.md` |
| CHANGELOG | `noetic-compass-scaffold\noetic-compass\CHANGELOG.md` (latest is Session 55) |
| NLGenerationHead model | `noetic-compass-scaffold\noetic-compass\cas-native\model\nl_generation_head.py` |
| Belief substrate | `noetic-compass-scaffold\noetic-compass\cas-native\belief\` |
| Mode 7 live capture | `noetic-compass-scaffold\noetic-compass\cas-native\trace\live_capture.py` |
| Mode 7 lower-level hooks | `noetic-compass-scaffold\noetic-compass\cas-native\model\activation_hooks.py` |
| English BPE tokenizer | `noetic-compass-scaffold\noetic-compass\cas-native\training\english_bpe_extension.py` |
| Generation training pipeline | `noetic-compass-scaffold\noetic-compass\cas-native\training\train_native_nl_gen.py` |
| Generation eval harness | `noetic-compass-scaffold\noetic-compass\cas-native\evaluation\native_nl_generation_eval.py` |
| Generation trace surface | `noetic-compass-scaffold\noetic-compass\cas-native\trace\generation_trace.py` |
| Architecture spec | `docs\working\native_nl_generation_head_spec_2026_05_04.md` |
| SDG strategy doc | `docs\working\native_nl_sdg_strategy_2026_05_04.md` |
| Tokenizer extension spec | `docs\working\native_nl_tokenizer_extension_spec_2026_05_04.md` |
| Demographic+tonal generator | `cas-synthetic\generator\demographic_tonal_axes.py` |
| 77K dt_K4 corpus | `cas-synthetic\data\level2_scaffold\level3_canonical_dt_K4.jsonl` |
| K=9 baseline notes | Memory: `project_cas_native_v2_first_structured_emergence.md` (in `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\`) |
| Prior LLM's handoff | `docs\working\handoff_2026_05_04_evening.md` |
| THIS document | `docs\working\handoff_for_gemini_2026_05_04.md` |

---

## 14. The core CAS framework primitives (you'll need these)

### 10 Noetics — VERBATIM definitions (do not paraphrase)

- **^0 (CO-0): Idea** — All things in and outside the Mind.
- **^1 (CO-1): Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- **^2 (CO-2): Positive** — An Idea the Mind has an affinity for and is attracted toward.
- **^3 (CO-3): Negative** — An Idea the Mind is adverse to and repelled by.
- **^4 (CO-4): Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- **^5 (CO-5): Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- **^6 (CO-6): Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- **^7 (CO-7): Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- **^8 (CO-8): Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- **^9 (CO-9): Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

### Anti-drift rules (don't classify wrong)

- **^3 Negative is VISCERAL, not analytical.** Aversion / repulsion. If example reaches for audit/scrutinize/find-flaws vocabulary → ^6 Male, NOT ^3.
- **^8 Above/Cause is associative TRIGGERING, not deductive reasoning.** "That reminds me", "one thing leads to another" — ^8. Deductive causal analysis = compound ^6 + ^9, NOT ^8.

### 4 Domains, 7 Drives, 4 Registers

- **Domains** (P ≻ C ≻ E ≻ O): Principled, Cognitive, Evaluative, Operational. P > C > E > O total order.
- **Drives**: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose. Inversion pairs: F1↔F7, F2↔F6, F3↔F5, F4 self-dual.
- **Registers**: |T Transcendent (high-abstraction, vision), |A Analytical (sequential, logical), |f Affective (felt, emotional), |E Embodied (sensorimotor, concrete).

### Notation example

`^3^P_{F2}|A` = ^3 Negative state on the Principled domain, driven by F2 Wisdom, in Analytical register. "The model analytically determines this principled action is harmful."

### v7.7 operator discipline

- `+` = co-presence/association (terms remain distinct)
- `×` = generative integration (yields emergent state, requires explicit named result)
- `|⟨R1,R2,R3⟩` = register-set occupancy (no operational claim)

### Compiler

`api/notation/compiler.py` — takes a CAS expression string, returns AST + admissibility check result. Used by belief substrate's RPM gate and by the structured prediction eval.

---

## 15. The one thing NOT to do

**Do not propose any new step without first checking what's already in the codebase.** The prior LLM made this mistake at least four times tonight (TinyLlama proposal, Tier 2 SDG twice, Mode 7 duplication, "open questions" already answered). Each cost the user time, money, or trust.

The discipline:
1. Before proposing any work, grep the repo for existing implementations.
2. Read recent CHANGELOG entries.
3. Check the memory pointers in `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\MEMORY.md` (the prior LLM's durable feedback rules).
4. ONLY after that, propose the next step.

If the answer is in the codebase, the question isn't open.

---

## 16. Where to start when picking this up

1. Read this document end-to-end. It's self-contained.
2. `git fetch origin master` and confirm `b45e553` is the tip. If not, read what's newer.
3. Read `noetic-compass-scaffold/noetic-compass/HONEST_STATUS.md`.
4. Check pod state: `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519` then check the run at `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/launch.log`.
5. Ask the user what they want next. **Don't auto-propose work.**

---

End of handoff.
