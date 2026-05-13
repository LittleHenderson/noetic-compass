# Stage 4 — Minimal NL Front Door Training Spec (2026-05-13)

**Status:** DRAFT v1 — spec only. NOT a training launch. Codex audit + user "go" required before any pod work.

**Owner trail:** Step 5B Part 1 (heuristic NL→CAS bridge `nl_to_cas_v0.py`) shipped at commit `8e8d843` 2026-05-13. AUTHORIZED entry `decisions.md` 2026-05-13T18:25Z, Part 2: "Stage 4 training spec (DOC ONLY)." This is that doc.

**Companion docs:**
- `docs/working/agent_exchange/decisions.md` 2026-05-13T18:25Z — Step 5B authorization scope.
- Memory `feedback_cas_native_data_strategy_2026_05_13.md` — data hierarchy (own → synthetic → HF for style only; no foreign-model distillation).
- Memory `feedback_no_foreign_architecture_cas_only.md` — no foreign pretrained models in production stack.
- `docs/working/mode_7_traceability_design_2026_05_13.md` — trace consumer; Stage 4 outputs must populate this surface.

**Glossary:**
- *Stage 3* — the checkpoint shipped in `/workspace/tksCAS/stage_e3_20260513T043823Z/`. CAS-grounded English generation with one-step scheduled-sampling training. Free-decode identifier recovery 0.78 dev / 0.64 held-out. Cross-emission count = 0.
- *NL Front Door* — the surface that turns English the user types into a CAS expression the model can explain. Stage 3 explains a CAS expression; Stage 4 generates one from English.
- *Heuristic bridge* — `nl_to_cas_v0.py`, the ~15-pattern rule-based v0 surface (Step 5B Part 1). Deterministic. Never fabricates.
- *Trained bridge* — Stage 4 model. Generalizes beyond the curated patterns.
- *Gold supervision* — pair `(english_prompt, canonical_CAS_expression)` where the CAS side is verified compilable.

## 1. Goal

Train a minimal NL→CAS generation head that lets the user type free English and get a canonical CAS expression back. The CAS expression then routes through the existing Stage 3 cas-explain pipeline so Plain Mode + Layered self-explainer + Traceability v0 trace all attach normally.

The success bar is "user can type 20-30 different English phrasings of common CAS concepts and the bridge produces compilable CAS that explains correctly." Not "general open chat." Not "full conversational model." This is the **constrained NL surface** for the demo, sitting in front of the proven Stage 3 explanation pipeline.

The heuristic bridge (Step 5B Part 1) stays in production after Stage 4 lands — deterministic fast-path for known patterns, with the trained model serving novel phrasings.

## 2. Scope — what's IN, what's OUT

**IN scope:**
- 4 curriculum tasks (§4): `english_to_cas`, `simple_chain_construction`, `symbol_query`, `depth_request_routing`.
- Curated 5K–25K corpus per memo `feedback_cas_native_data_strategy_2026_05_13.md`.
- Compiler-validated gold CAS on every training pair.
- Trace-aware training (Stage 4 outputs must populate `traceability_v0` schema fields).
- Stage 3 checkpoint as the explanation tail (Stage 4 does NOT regenerate the CAS explanation; it routes inferred CAS into Stage 3).

**OUT of scope:**
- General free-form chat / open-domain Q&A.
- Foreign-model distillation as a corpus source. Per memory `feedback_no_foreign_architecture_cas_only.md`. CAS-grounded data only.
- Conversational dialogue trees (multi-turn beyond what Stage 3 REPL already supports).
- Mode 7 visualization UI (separate track).
- Living Thought Atlas presentation layer (separate track).
- New model architecture. Stage 4 reuses the simplex-MVP encoder/decoder backbone; only training data + objective change.

## 3. Data strategy — sources, hierarchy, hard rules

Per `feedback_cas_native_data_strategy_2026_05_13.md`. Tier order matters: lower tiers fill gaps the higher tiers can't fill.

### Tier 1 — Own CAS data (compiler-validated)

Source: existing `cas-synthetic/` corpora. Specifically:
- `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` (eval-only — DO NOT train on this).
- `cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260508T203848Z.jsonl` (+ `..._20260509T002355Z.jsonl` + `..._20260509T002541Z.jsonl`, 5,268 SFE-certified records total per memory `project_path_d_wave_2_5_promoted_2026_05_08.md`).
- Sibling validator-clean file: `cas-synthetic/data/path_d/wave3_step2_5_clean_current_validators_20260508T110453Z.jsonl` (346 records). Use as a verification subset before pulling the full SFE corpus.
- `cas-synthetic/data/native_nl/v1_dialogue_*` corpora — sample-read for fluent-Q&A pairs, filter heavily. Memory `feedback_audit_corpus_before_proposing_reuse.md` warns these reply with "the precise notation is...", not casual English; strict filter accepted 0 of 24,565 last audit.

Hard rules:
- Every (english, CAS) pair must compile via `api/notation/compiler.py`. Compiler is authoritative grammar.
- Reject any pair where the English side says "the precise notation is" / "in CAS this becomes" / other meta-explanatory framing. We want English that asks for a CAS expression, not English that explains one.
- Sample-read 20-30 records before promoting any tier-1 source. Memory `feedback_audit_corpus_before_proposing_reuse.md`.

### Tier 2 — Compiler-synthetic (heuristic-bridge-as-gold)

Source: programmatic generation seeded by the heuristic bridge pattern table.

Approach:
1. Take each entry in `_NL_PATTERNS` (Step 5B Part 1, `nl_to_cas_v0.py`).
2. For each pattern, generate 50-200 phrase variants via a paraphrase grammar (rule-based; no foreign LLM). Variants cover: word reorderings, synonym swaps within CAS vocab (e.g., "anger" / "rage" / "fury" all → `^3^E|f`), question forms ("how would you express anger in CAS?"), declarative forms ("anger maps to..."), imperative ("show me anger").
3. Gold CAS = the heuristic bridge's mapping. Compiler-validated automatically (the bridge's mappings are pre-validated).
4. Reject any variant the heuristic bridge then matches in reverse — keeps Stage 4 generalizing beyond the bridge's exact regexes.

Target: 3K-15K records this tier. Cheap to generate. No external dependencies.

### Tier 3 — HF/Kaggle for style only (NOT for CAS content)

Per memo: HF/Kaggle dialogue corpora are permitted as STYLE PRIORS — i.e., the NL side may be lightly reformulated to match natural English question forms — but the CAS side must never come from a foreign source.

Hard rules:
- No CAS expression in any training record derived from foreign-model output. Period. Memory `feedback_no_foreign_architecture_cas_only.md`.
- License: Apache / MIT / BSD / CC0 preferred. CC-BY-SA flagged for IP review before any commercial release. No GPL.
- Sample-read 5-10 records per candidate. Memory `feedback_audit_corpus_before_proposing_reuse.md`.

Use cases:
- Tone calibration: do users phrase questions casually ("what's anger in CAS?") or formally ("please express anger as a CAS expression")? Tier 3 informs the paraphrase grammar in tier 2.
- Out-of-domain rejection priors: examples of English that should NOT map to a CAS expression. Trains the model's "I don't know" pathway.

Target: 1K-5K records this tier, used as priors only. Not core supervision.

### Total corpus budget

5K (minimum viable) to 25K (rich). Memory `feedback_cas_native_underfit_over_overfit_short_epochs.md` warns against overfit — start at the low end of the band, gate-test, then expand if and only if eval shows generalization headroom.

## 4. Curriculum — 4 task heads

Each task is a separate `(input_format, output_format, loss_weight)` triple. All four share the simplex encoder/decoder backbone.

### Task 1 — `english_to_cas` (PRIMARY, ~60% of training data)

Input: English question / statement / request describing a CAS concept.
Output: Canonical CAS expression.

Example: `"explain a thought becoming action"` → `"^9^O"`.

Gold supervision:
- Heuristic bridge entries (~15 base patterns × ~100 variants = ~1500 anchor pairs).
- Tier-1 SFE-gated cas_to_english pairs (inverted — English becomes input, CAS becomes target).
- Tier-2 synthetic variants.

Loss: cross-entropy on the CAS expression tokens, with copy-supervision losses (L_span, L_contrastive_margin, L_coverage from E2b) when the English side names identifiers that appear in the gold CAS.

Eval gate: ≥0.70 free-decode compile-rate on held-out paraphrases of the heuristic bridge anchor set.

### Task 2 — `simple_chain_construction` (~20% of training data)

Input: English that describes a 2- or 3-stage RPM chain.
Output: Canonical chain syntax (`let stageA0_X = ...; let stageD3_Y = ...; stageA0_X -> stageD3_Y`).

Example: `"show me a simple CAS example"` → the canonical 2-stage RPM chain.

Gold supervision: programmatically generated chains from the seed CAS enumerator + paraphrase grammar over the English side.

Loss: cross-entropy with the existing E2c per-span start-anchor losses.

Eval gate: ≥0.60 free-decode compile-rate on held-out chain prompts.

### Task 3 — `symbol_query` (~15% of training data)

Input: English question of the form "what does `<symbol>` mean?" or "explain `^7`" or "what's `|f`?".
Output: Routes to the self-explainer symbol-legend topic (NOT a CAS expression — routing target). The model emits a short routing token sequence the REPL consumes.

Gold supervision: enumerate every symbol in CAS surface (states, drives, registers, operators, recipe markers, meta-logic constructors, Cognitive Fractal `⟨…⟩` sequences) — memory `feedback_cas_token_enum_must_include_metalogic_and_fractals.md`. Pair each with question phrasings.

Loss: cross-entropy on routing tokens.

Eval gate: ≥0.90 correct routing token on held-out symbol queries (high bar because the answer space is small and discrete).

### Task 4 — `depth_request_routing` (~5% of training data)

Input: English signal that the user wants a different depth ("go deeper," "explain that simpler," "give me the technical version").
Output: Routing token for the self-explainer level (`simple` / `stakeholder` / `user` / `builder` / `technical`) + a `deeper` or `simpler` direction signal.

Gold supervision: enumerate depth-signal phrasings.

Loss: cross-entropy on routing tokens.

Eval gate: ≥0.85 correct routing decision on held-out depth signals.

## 5. Architecture

Reuse simplex-MVP encoder/decoder backbone. NO architectural changes for Stage 4. Per `feedback_no_foreign_architecture_cas_only.md`.

Specific reuse:
- Encoder: `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py::build_simplex_mvp_model`.
- Decoder: same. Same `cas_prefix_mask` from v1 architectural milestone (memory `project_v1_architectural_milestone_2026_05_09.md`).
- Loss family: existing E2b/E2c losses (L_span, L_contrastive_margin, L_coverage, L_start_anchor, L_anchor_contrastive). Scheduled-sampling training (E3 path) for the generation head.

Task head differentiation:
- Task 1 (`english_to_cas`) and Task 2 (`simple_chain_construction`) use the existing CAS expression generation head.
- Task 3 (`symbol_query`) and Task 4 (`depth_request_routing`) use NEW lightweight routing heads (single linear layer on the decoder's first non-prefix position; output dim = small routing vocab).

Routing vocab size: <100 tokens. The routing heads are cheap and isolated.

## 6. Trace integration (Stage 4 outputs must populate Traceability v0)

Per `mode_7_traceability_design_2026_05_13.md` and the Step 5B AUTHORIZED entry (Living Thought Atlas framing line). Every Stage 4 output must produce:
- `input` section: English prompt + tokenization.
- `output` section: inferred CAS expression + emitted tokens.
- `copy` section: which CAS surface tokens the English side licensed (e.g., "anger" → `^3^E|f` licenses `^3`, `^E`, `|f`).
- `slot_trace`: normal slot structure for any chains generated.
- `confidence`: bands (low / medium / high) with caveats. Low confidence when no heuristic bridge pattern matches AND the model's top-1 logit margin is small.
- `thought_tree`: node-edge JSON consumable by the Living Thought Atlas UI.

The trace surface is non-optional. Memory `feedback_traceability_is_the_whole_purpose.md` is load-bearing.

## 7. Training compute estimate

Per memo `feedback_cas_native_data_strategy_2026_05_13.md` and memory `feedback_gpu_vs_cpu_for_real_training_runs.md`. Buckets are **separated** so planning doesn't conflate small-model pod cost with multi-sweep program cost.

### Bucket A — Current small-model Stage 4 v0 pod training

This is the realistic v0 demo cost — one training run at the current ~150M simplex-MVP scale, single sweep, no extensive hyperparameter search.

- Pod: RunPod A100 80GB.
- Steps: 5K records × 3 epochs × batch 128 ≈ 120 steps. 25K records × 3 epochs × batch 128 ≈ 600 steps.
- Wall-time: ~30 min (5K) to ~4 hours (25K). Memory `feedback_cas_native_underfit_over_overfit_short_epochs.md` — 2-3 epochs default, sample-read every epoch.
- GPU rate: A100 80GB ≈ $2/hr on RunPod.
- **Pod cost: ~$1-15 for a single Stage 4 v0 training run.**
- Memory `feedback_canary_cost_dominates_short_runs.md` — set canary cadence to final-step only for short runs.

### Bucket B — Corpus engineering (CPU + paraphrase grammar build + sample-read audits)

This is the labor cost of building Tier 1+2 corpus before training. No model training here.

- Paraphrase-grammar build: ~2-5 days laptop wall-time. CPU.
- Compile-validation pass: ~hours of compiler-time. Free.
- Human sample-read audits per memory `feedback_audit_corpus_before_proposing_reuse.md`: ~10-20 hours of user review across audit gates.
- **Bucket B cost: $0 in cloud spend. Wall-time-bound, not money-bound.**

### Bucket C — Optional Tier 3 ingestion (HF/Kaggle style priors)

This is the cost of ingesting Tier 3 dialogue corpora for English-side style priors only. CAS supervision still comes from Tier 1+2.

- License review: pre-flight, free.
- Ingestion + sample-read filtering: ~1-2 days laptop wall-time + ~$100-500 in API spend if Claude/programmatic filtering is used for triage.
- **Bucket C cost: $0-500. Skip entirely if Tier 1+2 alone clears the gates.**

### Bucket D — Multi-sweep release-quality program (NOT v0)

This is the cost of an ablated, peer-reviewable Stage 4 release with multiple hyperparameter sweeps and held-out audits across corpus sizes. This is NOT Stage 4 v0.

- ~5-10 sweeps × ~$5-15 per sweep ≈ $25-150 in pod time.
- Optional Mode 7 visualization tests, Atlas integration tests: extra ~$50-200.
- Memory `feedback_back_up_successful_runs_imperative.md` — backup archive overhead is bytes, free.
- **Bucket D cost: $75-500 if the program is run on the current small-model scale.**

### Bucket E — Future large-model scaling (300M / 1B / larger)

This is the cost band the original AUTHORIZED entry's "$5-25K" referred to: scaling Stage 4's recipe to a future larger CAS-Native backbone. NOT in scope for Stage 4 v0. Captured here so the v0 planning numbers don't contaminate the large-model planning numbers.

- Scale 300M-1B params: ~$500-5K per training run on A100 cluster.
- Multi-run ablation + Atlas-quality demo: ~$5-25K.
- **Bucket E cost: $5-25K. Treat as a separate AUTHORIZED entry, gated on Stage 4 v0 success + large-model architecture decision.**

### Honest summary

**Stage 4 v0 (Buckets A + B + optional C) — total realistic cost band: $1-500.** Almost all of that is Tier 3 ingestion API spend, which is optional. Pure Tier 1+2 v0 training is single-digit dollars.

Buckets D and E are deliberately separated so the v0 plan isn't inflated by large-model or multi-sweep numbers.

## 8. Gate criteria for Stage 4 promotion

Per memory `feedback_separate_evidence_levels_in_status.md` — don't conflate "wired" with "passes gates." All four must be true to promote Stage 4 to production:

### Gate 1 — Compile rate (mechanical)

≥0.70 of free-decode outputs on held-out english_to_cas paraphrases compile via `api/notation/compiler.py`. NO partial credit.

### Gate 2 — Round-trip preservation (CAS grounding)

Generate CAS from English → explain CAS via Stage 3 → recover original concept via the heuristic bridge or the K=9 classifier (`inference/predict_cas.py`). ≥0.80 round-trip on held-out anchor set. Memory `feedback_cas_native_5_layer_eval.md` — round-trip is the CAS grounding eval layer.

### Gate 3 — Trace coverage (Traceability v0)

100% of Stage 4 outputs populate all 7 Traceability v0 sections. Schema-validated automatically. Memory `feedback_traceability_is_the_whole_purpose.md`.

### Gate 4 — Human sample read (the deciding gate)

User reads 30-50 free-decode samples from Stage 4 + Stage 3 pipeline end-to-end. PASS = "this feels like a CAS expert clarifying my prose," not "this is a polite chatbot that name-drops CAS." Memory `feedback_samples_are_the_only_true_eval_for_cas_native.md` is the deciding standard.

A model that passes gates 1-3 but fails gate 4 does NOT ship. Memory `feedback_audit_only_after_automated_checks.md` — automated checks first, human read decides.

## 9. What this doc is NOT

- NOT a training launch. Per AUTHORIZED entry "DOC ONLY." A new AUTHORIZED entry is required before any Stage 4 pod work.
- NOT a corpus engineering green-light. Tier 2 paraphrase grammar + Tier 3 license review + sample-read audits all gate corpus assembly.
- NOT a replacement for the heuristic bridge. The heuristic stays in production as a deterministic fast-path.
- NOT a foreign-model-distillation plan. No Claude / GPT / Gemini outputs as CAS supervision. Style priors only, on the English side, with sample-read audits.

## 10. Next steps (after this doc lands)

1. Codex audit this spec. Block on any data-strategy concerns.
2. User "go" on the spec.
3. Open a NEW AUTHORIZED entry for "Stage 4 corpus engineering" (Tier 1 audits + Tier 2 paraphrase grammar build + Tier 3 license review).
4. After corpus gate passes: open ANOTHER AUTHORIZED entry for "Stage 4 training launch" with the locked pod commands.
5. After Stage 4 promotes: integrate the trained bridge alongside the heuristic bridge in `stage3_chat_repl.py` (heuristic first as fast-path; trained bridge as fallback).

---

**Verification — this spec:**

- Codex audits `8e0ae2d`, `8997125`, AUTHORIZED entry `decisions.md` 2026-05-13T18:25Z Part 2 scope satisfied.
- All cross-references to memories validated against actual memory files at time of writing.
- Corpus paths cited exist (`cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl`, `cas-synthetic/data/path_d/wave_2_5/`).
- Heuristic bridge module path exists (`noetic-compass-scaffold/noetic-compass/cas-native/inference/nl_to_cas_v0.py`, commit `8e8d843`).
- No foreign-model-distillation paths in any tier (per `feedback_no_foreign_architecture_cas_only.md`).
- Trace integration §6 references the actual `traceability_v0` schema fields shipped 2026-05-13.
