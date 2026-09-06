# Known-example training diagnostic

Purpose: determine whether a fresh CAS candidate can fit known nested programs
before spending on a larger fresh-data campaign. This is a diagnostic step
toward program synthesis, not a substitute for that objective.

The current module is `cas_meta2.fit_diagnostic_v5`. It is pure on import and
refuses non-Linux, missing explicit enablement, mismatched job IDs, or an
invalid time bound before importing neural code. These checks do not prove
AWS identity or authorize spend: a separately checked launcher must bind the
source, reserve budget, verify the GPU and enforce cloud termination.

## Fixed experiment

- Use only the byte-pinned original 3,072-example training file. Select the
  same first eight task IDs at each depth as the previously recorded probe.
  The 24-example cohort includes 16 nested examples and eight shallow ones.
- Fit the lexical vocabulary from those original 3,072 training descriptions,
  matching the original setup. Do not open validation/test data or load old
  checkpoint weights. Build fresh, matched CAS/generic candidates with seed 7.
- Train both on identical shuffled batches of eight for 200 epochs: exactly
  600 optimizer steps each. Use the existing 3:1 semantic-token loss, AdamW
  learning rate 0.001, weight decay 0.01 and gradient clipping 1.0.
- Measure before training, at epoch one, and every tenth epoch. Retain all
  24 freely generated actions and depth-specific exact program/binding
  scores. Use the original v3 decoder for comparison with the saved probes.
  Separately measure teacher-forced token correctness by decision role.
- Save initial and final candidate checkpoints. Do not select a best model
  using these known examples, promote a memory, update the accepted executor,
  or claim held-out learning. Completion of the run is not successful fit.

The time limit is at most 2,700 seconds. The worker checks it between paired
batches and measurement batches; the external launcher must enforce a hard
wall-clock ceiling, including an in-flight kernel. No local neural execution
or T4 training is allowed.

## Current verification boundary

The pure suite passed 1,270 test functions and 178 subtests, with no failures
and eight GPU modules skipped (`records/local_fit_diagnostic_v5_001`). All
123 captured source files and 316 protected baseline files stayed unchanged.
The real-cohort check also matched all 24 IDs to the recounted old probe
(`records/fit_input_check_v5_001`). These checks are separate from
GPU verification. The cloud launcher, GPU tests and actual fit measurements
are not yet complete. Do not use the older `learning_v3` or `decoder_ablation_v4`
profile to silently run this different experiment.

Run the module only through its future source-bound fit profile. Its command
interface is `python -B -m cas_meta2.fit_diagnostic_v5 --training-file PATH
--output NEW_DIRECTORY --job VERIFIED_JOB --max-seconds 2700`.

After the diagnostic, distinguish failure to fit known examples from failure
to generalize. Neither this cohort nor the exposed v3 test may be called a
fresh holdout in the next learning campaign.
