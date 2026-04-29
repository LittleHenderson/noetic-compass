# Level 3 Recoverable Dataset Report

Generated on 2026-04-29 from `level2_full_10k.jsonl`.

## Command

```powershell
python cas-synthetic\scripts\generate_level3_conversations.py `
  --input cas-synthetic\data\level2_scaffold\level2_full_10k.jsonl `
  --output cas-synthetic\data\level2_scaffold\level3_recoverable_full.jsonl `
  --variants-per-source 2 `
  --style-id recoverable_translation `
  --progress-every 5000
```

## Validation

```text
Total records:      19454
Valid records:      19454
Invalid records:    0
Compiler checked:   19454
Compiler skipped:   0
```

## Summary

- Source records read: 10,000
- Source records used: 9,727
- Source records skipped: 273 deliberate invalid Level 2 examples
- Output records: 19,454
- Exact expression leaks in user prompts: 0
- Unique prompt ratio: 0.828005
- Records with formal family hints: 19,372
- Records with Noetic slot hints: 18,962
- Records with domain slot hints: 17,476
- Records with drive slot hints: 16,750
- Records with register slot hints: 13,486
- Records with production recipe coefficients: 2,000

## Bucket Counts

- v75_register: 5,000
- v77_rule_four: 2,454
- v77_omega: 4,000
- v74_baseline: 4,000
- v76_production: 2,000
- meta_logic: 2,000

## Decision

The raw JSONL is intentionally not committed here because it is 43.9 MB and deterministic from tracked inputs plus the generator command above. The committed artifacts are the generator changes, the validation report, and `level3_recoverable_full_metrics.json`. Regenerate the JSONL locally or on a training pod before the next CAS-Native run.

This dataset is the correct next input for exact prompt-to-CAS training because it verbalizes the recoverable CAS slots without placing the full expression string in the user prompt.
