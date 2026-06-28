# Combined Retrain Runbook — v1 Demoable Model

Date authored: 2026-05-04
Branch (target): `combined-v1-retrain` (cherry-picks PR #33 vocab14 + PR #34 demographic-tonal + Lever 3 paired data drop)
Hypothesis under test: the combination of (vocab14 closing the meta-logic vocabulary gap) + (Lever 3 paired free-form English) + (demographic-tonal K=4 surface expansion) lifts the K=9 baseline from a structurally-correct-but-narrow-voice prediction model to a v1 demoable model that holds canonical exact ≥92%, paraphrase invariance ≥65%, meta_logic ≥30%, v76_production ≥50%, and is within 10pp on the worst demographic stratum.

This is a **single combined retrain** that folds three independent levers into one pod-run. The decision to combine rather than stage them is in `vocab14_prep_memo_2026_05_04.md` (Decision (b)) and is justified by per-bucket disjointness of the three levers' targets.

## 1. Executive Summary

- **Delivers:** a v1 candidate model that has been simultaneously exposed to (a) reserved CAS-literal tokens for meta-logic constructors and v7.6 production-semantics symbols (PR #33), (b) ~5K Claude-rewritten paired free-form English prompts that share canonical labels with their training-surface peers (Lever 3), and (c) K=4 demographic + tonal surface variants per training canonical (PR #34). The same model is then evaluated on the original held-out 1K and on a demographic-stratified version of the same held-out 1K, against five pre-committed pass/fail criteria.
- **Cost / time:** single RTX A6000 (48GB) on a fresh RunPod. Wall-clock estimate ~4–6 hours from pod-up to land/rollback decision: ~10 min stage-1 corpus build, ~3–5 hours training, ~25 min combined eval + post-mortem. Total cost on RunPod's published rate: ≤ $5.
- **Expected outcome ranges:** PASS on canonical (high-prob; the model trained the K=9 baseline at 88.6% canonical exact and the levers are additive on training set size). HALF-PASS on paraphrase invariance (medium-prob; Lever 3 is the relevant lever and 5K records is small relative to 19.5K canonicals). HALF-PASS on meta_logic (median expectation per `vocab14_prep_memo_2026_05_04.md`). HALF-PASS or FAIL on v76_production (the architectural multi-operand routing is not addressed by any lever in this pass). PASS on demographic-robustness gate (K=4 expansion of the training corpus is the gate's canonical input, and the gate's tolerance has not yet been calibrated tighter than 10 pp).

## 2. Pre-flight Checklist

Run each item in order. Do NOT proceed to stage 1 until every item is GREEN.

### 2.1 Lever 3 paired data must be present and clean
- [ ] `ls cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl` exists. (NOT the `.partial.jsonl` sibling.) Expected ~5,000 records.
- [ ] `wc -l cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl` returns ≥ 4,800 (allow up to 4% drop from validation failures, per `lever3_script_completion_2026_05_04.md`).
- [ ] The 50-record calibration JSONL exists and was reviewed: `cas-synthetic/data/level2_scaffold/lever3_paired_freeform_calibration_50.jsonl`. Spot-check 10 records for tone naturalism, no leak of `^`, `|T/A/f/E`, `F1..F7`, `CO-`, the words `cas`/`noetic`/`domain`/`drive`/`register`. If >2/10 leak any disallowed token, abort and regenerate that bucket of Lever 3.
- [ ] Eval-overlap audit: `python -c "import json; train_ids = {json.loads(line)['source_level2_id'] for line in open('cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl')}; eval_ids = {json.loads(line)['source_level2_id'] for line in open('cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl')}; print('overlap:', len(train_ids & eval_ids))"`. Expected: `overlap: 0`. Any non-zero overlap is a HARD ABORT — Lever 3 generator's eval-overlap filter (per `generate_lever3_paired_freeform.py:40-44`) was bypassed and the run cannot proceed.
- [ ] Per-bucket count audit: `python -c "import json; from collections import Counter; print(Counter(json.loads(line)['bucket'] for line in open('cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl')))"`. Expected: each of the six buckets (v74_baseline, v75_register, v76_production, v77_omega, v77_rule_four, meta_logic) ≥ 750. If any bucket is severely under-represented (< 600), the Lever 3 contribution to that bucket's paraphrase invariance is too thin; flag in the post-mortem but do not abort.

### 2.2 Patches must be in the working tree
- [ ] PR #33 (vocab14): branch `fix/vocab14-reserved-tokens` is either merged to `master` OR the runbook branch (`combined-v1-retrain`) was rebased onto it. Verify with `git log --oneline -- noetic-compass-scaffold/noetic-compass/cas-native/tokenizer/vocabulary.py | head -5` and look for the vocab14 commit (the diff should show the `RESERVED_CAS_TOKENS` constant). 99/99 tokenizer tests must pass: `cd noetic-compass-scaffold/noetic-compass/cas-native && python -m pytest tests/tokenizer/ -q`.
- [ ] PR #34 (demographic-tonal): files `cas-synthetic/generator/demographic_tonal_axes.py`, `cas-synthetic/generator/demographic_tonal_rewrite.py`, `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py`, and `cas-native/evaluation/demographic_robustness_eval.py` are present. 12/12 robustness tests pass: `cd noetic-compass-scaffold/noetic-compass && python -m pytest cas-native/evaluation/tests/test_demographic_robustness_eval.py -q`. Driver expansion test: `cd cas-synthetic && python -m pytest tests/test_demographic_tonal.py -q`.
- [ ] Combined sanity: `python -m pytest cas-synthetic/tests/ noetic-compass-scaffold/noetic-compass/cas-native/tests/tokenizer/ noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/ -q`. All green.

### 2.3 Pod state
- [ ] RunPod RTX A6000 (48GB) reachable; `nvidia-smi` shows ≥ 40 GB free VRAM.
- [ ] At least 100 GB free disk in `/workspace/` (78–100K-record demographic-expanded JSONL is ~150–200 MB; training checkpoints, eval artifacts ~100 MB; logs ~30 MB; total < 1 GB but reserve more for parallel runs).
- [ ] `pip show torch | grep -i version` shows torch 2.5+ with cu124 build (`pip install torch --index-url https://download.pytorch.org/whl/cu124` if not).
- [ ] `pip show anthropic` shows the SDK is installed (used by Lever 3 generator only; not strictly required at retrain time, but pre-flight verifies a working env in case Lever 3 needs a top-up).
- [ ] CUDA smoke: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"` returns `True ... A6000`.

### 2.4 Repo state on pod
- [ ] `cd /workspace/tksCAS && git status` is clean OR diff is limited to the combined-v1-retrain branch's expected files.
- [ ] `git log --oneline -10` shows the latest commits include both vocab14 and demographic-tonal files. (Spot-check for `RESERVED_CAS_TOKENS` and `demographic_tonal_axes.py` referenced.)
- [ ] CHANGELOG up to date with a Session 53 entry naming the combined retrain. If absent, add a stub entry now.

### 2.5 Authoritative eval file
- [ ] `ls cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` exists, 1,000 records. **Do NOT use the non-relabeled `level3_recoverable_eval_1000.jsonl`** (per `feedback_eval_file_slip_recurrent.md` — this slip recurs across agents). Always grep for the `_v77_relabeled` suffix before launching anything.

### 2.6 Run-name convention
- [ ] Pick run name: `RUN=combined-v1-vocab14-lever3-demographic-K4-20epoch-gpu-$(date +%Y%m%d-%H%M)`. Confirm directory does not exist under `noetic-compass-scaffold/noetic-compass/cas-native/training/runs/`.

## 3. Stage Sequence

### Stage 1 — Build the merged training corpus (CPU-bound, ~10 min)

The merged corpus is built in three substeps: (a) v77 relabel of the canonicals, (b) merge canonicals + Lever 3, (c) K=4 demographic-tonal expansion. The first and third substeps already have scripts; the second needs a small new script (~50 lines, see note below) which is documented inline.

```bash
cd /workspace/tksCAS

# (a) v77 relabel of canonicals (idempotent; produces level3_recoverable_full_v77_relabeled.jsonl).
python cas-synthetic/scripts/relabel_v77_overlap.py \
    --in cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
    --out cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl
# Expected: ~19,454 input → ~19,454 output (same count; relabeling is in-place per record).

# (b) Merge canonicals (v77-relabeled) + Lever 3 paired data into a single combined JSONL.
# Note: merge_corpora.py does NOT exist yet. It is a follow-on script (~50 lines) that:
#   1. opens --canonical and --lever3 in append-only mode,
#   2. emits every canonical record verbatim,
#   3. emits every Lever 3 record verbatim,
#   4. dedupes on (id, source_level2_id, cas_expression) joint key (Lever 3 keeps a
#      separate ID space so dedup typically returns 0 collisions),
#   5. writes a manifest json with input_paths, output_path, record_count, dedup_dropped.
# Until this script lands, a one-liner is:
cat \
    cas-synthetic/data/level2_scaffold/level3_recoverable_full_v77_relabeled.jsonl \
    cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl \
    > cas-synthetic/data/level2_scaffold/level3_combined_v1.jsonl
# Expected: ~24,454 records (19,454 canonicals + ~5,000 Lever 3).

# Optional: include the Phase 3 free-form English generator output if it has landed
# before this stage runs. See Section 8 for the sequencing rule. If it has landed,
# include it in the cat above; otherwise omit.

# (c) K=4 demographic-tonal expansion.
python cas-synthetic/scripts/expand_jsonl_demographic_tonal.py \
    --input cas-synthetic/data/level2_scaffold/level3_combined_v1.jsonl \
    --output cas-synthetic/data/level2_scaffold/level3_combined_v1_demographic_K4.jsonl \
    --variants-per-canonical 4 \
    --seed 42 \
    --progress-every 5000
# Expected: ~24,454 × 4 = ~97,816 records out. Script prints a summary block with
# profile_counts, tone_counts, pair_counts; verify each profile got ~12,200 ± 500
# records and each tone got ~19,500 ± 500 records (per the K=4 stratified-sampling
# guarantees in sdg_demographic_tonal_spec_2026_05_04.md §3).

# (d) Joint-key eval-overlap audit on the FINAL combined-and-expanded corpus.
python -c "
import json
train_keys = set()
with open('cas-synthetic/data/level2_scaffold/level3_combined_v1_demographic_K4.jsonl') as f:
    for line in f:
        r = json.loads(line)
        # demographic variants share source_level2_id with their canonical, so audit
        # against source_level2_id, not the per-variant id.
        train_keys.add(r.get('source_level2_id'))
with open('cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl') as f:
    eval_keys = {json.loads(l).get('source_level2_id') for l in f}
print('train|source ids:', len(train_keys))
print('eval|source ids:', len(eval_keys))
print('overlap:', len(train_keys & eval_keys))
"
# Expected: overlap: 0. Any non-zero is a HARD ABORT.
```

Disk after stage 1: ~250 MB total for the four JSONLs.

### Stage 2 — Verify vocab14 patch is wired

Vocab14 lives in `cas-native/tokenizer/{__init__.py, cas_notation.py, vocabulary.py}`. The training script picks it up automatically because `train_structured_prediction.py` calls `StructuredTokenVocabulary.from_token_sequences(...)` which seeds `RESERVED_CAS_TOKENS` after the special tokens before frequency-sorted corpus tokens. No retrain-time configuration toggles vocab14 on or off — it's purely structural.

```bash
# Quick patch verification (mirrors the equivalent step in vocab14_retrain_RUNBOOK_2026_05_04.md):
cd /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native
python -m pytest tests/tokenizer/test_reserved_cas_tokens.py -q  # 20/20
python -m pytest tests/tokenizer/ -q                              # 99/99
python -m pytest tests/test_train_structured_prediction.py -q     # 10/10
```

If any test fails, abort and investigate. The 99/99 tokenizer tests are load-bearing for the vocab14 patch's correctness.

### Stage 3 — Launch training (~3-5 hours on A6000)

The training command extends the K=9 baseline command (`STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md` from run `structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045`) with three changes:

- **Input** is the demographic-K=4 expansion of the merged corpus (Stage 1c output).
- **`--paraphrase-augment-train 9`** raises augmentation from K=9 baseline's 3 to 9 (per `project_k9_baretemplate_partial_success_2026_05_02.md`'s K=9 + bare-slot template line; this lever has tested-positive on per-head exact lift).
- **NO `--diagram-loop-pairs`** flag. Diagloop is deprecated per outcome C in the v76 deep-dive memo; this run is K=9 architecture only.

```bash
cd /workspace/tksCAS

RUN=combined-v1-vocab14-lever3-demographic-K4-20epoch-gpu-$(date +%Y%m%d-%H%M)

nohup python3 -u /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py \
    --input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_combined_v1_demographic_K4.jsonl \
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
    --paraphrase-augment-train 9 \
    --out-dir /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN \
    > /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN.log 2>&1 &

echo "Launched as PID $!"
echo "Tail with: tail -f /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN.log"
```

Notes on flags (cross-check against vocab14_retrain_RUNBOOK_2026_05_04.md):

- `--limit 100000` is explicit per `feedback_limit_default_128_trap.md`. Default 128 will silently produce a useless run.
- `--paraphrase-augment-train 9` is the K=9 setting; this means each canonical contributes itself + 9 paraphrase variants on the structured-token training side. With ~98K records before this multiplier, expect the actual number of training "tokens-batched-in" to be ~98K × (1 + 9) = ~980K records, but `--limit 100000` caps to 100K records pre-paraphrase-augment, so effective training corpus is 100K × 10 = 1M paraphrase-augmented records. That's substantially larger than the K=9 baseline's 19.5K × 4 ≈ 78K. Re-check epoch-count budget below.
- Wall-clock estimate: K=9 baseline (19.5K × 4 = 78K records, 20 epochs) ran ~70 min. This run is ~13× more records. Expected wall-clock: **~3-5 hours**. The A6000 has ~2× the K=9 baseline's compute throughput, so the linear scaling is partially absorbed. If the run exceeds 6 hours wall, kill it and reduce `--epochs` to 12.
- `--paraphrase-augment-train 9` — the optimal-for-K=9-baseline. The bare-template at K=9 was a NET −2.2 pp on aggregate paraphrase exact (per `project_k9_baretemplate_partial_success_2026_05_02.md`). The combined retrain DOES NOT include the bare-template lever. K=9 is a quantity-of-augmentation knob, not a template-content knob.

### Stage 4 — Standard eval on held-out 1K (~10 min)

The training script's per-epoch eval already produces `paraphrase_relabeled_eval_report.json` and `relabeled_eval_*.json` in the run dir. Verify the artifacts exist:

```bash
ls /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/
# Expected: best_structured_token_model.pt, structured_token_vocab.json,
#           paraphrase_relabeled_eval_report.json, relabeled_eval_samples.jsonl,
#           train.log, manifest.json.
```

Pull headline metrics:

```bash
python3 << 'EOF'
import json, os
RUN_DIR = os.environ.get('RUN_DIR') or '/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/' + os.environ['RUN']
with open(f'{RUN_DIR}/paraphrase_relabeled_eval_report.json') as f:
    r = json.load(f)
print('===== HEADLINE =====')
print(f"all_heads_exact_rate (paraphrase): {r['all_heads_exact_rate']:.4f}")
for bucket, stats in r['by_bucket'].items():
    print(f"  {bucket}: exact={stats['all_heads_exact_rate']:.4f} per_head={stats['per_head_acc']}")
EOF
```

Confirm vocab size:
```bash
python3 -c "import json,os; v=json.load(open(os.environ['RUN_DIR']+'/structured_token_vocab.json')); print('vocab_size:', len(v['token_to_id'])); reserved=['cas:NoeticCluster','cas:StateSet','cas:StateCluster','cas:RelationCluster','cas:CoverOf','cas:PartitionOf','cas:Product','cas:∪','cas:∩','cas:∈','cas:⊆','cas:Λ','cas:Ω','cas:Θ']; print('reserved present:', sum(1 for t in reserved if t in v['token_to_id']))"
# Expected: vocab_size > 307 (corpus tokens grow with combined corpus); reserved present: 14.
```

If `reserved present` is not 14, abort the eval and investigate — vocab14 patch was not wired or was reverted.

### Stage 5 — Demographic-tonal stratified eval (~10 min)

First, build the demographic-stratified version of the held-out eval (this happens AT eval time, NOT pre-baked, because the eval is held-out and was not part of the SDG corpus):

```bash
python cas-synthetic/scripts/expand_jsonl_demographic_tonal.py \
    --input cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
    --output cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled_demographic_K4.jsonl \
    --variants-per-canonical 4 \
    --seed 4242   # NB: distinct seed from training expansion to avoid per-record-pair correlations
# Expected: 1000 × 4 = 4000 records out.
```

Run the demographic-robustness eval gate:

```bash
python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py \
    --checkpoint /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/best_structured_token_model.pt \
    --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled_demographic_K4.jsonl \
    --tolerance-pp 10 \
    --out-json /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/demographic_robustness_report.json \
    --out-markdown /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/demographic_robustness_report.md \
    --device cuda

# Exit 0 = PASS gate (verdict.passed = True); exit 1 = FAIL gate.
echo "Demographic robustness gate exit: $?"
```

Surface key numbers:

```bash
python3 << 'EOF'
import json, os
RUN_DIR = '/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/' + os.environ['RUN']
with open(f'{RUN_DIR}/demographic_robustness_report.json') as f:
    v = json.load(f)
print('===== DEMOGRAPHIC =====')
print(f"verdict.passed: {v['passed']}")
print(f"population mean rate: {v['population_mean_rate']:.4f} (n={v['population_n']})")
print(f"tolerance_pp: {v['tolerance_pp']}")
print(f"failing_strata ({len(v['failing_strata'])}):")
for s in v['failing_strata']:
    print(f"  {s['stratum_label']}: rate={s['rate']:.4f} delta_pp={s['delta_pp']:.2f} n={s['n']}")
# Compute worst stratum gap regardless of pass/fail:
all_strata = v.get('per_profile', []) + v.get('per_tone', [])
worst = min(all_strata, key=lambda s: s['delta_pp'], default=None)
if worst:
    print(f"worst stratum overall: {worst['stratum_label']} delta={worst['delta_pp']:.2f}pp n={worst['n']}")
EOF
```

### Stage 6 — Honest assessment + decision

Apply the pass/fail criteria in Section 4 strictly. Land, refine, or rollback per Section 5.

## 4. Pre-committed Pass/Fail Criteria

Five axes; each must clear at least HALF-PASS for the model to be accepted as v1-rc, and all must clear PASS for v1.

| Axis | PASS | HALF-PASS | FAIL |
|---|---|---|---|
| **Canonical exact** (canonical-only eval, all 1K records, all_heads_exact) | ≥ 92% | 88–92% | < 88% |
| **Paraphrase invariance** (paraphrase eval, all 1K records, all_heads_exact rate; with self-prior if available else default) | ≥ 65% | 50–65% | < 50% |
| **meta_logic per-bucket all_heads_exact** (paraphrase eval, n=102) | ≥ 30% | 20–30% | < 20% |
| **v76_production per-bucket all_heads_exact** (paraphrase eval, n=108) | ≥ 50% | 35–50% | < 35% |
| **Demographic robustness** — worst single-axis (per-profile OR per-tone) stratum delta vs population mean | within 10 pp | 10–15 pp gap | > 15 pp gap |

Decision rules:

- **All 5 PASS** → land as v1; demo to outsiders; queue Paper A v2 §5.7 update.
- **Any HALF-PASS, no FAIL** → land as v1-rc on a pre-release tag; demo to internal-only; queue follow-on lever for the failing axis (mapping in §5).
- **Any FAIL** → DO NOT LAND. Rollback per §5; document the negative result in CHANGELOG and `combined_retrain_results_2026_05_05.md`.

The headline metric for the v1 release decision is **canonical exact**. A canonical-exact regression below 88% indicates that one of the three levers materially hurt the model's structured-token prediction core — most likely cause is the demographic K=4 expansion overweighting surface noise. A canonical FAIL is the single highest-cost outcome and requires a targeted rerun without the demographic expansion.

The most-controversial pre-committed criterion is **meta_logic ≥ 30%**. The vocab14 prep memo (`vocab14_prep_memo_2026_05_04.md`) puts median expectation at 30–45% meta_relations *failure* (i.e. 55–70% accuracy on the meta_relations head specifically). But all_heads_exact is a stricter all-of-N gate: even with meta_relations at 60% accuracy, the bucket's all_heads_exact requires all 8 heads to be simultaneously correct. Empirically, K9_DiagLoop honest meta_logic all_heads_exact was 19.6%; the deep-dive memo expects vocab14 to lift this proportionally to the meta_relations improvement. 30% all_heads_exact is approximately a 50% relative lift — aggressive but not unreasonable given the deep-dive memo's "half-pass for sure, full-pass with luck" framing.

## 5. Rollback Procedure

If any axis FAILs:

1. **Do not merge any of the trained-checkpoint commits to master.** The combined-v1-retrain branch stays as a development branch only.
2. **Document the negative result.** Write `docs/working/combined_retrain_results_2026_05_05.md` (publishable like the diagloop outcome-C verdict) with: which axis failed, by how much, the candidate root cause from the table below, and the recommended next experiment.
3. **Keep the K=9 baseline as production.** The K=9 baseline checkpoint at `runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/best_structured_token_model.pt` remains the production model.
4. **Identify which axis failed and consult the corresponding lever.** Mapping (axis → most likely root cause → next lever):
   - **Canonical regression (FAIL: < 88%)**: vocab14 ID-shift caused embeddings to learn the new layout but the base layer sizes are constrained. Most likely a quantity-of-augmentation issue from K=4 demographic expansion overweighting demographic noise vs canonical signal. Next lever: regenerate without `--paraphrase-augment-train 9` (back to K=3) and without demographic expansion; retain only vocab14 + Lever 3.
   - **Paraphrase regression (FAIL: < 50%)**: Lever 3 data quality issue — most likely Lever 3 paraphrases are systematically more divergent from training-surface than the demographic-tonal variants are from the merged corpus, so the model overfits to demographic-tonal style and regresses on Lever 3-style colloquial English. Next lever: regenerate Lever 3 with stricter validation filter (e.g., bound each paraphrase length to `original_length × [0.6, 1.6]`, reject paraphrases with sentence count > 3, reject Type B 3rd-person frame leaks).
   - **meta_logic regression (FAIL: < 20%)**: vocab14 was contributory but graph encoder undersizing dominates. Escalate to architectural-constraint hypothesis (graph encoder hidden dim 64 → 128 enlargement, per `v76_meta_logic_deep_dive_2026_05_04.md` E2). Note: the diagloop graph encoder is deprecated per outcome C, but a vanilla graph-encoder enlargement on K=9 architecture is the next experiment.
   - **v76_production regression (FAIL: < 35%)**: multi-operand routing failure (the architectural problem identified in `v76_meta_logic_deep_dive_2026_05_04.md` H2). No lever in this combined retrain addresses it. Next lever: E3 from the deep-dive memo (auxiliary first-operand pointer loss on v76 records).
   - **Demographic gap (FAIL: > 15 pp)**: Path A rule-based rewriter is not naturalistic enough on the failing profile (most likely P2 academic or P4 L2-indirect, per `sdg_demographic_tonal_spec_2026_05_04.md` §7). Escalate to Path B: regenerate ONLY the failing (profile, tone) cells through Claude (`expansion_method = "claude_v1"`).

5. **Tag the failed checkpoint** with `git tag combined-v1-fail-<axis>-2026-05-05` so the negative-evidence checkpoint stays addressable for diagnosis runs without polluting master.

If multiple axes FAIL simultaneously: prioritize canonical (highest signal) → meta_logic (vocab14 hypothesis test) → demographic (cheapest to fix). Do NOT attempt joint-lever fixes (e.g., graph encoder + Path B Claude rewrites in the same run); each next experiment must be a one-variable change to preserve attribution.

## 6. Eval Commands (Fully Specified, Copy-Pasteable)

### 6.1 Standard eval (canonical + paraphrase, on held-out 1K)

The training run already produces `paraphrase_relabeled_eval_report.json` per epoch (best-of). To run an explicit re-eval (e.g., after a checkpoint adjustment or to confirm the headline numbers off-line):

```bash
cd /workspace/tksCAS

python3 -u /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py \
    --input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_combined_v1_demographic_K4.jsonl \
    --limit 100 \
    --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl \
    --input-mode structured_token \
    --epochs 0 \
    --eval-only \
    --resume /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/best_structured_token_model.pt \
    --device cuda \
    --out-dir /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN
```

(Verify `--eval-only` and `--resume` flag names against the current `train_structured_prediction.py` argparse; if not present, the in-run artifacts are sufficient. Same caveat as in `vocab14_retrain_RUNBOOK_2026_05_04.md`.)

### 6.2 Demographic-robustness gate eval

Already covered in §3.5 above. Repeating here for completeness:

```bash
python /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py \
    --checkpoint /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/best_structured_token_model.pt \
    --eval-input /workspace/tksCAS/cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled_demographic_K4.jsonl \
    --tolerance-pp 10 \
    --out-json /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/demographic_robustness_report.json \
    --out-markdown /workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/$RUN/demographic_robustness_report.md \
    --device cuda
```

Per `task_69_demographic_robustness_completion_2026_05_04.md` §5, the 10 pp tolerance is a placeholder, NOT a calibrated threshold. After this combined retrain, the v1 calibration step is to record the worst observed Δ on this run and set future runs' `--tolerance-pp = max(5, |worst observed Δ| + 5)`.

### 6.3 Per-bucket per-head extraction

```bash
python3 << 'EOF'
import json, os
RUN_DIR = '/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/' + os.environ['RUN']
with open(f'{RUN_DIR}/paraphrase_relabeled_eval_report.json') as f:
    r = json.load(f)
print(f"{'bucket':<18} {'n':>5} {'exact':>8} | per-head failures (>5%)")
for bucket, stats in sorted(r['by_bucket'].items()):
    failing_heads = sorted(
        [(h, 1 - acc) for h, acc in stats['per_head_acc'].items() if (1 - acc) >= 0.05],
        key=lambda x: -x[1],
    )
    print(f"{bucket:<18} {stats['n']:>5} {stats['all_heads_exact_rate']:>8.4f} | "
          + ', '.join(f'{h}={f:.2%}' for h, f in failing_heads))
EOF
```

This is the canonical view used for the meta_logic and v76_production criteria in §4.

## 7. Honest Expectations

Subjective probability allocation (no sandbagging):

| Outcome | Probability |
|---|---|
| All 5 PASS (clean v1) | **15%** |
| 1–2 HALF-PASS, no FAIL (v1-rc, ship to internal demos) | **45%** |
| 3+ HALF-PASS, no FAIL (v1-rc, with caveats) | **15%** |
| Any FAIL (rollback) | **25%** |

Reasoning per axis:

- **Canonical exact ≥ 92%** (P_pass ≈ 0.55, P_half ≈ 0.30, P_fail ≈ 0.15). The K=9 baseline achieved 88.6% canonical exact on a smaller 19.5K training set. The combined corpus is ~5× larger (97K) which should help, but `--paraphrase-augment-train 9` raises the per-canonical augmentation ratio (was 3, now 9) — at K=9 with bare-template the result was a NET regression on aggregate (per `project_k9_baretemplate_partial_success_2026_05_02.md`); without bare-template, the K=9 augmentation alone is untested at scale. Most likely outcome: HALF-PASS at 88–92%.
- **Paraphrase invariance ≥ 65%** (P_pass ≈ 0.30, P_half ≈ 0.50, P_fail ≈ 0.20). K=9 baseline paraphrase exact was 86.8% (paraphrase eval, not honest two-pass — apples-to-apples is closer to 50–60%). Lever 3 contributes 5K paired records; demographic expansion contributes K=4 surface variants on the canonicals; both expand the surface-form training distribution. The risk is that Lever 3 paraphrases are stylistically MORE divergent than the demographic-tonal variants, so the model could overfit to the latter (4× more records per canonical) and regress on the former. Most likely outcome: HALF-PASS at 50–65%.
- **meta_logic per-bucket ≥ 30%** (P_pass ≈ 0.25, P_half ≈ 0.50, P_fail ≈ 0.25). This is the vocab14 hypothesis test, with the prep memo's exact probability allocation. Median expectation is HALF-PASS at 20–30%.
- **v76_production per-bucket ≥ 50%** (P_pass ≈ 0.20, P_half ≈ 0.45, P_fail ≈ 0.35). This is the **single highest-probability failure axis.** No lever in this retrain attacks the multi-operand routing failure identified in `v76_meta_logic_deep_dive_2026_05_04.md` H2. Vocab14 adds the recipe-arrow `cas:→` and `cas:Λ`/`cas:Ω`/`cas:Θ` tokens, which gives the model a small additional structural signal, but the per-deep-dive judgment is "v76 weakness is dominated by an architectural multi-operand-routing failure." Lever 3 paraphrases v76 surface forms but doesn't change the routing inductive bias. Demographic expansion further dilutes v76 signal density. Most likely outcome: HALF-PASS at 35–50%; meaningful FAIL probability.
- **Demographic robustness within 10 pp** (P_pass ≈ 0.65, P_half ≈ 0.20, P_fail ≈ 0.15). The demographic K=4 expansion is the gate's canonical training input — the model has seen all 8 profiles and all 5 tones at training time. If the rewriter's surface variations preserve the slot block faithfully (as `sdg_demographic_tonal_spec_2026_05_04.md` §4 specifies, and `test_rewrite_preserves_slot_block_in_prompt` enforces), the model has no a priori reason to regress on any single stratum. The only known risk is P2/P4 syntactic divergence (per spec §7); Path A rewriter's coverage there is "weaker." Most likely outcome: PASS, with possible HALF-PASS if P2 or P4 specifically gap > 10 pp.

The 25% combined "any FAIL" probability is mostly carried by v76_production (if it FAILs at < 35%) and partly by canonical (if `--paraphrase-augment-train 9` overweighting demographic-tonal noise drops canonical below 88%).

## 8. Sequencing if Multiple Things Land Before Retrain Fires

Two parallel work streams may finish before this retrain is launched:

1. **Phase 3 free-form English generator** (a new SDG layer producing more colloquial training-surface variants beyond what Lever 3 generates). If complete, its output JSONL would naturally fold into Stage 1b's `cat` invocation as a third input file. This adds substrate variety without changing the retrain's experimental design — Phase 3 is a paraphrase-density lever, like Lever 3, just at higher volume.
2. **Targeted meta_logic generation** (additional canonical records specifically in the meta_logic bucket to address the n=102 thinness called out in `vocab14_prep_memo_2026_05_04.md`). If complete, its output would fold into Stage 1b as a fourth input file.

**Sequencing rule:** include both in the merged corpus IF AND ONLY IF they land before retrain start AND their output files pass the same eval-overlap audit as Lever 3 (Pre-flight 2.1, the joint-key check). If they land MID-retrain or AFTER, defer to v1.1 — do NOT restart this run to fold them in. The cost of confounding the v1 result by changing the corpus mid-run far exceeds the marginal lift from including more data.

If a third lever lands BEFORE retrain start and is folded in, document it in CHANGELOG Session 53 as a corpus-composition note and adjust the run name suffix (`combined-v1-vocab14-lever3-phase3-meta_logic-demographic-K4-...`) so the run dir is self-documenting.

The combined retrain is intentionally NOT optimized for "wait for everything." The user has lost weeks on serialized SDG-then-train sequencing (per `feedback_parallelize_sdg_with_training.md`); this run targets a fixed end-of-day-2026-05-05 launch with whatever has landed. Phase 3 and meta_logic targeted generation are explicitly NOT blockers.

## 9. Post-run Procedure

1. Update `noetic-compass-scaffold/noetic-compass/CHANGELOG.md` Session 53 with: run name, date, hypothesis under test, the 5-axis pass/fail table, headline canonical/paraphrase/meta_logic/v76_production/demographic numbers.
2. Add the bucket and per-head numbers to a new memo at `docs/working/combined_retrain_results_2026_05_05.md`, modeled on `STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md` from the K=9 baseline run.
3. If PASS or v1-rc HALF-PASS: open a PR titled `combined-v1: vocab14 + lever3 + demographic-K=4 retrain → v1[-rc]`; cross-link the result memo and this runbook. If any FAIL: do NOT open a PR; document in the result memo and tag the negative-evidence checkpoint per §5.
4. Update `MEMORY.md` with: outcome of the combined retrain, attributable lift per lever (post-hoc per-bucket analysis: meta_logic improvement → vocab14; v77/v74 paraphrase improvement → Lever 3; demographic gap → demographic K=4 expansion).
5. Calibrate the demographic-robustness gate's `--tolerance-pp` per `task_69_demographic_robustness_completion_2026_05_04.md` §5: set `tolerance_pp = max(5, |worst observed Δ| + 5)` for future runs.
6. If the run is v1, schedule a one-hour internal demo. If v1-rc, queue the next experiment per the §5 mapping.

## 10. References

- Predecessor runbook: `docs/working/vocab14_retrain_RUNBOOK_2026_05_04.md` (vocab14 standalone; this combined retrain supersedes it for the case where the user picked Decision (b)).
- Vocab14 prep memo: `docs/working/vocab14_prep_memo_2026_05_04.md` (Decision matrix; honest assessment of expected meta_logic lift).
- v76/meta_logic deep dive: `docs/working/v76_meta_logic_deep_dive_2026_05_04.md` (per-bucket weakness analysis; root-cause attribution; experiment ranking E1-E5).
- Lever 3 generator completion: `docs/working/lever3_script_completion_2026_05_04.md`.
- Lever 3 generator: `cas-synthetic/scripts/generate_lever3_paired_freeform.py`.
- Demographic-tonal spec: `docs/working/sdg_demographic_tonal_spec_2026_05_04.md` (canonical 8 profiles × 5 tones; K=4 stratification rationale; Path A vs Path B escalation).
- Demographic-tonal driver: `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py`.
- Demographic-robustness gate: `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py`.
- Demographic-robustness gate completion: `docs/working/task_69_demographic_robustness_completion_2026_05_04.md` (calibration recommendations for `--tolerance-pp`).
- K=9 baseline run: `noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md`.
- v77 relabel script: `cas-synthetic/scripts/relabel_v77_overlap.py`.
- Eval-file-slip caveat: MEMORY entry `feedback_eval_file_slip_recurrent.md`.
- `--limit 128` trap caveat: MEMORY entry `feedback_limit_default_128_trap.md`.
- Parallelize-SDG-with-training caveat: MEMORY entry `feedback_parallelize_sdg_with_training.md`.
- K=9 + bare-template result: MEMORY entry `project_k9_baretemplate_partial_success_2026_05_02.md`.
