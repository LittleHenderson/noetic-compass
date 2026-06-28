# Claude Handoff: CAS Transformer Step 5

**Date:** 2026-04-29
**Read first:** `docs/CAS_NATIVE_AI_CLAUDE_PLAYBOOK.md`
**Then read:** `docs/architecture/CAS_TRANSFORMER_ARCHITECTURE.md`
**Then read:** `docs/working/cas_transformer_first_wedge_plan.md`

## Current North Star

Do not frame this as an LLM wrapper.

The active architecture is **CAS Transformer**: typed CAS transitions first, surface language second. Every conversational turn must be trace-linked, meta-logic aware, and compiler/admissibility checked before rendering.

## Current Local State To Preserve

Recent uncommitted CAS Transformer work may already exist locally:

- `docs/architecture/CAS_TRANSFORMER_ARCHITECTURE.md`
- `docs/working/cas_transformer_first_wedge_plan.md`
- `cas-synthetic/schemas/cas_transformer.py`
- `cas-synthetic/generator/cas_transformer.py`
- `cas-synthetic/validation/cas_transformer_recovery.py`
- `cas-synthetic/schemas/shape2.py`
- `cas-synthetic/scripts/generate_cas_transformer_turns.py`
- `cas-synthetic/scripts/write_shape2_records.py`
- CAS Transformer tests under `cas-synthetic/tests/`
- `noetic-compass-scaffold/noetic-compass/api/notation/turn_admissibility.py`
- `noetic-compass-scaffold/noetic-compass/tests/test_turn_admissibility.py`

Do not revert these. If they are unstaged, work around them.

## What Has Already Been Done

Step 6 was implemented before Step 5 because it closed the hollow-compiler gap.

Turn-type admissibility hook:

```text
noetic-compass-scaffold/noetic-compass/api/notation/turn_admissibility.py
```

Focused tests passed:

```powershell
pytest noetic-compass-scaffold\noetic-compass\tests\test_turn_admissibility.py -q
# expected: 9 passed

pytest cas-synthetic\tests\test_cas_transformer_schema.py cas-synthetic\tests\test_cas_transformer_generator.py cas-synthetic\tests\test_cas_transformer_recovery.py cas-synthetic\tests\test_shape2_record_writer.py -q
# expected: 36 passed
```

Do not proceed to Step 7 until Step 5 exists.

## Next Best Step

Step 5: generate a **1,000-record held-out recoverable Level 3 eval set**.

This is a data/eval prerequisite for the structured-prediction head. The eval set must be fixed, reproducible, and excluded from model training.

## Important Constraint

The existing generator supports:

```text
--max-source-records
--variants-per-source
--style-id recoverable_translation
--seed
```

It may not yet support a source offset. If no offset/split support exists, add it or create a deterministic split script. Do not just regenerate the first 1,000 records and call them held-out if those same source records were used for training.

## Preferred Output Paths

Use these paths unless there is a strong reason not to:

```text
cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl
cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_metrics.json
cas-synthetic/data/level2_scaffold/LEVEL3_RECOVERABLE_EVAL_1000_REPORT.md
```

## Source Dataset

Preferred Level 2 source:

```text
cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl
```

Existing related data:

```text
cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl
cas-synthetic/data/level2_scaffold/level3_recoverable_full_metrics.json
cas-synthetic/data/level2_scaffold/LEVEL3_RECOVERABLE_FULL_REPORT.md
```

## Implementation Plan

1. Inspect whether `generate_level3_conversations.py` supports source offset or split exclusion.

2. If it does not, add one of these minimal mechanisms:

```text
Option A: --start-source-record N
Option B: --source-index-min N --source-index-max M
Option C: a separate split script that writes eval records from a deterministic held-out source range
```

Recommended: add `--start-source-record` to the generator path because it is reusable and simple.

3. Generate exactly 1,000 Level 3 records using `recoverable_translation`.

Because `recoverable_translation` usually emits one variant per source when restricted, use:

```powershell
python cas-synthetic\scripts\generate_level3_conversations.py `
  --input cas-synthetic\data\level2_scaffold\level2_full_10k.jsonl `
  --output cas-synthetic\data\level2_scaffold\level3_recoverable_eval_1000.jsonl `
  --style-id recoverable_translation `
  --variants-per-source 1 `
  --max-source-records 1000 `
  --start-source-record 9000 `
  --seed 20260429 `
  --progress-every 250
```

If `--start-source-record 9000` yields fewer than 1,000 valid records because invalid Level 2 sources are skipped, use a range earlier in the dataset and record the exact range in the report. The key is that the eval source IDs must be disjoint from whatever training source IDs are used.

4. Validate with compiler checks:

```powershell
python cas-synthetic\scripts\validate_level3_conversations.py `
  cas-synthetic\data\level2_scaffold\level3_recoverable_eval_1000.jsonl
```

Expected gate:

```text
Total records:      1000
Valid records:      1000
Invalid records:    0
Compiler checked:   1000
Compiler skipped:   0
```

5. Write metrics JSON with at least:

```json
{
  "dataset": "level3_recoverable_eval_1000",
  "count": 1000,
  "style_id": "recoverable_translation",
  "seed": 20260429,
  "source": "level2_full_10k.jsonl",
  "source_range": "...",
  "valid_records": 1000,
  "invalid_records": 0,
  "compiler_checked": 1000,
  "bucket_counts": {},
  "source_level2_ids_unique": 1000,
  "heldout_policy": "disjoint source-index range from training split"
}
```

6. Write a short report:

```text
cas-synthetic/data/level2_scaffold/LEVEL3_RECOVERABLE_EVAL_1000_REPORT.md
```

Report must include:

- Exact command used.
- Source dataset.
- Source index range / split policy.
- Count.
- Validation result.
- Bucket counts.
- Whether any invalid Level 2 sources were skipped.
- Confirmation that this dataset is held-out and should not be used for training.

7. Add/adjust tests only if you changed generator CLI behavior.

Likely test target:

```text
cas-synthetic/tests/test_level3_conversational.py
```

Add a focused test proving the offset/split behavior is deterministic and actually skips earlier source records.

8. Run focused tests:

```powershell
pytest cas-synthetic\tests\test_level3_conversational.py -q
pytest noetic-compass-scaffold\noetic-compass\tests\test_turn_admissibility.py -q
pytest cas-synthetic\tests\test_cas_transformer_schema.py cas-synthetic\tests\test_cas_transformer_generator.py cas-synthetic\tests\test_cas_transformer_recovery.py cas-synthetic\tests\test_shape2_record_writer.py -q
```

Run the two test roots separately. Do not combine `cas-synthetic/tests` and `noetic-compass-scaffold/noetic-compass/tests` in one pytest process because both have `tests.conftest` and can trigger import-path mismatch.

## Commit Guidance

If committing, keep the commit scoped to Step 5:

```text
cas-synthetic: add held-out recoverable Level 3 eval set
```

Include:

- Generator offset/split code if needed.
- Test for offset/split behavior if added.
- `level3_recoverable_eval_1000.jsonl`
- `level3_recoverable_eval_1000_metrics.json`
- `LEVEL3_RECOVERABLE_EVAL_1000_REPORT.md`
- Updates to playbook/report docs.

Do not include model checkpoints.
Do not start Step 7 in the same commit.

## Step 7 Blocker

Step 7, structured-prediction head, must wait until:

- 1,000-record eval set exists.
- Validation passes with 0 invalid.
- Eval IDs/source split are documented.
- The dataset is marked held-out.

Only then begin model work.

## Final Session Update Required

At the end of the session, update:

```text
docs/CAS_NATIVE_AI_CLAUDE_PLAYBOOK.md
```

Include:

- Commit hash if committed.
- Exact generation command.
- Exact validation result.
- Output file paths.
- Any skipped source-record count.
- Whether Step 7 is now unblocked.

