# Candidate E Stage 2 — locked launch commands (2026-05-12)

**Status:** E2a LAUNCHED + EVALUATED 2026-05-12 (run `stage_e2a_warmup_20260512T150330Z`). E2b unblocked — three new losses (L_span, L_contrastive_margin, L_coverage) wired, evaluator has fail-exit gates. **E2b ready to launch pending user pre-launch checks.**

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

## E2b launch command (READY — locked 2026-05-12)

`--ablation e2b` is unblocked. Loss weights at parse time:
```
lm=1.0  fr=1.0  slot_type=1.0  copy=0.5
phrase_bias_aux=0.1
span=1.0  contrastive_margin=0.5  coverage=0.1
```

E2b adds three new objectives on top of E2a:
- **L_span (1.0)** — within-span source-position adjacency (whole-ID discipline)
- **L_contrastive_margin (0.5)** — gold src vs hardest-non-gold negative (paired-ID pressure)
- **L_coverage (0.1)** — copy distribution entropy at STAGE_VAR positions (sharp source pointing)

Plus copy weight back ON at 0.5 (DEFAULT) — the existing pointer loss is the primary source-binding gradient; the three new terms add discipline / margin / decisiveness.

### Pre-launch user actions (same as E2a)

1. Sync files (training code + corpora; MD5-verify).
2. Resolve E2A checkpoint path on pod:
   ```bash
   ls -1dt /workspace/tksCAS/stage_e2a_warmup_*/ckpt_final.pt | head -3
   ```
   E2A ckpt from this PR's E2a run: `/workspace/tksCAS/stage_e2a_warmup_20260512T150330Z/ckpt_final.pt`
3. Confirm GPU idle.

### Launch block

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
E2A_CKPT=/workspace/tksCAS/stage_e2a_warmup_20260512T150330Z/ckpt_final.pt
test -f "$E2A_CKPT" || { echo "E2A_CKPT does not exist: $E2A_CKPT"; exit 1; }
OUT=/workspace/tksCAS/stage_e2b_full_${TS}

nohup python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_simplex_mvp.py \
  --data-path /workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl \
  --output-dir ${OUT} \
  --device cuda:0 \
  --d-model 384 --encoder-n-layers 4 --decoder-n-layers 6 \
  --encoder-n-heads 6 --decoder-n-heads 6 \
  --batch-size 16 --limit 100000 --n-steps 1000 \
  --lr 1e-4 --weight-decay 1e-4 --grad-clip 1.0 \
  --ablation e2b --max-cas-prefix-len 192 \
  --train-log-every-steps 50 \
  --tokenizer-path /workspace/tksCAS/stage6_v6_artifacts/tokenizer.json \
  --english-bpe-path /workspace/tksCAS/stage6_v6_artifacts/english_bpe.json \
  --sample-canary-at 1000 --sample-canary-post-training \
  --save-checkpoints-at 250,500,750,1000 --save-final-checkpoint \
  --canary-max-new-tokens 128 --seed 1729 \
  --load-model-from ${E2A_CKPT} \
  > ${OUT}.log 2>&1 &
```

**Note on canary schedule:** dropped to `--sample-canary-at 1000` only (one canary at end) per `feedback_canary_cost_dominates_short_runs.md` — mid-training canaries on the B-era pack add ~14 min each without informing E2b training behavior (we don't `--halt-on-canary-kill`). E2b run total wall: ~15-20 min instead of ~90 min.

## E2b evaluator command (READY)

Two fail-exit gates per design doc §Stage 2b:
- `dev_summary.full_recovery_rate >= 0.80` (exact ID recovery)
- `swap_summary.pair_pass_rate >= 0.85` (source-swap conditionality)

Evaluator returns exit code `2` on any gate miss; CI / shell scripts catch it.

```bash
EVAL_TS=$(date -u +%Y%m%dT%H%M%SZ)
EVAL_OUT=/workspace/tksCAS/eval_e2b_${EVAL_TS}

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
  --stage e2b \
  --gate-recovery 0.80 \
  --gate-swap 0.85
echo "evaluator_exit=$?"
```

If `evaluator_exit=0`: both gates passed — E2b promoted, Stage 3 (CAS-DAgger) can proceed.
If `evaluator_exit=2`: at least one gate missed — surface `evaluate_candidate_e_stage2_findings.md` for diagnosis. Per design doc §Stage 2b kill rule: do NOT proceed to Stage 3 if TF recovery stays near 30%; the data/labels are still wrong.

### Not yet in evaluator (deferred to follow-on PR)

Per user 2026-05-12 evaluator-upgrade scope decision: slot F1 against gold target slot tags + non-rpm leakage scoring against a non-rpm dev subset are deferred. The two gates above cover the user's stated requirements: "exact ID recovery and wrong-pair leakage." Slot F1 and non-rpm leakage scoring land in a follow-on evaluator PR when needed; they are NOT prerequisites for the E2b launch decision.

## E2b status — LANDED (2026-05-12 follow-up PR)

| Component | Status |
|---|---|
| Trainer: L_span, L_contrastive_margin, L_coverage in `compute_losses` | ✓ landed |
| Trainer: ABLATION_OVERRIDES["e2b"] activates the three weights | ✓ landed |
| Trainer: `_enforce_e2b_block` no longer raises on `e2b` | ✓ landed |
| Evaluator: `--stage e2b` no longer raises | ✓ landed |
| Evaluator: two fail-exit gates (dev recovery + swap pair pass) | ✓ landed |
| Evaluator: slot F1 + non-rpm leakage scoring | DEFERRED (not E2b-blocking) |
| Trainer: pair-aware batcher | NOT NEEDED (L_contrastive_margin is per-record with hard-negative within same source) |

L_contrastive_margin clarification: the original Stage 2 audit summary wrote "pair-aware batcher required for L_contrastive_margin." That over-specified the design doc, which actually says "correct source position scores higher than hard-negative source positions by margin m." Per-record contrastive within the same source — finding the most-confusable non-gold source position — provides the gradient without needing both pair members in the same batch. The swap-pair invariance is then VERIFIED at eval time via the existing `pair_cross_emission` metric, not enforced through batch sampling.

## What we are NOT doing in Stage 2 (after E2b lands)

- Slot F1 against gold target slot tags (deferred — not E2b-blocking)
- Non-rpm leakage scoring against a non-rpm dev subset (deferred — not E2b-blocking)
- TF entrypoint in the evaluator (`--tf-mode` reserved; free-decode is the primary falsification metric per A/B/C/D postmortem TF/free-decode divergence pattern)
- DAgger / on-policy training (Stage 3, gated on E2b gate verdict)

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
