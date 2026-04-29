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

Latest successful CAS-Native AI result:

- Run path: `noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/semantic-reranker-recoverable-20260429/`
- Dataset: `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`
- Records: 19,454 recoverable Level 3 prompt-to-CAS examples
- Compiler validation: 19,454 / 19,454 valid
- Exact top-1: 12 / 30
- Ground-truth top-5: 24 / 30
- Mean ground-truth rank: 5.1111
- Pairwise training accuracy: 0.985 by epoch 10
- Compiler-valid outputs: 30 / 30

This is the first strong evidence that CAS-Native can learn exact prompt-to-CAS recovery when the prompt actually verbalizes recoverable CAS slots.

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

1. Improve prompt-slot filters for the recoverable prompt wording.
   Current recoverable reranker summary still reports low `slot_match` because the old slot parser was tuned for short prompts, not the new "states: Noetic ^N; domain D; drive Fk" wording.

2. Add a direct recoverable-expression evaluation mode.
   Current evaluation uses candidate banks and semantic rank. Add metrics that separately report:
   - family recovery
   - slot recovery
   - exact expression recovery
   - top-k exact recovery

3. Train the main CAS-Native generator on a mixed curriculum:
   - Level 2 symbolic corpus for formal vocabulary
   - Level 3 recoverable prompts for exact prompt-to-expression translation
   - Level 3 conversational prompts for explanation/conversation

4. Re-run qualitative sample generation after curriculum training.
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
