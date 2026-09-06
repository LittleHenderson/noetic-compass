# Pure cold-child review

This is a local regression of the v7 data-validation child, not AWS execution
or model evaluation. It uses only the saved seed-926603 bundle: 352 training,
24 validation, and nine test records.

The test bootstrap replaces only the AWS/Linux request check in its disposable
child. Neural and provider imports and network/process launches inside that
child are trapped. The coordinator uses a real exited Windows child with
CREATE_NEW_PROCESS_GROUP and records that platform adaptation explicitly.
Production code and its process-exit checker are not weakened.

The synthetic four-arm predictions and parent training gate in the ordering
check are test fixtures, not a trained model or successful training receipt.
The actual preparation function must seal all five arms before opening private
targets. The actual cold validator must then verify the hash-bound saved bundle.

Raw outputs, exact commands, source hashes, and final results are retained by
run.py when that runner is executed. Its records must not be overwritten.

## Result

The retained run in `checks_002/` passed **14 test functions and 7 subtests**
in 32.26 seconds. The JUnit file contains 14 test-function entries; the seven
passing subtests are separately reported in raw pytest output. There were no
failures, errors, or skips.

The run used 12 real child processes: one successful cold check and 11 controlled
rejection cases. The successful report retained the exact 352/24/9 split counts.
All source hashes and copied dataset bytes stayed unchanged.

The actual frozen baseline checker verified all 316 protected files before and
after. It also verified exact package-file copies from both protected wheels:
nine casformer files and 26 cas_cjt files. The temporary package files were
discoverable through `find_spec` but were never imported or installed into the
environment. The coordinator's import hooks and search path remained identical
across cold validation, so the child's permanent guard did not leak back.

## What was checked

- The unchanged preparation function sealed all five arms before its first
  private-target read. Four neural-arm actions and the training gate were
  explicitly synthetic fixtures; they are not training evidence.
- A real child verified the externally hashed request, source identities,
  loader, source pins, original bundle, seed, curriculum configuration, and
  exclusions. The parent consumed its report only after successful exit checks.
- Changed source, manifest, loader, and source-pin identities rejected the request.
- Changed seed, curriculum configuration, and exclusions rejected it with
  `MANIFEST_IDENTITY_MISMATCH`.
- A changed request hash rejected before child private reads. Changing the
  request after a successful exit also rejected before report consumption.
- Controlled copies of the exit receipt with a failed completion flag or the
  coordinator's PID were rejected. The unmodified actual receipts are preserved
  beside these deliberately changed test receipts.
- No neural/provider imports or network actions occurred in the coordinator or
  children. The child bootstrap also blocked subprocess and shell actions.

Source and request failures were checked before private reads. Valid-shaped but
wrong seed/configuration/exclusion values are rejected during full cold
reconciliation, which reads private targets; this is an evaluator-only phase
after prediction sealing. The cold helper does not itself replace the caller's
prediction-seal gate. These two boundaries are tested separately.

The child command is bounded by the earlier of the caller's deadline and 180
seconds in production source. Each test launch also checked that supplied bound.
This run did not force a timeout or test Linux process-group termination.

## Exact identities and paths

- Tested `cas_meta2/contrast_v7/native_evaluation.py`:
  `cba4069c71dac86612a6c82192471af305454f615e572b6f35fa18138477652b`
- New `tests/test_contrast_v7_cold_child.py`:
  `df8938fa4c9c3ed5c8bcc09ad322fcbfe8c269e2c8637fe18b13ab23b35efae2`
- `checks_002/receipt.json`:
  `5cf1feec071bcc44e5d54927583227e3b30e8458b287758a8052918007882091`
- `checks_002/probe_records/probe_receipt.json`:
  `9bd6fc006ec5f43b6f97ad5e5e017a696e1ebb59746c397b7d44a1148e53d9e0`
- Original merged manifest:
  `19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29`
- Source pins:
  `9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d`
- Public loader:
  `5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0`

The full known-data copies and wheel-file fixture remain under
`runs/v7cold-c7e1a0ce4597/`; audit-only requests, reports, child startup/exit
markers, raw stdout/stderr, and exact process commands were copied into
`checks_002/probe_records/`. No temporary evidence was deleted.

An initial helper typo failed before child execution at
`runs/v7cold-d74699be4213/`. A subsequent 14-test pass at
`runs/v7cold-c99de044b6fe/` proved callable lookup without installed package
discovery; the retained final run adds the stronger exact-wheel-file check.
The first recording attempt in `checks_001/` could not find user-site pytest
because it used Python's `-I` option. Its raw output and failure explanation are
preserved. The final pytest process uses the existing environment, while its
actual coordinator is a fresh isolated process and all validation children are
separate processes.

No production code, permissions, canonical guard, live job, or accepted model
was changed. No concrete production defect was found in this bounded review.
Full native execution, actual AWS/Linux behavior, GPU behavior, fresh
installation, and a new learning result remain outside this proof.
