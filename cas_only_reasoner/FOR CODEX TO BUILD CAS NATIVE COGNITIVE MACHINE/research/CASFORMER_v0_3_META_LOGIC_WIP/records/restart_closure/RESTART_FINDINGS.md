# CAS-META-0 restart closure findings

Source correction: cbce17dad55b61ffc0f77860324ca1e9ffad3746.
Original tested source: fda27bcff9c38af5941a15433db6ae7d59bf0d9a.
Original evidence: 35a81a774dd1b2be1106b6f7403d410e28c81e4c.

## Demonstrated cause in the published builder bundle

The original full demo saved checkpoint.json after native step 4, then automatically
called the public resume CLI against the same compiled.db. That successful resume
advanced the database to step 5. The original checkpoint was retained at step 4;
final_checkpoint.json records step 5.

Replaying the earlier resume command against that completed database is therefore
a stale-pair attempt. NATIVE_HEAD_MISMATCH is the correct refusal, not evidence of
a restore-order defect. Native head is the committed SQLite active_head row, not
Git HEAD. cli_validation/native_head_diagnosis.json preserves both exact values.

The passing original test called resume BEFORE the database advanced. No hidden
initialization step was found in that test. The public workflow was incomplete
because there was no pause-only preparation command and no retained matching
paused database after a complete demonstration.

## Correction

- Added --prepare: create the paused database, checkpoint, and its creation receipt;
  close the writer; preserve a matching copy in paused/; exit without continuation.
- --output still executes the full existing fixed-weight demonstration. Its paused/
  copy remains available for replay after the root database reaches step 5.
- --resume names missing database/checkpoint dependencies before opening SQLite.
- Resume records exact restored frames, before/after native heads, budget and model
  identities, and verifies that prior native state projections and meta events
  remain unchanged. Only resumed C adds a native step.
- The checkpoint and native-head guards in cas_meta/executor.py were NOT changed.
- Frozen v0.2, its manifest, and its source/evidence commits were NOT changed.

The documented workflow is prepare in one process, then resume in another using
the digest issued for that exact checkpoint. To replay preserved evidence, copy
the whole paused/ folder to a fresh writable directory and resume the copy.
Never rewrite an authoritative database head or restart the workflow from scratch
and label that action resume.

## Checkpoint identity is per invocation

The checkpoint hashes canonical serialized bindings, native head, frames, events,
counters, result ID, and artifact IDs. Executor.__init__ assigns uuid4().hex to
run_id. That ID occurs in bindings/call IDs and affects the meta-event hash chain.

Two public prepare runs were measured in cli_validation/checkpoint_identity_comparison.json.
Their run IDs and checkpoint hashes differ; their program/model identities and
native heads agree. This is per-run artifact identity, not a requirement for
identical checkpoint hashes across independent runs. No fields or identity checks
were removed.

## Preservation and scratch check

All 31 payload files in the ORIGINAL evidence manifest were compared both with
their recorded hashes and with Git blobs at 35a81a774dd1b2be1106b6f7403d410e28c81e4c.
They match. The shared Git object store is outside Temp:
C:/Users/wakil/OneDrive/Desktop/tksCAS/.git

The original records were already committed. No temporary _te*, _final*,
_verify_*, or api-review-* file was found in the tracked prototype source.
Scratch directories were not deleted. The public CLI preparation needs no such
scratch directory; tests use newly owned disposable paths.

Original receipts are retained unchanged under records/validation. The supplied
partial-audit and failure narratives, and both owner assessments, are appended
under inputs/. The assessment attachments were copied byte-for-byte.

## Evidence limits and unresolved external item

The original GLM narrative reports a self-consistent checkpoint/digest pair failing
at NATIVE_HEAD_MISMATCH, but gives no full command, working directory, full digest,
checkpoint/database paths, or raw traceback. Those original failure files were not
found. We cannot establish their exact state or prove that GLM's particular pair
had the same cause as the published builder pair.

The locally reproduced stale-pair failure is recorded separately, on a copy of the
published builder files. It is NOT relabeled as GLM's raw failure.

The new local tests and separate internal-agent CLI rerun are local engineering
evidence, not a new independent GLM audit. The external auditor's updated verdict
remains pending. The original audit remains
CAS_META_0_FIXED_WEIGHT_COMPOSITION_AUDIT_PARTIAL until that external scope is
reconciled. No full Fractal implementation, training, learning isolation,
crash-atomic recovery, or new cognitive capability is accepted here.

Persistent Bias remains per native CJT, not a separately isolated Bias for every
call. The fifth tick remains inference-only, not the original v0.2 learning tick.

## Evidence entry points

- full_validation/receipt.json: complete current meta suite, five frozen manifest
  tests, full demo, installed-wheel identity, and environment.
- cli_validation/receipt.json and commands.json: public CLI acceptance/rejection
  cases and exact raw stdout/stderr.
- cli_validation/native_head_diagnosis.json: expected versus actual native head.
- cli_validation/checkpoint_identity_comparison.json: measured per-run identity.
- cli_validation/preservation.json: old evidence Git-byte and scratch checks.
- reviewer/: separate internal-agent public CLI rerun and its provenance.
- final_receipt.json: consolidated source-bound outcome and remaining external item.

A new validation does not re-execute the historical full v0.2/v0.1/CNCM suites.
Their previous evidence remains separate. The complete current meta suite and
frozen v0.2 manifest checks are the regression scope of this focused change.
