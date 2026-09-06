# Saved native failure: AWS read-only inspection

## Result: exact failure located; repair not yet attempted

The AWS export completed successfully. Six committed native ticks were stored
in the failed candidate: A, B, C, R, C, R. The first five accepted one Effect
each. At tick 6, R produced L0 instead of the authored L1 target; the verifier
recorded REPAIR / SEMANTIC_OFF_AXIS, published no Effect, and opened a repair.

Two gaps are separate: the actual output mismatch and the generated wrapper's
missing repair continuation. All readiness axes remained SUFFICIENT. WISDOM
is the default repair axis for this mismatch, not proof of missing knowledge.
The intended L1 target must not be replaced with L0 to manufacture success.

`analysis_001/REPORT.md` and `analysis.json` record the checked six-tick
chain. The analyzer verified 73 payload JSON hashes, 6 public-payload hashes,
13 opaque byte records (including metadata-bound artifact identities), state
and trace chains, final head, receipt ownership and expected-label links.
This is analysis of the saved image, not an independent neural replay or a
full native-store validation. The earlier 21 ticks in four completed executions
remain separate evidence. No new full-task success or learning is claimed.

`repair_path_review.md` identifies the existing supported next attempt: C on
the exact repair subgoal, then resumed R with the original repair ID and L1
expectation. Its success is unproven. The unexecuted subgoal's full Cause and
outer caller stack were not saved in this database; exact reconstruction of
the subgoal must be checked before a copy-based attempt. A complete wrapper
integration also needs explicit multistep budget and trace checks.

## Actual run and cleanup

- Job: `cas-meta2-20260906162339-56837284`.
- Parent/worker source: `37c591f3d6ae0606b27334c26d4392e0da94c675`.
- Instance: `i-048a3cc3dfddf75e6`; parent exit 0.
- Result archive: `execution_001/lifecycle/cloud_artifacts.zip`, 127,026 bytes,
  SHA256 `fe2a65efe0dc9119ffdc29cf5931e5e6b550774471747e4634dd53ce510862b3`.
- Exported database image: unchanged; 20 tables, 56 schema objects, 88 rows.
- Provider check: `provider_check_001/receipt.json`, 15 checks passed using
  13 read-only provider calls. Instance terminated, no job volumes, temporary
  access resources and inputs removed. Three result objects and bucket remain
  under the observed seven-day expiration rule; future deletion is not claimed.
- Termination confirmed: `2026-09-06T16:30:36.302749+00:00`.
- Launch-attempt-to-termination interval: 380.815727 seconds at $2.52/hour.
  Estimated EC2: $0.2665710089, not an invoice; excludes other AWS charges.
- Ledger revision 15: $94 reserved, $306 unreserved within the $400 cap.
  The $4 reservation is retained and is not an actual $4 bill.

Accepted source, model and verifier were unchanged. The original qualification
remains refused. Earlier held-out CAS 0/72 and familiar-program 24/24 results
remain separate. No new training, automatic retry, merge or deployment followed.

## Scope and reproduction

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
