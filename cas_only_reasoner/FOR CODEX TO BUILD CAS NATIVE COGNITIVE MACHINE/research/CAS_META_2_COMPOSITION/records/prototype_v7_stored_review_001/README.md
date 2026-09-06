# Independent v7 stored-evidence review

This is a prepared checker, not a v7 pass or learning result. Only a complete,
externally pinned packet that passes `review.py` can produce
`PROTOTYPE_V7_STORED_REVIEW_PASSED`. Partial or inconsistent evidence produces
`review_failure.json`, never a partial success claim.

The checker imports no model framework, loads no tensors, calls no provider,
generates no tasks, and does not train or choose a checkpoint. Existing approved
source/fixture assets and authenticated stored results are read only.

## Exact run command

Run from the META2 package directory. Supply the actual packet path and its
externally received SHA256 after collection. No packet hash is guessed or taken
from the packet itself. Join the following lines into one command:

```text
C:/Python314/python.exe -B records/prototype_v7_stored_review_001/review.py
  --packet ACTUAL_PACKET_ZIP
  --packet-sha256 ACTUAL_EXTERNALLY_RECEIVED_PACKET_SHA256
  --source-archive records/aws_prototype_v7_source_001
  --source-archive-sha256 f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9
  --source-sha 42f9164754312f12850d9b8789c062fa7fb8069f
  --job cas-meta2-20260906094002-39762c47
  --extracted records/prototype_v7_stored_review_001/extracted_001
  --create-extraction
  --output records/prototype_v7_stored_review_001/run_001
```

The source archive is an extensionless ZIP file. Every external identity is a
required CLI argument. Extraction/output targets must be new and inside this
checker directory; nothing is overwritten or deleted. Omit
`--create-extraction` only for an already existing extraction whose every byte
will still be checked against the exact ZIP.

Successful output:

- `prototype_stored_review.json`: full independent receipt, source map, input
  hashes, checkpoints, process evidence, all 72/360 outcomes and diagnostics.
- `SUMMARY.md`: human-readable before/after results and limits.

The checker prints stage progress and the final receipt SHA256. Retain the exact
command, stdout, stderr and exit status when running it. No receipt from this
prepared checker has yet been accepted as an actual v7 result.

## Checks and fixed boundaries

1. Authenticate the source archive, all 603 closed source inputs and their Git
   blobs at the externally supplied commit before project imports. Check all
   316 protected baseline files. Admit the exact prerequisite recovery review
   `5396e0ab263fa435eefd2b8925382ce802b7af7c8d1c4dae5702d51435349ac3`
   and recovery runtime manifest `897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37`.
   Previously checked semantic/report helpers are read with their hashes from
   that prerequisite review; their code is not changed.

2. Authenticate the packet and every extracted member. Refuse traversal,
   links, aliases, duplicate keys, nonfinite JSON, incomplete collection,
   failed processes or mismatched indexes. Bind the outer coordinator command,
   source/experiment/job, exact four-test original GPU contract gate, and raw
   phase command/output receipts.

3. Independently validate the retained base and exact training-only append:
   640 new base records + the unchanged original256 = 896 training records.
   Keep the full 8,837 known graph exclusions for new base/validation/test
   records; never globally subtract the allowed old training graphs.
   Recheck 96 validation and 72 test records, unchanged held-out bytes, public
   export without a private file, and train-only tokenizer.

4. Run the source-bound pure training checker over saved records. Recount all
   200 epochs / 11,200 optimizer steps per family, validation-only selection,
   before/selected/final checkpoint byte identities and freely generated
   prediction seals. This is recorded-action and byte checking, not neural
   arithmetic, gradients or tensor verification.

5. Check the one-test known-fixture GPU smoke: saved seed926603,
   352/24/9 records, one epoch / 22 steps per family, real preparation exit
   before training exit, CUDA-authored changed-weight receipt, and native9/45.
   Check saved checkpoint bytes, child commands, cold parent admission,
   workers and aggregates. The smoke’s tensors and SQLite/verifier semantics
   are not independently replayed. They are kept separate from main72 results.
   The outer GPU phase is capped at 450 seconds; inner smoke900 is not extra
   time. Main parent6900 / compute7200 and registered phase limits are checked.

6. Check every main reference and all 360 saved choices with the unchanged
   stored verifier. Rule choices are derived from permitted public inputs;
   all neural choices must match the pre-private-opening seal unchanged.
   Complete executions use the source-bound old semantic checker. Rejections
   must fail the unchanged admission check before any native writes.
   Only the exact known post-start exception is contained:
   `repair cannot open without a durable distinct ^6 round trip`.
   Its committed database prefix is checked separately, not passed into the
   success-only verifier. Failed-tick compute remains unknown/incomplete.

7. Recount fixed-denominator all/per-depth/per-condition results and literal
   observation binding, input-site, child-selection and first-recorded-error
   diagnostics. Recheck every database trace against the published schema and
   match complete exports. Rehash source, helper and extraction bytes at end.

V7 worker files record PID, environment, source, baseline and helper identity.
They do not record independent before/after process parent IDs. The review
does not invent that missing attribution. Main stored semantic checking is
stronger than smoke documentary checks; those two scopes are not conflated.

## Interpretation

The 72 tests are 24 related triplets, not 72 independent program structures.
Depth3 has48 variants; depth4 has24. New-input testing of a previously known
program is not isolated here. Literal names can penalize equivalent renaming;
first recorded divergence is not proof of the earliest causal neural token.

Original256 examples are known practice material allowed only in v7 training.
V6’s 640-record training set did not include them. The recovered v6 zero/72
scores and the earlier separate generic12/72 result remain separate historical
facts. No actual v7 learning result is asserted by this preparation.

A valid trace alone is not a correct answer. A stored evidence pass does not
independently reproduce neural arithmetic, establish general reasoning or
CAS-specific advantage, or authorize automatic promotion.

## Retained pure tests

```text
C:/Python314/python.exe -B records/prototype_v7_stored_review_001/run_checks.py
  --output records/prototype_v7_stored_review_001/checks_001
  --source-archive records/aws_prototype_v7_source_001
  --source-archive-sha256 f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9
  --source-sha 42f9164754312f12850d9b8789c062fa7fb8069f
```

The tests use synthetic packet/collection/authentication/training/parent callback
fixtures where stated. They exercise actual pure process, metadata, command,
path, aggregate and refusal helpers. The separate source preflight checks the
real frozen source archive/Git bytes. A green synthetic test run is not an actual
packet pass or a complete end-to-end production evaluation.

The command above identifies a retained attempt. For a new rerun, use a new
output directory such as `checks_005`; existing outputs are never overwritten.

## Completed preparation checks

`checks_003/checks_receipt.json` passed with SHA256
`7b707571253ffa33ed6dbc5997dc1585b13de012161498611ab72e9eb17b416c`.
It records 55 dataset/byte tests, 29 smoke-evidence tests, 32 metadata/CLI tests,
and 2 summary-rendering tests: 118 tests total. The dataset pytest run reported
one suppressed collection alias, which is not counted as another test. All
four subprocesses exited 0. Actual source preflight and the final byte recheck
confirmed all 603 source files and 316 protected files unchanged.

The two earlier combined runs remain in `checks_001` and `checks_002`. Their
dataset subprocess stopped before tests because isolated Python hid the
existing user-site pytest installation. The final runner uses the canonical
validator's existing-environment `-B` mode for this one pytest process, with
the neural/provider import guard and plugin auto-loading disabled. The three
standard-library unittest files still run with `-I -S -B`. No package was
installed and no checker acceptance rule was loosened. Summary layout and
explicit after-denominator fixes have dedicated synthetic regressions.

The main agent independently reran the same 118 tests in `checks_004`.
All four subprocesses exited 0 in 7.507 seconds total, and all 603 source and
316 protected files matched again. Receipt SHA256:
`51d7131492406f35e45e70a73b1a4cb2e3bd62f2ab03d8213562f6cd204f6ae6`.
The ten checker Python files were unchanged throughout both passing runs.
No actual current-job packet was read in either preparation run.
