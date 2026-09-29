# CB1 / PRIMARY-AUTONOMY-24H-01/A01: version-transition review of the incumbent AWS transport (read-only)

Prepared 2026-09-29 by Claude (session `session_011hJxopymaeoPQ67KvchtwW`) inside packet
`PRIMARY-AUTONOMY-24H-01/A01` (manager dispatch comments 5896439234 and 5896847088). Read-only review of
Codex-owned code; no file of Codex's was edited. Nothing was executed. Purpose: make C01 (the versioned
Stage A / Stage B profiles) easier to finish. Line numbers refer to the files at the frozen executable
commit `af9fb57ec45b2e4202a2fbedb26283fc15a4e16b`:

| File | sha256 | lines |
|---|---|---:|
| `research/helm_self_improvement/cas_hh_rde_01/diagnostic_admission.py` | `018b5263be7d67c05de4305cb12c00ec569a8756684136825481019df96af05d` | 96 |
| `research/helm_self_improvement/cas_hh_rde_01/aws_worker.py` | `5fd9a7d8a44a999d1d5d338debc4b4f90a29b63f3494a236924d2e0c482ea655` | 157 |
| `research/helm_self_improvement/cas_hh_rde_01/aws_runner.py` | `9c9d9b795644f1cff46060c4d10fd2d6f596d0026db032a4f1b52e31c1f101de` | 506 |

Request documents reviewed at tree `1b89af69ce10a8396c10ee6aa1e4ee0f6d31c6b0`:
`STAGED_VALIDATION_REQUEST.md/.json`, `stage_a_files.txt`, `stage_a_expected_nodeids.txt` (108 IDs),
`stage_a_pre_model_nodeids.txt` (3 IDs).

## 1. Stage A cannot load a checkpoint or fall through to the witness

Incumbent state (as source):
- `aws_worker.execute` is straight-line. After the contract tests (lines 99-109) it unconditionally runs the
  witness (`real_parent_parity`, lines 110-112, `--parent parent.pt`), then `retain` (121) and `reload`
  (125-126). The only branch key is `cfg.get('phase')=='parity_corrective_setup'` (line 39); both values
  reach the witness. There is no Stage A exit.
- `parent.pt` arrives through `cfg['inputs']` pins (lines 56-60). The worker env sets
  `CUDA_VISIBLE_DEVICES='0'` (line 36) and installs the `cu128` torch wheel (lines 68-69); it never sets
  `HELM_DIAG_TEST_DEVICE`.
- `diagnostic_admission.validate_freeze` (lines 42-48) pins `phase` to `parity_setup` /
  `parity_corrective_setup`, `instance_type` `g7.2xlarge`, `expected_tests` 62/21, `expected_status`
  `PASS_HH_RDE_PARITY_RELOAD`, `max_packet_forwards` 6, `max_checkpoints` 1, `max_inputs` 2,
  `maximum_all_services_usd` `'2.00'`. Any Stage A freeze fails at `DIAGNOSTIC_FREEZE_FIELD:phase`.
- `aws_runner.execute` accepts a matching terminal only if `packet_forwards == 6`, `optimizer_updates == 0`,
  `fresh_reload == 'PASS_FRESH_PROCESS_OBSERVATION_RELOAD'` and `tests == {expected_tests,0,0,0}`
  (lines 368-370); the worker's exit code is `0` only for `PASS_HH_RDE_PARITY_RELOAD` (line 153).
- The fresh price probe is a literal `g7.2xlarge` / `2.52` (runner lines 248-258) while the launch uses
  `plan["instance_type"]` (line 305). They agree today only because the freeze pins the type.

Exact conditions C01 needs (smallest set):
- A new `phase` value for Stage A in `validate_freeze`'s `exact` table with `instance_type` `c6i.xlarge`,
  `expected_tests` 108, a new `expected_status`, `max_packet_forwards` 0, `max_checkpoints` 0,
  `maximum_all_services_usd` `'1.00'`, and `max_inputs` equal to the exact count of non-checkpoint pins.
  Historical rows unchanged.
- In `aws_worker.execute`: a Stage A branch that ends before line 110 (sets the Stage A terminal status and
  returns), refuses if `(base/'parent.pt').exists()` or any pin path ends in `.pt`, sets
  `CUDA_VISIBLE_DEVICES=''` and `HELM_DIAG_TEST_DEVICE=cpu`, and makes line 153's success test
  stage-aware.
- In `aws_runner.execute`: make the terminal check (368-370) stage-conditional: Stage A requires
  `packet_forwards == 0`, `optimizer_updates == 0`, `tests == {108,0,0,0}` and no reload field;
  derive the price filter and the expected rate from the plan (`instance_type`, a pinned
  `compute_hourly_usd`) instead of the literals, so the probe and the launch cannot drift apart.

## 2. Actual 108 / 62 inventory and the three prerequisite fixtures

- The 62 incumbent contracts are exactly `test_observation.py` 21 + `test_diagnostic_configuration.py` 24 +
  `test_diagnostic_intervention.py` 17. Stage A's 108 = those 62 + 46 CB1 (19 + 9 + 2 + 6 + 10). The three
  prerequisite IDs all lie inside the 62, so Stage B can reuse the same preflight.
- Incumbent collection identity compares bare test names (`rsplit('::',1)[1]`, lines 87-90) and `len == 62`;
  `counts()` (48-53) and the final identity check (107-109) also use bare names. For Stage A compare the full
  `file::name` node IDs against `stage_a_expected_nodeids.txt` (no extra, missing, duplicate, skipped,
  xfailed), then require `len == 108`. Names are unique today, but the request's rule is the full ID.
- Incumbent runs one prerequisite fixture (lines 92-98, `PCBA_FIXTURE_GATE`) and deselects it once (101).
  Stage A needs the three IDs from `stage_a_pre_model_nodeids.txt` in that order into `preflight.xml`
  with `{'tests':3,'failures':0,'errors':0,'skipped':0}`, then three `--deselect` flags into
  `contracts.xml` requiring 105, and `counts()` summing `preflight.xml + contracts.xml` to 108.
  Generalising the single fixture into a list serves both stages.

## 3. Preserved dependency and source pins

- Keep: input pins by size and sha256 (worker 56-60); `legacy_source.zip` and `source.zip` extraction (62);
  frozen native wheels (70-72); harness pins `pytest==9.0.2`, `pydantic==2.12.5`, `pydantic-core==2.41.5`
  (77-80); runner self-hash `launcher_sha256` (122-123), payload hash and byte count (124-126),
  `package_source_commit == source_commit` (106).
- Gap for Stage A: `constraints.txt` (line 67) and `exact_dependency_inventory` (81-84) are applied only when
  corrective. Stage A must apply the 44-pin constraints (`DEPENDENCIES.txt`, sha256
  `41b403ea97579e2c7c76a052d7839eec0305ae36680f9e44848ccf11c3dda126`) and the inventory assertion too.
- Same pinned torch package on CPU: keep `torch==2.11.0` from the same index; no replacement wheel. The
  request's pre-spend items (image ID, Python 3.12 patch, wheel hashes) are not in the incumbent and must
  be plan fields checked before `ATTEMPT_STARTED.json` (runner line 130).

## 4. Expiry, deadline and output limits

- Time chain already enforced and reusable for both stages: `hard_wall_seconds` 1800 (freeze), OS shutdown
  `+28` minutes and bootstrap `timeout 1620` (runner 87-89), scheduler termination at
  `scheduler_after_seconds` with `MaximumRetryAttempts 0` (331-335), operator loop `operator_seconds` 1500
  (340), worker total 1380 with per-command clamp `min(maximum, 1380 - elapsed)` (worker 40-42).
  `PRICE_WALL_BOUND` (admission 68) is generic and holds for `0.17 x 0.5 = 0.085 <= 1.00`.
- Numeric mismatch: the incumbent setup maxima sum to 990 s (venv 90 + torch 600 + wheels 90 + requirements
  180 + harness 120 minus nothing) while the request states dependency setup `<= 900 s`. C01 should set a
  setup sub-budget in the worker or correct the request figure; the global clamp already prevents overrun.
- Output limits enforced: archive `<= 32 MiB` (worker 146; bootstrap emergency upload 76), collected object
  `<= 1 GiB` (runner 447), failure receipt `<= 16 KiB` (353). NOT enforced: the request's `logs <= 16 MiB`;
  stdout/stderr files (worker 44) are unbounded until the archive bound.
- NOT enforced anywhere: `MemoryMax`, `MemorySwapMax=0`, `CPUQuota`. The bootstrap runs the worker under
  `timeout` only (runner 89). The request itself says the versioned transport must enforce these. Smallest
  change: wrap the worker call in the userdata in a scoped unit (for example `systemd-run --scope -p
  MemoryMax=6G -p MemorySwapMax=0 -p CPUQuota=400%` for A, `24G` / `800%` for B). A Python check is not a
  hard process-memory limit; only the OS-level scope is.
- Approval expiry `2026-09-30T18:39:47Z`: no calendar check exists in the incumbent. Smallest change: a
  plan field `approval_expiry_utc` pinned per profile and one refusal in `aws_runner.execute` before line
  130: `utc() + hard_wall_seconds > expiry` refuses with a named code.

## 5. Stage A cleanup before Stage B

- The runner's `finally` block already produces the machine-checkable evidence: terminate (407), confirm
  terminated within 150 s (408-419), collect all outputs with archive hash and byte match against
  `terminal.json` (423-459), dependency deletion only if `cleanup_safe and collected` (460-479),
  `cleanup_complete` (486), exit 0 only if `status == expected_status and cleanup_complete` (493).
- Stage B admission should therefore require, in `validate_freeze` for the B profile: path + sha256 of Stage
  A's `execution.json` with `status == <Stage A expected_status>` and `cleanup_complete == True`, plus the
  collected Stage A `terminal.json` with `tests == {108,0,0,0}` and `packet_forwards == 0`. The incumbent
  already has this pattern for the corrective slot (`original_reservation_path` /
  `original_reservation_sha256`, admission 62-65); mirror it.
- The global concurrency scan (runner 221-245) independently blocks B while any non-exempt instance,
  including a leftover Stage A instance, is not terminated.

## 6. Zero fit and zero real active edits

- Stage A: none of the eight files calls `fit`; my 9 reconstructor and 6 binding-edit cases are excluded and
  none of their IDs is in the 108. `test_plan_connection.py` composes a synthetic `Plan` through my composer
  against a small synthetic host, which the dispatch allows; no HELM checkpoint exists in Stage A.
- Stage B: the worker never imports `cube_binding`; `max_optimizer_updates 0` is pinned in the freeze and
  `optimizer_updates != 0` refuses (`EXACT_PARITY_REQUIRED`, worker 116-117). The result dict starts with
  `packet_forwards 0` / `optimizer_updates 0` (33-34) and only the witness updates them (114), so a Stage A
  branch that returns before line 110 reports 0 / 0 by construction.

## 7. Single extra Stage B slot and no retry

- Slot pattern to mirror: `reserve_corrective` writes `parity_02_corrective.json` with exclusive create
  (`open('x')`, admission 94), refuses unless the ledger holds exactly `{parity_01.json}` (85), and pins
  `model_job_slot 2` / `maximum_model_jobs 2` plus the allocation dict (78-81); `validate_freeze`
  re-checks those in the corrective branch (58-65).
- Stage A reservation: a new `reserve_stage_a` writing one file with `reserved_usd '1.00'`, bucket
  `stage_a_contracts`, no model slot field, refusing unless the ledger holds exactly
  `{parity_01.json, parity_02_corrective.json}`.
- Stage B reservation: `reserve_stage_b` writing one file with `reserved_usd '2.00'`, `model_job_slot 3`,
  `maximum_model_jobs 3`, allocation `{original 2, corrected 2, stage_a 1, stage_b 2, remaining_discovery 1,
  readout 2, cleanup 2}` = 12, refusing unless the ledger holds exactly the three prior files and the Stage A
  execution record passes item 5.
- No-retry mechanisms already present and reusable unchanged: `ATTEMPT_STARTED.json` exclusive create
  (runner 130), one `run_instances` call with `ClientToken=job` (306, 327), SDK `total_max_attempts 1`
  (133), scheduler `MaximumRetryAttempts 0` (335), worker `AWS_MAX_ATTEMPTS=1` (35), `pip --retries 0`.
  Each stage needs a fresh `job_id` (`helm-cb1-contract-20260929-p1`, `helm-hh-rde-passive-20260929-p3`)
  so the token and the per-directory attempt guard are new.

## Where it touches my contracts

Stage A carries my 10 `test_role_schemes.py` cases at `166545eb…` and the 41 RDE cases at `54dac34e`
bytes; the 15 fit-dependent cases stay out. Nothing in my six files needs a change for either stage.

## Claim states

- Real: the three file hashes above and every line reference, read from the Git objects.
- Written NOT RUN: all 108 Stage A identities and the 62 Stage B identities; nothing executed here.
- Not done and not mine: any edit to Codex's files, any freeze, reservation, launch or spend.
