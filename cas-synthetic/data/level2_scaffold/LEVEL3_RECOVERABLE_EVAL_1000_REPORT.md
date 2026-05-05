# Level 3 Recoverable Eval 1000 Report

**Date:** 2026-05-01
**Dataset:** `level3_recoverable_eval_1000.jsonl`
**Purpose:** Held-out recoverable Level 3 eval set for CAS Transformer Step 5. This dataset is an evaluation artifact and should not be used for model training.

## Generation Command

```powershell
python cas-synthetic\scripts\generate_level3_conversations.py --input cas-synthetic\data\level2_scaffold\level2_full_10k.jsonl --output cas-synthetic\data\level2_scaffold\level3_recoverable_eval_1000.jsonl --style-id recoverable_translation --variants-per-source 1 --start-source-record 8000 --max-source-records 2000 --max-output-records 1000 --seed 20260429 --progress-every 250
```

## Generation Result

```json
{
  "source_records": 1000,
  "source_records_seen": 9035,
  "start_source_record": 8000,
  "selected_source_records": 1034,
  "source_records_skipped": 34,
  "max_output_records": 1000,
  "written": 1000,
  "variants_per_source": 1
}
```

The output uses source indices `8000..9033`, with 1,000 unique Level 2 source IDs. Thirty-four invalid Level 2 sources were skipped by the existing positive-conversation policy.

## Bucket Counts

```json
{
  "v74_baseline": 200,
  "v75_register": 264,
  "v77_rule_four": 123,
  "v77_omega": 203,
  "meta_logic": 102,
  "v76_production": 108
}
```

## Validation Command

```powershell
python cas-synthetic\scripts\validate_level3_conversations.py cas-synthetic\data\level2_scaffold\level3_recoverable_eval_1000.jsonl
```

## Validation Result

```text
Total records:      1000
Valid records:      1000
Invalid records:    0
Compiler checked:   1000
Compiler skipped:   0
Bucket counts:      {'v74_baseline': 200, 'v75_register': 264, 'v77_rule_four': 123, 'v77_omega': 203, 'meta_logic': 102, 'v76_production': 108}
```

## Held-Out Policy

This dataset is held out by deterministic source-index split. It starts at zero-based Level 2 source index `8000` and writes exactly 1,000 recoverable Level 3 records from 1,000 unique source IDs. Future training runs should exclude this source-index range or exclude this exact output file.

## Step 7 Status

Step 7, structured-prediction head work, is now unblocked once this eval set is committed or otherwise preserved outside the ignored data directory. Use this dataset as the fixed held-out recoverable Level 3 eval set for the first structured-prediction head validation.
