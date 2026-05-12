# Candidate E Stage 2 — locked launch commands (2026-05-12)

**Status:** E2a ready to launch. E2b stub-blocked until L_span +
L_contrastive_margin + L_coverage + pair-aware batcher land.

**Locked against:** trainer commit after `Stage 2 setup` PR; corpus
`rpm_copy_grounding_v2_{train,dev,source_swap_dev}` at commit `4ecddfa`;
evaluator `evaluate_candidate_e_stage2.py` at this PR.

## Locked hparams (carried from B1/B2 verbatim)

| Hparam | Value | Source |
|---|---|---|
| `--batch-size` | 16 | B1/B2 launch (Candidate B design doc 2026-05-11) |
| `--n-steps` | 1000 | Candidate E design §Stage 2 (`design_2026_05_12.md`) |
| `--lr` | 1e-4 | B1/B2 launch — anti-tuning rule |
| `--weight-decay` | 1e-4 | B1/B2 launch — anti-tuning rule |
| `--grad-clip` | 1.0 | B1/B2 launch |
| `--d-model` | 384 | trainer default; matches B1/B2 |
| `--encoder-n-layers` | 4 | matches B1/B2 |
| `--decoder-n-layers` | 6 | matches B1/B2 |
| `--encoder-n-heads` | 6 | matches B1/B2 |
| `--decoder-n-heads` | 6 | matches B1/B2 |
| `--seed` | 1729 | B1/B2 launch |
| `--limit` | 100000 | per `feedback_limit_default_128_trap` (corpus has 3000 records; high cap = no truncation) |
| `--max-cas-prefix-len` | **192** | Candidate E spec — every launch must pass this explicitly |
| `--train-log-every-steps` | 50 | B1/B2 launch |
| `--canary-max-new-tokens` | 128 | B1/B2 launch |
| `--sample-canary-at` | 250,500,750,1000 | Candidate E design §Stage 2 sanity checks |
| `--save-checkpoints-at` | 250,500,750,1000 | matches B1/B2 |
| `--save-final-checkpoint` | (flag) | required for warm-start chain |

## E2a launch command (TEMPLATE — see USER ACTION below before running)

Pre-launch verification checklist:
- `--ablation e2a` accepted by parse_args (test: `test_trainer_cli_ablation_e2a_loss_weights`)
- `--max-cas-prefix-len 192` plumbed through to collator (test: `test_trainer_cli_max_cas_prefix_len_override`)
- Loss weights: `lm=1, fr=1, slot_type=1, copy=0, phrase_bias_aux=0` (functionally identical to b2; named distinctly so logs/manifest show E-era intent)
- Warm-start source: B2's `ckpt_final.pt`

### USER ACTION REQUIRED - sync patched code and corpora to pod

Do this before resolving `B2_CKPT` or launching. E2a is invalid if the pod
still has stale B-era trainer/collator/evaluator files.

Required files on `/workspace/tksCAS`:

| Local file | Remote file |
|---|---|
| `noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py` | same path |
| `noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py` | same path |
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py` | same path |
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.audit.json` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.audit.json` | same path |
| `cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.audit.json` | same path |

After sync, verify local and remote MD5s match. From local PowerShell,
compute local hashes:

```powershell
$files = @(
  "noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py",
  "noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py",
  "noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py",
  "noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.audit.json",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.audit.json",
  "cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.audit.json"
)
$files | ForEach-Object {
  "{0}  {1}" -f (Get-FileHash -Algorithm MD5 $_).Hash.ToLower(), $_
}
```

Then on the pod:

```bash
cd /workspace/tksCAS
md5sum \
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  noetic-compass-scaffold/noetic-compass/cas-native/training/datasets/simplex_collator.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py \
  noetic-compass-scaffold/noetic-compass/cas-native/evaluation/sample_decoder.py \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.audit.json \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.audit.json \
  cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.audit.json
```

Launch only if every hash matches. This closes the stale-pod-code failure
mode observed earlier in the architectural review.

### USER ACTION REQUIRED — resolve `<B2_TS>` before running

The B2 checkpoint timestamp is unknown locally (B2 ran on the pod;
checkpoints live on pod storage, not in the local repo). On the pod,
discover it with:

```bash
ls -1dt /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_* | head -3
# Example output:
#   /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_20260512T034221Z
#   /workspace/tksCAS/stage7_candidate_b2_lmfr_slot_20260511T235100Z
```

Pick the run whose `<TS>/ckpt_final.pt` exists AND was the strict-validate
B2 run (slot stable, no leakage — the design doc says use this one as
warm-start base). Then substitute the actual timestamp into the `B2_CKPT`
line below, verify with `ls -l $B2_CKPT` returns a real file, and only
then execute the launch block.

### Launch block

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
# USER: replace <B2_TS> with the actual timestamp from the ls above.
B2_CKPT=/workspace/tksCAS/stage7_candidate_b2_lmfr_slot_<B2_TS>/ckpt_final.pt
test -f "$B2_CKPT" || { echo "B2_CKPT does not exist: $B2_CKPT"; exit 1; }
OUT=/workspace/tksCAS/stage_e2a_warmup_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 100000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation e2a --max-cas-prefix-len 192 \
  --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 250,500,750,1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  --load-model-from ${B2_CKPT} \
  > ${OUT}.log 2>&1 &
```

Verify before pressing Enter:
- `${B2_CKPT}` resolves to a real file (`ls -l ${B2_CKPT}`)
- `${OUT}` parent dir is writable
- `--max-cas-prefix-len 192` appears verbatim in the command
- `--ablation e2a` is on the command line (not b2 — the rename is the point)
- GPU is idle (`nvidia-smi`)

## E2a evaluator command (READY, runs after E2a finishes)

Reads dev + source-swap-dev artifacts and reports both metrics. At
stage=e2a these are **informational only** — no gate-fail. Recovery is
expected near 0 because copy is off; the LM/slot warmup is what matters.
The evaluator metrics serve as the empirical anchor for L_span /
L_contrastive_margin / L_coverage design in the E2b PR.

```bash
EVAL_TS=$(date -u +%Y%m%dT%H%M%SZ)
EVAL_OUT=/workspace/tksCAS/eval_e2a_${EVAL_TS}

python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate_candidate_e_stage2.py \
  --checkpoint ${OUT}/ckpt_final.pt \
  --dev-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl \
  --source-swap-dev-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --output-dir ${EVAL_OUT} \
  --device cuda:0 \
  --max-cas-prefix-len 192 \
  --max-new-tokens 192 \
  --stage e2a
```

Surface contents of `${EVAL_OUT}/evaluate_candidate_e_stage2_findings.md`
and `evaluate_candidate_e_stage2_report.json` before deciding to start
Stage 2b implementation. Specifically look at:

- `dev_summary.full_recovery_rate` — informational at E2a; if it's
  surprisingly high (>10%) flag it: that would mean LM/slot warmup is
  recovering identifiers without explicit copy supervision, which is
  evidence about template completion or memorization that should inform
  the L_span design.
- `swap_summary.n_pairs_with_cross_emission` — informational; high
  cross-emission at warmup = memorization signature surviving from B2
  initialization, which means L_contrastive_margin is the load-bearing
  Stage 2b add.
- `dev_per_record[*].slot_type_trace` (full) +
  `dev_per_record[*].slot_type_trace_prefix` (first 40) — should show
  STAGE_VAR spans (slot id 2) at the right approximate positions if the
  slot head is healthy. **This is E2a's load-bearing evidence — the
  warmup's job is slot-head stability, not recovery.** Per Codex audit
  2026-05-12 finding 1 the evaluator now emits the full trace; without
  it the run's most important signal would be discarded.
- `dev_per_record[*].longest_stage_var_run` — should be in a sensible
  range (~8-12 tokens for a 4-stage rpm chain identifier). 0 = slot head
  not firing STAGE_VAR at all; >>20 = slot head locked open / phrase loop.
- `dev_per_record[*].stage_var_token_count` — total STAGE_VAR positions
  across all spans. Compare to `n_target` × ~10 tokens-per-identifier
  to detect under-firing.
- `dev_per_record[*].n_tokens_generated` / `hit_eos` / `text_len` —
  early-EOS / runaway-generation diagnostics; truncated runs indicate
  EOS bias, runaway runs indicate decoder collapse.

## E2b launch command (BLOCKED)

**Do not run.** `parse_args(--ablation e2b)` raises
`NotImplementedError` at the trainer entrypoint per
`_enforce_e2b_block`. The blocker message:

> Candidate E Stage 2b is stub-blocked. e2b requires L_span,
> L_contrastive_margin, L_coverage, and pair-aware batch sampling,
> none of which are wired yet. Run --ablation e2a first; loss design
> for 2b follows from E2a evaluator results.

When the Stage 2b loss-implementation PR lands, this section will be
updated with the locked E2b launch command. Until then, leave as a
placeholder so the structure is visible:

```bash
# DO NOT RUN UNTIL Stage 2b loss PR lands and removes the stub-block.
# Template only — losses L_span / L_contrastive_margin / L_coverage
# do not exist in the trainer yet.
#
# TS=$(date -u +%Y%m%dT%H%M%SZ)
# E2A_CKPT=${OUT}/ckpt_final.pt   # from the E2a run above
# OUT_E2B=/workspace/tksCAS/stage_e2b_full_${TS}
# python .../train_simplex_mvp.py \
#   --data-path .../rpm_copy_grounding_v2_train.jsonl \
#   --output-dir ${OUT_E2B} \
#   --ablation e2b --max-cas-prefix-len 192 \
#   --load-model-from ${E2A_CKPT} \
#   [... same hparams as E2a ...] \
#   [+ TBD flags for new loss weights, pair sampling, TF mode]
```

## E2b evaluator command (BLOCKED)

`--stage e2b` raises `NotImplementedError` at parse-time. The evaluator
today has NONE of the four E2b gate paths:

| Gate | Status in evaluator | Required for E2b |
|---|---|---|
| TF fresh source recovery ≥80% | absent (`--tf-mode` reserved, raises) | yes |
| Source-swap conditionality ≥85% | partial — pair-pass rate computed but no fail-exit threshold | yes |
| Slot F1 for copy-bearing slots ≥90% | absent (no F1 computation across records) | yes |
| Non-rpm leakage = 0 | absent (evaluator reads dev + swap_dev, both rpm-only) | yes |

E2b unblock requires BOTH:

1. **Trainer-side:** Stage 2b loss PR adds L_span, L_contrastive_margin,
   L_coverage, pair-aware batcher (`_enforce_e2b_block` is removed
   from `train_simplex_mvp.py`).
2. **Evaluator-side:** this evaluator gains a TF entrypoint, slot F1
   metric, non-rpm leakage scoring path that reads a non-rpm dev subset,
   and fail-exit threshold enforcement (4 gates above).

Both PRs must land before `--stage e2b` is unblocked. The evaluator
`--stage e2b` raise lists the four missing scoring paths verbatim so a
stray launch surfaces the gap immediately.

## What we are NOT doing in Stage 2 setup

- Implementing L_span / L_contrastive_margin / L_coverage (deferred to a
  separate Stage 2b PR after E2a evaluator results are in)
- Pair-aware batch collation (deferred to Stage 2b PR — L_contrastive_margin
  requires both pair members in the same batch)
- TF entrypoint in the evaluator (`--tf-mode` raises NotImplementedError;
  free-decode is the primary falsification metric per the A/B/C/D
  postmortem TF/free-decode divergence pattern)
- DAgger / on-policy training (Stage 3, gated on Stage 2b TF gates)

## Pre-launch audit checklist (user sign-off before any pod work)

- [ ] B2 checkpoint path resolves to a real file
- [ ] Patched code and Candidate E corpora are synced to pod
- [ ] Local MD5s match pod MD5s for all required files listed above
- [ ] `--max-cas-prefix-len 192` appears verbatim in the E2a command
- [ ] `--ablation e2a` (not b2) appears in the E2a command
- [ ] Evaluator command points at `rpm_copy_grounding_v2_dev.jsonl` AND
      `rpm_copy_grounding_v2_source_swap_dev.jsonl` (the new artifacts,
      not a v1_mix subset)
- [ ] `--stage e2a` flag set on evaluator (informational mode)
- [ ] Trainer test suite green (`pytest tests/training/test_candidate_e_stage1a_patches.py`)
- [ ] Evaluator test suite green (`pytest tests/evaluation/test_evaluate_candidate_e_stage2.py`)
