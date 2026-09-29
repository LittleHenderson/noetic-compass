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

## Successor `a4552e532b3008dea3f66dbc04df4f40167f489b` (Codex comment 5897023202): `PASS`

Parent `e373ef1b`; same three files only (`diagnostic_admission.py` 253 lines `259ad8465488…`, `aws_worker.py` 245
`a85fd8e8a572…`, `aws_runner.py` 657 `a457f4b1e6e8…`); six leased files unchanged (6/6). Disposition posted:
Stage A `PASS` as source; Stage B `PASS` as source, execution gated by the code on Stage A evidence and the runtime
receipt.

- Blocker cleared: `LimitFSIZE` removed (zero occurrences); staged commands use piped stdout/stderr with a selector
  loop bounded by `max_log_bytes` (`TOTAL_LOG_BOUND`), deadline and process-group kill retained.
- B prerequisite producer added: `inspect_staged_cleanup(directory)` (read-only provider inspection; instances
  terminated, SG/schedule/profile/roles provider-not-found, no tagged volumes; writes `INDEPENDENT_CLEANUP_*.json`).
  `validate_staged_freeze` for B binds `stage_a_gate.json` to the actual execution/terminal/receiver/cleanup files
  by path+hash and re-derives job id, status, `cleanup_complete`, forwards 0, updates 0, tests, receiver hash,
  cleanup receipt hash.
- Admission tightened: payload pins `constraints.txt` `41b403ea…` and `legacy_source.zip` `38761e95…`; Stage A
  refuses checkpoint-suffixed members in both nested archives; profile pins `max_checkpoints`/`max_inputs`/
  `max_conditions`/`max_fitting_steps 0`/`max_real_active_edits 0`/`maximum_model_jobs 3`/`max_raw_capture_bytes`;
  `staged_authority` re-checked before the first paid mutation and immediately before `run_instances`.
- Canonical export now uses `contracts.canonical`.
- Open, non-blocking (unchanged): exact production-instance ID pin skipped for staged; single-reviewer PASS gate;
  systemd-run exit/env attestation; JUnit names vs request. New fail-closed condition: legacy archive must contain
  no checkpoint-suffixed member.

Claim states: real, hashes and readings from the objects; written NOT RUN, 108 + 62; reported by Codex, not
verified by me, prices, ledger hashes, image Python identity. A02 about 12 of 30 active minutes used.

## Candidate `0a6eca5dabb4b60854e917a8d5efc7fa540798ff` (Codex comment 5897085832): `PASS`, supersedes `a4552e53`

Parent `a4552e53`. Changed: `diagnostic_admission.py` +3 (`8c978603666f…`), `aws_runner.py` 14 lines (`c2adc9f52365…`),
new `STAGED_SOURCE_PROJECTIONS.json`; `aws_worker.py` unchanged (`a85fd8e8a572…`); six leased files unchanged (6/6).
The fail-closed condition I named materialised: the original legacy archive `38761e95…` holds 9 old checkpoints, so
Codex split it per stage. Code delta: profile pins `legacy_parent_archive_sha256` (original) and per-stage
`legacy_source_sha256` (`0f8bde13…` A, `e728bc51…` B); payload check uses the per-stage pin; the no-checkpoint scan
now runs on both nested archives for both stages (`NO_CHECKPOINT_IN_SOURCE_ARCHIVES`). Projections parsed: A keeps
255 entries, drops the 21 `records/` entries (3 course/tokenizer/development JSON, 9 `.pt`, 9 metadata JSON,
`body_read: False`); B keeps 258 = same 255 (equal hashes) + the 3 course files, drops the 18 practice checkpoint
entries; no checkpoint-suffixed entry retained; both keep the two frozen wheels, `requirements-gpu.txt` and the 174
`CAS_META_2_COMPOSITION` entries. Record states `tests_run 0`, `checkpoint_deserializations 0`,
`scientific_code_bytes_changed 0`. Grep of the eight Stage A test files and all cube_binding/diagnostic modules at
this commit: zero references to the dropped records. Claim states: real, code delta, parse and grep from Git;
reported by Codex, not verified by me, byte-identity of retained entries and the archive digests (archives not in
Git). A02 about 16 of 30 active minutes used.

## Final candidate `a851851110802a0d4ba4f52daa9d190e96e01fc2` (Codex comment 5897116547): `PASS`, supersedes `0a6eca5d`

Chain `0a6eca5d` -> `d187a3f0` -> `a8518511`; cumulative delta touches only the three transport files
(`diagnostic_admission.py` 262 lines `5d04c7e220b6…`, `aws_worker.py` 251 `15ef8622182d…`, `aws_runner.py` 672
`a1f3039f9319…`), +32/-7, no non-code change; six leased files unchanged (6/6). Delta: `production_instance_ids`
pinned in the profile (`i-02137d196e671b5c1`, `i-0bd0a082507a51ae3`) and enforced for staged plans
(`EXACT_CURRENT_PRODUCTION_IDENTITIES_REQUIRED`) — finding 1 closed; `source_review.json` must carry two reviews
(Claude and DeepSeek) each naming the exact commit with `PASS` and a receipt (`BOTH_ACTUAL_SOURCE_REVIEWS_REQUIRED`)
— finding 2 closed; `runtime_receipt.json` must carry `systemd_wait_exit_status_verified` and
`service_environment_verified` — finding 3 now a required gate; `inspect_staged_cleanup` re-reads the exact recorded
instance ID (terminated, tag equal; NotFound accepted only after recorded termination), `storage_retained` honest;
`output_bounds()` tolerates a file removed between listing and stat. Doc-only mismatch on JUnit names remains.
Claim states: real, hashes/chain/delta from Git; reported by Codex, not verified by me, archive byte-identity, prices,
ledger hashes, image identity. A02 about 20 of 30 active minutes used.

## C02 object `e16c00edc7861c432211f26f9847db9f4046cb2b` (Codex comment 5898089682): changed-scope check, `PASS` for the worker delta

Parent `a8518511`. Five files: new `runtime_attestation.py` (421 lines), `test_runtime_attestation.py` (316),
`RUNTIME_IDENTITY_EVIDENCE.json`, `RUNTIME_ATTESTATION_C02.md` (168), and an 11-line `aws_worker.py` delta;
`aws_runner.py` and `diagnostic_admission.py` byte-identical to `a8518511`; six leased files unchanged (6/6).
Worker delta: `run(..., expected_returncode=0)`; only 0 or 7 allowed; 7 only for label `runtime_probe` with
`argv[0]=='/usr/bin/systemd-run'` and `--runtime-child` present; failure test `returncode != expected`; all sixteen
existing `run(` calls keep the default 0, so the 108/62 runs and the witness are unchanged. Nothing wired: no write of
`runtime_receipt.json`, no call into `validate_staged_freeze`; the freeze still refuses without measured runtime
fields and both reviewer receipts. 38 synthetic regression specs, outside the frozen inventories, written NOT RUN.
Proposal: boot-only freeze before spend, boot phase with no dependency/contract/model work, runtime freeze
(`runtime_pin.json`) before stage work, same attempt and caps; it moves the measured fields from pre-spend to
post-boot/pre-work; that timing decision is owner-level, not mine; one implementation seam to specify: a bounded,
deadline-limited mid-job exchange for the host's acceptance (the worker has no download path today except the
payload URL). Claim states: real, hashes/delta/grep from Git; reported by Codex, not verified by me, provider record
hash, a2 evidence, and all runtime measurements (recorded `UNAVAILABLE`). A02 about 25 of 30 active minutes used.

## C02 successor `2cf9aeee194cea70dd2afc9d8b1b768deb9b3649` (Codex comment 5898123721): transport unchanged, `PASS` carries; A02 RETURNED

Parent `e16c00ed`. Delta only in `runtime_attestation.py`, `test_runtime_attestation.py`, `RUNTIME_ATTESTATION_C02.md`
(+33/-10). `aws_worker.py` `fc8bc2ec4bc8…`, `aws_runner.py` `a1f3039f9319…`, `diagnostic_admission.py`
`5d04c7e220b6…` byte-identical to `e16c00ed`; six leased files unchanged (6/6). Probe argv still
`/usr/bin/systemd-run … --runtime-child`, matching the worker's exit-7 guard; environment fields now passed by
`--setenv`. 39 synthetic specs written NOT RUN. Disposition posted: PASS carries to `2cf9aeee` for A and B on the
same source-only terms. A02 returned at about 28 of 30 active minutes. No Claude packet active; A03 only for an
owned defect, A04 only on delivered execution evidence. WAIT: owner decision on boot-attestation timing or another
source of runtime measurements (owner/Codex); DeepSeek exact-source receipt on the frozen commit (DeepSeek via the
manager's route).

## After A02: Codex C02 successors `c36ffd7a` and `376b3d20`, C02 FINAL RETURN (records only, no packet active)

- `c36ffd7ae3246e4d7a937a524169a67721811557` (Codex comment 5898301940): `diagnostic_admission.py` changed
  (`dc93171f72b4…`, +30/-3: host-fixed canonical ledger path, `require_canonical_staged_ledger`, corrective custody
  binding, Stage A slot `None` / Stage B slot `3` bound in reservation and freeze); `aws_worker.py` and
  `aws_runner.py` byte-identical to `2cf9aeee`; six leased files unchanged (6/6). DeepSeek D01 (on `a8518511`) and
  D02 (on `e16c00ed`) reports added under `cas_hh_rde_01/reviewer_returns/`; they name no defect in my files.
  Posted WAIT note (comment 5898323784): no Claude receipt on `c36ffd7a` without an allocated packet; the 30-line
  delta shows nothing in my scope.
- `376b3d20d4dcd3ad94bb9660582c5dcb55d1f2d4` (comment 5898339507): only unwired `runtime_bootstrap_spec.py`, its
  test file and `D01_DISPOSITIONS_C02.md` changed; transport bytes equal `c36ffd7a`; six files unchanged. Nothing
  posted.
- Codex C02 FINAL RETURN (comment 5898396285, 20:38Z): final source `376b3d20`; 54 specs written (39 runtime, 9
  ledger, 6 bootstrap), 0 run; C03 NOT_STARTED. DeepSeek D02b (on `c36ffd7a`) and D02c (on `376b3d20`) relayed by
  Codex: D01-02 closed on source, D01-01 (circular runtime gate) CONFIRMED/PENDING, Stage A/B admission
  CHANGES_REQUIRED, execution BLOCKED.
- Standing WAIT: owner decision on the same-job boot-only attestation phase (`RUNTIME_ATTESTATION_C02.md`) or another
  source of runtime measurements; Codex wiring of the bounded acceptance exchange and bootstrap; both reviewer
  receipts on the exact frozen commit (a Claude receipt needs an allocation).
- Claim states: real, hashes from the Git objects; reported by Codex, not verified by me, DeepSeek's route and
  dispositions, specification counts, reservation hashes; not done, no test, freeze, reservation, launch or spend
  by anyone that I have verified. 21:30Z check-in: no change.
