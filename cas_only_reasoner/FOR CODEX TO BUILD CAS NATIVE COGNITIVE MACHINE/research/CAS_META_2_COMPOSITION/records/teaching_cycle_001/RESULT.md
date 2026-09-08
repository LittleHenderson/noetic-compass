# Teaching-cycle preparation receipt

Status: **PREPARED_NOT_TRAINED**.

Source commit: `19edf7f985227269fb158d128152ecff9fa7b043`.
Dataset identity: `8ea6e0c333a9dee5067e4bbc134c01bfe85352184046fb3b788a77152ec601f3`.

Built a separate finite input-binding curriculum, exposure/readiness controller,
and candidate-only CUDA adapter. The source commit changes eleven new files;
it does not change accepted executors, models, or frozen condition-skill v9.

Prepared 256 training cases, 64 development cases, and three separate 64-case
final-test sets. Minimum allocation is 1,024 complete aligned cycles per
learner, with at least four full cycles for each of the 256 families. All
seven stages must be recorded. The ordinary comparison has seven presentations
per block but is not labelled an aligned cycle.

## Verified here

- Final guarded check: **63 passed in 25.95 seconds**, exit 0.
- Raw outputs and exact command: `checks_003/`.
- The check blocks neural, NumPy, SQLite, provider imports, and network calls.
- Monitored source, frozen v9 trainer/protocol, and budget bytes were unchanged
  across the check.
- Preparation reran after the source commit and emitted `material_001/`.
- Prepared output: 11 files, 685,224 bytes. The preparation receipt hashes
  each payload. Gold is stored separately from final public inputs.
- Lossless tokenizer maximum unassisted input length: 54, within the 512 limit.
- The 11,008 rows used to prepare the shared tokenizer are **not** delivered
  lessons or optimizer steps.
- Actual delivered neural cycles: **0**. Actual optimizer steps: **0**.
- No paid launch, additional reservation, or refund was made.
- Ledger remained SHA-256
  `83fd87829a34a559ae901b553a851d79ec27359601230561afffb55955df2b92`.

Earlier `checks_001` and `checks_002` retain 47- and 60-pass development
snapshots. They are not substituted for the final source check.

## Still required before a learning claim

1. Integrate the end-to-end four-arm runner, matching initialization and
   training budgets. Persist exposure events with checkpoints so interruption
   does not invent or erase delivered cycles.
2. Authenticate the frozen train/development partitions at worker admission;
   exclude private final targets from training-worker access. Pin dependencies,
   freeze the scorer and save blind predictions before opening final targets.
3. Close and test the AWS launch-path faults recorded in the separate v9
   forensic note. Bind a new bounded job to the canonical ledger without
   reusing the failed run's one-shot authorization.
4. Execute the CUDA adapter on AWS and verify actual optimizer, checkpoint,
   reload and prediction behavior. Static checks do not establish those facts.
5. Score real selected input bytes at the native boundary separately from
   binding labels. Native A behavior on these inputs is not yet tested.
6. Add paired relevant/irrelevant-change probes, rule control, retention after
   intervening learning, and restart evaluation. None is a completed result.

This package implements the first teaching components. It is not a completed
training run, a mastery result, or a CAS-specific advantage result. The accepted
selection pilot and the negative held-out composition results remain separate.
