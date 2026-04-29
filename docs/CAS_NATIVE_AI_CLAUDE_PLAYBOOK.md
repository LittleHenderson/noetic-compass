# CAS-Native AI Claude Playbook

## Memory Instruction For Claude

At the beginning of every CAS-Native AI work session, read this file before making a plan.

At the end of every CAS-Native AI work session, update this file with:

- Latest known-good commit hash.
- Any new dataset, training, or validation result.
- Exact commands that reproduced the result.
- Any failed hypothesis and what it means.
- Next safest action.

Do not rely on memory alone. This file is the session handoff contract between Claude and Codex.

## Current Known-Good State

Latest relevant pushed commits:

- `aa6a69f` - `cas-native: add semantic reranker diagnostic`
- `3f82149` - `cas-synthetic: add recoverable Level 3 prompts`
- `3fd565c` - `cas-synthetic: record recoverable Level 3 dataset metrics`
- `bdd8d62` - `cas-native: support Level 3 reranker datasets`
- `0612b9a` - `cas-native: record recoverable reranker success`
- `9cbcb6b` - `cas-native/inference: fix phantom carriers/foundations slots in non-meta-logic prompts`
- **THIS COMMIT** - `cas-native: PATCHED-parser A/B validation run (recoverable Level 3) — all gates clear`

Latest successful CAS-Native AI result (PATCHED parser, A/B validation, 2026-04-29):

- Run path: `noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/semantic-reranker-recoverable-PATCHED-20260429/`
- Dataset: `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl` (identical to baseline)
- Tokenizer: identical bytes to the baseline (same `tokenizer.json`, vocab=665, hash `b7552dbf2ebef0a5`)
- Hyperparameters: identical to baseline (epochs 10, batch 512, lr 0.001, seed 42, train-records 19000, max-candidates 5000, negatives-per-positive 4)
- Hardware: A6000 48 GB, bf16, CUDA torch 2.5.1+cu124
- Wall clock: 2841.0 s (≈ 47 min; baseline was 1784 s ≈ 30 min — patched parser admits tighter slot-filtered candidate pools, so harder per-pair discrimination)
- Pairwise training accuracy: 0.917 by epoch 10 (lower than baseline 0.985 — *expected and correct*: tighter slot filter → harder negatives per pair → better top-1 selection despite lower per-pair accuracy)

A/B gate clearance:

| Metric                | Baseline   | Gate            | This run        | Margin              |
|-----------------------|------------|-----------------|-----------------|---------------------|
| Exact top-1           | 12 / 30    | ≥ 15 / 30       | **21 / 30**     | +6 above gate, +9 vs baseline (+75 %) |
| Ground-truth top-5    | 24 / 30    | ≥ 24 / 30       | **26 / 30**     | +2                  |
| Mean ground-truth rank | 5.11      | < 5.11          | **2.89**        | −43 %               |
| Ground-truth scoreable | 27 / 30   | ≥ 27 / 30       | **27 / 30**     | at gate             |
| slot_match (live measurement) | 3 / 30 (baseline raw) → 21 / 30 (offline-recompute prediction) | — | **28 / 30** | confirmed and exceeded |

Per-bucket result:

| bucket          | exact      | top-5      | mean_rank |
|-----------------|------------|------------|-----------|
| v74_baseline    | 4 / 5      | 4 / 5      | 1.0       |
| v75_register    | 5 / 5      | 5 / 5      | 1.0       |
| v77_rule_four   | 5 / 5      | 5 / 5      | 1.0       |
| v77_omega       | 3 / 5      | 5 / 5      | 1.6       |
| v76_production  | 2 / 5      | 5 / 5      | 1.8       |
| meta_logic      | **2 / 5**  | **2 / 5**  | **15.67** |

Five of six buckets now near-saturated on top-5 (≥ 4/5). meta_logic is the lone laggard and it dominates the mean-rank average — the patched parser left meta_logic slot_match unchanged at 3/5 (the phantom-slot fix gated `carriers`/`foundations` to meta_logic only, so meta_logic's prompt-side parsing was already correct; meta_logic's residual failure mode is upstream of slot extraction).

This is the empirical confirmation that the prediction in `9cbcb6b` was correct: the patched parser used as a hard candidate-bank filter (not just a diagnostic) lifts exact_match materially in the buckets where slot_filter previously fell back. v77_rule_four 0 → 5 exact, v77_omega 0 → 3 exact, v76_production 0 → 2 exact.

Validation report at: `runs/semantic-reranker-recoverable-PATCHED-20260429/SEMANTIC_RERANKER_VALIDATION_REPORT.md`. Trained `.pt` checkpoint (2.0 MB) is present locally but kept off-VCS per existing policy. Available for next experiment without retraining.

### Phantom-slot fix (this commit)

The `infer_prompt_slots` function was populating two phantom slots for non-meta-logic buckets:

- **`carriers`** — set whenever a prompt contained any literal carrier word (`Noetics`, `States`, `Domains`, `Foundations`, etc.). Recoverable Level 3 prompts use `states:` and `noetics:` as prose section headers, which triggered this. But for non-meta-logic buckets the candidate expression never contains the carrier name as a literal token (e.g. `^5^C_{F2} * ^1^C_{F2}` has no `States` substring), so `candidate_matches_slots` could never be satisfied.

- **`foundations`** — set from `_DRIVE_RE` matches in the prompt for all buckets. But `expression_slots` only emits `foundations` for `Foundation_N` literals (which only appear in meta_logic expressions). For non-meta-logic, F-numbers are Drive subscripts, not Foundation refs.

Fix: gate both `carriers` and `foundations` to `bucket == "meta_logic"`. Drives still populate from F-numbers via the existing path. The meta_logic-bucket regression tests still pass.

Effect on the recoverable run, recomputed offline:

| bucket          | slot_match before | slot_match after |
|-----------------|-------------------|------------------|
| v74_baseline    | 0 / 5             | 2 / 5            |
| v75_register    | 0 / 5             | 2 / 5            |
| v77_rule_four   | 0 / 5             | 5 / 5            |
| v77_omega       | 0 / 5             | 4 / 5            |
| v76_production  | 0 / 5             | 5 / 5            |
| meta_logic      | 3 / 5             | 3 / 5 (unchanged) |
| **overall**     | **3 / 30**        | **21 / 30**      |

`exact_match` is unchanged at 12 / 30 (the rerank made the same picks); the fix is purely in the slot-match measurement layer. But the implication is significant: when the next GPU run uses the patched parser as a hard candidate-bank filter (not just a diagnostic), exact_match should also lift, especially in v76_production and v77_rule_four where the slot filter was previously falling back to the family-only set on every prompt.

## Core Finding

The earlier Level 2 prompt corpus was underdetermined for exact CAS recovery.

Example failure mode:

- Prompt: "A doctor facing an unfamiliar diagnosis is asked to give their perspective."
- Hidden target: some exact `^N^D_{Fk}` expression
- Problem: the prompt does not expose enough Noetic/Domain/Drive/Register evidence to recover one exact target among thousands of valid candidates.

The fix was not more GPU time. The fix was a recoverable prompt layer.

## Data-Side Fix

The recoverable Level 3 style is `recoverable_translation`.

It verbalizes the exact CAS slots without copying the full CAS expression into the user prompt.

Example prompt shape:

```text
I am learning CAS. The target structure is families: state expression;
states: Noetic ^2; domain O (operational); drive F3; register |T
(meaning-level). What is the precise notation?
```

The target remains:

```text
^2^O_{F3}|T
```

This makes exact prompt-to-CAS recovery learnable.

## Local Reproduction Commands

Run from repo root:

```powershell
python cas-synthetic\scripts\generate_level3_conversations.py `
  --input cas-synthetic\data\level2_scaffold\level2_full_10k.jsonl `
  --output cas-synthetic\data\level2_scaffold\level3_recoverable_full.jsonl `
  --variants-per-source 2 `
  --style-id recoverable_translation `
  --progress-every 5000
```

Expected generation summary:

```text
source_records_read: 10000
source_records_skipped: 273
written: 19454
bucket_counts:
  v75_register: 5000
  v77_rule_four: 2454
  v77_omega: 4000
  v74_baseline: 4000
  v76_production: 2000
  meta_logic: 2000
```

Validate:

```powershell
python cas-synthetic\scripts\validate_level3_conversations.py `
  cas-synthetic\data\level2_scaffold\level3_recoverable_full.jsonl
```

Expected validation:

```text
Total records:      19454
Valid records:      19454
Invalid records:    0
Compiler checked:   19454
Compiler skipped:   0
```

Run focused tests:

```powershell
pytest cas-synthetic\tests\test_level3_conversational.py -q
pytest noetic-compass-scaffold\noetic-compass\cas-native\tests\test_constrained_sampling.py -q
```

Expected:

```text
13 passed
18 passed
```

## Cloud GPU Reproduction Commands

Use an A6000/A5000 class RunPod with CUDA torch available. Copy or pull latest `origin/master`.

Generate and validate the recoverable dataset on the pod:

```bash
cd /root/workspace
python cas-synthetic/scripts/generate_level3_conversations.py \
  --input cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
  --output cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
  --variants-per-source 2 \
  --style-id recoverable_translation \
  --progress-every 5000

python cas-synthetic/scripts/validate_level3_conversations.py \
  cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl
```

Build a tokenizer from the recoverable Level 3 corpus:

```bash
cd /root/workspace/noetic-compass-scaffold/noetic-compass
mkdir -p cas-native/inference/runs/semantic-reranker-recoverable-20260429
python - <<'PY'
import sys, types
from pathlib import Path
repo = Path('/root/workspace/noetic-compass-scaffold/noetic-compass')
pkg = types.ModuleType('cas_native')
pkg.__path__ = [str(repo / 'cas-native')]
sys.modules['cas_native'] = pkg
sys.path.insert(0, str(repo))
from cas_native.training.data_pipeline import load_cas_data
from cas_native.training.tokenizer import HybridCASTokenizer
records = load_cas_data('/root/workspace/cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl')
tokenizer = HybridCASTokenizer.from_records(records, freeze=True)
out = repo / 'cas-native/inference/runs/semantic-reranker-recoverable-20260429/tokenizer.json'
tokenizer.save(out)
print({'records': len(records), 'vocab_size': tokenizer.vocab_size, 'hash': tokenizer.vocab_hash(), 'path': str(out)})
PY
```

Expected tokenizer:

```text
records: 19454
vocab_size: 665
hash: b7552dbf2ebef0a5
```

Train/evaluate the semantic reranker:

```bash
cd /root/workspace/noetic-compass-scaffold/noetic-compass
python cas-native/inference/train_semantic_reranker.py \
  --dataset /root/workspace/cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
  --tokenizer /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/semantic-reranker-recoverable-20260429/tokenizer.json \
  --out-dir /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/semantic-reranker-recoverable-20260429 \
  --train-records 19000 \
  --eval-per-bucket 5 \
  --max-candidates 5000 \
  --negatives-per-positive 4 \
  --epochs 10 \
  --batch-size 512 \
  --lr 0.001 \
  --device cuda
```

Expected headline:

```text
epoch 10 loss=0.0276 pairwise_acc=0.985
exact=12/30
top5=24/30
mean_rank=5.111111111111111
```

## What Not To Repeat

Do not spend more GPU time trying to force exact recovery from the original Level 2 scenario prompts. That experiment already falsified the hypothesis:

- Level 2 semantic reranker: exact 2 / 30, top-5 2 / 30, mean rank 363.8
- Cause: prompt underdetermination, not model inability to compile

Do not commit large raw generated JSONL unless explicitly requested:

- `level3_recoverable_full.jsonl` is about 43.9 MB
- It is deterministic from tracked code plus `level2_full_10k.jsonl`
- Commit metrics/report, not the raw file, unless there is a deliberate release reason

Do not commit large model checkpoints by default:

- Reranker `.pt` is small enough to archive manually, but binary model artifacts should normally stay local/off-VCS unless explicitly approved

## Next Best Actions

1. ~~Improve prompt-slot filters for the recoverable prompt wording.~~
   **DONE this commit.** The phantom `carriers` and `foundations` slot
   population was the dominant cause of low `slot_match`. Offline recompute
   on the existing samples shows slot_match jumped from 3/30 to 21/30
   without re-running inference. Next GPU run will see the same parser
   used for hard candidate-bank filtering (not just diagnostic), which
   should also lift exact_match in buckets where slot_filter previously
   fell back (especially v76_production and v77_rule_four).

2. **Diagnose meta_logic bucket residual failure (mean_rank 15.67).**
   With the patched parser, meta_logic is the only structural laggard
   (2 / 5 exact, 2 / 5 top-5). Phantom-slot fix did not affect it because
   `carriers`/`foundations` were gated to it (correctly). Residual issue is
   upstream of slot extraction. Likely candidates:
   - meta_logic candidate-bank coverage too narrow (only 858 candidates vs
     1005-3964 for other buckets) — may not contain ground-truth target
     for some prompts
   - meta_logic prompt wording is structurally different from the other
     buckets (foundation references, set notation) and the reranker may
     not be picking up on the right tokens
   - the 7660 records skipped at pair-build time as `target_not_scoreable`
     may be disproportionately from meta_logic, starving training
   Investigate before broader curriculum training — meta_logic correctness
   matters because it is where typed-set / recipe / cluster expressions
   surface, the highest-information-density CAS forms.

3. Add a direct recoverable-expression evaluation mode.
   Current evaluation uses candidate banks and semantic rank. Add metrics that separately report:
   - family recovery
   - slot recovery
   - exact expression recovery
   - top-k exact recovery

4. Train the main CAS-Native generator on a mixed curriculum:
   - Level 2 symbolic corpus for formal vocabulary
   - Level 3 recoverable prompts for exact prompt-to-expression translation
   - Level 3 conversational prompts for explanation/conversation

5. Re-run qualitative sample generation after curriculum training.
   Success criterion should not be raw text fluency first. Track:
   - compiler-valid complete expression rate
   - exact/top-k recovery on recoverable prompts
   - conversational explanation quality on Level 3 dialogue prompts

## Session-End Checklist

Before ending a CAS-Native AI session:

- Confirm any active RunPod is terminated or explicitly tell the user it is still running.
- Retrieve small reports/metrics/samples from the pod.
- Do not retrieve or commit huge checkpoints unless approved.
- Commit only scoped files; ignore unrelated dirty worktree entries.
- Push to `origin/master` if the user expects GitHub continuity.
- Update this file with the new known-good result and next safest action.
