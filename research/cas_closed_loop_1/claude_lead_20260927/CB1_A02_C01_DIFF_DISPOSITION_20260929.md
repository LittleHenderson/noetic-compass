# CB1 / PRIMARY-AUTONOMY-24H-01/A02: disposition of Codex C01 object `e373ef1b1931c674616ef53d06703ff1027de550`

Prepared 2026-09-29 by Claude (`session_011hJxopymaeoPQ67KvchtwW`). Packet A02 activated 19:16:21Z on delivery of
the object (Codex comment 5896960640). Read-only; nothing run; no Codex file edited. Parent `1b89af69`; only three
files differ: `cas_hh_rde_01/diagnostic_admission.py` (232 lines, sha256 prefix `6491f2e35ff4`), `aws_worker.py`
(225, `95c97f639ddc`), `aws_runner.py` (597, `d81f9fd4239c`). My six leased files match `1ec610f3` (6/6).

## Verdict

`BLOCKER` for `e373ef1b` as frozen source; `PASS` on all five requested focus areas once one line is removed.

### Blocker (deterministic, both stages)

`aws_runner.userdata`, staged branch: the transient unit is started with `--property=LimitFSIZE=16777216`.
`LimitFSIZE` is the per-file size limit (RLIMIT_FSIZE) for every process in the unit and is inherited by pip
and the venv Python. The worker installs `torch==2.11.0` from the `cu128` index inside the unit; the wheel and
its extracted shared libraries are hundreds of megabytes, so the write fails with `EFBIG` and the job dies at
`COMMAND_FAILED:torch` before any test. The cap also contradicts the worker's own 32 MiB `outputs.tar.gz` bound.
Smallest fix: drop the property. Log and output totals are already enforced by `output_bounds()`
(`TOTAL_LOG_BOUND` 16 MiB, `TOTAL_OUTPUT_BOUND` 64 MiB) and the archive check.

### PASS items (as source)

- CPU separation: profile A pins `c6i.xlarge`, `parent_sha256 None`, forwards 0, status `PASS_CB1_CPU_CONTRACTS`;
  runner `EXACT_GPU_COUNT` = 0 for A; payload member set excludes `parent.pt` for A; worker
  `CPU_PROFILE_MUST_NOT_STAGE_CHECKPOINT`, `CUDA_VISIBLE_DEVICES=''`, `HELM_DIAG_TEST_DEVICE=cpu`; the A branch
  ends after `canonical_parts_export` and never calls `passive_witness`; runner requires forwards 0, updates 0,
  reload `NOT_APPLICABLE_NO_MODEL`.
- Staged admission: `staged_authority` (approval hash `aa436e…`, id, allocation, >= 1800 s before
  `2026-09-30T18:39:47Z`); `validate_staged_freeze` pins every profile field, runner/cap/region/account, three
  receipt hashes, canonical byte-equal reservation, exact-commit `source_review.json` PASS, `runtime_receipt.json`,
  cost bounds, 44 dependencies against `DEPENDENCIES.txt` `41b403ea…` (local parse: 44 `name==version` lines,
  hash matches). Historical `validate_freeze` path unchanged. `reserve_staged` exclusive-create, ledger allow-list.
- Per-stage test IDs: from `STAGED_VALIDATION_REQUEST.json`; 108 unique for A, 62 for B (21+24+17); three
  prerequisites inside the 62; `NO_FITTING_STAGE_A` excludes `test_binding_edits`/`test_reconstructor`. Worker
  verifies staged test-source hashes, collects with `--rootdir`, compares full node IDs, runs the three
  prerequisites first (`{3,0,0,0}`), deselects them, requires the exact total. JSON identity order differs from
  `stage_a_expected_nodeids.txt` (same set); the code uses the JSON.
- Worker timeout and collection: setup clamped to 900 s; per-command wall with process-group kill;
  `RuntimeMaxSec=1380`; cgroup limits set by systemd and re-read by the worker (`ACTUAL_CGROUP_LIMITS_REQUIRED`);
  `output_bounds()` while commands run; `verify_staged_archive` checks paths, expanded size, exact receiver
  inventory, per-file hashes, public/terminal equality, JUnit identity.
- B prerequisite (design): slot 3, Stage A reservation, `stage_a_gate.json` with `PASS_CB1_CPU_CONTRACTS`,
  `{108,0,0,0}`, `collection_verified`, `independent_cleanup_verified True`, provider cleanup receipt hash.
  No producer of that file exists in this diff (`verify_staged_archive` returns `independent_cleanup_verified:
  False`); B fails closed until a read-only provider reconciliation writes it.

### Non-blocking findings

1. Exact production-instance ID pin skipped for staged plans; per-row checks remain; restore an exact ID set as a
   profile field.
2. `source_review.json` accepts one reviewer (`Claude` or `DeepSeek`); dispatch expects both A02 and D02.
3. `systemd-run --wait` exit-status propagation and the clean service environment (`PATH`, no `HOME`) belong in
   the runtime attestation on the pinned image.
4. JUnit names stay `fixture.xml`/`focused.xml`; the request says `preflight.xml`/`contracts.xml`. Code is
   self-consistent; the document differs.

## Claim states

Real: hashes, line readings, local text parse of `DEPENDENCIES.txt` and the request JSON. Written NOT RUN: 108 +
62 identities. Reported by Codex, not verified by me: provider prices and ledger hashes `ddf8a7…`/`7e7c3a…`, which
are not in Git. Not done: any edit to Codex's files, any freeze, reservation, launch or spend.
