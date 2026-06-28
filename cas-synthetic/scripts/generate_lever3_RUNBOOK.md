# Lever 3 Paired Free-Form Generation — Runbook

Generates ~5,000 paired training records by rewriting the Level-3 recoverable
training-surface prompts into natural colloquial English using Claude Sonnet 4.6.

## Prerequisites

```powershell
pip install anthropic
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Inputs (must exist):
- `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl` (19,454 records)
- `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` (1,000 records)

## Invocation (full 5K run)

From repo root `C:\Users\wakil\OneDrive\Desktop\tksCAS`:

```powershell
python cas-synthetic/scripts/generate_lever3_paired_freeform.py `
    --target 5000 `
    --out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl `
    --calibration-out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_calibration_50.jsonl `
    --checkpoint-every 500 `
    --seed 42
```

## Dry run (no API calls — pipeline validation)

```powershell
python cas-synthetic/scripts/generate_lever3_paired_freeform.py `
    --target 5000 --limit 20 --dry-run `
    --out cas-synthetic/data/level2_scaffold/_dryrun.jsonl `
    --calibration-out cas-synthetic/data/level2_scaffold/_dryrun_cal.jsonl
```

## Small-batch smoke (50 real API calls — calibration only)

```powershell
python cas-synthetic/scripts/generate_lever3_paired_freeform.py `
    --target 5000 --limit 50 `
    --out cas-synthetic/data/level2_scaffold/lever3_smoke50.jsonl `
    --calibration-out cas-synthetic/data/level2_scaffold/lever3_smoke50_cal.jsonl
```

Inspect `lever3_smoke50_cal.jsonl` — every `user_prompt` should be colloquial
English with no `^`, no `|T/|A/|f/|E`, no `F1..F7`, and no occurrences of the
words `CAS`, `Noetic`, `domain`, `drive`, or `register`.

## Expected runtime and cost

- **Runtime:** ~15 minutes for 5,000 calls (Sonnet 4.6 messages typically
  return in ~150-250 ms each; serial execution dominates wall time).
- **Cost:** ~$0.002 per call x 5,000 = **~$10**. Sonnet 4.6 input is ~400-600
  tokens per call (the rewrite prompt + record fields), output ~30-80 tokens.
  Confirm against current Anthropic pricing before launch if cost-sensitive.

## Resume on crash

The script appends each validated example to a `*.partial.jsonl` checkpoint
sibling of `--out` (e.g. `lever3_paired_freeform_5k_2026_05_04.partial.jsonl`).
On rerun, the script reads the partial file and skips any `source_id` already
present, so re-running the **exact same command** will resume where it left
off without duplicating API calls.

The final `--out` file is rewritten from the partial at the end of every run,
so it is safe to rerun on partial completion.

## Outputs

- **Final dataset:** `lever3_paired_freeform_5k_2026_05_04.jsonl` — only
  validated records.
- **Partial checkpoint:** `lever3_paired_freeform_5k_2026_05_04.partial.jsonl`
  — validated stream as it accumulates; identical to final on clean exit.
- **Calibration:** `lever3_paired_freeform_calibration_50.jsonl` — the first
  50 validated records, written before the bulk run completes for fast review.

## Validation rules

A rewrite is accepted iff:
- length in `[10, 500]` characters,
- ends with a letter, `.`, or `?`,
- contains no `^`, no `|T/|A/|f/|E`, no `F1..F7`, no `CO-`,
- contains no whole-word match for `cas`, `noetic`, `noetics`, `domain(s)`,
  `drive(s)`, `register(s)` (case-insensitive).

Failures are retried once at `temperature=0.5`; if the retry also fails the
record is dropped and logged to stderr.

## Final summary

On exit the script prints a summary block with:
- attempted / validated / drop counts (validation vs. API failures broken out),
- overall pass rate,
- per-bucket validated counts across the six buckets
  (`v74_baseline`, `v75_register`, `v76_production`, `v77_omega`,
  `v77_rule_four`, `meta_logic`),
- absolute paths of `--out`, `--calibration-out`, and the partial checkpoint.
