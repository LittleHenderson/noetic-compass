# Vocab14 Retrain Runbook

Date authored: 2026-05-04
Patch: vocab14 (14 reserved CAS-literal tokens — meta-logic constructors, set-relation operators, bare v7.6 production-semantics symbols)
Patch test status: 20/20 new tests + 105/105 existing tokenizer tests + 14/14 train_structured_prediction tests passing
Hypothesis under test: closing the meta-logic vocabulary gap drops `meta_relations` head failure on the meta_logic bucket from 53.6% (K9_DiagLoop honest) toward <30%.

This is a one-shot retrain. No other levers (graph encoder, bare-template paraphrase, self-conditioning) move in this run. Lever 3 is expected to land before this fires; if Lever 3 is folded in, that's covered under Decision (b) in the prep memo.

## Pre-flight checklist

Run each item in order. Do NOT proceed to the training command until every item is GREEN.

1. Pod state
   - [ ] RunPod RTX A6000 reachable; SSH or Web Terminal works.
   - [ ] `nvidia-smi` shows ≥40 GB free VRAM (the 20-epoch K=9 baseline used ~12 GB peak).
   - [ ] At least 80 GB free disk in `/workspace/` (training + checkpoints + eval artifacts).

2. Repository state
   - [ ] `cd /workspace/tksCAS` and `git status` is clean OR the only diff is the vocab14 patch (`cas-native/tokenizer/{__init__,cas_notation,vocabulary}.py` and `cas-native/tests/tokenizer/test_reserved_cas_tokens.py`).
   - [ ] If on a feature branch, branch is `vocab14-retrain` (or whatever your local convention is); rebase against origin/master if needed.
   - [ ] Patch applied. Verify with `git diff HEAD --stat -- cas-native/tokenizer/` — expect `116 insertions(+), 6 deletions(-)`.

3. Patch verification on the pod
   - [ ] `cd /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native && python -m pytest tests/tokenizer/test_reserved_cas_tokens.py tests/tokenizer/ -q` — 99 passed.
   - [ ] `python -m pytest tests/test_train_structured_prediction.py -q` — 10 passed.

4. Training data
   - [ ] `ls /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl` exists, ~19,454 records.
   - [ ] `ls /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` exists, 1,000 records. **Do NOT use `level3_recoverable_eval_1000.jsonl` (no `_v77_relabeled` suffix); see `feedback_eval_file_slip_recurrent.md`.**

5. Output directory
   - [ ] Pick run name: `structured-token-vocab14-20epoch-gpu-YYYYMMDD-HHMM`. Confirm it does NOT collide with an existing run dir under `cas-native/training/runs/`.

## Exact training command

This mirrors the K=9 baseline command (`STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md` from run `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`) with two changes:

- **Eval file is the v77-relabeled version** (per `feedback_eval_file_slip_recurrent.md`). The K=9 baseline command used the non-relabeled eval; switch to relabeled here so the headline numbers are directly comparable to the K9_DiagLoop_full_v2_honest reference numbers in `docs/working/v76_meta_logic_deep_dive_2026_05_04.md`.
- **`--limit 100000`** (per `feedback_limit_default_128_trap.md`) — explicit, do not rely on default.

```bash
cd /workspace/tksCAS

# Use a short variable for the run dir to keep the command grokkable.
RUN=structured-token-vocab14-20epoch-gpu-$(date +%Y%m%d-%H%M)

python3 -u /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py \
  --input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl \
  --limit 100000 \
  --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --input-mode structured_token \
  --epochs 20 \
  --batch-size 128 \
  --d-model 128 \
  --bottleneck-dim 64 \
  --lr 0.001 \
  --weight-decay 0.0001 \
  --device cuda \
  --seed 42 \
  --max-length 256 \
  --vocab-min-count 1 \
  --paraphrase-augment-train 3 \
  --out-dir /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN \
  2>&1 | tee /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN.log
```

Notes on flags:
- `--paraphrase-augment-train 3` matches the K=9 baseline (49,710 paraphrases + 16,570 canonicals = 66,280 total).
- `--vocab-min-count 1` is unchanged. The 14 reserved CAS tokens are seeded regardless of this setting (they are NOT count-gated).
- `--seed 42` matches the K=9 baseline. Reproduces eval-overlap filter, paraphrase augmentation, and shuffle order.

## Expected wall-clock and disk

Hardware: RunPod RTX A6000.

Estimate sources: K=9 baseline run took ~70 min wall (per the train.log timestamps in `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`). Vocab14 grows the embedding table by 14 rows × 128 dims = +1,792 parameters; this is negligible (<0.01% of the model). No other path changes. Wall-clock estimate: **~75-90 minutes** (tokenization is unchanged in cost; embedding lookup is unchanged in cost; only vocab size differs by 14 rows).

Allow up to **2 hours** including pre-flight, post-eval, and artifact upload.

Disk usage:
- Per-epoch checkpoint (20 epochs): ~15 MB each (checkpoint disk usage) → typically only `best_structured_token_model.pt` is kept (~15-20 MB).
- Eval artifacts (sample JSONLs, confusion matrices): ~30-50 MB.
- Train log: ~5-10 MB.
- **Total: ~80-100 MB per run.**

## Expected vocab size after training

Pre-patch (K=9 baseline): 293
Post-patch (vocab14): **307** (= 293 + 14)

Confirm with:
```bash
python3 -c "import json; v=json.load(open('/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/structured_token_vocab.json')); print('vocab_size:', len(v['token_to_id'])); print('reserved_cas tokens present:', sum(1 for t in ['cas:NoeticCluster','cas:StateSet','cas:StateCluster','cas:RelationCluster','cas:CoverOf','cas:PartitionOf','cas:Product','cas:∪','cas:∩','cas:∈','cas:⊆','cas:Λ','cas:Ω','cas:Θ'] if t in v['token_to_id']))"
```
Expected output: `vocab_size: 307` and `reserved_cas tokens present: 14`.

If the vocab size is not 307, abort the eval and investigate — most likely cause is patch not fully applied or the training script using a different vocabulary build path.

## Pre-committed pass/fail criteria

Headline metric: meta_relations head failure rate on the meta_logic bucket of the **honest two-pass eval** on `level3_recoverable_eval_1000_v77_relabeled.jsonl`.

Reference: K9_DiagLoop_full_v2_honest reports meta_logic meta_relations failure at **53.6%** (164/306 — note the eval there had 306 meta_logic records; this run uses the v77_relabeled 1000-record split which has 102 meta_logic records, so absolute counts differ but the rate is comparable).

| Outcome | meta_relations failure | Interpretation | Next action |
|---|---|---|---|
| **PASS** | < 30% | Vocab gap was the dominant constraint; meta_logic is now solvable with the existing K=9 architecture. | Land vocab14 to master. Move on to Lever 3 + graph-encoder hypotheses for v76. |
| **HALF-PASS** | 30-45% | Vocab gap was contributory and material, but secondary architectural constraints remain. | Land vocab14 to master, then run a follow-up combining vocab14 + graph encoder enlargement. Document the partial improvement in Paper A v2 §5.7. |
| **FAIL** | > 45% | Vocab gap was not the load-bearing constraint. Multi-operand routing or graph-encoder undersizing is the actual bottleneck. | Do NOT land vocab14 to master automatically; first re-examine the multi-operand routing hypothesis (the open question in `v76_meta_logic_deep_dive_2026_05_04.md` H2). Vocab14 may still be worth landing as a small additive gain, but it's not the answer. |

Secondary metric (track but not load-bearing): meta_logic bucket all_heads_exact rate. K=9 baseline (paraphrase eval) was 78.4%. K9_DiagLoop_full_v2_honest was 19.6%. Expect vocab14 to lift the honest meta_logic all_heads_exact rate **proportionally** to the meta_relations improvement (since meta_relations is the dominant per-head failure on this bucket).

Tertiary metric (track but not load-bearing): v76_production noetic head failure. Vocab14 includes `cas:Λ`, `cas:Ω`, `cas:Θ` which are v7.6 production-semantics tokens. Some incidental v76 lift may appear; if v76 noetic head improves >5pp, document it in the post-eval report.

Aggregate sanity: all_heads_exact_rate on the full 1000-record eval should be roughly comparable to K=9 baseline (86.8%). A regression below 80% indicates the vocab change is hurting other buckets — likely cause is the ID-shift (existing baseline tokens that were at IDs 8-292 moved to 22-306) breaking downstream consumers, but since we train from scratch this should be a non-issue.

## Honest eval command (post-training)

The training script's per-epoch eval uses paraphrase-only mode by default. The honest two-pass eval (canonical + paraphrase, with both passes contributing) is what matches the K9_DiagLoop_full_v2_honest reference numbers. Use the standard eval-only invocation:

```bash
# After training completes, invoke train_structured_prediction.py in eval-only mode
# (it auto-loads the best checkpoint and writes paraphrase + canonical eval reports
# to the run dir).
python3 -u /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py \
  --input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl \
  --limit 100 \
  --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
  --input-mode structured_token \
  --epochs 0 \
  --eval-only \
  --resume /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/best_structured_token_model.pt \
  --device cuda \
  --out-dir /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN
```

Verify `--eval-only` and `--resume` flag names against the current `train_structured_prediction.py` argparse; they may need adjustment if the script's CLI is slightly different. The training run already produces `paraphrase_relabeled_eval_report.json` and `relabeled_eval_*.json` artifacts, so the in-run eval may be sufficient. If those artifacts already cover the honest two-pass meta_relations metric for the meta_logic bucket, skip the explicit eval-only re-run.

Pull the meta_logic per-head accuracy out of the report:
```bash
python3 -c "import json; r = json.load(open('/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/paraphrase_relabeled_eval_report.json')); print(json.dumps(r['by_bucket']['meta_logic']['per_head_acc'], indent=2))"
```

`meta_relations` accuracy here is `1 - failure_rate`. Compute failure rate as `1 - meta_relations` and compare to the 53.6% reference. Note that the run's per-bucket eval is paraphrase-eval; the honest two-pass numbers come from a separate honest_eval invocation that the K9_DiagLoop_full_v2_honest run produced. If the honest_eval pipeline is not available in this run dir, accept the paraphrase-eval number as a leading indicator and queue the honest_eval as a follow-up.

## Resume / rollback procedure

If the patch needs to be reverted:

```bash
# Local rollback (git-clean revert, working copy):
cd /workspace/tksCAS
git checkout -- noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/__init__.py
git checkout -- noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/cas_notation.py
git checkout -- noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/vocabulary.py
rm noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/test_reserved_cas_tokens.py
```

If the patch was committed and needs reverting after merge:

```bash
git revert <patch-commit-sha>
```

The patch is reversible — `git stash` of the three modified files cleanly restores pre-patch behavior (verified during patch authoring on 2026-05-04). The previously-trained vocab artifact (`structured_token_vocab.json` at 293 entries) is bit-identical to the pre-patch state.

Note: a vocab artifact trained under the vocab14 patch is **not** compatible with code at pre-patch state. Loading a 307-entry vocab into the pre-patch `__post_init__` will raise (because pre-patch only validates the 8 reserved special tokens, not the 14 reserved CAS tokens; but it does enforce contiguity, so a 307-entry vocab still loads cleanly into pre-patch code — just without the seeded-at-stable-IDs guarantee). The rollback is one-directional: revert code, retrain. Do not mix patched code with patched checkpoints across the boundary.

## After the run

1. Update `CHANGELOG.md` with: run name, date, hypothesis under test, pass/fail outcome, headline metric.
2. Add the bucket and per-head numbers to a new memo at `docs/working/vocab14_retrain_results_YYYY_MM_DD.md`.
3. If PASS: open a PR for the patch. If HALF-PASS: open a PR with caveats noted in the description. If FAIL: do NOT open a PR; document in the results memo and re-examine the architectural-constraint hypothesis.
4. Note in `MEMORY.md`: outcome of the vocab14 retrain and what it tells us about the meta_logic constraint structure.
