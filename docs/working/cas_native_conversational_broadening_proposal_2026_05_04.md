# CAS-Native Conversational Broadening — Three (Plus One) Lever Proposal

**Author:** Research agent
**Date:** 2026-05-04
**Scope:** 1–2 week levers to broaden the K=9 baseline's conversational reach without waiting for Version B Phase 1–6.
**Checkpoint under analysis:** `noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/` (commit 3232f05, 86.8% all-heads-exact, 93.2% canonical-exact, 20 epochs, 66,280 train rows, vocab=293, d_model=128, bottleneck=64).

---

## 1. Executive Summary

- **Recommended first move:** Lever 3 (Claude-rewritten paraphrase fine-tune). It is the only option that buys real free-form English coverage in under a week, costs ~$30 in API + ~$15 in RunPod, and *does not perturb the K=9 vocab/architecture* — it is a continued-fine-tune over the same head, same vocab, same loss.
- **Lever 1 (template paraphrase expansion in `cas-synthetic`)** is structurally clean but does not actually solve the modality mismatch — it generates more *templated* prompts, not free-form English. It is the right move for Version B Phase 1, not for the demo bridge.
- **Lever 2 (two-stage retrieval shim)** is a real product option but hides the K=9 model behind a retriever. It is the most defensible against catastrophic regression, but it is a *demo trick*, not a capability gain. Useful as the safety net under Lever 3.

---

## 2. The Current Bottleneck

The K=9 baseline reaches 93.2% canonical-exact and 86.8% all-heads-exact on the held-out 1K eval, but the eval surface and the training surface are nearly the same distribution. Inspection of `cas-synthetic/templates/level3_conversational_templates.yaml` lines 6–11 and `paraphrase_templates.py` lines 24–47 confirms that **every prompt in the 19,454-record training corpus and the 1,000-record eval embeds a `families:` slot block followed by an explicit Noetic/domain/drive/register listing**. The training-time augmentation (`paraphrase_augmentation.py`) just rewrites the wrapper *around* that slot block — the slot block itself is verbatim. The model has never seen a prompt without it. When `predict_cas.py` is called with `"I can't stand it when people interrupt me"`, the input distribution is alien and the model collapses to its largest prior, `expression_family=meta_logic` (cf. `predict_cas.py:268-279` __main__ examples).

The current rule-based remediation (`rewrite_shim.py`, 393 lines) is a heuristic rewriter from colloquial English into the training-surface template. It works well on the 21 curated `demo_prompts.py` cases because those were *picked* to satisfy the colloquialism map. It fails silently on anything outside that map, returning the original text and letting the model collapse. The shim is a v0 bridge, not a solution. The deeper question is whether to **(a)** expand training distribution toward free-form English (Levers 1, 3, 4), **(b)** project free-form English into the existing training distribution at inference (Lever 2), or **(c)** accept the shim's coverage and stay narrow until Version B ships.

---

## 3. Levers

### Lever 1 — Paraphrase corpus expansion via existing SDG

**Description.** Extend `cas-synthetic/generator/conversational.py` and `level3_conversational_templates.yaml` with 5–10 *non-recoverable* template families: paraphrase styles that strip the `families:` slot block and write the prompt as a colloquial first-person utterance (e.g. *"That song hit me hard"*, *"I keep practicing the same scale"*). Generate 5–10K new records, mix into the K=9 training set, retrain.

**Data work.** Add a new style block (`colloquial_first_person`) to the YAML. Each Noetic gets 6–10 colloquial templates drawn from the canonical colloquialism map (`CLAUDE.md` Anti-drift section). Domain/drive/register chosen by the existing template logic with `formal_axis_reading` removed from the prompt but kept in `natural_language_mapping`. Estimated 1.5 days to author + validate templates and 0.5 day to regenerate ~7K records via `scripts/generate_level3_conversations.py`. Output: `level3_recoverable_full_with_colloquial_v0.jsonl` (~26K rows total).

**Training work.** Single retraining run on RunPod A40 / RTX 4090, 20 epochs, batch=128, lr=1e-3, vocab regenerated (will likely grow from 293 to ~600–900 tokens because colloquial text introduces unseen lexicon items). Wall-clock: K=9 baseline took ~1.5 hr on GPU for 66K rows × 20 epochs; this is ~88K rows × 20 epochs ≈ 2 hr GPU + ~30 min eval = 2.5 hr.

**Expected lift.** Modest. The model will recognize the canonical colloquialisms (because they map cleanly to single Noetics) but will not generalize to *novel* free-form English. This is essentially "memorize the colloquialism map at training time." Free-form coverage probably moves from ~5% to ~25–35% on a held-out colloquial eval.

**Risk.** Vocab regeneration changes the embedding table, so this is *not* a continued fine-tune — it is a fresh run. Risk that overall canonical-exact drops from 93.2% (the colloquial records dilute the slot-block prior). Memory item `feedback_eval_file_slip_recurrent.md` flags that mixing eval files is a recurring failure mode; if the new training set leaks colloquial samples into the held-out eval, results will look better than they are. Speculative: lift on truly out-of-distribution English may be near-zero if the templates are too narrow.

**Total time:** 4–5 days (2d data, 0.5d train, 1d eval + report, 0.5d slack).

---

### Lever 2 — Two-stage NL-encoder retrieval shim

**Description.** Train (or use off-the-shelf) `sentence-transformers/all-MiniLM-L6-v2` to embed the user's free-form English. Build an index over the 19,454 training-surface prompts in `level3_recoverable_full.jsonl`. At inference, retrieve top-1 nearest training prompt, feed *that* (not the user's text) to the K=9 baseline. The inference output is the K=9 prediction; `cas_renderer.py` converts to NL.

**Data work.** Construct a `(free_form_english → training_surface_prompt)` pair set. Two paths: **(a)** programmatic — for each of the 19,454 records, generate 1–2 free-form colloquial paraphrases with Claude API (~30K Claude calls, ~$15–20 in API cost, ~6 hr wall-clock); **(b)** retrieval-only — skip the encoder fine-tune, use the off-the-shelf MiniLM and rely on raw cosine similarity over the existing training prompts. Path (b) is 0 data-side work but probably retrieves the wrong record because the training prompts are dominated by the `families:` slot frame — colloquial English will land near random neighbors.

**Training work.** Path (a): fine-tune MiniLM on the 30K paraphrase-pair set with InfoNCE for 3 epochs on a single GPU, ~30 min. Index build with FAISS / NumPy: 5 min. Total GPU: ~1 hr.

**Expected lift.** Moderate-to-high *on the demo*, low on out-of-distribution. If a user's input is structurally close to one of the 19K training items, retrieval will find it and the K=9 head will fire correctly. If not (recipe expressions, novel omega binds, multi-turn), retrieval will degrade silently.

**Risk.** This is a **retrieval system, not a CAS-Native model**. It works by faking generalization: every output is the prediction for *some training row*. It cannot produce CAS expressions outside the 19,454 ground-truth set. For a public demo it is a defensible bridge ("the model retrieves a structurally analogous case and reports its CAS reading"); for a research demo it is a tell. Memory item `project_cas_transformer_modality_mismatch_pivot.md` already warned against backbone-as-prompt-encoder; this is the opposite direction (encoder feeds raw-text retrieval, not the model), but the user should know this is a *band-aid*, not a step on the Version B path.

**Total time:** 3–4 days (1.5d data + Claude API, 0.5d train, 1d eval/index/wire, 0.5d slack).

---

### Lever 3 — Continued fine-tune on Claude-rewritten paired data

**Description.** Use Claude API to generate, for each of the 1,000 held-out eval records (or the 19,454 training records), a *paired* free-form-English version of the prompt. The CAS expression and all 12 head targets stay identical; only `user_prompt` is rewritten. Continued-fine-tune the K=9 checkpoint for 3–5 epochs on the hybrid corpus (canonical + Claude-rewritten). Vocab is preserved (Claude rewrites stay in lexicon-friendly tokens, plus some new colloquialism tokens we accept as OOV).

**Data work.** Claude API call per record: input = canonical training prompt + the CAS expression, instruction = "rewrite as natural first-person English, drop the slot listing, preserve the structural meaning". Cost: at $3/M output tokens, ~150 tokens/record × 19,454 records ≈ 3M tokens ≈ $9 + cache discounts. Wall-clock ~3 hr at modest concurrency. Validation: re-run the existing `level3_review_gate.py` on the rewritten records to confirm uniqueness ratios and CAS-in-response invariants. Authorship spot-check: 100 rows by hand against the colloquialism map and anti-drift rules in `CLAUDE.md`.

**Training work.** Continued fine-tune from `best_structured_token_model.pt`. **Critical: vocab must be preserved**, so OOV tokens in Claude rewrites get mapped to `<unk>` rather than triggering vocab regeneration. Hyperparams: 5 epochs, lr=3e-4 (lower than original 1e-3 to avoid catastrophic forgetting), batch=128, weight decay unchanged. Hybrid sampling: 50% canonical training rows, 50% Claude-rewritten — prevents the model from forgetting the slot-block surface. RunPod A40, ~30K rows × 5 epochs ≈ 30 min GPU + 15 min eval. **Memory `feedback_gpu_vs_cpu_for_real_training_runs.md` applies**: this must be a RunPod, not local CPU.

**Expected lift.** This is the option most likely to move the needle on actual free-form English. Expected: free-form coverage 40–55% (held-out colloquial eval), with canonical-exact holding at 90%+ if hybrid sampling is honored. Speculative upside: 60–70% if Claude generates cleanly anti-drift-compliant rewrites (not guaranteed; spot-check is mandatory).

**Risk.** Two real risks. **(1) Catastrophic forgetting**: aggressive fine-tune can wreck the canonical 93.2%. Mitigation: low lr, hybrid sampling, eval-every-epoch with rollback. **(2) Claude-induced label drift**: if Claude's rewrites subtly shift the CAS reading (e.g., turns a `^3` into a `^6` because it sounds analytical), the labels become inconsistent. Mitigation: keep CAS expression frozen, only rewrite the prompt; spot-check 100 by hand; reject any rewrite that would change the colloquialism-test outcome. Memory `feedback_real_metric_is_samples.md` applies — measure on per-sample exact_match, not on internal slot/family metrics, to catch label drift.

**Total time:** 5–7 days (1d Claude-data gen, 1d spot-check + filter, 0.5d train, 1.5d eval (canonical + new free-form set + per-bucket), 1d demo wire-up, 1d slack).

---

### Lever 4 (proposed) — Inference-time grammar-constrained decoder + two-pass shim

**Description.** Speculative but concrete. The K=9 model is a 12-head classifier — there is no "decoder" today, predictions are independent argmaxes per head. Lever 4: at inference, replace the per-head argmax with a *constrained scoring pass*. Step 1, run rewrite_shim.py and the K=9 head as today, get a draft prediction. Step 2, enumerate the top-3 candidates per head, score each *combination* against (a) the CAS compiler at `api/notation/compiler.py` for grammatical validity and (b) admissibility (CLAUDE.md Correction 1) for source/target. Pick the highest-scoring valid combination. This is a beam search over 12 categorical axes, complexity ~3^12 ≈ 530K combinations — well under a second on CPU, but most are pruned early by compiler/admissibility.

**Data work.** None. Pure inference-time. Requires that `api/notation/compiler.py` is importable from the inference path (already is, per memory `cas_grammar_subtleties.md`).

**Training work.** None. Zero retraining. The K=9 head is unchanged; only the decoding is changed.

**Expected lift.** Hard to predict. The constraint will catch the *invalid combinations* that drag down all-heads-exact (the gap between 93.2% canonical-exact and 86.8% all-heads-exact is exactly this — heads are individually ~95–99% but their joint validity is lower). Won't help free-form English coverage at all (still hits the same broken priors); will help quality on the prompts that DO route correctly. Speculative magnitude: +3–5pp all-heads-exact on canonical eval, ~0pp on free-form. Pair with Lever 2 or 3 for compounding effect.

**Risk.** Compiler grammar quirks (`cas_grammar_subtleties.md` memory: `→` is binary not chained; `^N^D ∈ Noetics` compiles but is semantically false) mean some constraint passes will silently accept structurally wrong combinations. Mitigation: run Lever 4 in shadow mode for a week before flipping it on; A/B against the unconstrained head.

**Total time:** 2–3 days (0.5d compiler-import-from-inference, 1d beam decoder, 1d eval + shadow A/B).

---

## 4. Recommendation: Fire Lever 3 First

**Reason 1 — fastest path to demo-grade free-form coverage.** Lever 1 retrains from scratch with vocab regen (all-or-nothing); Lever 2 is a retrieval band-aid; Lever 4 doesn't move the modality mismatch needle. Lever 3 is the only option that *grows the model's training distribution into free-form English while preserving the existing K=9 architecture and weights*.

**Reason 2 — cost is bounded.** ~$10 Claude API + ~$15 RunPod = ~$25 total. Versus Lever 1 (~$30 RunPod, more risky retrain) or Lever 2 (~$15 API + ~$15 RunPod, but ceiling is lower).

**Reason 3 — fail-soft.** If continued fine-tune regresses canonical-exact, we roll back to the K=9 checkpoint. The fine-tuned checkpoint becomes a separate artifact gated by per-bucket regression test, not a force-overwrite.

**Reason 4 — composes with the others.** Lever 3 + Lever 4 on top is a clean compound: train the model to handle free-form English, then beam-decode for joint validity. Lever 2 stays in reserve as the demo safety net if Lever 3 doesn't clear 40% on the free-form eval.

**Pre-flight checklist before kickoff (non-negotiable):**
1. Hold-out a *new* free-form English eval set (~200 prompts, hand-authored from the colloquialism map, no overlap with training corpus). Score the K=9 baseline on it *before* fine-tuning to establish the floor.
2. Confirm vocab preservation path in `train_structured_prediction.py` works (load existing `structured_token_vocab.json`, do not regenerate).
3. Confirm `--limit 100000` is passed (memory `feedback_limit_default_128_trap.md`).
4. Confirm eval file is `level3_recoverable_eval_1000_v77_relabeled.jsonl`, not the unrelabeled twin (memory `feedback_eval_file_slip_recurrent.md`).

**Estimated total time for Lever 3:** 5–7 days end-to-end, with the diagnostic-and-rollout pattern from `feedback_schedule_followup_agents_pattern.md` if pieces can be parallelized to remote agents.

---

## 5. What NOT to Do

**Do not attempt Levers 1 and 3 simultaneously on the same checkpoint.** Lever 1 changes the vocab; Lever 3 requires the vocab frozen. Running both together either destroys the continued-fine-tune contract or silently masks free-form coverage gains as vocab artifacts. If the user wants both, Lever 3 first (preserve K=9 checkpoint as `K9_FF` artifact), then Lever 1 as a separate from-scratch run for Version B Phase 1. Also: do not let any of these proposals smuggle in "while we're at it, let's also retrain the encoder" — every prior modality-mismatch attempt that combined an encoder swap with a head retrain has failed (memory `project_cas_transformer_modality_mismatch_pivot.md`). Single-variable changes only.

---

## 6. Stale Assumptions to Retire

- **"Free-form English coverage will emerge from larger paraphrase template variety."** It hasn't. The K=9 corpus already has 4 eval templates × 8 training templates × 6 conversational styles. Adding more templates inside the `families:` frame changed nothing. The bottleneck is the *frame itself*, not template count. (Refuted by 2026-05-02 K=9 + bare-slot result, memory `project_k9_baretemplate_partial_success_2026_05_02.md`: bare-slot lever has reached its ceiling.)
- **"The rewrite_shim.py rule-based detector is sufficient until Version B."** It is sufficient for the 21 curated `demo_prompts.py` items, not for arbitrary user input. The shim returns the input unchanged when no rule fires (line 364), and the model then collapses to the meta_logic prior. The shim's coverage is upper-bounded by the canonical colloquialism map (~50–80 phrases); real users say things outside that map.
- **"Soft targets give the model room to disambiguate ambiguous English."** Inspection of `level3_recoverable_eval_1000_v77_relabeled.jsonl` line 1 shows soft_operator_targets are nearly one-hot (`0.480952` on the active Noetic, `0.004762` on the others). The "soft" targets are effectively hard labels with a smoothing floor; they do not provide the ambiguity-handling capacity the name suggests.
- **"CAS-CLM-as-prompt-encoder is back on the table for Version B." It is not** (memory `project_cas_transformer_modality_mismatch_pivot.md`). Lever 2's NL encoder is a sentence-transformer / off-the-shelf NL backbone, not a CAS-CLM. Do not relitigate this.
- **"19,454 records is corpus-saturating for the K=9 head."** It is not. Vocab is only 293 tokens. Most of the corpus is template boilerplate; effective unique slot patterns are probably ~3–5K. The model has plenty of headroom for 30K+ rows of new free-form English without overfitting, *provided* hybrid sampling preserves the canonical surface.
- **"Continued fine-tune is risky and should be deferred to Version B."** It is risky on the *whole architecture*; it is low-risk when the change is `lr=3e-4, 5 epochs, hybrid 50/50 sampling, vocab frozen, eval-every-epoch with rollback`. The K=9 checkpoint is not sacred — it is a 200 MB artifact we can roll forward or back at will.

---

*End of proposal. Single decision required: green-light Lever 3 with the pre-flight checklist, or hold for a different framing.*
