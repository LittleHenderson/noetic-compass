# CONT19 v1

Separate child experiment from the unchanged c45f775f scientific source. Original checkpoints, source and historical ledgers remain untouched.

Public seams: restore_parent, adopt_new_lineage, extend_batch_stream. Parent SHA256 5b37699d52e530a9ecd3563e235f0884630225da2fbe27489767a196c0f7a109. Clean cursor2940, total final5880, readouts2940/4410/5880. Fixed LR0.003; old AdamW object, moments, step, weights, frozen encoder, CPU/CUDA/Python RNG and full counters survive adoption. The registered 24-pass ceiling stays unchanged; a separate schedule verifies its complete overlapping prefix before extending the same frozen pass to40.

New child identity and fresh wall/core limits are distinct from preserved cumulative history. Exported child checkpoints use helm.continuation-checkpoint/1 and require the new loader. They cannot be passed off as original c45 checkpoints. Validation restores a separate child clone and restores process RNG in finally; main counters/mode/cursor/pending state and four numerical hashes must match before and after. Validation time still consumes job wall time; validation work is recorded separately.

Tests written:30 focused refusal/accounting/limit cases, plus worker proof performing exact parent restore, real next batch/update2941, bitwise comparison with versus without clone validation, and child reload. The initial revision ran29/29focused tests on AWS. Its numerical worker stopped before restoration because the adapter used schedule instead of the actual pointer_schedule API. The corrected revision adds one real frozen-material schedule regression; that new case and numerical proof are NOT RUN. Failed job and reservation are retained; no automatic retry. No local numerical imports or tests. No CAS/SI dependency for this unchanged-model continuation.

The transport aws_runner.py is a versioned derivative of the established replication validation_launch.py. New schema, authority/ledger API, fixed $24 allocation2/20/2, separate phase identities, one attempt per phase, exact production-instance exemptions, one GPU, guest/outer/provider shutdown and append-only state snapshots. The parent archive is retained privately. Prospective reservations are not actual bills. A training freeze requires the matching numerical preparation receipt before execution.

AWS command (outer environment supplies pinned legacy snapshot and parent):
python -B -m helm_continuation.worker --root /opt/cas-graph6curr/package --parent /opt/helm-validation/parent.pt --plan /opt/helm-validation/child_plan.json --out /opt/helm-validation/outputs/numeric --mode proof

Admission does not claim test success. No automatic training retry or extension beyond40. Source/profile, failed attempts, proof records, readouts and receiver inventories remain evidence. CASalescence parked.
