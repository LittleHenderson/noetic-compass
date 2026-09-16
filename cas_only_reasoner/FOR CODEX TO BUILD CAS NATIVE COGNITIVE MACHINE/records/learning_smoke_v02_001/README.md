# Input-v0.2 single-graph smoke delivery gate

Verifier development: **24 pure controls passed, followed by independent source
review.** The current run and its delivery status are recorded separately in
STATUS.md. This is separate from full-course scoped encoding. The existing smoke
uses one graph and the preserved ordered encoder.

`verify_delivered.py` reuses the unchanged verifier at
`records/learning_smoke_001/verify_delivered.py`, SHA256
`318b36e66225ed90f8c2da533fd9ee8685f7d6940c3ef7a75c5a4ebac2c7898c`.
The old verifier requires input rendering v0.1. The extension changes exactly
that comparison in the inherited `measured_evidence` function through a checked
AST transformation. Restoring the comparison must produce the identical original
function AST. All other checks are reused. The new receipt records both source
hashes and the original/adapted function AST hashes.

The extension additionally requires a caller-selected 40-character source commit
and SHA256 of the packaged `cncm/rpa_learning_adapter.py`. It checks the exact
v0.2 prepared, lesson, and rendering constants; the complete-inventory disclosure;
the fixed exposed fixture hash and its exact `contains_inventory_complete=True`;
and v0.2 source context in both delivered checkpoint metadata documents. It does
not rewrite or repair delivered evidence. It retains success or failure receipts
in a new directory and refuses to overwrite them.

The tests use the previous exposed smoke as a preserved control. Altered v0.2
metadata in tests is explicitly synthetic and proves only verifier behavior.
The old packaged adapter remains refused even when those synthetic metadata
documents pass the updated measurement guard. Checkpoint bytes are hashed but
never decoded. No final evaluation targets are read.

## API and command

```python
verify(result_path, expected_lifecycle_sha256, output,
       source_commit=expected_40_character_commit,
       adapter_source_sha256=expected_packaged_adapter_sha256)
```

Run from the selected inner project root, using the actual new lifecycle result
and its caller-observed hash after delivery:

```powershell
python -B records/learning_smoke_v02_001/verify_delivered.py --lifecycle-result records/learning_smoke_001/receipt_NEW_JOB/result.json --lifecycle-result-sha256 ACTUAL_RESULT_SHA256 --source-commit ACTUAL_SOURCE_COMMIT --adapter-source-sha256 ACTUAL_PACKAGED_ADAPTER_SHA256 --output records/learning_smoke_v02_001/delivery_verification_001
```

Successful status is `RECORDED_INPUT_V02_MECHANICAL_EVIDENCE_VERIFIED`. This means
the recorded local evidence passes integrity and consistency checks. It does not
establish an independent numerical rerun, source authenticity, matched learning
gain, full-course correctness, current provider state, or final invoiced cost.

## Remaining preparation, in order

1. Select and verify a committed source containing input v0.2. Commit
   `da3e0ffd8be53fc9ba40b34c91ec571e3d99e4a8` contains that input contract; a later
   verified commit is permitted. Keep this new verifier and its evidence bound
   separately if the worker source commit precedes the verifier publication.
2. Use a clean source checkout for packaging. `worker.input_inventory` recursively
   includes all local `.py` files under `cncm` and `cas_meta2`, including untracked
   files. Packaging an older commit from the dirty full-course worktree fails
   committed-byte checks; do not stage unrelated work merely to satisfy it. An
   isolated checkout under physical HOME `/_worktrees/<name>` with the same inner
   repository layout preserves the preparation helper's HOME calculation.
3. Run the existing pure smoke/material checks on the selected source. The Windows
   package rehearsal checks actual configuration/imports/dispatch and stops at
   `TEACHING_GPU:LINUX_WORKER_REQUIRED`; it does not reach numerical preparation.
   Retain the actual three-training/six-prediction v0.2 preparation and both token
   ceiling checks separately.
4. Build a **new** source-only package using `aws.ingestion_smoke_launch`:
   from `research/CAS_META_2_COMPOSITION`, call
   `build_smoke_package(Path.cwd()/"records/ingestion_smoke_001/package_input_v02_001", source_sha=SOURCE_COMMIT)`.
   The parent directory must exist and the output child must not exist. The package
   uses committed bytes and checks them against all current declared inputs.
5. From the inner root, run
   `python -B records/learning_smoke_001/rehearse_package.py --package-receipt PACKAGE_RECEIPT --package-receipt-sha256 PACKAGE_RECEIPT_SHA256 --output records/learning_smoke_001/rehearsal_input_v02_001`.
   Preserve its receipt, exact package hash, and any failed attempts.
6. Run the existing `prepare_launch.py` with those pinned package and rehearsal
   receipts and a new output child
   `records/learning_smoke_001/launch_input_v02_001`. Its CLI arguments are
   `--package-receipt`, `--package-receipt-sha256`, `--rehearsal-receipt`,
   `--rehearsal-receipt-sha256`, and `--output`. It requires HEAD equal to the
   package source and no tracked changes. It creates a fresh timestamped job,
   request, authority, owner-instruction record, and canonical-ledger snapshot;
   it creates **no reservation**. Its hard-coded physical-HOME ledger location
   remains the canonical `/_worktrees/meta1/.../records/budget/campaign_ledger.json`.
7. Before the separately authorized execution, retain the new request/authority
   hashes and canonical ledger path. From the composition root the existing CLI is
   `python -B -m aws.ingestion_smoke_launch --execute --request REQUEST --request-sha256 REQUEST_SHA256 --authority AUTHORITY --authority-sha256 AUTHORITY_SHA256 --receipt-dir NEW_RECEIPT_DIRECTORY --owner-authorization OWNER_FILE --ledger-path CANONICAL_LEDGER --profile default`.
   This is the first provider/reservation step. Do not invoke it during pure
   preparation. It rechecks authority, source/archive, fresh job, ledger scope,
   provider identity/capacity and a positive observed hourly quote at or below
   the declared ceiling before reserving once and launching once.
8. After collection, run the new verifier above. Keep preparation under the
   existing `records/learning_smoke_001/*` children and package receipts under
   `research/CAS_META_2_COMPOSITION/records/ingestion_smoke_001/*`, because inherited
   discovery intentionally searches those scopes. Store the new verification
   output here. Preserve failures; do not turn them into automatic retries.

The unchanged bounds are 64 updates, 600 seconds for training, a 1,200-second
numeric child limit, 3,600-second outer worker timeout, boot-relative 6,900-second
guest shutdown timer, one job, no automatic retries, and a $7 reservation under
the canonical campaign authority. These are configuration bounds, not a fresh
capacity, price, available-budget, invoice, or termination claim. The worker
creates a fresh training-only tokenizer, model origin, and initial/final
checkpoints; it does not load the previous smoke's model. It verifies actual
installed wheel sources and requires the recorded CUDA/runtime profile.

Required delivered artifact names remain `origin.pt`, `initial.pt`, `final.pt`,
`initial_checkpoint.json`, `final_checkpoint.json`, `before_predictions.json`,
`after_predictions.json`, `initial_reload_predictions.json`,
`final_reload_predictions.json`, `receipt.json`, `installed_sources.json`,
`worker_report.json`, and `measurements.json`, plus the artifact manifest and
terminal envelope/digest. These prove only their covered mechanical checks.
