# In-flight handoff — 2026-05-05 morning

**Author:** Claude (this LLM)
**For:** the next LLM picking up this project
**Status:** v1 retrain on the pod is at 2h 8min, frozen at `model_init` — same pattern as the prior stuck run that was killed at 6h 22min. Per user directive, NOT killing. Monitoring on 20-30 min cadence. Side work in this doc is read-only preparation while we wait.

---

## 1. Live pod state (last sample 08:04 UTC)

| Field | Value |
|---|---|
| Pod | `ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519` |
| PID | 11823 |
| Run dir | `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/` |
| Started | 2026-05-05T05:56 UTC |
| Elapsed (08:04 UTC) | 2h 8min |
| CPU / MEM | 99.8% / 6.0% on main thread (single-threaded loop) |
| launch.log mtime | **2026-05-05T07:21:15 UTC** (frozen 43 min) |
| Last event | `model_init`, vocab_size 2673 |
| `epoch_end` count | 0 |
| GPU | 520 MiB / 14% util / 77 W (essentially A6000 idle draw) |
| Run dir contents | only `launch.log` — no manifest, no checkpoint, no eval reports |

**Verified read-only:** `train_structured_prediction.py` does NOT call `faulthandler.register(signal.SIGQUIT, ...)` anywhere in the file or in any imported helper under `cas-native/training/`. **SIGQUIT will TERMINATE the process.** Cannot use SIGQUIT for non-destructive diagnostics on this run.

**Why "no progress" doesn't mean "stuck" yet:** the script's inner training loop iterates 8,678 batches per epoch (555,400 records / batch_size 64) and the launch did NOT pass `--eval-every-steps`, so `eval_every_steps` is None. With that flag unset, the script logs nothing between batches; the only signal is the `epoch_end` print at the end of each epoch. The run can be silently training OR genuinely stuck — both look identical until either `epoch_end` appears or the GPU shows sustained high-util compute.

GPU at 14% util / 77W (vs ~250W active draw expected for healthy training) is the strongest signal that this isn't healthy training — but it's not zero either.

## 2. Monitoring rules

- **Cadence:** every 20-30 min.
- **Commands** (read-only, single SSH):
  ```
  ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
    "date -u && \
     ps -p 11823 -o pid,etime,pcpu,pmem,cmd && \
     tail -n 30 /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/launch.log && \
     grep -c epoch_end /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/launch.log; \
     nvidia-smi --query-gpu=memory.used,utilization.gpu,power.draw --format=csv,noheader"
  ```
  Note: chain with `;` not `&&` because `grep -c` returns exit-1 when count is zero, which aborts `&&` chains.

- **Milestones to watch:**
  - First `epoch_end` appears → training is working. Stop side work, summarize run status.
  - 3-4h elapsed with no `epoch_end` → report exact elapsed time, GPU/CPU state, last log line. Do NOT act beyond reporting.

- **Hard rules:** no signals to PID 11823, no kill, no restart without explicit user authorization.

---

## 3. Deliverable 1 — Eval pull commands + result table template

### 3.1 Pull commands (small artifacts ONLY)

When the run completes (or when explicitly authorized), pull this set first. The big `.pt` checkpoint is excluded by default; pull it only when explicitly needed for further inference.

```bash
# Local target dir (create on local laptop, NOT on pod):
mkdir -p ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart

# Run dir small artifacts:
scp -P 15409 -i ~/.ssh/id_ed25519 \
  root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/launch.log \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/

scp -P 15409 -i ~/.ssh/id_ed25519 \
  "root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/manifest.json" \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/

# Eval reports + samples (existence depends on whether eval was run on pod or pulled-and-run locally):
scp -P 15409 -i ~/.ssh/id_ed25519 \
  "root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/honest_eval_*.json" \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/ 2>/dev/null || true

scp -P 15409 -i ~/.ssh/id_ed25519 \
  "root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/honest_eval_*.md" \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/ 2>/dev/null || true

scp -P 15409 -i ~/.ssh/id_ed25519 \
  "root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/demographic_robustness_*.json" \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/ 2>/dev/null || true

scp -P 15409 -i ~/.ssh/id_ed25519 \
  "root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/*samples*.jsonl" \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/ 2>/dev/null || true
```

The big checkpoint (only when needed):
```bash
# DO NOT pull by default. Multi-GB. Only pull if doing local inference / deeper analysis.
scp -P 15409 -i ~/.ssh/id_ed25519 \
  root@104.255.9.187:/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/best_structured_token_model.pt \
  ~/Desktop/tksCAS_pulls/v1_full_stack_2026_05_05_restart/
```

### 3.2 Eval commands (run on pod after training completes, NOT locally)

Per `combined_retrain_runbook_2026_05_04.md`:

```bash
# Honest two-pass eval (canonical + paraphrase-with-self-prior):
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  'cd /workspace/tksCAS && python3 noetic-compass-scaffold/noetic-compass/cas-native/training/evaluate_diagram_loop_honest.py \
    --run-dir noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart \
    --eval-input cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
    --out-dir noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart \
    --prefix honest_eval --variants-per-record 3 --device cuda' 2>&1 | tail -25

# Demographic robustness eval:
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 \
  'cd /workspace/tksCAS && python3 noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py \
    --checkpoint noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/best_structured_token_model.pt \
    --eval-input cas-synthetic/data/level2_scaffold/level3_eval_dt_K4_seed4242.jsonl \
    --tolerance-pp 10 \
    --out-json noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/demographic_robustness_report.json \
    --out-markdown noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1_full_stack_2026_05_05_restart/demographic_robustness_report.md \
    --device cuda' 2>&1 | tail -25
```

CRITICAL: use `level3_recoverable_eval_1000_v77_relabeled.jsonl` (the relabeled file). Do NOT use the un-suffixed `level3_recoverable_eval_1000.jsonl` (per `feedback_eval_file_slip_recurrent.md` — this slip recurs across agents).

### 3.3 Pre-committed pass/fail table template

| Metric | Result | PASS | HALF-PASS | FAIL | Verdict |
|---|---:|---|---|---|---|
| Canonical exact (all heads) | __ % | ≥92% | 88-92% | <88% | __ |
| Paraphrase-with-self-prior (all heads) | __ % | ≥65% | 50-65% | <50% | __ |
| `meta_logic` per-bucket exact | __ % | ≥30% | 20-30% | <20% | __ |
| `v76_production` per-bucket exact | __ % | ≥50% | 35-50% | <35% | __ |
| Demographic robustness (worst stratum gap) | __ pp | within 10pp | 10-15pp | >15pp | __ |

**K=9 baseline reference (production current):** canonical 93.2%, paraphrase 46.9%.

**Decision rules:**
- All 5 PASS → land v1, document in HONEST_STATUS + CHANGELOG, replace K=9 as production.
- 3-4 PASS / 1-2 HALF-PASS → land v1 as candidate, schedule targeted follow-on for half-passing metrics.
- Any FAIL on canonical or demographic → do NOT land v1; targeted experiment instead (v76 first-operand routing OR meta_logic vocab/relations).

---

## 4. Deliverable 2 — Native generator reconciliation plan

### 4.1 The mismatch, concrete

**Training script `train_native_nl_gen.py` emits per batch:**
```python
{
  "input_ids": Tensor[B, L],
  "target_ids": Tensor[B, L],
  # ... possibly "struct_targets"
}
```
Built by `_records_to_batch(records, device)` at line 597. Each record needs pre-tokenized `input_ids` and `target_ids` fields.

**Real `NLGenerationHead.forward` consumes (line 246):**
```python
forward(
    decoder_input_ids: Tensor[B, L_dec],
    bottleneck_z: Tensor[B, 64],     # continuous CAS state from encoder
    cas_prefix_ids: Optional[Tensor[B, K]],    # discrete CAS expression tokens
    encoder_outputs: Optional[Tensor[B, S_enc, D]],  # full prompt encoding (for cross-attn)
    domain_mask: Optional[Tensor[B, S_enc]],    # P/C/E/O validity mask
    register_id: Optional[Tensor[B]],   # 0..3 for T/A/f/E
    return_meta: bool = False,
) -> Tensor[B, L_dec, V] | (Tensor, GenerationMeta)
```

The `_FallbackNLGenerationHead` (line 213) fakes a compatible signature `forward(input_ids, target_ids, ...)` — that's why current smoke tests pass. **For real GPU training on the production NLGenerationHead, the batcher needs replacement.**

### 4.2 What records need to carry

For each training example, the dataset record needs at minimum:
| Field | Source | Used for |
|---|---|---|
| `prompt_text` | SDG record | Encoder input — tokenize → `prompt_ids` |
| `cas_expression` | SDG record | (a) Encoder context, (b) `cas_prefix_ids`, (c) parse register_id, (d) compute domain_mask |
| `reply_text` | SDG record | Decoder targets — tokenize → `reply_ids` |
| `noetic`, `domain`, `drive`, `register` | SDG record (parsed) | Optional structured-supervision targets |

The dt_K4 corpus on disk (`level3_canonical_dt_K4.jsonl`, 77,816 records) carries `prompt_text`, `cas_expression`, plus the demographic+tonal-rewritten paraphrase. **`reply_text` is NOT in dt_K4** — the dt_K4 corpus is for classifier paraphrase invariance training, not for generation training. Generation training needs the Tier 3 multi-turn dialogue corpus (per the SDG strategy doc) which has not been generated yet.

Until Tier 3 lands, the closest available training data is:
- `lever3_paired_dt_K4.jsonl` (19,652 records) — has paired prompt + reply but the "reply" is a CAS expression, not fluent English
- The 2,500 Tier 1 seed records committed last night — has `reply` field but they are template-based, not fluent

**Honest:** **the corpus needed for generation training does not yet exist on disk in fluent-English form at scale.** Tier 3 SDG must run before generation training can produce a useful model.

### 4.3 The bridge — what code must be written

A new collator `cas_native.training.datasets.native_nl_collator.NativeNLCollator` that:

1. **Tokenizes inputs** using the extended HybridCASTokenizer + English BPE (commit e4bbad8):
   - `prompt_ids = tokenizer.encode(prompt_text)`
   - `reply_ids = tokenizer.encode(reply_text)`
   - `cas_prefix_ids = tokenizer.encode_cas(cas_expression)` (CAS-only path that hits low-ID reserved tokens)

2. **Builds decoder inputs** (teacher-forcing convention):
   - `decoder_input_ids = [BOS] + reply_ids[:-1]`
   - `lm_targets = reply_ids` (one-position-ahead prediction)
   - `loss_mask` = 1 for reply positions, 0 for prompt + CAS prefix positions (so loss is only computed on reply tokens)

3. **Parses CAS axes** from the expression:
   - `register_id = {"T": 0, "A": 1, "f": 2, "E": 3}[parsed_register]` (default 0 if unspecified)
   - `domain_mask` — `(B, S_enc)` mask. The current model just expects a validity mask over encoder positions. v0 implementation: all-ones mask of shape `(B, S_enc)`. Production version: derive from CAS expression's domain field if it constrains the encoder positions.

4. **Returns the batch dict** that `NLGenerationHead.forward` and the existing `CASNativeModel.forward_with_lm` can consume directly.

### 4.4 Training-step changes

```python
# OLD (smoke + fallback only):
batch = _records_to_batch(batch_records, device)
output = model(batch["input_ids"], batch["target_ids"])

# NEW (real model):
batch = native_nl_collator(batch_records, tokenizer, device)
encoder_outputs, bottleneck_z = cas_native_model.encode(batch["prompt_ids"])
lm_logits = nl_gen_head(
    decoder_input_ids=batch["decoder_input_ids"],
    bottleneck_z=bottleneck_z,
    cas_prefix_ids=batch["cas_prefix_ids"],
    encoder_outputs=encoder_outputs,
    domain_mask=batch["domain_mask"],
    register_id=batch["register_id"],
)
loss_lm = masked_cross_entropy(lm_logits, batch["lm_targets"], batch["loss_mask"])
loss_total = alpha * loss_structured + beta_now * loss_lm  # joint loss with curriculum on β
```

`cas_native_model.encode` is a new helper method that returns `(encoder_outputs, pooled_hidden_state)` — a thin wrapper around existing `forward()` that extracts the bottleneck before the structured-prediction head runs. (Or just use the existing model's intermediates if exposed.)

### 4.5 Estimated build effort

- New collator: ~200 LOC + ~80 LOC of tests
- New encode helper on CASNativeModel: ~30 LOC (or 0 if existing `forward()` already exposes intermediates — needs check)
- Updated training loop in train_native_nl_gen.py: ~50 LOC of changes
- New masked-CE loss helper: ~30 LOC + tests
- **Total: ~400 LOC + ~150 LOC tests = ~half a day of focused work**

This is unblocked the moment we have a Tier 3 dialogue corpus on disk.

### 4.6 Soft-prefix design tracking (open task #105)

Spec recommends `soft_prefix_proj` as `Linear(d_model, K * d_model)` projecting `pooled_hidden_state`. The committed model at `e645296` already implements this — `_build_soft_prefix(self, bottleneck_z)` calls `self.soft_prefix_proj(bottleneck_z)` then reshapes to `(B, K, d_model)`. The "free embeddings" that the prior session flagged were superseded by the projection — task #105 may already be effectively closed. **VERIFY** by re-reading `nl_generation_head.py:392-410` before closing the task.

---

## 5. Deliverable 3 — PR replay/cleanup plan (read-only diff analysis)

### 5.1 PR #34 — demographic + tonal SDG/eval (LOW RISK)

**Files PR #34 adds:**
- `cas-synthetic/generator/demographic_tonal_axes.py` (505 lines, NEW)
- `cas-synthetic/generator/demographic_tonal_rewrite.py` (502 lines, NEW)
- `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py` (229 lines, NEW)
- `cas-synthetic/tests/test_demographic_tonal.py` (407 lines, NEW)
- `docs/working/sdg_demographic_tonal_spec_2026_05_04.md` (NEW)
- `docs/working/task_68_completion_2026_05_04.md` (NEW)
- `docs/working/task_69_demographic_robustness_completion_2026_05_04.md` (NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py` (743 lines, NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/__init__.py` (NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/conftest.py` (NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/test_demographic_robustness_eval.py` (449 lines, NEW)

**Verified read-only:** ALL of these files are MISSING on origin/master right now. The dt_K4 corpora (77,816 records etc.) exist on disk because someone ran this PR's code locally and saved the output, but did not commit the source files.

**Risk assessment: LOW.** No file collision with origin. Direct cherry-pick should be clean. No Session 55 work would be erased.

**Strategy:** cherry-pick PR #34's commits onto a fresh branch off `origin/master`. Verify all 11 files apply clean. Run the test suites:
```bash
pytest cas-synthetic/tests/test_demographic_tonal.py
pytest noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/test_demographic_robustness_eval.py
```
Expected: 12/12 + 20/20 pass. PR can be merged via standard GH flow once tests pass.

### 5.2 PR #33 — vocab14 reserved CAS tokens (MEDIUM RISK)

**Files PR #33 modifies/adds:**
- `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/__init__.py` (+2 lines)
- `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/cas_notation.py` (+45 lines — file EXISTS on origin, will need 3-way merge)
- `noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/vocabulary.py` (+75 lines)
- `noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/test_reserved_cas_tokens.py` (257 lines, NEW)
- `docs/working/vocab14_prep_memo_2026_05_04.md` (NEW)
- `docs/working/vocab14_retrain_RUNBOOK_2026_05_04.md` (NEW)

**Verified read-only:**
- `cas_notation.py` exists on origin/master
- `test_reserved_cas_tokens.py` is MISSING on origin/master
- `RESERVED_CAS_TOKENS` does NOT appear in origin/master's `cas-native/tokenizer/__init__.py`
- Origin's `tokenizer/__init__.py` was modified by tonight's commit `e4bbad8` (English BPE extension) — adding lazy `__getattr__` exports for `ExtendedHybridCASTokenizer`, `train_english_bpe`, etc.

**Risk assessment: MEDIUM.** PR #33 modifies the same `__init__.py` that origin's English BPE work modified. Direct rebase will hit a conflict on `__init__.py`.

**Strategy:** cherry-pick PR #33's commits, then resolve the `__init__.py` conflict by keeping BOTH origin's English BPE exports AND PR #33's vocab14 exports. They're additive, not contradictory. Run tests:
```bash
pytest noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/
pytest noetic-compass-scaffold/noetic-compass/cas-native/tests/training/test_english_bpe_extension.py
```
Both must pass after merge.

### 5.3 PR #32 — v0 conversational CLI (HIGH RISK — REBUILD, do not rebase)

**Files PR #32 modifies/adds:**
- `cas.bat` (NEW) — Windows wrapper at repo root
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/QUICKSTART.md` (180 lines, NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_cli.py` (338 lines, NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_renderer.py` (672 lines, NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/chat.py` (666 lines — origin has SUPERSET version with CABS + Mode 7)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/demo_prompts.py` (156 lines, NEW)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/predict_cas.py` (279 lines — origin has SUPERSET version with `with_trace`)
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/rewrite_shim.py` (392 lines, NEW)
- `docs/working/cas_native_conversational_broadening_proposal_2026_05_04.md` (NEW)

**Verified read-only:**
- `chat.py` EXISTS on origin/master — it's the Session 55 version with `/beliefs` `/why` `/forget` `/trace` commands wired in
- `predict_cas.py` EXISTS on origin/master — it's the Session 55 version with `with_trace=False` parameter
- `cas_renderer.py` MISSING on origin/master
- `cas_cli.py` MISSING on origin/master
- `cas.bat` MISSING on origin/master
- `demo_prompts.py` and `rewrite_shim.py` likely MISSING on origin/master (not verified yet — verify before cherry-pick)

**Risk assessment: HIGH on chat.py + predict_cas.py.** A direct rebase of PR #32 onto origin/master would erase the CABS commands + Mode 7 trace integration. The PR's chat.py is from before those features existed.

**Strategy: split PR #32 into two pieces:**
1. **Cherry-pick the new files cleanly:** `cas.bat`, `QUICKSTART.md`, `cas_cli.py`, `cas_renderer.py`, `demo_prompts.py`, `rewrite_shim.py`, the proposal doc. None of these exist on origin, so they apply clean.
2. **Rebuild chat.py + predict_cas.py changes manually.** Read PR #32's diff to those two files. Identify the new functionality (probably: `/menu`, `/sample`, `/raw` commands, demo prompts integration, rewrite shim integration). Add those features ON TOP of origin's current chat.py + predict_cas.py — do NOT replace.

This is the only PR that requires manual work. Estimate: 1-2 hours of careful merging.

### 5.4 Recommended sequencing

1. PR #34 first (lowest risk, biggest content delivery — 11 new files, 3,665 lines, 32 tests).
2. PR #33 second (resolves the `__init__.py` conflict cleanly).
3. PR #32 last as a SPLIT (new files cherry-pick clean; chat.py / predict_cas.py reconciliation done manually with full attention).
4. After all three land: run full test suite. Target ~250+ tests passing.
5. Update HONEST_STATUS to reflect new state.

### 5.5 What NOT to do

- DO NOT use `git merge` directly on any of these PRs. The non-fast-forward path will resolve in unpredictable ways.
- DO NOT cherry-pick PR #32 wholesale — chat.py + predict_cas.py will erase Session 55 work.
- DO NOT do this work in the dirty current local checkout. Use a fresh worktree from `origin/master`. (Worktree creation requires user authorization per current directive.)

---

## 6. Deliverable 4 — HONEST_STATUS draft notes (DO NOT COMMIT YET)

The current HONEST_STATUS.md is from 2026-05-04 evening, BEFORE the agent commits landed. It still labels things as "IN PROGRESS" that are now SHIPPED. Below is the diff to apply when (a) the v1 retrain produces a verdict, and (b) PRs #32/#33/#34 are reconciled.

### 6.1 What changed since 2026-05-04 evening

| Feature | Old status (current HONEST_STATUS) | New status (post-Session 55) |
|---|---|---|
| Belief substrate (CABS) | IN PROGRESS | **SHIPPED + WIRED** (commit fbf44e0). 98 tests pass. |
| `/beliefs`, `/why`, `/forget` REPL commands | IN PROGRESS | **WIRED** (commit fbf44e0). |
| Mode 7 trace package | SCAFFOLD (1,855 LOC, synthetic tests) | **SHIPPED + WIRED** (commit 32a76d5). Real PyTorch hooks during predict_cas. 17 new tests. Combined 148 trace+belief tests. |
| `/trace` REPL command | NOT STARTED | **WIRED** (commit 32a76d5). `/trace` and `/trace --raw`. |
| Idea Atlas adapter | TO BE BACKED OUT (cas-native/atlas/) | adapter at cas-native/inference/atlas_adapter.py (commit 21ff240) bridges to shipped /idea_atlas API. The cas-native/atlas/ duplicate scaffold still pending back-out. |
| Native NL gen architecture spec | NOT STARTED | **DONE** (~7,164-word spec at docs/working/native_nl_generation_head_spec_2026_05_04.md). |
| NLGenerationHead module | NOT STARTED | **SCAFFOLD** (commit e645296). 50.2M params, random-init, "NO foreign pretrained" enforced by static docstring scan. **NOT TRAINING-READY** — batcher mismatch (see §4 above). 18 tests pass. |
| English BPE tokenizer extension | NOT STARTED | **DONE** (commit e4bbad8). Stdlib-only BPE, deterministic merges, full vocab provenance. 28 tests pass. |
| Native NL gen training pipeline | NOT STARTED | **SCAFFOLD** (commit bd70c05). Smoke test exits 0. NOT REAL-TRAINING-READY until §4 bridge built. |
| Native NL gen eval harness | NOT STARTED | **SCAFFOLD** (commit bd70c05). 9 tests pass. Three metrics: CAS-grounding rate, fluency PPL, distinct-2 diversity. |
| Generation trace surface | NOT STARTED | **SCAFFOLD** (commit bd70c05). GenerationTraceCapture wraps model trace + NN lookup + live CAS-grounding. 8 tests pass. |
| SDG: Tier 1 seed (template) | DONE in seed batch | **SHIPPED but redundant.** 2,500 records on disk. The 77K dt_K4 corpus (PR #34) supersedes templates. |
| SDG: Tier 2 (demographic + tonal) | (Not yet listed) | **Code missing on origin/master** (PR #34 unmerged) but **77,816 dt_K4 records exist on disk locally.** Cherry-pick PR #34 to land the code. |
| SDG: Tier 3 (multi-turn dialogue) | (Not yet listed) | **NOT STARTED.** Required for native generation training. ~50-200K records via Claude API, ~$200-500. |
| v1 Full Stack retrain | IN PROGRESS | **STILL IN PROGRESS** (PID 11823, run dir `v1_full_stack_2026_05_05_restart`, restarted 2026-05-05T05:56 UTC). At 2h 8min, frozen at model_init same as prior stuck run. Watch for first epoch_end. |
| K=9 baseline classifier | WIRED (production) | **STILL WIRED** as production. 93.2% canonical / 46.9% paraphrase. v1 retrain will replace if all 5 gates pass. |
| Diagloop architecture | (Tested via PR #6) | **DEPRECATED** as production path (Session 52 verdict, K=9 stays). Honest +17.6 pp paraphrase lift was real, but canonical regressed to 63.0%. Tri-channel framework (the methodology) preserved; that specific architectural realization deprecated. |

### 6.2 New "★ Architectural rules ratified" section to add

(This was the headline of the 2026-05-04 evening session; should be in HONEST_STATUS.)

```markdown
## ★ Hard architectural rules — non-negotiable

### Rule 1: NO foreign pretrained models in the production stack
No TinyLlama, Llama, Qwen, Mistral, Phi, Gemma, GPT-2, BERT. Random-init from scratch only. Acceptable third-party tools: PyTorch (framework), HuggingFace `transformers` patterns as REFERENCE only (not loading weights), Claude API for SDG (data only). "CAS gets the glory, or the project doesn't ship."

### Rule 2: TRACEABILITY is the architectural spine
Every model output, belief lock-in, training record, generated reply, and eval result walks back to its origin via id/created_at/schema_version/parent_ids/source/trace_id. "Show your work, or don't ship it."

### Rule 3: Plain language, no jargon
The user is direct and intolerant of conference-paper vocabulary. Translate any technical term inline.

### Rule 4: Project familiarity required for every spawned agent
Agents read CLAUDE.md, HONEST_STATUS.md, recent CHANGELOG, and the relevant memory files BEFORE writing code.

### Rule 5: Always git-fetch + read CHANGELOG before launching expensive operations
Session summaries can be stale by 6+ hours.

### Rule 6: If the answer is in the codebase, the question isn't open
Before flagging anything as "open," grep the repo and search memory.
```

### 6.3 What to NOT add yet

- Do NOT mark v1 retrain as completed. Wait for first epoch_end.
- Do NOT update the elevator pitch yet — wait for retrain verdict.
- Do NOT commit this draft. Hold until retrain lands.

---

## 7. Deliverable 5 — Sample review template

When the run completes and eval samples land, do NOT just look at aggregate metrics. Pull samples per bucket per failure mode and read them.

### 7.1 Buckets to sample from (ordered by importance for v1 verdict)

| Bucket | n in eval | Key failure mode |
|---|---:|---|
| `meta_logic` | 102 | meta_relations head fails 53% on multi-label sets; `^0`→`^5` noetic confusion on constructor-only expressions |
| `v76_production` | 108 | Multi-operand routing failure: target.noetic = first state-literal but model emits other operands (often heavier-coefficient) |
| `v75_register` | 264 | Register paraphrase invariance |
| `v77_omega` | 267 | Generally strongest; sample wins to confirm not regressed |
| `v74_baseline` | 200 | Baseline; sample for paraphrase invariance regressions |
| `v77_rule_four` | 59 | transition_kind head failures historically |

### 7.2 Sample selection per bucket

For each bucket, pull 5 of each:

| Category | Selection |
|---|---|
| Clean wins | `all_heads_exact == True` on canonical AND paraphrase. 5 samples for confirmation. |
| Canonical failures | `all_heads_exact == False` on canonical. 5 samples. Diagnose: which head failed? What was target vs predicted? |
| Paraphrase failures | `all_heads_exact == True` canonical, `False` on paraphrase. 5 samples. This is the dominant failure mode — pure invariance issue. |
| Both-wrong | `all_heads_exact == False` on both. 5 samples. Genuine knowledge gap. |

### 7.3 Demographic stratum sampling (for demographic robustness eval)

For each of the 8 demographic profiles × 5 tones = 40 strata, pull at least:
- 2 wins
- 2 losses

Especially focus on the WORST stratum identified by the eval — read 10 samples from there to understand the failure mode.

### 7.4 Sample template (one record per row)

```
## Sample {id} — bucket: {X}, type: {clean win | canonical fail | paraphrase fail | both-wrong}

INPUT (canonical)            "{text}"
INPUT (paraphrase)           "{text}"
INPUT (demographic profile)  {profile_name}
INPUT (tone)                 {tone_name}

TARGET CAS                   {cas_expression}

PREDICTED CAS (canonical)    {expression or "predicted axes: noetic=^X, domain=Y, drive=FZ, register=|R, ..."}
PREDICTED CAS (paraphrase)   {same shape}

PER-HEAD MATCHES (canonical):  noetic ✓ domain ✓ drive ✓ register ✓ reg_mode ✓ has_omega ✓ has_meta ✓ exp_fam ✓ meta_rel ✓ trans_kind ✓ turn_type ✓ authority ✓
PER-HEAD MATCHES (paraphrase): noetic ✓ domain ✗ drive ✓ register ✗ ...

DIAGNOSIS (free text):
- e.g., "v76: noetic emitted second operand (^4) instead of first (^6); coefficient 1.1 on operand 3, 0.9 on operand 1 — model anchored to heavier-coefficient operand, label policy expects first-position"
- e.g., "meta_logic: meta_relations emitted [] when target was [membership]; expression was Product(Noetics, Registers) — vocab gap, no token for `Product` constructor in pre-vocab14 vocabulary"
- e.g., "v75 demographic-rural-rural-tone-elder: register flipped from |E to |A under elder paraphrasing; demographic rewriting may be smoothing concrete/embodied phrasing into analytical"
```

### 7.5 What to LOOK FOR (decision-support)

After reading ~50 samples, the question to answer is NOT "did the numbers move" but "is the model actually learning the structure or shifting the failure surface."

| Pattern | Interpretation | Action |
|---|---|---|
| Clean wins look correct, all 12 heads matching | Model is learning correctly | Land v1 |
| Canonical wins, paraphrase failures concentrated in one head | Invariance gap, not knowledge gap | Land v1 with caveat; targeted invariance work next |
| Per-bucket failures concentrated in v76 noetic head with heavier-coefficient routing | Confirms architectural multi-operand routing failure (v76_meta_logic_deep_dive's diagnosis) | Land v1; queue first-operand-anchor architecture work |
| meta_relations head still failing 50%+ even with vocab14 | Vocab patch didn't reach this head | Land v1; deeper meta_relations head work needed |
| Demographic stratum gap >15pp on any one profile | Demographic robustness FAIL | Do NOT land v1; targeted demographic re-balancing |
| Sample text looks plausible but axes wrong | Surface-level fluency masking structural confusion | Inspect carefully — may indicate model is gaming surface tokens |

---

## 8. Read-only command log (this session)

Every command run during this preparation. All read-only (no signals to PID 11823, no edits to existing files, no commits, no worktree creation).

```
# Pod check
ssh root@104.255.9.187 -p 15409 -i ~/.ssh/id_ed25519 "date -u && ps -p 11823 -o pid,etime,pcpu,pmem,cmd && tail -n 30 [run_dir]/launch.log && grep -c epoch_end [run_dir]/launch.log; nvidia-smi"
# At 08:04 UTC: PID alive 2h 8min, 99.8% CPU, log frozen 43min at model_init, GPU 14%/77W, 0 epoch_end

# SIGQUIT registration check
ssh ... 'grep -nE "faulthandler\.register|signal\.SIGQUIT" [training_script]'
# Result: empty. SIGQUIT NOT registered → would terminate.

# Post-model_init code path read
ssh ... 'sed -n "853,1010p" [training_script]'
# Confirmed: 8,678 batches/epoch with no inter-batch logging, eval_every_steps=None.

# PR #33 read-only diff
git fetch origin pull/33/head ; git diff --stat origin/master...FETCH_HEAD
# Result: 6 files, 688 insertions. Modifies tokenizer/__init__.py (conflict risk with English BPE).

# PR #34 read-only diff
git fetch origin pull/34/head ; git diff --stat origin/master...FETCH_HEAD
# Result: 11 files, 3,665 insertions. ALL files MISSING on origin → clean cherry-pick.

# PR #32 read-only diff
git fetch origin pull/32/head ; git diff --stat origin/master...FETCH_HEAD
# Result: 9 files, 2,814 insertions. Modifies chat.py + predict_cas.py — origin has Session 55 SUPERSET versions. HIGH RISK.

# Origin file existence checks
git cat-file -e origin/master:[file]
# Verified: PR #34 files all MISSING on origin. PR #33 cas_notation.py EXISTS but RESERVED_CAS_TOKENS NOT in origin's __init__.py. PR #32: chat.py + predict_cas.py EXIST on origin (newer); cas_renderer/cas_cli/cas.bat MISSING.

# Native gen batcher signature read
git show origin/master:[train_native_nl_gen.py] | grep "_records_to_batch|input_ids|target_ids|FallbackNLGenerationHead"
# Confirmed: training emits {input_ids, target_ids} via _records_to_batch (line 597). NLGenerationHead.forward expects (decoder_input_ids, bottleneck_z, cas_prefix_ids, encoder_outputs, domain_mask, register_id). Concrete bridge needed.
```

---

## 9. Hard rules (recap, for the next LLM)

1. **No foreign pretrained models in production.** Random-init only. Claude API OK for SDG.
2. **Object traceability mandatory.** Every artifact has id + created_at + schema_version + parent_ids + source + trace_id.
3. **Plain language only.** No jargon without inline definition.
4. **Always git-fetch + read CHANGELOG before expensive operations.**
5. **If the answer is in the codebase, the question isn't open.** Grep before flagging.
6. **PYTHONFAULTHANDLER=1 alone does NOT make SIGQUIT non-destructive.** Must verify `faulthandler.register(signal.SIGQUIT, ...)` is in the script. Verified for the current pod run: NOT registered. SIGQUIT will kill.

## 10. What to do if pod produces `epoch_end`

1. Stop side work in this doc.
2. Pull launch.log immediately.
3. Note the wall-clock per epoch (epoch_end timestamp - model_init timestamp).
4. Continue monitoring; ETA for 20-epoch run = 20 × per-epoch time.
5. When training completes (manifest.json appears in run dir): pull small artifacts per §3.1, run eval per §3.2, fill in pass/fail table per §3.3, do sample review per §7, draft HONEST_STATUS update per §6.

## 11. What to do if pod hits 3-4h without `epoch_end`

1. Report the elapsed time, GPU/CPU state, last log line. Do NOT act beyond reporting.
2. The user will decide whether to authorize SIGKILL + restart with `--eval-every-steps 50` (gives intermediate logs to break the silent-loop ambiguity).
3. SIGQUIT is NOT a non-destructive option on this run (verified).

## 12. What NOT to do

- No signals to PID 11823 without explicit user authorization.
- No file edits to existing tracked files. (This handoff note is a NEW file, explicitly authorized.)
- No commits.
- No worktree creation.
- No PR merges. PRs need careful sequenced cleanup per §5.
- Do NOT regenerate dt_K4 corpora — 77,816 records already on disk.
- Do NOT propose Tier 1 templates as primary training data — use the Tier 2 dt_K4 corpus + Tier 3 dialogue (when generated).
- Do NOT propose foreign pretrained models, ever.

---

End of handoff. Re-check pod state every 20-30 min until `epoch_end` appears or 3-4h threshold hit.
