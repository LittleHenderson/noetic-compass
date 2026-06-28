# Lever 3 Paired Free-Form Generator — Completion Note (2026-05-04)

## Deliverables

1. **Script:** `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\scripts\generate_lever3_paired_freeform.py`
   (574 lines, parses cleanly under `python -c "import ast; ast.parse(...)"`)
2. **Runbook:** `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\scripts\generate_lever3_RUNBOOK.md` (100 lines)

## Exact invocation

From the repo root `C:\Users\wakil\OneDrive\Desktop\tksCAS` with `ANTHROPIC_API_KEY` set:

```powershell
python cas-synthetic/scripts/generate_lever3_paired_freeform.py `
    --target 5000 `
    --out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl `
    --calibration-out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_calibration_50.jsonl `
    --checkpoint-every 500 `
    --seed 42
```

## What the script does

- Loads `level3_recoverable_full.jsonl` (19,454 records) and the v77-relabeled
  eval set (1,000 records).
- Removes eval-overlapping records on the joint key
  `(id, source_level2_id, cas_expression)`.
- Stratified-samples 5,000 records across the six buckets (`v74_baseline`,
  `v75_register`, `v76_production`, `v77_omega`, `v77_rule_four`, `meta_logic`)
  with deficit redistribution when a bucket is under quota (the empirical
  histogram shows all six can supply >=833 records, so the base 833 quota
  per bucket is met without spillover for the standard 5K target).
- Calls Claude Sonnet 4.6 (`model="claude-sonnet-4-6"`) at `temperature=0.7`
  with the rewrite prompt verbatim from the spec.
- Validates each rewrite (length 10-500, ends letter/`.`/`?`, no `^`, no
  `|T/|A/|f/|E`, no `F1..F7`, no `CO-`, and no whole-word `cas`, `noetic(s)`,
  `domain(s)`, `drive(s)`, `register(s)`).
- On validation failure: retries once at `temperature=0.5`. Still-bad outputs
  drop and are logged to stderr.
- Streams every validated example to a `*.partial.jsonl` sibling for resume,
  writes the first 50 to the calibration JSONL before bulk completes, prints
  a progress line every 100 records, and writes the final dataset by copying
  the partial to `--out` at exit.
- Prints a summary block with attempted/validated/drop counts, validation vs.
  API failure split, overall pass rate, and per-bucket validated counts.
- Resume: rerunning the same command reads `*.partial.jsonl` and skips any
  `source_id` already completed.
- Flags: `--dry-run` (no API calls; synthetic placeholder rewrite for pipeline
  validation), `--limit N` (cap source records for testing), `--seed`,
  `--checkpoint-every`, `--train-file`, `--eval-file`.

## Confidence

**High** — would run end-to-end on a clean machine given:

- `pip install anthropic` (sole non-stdlib import),
- `ANTHROPIC_API_KEY` set,
- the two input JSONL files at the documented paths,
- network access to `api.anthropic.com`,
- `claude-sonnet-4-6` available to the calling key.

The script is self-contained, uses only `anthropic` plus stdlib, has no
side-effects outside the `--out`/`--calibration-out` directories, parses
cleanly under `ast.parse`, handles transient API errors with exponential
backoff, and supports resume via the partial checkpoint.

The only runtime risks I cannot fully eliminate from a static script:

- the exact model id `claude-sonnet-4-6` must be valid for the calling
  account on the day of the run (per current Anthropic SDK conventions);
- `--dry-run` is the single best smoke before the paid run.
