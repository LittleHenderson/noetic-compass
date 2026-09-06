# Saved native failure: AWS read-only inspection

Purpose: identify the first non-returnable native operation in the saved
`candidate_03` R_CR execution of job `cas-meta2-20260906155525-195f5ad8`.
The failed qualification remains negative. This inspection does not train,
re-execute a native operation, change the model, or qualify the curriculum.

Input is the unchanged original result ZIP, SHA256
`39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f`.
The selected member is
`qualification/cases/case_00/candidate_03/native.db`, 1,523,712 bytes,
SHA256 `41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2`.
No actual SQLite connection is opened locally.

The AWS worker uses a read-only immutable connection, query-only mode,
disabled trusted schema and a SELECT-only authorizer. It exports the stored
20 tables and records all 36 immutable triggers. Opaque artifact bytes remain
base64 bytes; no tensor/model loader runs. The source constructor is not used.
The exporter checks that the database and input archive remain unchanged.
The stored image cannot recover uncaptured caller/process state.

The new launcher reuses the byte-pinned cloud lifecycle through a private
module with explicit inspection callbacks. Inner CHQ-named receipts refer only
to transport; they do not claim a new qualification. New source, job, request,
standing authority and budget reservation are bound separately. No automatic
retry. No merge, push or deployment.

Resource envelope: one g7.2xlarge, $4 conservative reservation within the
existing $400 campaign cap. Read-only inspection phase: 180 seconds maximum;
whole remote Python process: 600 seconds; inherited outer instance limit:
3600 seconds with independently scheduled shutdown. GPU hardware is not used
for model computation in this inspection. No T4 or laptop neural work.

Pure checks: `checks_001/receipt.json`, stdout and stderr record **153 passed**
in 2.48 seconds. Fake SQL/provider objects and opaque byte checks only;
SQLite, neural/provider imports and network operations were blocked.
The two source files, two test files and check runner were unchanged during
that capture; the canonical ledger was unchanged.

Registration is produced by `register_launch.py` without provider calls or a
reservation. `registration_001/capture_parent.py` is a PAID one-shot entrypoint
after registration: never run it again after its start marker exists.
Actual provider/execution results belong in `execution_001/`, with the reused
lifecycle under `execution_001/lifecycle/`.
