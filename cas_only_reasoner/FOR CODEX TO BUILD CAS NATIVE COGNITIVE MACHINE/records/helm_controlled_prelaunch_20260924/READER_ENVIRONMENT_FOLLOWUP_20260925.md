# Reproduction environment follow-up - 2026-09-25 UTC

**Partial closure of the existing reader finding. The same MAJOR remains open.**
One bounded static follow-up from `fee4ebecca7457a341bc3427bb8773b040aa0666` to
`6c191fc8eb9505aaa93345435e6e4b44eeb8f544` (reader revision `55182f5f` plus public lock candidate).
Claude retains implementation and AWS execution. No new general review or policy change.

## What closes in source

Every declared lock leaf must be required-equal; driver and kernel cannot be diagnostic. Kernel suffixes are
preserved in exact text comparison. Historical UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS explicitly produces
ENVIRONMENT_ADMISSION_UNVERIFIED. The deciding function is byte-identical to the inspected prior version:
SHA-256 `637db5ebe7608dae5eec1df3c8c9657f6099308517e8257908b3e92e2742b635`.
These are source findings, not AWS runtime acceptance.

## What still needs the already-requested correction

In `repro_common.py:1056-1057`, a required field without an ENVIRONMENT_OBSERVED mapping is still skipped even
when must_observe=True. Fourteen of 24 required leaves have mappings. The ten without mappings are:

- image.ami_id, image.provider, image.region, accelerator.instance_type;
- libraries.packages;
- numerics.dtype, numerics.environment_variables, numerics.float32_matmul_precision, numerics.seeds,
  numerics.thread_counts.

Some have separate package/configuration checks. Those checks do not establish every required runtime observation.
`read_reproduction.py:1087-1089` lists omissions without adding invalid reasons. The producer at
`recompute_reproduction_evidence.py:336-350` is unchanged. Packages, thread counts and precision remain concrete
uncovered examples. This is the same missing-observation defect in the prior review, not a new standard.

Minimal closure: bind an actual observation/comparison for each required field, or return explicit INVALID/unverified
for it. A missing mapping must not pass. Add the already-requested missing/mismatch coverage; do not start an
additional environment experiment or rewrite the reader architecture.

Source tests inspected: `test_unchanged_repro.py:2217-2250` cover driver/kernel equality and envelope restrictions;
2252-2274 cover historical unknowns; 2276-2294 cover historical-pin contradictions. The final mapping-partition
assertion does not require missing mappings to invalidate. Tests were not run by Codex.

All source paths above are below
`records/typed_pointer_001/admission_unchanged_repro_001/`.

## Historical evidence limitation, kept explicit

ENVIRONMENT_LOCK_CANDIDATE.json has SHA-256
`4059b88810d800f5f7356facba6fd463b3946d349b97a56e7055a65171356419`.
It explicitly leaves eight historical fields unestablished: kernel, Python implementation/version, GPU compute
capability, driver, cuDNN, installed packages and thread counts. This candidate already fails closed. The report's
16 filled fields have not received a full independent citation audit here; accepting their existence does not
certify their provenance or infer missing historical values.

Do not substitute another job's settings merely because it used the same AMI. Do not weaken the fixed requirements
after seeing results. The current strict reproduction admission remains INVALID/unverified. Exact learned-state
and output comparisons may still be reported under the previously allowed conditional-diagnostic label; they must
not become a certified reproduction or proof about the other two historical seeds. This does not itself change
Claude's separately recorded training-first execution route or authorize a new job.

## Current training records, separate from scientific conclusions

[Public receipt observation](PUBLIC_TRAINING_PROGRESS_20260925.json) records R17's pushed completion at
`e17d7d2c3d556cb77329c1dfd8352661397cab26` and R18's local, untracked completion receipt left untouched.
Both report completed_deliverable=true, 102/102 required artifacts verified and compute cleanup COMPLETE.
Codex checked receipt bytes and fields, not every artifact or model output. R17's commit reports 9.03 USD plus
0.10 USD allowance; R18 final cost and current cumulative charges remain unverified. R19/U17 completion is not
verified. The fresh provider lookup returned no records for R17/Q4, which is not independent termination proof.
No repair-benefit, all-eighteen-checks or controlled-comparison conclusion follows from delivery receipts.
The owner was told this progress, and codex-0030 requested Claude's current public status and spend reconciliation.

## Checks and handoff

Exact-path Git delta/source review, JSON parsing, candidate/receipt SHA-256 and AST-only extraction; no project
imports, tests, model execution, protected reads, cloud jobs, active-source changes or ledger edits. Required AWS
acceptance remains pending. Claude supplies the one missing-observation correction and evidence; the prior E1b
preservation, cumulative-reserve and P1b lifetime fixes remain open. No additional owner approval is requested.
