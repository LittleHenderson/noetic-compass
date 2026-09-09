# tksCAS — Changelog

Monorepo-level log. Subprojects keep their own changelogs
(`cas-forex/CHANGELOG.md`, `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`,
`book/CAS_PCBA_Engineer/CHANGELOG.md`). This file records cross-cutting campaign milestones.

## 2026-09-09 - Graph-first ^6 paid attempt 003: clean lifecycle; preserved error #2 (tokenizer list contract)

Attempt 003 (`cas-meta2-teaching-graph-20260909024008-f27c195e`, `$4.00`
reserved, ledger 25 → 26: `$154.00` reserved, `$246.00` unreserved) ran a
fully clean lifecycle — launch, wait, collect, and cleanup with **zero
leftovers** — and the worker's **original inner error was preserved verbatim
again**: `PolicyContractError: LOSSLESS_TRAIN_INPUT_INVALID` (the frozen
tokenizer's `fit_train` requires a `list`; the encoder passed a `tuple`).
The error-capture path is now proven repeatedly, and each paid attempt peels
exactly one real defect.

- **Fixed** (`27f5efff`, a package member): `fit_train(list(texts), ...)` with
  a source-level regression test. **New corrected package** (`c0e26e9a`,
  `package_003/`): source `27f5efff…`, archive `a4c07dda…`, manifest
  `1f554acf…`.
- A corrected re-attempt needs a new job, a new `$4.00` reservation, and a new
  owner record binding the NEW identities. **No retry was attempted.**
  Evidence: `training_mode_001/ATTEMPT_GRAPH_003_FAILURE.md` + receipt.
- Binding-fit attempt-004 request still pending; attempt 003's lost error
  remains UNKNOWN (hypothesis-only).

## 2026-09-09 - Graph-first ^6 paid attempt 002: lifecycle worked; original inner error PRESERVED (explicit-enable gate)

The corrected attempt (`cas-meta2-teaching-graph-20260909021717-7891f672`,
`$4.00` reserved, ledger 24 → 25: `$150.00` reserved, `$250.00` unreserved)
ran the full lifecycle successfully — the attempt-001 wait/collect defect is
gone — and the worker's **original inner error was preserved verbatim for the
first time**: `ValueError: TEACHING_GPU:EXPLICIT_ENABLE_REQUIRED`. The
teaching-cycle GPU guard requires `CAS_META2_RUN_TEACHING_CYCLE=1`, which the
bootstrap did not export; the run never reached CUDA or training. The
error-capture machinery itself worked exactly as the review demanded.

- **Fixed** (`7eec3604`, all outside the package): bootstrap now exports the
  explicit enable flag; termination wait 300 s → 600 s (one leftover SG from
  the slow shutdown was remediated and verified absent). Launcher suite now 16.
- Package identities unchanged (`fec63492…` / `e6c87689…` / `e435e411…`); a
  corrected re-attempt needs a new job, a new `$4.00` reservation, and a new
  owner record. **No retry was attempted.** Evidence:
  `training_mode_001/ATTEMPT_GRAPH_002_FAILURE.md` + receipt directory.
- Binding-fit attempt 003's lost error remains UNKNOWN; the same guard class
  existing there is not promoted beyond hypothesis. Attempt-004 request still
  pending.

## 2026-09-09 - Graph-first ^6 paid attempt 001: launched, then destroyed by a launcher defect (recorded honestly)

The owner-authorized paid run (`cas-meta2-teaching-graph-20260909011302-e654ae56`,
archive `e6c87689…`) succeeded through preflight, the single `$4.00`
reservation (ledger 23 → 24: `$146.00` reserved, `$254.00` unreserved), and
the launch (`i-0b8e902eab4019ff9`). Then a `NoSuchKey` result poll escaped the
wait loop because the provider was wired with the default fake error class
instead of `botocore`'s `ClientError`; the finally-cleanup terminated the
instance and deleted the bucket while the worker was still bootstrapping. No
training result exists. The account was verified clean afterward (instance
terminated, no security groups, roles/profiles absent, bucket `404`).

- **Fixed** (`4fd22968`): `main()` wires `ClientError`; four regression tests
  (launcher suite 14). The package identities are unchanged (the launcher is
  not a package member), so a corrected re-attempt needs only a NEW job id, a
  new `$4.00` reservation, and a new owner record.
- **No retry was attempted.** Evidence: `training_mode_001/ATTEMPT_GRAPH_001_FAILURE.md`
  and the attempt receipt directory (26 provider events).
- Binding-fit attempt-004 request still pending; attempt 003 CUDA hypothesis
  stays hypothesis-only.

## 2026-09-09 - Graph-first ^6: real adapter chain and finished package (review milestone; no launch)

Per the review mandate, the graph→^6 connection is implemented with candidate
copies only (`ce1a3882`, `22a9e015`): exact module input (graph + question
tokens), candidate decompose module (`_DecomposeTransform`, never the accepted
model), frozen dot-product readout, checker-derived per-op scoring, AdamW over
`operation:^6` (the REAL contract role from `make_operation_contract("^6")`;
`bias_update_head` stays frozen), digest-verified containment. Conditions are
labeled `prompt_framing_only`; budget resolved as 64 steps / 600 s per
condition, totals 128 / 1200 s in ONE job with ONE `$4.00` reservation;
per-op lesson exposure is reported; sealed predictions are recorded before
answers. `aws/graph_training_launch.py` carries every binding-fit execution
fix and runs both conditions sequentially.

- Finished package at freeze `ce1a3882c57400bb72a810c056c4baf978b72db6`:
  archive `52151c8b…`, manifest `0b280175…`, 356,470 bytes, 30 members.
- Full suite **137 passed, 24 subtests passed** (receipt sha `9a2ab5ac…`,
  `training_mode_001/checks_002/`).
- Precise authorization request: `training_mode_001/AUTHORIZATION_REQUEST_AWS.md`
  (job `cas-meta2-teaching-graph-20260909011302-e654ae56`) — **NOT launched,
  NOT reserved**; adapter spec: `training_mode_001/ADAPTER_SPEC.md`.
- Binding-fit attempt-004 request still pending; attempt 003 CUDA hypothesis
  stays hypothesis-only; ledger untouched.

## 2026-09-09 - Graph-first targeted ^6 trainer mode: pure-tested; AWS run request prepared (not launched)

The owner-directed trainer mode exists and is pure-tested (`b2fc91e1`):
`cas_meta2/graph_teaching/trainer.py`. Targets the registered
`cas.cjt.operation.^6.decompose/0.2` module with ONLY the `operator.^6`
plasticity group trainable; every other parameter is frozen and
digest-snapshotted before/after with a containment report that names any
forbidden change. Frozen budget: lr `0.003`, `64` optimizer steps, `600.0`
wall seconds. Training reads train+practice whole-part records only;
`evaluate_sealed()` reads only validation/test post-training. CAS and generic
arms share graphs and answers; only framing differs. The real framework hook
fails closed with `GRAPH_TRAINING_FRAMEWORK_HOOK_NOT_BUILT` until the
authorized AWS adapter build.

- Tests: 12 new; full suite **116 passed, 24 subtests passed** (receipt sha
  `0cc529b2`, `training_mode_001/checks_001/`).
- AWS run request registered (NOT launched, NOT reserved):
  `AUTHORIZATION_REQUEST_AWS.md`, job
  `cas-meta2-teaching-graph-20260909011302-e654ae56`, one future `$4.00`
  reservation; adapter build is the funded next step, gated on the owner's
  signed record. Results record: `training_mode_001/RESULTS.md`.
- Binding-fit attempt-004 authorization request remains awaiting owner
  signature; attempt 003's CUDA hypothesis stays hypothesis-only.

## 2026-09-09 - Graph-first teaching candidate landed (pure phase; no training yet)

Owner-directed graph-first candidate, `cas_meta2/graph_teaching/` (`0a8bc7c0`),
pure and deterministic only — no GPU, no AWS, no run, ledger untouched.

- **Owner corrections enforced mechanically:** four pieces (branches ARE
  connectors; `Graph.outgoing` is the only branch API); a node is an idea box
  with a label and contents about itself; a connector's information content IS
  the commonality of its two adjacent nodes (`Relation.content` validated
  against the recomputed commonality); no limit on a node's connectors or
  contents; shared constituents are DIRECT parts in common, nested reach is
  taught separately (REACHED_VIA).
- **Lessons:** binding (color/shape/value + requires/triggers, one-hop,
  two-hop, changed-request) and the whole-part ^6 curriculum (LIST_PARTS,
  FIND_SHARED_PART, REACHED_VIA) over bicycle/cart/wheel-style families with
  renamed, shuffled labels. Deterministic checker computes every answer; no
  answer edges; derived connectors never stored; CAS and generic framings
  share identical graphs and answers.
- **Sealed dataset:** train 48 / practice 16 / validation 16 / test 16, seed
  `20260909`, byte receipt in
  `records/teaching_cycle_001/graph_first_candidate_001/dataset_001/`.
- **Targeted ^6 specialist plan:** real registry target
  `cas.cjt.operation.^6.decompose/0.2`, plasticity group `operator.^6`, all
  else frozen; verification of both the learned skill and update containment.
  Honest gap list: NO trainer mode exists yet; NO AWS run is authorized.
- Tests: 20 new; full suite **104 passed, 24 subtests passed**. The binding-fit
  attempt-004 authorization request remains awaiting owner signature.

## 2026-09-09 - Teaching binding-fit: error preservation demonstrated; environment compared; attempt-004 authorization request prepared (no launch)

Per the owner's instruction, with attempt 003 preserved and its worker failure
left UNKNOWN (the CUDA idea remains hypothesis-only):

- **Error preservation demonstrated through the actual exported worker**
  (`9038087f`, `tests/test_binding_fit_worker_execution.py`): the rendered
  worker text was executed with a real, deliberately failing, non-neural child
  process; the child's original error is preserved verbatim in the failure
  report, survives a second simulated reporting failure, and survives the
  launcher wait/collect path into `training_result.json`. Combined suite:
  **84 passed, 24 subtests passed**.
- **Environment comparison** (`ENVIRONMENT_COMPARISON.md`): the recorded
  successful teaching job 003 used the SAME account, region, AMI
  (`ami-0fbbd0facbc9e3cff`), `g7.2xlarge`, `RTX PRO 4500` plan, python 3.12 and
  torch `2.11.0+cu128` stack as this check. Actual differences: job 003
  retained bootstrap/environment evidence while this check's worker retained
  none, and NEITHER record contains an independent CUDA observation (job 003's
  own receipts say `provider_identity_proved: false`). No driver fix is
  proposed; no environment behavior is guessed.
- **Corrected package built** to `package_002/`: archive sha
  `98712cae5ed31bff5740481127116dd4711cde207937b343c847b5561be1df01`, manifest
  sha `7560e33869b823e4bd03bf7d5dea6af2cf259caab052e970f59c2888e830e197`,
  neural source unchanged (`31e78792`). New job
  `cas-meta2-teaching-binding-20260909000105-9e8f0937`, inert request sha
  `fc358d6f2306b28eb1dd29c67d4dba1456ea427bd48900d7f5f1030dd6d1b806`.
- **Authorization requested, not granted, nothing launched, nothing
  reserved**: `AUTHORIZATION_REQUEST_004.json`. Budget, task, candidate
  definitions, and scoring remain the frozen 48-step / 600-second / `$4.00`
  allocation. Ledger unchanged at revision 23.

## 2026-09-08 - Teaching binding-fit attempt 003: launch and bootstrap worked; worker failed; error preservation fixed

The owner authorized one new binding training-fit job
(`cas-meta2-teaching-binding-20260908203112-fb18899f`, request sha
`4cf78769…`, bound by `OWNER_AUTHORIZATION_003.json`, sha `09032ecc…`), with
the frozen 48-step / 600-second budget, the frozen package, and the corrected
launcher. Preflight, the single `$4.00` reservation (ledger 22 → 23: `$142.00`
reserved, `$258.00` unreserved, no refund), and the launch
(`i-0dd72858329273a9b`, IAM readiness check passed on the first poll) all
succeeded, as did the worker bootstrap (venv + torch 2.11.0 cu128 + wheels).
Then the inner runner (`mode.launch`) exited 1, and the original inner error
was NOT preserved — the worker had run it with inherited output, so the
traceback died with the instance. A second defect crashed the lifecycle
summary write (`collect()` and `execute()` both wrote `result.json`), and the
SG deletion raced the shutdown (`DependencyViolation`); that leftover group was
remediated and verified absent.

- **Fixed** (`d031ba61`): the rendered worker now captures the inner runner's
  stdout/stderr (`INNER_RUNNER_EXIT_<code>` + last 1800 chars) into the failure
  report; `collect()` writes `training_result.json`; cleanup waits bounded
  (300 s) for termination before SG deletion. Launcher suite: 43 tests.
- **Deliverables:** before/after training loss and binding accuracy for CAS and
  generic — NOT AVAILABLE (0 optimizer updates completed; no checkpoints). The
  most plausible inner cause (unconfirmed, error lost) is the fail-closed
  `TEACHING_GPU:CUDA_REQUIRED_NO_CPU_FALLBACK` guard.
- **Note:** the rendered worker changed, so any future authorized run requires
  a new package build with new identities. **No retry was attempted.** Claims:
  `training_fit_claimed: false`, `composition_claimed: false`,
  `final_targets_read: false`; frozen negatives `0/72` untouched. Evidence:
  `ATTEMPT_003_RECOVERY.md` and the attempt-003 receipt directory.

## 2026-09-08 - Teaching binding-fit check: attempt 001 refused at preflight ($0), attempt 002 failed at RunInstances ($4 reserved, no retry)

The owner-authorized training-fit check for the teaching campaign
(`records/teaching_cycle_001/binding_fit_training_check_001/`, source freeze
`31e78792`, archive `ddf39e5e…`) built its launcher and ran twice, and both
outcomes are recorded honestly.

- **Attempt 001** (`cas-meta2-teaching-binding-20260908120635-035f9ac7`,
  request sha `7910b607…`): refused at preflight with `AccessDeniedException`
  on `pricing.get_products` — the AWS Price List API only serves `us-east-1`,
  and the pricing client had been built with the frozen `us-west-2` session
  region. **$0.00 spent, no reservation.** Fix committed with a regression
  test (`test_build_prices_client_from_us_east_1`; launcher suite 35).
- **Attempt 002** (`cas-meta2-teaching-binding-20260908191109-dcf939ab`,
  request sha `cdcfcfb1…`): preflight passed (live confirmation of the fix);
  the single `$4.00` reservation was appended (ledger revision 21 → 22:
  `$138.00` reserved, `$262.00` unreserved, no refund by policy); then
  `RunInstances` refused the just-created instance-profile ARN
  (`InvalidParameterValue`, IAM eventual consistency — no verification wait
  existed) and cleanup hit `DeleteConflict` on the role/profile because it
  lacked the detach and inline-policy steps. No instance ever launched; no
  training results exist.
- **Fixes committed** (`73b66079`): `_await_instance_profile` — a bounded,
  verified wait (120 s timeout, 2 s poll, 15 s settle) between the
  `add_role_to_instance_profile` and the single `RunInstances` attempt, every
  poll recorded as evidence; cleanup now detaches the role and drops the
  inline `job-only` policy before deleting role/profile. Three new tests
  (launcher suite 38). Live IAM leftovers (role, inline policy, instance
  profile) were remediated and verified absent.
- **No retry was attempted.** The `$4.00` reservation stands. A corrected run
  — new job id, new request/authority, new `$4.00` reservation — requires a
  new owner authorization; the standing authorization bound a single
  reservation, which is now consumed. Evidence:
  `PREFLIGHT_REFUSAL_ATTEMPT_001.md`, `ATTEMPT_002_LAUNCH_FAILURE.md`, and the
  attempt-002 receipt directory (24 provider events).

## 2026-09-07 - Condition-skill v9: first paid run FAILED at launch, recorded honestly

The first paid run (`cas-meta2-20260907155404-80e827c9`, source freeze
`331f2746`) executed with the owner's authorization. Preflight passed; the
single `$4.00` reservation was appended (ledger revision 16 → 17:
`$102.00` reserved, `$298.00` unreserved, no refund by policy); the launch did
not complete and the instance was terminated and confirmed with the bucket
emptied and deleted. The exact launch error was lost because `execute()` raised
on incomplete cleanup before persisting its result — that defect and two
cleanup defects (already-absent schedule treated as failure; security group
never deleted) are now fixed, and the result is persisted on every exit.
Recovery of the same job (not a retry) removed every straggler, including
security group `sg-0a00c1e60f1b9ab6d`. No training results exist; the
development scorecard remains NO_RUN. **No retry was attempted.** A new run
requires the owner to authorize a new job and reservation. Guarded capture:
**398 passed, 24 subtests passed** (`checks_019`). Evidence:
`records/condition_skill_v9_001/execution_001/RESULT.md`.

## 2026-09-07 - Condition-skill v9: instance bootstrap completed (Lane E)

The paid-run bootstrap inside the provider now: creates/discovers the venv
(CAS_META2_VENV_PYTHON or python3.12/3.11/3), installs torch 2.11.0 from the
frozen cu128 index, both frozen wheels with --no-deps, and
requirements-gpu.txt — all fail-closed with pip --report receipts — then runs
the v9 remote orchestrate with the venv python and uploads a real
results/artifacts.zip plus results/complete.json with genuine sha256/bytes,
including the REMOTE_FAILED path. No placeholder hashes remain. The frozen
torch index is byte-identical across every repo launcher. Guarded merged
capture: **396 passed, 24 subtests passed** (`checks_018`). Ledger unchanged;
no reservation, no run, no neural work yet.

## 2026-09-07 - Condition-skill v9: owner sign-offs recorded, F5 amended, provider re-audit closed

Per the owner's rulings (recorded 2026-09-07): the freeze and single-run
sign-offs are ticked in `preregistration_v9_001.md` (8.1 and 8.3), and F5 was
ruled **Amend now** — `"instance_count": 1` added to the frozen provider
attestation keys, bound by `OWNER_F5_AMENDMENT.json` (old trainer `bfbd3989…`
→ new trainer `4d4ab00a…`), so re-adjudication now enforces the
single-instance bound. The second-pass provider audit (audit_002) found F1/F2/F3
resolved and two new items, both fixed by the integrator: cleanup now deletes
`results/*` before deleting the bucket (a successful run could otherwise end
`CLEANUP_INCOMPLETE_BLOCKS_RESULT`), and `_ensure_bucket` no longer memoizes a
half-hardened bucket. Guarded merged capture: **394 passed, 24 subtests
passed** (`checks_017`). Ledger unchanged; no reservation, no run, no neural
work. Execution still requires an environment able to approve and launch.

## 2026-09-07 - Condition-skill v9: automatic test-point layer landed

Per the owner's directive (`TEST_POINT_DESIGN_2026-09-07.md`), Lane D built the
smallest useful automatic test-point layer: `tools/condition_skill_v9_test_points.py`
plus 14 pure tests. Three outputs, all read-only and never touching a dataset
partition: the startup identity report (OK / MISMATCH / MISSING / NOT_REACHED
per frozen file, with incompleteness never reported as failure), the
per-transition failure record (on the real saved-repair evidence: C tick 7
produced L0 vs the fixture's L2, verifier refused, R tick 8 not reached,
repair open, caller not restored, first observed failed check named), and the
development scorecard (NO_RUN until a trainer result.json exists; malformed
input is MALFORMED, never a fake pass). The three committed files the packet
does not rebind are now pinned by the layer itself. Guarded merged capture:
**392 passed, 24 subtests passed** (`checks_016`). Ledger unchanged; no
reservation, no run, no neural work.

## 2026-09-07 - Condition-skill v9: parallel lanes merged, adapter audited

Parallel-agent lanes (established in `AGENT_LANE_BOARD.md`) completed and were
merged by the integrator:

- **Lane A (provider adapter):** `aws/condition_skill_v9_provider.py` — lazy
  boto3 behind the injected interface; the single owner of the v9 reservation
  path; reserves exactly once through the canonical budget helper (ledger
  append first, then the AWS-side step) and is not wired to any lifecycle
  entrypoint that owns its own reservation; single instance with
  `ClientToken=job` and IMDSv2 required; call-safe cleanup records every
  failure; 26 pure tests.
- **Lane B (independent audit):** `records/condition_skill_v9_001/audit_001/`
  — 0 critical, 1 major, 6 minor, 7 info. Major: reservation ordering is now a
  pinned provider contract. Minor findings resolved by the integrator
  (visible_gpu_count preflight, owner-approval record cross-check, CRLF
  rejection at verify, log-cap documentation, reproduction-tool tracking,
  git-error vs non-ancestor distinction). F5 (trainer attestation key set)
  is deliberately deferred pending an owner-approved pre-run amendment.
- Guarded merged capture: **378 passed, 24 subtests passed** (`checks_015`),
  including the two-phase reservation refinement: canonical ledger append
  first under the budget lock, AWS-side record after, no refund or retry.
  Ledger unchanged; no reservation, no run, no neural work.

## 2026-09-07 - Condition-skill v9 adapter integrated with the real ledger and wheels

A parallel agent's handoff (`records/condition_skill_v9_001/INTEGRATION_CORRECTION_2026-09-07.md`)
was reviewed and merged. It corrected real integration defects in the
preparation code without touching the trainer, dataset, checkpoint rule, or
adjudicator: the launch reader now uses the canonical budget validator and the
real ledger field names (`owner_task_cap_usd`, `total_reserved_usd`,
`remaining_unreserved_usd`) with exact decimal strings; the package builder
uses the correct repository git prefix, binds the 316-file frozen baseline
manifest and ships the two frozen wheels; the remote worker places outputs
where the real trainer requires, preserves failure receipts, and proves neural
imports come from installed wheels. A second reservation for the same job is
refused before provider callbacks. Merged guarded capture: **346 passed, 24
subtests passed** (`checks_013`). Ledger unchanged; no reservation, no run.

## 2026-09-07 - Condition-skill v9 launch adapter complete as pure code

The dedicated v9 launch adapter is finished and guarded: frozen resource plan
and inert launch-request contract; source package builder from exact git
objects with member/size/hash bounds and zip readback; remote worker with
bounded safe extraction, manifest rehash, one trainer run under an independent
600-second process-group kill, allowlisted result collection with a 32 MiB
bound, and failure recorded without retry; launch lifecycle with an inert
plan by default, hash-bound request plus separate standing authority, one-shot
$4.00 reservation under the campaign ledger after read-only preflight, and
cleanup on every exit. The paid path remains inert until the separate AWS
provider adapter exists and the request/authority pair is hash-bound.
Guarded pure capture: **222 passed** (`records/condition_skill_v9_001/checks_011`).
No neural, SQLite, or provider work ran; the campaign ledger is unchanged.

## 2026-09-07 - Condition-skill v9 metric amendment and launcher start

- Owner phase approval recorded and published (`OWNER_PHASE_APPROVAL.json`):
  build the dedicated AWS launch adapter, and pre-authorize one `$4`
  `g7.2xlarge` training run under the `$400` campaign ledger, with ten
  execution gates. The paid run still requires the adapter, an independent
  audit, a source freeze, and a reservation.
- Pre-run metric amendment (`OWNER_METRIC_AMENDMENT.json`): per-bit trained
  accuracy gates now require strictly above `0.5` (binary chance), never
  `0.25`; trained-beats-untrained gates added; joint baseline `0.25`, per-bit
  baseline `0.5`, denominators defined; per-family gate rows and
  initial-versus-trained observations reported separately from the combined
  verdict. Old wording preserved in history; no threshold changes after scores.
- Launcher module one landed: `aws/condition_skill_v9_resource_plan.py` freezes
  the resource plan and validates the inert launch-request contract.
- Guarded pure capture: **179 passed** (`records/condition_skill_v9_001/checks_010`).
  No neural, SQLite, or provider work ran; the campaign ledger is unchanged.

No training result, native admission, repair, caller return, reservation, or
launch is claimed. The 0/48, 0/24 and 0/72 held-out results are untouched.

## 2026-09-07 - Condition-skill v9 corrected against independent audit

The input-dependent two-condition learning candidate froze its dataset and pure
checks, and a read-only audit then found three material pre-freeze defects. All
three are corrected in the CNCM worktree on `codex/cas-meta-2-composition`:

- **Sealed target boundary repaired.** The learner previously hashed every
  dataset partition (including private test targets) before checkpoint
  selection. `bundle.inspect_structure` now validates only the manifest
  declaration and builder-source pins without reading any partition, and
  `read_partitions` reads only the partitions it is given. The trainer's
  pre-seal stage reads only train/validation; private targets are opened only
  after the blind prediction receipt is hash-bound.
- **Required reporting added.** `train.summarize` now emits the first wrong bit
  (bit order respected; NO_EFFECT counts as bit 1 wrong) and equality/unit-
  margin slice reports when scored rows carry margin fields.
- **Deterministic adjudicator added.** `train.adjudicate` assigns
  `PASS`/`FAIL`/`EVIDENCE_INCOMPLETE` from frozen gates: completion status,
  sealed selection, unchanged source pins, constant baseline exactly 0.25,
  integer rule exactly 1.0, trained CAS and generic strictly above 0.25 on both
  test splits with both bits above 0.25, all six evaluation controls at joint
  accuracy 1.0 per family per split, exactly 2,400 steps per family, and a
  matching independent provider attestation. The trainer-side verdict is
  EVIDENCE_INCOMPLETE by design until the outer provider receipt re-adjudicates.
- **Publication packet verifier added.** `tools/verify_condition_skill_v9_publication_packet.py`
  builds and re-verifies the byte-bound packet: strict duplicate-key JSON,
  schema/type/path safety, exact changed-file coverage, source-commit ancestry,
  and byte-count/SHA-256/Git-blob identity per file. Packet bytes are LF-only;
  the monorepo `CHANGELOG.md` is an explicitly allowed bound path, and an
  optional base commit binds multi-commit correction ranges.
- **Dataset re-manifested, partitions unchanged.** All six partition files are
  byte-identical to the revision bound at commit `bc3cdc4b` (manifest
  `edaf3d6b…`); only the embedded builder-source hashes changed (new manifest
  `6b19020c…`).
- Guarded pure capture: **155 passed** (`records/condition_skill_v9_001/checks_007`).
  No neural, SQLite, or provider work ran; the campaign ledger is unchanged.

No training result, native admission, repair, caller return, reservation, or
launch is claimed. The 0/48, 0/24 and 0/72 held-out results are untouched.

## 2026-09-04 - CASformer v0.2 source freeze

- Accepted the GLM execution audit as `CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL`.
- Froze the unchanged 50-file v0.2 controlled source set, its source manifest,
  tests, schemas, demo, and wheel-build configuration under
  `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/`.
- Added the hash-locked CPython 3.14 Windows CPU dependency set and committed
  the frozen 26-file `CASFORMER_v0_1` sibling source required by v0.2.
- Clean wheel installation, pristine-worktree reproduction, blocker attacks,
  and evidence binding remain for a separate evidence commit tied to the
  source-freeze SHA.
- No language capability, general reasoning capability, CAS-specific
  advantage, CNCM brain completion, AGI, or production readiness is claimed.

## 2026-09-02 - CPB-0 DO_NOT_BUILD at $0; the question itself was malformed

Second design retired at zero cost in a row. This one is not "designed badly" - the corpus lacks
the structure the question presupposes.

**The impossibility, measured over three probe worlds.** A payload rule is useful only if it
catches all 36 forgeries and kills 0 honest corroborations. Nothing does, not even the oracle:
`f(topic)` catches 10/36 because the exact-copy forgery inherits the host's payload; per-memory
random catches 36 and kills 60 of 60; hand-written ground truth catches 36 and still kills 35.
Three cases, exhaustive - copied field, fresh field, or the label itself. There is no fourth.

**The sixth shortcut.** Four of six registered statuses were selectable by one line in the corpus
generator, and no gate constrained it - `GATE_LEGIT_CORROBORATION_EXISTS` measures the unrepaired
verifier, which never reads payload, so it passes in every regime.

**Both cheap competitors are dead.** `coherence()` never reads the semantic vector, so an
exact-duplicate check dies at attacker cost zero. `ROOT_NOVELTY` is an insertion-order oracle.

**What actually matters:** a trajectory-only duplicate check kills the attack *and* takes
legitimate corroboration from 444 to 0 - because legitimate corroboration in this corpus IS an
exact trajectory copy. The attack and honest corroboration are the same object in every field the
verifier reads. Corroboration here is content duplication, and treating content duplication as
independent evidence is the defect.

**What I got wrong:** I proposed the payload framing and predicted a one-line fix. Both wrong in
the same direction - I assumed the missing thing was a check when the missing thing is a
representation.

Not redesigned. A cheap mitigation exists and is recorded as a mitigation, never a repair.

## 2026-09-02 - CMB-RP1 DO_NOT_BUILD at $0; the diagnostic is withdrawn

The design was authorized, preregistered, attacked by six lanes the same day, and retired before
anything was built. Every consequential claim re-verified by me before acceptance.

**The curve cannot exist.** `traj_sim` over lengths 3-6 admits only thirteen values; the band
`[0.80, 0.99)` is reachable by exactly two, both at edit distance 1. The verifier's exclusion
rate is a step function of an integer, not a curve. The design's own falsifier fires before a
world runs.

**The diagnostic is misattributed.** On the registered near-miss attack `cond_consistent` fires
0/30, and turning the contradiction band off changes nothing - not one forgery, not one true
memory. The `119 -> 0` headline is the relative margin's work.

**RGM-0.2: numbers stand, explanation withdrawn.** My self-correction came from an adaptive
forgery I built at `0.9375`, which sits inside `DELTA`. True of that attack, not of the one that
produced the headline.

**CMB-RP0: `DEGREE_FILTER` qualified.** Link ties break by ascending `memory_id`. Changing the
forgery prefix from `poison_` to `aaaF` erases the degree signal and inverts its sign. The
verdict is unchanged; one competitor's claim is narrowed.

**Free finding:** an exact copy with a fresh provenance root is authorized 20/20. Corroboration
is judged on the fields the query matches, not on the payload that would be acted upon.

Not redesigned. Total cost `$0`.

## 2026-09-02 - Interlock audited PASS; the last human promise is now a grep

GLM's sixth audit this session, `$0` total across all six. Both named risk points judged sound:
the derived-manifest path takes the pipeline config, not a manifest object, so there is no
manifest-shaped injection parameter anywhere on it; and the residual limit is correctly bounded.

**Its one recommendation is built.** `verify_receipt_clearance.py` is a CI step that fails any
run receipt lacking a bound clearance - the likeliest real failure being a run that simply never
called the gate - and any clearance that does not re-verify against the trigger receipt embedded
in it. `validate_receipt_check.py` proves it on ten receipts: one genuine, nine damaged one
specific way each, all caught.

Built now rather than "the day the first real training launcher exists", so it is audited before
it is needed rather than invented under pressure.

**Still not closed, and said so:** a launcher controlling its own source can lie about everything
consistently. That is impossible in code, and claiming otherwise would be the dressed-up green
row this lane already caught once.

CMB-RP1: technically unblocked, not authorized.

## 2026-09-02 - Trigger PASSED; the interlock is built and the trainer provably stops

Owner ruled the trigger itself PASS at `bc9e89df`, with the alarm bench-tested but not yet wired
to the furnace. It is wired now.

**`T1`'s metric is frozen as a calibration package.** Any future change to it is a
**recalibration event** requiring new population measurements; thresholds may never be carried
across metrics unchanged. `0.80`/`0.99`, the `0/3794` collateral measurement and the `54/108`
forgery-pair measurement were all calibrated with edit distance - swapping the metric leaves the
same digits measuring a different quantity.

**`replay_training_gate.py`** implements the five launcher requirements as a module. The launcher
never writes a manifest: it hands over the config its pipeline emitted and the manifest is
derived from it, so no hand-editable boolean sits anywhere on the path.

**`validate_gate.py` proves it**, and the assertion is not "an exception was raised" but **"the
trainer function never executed"**. All five blocking states: `trainer ran: False`. Clear states:
`trainer ran: True` with the clearance bound into the receipt.

**The limit, stated rather than dressed up:** this defends against mistake, not against a
launcher that deliberately lies about itself. A launcher controlling its own source can skip the
call. An earlier draft of the gate test recorded "a hand-built clearance dict is accepted" as a
*passing* row - a limitation dressed as a success - and that was corrected to a refusal plus an
explicit disclosure.

CMB-RP1 remains blocked.

## 2026-09-02 - External spec-only conformance suite: one real bug, three spec defects

Closes GLM audit finding 1 - the existing suite was the checker validating itself. Eight parties
read only the specification, never the implementation or the existing suite, and predicted state
and exit for 75 fixtures before anything ran. **64 matched, 11 diverged.**

**The real bug:** an unrecognised `--expected-scope` made argparse exit `2` - a code the frozen
ladder does not define, in the same commit whose contract says a launcher must not meet an
undocumented code. Fixed; every invocation error is now `REFUSED`/`10`.

**The finding an author-written suite cannot produce:** three divergences shared one root cause -
`T1`'s similarity metric was never defined. All three authors assumed cosine similarity; the code
uses edit distance. My own fixtures would have used my own metric and never noticed. Now
normative.

**The acknowledgement format was undocumented** - and it is the only path from a blocking state
to exit 0. Now normative, with proof that an ack cannot clear `NECESSARY` or `URGENT`.

**The ladder had no resolution rule.** `T5` true with `T1` fired and `T2` unknown satisfied two
rows at once. Now ordered: `REFUSED` is a precondition gate, not a ladder row; a fired defence
beats an unknown one; `T5` false is `DORMANT` regardless.

**Empty evidence is UNKNOWN, not clear.** Zero measurements is not a measurement of zero.

Three divergences were fixture errors and are recorded as such, including one the author
disclosed unprompted before submitting.

Both suites now run. A future change must keep both green.

## 2026-09-02 - Trigger v0.3: the wiring gap closed, manifests bound to scope and job

The owner found that the `DORMANT` result could not clear CMB-RP1, and was right. A
`PRODUCTION_DEPLOYMENT` manifest reading *no production system feeds training* is true, and
useless as clearance for a development replay job that really does put memories into training.

> "It can truthfully report that the empty production building is safe while the experimental
> workshop next door is actively using the furnace."

The recurring failure class this lane keeps hitting: **the correct field exists, but the
authority path does not read it.**

**Manifests are now scope- and job-bound.** Flag names differ by scope, so one file cannot be
repurposed across the boundary by editing a single field. The launcher declares
`--expected-scope` and `--job-id`, and the checker REFUSES a manifest that does not govern the
job. It also refuses a `derivation: derived_from_pipeline_config` claim with no pipeline config
to verify it, and a declared flag that disagrees with the pipeline. **The pipeline is the fact;
the manifest is a claim about it.**

**`WATCH` is no longer a silent green** - new exit `5`, passing only with an owner
acknowledgement bound to both the job id and the manifest digest.

```
0   DORMANT | CLEAR | WATCH_ACKNOWLEDGED
5   WATCH               needs an owner ack bound to this job
10  WATCH_UNRESOLVED | REFUSED
20  NECESSARY
30  URGENT
```

A machine-readable trigger receipt (`--receipt-out`) can now be bound into the run receipt.

Self-validation 16 -> 25 scenarios, all passing, including the decisive pair: the same
production manifest is REFUSED when a dev job declares its scope, and would have returned
DORMANT without it.

**Stated plainly in the spec:** until a launcher actually calls this, it is a correctly
functioning checker standing beside the machinery, not an interlock inside it.

CMB-RP0 is not retrofitted. **CMB-RP1 may not launch** without its own `DEVELOPMENT_REPLAY`
manifest, derived from its actual pipeline configuration and checked.

## 2026-09-02 - Trigger repaired under owner ruling: four fixes, and a correction to my own wording

**Concept approved, implementation needed four authority/logic fixes.** All applied, and the
self-test now covers 16 scenarios, all passing.

**My wording withdrawn.** I wrote that the admission headline "is a count, not a mean, so it is
not power-limited at all." Too absolute. The counts are exact (`119 -> 0`), but any claim about
future unseen attacks is sample-limited. Rule-of-three 95% upper bounds: `0/119` -> ~2.52%,
`0/3794` -> ~0.08%, `0/358` -> ~0.84%. Corrected to: **the registered attack set was blocked
completely; generalization beyond it remains sample-limited.** "Not a mean" is not "not
sample-limited", and I had run the two together.

**Bench scope bound to the rename.** The status now emits
`status_scope = RGM-0.2_SYNTHETIC_BENCHMARK_FAMILIES` and
`universal_geometry_superiority = false`. "Only" means *among the five families tested*.

**Fix A - direction-free separability.** This was a **documentation** defect, not a code one:
the code always computed `max(AUC, 1-AUC)`, but the spec sentence said "AUC < 0.65", which would
read an AUC of `0.10` - excellent *reverse*-direction separation - as an alarm.

**Fix B - T3 had no authority**, appearing in the condition list and in no decision path. Now on
an explicit ladder where scale escalates `NECESSARY` to `URGENT`. The self-test then exposed a
*second* T3 bug: it read the memory count from the corpus and discarded the manifest, so an
80-memory sample overrode a declared 50,000-memory deployment. Corpus is a sample, manifest
declares the deployment, larger wins.

**Fix C - unknown must stop the machinery.** Exit codes `0` / `10` / `20` / `30`; every nonzero
code blocks a memory-to-training job. If `T5` itself is unknown the state is `WATCH_UNRESOLVED`,
not `DORMANT`.

**Fix D - flag authority.** Production-scoped flags inside an exact-schema manifest with owner
attribution and a config digest. A missing or malformed manifest yields `UNKNOWN`, never
`False`.

**Honesty fix the owner caught:** CMB-RP0 literally put retrieved memories into training, so a
flat `memory_feeds_training: false` was misleading. Recorded separately as
`development_memory_feeds_training = true`. The dormancy now reads honestly: the experimental
bench used memory in training; no deployed system does.

No periodic daemon - event-driven and mandatory at seven named events. CMB-RP0 is not
retrofitted. **CMB-RP1 may not launch unless the trigger is clear or the defence is built.**

## 2026-09-02 - Owner rulings: 12 worlds accepted, geometry status renamed, structural-forgery trigger armed

**12 worlds accepted with the caveat.** The caveat is now a permanent rider on RGM-0.2: the two
winning families are 12/12 and unambiguous; the three losing families are small and
noise-limited and 12 worlds cannot establish their magnitude; and the admission headline
(`119 -> 0`) is a **count, not a mean**, so it is not power-limited. The caveat binds the
geometry comparison, not the admission result - and the admission result is the one that carries
the lane.

**Rename ratified.**

```
GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED     -> CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY
GENERIC_GEOMETRY_ADVANTAGE_NOT_SUPPORTED -> CAS_GEOMETRY_NO_ADVANTAGE_OVER_GENERIC_CONTROL
```

The code emits the new name and also emits the old one as `generic_geometry_status_legacy_name`.
`RGM02_RECEIPT.json` is **deliberately not rewritten** - GLM reproduced it byte-identically and
that hash is the determinism proof. Editing it to look tidier would destroy the best evidence
the result has.

**Structural-forgery defence: deferred build registered, trigger armed.**

The measured gap: the verifier detects semantic contradiction, a degree check detects structural
anomaly, and **neither covers a forgery that is both semantically consistent and structurally
normal.** Not built and not authorized - deferred under the standing `No automatic second
repair`, because in this lane a repair manufactured the next problem four times and building
straight off the measurement would be the fifth.

Six conditions, three computed and three declared. Firing rule: `NECESSARY = T5 AND (T1 OR T2)`
- memory feeds training, and either the semantic band has collided or the structural signal has
vanished. **`UNKNOWN` is not `NO`**: an unevaluated condition while memory feeds training
escalates to `WATCH_UNRESOLVED` rather than passing silently.

Self-validated across 7 constructed scenarios, all passing - and the validation caught a fault
in my own test fixture, not the checker. Current state `DORMANT`.

It is a checkpoint, not a daemon. It fires because the spec sheet is mandated read-first, and
the checker exits non-zero on `NECESSARY`/`URGENT` so it can gate a pipeline.

## 2026-09-02 - CMB-RP0 audited PASS by GLM; lane CLOSED on an honest negative

Independent audit, $0. GLM verified live: spend inside the frozen cap, `PYTHONHASHSEED=0`
pinned, both code mirrors byte-identical (it re-checked the hashes itself). Three findings,
none status-changing; all three dispositioned.

**The diagnostic worth keeping** - the auditor's third finding, now recorded in both benches
so neither can be read without the other:

The same verifier was measured against two different attacks and gave opposite answers.

| | RGM-0.2 (admission) | CMB-RP0 (replay selection) |
|---|---|---|
| attack | ONE adaptive forgery at `0.9375` | 132 cheap lev-1 forgeries |
| defeated by | **consistency** | **graph degree** |
| verifier | `119 -> 0`, `358` true kept | ingests `5.67`; a degree count ingests `4.41` |
| verdict | **earns itself** | **adds nothing** |

**The two-tier verifier detects semantic contradiction, not structural anomaly.** Where an
attacker must make a forgery *agree* with what it impersonates, it wins by mechanism rather than
threshold. Where forgeries are cheap they stop being ambiguous and start being conspicuous, and
nothing in the verifier looks at that.

These are complementary defences; neither substitutes for the other. Nothing here licenses
building the combination - that is what the two measurements jointly imply, and it would need
its own preregistration and owner authorization.

**The structural weakness was findable only because the mechanism-free competitor was registered
before the run.** Without `DEGREE_FILTER`, CMB-RP0 would have reported the verifier beating
`RANDOM` and `NO_REPLAY` and looked like a modest success.

Also fixed: `make_audit_package.py` was still emitting the pre-launch package after the run
completed. It now detects a receipt and emits the close-out record.

```
CMB-RP0 lane      CLOSED
total spend       $0.2039
claims promoted   NONE
negatives deleted NONE
successor round   NOT started -- owner's standing "No automatic second repair"
```

## 2026-09-02 - CMB-RP0 RAN: the two-tier gate earns nothing as a replay selector ($0.2039)

9 registered worlds on an AWS T4. Owner-authorized development run. Hash `f2fbfd0c97df96f7`.

```
SAFETY      TWO_TIER_GATE_EARNS_NOTHING
CAPABILITY  CMB_REPLAY_BEATS_NO_REPLAY_ONLY
PROMOTION   NOT_PROMOTABLE -- 6 of the owner's 8 conditions fail
```

**The authorization tier is dominated by its own retrieval tier.** `CMB_RETRIEVED` is better on
*both* axes - forgets less (`0.1388` vs `0.1518`) and admits fewer forgeries (`5.33` vs `5.67`).
The thing that beats the mechanism is the tier directly beneath it.

**A filter that counts graph edges is safer than the verifier.** `DEGREE_FILTER` - no query, no
semantics, no CAS - ingested `4.41` forgeries against `5.67`. This settles the A2.8 limit
registered *before* the run, and settles it against the mechanism.

**The registered falsifier fired.** Required gap `> 1.0`; measured `-0.33`, positive in 3 of 9
worlds. Per-world: `-1, 0, -3, 0, -1, +3, +1, +1, -3`.

**Three decisive losses**, each in 0 of 9 worlds at `p = 0.0038` - the floor of a sign-flip test
at n=9: to `SEMANTIC_DIVERSE`, `CLASS_BALANCED`, and `CLASS_BALANCED_POOL`.

**Nine worlds answered the power objection both ways**: enough for the effects that exist
(losses at the permutation floor), not enough for the ties with `RANDOM` and `DEGREE_FILTER` -
which per A3.5 are absence of power, never equivalence.

**A control produced its own finding.** `CLASS_BALANCED_POOL`, added hours before launch, is
near-best at preserving old tasks (`0.0429`) and by far the worst under poisoning (`16.00`).
Label-balanced replay is highly vulnerable to label-forgery.

Does not disturb RGM-0.2, which GLM reproduced byte-identically. That result is about admission;
this one is about replay selection. The verifier is good at what it was built for and adds
nothing here.

## 2026-09-02 — CMB-RP0 built (owner items 5 and 6): six construction faults, one disclosed limit, $0

Selective replay against catastrophic forgetting. Built and dev-verified; **not launched**.

Why it matters: a wrong memory *shown* to a user can be dismissed. A forgery mixed into a
*training batch* is written into the weights. Replay is the case the two-tier verifier exists for.

Six faults, every one found by measuring the bench rather than reasoning about it:

- **A1.1** the task was broken two ways — topic is 100% recoverable from the semantic vector
  (`480/480`) and the trajectory carries no topic information (`17/480`, chance `0.0312`).
  Scope narrowed in writing: this tests the CMB as a **selector**, not CAS geometry as a feature.
- **A1.3** my own mechanism-free baseline was a straw man (`0.6291` forgetting vs `RANDOM`'s
  `0.0964`, covering 4 of 22 classes). Replaced; the straw man is kept as an illustration only.
- **A2.1** forgeries had no context vector, so the verifier would have excluded them by a
  missing field rather than by its mechanism.
- **A2.2** the replay pool *was* the training stream, which excludes poison — no arm could ever
  replay a forgery, so the safety test measured nothing.
- **A2.4** degree gave the forgeries away twice, in opposite directions (`12.55` vs `7.42`, then
  `4.00` vs `6.79`).
- **A2.6** `CMB_AUTHORIZED` returned nothing on all 64 slots. Not the disclosed fail-closed
  behaviour: `0` failures on every condition, best coherence `1.0000`. **The verifier was
  correctly returning the query's own source and my harness threw it away.** Third time this
  lane I have diagnosed a mechanism failure that was mine.

One limit disclosed **before** any run (A2.8): the residual degree gap cannot be removed without
faking the graph, so it gets a competitor instead — a new `DEGREE_FILTER` arm using graph degree
and nothing else, added to the safety law. Stated consequence: this bench cannot cleanly separate
*the verifier works* from *my forgeries happen to be low-degree*.

Nothing is licensed and no result is claimed. Not launched, `$0` spent.

## 2026-09-02 - RGM-0.2: ADMISSION_SAFETY_REPAIRED on 12 new worlds ($0, CPU)

Owner reversed my role: I build RGM-0.2, another model audits. Conflict of interest declared -
I audited RGM-0/0.1 and built on my own findings.

Items 1-2. The lev-1 near-miss attack RGM-0.1 could not stop (119 forgeries admitted over 120
queries) now reaches ZERO authorised memories, while 358 true ones are still authorised. A
two-tier split separates RETRIEVED (may be shown) from AUTHORIZED (may influence reasoning or
learning); forgeries still surface as candidates but cannot be acted on.

Item 3. With the control on the identical verifier the CAS geometry advantage survives
drop-one (+0.0672) - but the generic control BEATS CAS on three of five families. The
advantage is concentrated in fragment composition (+0.4108) and independent corroboration
(+0.3190), and survives only because there are two winners rather than one.

Item 4. The mechanism-free gate passes: no query-independent shortcut, answer set not
recoverable from the graph. But plain semantic retrieval already reaches 0.83-0.94 on three
families; the machinery earns its cost at pattern completion (0.0005 -> 0.4167) and
independent corroboration (0.3117 -> 0.9818), and little else.

Three self-corrections on one verifier, each found by measurement after my reasoning produced
a plausible wrong answer. The load-bearing idea: a forgery's signature is not that it is
different, but that it is almost the same.

Disclosed: it fails closed - under adaptive attack nothing is authorised, true memories
included. Not licensed: any claim that CAS geometry helps retrieval generally.

Items 5-6 not built; they were gated on this result and are now unlocked.


## 2026-09-02 - PHASE LANE CLOSED by owner ruling (CMB-P2 not launched, $0)

CMB-P2 closed as CONSTRUCT_INVALID_TWO_HOP_SHORTCUT. The benchmark contained a two-hop
shortcut, so it never required the system to separate thought chains: a phase-free, label-free
rule scored 0.8255/0.8568 against an oracle handed the true labels at 0.7682/0.6797. The
shortcut was created by the repair for the previous shortcut.

Frozen state. CMB-P0 and CMB-P1 preserved exactly, including PHASE_MEMORY_UNSAFE. P8+P9
preserved as a promising engineering observation, NOT as evidence that phase separates thought
chains. The phase hypothesis remains open - neither proven nor disproven. Phase integration
into CMB-R1 is not authorized. Frequency, pulse width and Q are not added to the main memory
system. No immediate phase-benchmark redesign is authorized.

Registered return condition: phase may return only when an independently designed benchmark
proves that ordinary content, one-hop search, two-hop search, topology and candidate identity
cannot solve the task - measured before any phase arm, and re-measured after any world repair.

Total spend across the whole phase arc: $0.2776.

Next active lane: CMB-R1 / RGM-0.2. The production memory board stays scalar and accountable.


## 2026-09-02 - CMB-P2 STOPPED PRE-LAUNCH: a phase-free rule beats the oracle ($0 spent)

The owner authorized one final controlled confirmation of the P8+P9 combination. Adversarial
review returned DO-NOT-LAUNCH, and the decisive finding verified: **a two-line rule that never
looks at which chains are active beats the arm handed the true chain labels.**

  K=2 / K=3      P0 0.4974/0.3464   ORACLE 0.7682/0.6797
                 B_TWOHOP 0.8255/0.8568   B_TWOHOP x amplitude 0.9661/0.9323

The candidate set falls out of the adjacency matrix (recovered exactly in 6/6 worlds), and
while one hop is flat as intended, two-hop mass identifies the gold at ~2.3x its nearest rival.
I built that shortcut myself in the repair for the previous one: replacing the cue's private
one-hop edge with 0.65-weight edges from the cue's own chain to its completion IS a two-hop
signature.

WITHDRAWN: the claim that the task requires chain separation, and the "% of oracle" framing.
PRESERVED: PHASE_MEMORY_UNSAFE for CMB-P0 and CMB-P1, every measured number, and every
arm-vs-arm comparison - no arm uses the shortcut, so all were equally blind.

Not fixed-and-launched: flattening two-hop mass removes the chain-specific evidence entirely,
so the oracle could not solve the task either. That is a world redesign, which the directive
prohibits. Owner decision.

Also: a verifying agent read held-out worlds 506-512, so the held-out range moved to 536-565.

Verified as NOT defects: the phase-shuffle control is fair and informative - in the
no-information limit shuffling is an exact no-op (gap 0.0000) and the collapse scales with real
structure.

Third label-free shortcut found in this bench family. The standing rule found it again: a win
by mechanism M is uninterpretable until it beats the cheapest method without M.


## 2026-09-02 - CMB-P1 phase repair bench: PHASE_MEMORY_UNSAFE, no repair survives ($0.1135)

Owner-authorized repair bench (R4). Three repairs tested separately: signed coupling,
frequency heterogeneity, and a trajectory readout. **None survives.**

The sharpest result: **at convergence the phase engine is numerically identical to the scalar
engine** - 0.503/0.343/0.251 at K=2/3/4, matching P0 to three decimals, with merge fraction
1.000 at every K. The CMB-P0 numbers were a transient; this is the destination.

P7 genuinely fixes synchronisation (global order 0.218 vs 1.000) but buys attribution by
destroying retrieval. P8 came closest, failing one criterion narrowly. P9 has a global order
parameter identical to P4, confirming it repairs the readout and not the dynamics.

P8's structural claim is NOT supported: shuffling the frequency values across nodes costs only
~0.05, so the benefit is desynchronisation rather than structural coding. The controls carried
for exactly this purpose caught it.

The exploratory P8+P9 combination reaches 90/84/77 percent of oracle accuracy with near-zero
merging, beating the tag arm on both axes - but it carries no verdict by construction, and it
has no shuffle control in this run, so it is an unverified number rather than a result.

A first launch cost $0.14 and returned nothing: it finished all GPU work then crashed writing
the receipt, and the partial-receipt guard was scoped too narrowly to save it. Root cause was
testing run_world() but never main(). Fixed, with an end-to-end test added.

Not licensed: any resonance or CAS-specific claim, any P8P9 claim, anything beyond these
synthetic worlds, or any merge into CMB-R1. Next step is a third-party audit.


## 2026-09-01 - CMB-P0 multi-chain phase bench: PHASE_MEMORY_UNSAFE (AWS GPU, $0.0241)

Owner-authorized side bench. Asked whether phase-coded two-state memory separates
simultaneous overlapping reasoning chains better than a scalar engine, explicit tags, the
same extra state without phase, and its own phase-destroyed control.

**Result: the phase arm beat every control at every K, and was still refused.**
`P4_PHASE_OSCILLATOR` won all five registered comparisons at K=2/3/4 - the pattern for
`PHASE_MULTICHAIN_SIGNAL` - but the pre-registered safety override fired first: it collapses
0.657 / 1.852 / 3.538 distinct chain pairs at K=2/3/4 (3.54 of 6 possible pairs at K=4) in
20/20 worlds, against a threshold of 0.50, versus 0.000 for the oracle. It retrieves better
while losing track of which chain it retrieved from.

Contamination is *not* the defect (P4 is better than P0 at every K). Secondary negatives:
extra state alone buys nothing, and *inferred* tags are worse than no tags while *oracle*
tags are far better - inference, not the tag mechanism, is the bottleneck. GATE_ORACLE
failed at K=4 (0.560 < 0.60), so that stratum is ill-posed; the verdict does not depend on
it and is decisive at K=3.

**The bench was stopped pre-launch by its own adversarial review and rebuilt first, at $0.**
Three reviewers found - and measurement confirmed - that the gold answer was recoverable
from one edge weight in 1152/1152 dev queries, that the 64 queries per world were only 2-4
distinct, and that K=2,3,4 were pooled into one bag tolerating 18 negative worlds (the same
defect this project raised twice against a sibling lane). Eleven further defects were
repaired, two broken control arms were re-frozen upward, and a seventh control arm added.

Not licensed: any resonance-specific or CAS-specific claim, anything beyond these synthetic
worlds, or any merge into CMB-R1. Stopped after the report; next step is independent audit.


## 2026-09-01 (CJT-EX1 RAN, AMENDED) - NO_CJT_EXPERT_SPECIALIZATION_SIGNAL: a PROVEN meaningless partition (E4) ties the CAS partition (E2) at +0.0006, so CAS expert MEANINGS are not load-bearing; the designated killer control E1S DEGENERATED via router collapse and that comparison is VOID; $0.2404 of the $1.20 cap; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner amended the protocol after the pre-launch stop and authorized the run: headroom-aware breadth (QB_COMP frozen as saturated; QB_REL + QB_INT eligible), repaired retention (phase 1 QB_INT -> phase 2 QB_COMP with a real-interference gate), E1S anonymous sparse top-1 added as THE killer control, E3 demoted to exploratory, result vocabulary frozen, E4 required to be PROVEN class-independent. 36/36 runs on one self-terminating g4dn.xlarge (i-090962eb9f5dc5129, 27.4 min, instance_runtime_estimate $0.2404 authoritative; harness lower bound $0.2032).
- **ARMS (family C transfer, 597 records, 3 seeds): E0 0.7733 / E1 dense 0.7767 / E1S 0.7655 / E2 CAS 0.7806 / E3 0.7789 / E4 shuffled 0.7800.**
- **THE DECISIVE RESULT - E2 vs E4 = +0.0006 (~0.09 paired se).** E4 was proven class-independent before the run (MI 0.000084 bits over 54,000 train clauses; 0.0030 in-run vs E2's 1.7477) with near-uniform expert load [0.236, 0.250, 0.264, 0.251]. A stable but MEANINGLESS partition of clauses across four experts does exactly as well as the CAS operation partition. Whatever small advantage exists over a learned router comes from having a FIXED assignment, not from the assignment carrying CAS meaning. In the owner's frozen vocabulary this is the substance of CAS_EXPERT_MEANINGS_NOT_LOAD_BEARING; the law did not emit that status only because its test is a strict point-estimate inequality (E4 >= E2) and E4 landed 0.0006 below. Status left exactly as emitted.
- **KILLER CONTROL VOID - E1S ROUTER COLLAPSE.** Measured expert load [0.001, 0.000, 0.999, 0.000]: 99.9% of clauses routed to ONE expert, so E1S was one working expert with three dead ones at a quarter of the active capacity - which is why it scored LOWEST of all six arms. The E2-E1S margin (+0.0151, below the 0.02 threshold anyway) is therefore evidence about four working experts versus one, NOT about CAS routing versus learned routing. Cause: no load-balancing auxiliary loss - the standard MoE failure mode; neither I nor the 56-agent review caught it. E1 dense was also skewed ([0.128, 0.167, 0.122, 0.583]).
- **BREADTH PASSED but is explained away by E4:** both eligible families improved vs E1S with 3/3 seeds - QB_REL paired +0.0204 (52.2% remaining-error reduction, +4.06 answers), QB_INT paired +0.0542 (8.3% error reduction, +10.78 answers). QB_COMP correctly excluded as saturated (E1S 1.0000); E2 actually LOST 0.0303 there.
- **RETENTION: catastrophic forgetting in every condition.** The interference gate PASSED (every arm gained 0.43-0.49 on the new task with 500/500 nonzero-gradient updates and real parameter movement), and retained QB_INT collapsed from ~0.37 to 0.005-0.041 - BELOW that family's 0.0909 chance, i.e. active re-mapping, not mere decay. Forgetting spread across all six arms is 0.343-0.368 against ~0.35 absolute, under 8% of the effect; E0 (single shared expert) and E4 (meaningless routing) tie for the LEAST forgetting. Expert organization gave essentially no memory protection. E3's involution body-sharing did not help (-0.0017): no STRUCTURED_WEIGHT_SHARING_SIGNAL.
- Cumulative spend $2.129 of $30 (7.1%). Protected splits and the sealed C2 half untouched; prohibited terms unused; no claim promoted. Per the standing rule there is no second EX1 repair - whether to re-run E1S with load balancing is an OWNER decision.

## 2026-09-01 (CJT-EX1 BUILT, PRE-LAUNCH REVIEW, NOT LAUNCHED) - 56-agent review found 18 confirmed defects; TWO of the owner's seven success conditions are compromised by DATASET properties, not by the architectures under test; STOPPED BEFORE SPEND pending an owner ruling; $0; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling: standalone table/J lane CLOSED; carry J forward as a computational constraint inside experts; next primary experiment = CJT-EX1 Expert Specialization and Transfer Pilot, on AWS GPU. Owner also CORRECTED my earlier wording (adopted): labels are street names, R is the map of how streets connect — labels alone do NOT literally contain R; labels + enough examples let a learner reconstruct it. J remains a legitimate inductive prior; my theorem wording was broader than the mathematics warranted.
- BUILT: five conditions over the A1 recurrent graph executor with its two clause-local scorers replaced by expert banks — E0 SHARED / E1 ANON_MOE (learned soft router) / E2 CAS_EXPERT (hard-routed by true operation class) / E3 CAS_STRUCT (E2 + the canonical ^2<->^3 involution as a COMPUTATIONAL rule: aversion IS attraction with reversed orientation) / E4 SHUFFLED (frozen per-clause hash). Transfer is built into the data (train families A,B verbs 0-5 forms 0-3; eval family C verbs 6-7 form 4, never seen). Prereg frozen (CJT_EX1_PREREGISTRATION.md), cap set at $1.20, projected $0.62.
- **TWO STRUCTURAL BLOCKERS, verified with exact counts, NEITHER about the architectures:** (1) **condition 3 near-unsatisfiable** — on the exact eval split QB_COMP is saturated at 1.0000 so a +0.02 margin is ARITHMETICALLY IMPOSSIBLE there, and QB_REL at 0.97449 would need 78.4% of ALL remaining errors; only QB_INT (0.3777) has room, so "spans >=2 families" reduces to QB_REL AND QB_INT. (2) **condition 6 decided by the generator** — QB_COMP contains ZERO ^3 clauses in all 3000 records (and no family but QB_REL uses ^3), so under hard class routing E2/E3's ^3 expert gets no gradient in retention phase 2 and CANNOT be overwritten; E2/E3 are structurally protected by the clause template, not by expert organization, while E0/E1 are not. Running as specified would spend on a near-certain negative that says nothing about the hypothesis — the same empty-comparison trap the owner praised avoiding when C2 was retired.
- **FIXED BEFORE ANY SPEND (mechanical, unambiguous):** match_capacity returned the FIRST width inside the 1% band while scanning upward, so every CONTROL landed on the low edge while hypothesis arms hit target exactly (E1 was 0.908% BELOW E2) — a bias toward the hypothesis, the dangerous direction; replaced with exact binary search, spread 0.974% -> 0.206%, E1 now +0.138% above target. E3 did NOT implement its registered mechanism (docstrings claimed a shared body; code allocated four independent bodies and tied only the readout) — E3 now genuinely shares the involution body, verified. False docstring claims that E1/E4 are label-blind corrected (every arm receives the class profile via the attention path — they are expert-organization-blind). The E2-vs-E1 sparsity confound (E1 dense 1,442,816 active params/clause vs E2 sparse 360,704) disclosed in code; it biases toward the null, the safe direction.
- One CRITICAL was REFUTED and the refutation is recorded: the claim that hard routing starves E2 was wrong (E4 is also one-expert-per-clause, and E2's per-class training density is 4.0x E4's). Ten further confirmed defects remain, all fixable at $0, and will be fixed before launch. NOT LAUNCHED; cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (J0 BENCH, $0 CPU) - J0_GENUINE_J_DEPENDENT_CASES_EXIST, BUT the owner's "flat labels do not reveal it" gate FAILS and is unsatisfiable for any R-based task; a J track is constructible only as a PRIOR-VS-LEARNED test, never as an identifiability test; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ordered J0: search the ACTUAL CAS rules for cases where M+C leave the answer ambiguous but M+C+J determines it, with counterfactual twins and four deterministic checks. Executed on local CPU, $0.
- **AUTHENTIC CASE FOUND: the ^8/^9 (Above-Cause / Below-Effect) converse pair.** Grounded in the canonical definitions and the CO-8<->CO-9 involution invariant: the two classes describe the SAME edge read in opposite directions. Twins: "algebra evoked botany for mira. chess was evoked by botany for mira." (answer chess) vs "algebra was evoked by botany for mira. chess evoked botany for mira." (answer algebra) — same entities, same class multiset, same M/C, same candidate set, same template. **All four checks pass**: full M+C+J resolves both; twins differ; J removed → both UNRESOLVED; J corrupted → wrong; unrelated J cell → no effect. M cannot do this job (it licenses BOTH directions); C cannot (identical both ways); only the DUAL relation determines it.
- **PRECISE DIAGNOSIS OF THE OLD TASK:** PATH B used ^2,^3,^6,^8 = ONE complete involution pair (^2<->^3) plus TWO half-pairs (^6 without ^5, ^8 without ^9). A half-pair cannot express a converse relation, so no composition had two admissible directions. **Sharper bonus finding:** under canonical edge semantics the task vocabulary DID contain an M-symmetric chainable pair (^6,^8) — but no question family ever queried it. It was the QUESTION DESIGN, not the algebra, that left J with nothing to do.
- **THE BLOCKING RESULT (measured, not asserted):** the owner's condition "flat operation labels do not reveal it" FAILS on the very case found — the twins have distinct (label-sequence, entity-slot) signatures, so a flat-label→answer function provably exists. And this is structural, not a fixable accident: **R = (M,C,J) is a function of the class labels**, so no part of R can ever be INFORMATIONALLY necessary to a learner that already receives exact labels. Any R-based task fails that condition by construction.
- **CONSEQUENCE:** Outcome B as written is not fully satisfiable (7 of 8 conditions are engineerable; the flat-label one is not). What survives is legitimate and testable but different in kind: whether the correct lookup supplied as a FROZEN PRIOR beats LEARNING it (sample efficiency, OOD transfer) — the R-CAS vs R-LEARNED contrast, with T2 as the diagnostic socket. That is a claim about inductive bias and must never be promoted into one about information or specificity. Also NOT established: >=2 J-dependent families (only one converse pair exists canonically — ^2/^3 is valence, ^5/^6 relates different entity types) and baseline headroom. Nothing further built; owner decides. Cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (J-NECESSITY TEST, $0 CPU) - TIER_C_J_NOT_IDENTIFIABLE_ON_CURRENT_TASK (owner Outcome A): removing the entire J plane changes ZERO answers; an M-first solver is invariant across all six registered J conditions; J is CAPABLE but REDUNDANT because M's asymmetry already decides every case; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruled after C1: run ONE CPU-only $0 J-necessity test before any further spend, six conditions (full M+C+J / J removed / sign flipped / dual swapped / wrong J / unrelated cell), count answer changes. Executed on 9,597 records (9,000 train + the 597 C1 val half; the C2_STRUCTURE_EVAL half NOT read).
- INSTRUMENT: pathb_core.solve() never consults R, so "perturb J and watch the gold" is degenerate (the gold would not move under M or C perturbations either). Built an R-DRIVEN solver that computes answers FROM the table, plus two clause-grammar rules that are observable surface structure and not table content. **Validity gate: reproduces gold 9,597/9,597 (1.0000).** The FIRST attempt scored only 3,196/9,597 and was reported INSTRUMENT_BROKEN rather than used — the defect was diagnostic (result_type IDEA cannot pick between the two idea slots of a ^8 clause). J was given every chance: the solver asks J FIRST, before M.
- **RESULT: J removed → 0 answers changed. M-FIRST control → 0 answers changed in ALL SIX conditions. M intact / J suppressed → 9,597/9,597 correct.** The J-FIRST instrument did change 12,793 answers under sign-flip / dual-swap / wrong-J, but those measure the cost of TRUSTING a wrong J, not the task's need for J — the registered status law decides identifiability from the M-first control and J-removal, explicitly excluding J-first-only changes.
- **CAPABLE BUT REDUNDANT (a distinct finding from useless):** M symmetrized + J available → 9,597/9,597; M symmetrized + J suppressed → 0/9,597. The duality/sign plane is a genuine, *sufficient* alternative route to the execution order; it is simply never the *only* route. ROOT CAUSE: M has 4 derived cells and every queried class pair is asymmetric in M — (^3,^2) licensed but not (^2,^3); (^2,^8) but not (^8,^2); (^2,^6) but not (^6,^2) — so direction is pinned by M alone and J's distinctive content is never consulted.
- CONSEQUENCES per the ruling: C2 must NOT run (its R-CAS vs R-EMPIRICAL contrast differs ONLY on J, which is not identifiable → empty by construction); the present Tier C task closes; the neural network is NOT to blame (T2 demonstrably read the table — authority 3.28x, bridge 0.5717 vs 0.3272, corruption collapse to 0.299 — there was nothing in it the task rewarded); C1 is NOT reinterpreted as a win and remains genuine negative evidence for this table, these transforms, and this task. Recorded (not proposed) for a possible Outcome-B task: J is identifiable only if some family names a class pair SYMMETRIC in M, so order cannot come from M. Retained: LM, recurrent graph executor, operation profiles, clause-entity binder, M/C/J algebra, T0-T4 implementations, control machinery. Cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (TIER C C1 RAN) - NO_TRANSFORM_CONSUMES_STRUCTURE: no transform beat the no-structure baseline (all four slightly NEGATIVE); T2 became heavily dependent on the table and nearly doubled formal-bridge agreement while gaining NOTHING on the task; $0.1808 of the $0.80 cap; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner authorized C1 ($0.80 cap, one instance, C2 NOT auto-authorized, "specific" after C1 = TOO EARLY). Ran 15 runs (T0 + T1-T4 x seeds 11/23/47, 1000 updates) on one self-terminating g4dn.xlarge T4 (i-07dfc2821c7032c44, 20.6 min, instance_runtime_estimate $0.1808 authoritative; harness compute_wall_estimate $0.1429 recorded separately as a lower bound). All P0 gates pass; preflight verified dataset digests, BOTH C1 and C2 pid-set digests, and the R_CAS/R_RANDOM digests fail-closed before any GPU work; cache binding verified 9000 + 597 records.
- **RESULT: T0 0.7800 / T1 0.7744 / T2 0.7783 / T3 0.7772 / T4 0.7521** — margins -0.0056 / -0.0017 / -0.0028 / -0.0279, none reaching +0.02, seeds-positive 0/3, 1/3, 1/3, 0/3 (se~0.024). Because T0 already carries the exact one-hot operation labels, C1 answered: **does a relational TABLE add anything ON TOP of exact operation labels? On this task: no.** The negative is NOT an artifact of the saturation-constrained family clause — every OVERALL margin is negative too.
- **PRINCIPAL MECHANISTIC FINDING (T2): consumption without benefit.** T2's structure channel reached 3.28x the base attention score and nearly DOUBLED formal-bridge agreement (0.5717 vs T0's 0.3272), and the trained model is massively table-dependent — removal 0.778→0.672, permutation →0.424, R-RANDOM →0.299 — yet its task margin is -0.0017. Structure consumption and formal-path agreement both improved while accuracy did not. Second time on this task family that the formal path and the answer came apart (in A1 the winning arm had WORSE bridge agreement; here the best-bridge arm gains nothing).
- **HEADROOM (beyond the registered disclosure):** the prereg flagged QB_COMP at ceiling (1.000); the run shows QB_REL is ALSO effectively saturated for the baseline at 0.9745. Real headroom exists only in QB_INT (0.378) and NO transform improved it (T1 -0.0246, T2 -0.0099, T3 exactly 0.0000, T4 -0.0755). The tournament had one genuinely open family and the table did not help it.
- Per-transform: T1's channel ended up carrying zero decision weight (all three ablation falls exactly 0.0000); T3 tolerates losing the table (removal +0.0022) but not being lied to by it (permutation +0.096, R-RANDOM +0.083); T4 is the only clearly harmful transform, costing QB_INT 15.3 answers per seed.
- **C2 CONSEQUENCE:** C2 was to freeze the C1 winner and swap rulebooks through it — there is no winner, so C2 as specified has no socket. Combined with the standing J-necessity blocker (C0 measured R-CAS and R-EMPIRICAL identical on M and C, differing only on J), C2 is now blocked on a DESIGN question, not merely on sign-off. Owner decision. Per the prereg, no second tournament: the negative is recorded and kept. Cumulative program spend $1.889 of $30 (6.3%). Protected splits and the C2_STRUCTURE_EVAL half untouched; prohibited terms unused.

## 2026-09-01 (TIER C C0 BUILT + GATED) - TIER_C_C0_READY_FOR_FOCUSED_REVIEW: frozen relation algebra R=(M,C,J) derived cell-by-cell from the solver + canonical invariants (Aut trivial), two-part non-equivariance proof on per-example trajectories (Test A exact 0.0 all 24 perms x T1-T4; Test B min divergence 0.114-1.160 vs floor 0.001, 2 data seeds), 3455 matched non-isomorphic controls, genuine trace estimator R-EMPIRICAL (M/C converge 16/16 MEASURED, J differs -> the C2 killer contrast isolates the duality/sign prior), QC_VALID diagnostic + R-only probe within bounds, 14-agent adversarial review (1 CRITICAL refuted, 7 CONFIRMED defects all fixed pre-freeze); CPU only, $0; C1/C2 GPU awaits owner sign-off; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling "TIER C v0.2 — C0 CONSTRUCTION AUTHORIZED" executed with all binding amendments: R-RANDOM reclassified RELATIONAL_MISINFORMATION_CONTROL (wrong structure = misinformation, the A1 lesson as law); killer controls = R-LEARNED + R-EMPIRICAL; QC_VALID diagnostic-only (excluded from win status/headline/family-removal) with the R-only <= chance+0.05 law (measured: REL .1013/COMP .1227/INT .1173, all within bounds); R=(M,C,J) minimal typed algebra, per-cell source rules, typed UNDEFINED/NO_DUAL, no invented strengths; QB-ORD stays dropped (final for this dataset version); C1 cap $0.80 / C2 cap $0.60, no transfer.
- STRUCTURE: M has exactly 4 derived cells — (^3,^2) REL mind-bridge, (^2,^8) COMP mind-bridge, (^2,^6) INT idea-bridge, (^6,^6) INT part-join — each citing its solve() rule; J carries the CO-2<->CO-3 involution, signs, and the missing-dual asymmetry of ^6/^8. Aut(R_CAS) = {identity} over all 24 perms; the M-only-triviality dependence on the join cell is disclosed with a persisted counterfactual (without it: {id, ^6<->^8}; full R stays trivial via the C plane).
- PROOF v2 (per-example criterion after review hardening): consistent renaming conforms EXACTLY (0.0, all 24 perms, all 4 transforms, plus the no-structure recipe-validity baseline mirroring A1's S-PERM); the class-indexed absorption recipe FAILS against frozen R by 0.114-1.160 per-example divergence on both data seeds (old batch-mean criterion gave only 0.0036-0.0093 — the review attack that curve-fit 5 means to 1e-4 was refuted as an absorption, diverging 1.68 per example and "absorbing" R_RANDOM under identity labels, but the per-example upgrade was adopted anyway).
- ADVERSARIAL REVIEW (TIER_C_C0_REVIEW_FINDINGS.json): CONFIRMED+FIXED before freeze — R_EMPIRICAL's C plane was transcribed not estimated (now a genuine slot/pool-typed estimator; the 16/16 M/C convergence is now a measurement); QC surface over-claim (registered char-level adversary persisted: char-ngram 0.4933 = chance, length-order rule 0.8350 — disclosed; readout = contrast between R-variants); QC pid suffix encoded gold (HashPRNG tag scramble + decorrelation gate); cache verifier missed duplicate pids and never checked model/tokenizer/extraction shas (now 11 violation classes fail closed); mutation battery had hardcoded 7-point entries (now per-point MEASURED/BY_CONSTRUCTION basis, M14 judges via the registered predicate); R_CORRUPTED50 confounded wrongness with 3x density and skipped J sign/dual (v2 cell-transplant law, density-preserving in expectation, all planes corrupted, per-plane counts persisted); runner hardening (full vocabulary schema, G-C0-5 split, byte-deterministic receipt, library versions persisted).
- All 10 gates PASS; receipt + all 13 tier_c artifacts byte-identical across three runs. NEXT: owner's focused review of the C0 package; C1 (transform tournament, 27 runs, cap $0.80) and C2 (7 conditions x 3 seeds, cap $0.60) remain NOT authorized until then. No GPU spend; no protected read; prohibited terms unused.

## 2026-09-01 (PATH-B-A1 CLOSURE + INDEPENDENT AUDIT + TIER C DESIGN) - owner closure ruling executed: component findings separated, one independent 3-auditor raw-result audit of 3bbcd2c1 (ZERO numerical discrepancies; flagged survives-clause concern SUBSTANTIATED with exact residuals), Tier C design v0.1 drafted for owner ruling; $0 spend; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling "PATH-B-A1 CLOSURE AND TIER-C TRANSITION": 3bbcd2c1 + NO_PATH_B_OPERATION_SIGNAL PRESERVED; separated findings recorded (cjt_path_b_v2/PATHB_A1_COMPONENT_FINDINGS.json): COMPOSITIONAL_GRAPH_EXECUTOR / EXACT_OPERATION_PROFILE_ADVANTAGE / PROFILE_CONTENT_CAUSAL_DEPENDENCE = SUPPORTED_IN_DEVELOPMENT; MONOTONIC_50_PERCENT_WRONG_LABEL_DOSE = REFUTED; FORMAL_PATH_FAITHFULNESS = UNESTABLISHED. Interpretation corrections adopted: S-ALT50 is a corruption arm; its −0.0033 vs S6 = no useful difference (the anti-informative evidence is the permutation ablation .787→.118); advantage concentrated in QB_REL.
- INDEPENDENT AUDIT (PATHB_A1_INDEPENDENT_AUDIT.json; three parallel auditor agents, raw artifacts only): every mean/std/margin/per-family value/boolean reproduced EXACTLY (population std n=3 confirmed); status-law replay shows NO_PATH_B_OPERATION_SIGNAL was the only reachable status (both failed clauses driven by the single raw fact SALT50 0.742815 < S6 0.746074, gap 0.003259); alt50 corruption rate 0.499736 train / 0.499333 val, balanced, substitutions spread ~1/3; dataset sha256 match manifest exactly; pids all unique/disjoint; ablations eval-only, S6 invariance mathematically forced; governance clean (zero protected-read violations, zero prohibited-term claim-use, cumulative spend independently recomputed $1.708 ≈ stated $1.71, 5.7% of ceiling).
- OWNER'S FLAGGED ITEM SUBSTANTIATED: survives_best_family_removal as coded = strict positivity vs S6 only; removing QB_REL leaves residuals 0.006222 vs S6 (~7 of 1125 answers), 0.001333 vs S0 (~1.5 answers), 0.008000 vs SALT50 — all would fail a 0.02 criterion. Honest as coded, weak as designed. Findings short of discrepancy: P0 gate_s3_profile_grads UNVERIFIABLE (grad log never persisted); cache assertions count-level only + not bound to dataset hash; four PATH B runs lacked standalone receipts → retroactive receipt filed with per-field sources (CLOUD_EXECUTION_RECEIPTS_PATHB_RETROACTIVE.json; A1 instance i-0b479d3ea577e98a7 recovered from the contemporaneous launch record; live sweep 2026-09-01T09:28Z: zero experiment instances, only the owner standby stopped).
- TIER C DESIGN v0.1 drafted (cjt_path_b_v2/TIER_C_DESIGN_v0_1.md), design only, $0: frozen 4×4×F CAS composition structure (solver semantics + involution sign + missing-dual asymmetry), PROOF_OF_NON_EQUIVARIANCE before spend (trivial-automorphism enumeration + pathway pinning + the A1 conformance test required to FAIL + mutants M13/M14), matched generic relational control R_gen (win over BOTH or CAS_SPECIFICITY_NOT_ESTABLISHED), new QC_VALID family, bounded Transform Tournament T0-T4 (27 runs ≈$0.55), attenuation (λ-blend) and misinformation (ρ) as SEPARATE dose axes (21 runs ≈$0.45), formal-path faithfulness as measured outcomes, all four audit corrections as harness laws (persist gate inputs; residual ≥0.01 vs all arms; cache-to-dataset-hash binding; same-commit receipt law). C0 is CPU-$0 and stops at TIER_C_CONSTRUCTION_FAILED; owner-signed approval required before any C1 spend.

## 2026-09-01 (PATH-B-A0 + A1 COMPLETE) - GRAPH_EXECUTOR_EARNED, executor P0 perfect, P1 = NO_PATH_B_OPERATION_SIGNAL on the monotone-dose clause alone; the corrupted-label dose point INVERTED (SALT50 0.7428 < S6 0.7461) — half-wrong labels are anti-informative, not half-informative; branch research/cjt-dev-p1-s7d1-fivearm-v1

- A0 (clean rerun after the pid-collision repair, $0.246): GRAPH_EXECUTOR_EARNED at every layer — bridge recovery 1.000/0.973, second-hop binding 1.000/up to 0.807, full gold-path (no gold bridge) 1.000/up to 0.767 vs uniform 0.104; destructive drops ≥0.30 both controls; earliest passing layer 6 FROZEN (L12's better holdout reported, not selected). Clean PRB-POS max 0.848 < 0.90 → QB-ORD drop confirmed on valid evidence.
- A1 (recurrent clause-entity graph executor, 2 preregistered hops, soft bridge pointer preserved between hops, identical across arms; first launch died on a missing sys.path import, $0.074, preserved as execution fault; relaunch i-0b479d3ea577e98a7, 26.6min, $0.233): **P0 ALL GATES PASS** — memorization 1.000, gold-path 1.000 vs shuffled-path 0.124 (gap 0.876), rewired 0.178 (drop 0.822), bridge top-1 0.922, S3 grads/swap ✓, S6 exactly invariant ✓, params matched ✓. The executor provably executes and depends on the path.
- **P1 (4 arms × 3 seeds × 1000u, L6): S0 0.7553, S3 0.7873, SALT50 0.7428, S6 0.7461** — the compositional task is now largely SOLVED on fully unseen verbs+forms (QB_COMP 1.000, QB_REL 0.86-0.98; QB_INT hard ~0.38). S3 clears S0 by +0.032, S6 by +0.041, SALT50 by +0.044 (all above thresholds and above the 0.019 B-KEY increment); S3's corruption ablation is devastating (true 0.787 → permuted 0.118, uniform 0.394); floor ✓; survives best-family removal ✓. **The single failed clause: monotone dose ordering — SALT50 < S6 overall and in 0/3 families.** Deterministic status NO_PATH_B_OPERATION_SIGNAL per the frozen law, preserved.
- SUBSTANTIVE FINDING (reported, not relitigated): the dose design assumed 50%-corrupted labels are half-informative; measured reality is that half-WRONG labels actively mislead routing (SALT50 ≈ its own uniform ablation 0.739/0.743; S3's permuted 0.118 ≪ uniform 0.394 shows the same asymmetry) — label noise is anti-informative in a routing channel. The exact-profile advantage itself met every margin clause. Mechanism note: S3's formal-bridge top-1 (0.330) is lower than S6's (0.550) despite winning — the profile-equipped executor routes by its own strategy, not the formal trace.
- Per the owner stop law: no second graph-binder repair, no threshold changes, no result-driven family substitution. PATH B closes with the executor earned+working, the task beaten, the exact-label advantage real by margins but the registered dose law honestly failed. Next per the directive: Tier C or the CAS Transform Tournament — owner's move. Cumulative arc GPU ≈ $1.71 of $30. Both protected splits untouched; no claim; prohibited terms unused.

## 2026-08-31 (PATH B P0 RAN) - BINDING_REPAIR_FAILED: the frozen P1.3 clause-local binder is structurally mismatched to the compositional v2 task (gold-routing INVERTED 0.133 vs shuffled 0.258; memorization 0.711); the gates stopped P1 exactly as designed; branch research/cjt-dev-p1-s7d1-fivearm-v1

- PATH B v0.3 CPU stage was fully green (PATHB_GATES_PASS; CHK_M_PASS 11/11; SPERM_EQUIVARIANCE_CONFIRMED 7.15e-07; 12000/1500/1500, 0 exclusions, round-trip 100%; commit 7b5dc11b). P0 then ran on one self-terminating T4 (i-06806594ed90c7648, 28.1min, ~$0.247): L*=12 (layer profile changed vs v1's 18/24 — task-dependent), all four dose arms trained (S0 .2693, S3 .2620, SALT50 .2267, S6 .2460 @100 updates), S6 exactly invariant (Δlogit 0.0000), S3 swap-sensitive (0.128), profile grads real, λ≈0.98-1.0.
- FAILED GATES (the owner return contract's first branch): gate1 memorization 128 = 0.711 < 0.95; gate2 gold-routed 0.133 < shuffled 0.258 — INVERTED: one-hot routing onto the answer-bearing clause DESTROYS the selector context the mixture needs, the cleanest possible mechanistic proof that the clause-local expert binder's core assumption (answer determined within one routable clause) is exactly what PATH B was built to break (v0.2 risk finding #18 realized); prb_pos 0.888 < 0.90 → QB_ORD auto-drop rule fires (owner D3) — though QB_ORD is ironically the ONLY family the head learns well (S0 0.784 vs uniform 0.143), a frozen-rule tension recorded for the owner; transfer floor: only QB_ORD above uniform+0.05 at 100 updates.
- NO P1 ran (correctly gated). NO redesign attempted (owner: "do not construct a third binder"; "endless static redesign PROHIBITED"). The v1-arc result stands untouched; the v2 finding is itself valuable: the architecture that WON the v1 task cannot express the v2 task's compositional binding — the task upgrade did its job. Whether to authorize a PATH-B-specific architecture round, resize the P0 gates (e.g. memorization updates), or bank here is an OWNER decision. Cumulative arc GPU ≈ $1.26 of the $30 ceiling. Protected splits (v1 AND PATH B) untouched; no claim; prohibited terms unused.

## 2026-08-31 (PATH B task design v0.1→v0.2) - operation-graph spec drafted, adversarially reviewed (19/19 findings CONFIRMED incl. the S-PERM equivariance THEOREM), rewritten as v0.2 for owner review; no build, no GPU, $0

- Owner ruled: move to PATH B (no third binder; new protected derivation; 7 bijection-breaking requirements). Drafted PATH_B_TASK_SPEC_v0_1.md (operation graphs, 5 question families, executable CHK gates) then ran a 22-agent adversarial design review: 19 non-MINOR findings, ALL confirmed, 0 refuted (SPEC_V0_1_REVIEW_FINDINGS.json).
- Deepest finding (#7, CRITICAL): with profiles entering only via learned linear W_r, (W_r g)·(P p)=(Pᵀ W_r g)·p — any bijective relabel control (S-PERM) has S3's loss landscape under reparameterization; the planned "identity vs distinguishability" tie is a THEOREM, not an experiment. Flat-label "CAS-specific" is untestable in this architecture; specificity relocates to Tier C (structural geometry, frozen read-in). Also CRITICAL: the answer-key gate was dishonest both directions (real leak = profiles+membership+positions+anchors composite; naive ceiling beatable by type priors) → rebuilt as a TRAINED adversary gated on the per-family PROFILE INCREMENT with a B-MEMBER symbolic reference; MAX_IDEAS=6 vs K≤9 crash; S-ALT bijection certificate contradiction.
- v0.2 folds in all 19: K≤6, 100% non-bijective passages w/ anchor exclusion, per-family gating + per-family uniform references, candidate-order shuffle law, QB-INT anti-counting law + registered surface shortcut, QB-ORD before/after balance + counterfactual CHK-8 + PRB-POS position-probe drop-rule, QB-XOP demoted to dataset property, per-family uniqueness constraints, v1 verbs retired from ALL surfaces, S-PERM demoted to two-sided sanity control, S-ALT as honest Δ.2 dose point, TOTAL interpretation law (incl. SHORTCUT_BOUNDED_SIGNAL and READOUT_UNDERPOWERED_V2 branches), transfer floor-guard, assemble_v2 plumbing, 40 new verbs / 6 forms with stated allocation.
- Owner decision points D1-D5 (Q-B2 reframe, K vs MAX_IDEAS amendment, QB-ORD keep/drop, sizes, protected derivation choice). v1 protected split untouched; nothing builds or runs until v0.2→v0.3 approval.

## 2026-08-31 (cjt-dev-p1.3 FINAL binding-conversion round) - PROMISING_DEV_SIGNAL: clause-local expert binder converts the CAS routing advantage into the arc's first task-level win (S3 0.7340 beats every control by 0.034-0.080; both S3+S0 exceed B0 0.668); all 9 smoke gates passed; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling executed verbatim: router/L18/profiles/λ/data/seeds/optimizer frozen; ONLY the binder replaced (pooled passage vector → clause-local answer experts P(c|x)=Σᵢ αᵢ·softmax_c(ℓᵢ,c), per-clause candidate occurrence vectors, absent candidates masked, no gold clause in train/eval). Pre-launch adversarial review caught a gate-validity defect (binding shuffle permuted padded rows = evidence deletion on 74.6% of records) — fixed to per-example live-prefix permutation BEFORE spend (15b79aea).
- P0 smoke: ALL 9 gates passed — memorization 1.000; gold-routed 0.984 vs shuffled 0.266 (+71.9pp; old binder's oracle gain was +3.6pp); binding-shuffle drop 0.781; S3 swap-sensitive; S6 exactly invariant; 0 answers lacking a clause occurrence; params matched (S0 803,712 vs 807,301 = 0.44%).
- P1 (5×3×1000, T4 21.3min $0.187, i-03930a7a062250516): S0 0.6997, S3 0.7340, S6 0.6843, S7H 0.6830, S7D 0.6537. S3−S0 +0.034 (2/3 seeds ≥0.02), S3−S6 +0.050 (2/3), S3−S7H +0.051 (3/3), S3−S7D +0.080 (3/3); no per-type collapse; S3 corruption: permuted 0.414 (wrong labels actively mislead), uniform/zeroed 0.642; S6 exactly invariant; S7-Δ's soft profiles HURT vs uniform (0.654 vs 0.681). Gold-clause hit S3 0.869. λ grew to ~1.13-1.15 on content-bearing arms. → deterministic status PROMISING_DEV_SIGNAL (all 6 owner win conditions).
- FIRST time any arm beats the B0 surface heuristic (S3 0.734, S0 0.700 > 0.668). Calibration caveat: S3 NLL 2.79 > S0 1.88 despite higher accuracy (over-confident when wrong) — reported, not gated. Bounded reading per ruling: task-aligned label advantage on a controlled surface-solvable dev task; "CAS-specific" PROHIBITED; development triage label only. Protected split untouched; no claim promoted; per the ruling this was the FINAL static binder test — no further static redesign. Cumulative arc GPU ≈ $0.83 of the $30 ceiling.

## 2026-08-31 (cjt-dev-p1.2b λ-fix rerun) - routing branch finally TRAINED; S3 routes gold clauses best (47.2%) and is the ONLY content-sensitive arm; final accuracy still NO_DEV_SIGNAL (binding ceiling); frozen-mode P0 honestly FAILED its gradient gate

- Single repair per the owner closure directive (λ init 1.0) + executable P0 gates + adversarial pre-launch review (6 agents; proved S6's routing gradient is mathematically zero by design — uniform profiles are a softmax-invariant shift — S6 exempted from the w_r gate; stale "λ learned from 0" provenance fixed pre-launch). One T4, 20.5min, ~$0.18 (i-0e3bfa3a929f5d6cd); cumulative project GPU ≈ $0.64.
- PRIMARY frozen-candidates config: PILOT_PIPELINE_FAILURE at P0 — S3 w_r grad 1.3e-14 at step 50 (early softmax saturation at L*=24 still starves routing); P1-frozen SKIPPED by the boot script per protocol. A real gate catch, preserved.
- SECONDARY contextual config: P0_SMOKE_OK (all gates; S3 routing grads real 7.9→2.2→0.08; swap Δlogit 0.52). P1 (5×3×1000, L*=18): S0 0.3737, S3 0.3780, S6 0.3630, S7H 0.3590, S7D 0.3617; S3−S0 +0.004, S3−S6 +0.015, S3−S7H +0.019, S3−S7D +0.016 → NO_DEV_SIGNAL (nothing ≥0.02; seed ranges overlap).
- FIRST MECHANISTIC SEPARATION: gold-clause attention hit rate S3 0.472 > S6 0.423 > S0 0.365 > S7H 0.346 > S7D 0.248 — the exact CAS operation profile routes best; and S3 is the ONLY arm whose accuracy declines under profile shuffle/replacement (.378→.365/.355/.356; S6 exactly invariant, verifying the shift-invariance math in vivo; S7H/S7D gain nothing from their true profiles). λ stayed ~0.9-1.0 everywhere.
- BINDING CEILING CONFIRMED: +11pp routing advantage converts to +0.4pp accuracy (matches Diagnostic D's oracle result). Emitted status NO_DEV_SIGNAL; the pattern matches the owner's READOUT_STILL_UNDERPOWERED description (observation, not the emitted status). Train-subset ~0.78 vs val ~0.37 = cross-family generalization gap on top. No protected split, no claim, prohibited terms unused.

## 2026-08-31 (cjt-dev-p1.1 + p1.2: diagnostics + five-arm relaunch RAN) - readout repairs lifted every arm ~0.21→0.37-0.40 on real GPU; five arms statistically indistinguishable → NO_DEV_SIGNAL; λ-init flaw locked routing (documented, not relaunched); branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner rulings S7Δ.2 ("association is not copying") + P1.2 ("correct the power analysis, diagnose the readout, then run five arms") executed end-to-end. S7-Δ-WN1-V3 ADMITTED under magnitude gates (A_soft*=0.523915<0.75, A_hard*=11/16<14; CAS-free builder, WordNet pin fail-closed, byte-frozen v2 profile reuse, 16-sense audit AUDIT_PASS_NO_SENSE_CORRECTIONS; MC nulls descriptive only). Corrected baselines frozen: chance = candidate-uniform (val 0.12284/2.15307), regime = ABOVE_UNIFORM_LOW_COMPETENCE_READOUT; train/val share ZERO clause verbs.
- CJT-DEV-P1.1 diagnostics (T4, 562.8s, ~$0.154, i-0a7840fe7f1e41f59): machinery healthy (128-ex memorization 1.000); v1 attention COLLAPSED+DEAD (entropy 0.0, gold top-1 23.7%, w_q grad ~1e-17); profile channel INERT (true=uniform=permuted=zeroed) — mechanically explains all v1 ties; gold-clause oracle +0.036; contextual candidates +0.031; in-distribution 0.278 vs cross-family 0.210 (binding-readout generalization is the primary bottleneck; CAS profile helped in-distribution +0.042, ~2.3 SE, evaporates cross-family).
- CJT-DEV-P1.2 five-arm relaunch (T4, 19.8min, ~$0.173, i-07a77393bfa2c7a27): RoutedHead + contextual candidates, L*=18, P0_SMOKE_OK, P1 = 5 arms × 3 seeds × 1000 updates. Mean val acc S0 0.3737, S3 0.3943, S6 0.3990, S7H 0.3810, S7D 0.3753 (all ~3× candidate-uniform; far below B0 0.668). S3−S0 +0.0207, S3−S6 −0.0047, S3−S7H +0.0133, S3−S7D +0.0190 → NO_DEV_SIGNAL; all seed ranges overlap; S6 (uniform) nominally highest.
- λ-INITIALIZATION FINDING (recorded, not relaunched — stop law): λ init 0 makes the routing-query gradient ∝λ=0, a chicken-and-egg lock; routing never engaged; the accuracy doubling came from the profile-independent candidate-grounding repair. S3 uniquely escaped λ=0 in 2/3 seeds (0.055/0.051) — directionally interesting, inside noise, licenses nothing. Fix (λ>0 init or no gate) documented for a future owner-authorized iteration.
- Cumulative GPU spend all three cloud runs: ~$0.46 of the $30 ceiling. No protected split, no claim, prohibited terms unused. Commits 3fb7802b (V3+audit), 91609d94 (diagnostics), this one (five-arm results).

## 2026-08-31 (cjt-dev-p1-s7d1 statistical correction + five-arm rebuild) - S7-H REGISTERED, S7-Δ v2 FAILED its frozen permutation-invariant anti-copy gates; five-arm pilot NOT launched ($0); branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling CJT-DEV-P1-S7Δ.1 (adopt-with-modifications) executed. Exact-null calibration INDEPENDENTLY RE-VERIFIED by full enumeration of all 63,063,000 balanced partitions before freezing anything: P(V≥0.353553)=0.9000405, P(V≤0.35)=0.0999595, P(A*≤8/16)=0.81205, P(A*≤9/16)=0.94555, attainable-V lattice 0.288675→0.353553→0.408248 — all five matched the ruling exactly. "Missed by 0.0036" language RETIRED (STATISTICAL_CORRECTION_S7.json); 19d9e843 preserved with narrowed interpretation (the protocol failed its gate; nonexistence of an honest semantic control NOT established).
- S7-H REGISTERED (build_s7_h.py → S7_H_WN1.json, sha a93a516c…): the honest primary-lexname partition (V=0.353553, exact-null p=0.90) rehabilitated as the hard control, re-verified from the frozen assignment (balanced 4/4/4/4, χ²=6.0, ≠S3, not a permutation, own A*=7/16 ≤ 9/16). Split type tags adopted: profile_semantics + authority fields.
- S7-Δ v2 rebuilt under ALL Δ.1 laws (build_s7_delta_v2.py): background NMF fit EXCLUDING the 16 target senses (TF-IDF, balancing, and factors all background-only, targets projected after); factor-stability gate PASSES perfectly (median mean-row JS 0.0000 across 5 predetermined random-init fits, Hungarian-aligned); all 4 background-frozen anti-uniform gates PASS; raw+balanced profiles preserved (mean balancing row-L1 0.0369). VERDICT: S7_DELTA_V2_CONSTRUCTION_FAILED — the permutation-invariant anti-copy gates fail: A_hard*=11/16 (>9/16 structural; shuffle-null p95=10, p=0.0109) and A_soft*=0.5239 (>p95=0.4532, p=0.0016); robust to the owner-literal entropy-matched null (diag_s7_delta_v2_nulls.py: p=0.00688/0.00121). Correction 1 caught exactly its target loophole — v1's naive argmax check missed the same 0.52 soft alignment (v1 would fail these gates too).
- Substantive reading (not a claim): the 16 verbs were CHOSEN to instantiate the 4 CAS operations, so any faithful soft semantic representation echoes that grouping; the hard partition survives the same standard only because hard categorization discards most of the alignment information. Semantic-coherence evidence about the VOCABULARY; NOT CAS specificity.
- STOPPED at the failed gate per "PROCEED AFTER THESE BOUNDED CONTROL-INTEGRITY CHECKS" + the research-governance law. No GPU, no AWS call, $0 this round. Owner decision: (a) four arms S0/S3/S6/S7-H without S7-Δ; (b) recalibrate the near-copy gate to copy MAGNITUDE rather than alignment SIGNIFICANCE (the current gate rejects any detectable alignment, in tension with the ruling's own "correlation reported, not contamination"); or (c) close the S7-Δ line.

## 2026-08-31 (cjt-dev-p1 CLOUD GPU pilot COMPLETE) - NO_DEV_SIGNAL: on real Qwen2.5-0.5B (AWS Tesla T4, $0.133) the CAS-coupled head ties the plain, uniform, and WordNet-soft controls at ~0.21 val accuracy; branch research/cjt-dev-gpu-pilot-v1

- Owner amendment CJT-DEV-P1-S7Δ (preserved at commit 354f315c): the hard S7-P partition (FAILED, below) is replaced by a SOFT WordNet semantic simplex control S7_DELTA_WN1. `build_s7_delta.py` gives each of the 16 verb senses a 4-component Δ³ profile (`SEMANTIC_COMPOSITION`) via a frozen 4-factor NMF (nndsvda, random_state 0) over the FULL ~13.7k-verb WordNet 3.0 sense inventory (TF-IDF over lexname/gloss/hypernym/frame features), sense-in-context per verb (CAS never consulted), then gentle global factor-scale equalization. Construction-integrity gates all pass (finite/nonneg/rows sum 1; rank 4; ≠S3; no permutation=S3; hardened-argmax ≠ CAS permutation; no CAS/Qwen input; 4-dim interface). Cramér's-V ≤0.35 is dropped for the soft control; soft CAS-alignment (soft MI 0.244 nats, mean entropy 0.604) is REPORTED after freezing, not optimized. The S7-P FAILED verdict is NOT rewritten.
- Owner directive "no local use cloud aws or runpod": ran the pilot on ONE self-terminating AWS g4dn.xlarge (Tesla T4 16GB, us-west-2a, torch 2.5.1+cu121, AMI ami-0c779ec711a581954). Boot → install → download Qwen → P0 smoke → P1 → upload results → self-terminate in 15.1 min for ~$0.133 (triple-guarded termination: terminate-on-shutdown + 90-min in-instance timer + 55-min client watchdog; far under the $30/2h owner ceiling). is_real_model true; no protected split touched; no claim promoted. The known EC2-GPU-quota 0.0 blocker is us-east-1 ONLY — us-west-2 has 8 vCPUs G/VT quota. AWS account 807562639912, IAM user cas-g5-operator, bucket cas-harness-runpod-92754088.
- P0 smoke: P0_SMOKE_OK (all 4 arms trained, candidate tensors present, losses finite, no CPU fallback, params matched). P1 (S0/S3/S6/S7-Δ × seeds 11/23/47 × 1000 updates, L*=24): mean val acc S0 0.2117, S3 0.2123, S6 0.2140, S7-Δ 0.2113. S3−S0 +0.0007, S3−S6 −0.0017, S3−S7-Δ +0.0010 — none clears +0.02. Verdict NO_DEV_SIGNAL. S3 ties S6 → the profile CONTENT is not load-bearing here.
- HONEST CAVEAT: all four neural arms (~0.21) fall far below the surface baselines (B0 class-blind floor 0.668; B1 surface ceiling 1.000). The comparison is FAIR (every arm shares the readout handicap) but the low absolute ceiling makes this a WEAK/underpowered test — a small profile benefit could be masked near the floor. A stronger-readout follow-up is an OWNER research-design decision, not taken here (stop law honored: committed raw results + CLOUD_EXECUTION_RECEIPT, pushed, stopped; no protected read, no claim, no auto-continue to Gate 1B, no redesign). Prohibited terms (CAS-specific / EMPIRICALLY_SUPPORTED / GATE1B_PASS / CJT_TRANSFORMER_VALIDATED) not used. One EOL note: Windows autocrlf made the S3-bundled S7_DELTA_WN1.json hash c216da05 vs the LF-canonical committed efe61cc1 — byte-identical modulo line endings, science unaffected; a .gitattributes now pins the pilot dir to eol=lf.

## 2026-08-31 (cjt-dev-p1 gpu pilot — S7-P gate) - S7_PILOT_CONSTRUCTION_FAILED: no principled semantic WordNet control of the 16 registered verbs is orthogonal to CAS; pilot stopped BEFORE any GPU use, on branch research/cjt-dev-gpu-pilot-v1

- The owner authorized CJT-DEV-P1, a development-only (non-claim-bearing) static neural GPU pilot: 4 arms (S0 plain / S3 CAS-coupled / S6 uniform-capacity / S7-P independent WordNet control) × 3 seeds × 1000 updates over frozen Qwen2.5-0.5B activations, $30/2h ceiling. The first hard gate — build S7-P — must pass BEFORE any GPU launch, else emit S7_PILOT_CONSTRUCTION_FAILED and stop.
- New separate directory `cas_only_reasoner/cjt_dev_gpu_pilot_v1/` (the frozen Gate 1B package is untouched). `build_s7_pilot.py` constructs S7-P from a pinned WordNet 3.0 snapshot (wordnet.zip SHA-256 `cbda5ea6…`, 10,775,600 bytes, Princeton WordNet 3.0 License) and computes every gate. Verdict recorded in `S7_PILOT_BUILD_RECEIPT.json`.
- RESULT: the gate FAILS. The 16 verbs' CAS classes are semantic operation-types (attract/avert/decompose/trigger) and WordNet organizes verbs semantically, so every CAS-blind semantic WordNet partition correlates with CAS above the ≤0.35 threshold: the repo's own frozen construction_law (verb primary-sense lexname) gives Cramér's V=0.3536 (fails by 0.0036); the hypernym-lexname fallback 0.6124; all no-judgment semantic features ≥0.354. The ONLY passing construction (synset-offset shuffle, V=0.289) is non-semantic and would only be selected because it passes — i.e. manufacturing, which the directive forbids. This confirms the taxonomy manifest's own circularity_disclosure.
- Per the directive + the owner's law ("a hard gate that fails is a FAILURE"; "Claude is NOT the research governor"), the pilot STOPPED before any GPU use. No model loaded, no AWS call, no spend, protected split never touched. The negative result is committed as a load-bearing artifact. Resolving S7-P (structured-random control, threshold change, vocabulary/resource change, or dropping the S3-vs-S7 comparison) is an OWNER governance decision.

## 2026-08-31 (gate 1a.2r.2b watchdog config authority) - config read moved inside the fail-closed boundary + no unsigned REAL default per the third-party recheck of 3ce84531 (R.2A VERIFIED_PASS; surviving MAJOR: malformable config envelope + unsigned-default fallback), on branch research/cjt-gate1a2r2b-config-authority-v1

- Two defects the recheck isolated: (a) `_read_signed_cap` ran OUTSIDE the try/except, so a top-level `[]`/`null`/scalar config raised before the boundary and the watchdog vanished with no marker/burn/termination; (b) a missing/malformed config fell back to an unsigned 2.5h default, loosening the owner-signed 2h cap. Fixed (amendment A17):
  - New exec/watchdog_config.py: dictionary-ONLY exact schema bound to campaign id / package commit / approval digest / owner key id / signed cap; the stale limit MUST equal signed_cap*3600*1.1; arrays/null/scalars/wrong-keys/list-valued-limits/bool/zero/negative/NaN/infinity all refused.
  - REAL mode has NO unsigned default: a missing/malformed config fails closed; only non-claim-bearing conformance modes may use a documented default when the file is absent.
  - watchdog_main reads+validates the config INSIDE the boundary → any failure yields WATCHDOG_INTERNAL_ERROR marker + protected-lock burn + termination request + exit 2.
  - Heartbeat writes are atomic (temp + os.replace); a top-level non-dict heartbeat envelope is WATCHDOG_INVALID_HEARTBEAT (no escaping TypeError).
  - The driver writes the bound config; 9 config-authority + 12 heartbeat + 9 clock tests pass; all suites + synthetic campaign + byte-domain green.
- SCOPE per the owner's directive: config authority ONLY. S7 and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.2a heartbeat fail-closed) - make the REAL heartbeat clock immutable and malformed timestamps fail closed per the third-party recheck of 7e69f8a2 (numeric-future attack CLOSED; surviving MAJOR: mutable _clock + a non-numeric heartbeat crashes the watchdog), on branch research/cjt-gate1a2r2a-heartbeat-failclosed-v1

- The watchdog assumed anything JSON-decodable is a number: `driver._clock = lambda: "not-a-number"` wrote a valid-JSON string heartbeat that the watchdog parsed then compared numerically -> raw TypeError escaped, and watchdog_main didn't catch it, so the timeout process could vanish. Fixed (amendment A16):
  - CLOCK IMMUTABILITY: CampaignDriver._beat() reads time.time() directly in REAL, so post-construction _clock mutation is inert (mirrors _hook()).
  - FAIL-CLOSED VALIDATION: is_valid_timestamp requires a finite, non-bool, non-negative number; beat() refuses invalid values; poll_once validates observed-now + the parsed heartbeat; json.loads rejects NaN/Infinity; a malformed heartbeat (string/list/dict/bool/NaN/inf/negative, or an unparseable non-empty file) emits WATCHDOG_INVALID_HEARTBEAT + terminates + returns False -- no raw TypeError, never fresh.
  - watchdog_main wraps poll in try/except -> WATCHDOG_INTERNAL_ERROR marker + termination request + exit 2 on any error.
  - 12 named heartbeat fail-closed tests pass; all suites + synthetic campaign + byte-domain green.
- SCOPE per the owner's directive: heartbeat fail-closed ONLY. S7 and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.2 production clock isolation) - remove production clock injection and reject future heartbeats per the third-party recheck of e3fcfda0 (hook isolation VERIFIED_CLOSED; surviving MAJOR: injectable production clock), on branch research/cjt-gate1a2r2-clock-isolation-v1

- The clock was the last injectable production adapter: a caller could pass clock=lambda: time.time()+1e9 to REAL, and the separate watchdog read the negative heartbeat age as fresh, suppressing the signed timeout. Fixed (amendment A15):
  - The production CampaignDriver has NO clock parameter. REAL ALWAYS uses time.time; SYNTHETIC_CONFORMANCE uses a fixed replay clock; a fake clock is permitted ONLY in REAL_BRANCH_CONFORMANCE via the subclass. A clock in REAL/SYNTHETIC is a hard CLOCK_ISOLATION_VIOLATION.
  - Watchdog.poll_once distinguishes no-heartbeat / fresh / stale / IMPOSSIBLE-FUTURE: a heartbeat beyond now+5s emits WATCHDOG_FUTURE_HEARTBEAT and terminates, so a future clock can never extend the ceiling.
  - The conformance status proof now EXECUTES the real emit_gate1_status program: REAL_BRANCH_CONFORMANCE → SOFTWARE_CONFORMANCE_ONLY / non_claim_bearing=true; a production-looking owner key under --conformance is refused.
  - 9 named clock-isolation tests pass; hook-isolation, REAL-branch, synthetic-campaign, byte-domain all green.
- SCOPE per the owner's directive: clock isolation ONLY. S7 (i//4 ≡ CAS class order) and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.1 production hook isolation) - structural isolation of production from conformance hooks per the third-party audit of a6d17c63 (F-G1A2R-1: REAL mode accepted fake AWS/GPU/model/lock adapters), on branch research/cjt-gate1a2r1-hook-isolation-v1

- The audit was right that a one-line constructor guard is insufficient: the driver also exposed set_real_feature_backend and a mutable _real_hooks dict. Fixed structurally (amendment A14):
  - The production CampaignDriver admits ONLY REAL + SYNTHETIC_CONFORMANCE, has NO public real_hooks parameter, NO set_real_feature_backend, and its _hook() helper reads the registry ONLY in REAL_BRANCH_CONFORMANCE — so mutating _real_hooks in REAL is inert.
  - A non-empty hook map in REAL or SYNTHETIC_CONFORMANCE is a hard HOOK_ISOLATION_VIOLATION.
  - New third posture REAL_BRANCH_CONFORMANCE, owned by a separate RealBranchConformanceDriver subclass (the only class that admits hooks): runs the REAL code paths with fakes but is PERMANENTLY non-claim-bearing — TEST trust root, SYNTHETIC clock, status --conformance (SOFTWARE_CONFORMANCE_ONLY; production owner keys refused).
  - Mode posture expressed by _is_claim_bearing()/_uses_real_branches()/_trust_mode().
  - 11 named hook-isolation attacks pass; the REAL-branch adapter suite still executes under the new posture.
- SCOPE per the owner's directive: hook isolation ONLY. The S7 independent-taxonomy control defect (the i//4 builder reproduces the CAS class order) and the other GATE 1A.2S findings (complete receipts, final-status finalization, in-status signature verification, burn-receipt binding, provenance replay, salted-manifest typing, complete container prep, verify-before-stage, failed-job cost) remain OPEN. The package is NOT owner-signable. Owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r real-path executability) - the REAL Gate-1B branch made executable per the owner's independent source audit of fc7ceb48 (verdict: REAL_GATE1B_EXECUTION_PATH_REFUTED — synthetic fixtures hid 14 branch defects), on branch research/cjt-gate1a2r-real-path-v1

- The audit's diagnosis was exact: synthetic conformance substituted working fakes precisely where the REAL branches were broken stubs. ALL 14 findings closed (amendment A13):
  - REAL candidate encoding WIRED (was `cand=None` → `.shape` crash): `extract_split` now returns h/g/cand (context-free frozen input embeddings) in ONE forward pass for all 4 layers; no passage reaches training/scoring with cand=None.
  - Container bootable: `aws` CLI calls (image never installed it) replaced by committed boto3 `exec/stage_main.py`; watchdog no longer terminates before the first heartbeat (startup grace), shares the REAL epoch clock, reads the SIGNED per-job cap from `watchdog_config.json`.
  - AWS protected-lock unified with local (both return `lock_receipt_sha256`, same schema; the REAL success path no longer KeyErrors after burn); ONE outer burn boundary wraps every post-claim step; the watchdog burns an abandoned AWS lock.
  - REAL training implements the frozen schedule: `exec/batching.build_batches` (batch-32, seeded full-corpus, 3000 updates, seed governs data order); the duplicate run is ACTUALLY compared and REFUTES on mismatch; all 29 runs emit complete receipts.
  - Container-prep driver (`exec/container_prep.py`); S7 staged + built; REAL monotonic cost (no invented 0.01h) + whole-remaining-schedule gate; live model allow-list + live PIP_FREEZE hash; salted-manifest digest enforced; status supports 3 OR 5 seeds (read from evidence); evidence chain validated SEMANTICALLY (checkpoint/cache bytes recomputed, receipts parsed, protected-eval receipt written AFTER evaluation); complete failure-evidence upload + S3 path join; CAS mapping-rules + PATH-A binding in the execution approval.
  - NEW `tools/test_real_branch_conformance.py` exercises EVERY REAL adapter with fakes (fake tokenizer/model/embeddings, fake DynamoDB, fake S3, fake clock) — no model, GPU, or AWS; the branches synthetic mode bypassed are now tested directly.
- Full battery green: 12 unit/attack suites + the end-to-end synthetic campaign (13 sabotages, replay-identical, SOFTWARE_CONFORMANCE_ONLY) + byte-domain. Scope held: NO model, NO GPU, NO AWS, NO protected read, NO key, NO signature. Neural evidence: 0.

## 2026-08-31 (gate 1a.2 campaign-authority freeze) - END-TO-END CAMPAIGN AUTHORITY, PROTECTED EVIDENCE, AND SYNTHETIC CONFORMANCE frozen per the owner's Gate 1A.2 directive, on branch research/cjt-gate1a2-execution-authority-v1 from the verified byte-freeze anchor a6140e0c

- CAMPAIGN LIFECYCLE (§1): one typed 18-state machine (`exec/campaign_state.py` + 3 schemas) — every transition binds campaign id, package commit, authorizing approval/receipt digest, and input/output digests in an append-only sha256-chained log; skips/repeats/wrong-campaign refused; failure inside the protected phase must burn before shutdown; synthetic replay is chain-digest-identical.
- TWO-SIGNATURE DETACHED APPROVALS (§2): prep-specific binding law repairs the v2 incoherence (prep never carries artifact_digests and can never authorize training); execution approval v3 binds EVERY resolved identity (model revision + weight/tokenizer file maps, container + dependency-lock digests, taxonomy table, run schedule, prep receipt, seeds, AWS account/instance/GPU, max hourly rate, ceilings) — nothing deferred past the signature; signed approvals are DETACHED files, refused if found inside the tree.
- OWNER TRUST ROOT (§3): production key ONLY from `trust/OWNER_PUBLIC_KEY_PIN.json` (template deliberately invalid: OWNER_KEY_NOT_YET_PINNED); no CLI/env/caller key substitution anywhere; TEST- keys refused in production and permanently non-claim-bearing; owner key NOT generated.
- REAL DRIVER (§4): LAUNCHER_STUB_GUARD REMOVED — `exec/campaign_driver.py` executes the 30-step ordered path; infra recipes frozen (Dockerfile, requirements.lock, bootstrap.sh, terminate-on-shutdown + IMDSv2-required launch template, separate watchdog process).
- FROZEN RUN SCHEDULE (§5): receipt set DERIVED from the signed RUN_SCHEDULE manifest (29 runs: 4 layer-selection + 24 claim-bearing + 1 duplicate), never `len==25`; 12 named refusals proven.
- CALLBACK-FREE PROTECTED EVALUATION (§6): committed prediction path that cannot read answer/seed_trace/raw labels; separate GoldScorer with per-prediction checkpoint provenance; digest-verified checkpoint loading; 7 attacks proven.
- ONE-USE PROTECTED LOCK (§7): atomic O_EXCL local backend + DynamoDB conditional-write AWS backend; burns on success/failure/interruption; 8 concurrent claimants → exactly 1 wins; burned tokens unreusable.
- IDENTITY + AWS CHECKS (§8): IMDSv2+STS real identity; local CUDA never satisfies the gate; model/tokenizer/container/dependency/taxonomy digest verification; 10+ named refusals proven live.
- COST + TERMINATION AUTHORITY (§9): no --hourly-rate anywhere; signed worst-case pre-job gate; overrun ⇒ campaign FAILED; every path (success/failure/timeout) writes receipt + requests termination; watchdog terminates abandoned campaigns.
- EVIDENCE-CHAIN-BOUND RESULTS (§10): RAW_GATE1_RESULTS v2 carries 21 provenance fields; status program v4 validates the chain (receipt-file digests, arm×seed key grids, baseline arithmetic) BEFORE reading any metric; unbound results → EVIDENCE_UNBOUND; conformance/TEST-key mode law makes synthetic status permanently SOFTWARE_CONFORMANCE_ONLY.
- BOTH protected derivations implemented, NEITHER chosen (§11); owner decisions represented as typed unresolved fields that fail the schema (§13).
- SYNTHETIC_CONFORMANCE (§12): the SAME driver runs end-to-end on CPU against a hermetic package copy (clean-tree law honored) — full lifecycle to TERMINATED, replay-identical chain, plus 13 sabotage detections (rogue key, widened prep, tampered approval, schedule binding, missing taxonomy, tampered weights, REAL-on-local refusal, second protected read, unbound results, cost manipulation, callback absence, stub absence, universal termination).
- Compute boundary held: NO model, NO GPU, NO AWS, NO container build, NO protected-set generation beyond the frozen in-memory law, NO key, NO signature, NO claim. Neural evidence: 0.

## 2026-08-31 (gate 1a.1r byte-domain repair) - FROZEN-BYTE REGENERATION AND FRESH-CLONE SELF-BINDING repaired per the owner's ruling on the third-party audit of ff6f40f9 (F-G1A1-1 CONFIRMED: the freeze was REFUTED — the manifest bound bytes that were not the bytes in the commit)

- ROOT CAUSE (owner-confirmed): `tools/generate_construction_gold.py` pinned LF for train/val but wrote `DATASET_MANIFEST_CANDIDATE.json` with the platform default → CRLF working tree (`dff10734…`, the hash PACKAGE_MANIFEST bound) while the committed blob was LF (`c05bf809…`, normalized by autocrlf at the pre-.gitattributes staging). A fresh clone therefore failed verification — the instrument correctly refused the mismatched specimen. SECOND coordinated defect: the frozen manifest embedded `"generation_interpreter": "3.14.0"` while claiming interpreter independence (the 3.11 container would rewrite it). ff6f40f9 preserved in history as the failed-freeze negative fixture.
- REPAIR (amendment A10, one commit): (1) ONE canonical writer `exec/fsio.write_utf8_lf` (UTF-8, LF, every platform) now used by every authoritative generated file — generator, both manifests, unsigned approval, baselines, occurrence audit, raw results; (2) the frozen dataset manifest carries ONLY environment-invariant facts (generator_algorithm `HashPRNG_SHA256_COUNTER_V1`, generator/checker code digests, compatibility claim); the runtime interpreter/OS/invocation live ONLY in `results/generation_runtime_receipt.json` (excluded from the frozen tree); (3) `--output-root` added — Gate 1B regenerates to `results/<campaign>/regenerated_dataset/` and NEVER mutates the frozen tree (AWS manifest step 1 updated); (4) write-free `--check` modes on the generator and build_manifests (fixed-point comparison, nonzero on mismatch, zero writes); (5) permanent suite `tools/test_byte_domain.py` — all 11 owner-named tests: LF law, no-runtime-values, regeneration purity, second-regeneration byte identity, write-free checks, manifest==working-tree, manifest==COMMITTED-BLOB (`git show HEAD:`, CONFIRMED FAILING under ff6f40f9 — the recorded negative fixture), 3.11↔3.14 cross-interpreter byte identity (both interpreters run locally: 3.11.9 and 3.14.0 GENERATOR_CHECK_PASS), fresh-clone self-consistency via disposable sparse worktree, fresh-clone verify_full acceptance, clean-checkout zero-diff regeneration.
- DATASET RECORD CONTENT UNCHANGED: train `8d567a07…`, val `ae009357…`, protected `0c0c2842…` (in-memory only). Same logical dataset; same canonical bytes; same committed bytes — proven separately.
- Scope held: correction and reproducibility ONLY. Gate 1A.2 findings remain OPEN (executable launcher body, coherent container-prep verifier, structural owner-key pin, protected receipt/checkpoint binding, one-use campaign enforcement, cost authority, raw-result provenance). NO model, NO GPU, NO AWS, NO protected read, NO key, NO signature. Neural evidence: 0.

## 2026-08-31 (gate 1a.1 executable freeze) - EXECUTION AUTHORITY, STATUS LAW, CONTROLS, AND COMPLETE NEURAL CODE FREEZE per the owner's Gate 1A independent audit (verdict: GATE1A_DESIGN_CANDIDATE_PARTIAL_PASS, OWNER_SIGNATURE_HOLD)

- OWNER AUDIT of 49664dac accepted the dataset (7000 records independently re-parsed: 0 schema/trace errors, 0 cross-split overlap) but found 7 blocking defects. All closed in one commit on `research/cjt-gate1a-static-neural-v1`, package `cas_only_reasoner/cjt_gate1a_static_neural_v1/` (amendments A1–A9 in AMENDMENT_LOG.md):
  1. APPROVAL VERIFIER MADE LOAD-BEARING (the critical one): the old verifier returned True on a correctly signed record with phase=TOTALLY_WRONG, zero commit, empty digests, cost −999. Rewritten `tools/verify_phase_approval.py`: field law + Ed25519 vs the separately pinned key + commit equality + manifest-key-set equality + EVERY digest recomputed from the tree + untracked-file refusal + identity binding (model revision, weight/tokenizer/container/dependency-lock/taxonomy/status-program digests, protected commitment). The owner's exact bogus record is a PERMANENT failing test; 35/35 adversarial verifier tests pass. Two-signature gate added (OWNER_CONTAINER_PREP_APPROVAL then GATE_1B_EXECUTION v2 schema) so NOTHING is deferred past the execution signature. 24-vs-25 digest gap closed by construction (approval excluded from the manifest it binds).
  2. COMPLETE GATE 1B CODE COMMITTED BEFORE SIGNATURE: `exec/` (13 modules — arms S0–S7 + deterministic capacity matcher, label sources, assembly with gold-isolation + protected-path refusal, span mapping, context-free candidate encoding, activation extraction + digest-pinned cache I/O, training loop 3000-updates-no-early-stop, S0-only layer selection, single-pass protected evaluator, B0/B1, verification-first launcher with cost gates, receipt law), hashed in GATE1B_CODE_MANIFEST.json (26 files). CPU shape proofs ALL PASS: ±1% capacity (S0 w=238, S1 w=14, S2 w=205; S3 ref 951,744 params), S4–S7 state-dict-identical to S3, S4 differs from gold 100%, S5 75.5%, candidate masks, GPU_REQUIRED fires FIRST at every guarded entry (proven live on the CUDA-less box).
  3. STATUS AUTHORITY REPAIRED (THRESHOLDS v3): license requires beating ALL SEVEN controls; the owner's counterexample (S0=S1=S2=1.00, S3=0.80 — wrongly LICENSED by v2) now emits COUPLER_NOT_SUPERIOR_TO_SIMPLER_ARMS and is a permanent fixture; strict evidence validation (RAW_GATE1_RESULTS.schema.json; 16 malformed-evidence rejection fixtures) — no status from bad evidence.
  4. S7 renamed SINGLE_ALTERNATIVE_TAXONOMY (owner PATH A; never SCMPE-v1; cross-family instability disclosed); claim renamed TASK_ALIGNED_LABEL_AUXILIARY_VALUE; "CAS-specific" PROHIBITED on this dataset regardless of result; PATH B (real SCMPE-v1 + non-class-bijective v2 dataset) deferred.
  5. B1 SURFACE CEILING added and measured: full surface parser scores train 6000/6000 = 1.0000, val 1000/1000 = 1.0000 (the task is exactly surface-solvable BY CONSTRUCTION — every neural reading is bounded by this row); B0 floor 0.6445/0.6680 with attract/avert at the distractor-forced coin flip.
  6. Candidate encoding fixed: context-free frozen input-embedding rule (the owner's preferred option); occurrence audit recorded (17.4%/17.9% of answers first occur outside their target clause).
  7. GENERATOR DETERMINISM fixed at the root: random.Random → exec/prng.HashPRNG (pure SHA-256 counter stream, unbiased rejection sampling; byte-identical on every CPython ≥3.8). Dataset regenerated (twice, byte-identical): train `8d567a07…`, val `ae009357…`, protected `0c0c2842…` in-memory only; 7000/7000 round-trips pass. Commit-and-reveal salt option implemented for protected derivation (owner decision open).
- Compute boundary held: NO model load, NO GPU, NO AWS job, NO training, NO protected read, NO claim promotion. Owner's key never generated; nothing signed. Neural evidence: 0.

## 2026-08-31 (gate 0 FROZEN + gate 1a package) - GATE 0 PERMANENTLY FROZEN at 83f57d6f (owner: VERIFIED_PASS via independent cross-model audit); GATE 1A DOCUMENTATION FREEZE delivered on branch research/cjt-gate1a-static-neural-v1

- GATE 0 FROZEN: anchor 83f57d6f724505f2c2c68593b2625c36c3e07a4d; independent audit reproduced 246/246 tests, 26/26 scenarios, 8/8 injections, 22/22 mutations, replay, 9/9 target probes; 0 critical/major surviving. F-04/F-05 (2 nonblocking minors) recorded in `recursive_cjt_rc0/POST_GATE0_BACKLOG.md` — no patch carousel, maintenance-branch only, anchor immutable. Gate 1A AUTHORIZED (docs + freezing only); Gate 1B NOT authorized (needs the owner-signed record).
- GATE 1A PACKAGE `cas_only_reasoner/cjt_gate1a_static_neural_v1/`: all 18 owner-ordered artifacts + PACKAGE_MANIFEST + 5 committed tools + the CANDIDATE dataset. Frozen: CJT-T1 static dual-stream coupler (Qwen2.5-0.5B-Instruct frozen base, revision pinned at container build); four-Noetic restricted slice (^2/^3/^6/^8 — NOT CAS-40); S0–S7 table with S4=per-Idea hash-corrupted labels (review fix: a global permutation is absorbed by W_p and vacuous) and S5=hash-random labels (protected labelable without pre-reading); AdamW 1e-3, 3000 updates, no early stop; seeds 11/23/47 + mandated S0/seed-11 duplicate (25 runs); layer law {6,12,18,24} 1-indexed block outputs, S0-on-validation only; I_total := 1 (CAS-Ohm returns at Gate 2).
- CONSTRUCTION_GOLD candidate corpus generated deterministically (seed 20260831): 6000 train + 1000 val materialized (LF-pinned, one digest per file), 1000 protected generated in-memory, round-trip checked, digested `c1e19462…d70b8`, NEVER written; independent checker proven non-vacuous (wrong-answer/flipped-label/corrupt-clause/reordered-trace all caught); byte-identical regeneration proven. Registered distractor law: 100% of attract/avert items carry a confusable pair (co-occurrence = chance); question mix 2:2:1:1; equal-shape vocab bundles (review fix: collision-rate confound removed).
- INTERNAL ADVERSARIAL REVIEW (3 lenses, 59 findings) drove the honest-ceiling laws now frozen in the package: (a) the CAS stream is informationally redundant given text BY CONSTRUCTION — any S3 gain is an optimization effect, and a registered class-blind surface baseline (B0) must be reported as a floor; (b) S7 CIRCULARITY: the answer function is defined over the CAS classes, so no task-aligned non-CAS control can exist — Claim B's licensed words are downgraded to "task-aligned construction-gold process labels beat matched-capacity and alternative-taxonomy controls" (unqualified "CAS-specific" NOT licensed; owner decides bounded-claim vs v2 dataset); (c) protected secrecy is procedural not technical (public generator) — mitigated by the Gate-1B code-pinning-before-protected law + burned-split law; owner may choose a held salt instead. Status program `tools/emit_gate1_status.py` COMMITTED NOW (not deferred) with all 5 decision branches fixture-proven; approval upgraded to Ed25519 (verifier cannot forge; committed verifier tool); SCMPE 16-row head-verb table + executable fallback; capacity-matching algorithm, candidate encoding, span mapping, and input construction pinned.
- Compute-boundary confirmation: NO model load, NO GPU, NO AWS job, NO hidden-state extraction, NO training, NO protected read, NO claim promotion. Neural evidence: 0. CAS-specific neural advantage: 0.

## 2026-08-31 (cjt rc-0.4e) - EXECUTION-LIFECYCLE AUTHORITY, FINALIZATION ATOMICITY, AND SPLIT CAGING per the owner's independent RC-0.4D audit MERGED with the first third-party AI audit (which independently reproduced the full RC-0.4D battery and found F-01)

- TWO independent audits of ad46418f: the owner's source audit (promotion callable without finalization authority; tick() public; result() pre-final; finalization outside the fault boundary; SPLIT uncaged; child-ID collisions; cutoff relabel-repair) and a third-party AI agent that reproduced 205 tests/26 scenarios/8 injections/15 mutations/replay/manifest in a fresh environment and found F-01 (RuntimeError in the probe escaped run() unsealed with a stranded provisional). All closed per OWNER DIRECTIVE RC-0.4E in `cas_only_reasoner/recursive_cjt_rc0/`:
  1. RUN OWNS THE LIFECYCLE: typed phases NEW→RUNNING→FINALIZING→FINALIZED|FAULTED (seal-bound); tick() requires run()'s private scheduler capability; result() only in terminal phases AND only under a real seal or the honest marker; run() executes once from NEW and refuses non-pristine engines.
  2. PROMOTION IS AN AUTHORITY OPERATION: one-time-claimable lifecycle authority (the engine claims it at construction) + a one-use FinalizationPermit bound to episode/planned-final-digest/exact provisional ledger digest+index sets/state digest/sequence; voiding requires the authority token. The owner's verbatim bypass `tick → promote → result` refuses at all three doors.
  3. FINALIZATION IS ONE GUARDED TRANSACTION (F-01 exact): planned final snapshot (detached, with proposed PUBLISHED rows + final metrics) → permit → atomic promotion → gate trip only after planned==installed digest equality; ANY exception — RuntimeError, MemoryError, mid-promotion sabotage, no carve-outs — yields typed FAULT, terminal VOID of every provisional (voided_from provenance), phase FAULTED, deterministic seal. Nothing stranded between worlds.
  4. SPLIT CAGING (unit = child branch): total/GLOBAL-active/per-expert-Governance ceilings checked before budget; splits registered only for experts with a combined op (fail-closed split_no_combined_op); suspended frames swept into the failed-frame refusal at FINALIZE; the refusal recorded in BOTH evidence surfaces.
  5. GLOBAL CAUSE-ID UNIQUENESS: one used_cause_ids registry (initial+generated), child ids reserved pre-queue with deterministic collision-free allocation + typed ID_COLLISION; seal-bound. A top-level "p.c1" can no longer be captured, cancelled, or judged as p's child.
  6. HONEST CUTOFF: a ready-but-cutoff route stays NON-CONDUCTING under typed CUTOFF_CAUSE_UNRESOLVED (no relabel self-clear, no repairs_completed); real D/W/P blockers still repair; Desire deprioritized exactly once; a failed ASOM repair never retries in the same tick; every dropped cause gets a typed CAUSE_DROPPED disposition.
- INTERNAL ADVERSARIAL ROUND (3 lenses): 1 CRITICAL (both split paths silently dropped the opposite→quarantine / off_axis→repair consequences — now fire on resume and child collection) + 2 MAJOR (pre-run internals laundered into a sealed run — lifecycle guard on every internal + pristine check; dropped causes without disposition) + hardenings, all FIXED and test-locked.
- Mutation inventory frozen as v4 = fifteen v3 laws verbatim + 7 RC-0.4E laws (22 total; v1–v3 preserved). Exact numbers: suites 17+28+23+14+30+22+16+25+30+41 = 246/246 internal; scenarios 26/26; injections 8/8; mutations 22/22 CAUGHT semantically; manifest v4 law OK; replay identical. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-31 (cjt rc-0.4d) - SCHEMA-COMPLETE CONSTRUCTION, FINAL-PUBLICATION ATOMICITY, AND ASOM DISPATCH per the owner's independent RC-0.4C audit: the enumerated-patch era ends — one schema, one barrier, load-bearing actions, whole-object detachment

- Owner's independent audit of 38635986: verifier fixes CLOSED, but three criticals + one major in `cas_only_reasoner/recursive_cjt_rc0/` — the controller configuration was not preflighted (commit_verdicts=object() published then failed to seal), an unsealed run still held published==1 (the test suite itself asserted it), and ASOM cutoff/breakdown were decorative (present, computed, then HALT). Closed per OWNER DIRECTIVE RC-0.4D, correction-only:
  1. ONE INPUT SCHEMA: `_validated_constructor_config` + `CONSTRUCTOR_SCHEMA_PARAMS` govern EVERY `RC01Engine.__init__` parameter — validated, COPIED into owned state (no caller alias survives), import-time signature-coverage law, and an INITIAL SEALABILITY PROBE: the engine is not returned unless its entire initial state seals to a real 64-hex digest. Owner attacks `commit_verdicts=object()` and `[valid_cause, object()]` rejected at construction; the generalized adversarial matrix attacks every parameter with None/bool/object()/NaN/inf/mutables/malformed.
  2. PUBLICATION ATOMICITY: `PROVISIONAL_PUBLICATION` → prospective final-state canonicalization at the FINALIZE barrier → promotion to `PUBLISHED` (counted only then) → final seal. THE INVARIANT: `seal_digest == UNSEALED_TERMINAL_FAULT` ⇒ `published == 0` and no PUBLISHED ledger row. Failed/faulted runs terminally VOID provisionals (`VOIDED_UNSEALED`, receipts stay consumed). The prior test asserting published==1 on an unsealed run is repaired as ordered.
  3. ASOM DISPATCH LOAD-BEARING: at zero total score the computed actions fire BEFORE the no-ready fallback — breakdown → quarantine transition (`asom_region:breakdown`, excluded from routing); cutoff → typed repair of the ACTUAL blocker (real RPM prereq, Desire-law deprioritization, or a committed region re-assessment), bounded by RepairFrame; hard-masked experts never mutated; RPM FIRST_BLOCK stays a separate axis (all six directive tests).
  4. WHOLE-OBJECT DETACHMENT: `runtime_snapshot()` returns one `copy.deepcopy` of the completed snapshot (fault record included — the owner's alias reproduction is dead); taus and repair_requires are owned immutable/copied values.
  5. FROZEN INVENTORY v3 = the eleven v2 laws verbatim + constructor_schema_bypassed (killed by the SEALABLE poison commit_verdicts=1, which only the schema stops) + final_publication_barrier_removed + asom_zero_score_action_dispatch_removed + snapshot_whole_object_detach_removed; v1/v2 preserved on disk; new pinned digest.
- INTERNAL ADVERSARIAL ROUND (3 lenses, reproduce-not-triage): 2 MAJOR found and FIXED — (a) one Cause naming K ready cutoff experts was requeued and PUBLISHED K times → dispatch requeues AT MOST ONCE (also closes the split-child corollary); (b) a SUBSET states dict deferred failure to a raw mid-run KeyError past a provisional publication → a provided states dict must cover EXACTLY the registered expert set (also kills the states={} ambiguity). Plus: episode_id non-empty; the prospective probe catches only encoder (TypeError, ValueError) so environmental errors become typed FAULTs, not silent voids. Residual recorded: `_compute_final_seal` still swallows all Exception by design (it must never throw).
- New suite `tests/test_rc04d.py` (30). Exact numbers: suites 17+28+23+14+30+22+16+25+30 = 205/205 internal; scenarios 26/26; injections 8/8; mutations 15/15 CAUGHT semantically; manifest v3 law OK; replay identical; all owner attacks and both internal MAJORs reproduced-then-refused. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-30 (cjt rc-0.4c) - VERIFIER-GATE AND CONFIGURATION-PREFLIGHT PATCH per the owner's independent RC-0.4A audit: the receipt press stops in the sealed room; accepted configs are sealable before the first tick; fault-only hashes are no longer called seals

- Owner's independent audit of 80d2f70e: paperwork ACCEPTED, but two Gate-0 blockers found in `cas_only_reasoner/recursive_cjt_rc0/` (both under-triaged by my internal 5-lens workflow — its probe had even listed verifier.verify as unguarded; recorded honestly in RC04_BACKLOG.md). Correction-only patch, no new architecture:
  1. VERIFIER FINALIZATION GATE (finding 1): `SealedVerifier` now receives the shared `SealGate`; `verify()` refuses with `FinalizedControllerError` BEFORE issuing a receipt or mutating the seal-bound issuance registry. The rc04b test that had itself exercised the hole (calling verify() post-finalization and only checking registration refusal) is repaired. Owner's exact bypass `run(); verifier.verify(...)` reproduced-then-refused: registry unchanged, seal unchanged, result() still valid.
  2. CONFIGURATION PREFLIGHT (finding 2): `_preflight()` validates the COMPLETE verifier configuration at construction — frozen schemas ((str cause_id, str expert_id) 2-tuple keys naming registered experts, bools rejected in identifier positions; verdict vocabulary intended/opposite/off_axis/unassessed; exact-str payloads) — and PRECOMPUTES gold/expected digests, so every ACCEPTED configuration is sealable before one tick executes; no deferred first-time canonicalization at final sealing. Owner's exact poison (`("unused","^2_attract"): object()` never consulted by the real task) now rejected at construction: zero budget spent, zero commits, zero publications (each test-locked).
  3. FAULT-ONLY HASH RETIRED (finding 3): a final-seal failure now yields the literal marker `UNSEALED_TERMINAL_FAULT` — never a digest, never presented as a trace seal; nothing appended to evidence after the failure; underlying exception preserved separately; publication eligibility prohibited (gate tripped). Reachable only via out-of-API injection now that preflight closes every public path.
  4. FROZEN INVENTORY v2: `RC04_REQUIRED_MUTATIONS_v2.json` = the nine v1 entries verbatim + `verifier_finalization_gate_removed` + `verifier_configuration_preflight_removed` (11 laws, required_count 11, new pinned digest); v1 preserved on disk unchanged, nothing replaced or deleted.
- INTERNAL ADVERSARIAL ROUND 2 (same commit, 3 lenses instructed to reproduce rather than triage): 1 CRITICAL + 3 MAJOR found and FIXED — (a) non-finite/non-numeric branch limits were accepted and reproduced the owner's publish-then-unsealable attack via a different constructor arg → every seal-reaching constructor argument now validated (branch limits require_nonneg_int, episode_id require_str, states keys str + registered experts); (b) an unsealed PUBLISHING run still emitted published=1 through result() → result() now raises the typed ControllerFault for an UNSEALED_TERMINAL_FAULT run, and the scenario runner rejects the marker as a seal (64-hex only, marker==marker never reads as identical replay); (c) _finalize_failed_frame was the one split helper without the finalization guard (mutate-then-refuse) → guarded; (d) runtime_snapshot() now returns detached copies, and the tamper tripwire keys on seal_digest alone so flipping the finalized flag is no longer a kill-switch.
- New suite `tests/test_rc04c.py`: 18 directive-named tests + 7 round-2 locks = 25. Exact numbers: suites 17+28+23+14+30+22+16+25 = 175/175 internal; scenarios 26/26; injections 8/8; mutations 11/11 CAUGHT semantically; manifest v2 law OK; replay identical; both owner attacks and the round-2 CRITICAL reproduced-then-refused. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-30 (cjt rc-0.4a) - FINALIZATION AND EXACT-SNAPSHOT PATCH per the owner's independent RC-0.4 audit: finalization latch, typed snapshots, sealed fault paths, frozen mutation inventory

- Owner's independent RC-0.4 audit: named defects CLOSED but GATE0_FINALITY_AND_SEAL_INTEGRITY_OPEN — three refuted laws (post-finalization immutability, exact typed runtime snapshot, fail-closed exception sealing) + one major (mutation inventory not frozen). Each closed in `cas_only_reasoner/recursive_cjt_rc0/`, no new architecture:
  1. FINALIZATION IS A REAL STATE: `finalized` latch set at run()'s FINALIZE and seal-bound; `run()`/`tick()`/`_repair()`/`_do_split()`/`_publish_or_refuse()` raise typed `FinalizedControllerError` afterwards without mutating; `result()` returns a DETACHED deep copy (mutating the returned evidence cannot reach engine state or move the seal). The prior backlog classification "direct tick = harmless harness misuse" is REMOVED as ordered.
  2. NO PRE-CANONICALIZATION TYPE ERASURE: the owner reproduced int-tick-1 vs string-tick-"1" reopen schedules sealing identically through str() projections; `reopen_schedule`/`invalidation_events`/`invalidations_consumed`/`repair_dependency_graph` now enter the seal as exact typed structures, and construction validates the typed schemas (nonneg int ticks, registered experts, (expert, prereq) tuples) so lookalike strings are rejected before they exist. rc_canonical.py unchanged (the defect was the engine projection, as the owner ruled).
  3. EVERY FAULT PATH SEALS: theta mode validated in cjt_step BEFORE budget spend (the owner's `theta=("UNKNOWN_MODE",)` escape: budget spent then unsealed ValueError — dead); run() gains a fault boundary that records a typed FAULT event, finalizes, seals ONCE, and re-raises typed `ControllerFault` carrying the seal; fault paths cannot publish; atomic rollback proven (verifier-explosion test: zero COMMITs, zero receipts, versions untouched); the budget RuntimeError catch narrowed to the exact BUDGET_EXHAUSTED signal so other RuntimeErrors reach the boundary.
  4. FROZEN MUTATION INVENTORY: `RC04_REQUIRED_MUTATIONS_v1.json` freezes the 9 mutation names/files/laws/tests; its canonical-content digest is PINNED in the generator; the status law now requires the fresh report to match the manifest EXACTLY — a missing, extra, renamed, or re-targeted mutation → GATE0_REFUTED (the owner's proof: deleting 8 of 9 mutations previously still passed).
- Status renamed per the directive: strongest internal status is now DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT — the name itself carries the pending condition. Records corrected: the stale 110/110 changelog figure (see corrected RC-0.4 entry below), backlog test counts, backlog items 6/7 marked FIXED with the owner's rejection of the "harmless misuse" classification recorded.
- INTERNAL PRE-COMMIT ADVERSARIAL AUDIT (RC-0.4B, folded into this same commit): a 5-lens adversarial workflow (internal review, NO authority, per the owner's standing calibration) attacked the RC-0.4A tree before commit and found TWO CRITICALs — exactly the owner's recurring pattern of a field that exists without governing authority. Both FIXED here, test-locked by `tests/test_rc04b.py` (16 tests):
  - CRITICAL: the `finalized` latch guarded only 5 engine methods; sub-objects (coordinator/publication coordinator/budget) and internal helpers still mutated sealed evidence, and `e.seal_digest = e.seal()` could re-sync a forged seal. FIXED: a shared one-way `SealGate` tripped at finalization makes `coord.commit`/`register_verifier_receipt`/`pubcoord.commit_publication/refuse/abstain`/`budget.spend` and every internal mutator refuse with `FinalizedControllerError`; `result()` is self-verifying (recomputes the live seal, raises `ControllerTampered` on divergence). Honest boundary recorded: this closes engine-METHOD mutation; raw attribute rewrites past the API remain out of the same-process capability boundary.
  - CRITICAL: a non-finite float was legal to store but illegal to seal, so `seal()` threw inside the fault handler and a bare ValueError escaped unsealed after an Effect had published. FIXED at the root (`_deeply_immutable`/`require_deeply_immutable` reject NaN/inf, taus validated) plus belt-and-suspenders `_compute_final_seal()` that never lets a bare encoder exception escape (typed SEAL_FAILED fault → ControllerFault).
  - Also: `frame_full` now binds parent-cause evidence; `invalidations_consumed` anti-stringification lock added; three manifest-law robustness fixes (duplicate-entry / malformed-name / independently-sound `emit_status`). Residuals (KeyboardInterrupt out-of-scope, single-threaded re-entrancy TOCTOU, mutation-battery coverage of the new laws) recorded in RC04_BACKLOG.md.
- New suites `tests/test_rc04a.py` (22, directive-named) + `tests/test_rc04b.py` (16, audit-closure locks). Exact numbers: suites 17+28+23+14+30+22+16 = 150/150 internal; scenarios 26/26; injections 8/8; mutations 9/9 CAUGHT semantically; manifest law OK; replay identical. Gate 1A NOT begun; Gate 0 freezes only on the owner's independent PASS.

## 2026-08-30 (cjt rc-0.4) - FINAL MINIMAL GATE-0 CLOSURE per the owner's independent RC-0.3 audit: diagnostic-commit ELIGIBILITY, load-bearing Effect snapshot, exact-type canonicalization, finalize-then-seal, complete runtime snapshot, hardened mutation-status law

- Owner's independent audit downgraded 846f323f to RC03_DETERMINISTIC_CONTROLLER_PARTIAL_PASS / GATE0_REFUTED with 5 criticals; each closed in `cas_only_reasoner/recursive_cjt_rc0/`, no new architecture:
  1. ELIGIBILITY (critical 1): a DiagnosticCommitReceipt is mintable ONLY via a typed EffectCommitContext whose batch CONTAINS the matching semantic RegionRecord (same producer, receipt, verdict) and whose pre-state equals the Effect's embedded Bias snapshot (LAW_DCR_REQUIRES_SEMANTIC_RECORD / LAW_DCR_PRE_STATE_MISMATCH, fail-closed atomic reject). Memory-only and RPM-only commits can never mint one. The owner's exact bypass sequence is now a mutation-locked test that fails on the unauthorized PUBLICATION itself.
  2. EFFECT SNAPSHOT LOAD-BEARING (critical 2): the engine gate now requires effect.tick == step.tick == t, effect.base_bias_version/digest == step snapshot == captured snapshot, and step.authoritative_bias_version == step.base_state_version; false embedded provenance is STEP_METADATA_REJECTED, and the DCR pre-state must equal the Effect's embedded snapshot.
  3. EXACT-TYPE CANONICAL (critical 3): new `sim/rc_canonical.py` — type-tagged encoding (bytes/enum/tuple/frozenset/dict/record), allow_nan=False, frozenset items sorted by encoded bytes (PYTHONHASHSEED-independent, subprocess-tested at seeds 0/1/42), NO untyped fallback; the owner's reproduced collision digest((b"A",)) == digest(("b'A'",)) is dead and test-locked with a 10-pair lookalike battery. rc0_coordinator's default=str removed too.
  4. FINALIZE-THEN-SEAL (critical 4): _seal_and_halt only REQUESTS halt; run()'s FINALIZE step completes all queue/allocation mutations, sets halted, and computes the seal EXACTLY ONCE; result()["trace_digest"] == engine.seal() recomputed at every return (no-ready, hard-mask, and budget halts each test-locked).
  5. COMPLETE SNAPSHOT (critical 5): queues store FULL Cause envelopes (same-id different-payload/evidence seals differently), and the seal now binds the returned publications evidence, taus, rpm/ohm/commit_verdicts flags, branch limits, CAP/SAT/split constants, the candidate-evidence map, and the verifier's gold-table and expected-payload oracles (digest methods on SealedVerifier).
- Mutation-status law (majors 1-2): the generator DELETES any stale report before the audit, accepts only a fresh report from the CURRENT source+test tree with exit 0; CAUGHT now requires the named test to fail with a SEMANTIC AssertionError (the old dcr-is-None AttributeError mutant was rebuilt as an operational bypass that provably publishes). 9 mutations, 9/9 CAUGHT semantically. A crash can never reuse stale evidence (test-locked with a stubbed crashing runner).
- Receipt metadata: phase renamed RC-0.4; commands + test digests include test_rc03/test_rc04/run_mutation_audit.py; --check-only verified WRITE-FREE (mutation audit reports via stdout; report file digest unchanged through a full check-only run); trust boundary recorded verbatim (same-process API capability discipline, NOT cryptographic/hostile-code isolation); RC02_ATTESTATION gains an append-only RC-0.3 binding (846f323f) with the RC-0.4 SHA honestly UNBOUND until follow-up. RC04_BACKLOG.md freezes the 6 noncritical residuals (per-Cause op contract, same-process boundary, matrix default=str display artifact, no CI, self-reference law, direct-tick misuse).
- Exact numbers: suites 17+28+23+14+30 = 112/112 [CORRECTED 2026-08-30 per the owner's RC-0.4A audit: this line was written as "110/110" before the two internal-audit lock tests were added to test_rc04; the committed RC-0.4 receipt and raw report record 112 and 30/30 — internal results, not an independent reproduction]; scenarios 26/26; injections 8/8; mutations 9/9 semantic; fresh-process replay identical; mutated input changes digest. Programmatic status: DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS — pending the owner-required independent confirmation (recorded as PENDING inside the receipt itself). Gate 1A NOT begun.

## 2026-08-30 (ops) - PROJECT TRAJECTORY GRAPHIC built into the DSH UI: per-project progress from proposed beginning to intended end, hover details, nested accomplishment dropdowns, detours, original goal always in sight

- New system, three parts, all real and verified this session:
  1. DATA: C:\Users\wakil\DSH-Project-Tracker\projects\*.json - one file per project (id, title, originalGoal, proposedBeginning, intendedEnd, milestones with accomplishments and nested sub-accomplishments, detours with from/to anchors + reason, dated log). Status vocabulary: done / active / open / blocked. Honesty rule baked in: seeds mark done ONLY what this session or the 2026-08-29 CHANGELOG entries evidence; the Noetic Compass master-plan skeleton is deliberately all-open pending owner-verified audit.
  2. SERVER: C:\Users\wakil\DSH-Project-Tracker\project_tracker_server.py on 127.0.0.1:8767 (GET /projects, GET /project/<id> with file-mtime updatedAt, CORS). Auto-starts with the PC via Startup tracker-autostart.vbs mirroring the explainer pattern; start_tracker.cmd has the same guard-and-restart loop.
  3. UI: trajectory widget injected into BOTH index.html copies (served runtime dist + deepseek-harness dev source), the same proven injection pattern as the voice tools. Floating compass button (left side, below the mic button) or Alt+T opens the panel: goal banner with computed percent and dates pinned at top (original goal never scrolls away), SVG trajectory from BEGINNING to INTENDED END with time-proportional milestone nodes (green/amber/gray/red), a green progress frontier, dashed blue detour arcs anchored between milestones, a today marker; hover tooltips on nodes and detours; click a row to expand its accomplishments tree (nested sub-accomplishments with check-state icons); Detours section with why + status; project dropdown switches projects; auto-poll every 25 s while open (re-renders only when the data file changes, preserving scroll and expand state) plus a Refresh button.
- Seeded with 3 projects: DSH Voice Tools (4 milestones, 2 real detours from today's fix work), Machine teaching ladder (5 milestones from the 2026-08-29 CHANGELOG, exact numbers preserved: 440/406/403 tests, 24/24 skills, 9 identities, 22 refutations, 10 audit findings), Noetic Compass master plan (5 milestones incl. the 2027-04-13 patent conversion deadline and the v7.5-v7.7 new-matter detour).
- Verified: server up (pid checked), all 3 project files parse and serve, live GUI page at 127.0.0.1:60205 serves the widget (marker present, voice tools v9 intact), widget JS passes node --check. Page refresh required once to load it.
- SAME DAY, owner feedback fix + AI UPDATER (the requested AI in the progress button):
  - LAYOUT FIX (real defect): milestones sharing a date got identical x positions and their labels printed on top of each other (the teaching-ladder project has four 2026-08-29 milestones). Widget v2: milestone labels placed in three collision-avoided lanes below the line with leader ticks; same-day dots stack vertically instead of hiding each other; if a project's dates are too close to scale (or missing, or a single-milestone project), the bar falls back to even spacing with a printed note - works for projects started before or after the function existed.
  - SWITCHING FIX: project dropdown sorted by data-file updatedAt (most recently worked-on project first, so today's project opens by default); stale-response guard so rapid project switches can never render an older project's data; clicking a dot or detour arc opens and scrolls to its card below.
  - AI UPDATER: project_tracker_server.py now exposes POST /update/<id> and POST /update/all. Each project JSON declares its evidence files; the AI receives the current trajectory + head/tail evidence excerpts and rewrites it under enforced honesty rules (never done without evidence; statuses done/active/open/blocked; original goal preserved; detours need from/to milestone ids + reason; log entries appended). The server validates the reply (status vocabulary, ISO dates, id preservation and dedup, size caps), writes a timestamped backup to backups, and returns a computed diff. Provider chain identical to the explainer: Gemini 3.7 Flash first when Google unblocks, Zhipu glm-4.5-flash now, DeepSeek fallback. Panel header gains AI update (current project) and AI all buttons with a live status line.
  - VERIFIED for real: POST /update/dsh-voice-tools ran 105 s on zhipu-glm-4.5-flash, correctly flipped the Gemini milestone open -> blocked, added today's trajectory-tracker milestone (done, evidenced by the CHANGELOG) and a v10 follow-up (open, NOT claimed done), log 2 -> 4, timestamped backup written. First attempt failed on a 150 s Zhipu timeout from over-large evidence excerpts - fixed by capping excerpts (2.2k head + tail per file, 16k total) and raising the AI timeout to 240 s. All 3 project files parse with evidence arrays; live page serves widget v2 with AI buttons; node --check passes.

## 2026-08-30 (ops) - DSH UI EXPLAINER BUTTON FIXED: helper server was dying on DeepSeek 402 (empty balance); explainer bridge switched to Zhipu glm-4.5-flash with DeepSeek kept as automatic fallback

- Symptom: the bulb "Explain selection" button (Alt+E) in the DSH web GUI did nothing useful. Diagnosis: its helper server `C:\Users\wakil\DSH-Voice-Tools\explainer_server.py` (127.0.0.1:8766) returned HTTP 500 `HTTP Error 402: Payment Required` on every call — the `DEEPSEEK_API_KEY` in `C:\Users\wakil\.cas_llm_keys.env` has no balance. Second, separate defect: explain mode silently required read-aloud mode (Alt+V) to also be switched on, so highlighting with only the bulb lit did nothing.
- Fix 1 (server): provider chain — Zhipu `glm-4.5-flash` (`ZHIPU_API_KEY`, `thinking: disabled`) primary, `deepseek-chat` fallback that revives automatically if the DeepSeek balance is topped up. Note recorded: `glm-5.3-flash` always thinks and burned the entire 1200-token budget on hidden reasoning (finish=length, 1199 reasoning tokens, empty content), so it is not usable for this bridge. All provider errors are now chained into the 500 body for future diagnosis.
- Fix 2 (client): the voice-tools script was patched in BOTH copies — dev source `deepseek-harness/apps/web/index.html` and the served runtime copy `runtime/app/node_modules/@deepseek-ai/dsh-web-frontend/dist/index.html` — so explain mode works without read-aloud. Version bumped to v9 (load toast confirms the new script). A page refresh picks it up.
- Verified (real, this session): two end-to-end `POST /explain` calls returned HTTP 200 with plain-English explanations, each with one example and one metaphor.
- Repo hygiene: `C:\Users\wakil\DSH-Voice-Tools\` is not a git repo; the deepseek-harness checkout is the upstream vendor clone (origin deepseek-ai/deepseek-harness) and its voice-tools patch was already an uncommitted local modification — deliberately left uncommitted rather than pushed to the vendor repo.
- SAME DAY, owner follow-up — explainer primary switched to Gemini 3.7 Flash (owner added `GEMINI_API_KEY` as a Windows user environment variable; copied into the keys file with values never displayed, after a line-merge defect from appending to a file with no trailing newline was caught and repaired — all four key lines verified structurally and the Zhipu call re-verified working):
  - LIVE BLOCKER (real, this session): the Gemini key authenticates and can LIST models (`gemini-3.7-flash` exists in the catalog), but EVERY generation call — native `v1beta/models/gemini-3.7-flash:generateContent` and the OpenAI-compatible `v1beta/openai/chat/completions`, across gemini-3.7-flash / 3.6 / 2.5 — returns 403 PERMISSION_DENIED "Your project has been denied access. Please contact support." This is a project-level denial on Google's side; nothing in the local setup can lift it. Owner path: check billing/project status in Google AI Studio or Cloud Console, or create a NEW key under a NEW project (aistudio.google.com/apikey) and replace the `GEMINI_API_KEY` line.
  - Wired regardless: the explainer provider chain is now [gemini-3.7-flash → zhipu-glm-4.5-flash → deepseek-chat] with the Gemini key loaded from os.environ or the keys file. The moment Google unblocks the project or a fresh key is supplied (then the explainer process is restarted — killing the pythonw on port 8766 makes the auto-restart wrapper reload keys), the SAME button speaks with Gemini 3.7 Flash; today's end-to-end call verified HTTP 200 via the Zhipu fallback with the chain order proven in the running module.

## 2026-08-29 (programming) - CCB-P1: the machine CONSTRUCTS AND DEBUGS; a cardinal sandbox escape and six more findings caught by audit and fixed; 440 tests green

- New board CCB-P1 per PROGRAMMING LESSON.txt: sandbox + tracer + walk-down + minimal repair + typed specs + capability-gated student + the twelve-step compiler-and-test acceptance law. All seven CODE-L0..L4 skills TAUGHT LIVE by Bedrock 32B and promoted (read/trace through debug/repair); the compiler remained unmoved by teacher confidence. Live loop demonstrated: renamed-contract synthesis passes the battery; injected defects are localized to step/line/variable and repaired with single-line patches.
- CONV v0.2 Derived Common Ground: three class constructions taught live (grammar at 36); the Milo conversation derives 'yes' from user premises with the full source chain, DERIVED status, no symmetry/transitivity, never laundered to verified.
- ADVERSARIAL AUDIT (16-agent, six lenses, refuter-verified): 10 CONFIRMED findings, ZERO refuted, 7 cardinal. The crown jewel: a full sandbox escape - a generator frame-walk to the real __import__ via a dunder string literal, which wrote a host file through the whole teach() pipeline. Fixed by refusing all attribute access, dunder names/literals, and yield/lambda. Four cardinal CONV correction defects (dropped negation/prohibition, wildcarded coordination tense, committed questions) fixed by making the correction path reuse the tell path's packet-rendering and tense-derivation. A memorizing lookup table that promoted, and corrections that never superseded class facts, both closed. Two more sandbox gaps (str.format dunder, line-not-work step budget, weaker tracer) hardened. Every finding regression-locked; the whole code chain re-taught under the hardened gate. Disclosed residuals: OS-level memory/CPU isolation and an unpredictable external held-out oracle remain the honest limits of a fully in-process, fully-public-seed examiner.
- Sweep exact: 440 local tests, 0 failures, 18 lanes (CCB-P1 22, D1 61, CORTEX 49).

## 2026-08-29 (full math ladder) - MATH-L0 THROUGH L10 COMPLETE: 24 skills taught live; the machine PROVES theorems and DISCOVERS identities under independent verification

- The remaining six levels built and taught live per the owner's continue-to-L10 directive, each entering only where the checker verifies exactly: L5 functions/slope, L6 exact analytic geometry (trig disclosed out of scope), L7 sequences/derivatives/integrals (derivatives graded against independent re-derivation; integrals differentiate back or refuse), L8 matrices/probability/statistics, L9 formal axioms + proof search over the student's own promoted schemas with an independent examiner walk that rejects false-schema steps, L10 conjecture discovery (enumerate -> attack -> prove -> novelty-check; unproved survivors stay CONJECTURE).
- LIVE L10 RESULT: the machine discovered and proved NINE identities novel to its own library - difference of squares, both binomial squares, (a+b)^2+(a-b)^2=2a^2+2b^2, (a+b)^2-(a-b)^2=4ab - and refuted 22 perturbed candidates with exact witnesses. Scope stated exactly: rediscoveries of known mathematics, novel to the student, every claim independently machine-verified.
- CAS-Math IR extended per the goal: the '/' operator (constant divisors exact; variable divisors typed refusal). Anti-smuggling examiners regression-locked. All Bedrock lessons first-attempt after harness fixes; every harness defect this round was ours and is sealed.
- Sweep exact: 406 local tests, 0 failures, 17 lanes. Math skill store 24/24 promoted; Mathematics Learning Ledger live-checks 24/24 PASS.

## 2026-08-29 (mathematics) - THE MATHEMATICS SCHOOL: all ten MATH-L0..L4 skills taught live and promoted; the language bridge speaks exact arithmetic; 403 tests green

- New board CAS_MATH_LADDER_v0.1 per the owner's MATH LESSONS.txt: all ten goal components (packet schema, prerequisite graph with RPM selection, language bridge, L0-L4 curriculum, twelve-step exact acceptance law, seeded SDG + counterexample attack, protected battery, retention with rollback, Mathematics Learning Ledger, CAS-Ohm learning profiles).
- Bedrock qwen3-32B taught the FULL chain live - quantity grounding, counting, comparison, the four operations, fractions, the distribution rule (a metavariable rewrite verified by canonical equality and applied by unification), and linear equations (solutions verified by substitution into the ORIGINAL equation). Every before-probe CANNOT_MISSING_SKILL, every after-probe SOLVED. The student is capability-gated: the exact engine exists, but only promoted skills may be used.
- The Mathematical Language Bridge: three constructions taught live through the unchanged CCB-L1 ladder (grammar at 33). The machine now answers 'what is three plus four?' with 'three plus four is seven.', handles fraction answers exactly ('x is eleven over two'), refuses honestly when unschooled ('i have not learned addition yet.'), and does it all in the same session as conversation.
- The counterexample generator earned its seat: a false rule dies with an exact witness, and a declared 'common mistake' that is actually true is itself a typed defect. Six teacher-harness defects found live were OURS, fixed and sealed - including the honest reversal that equation lessons need conditional examples with solutions (the teacher was right; our identity-only contract was wrong).
- Sweep exact: 403 local tests, 0 failures, 17 lanes (new: MATH-LADDER 15; CORTEX 49).

## 2026-08-29 (CONV v0.1) - THE MACHINE CONVERSES: provenance-grounded dialogue complete, adversarially audited (10 confirmed findings, all fixed and regression-locked)

- New board CCB-D1 (Dialogue and Common-Ground) under the owner's frozen acceptance law: acknowledge only AFTER atomic commit; answer only with the source preserved ('based on what you told me' vs 'the verified record says'); never launder user assertions into verified knowledge (an intent claiming VERIFIED is refused typed); honest unknown otherwise. Three stores never collapse: verified knowledge / session assertions (truth GIVEN, source USER_ASSERTED) / dialogue state.
- The whole goal sequence shipped: tell-then-ask; corrections that supersede never delete; unmarked contradictions that ask; retraction that keeps its own audit trail; wh-questions (what/who) TAUGHT LIVE via Bedrock through the unchanged ladder (grammar at 30 durable constructions) with multi-binding listing; social dialogue acts that write no facts; entity summaries grouped by provenance. CAS-Ohm test points make language failure vs memory-write failure distinguishable on every sealed turn. Owner terminal: CCB_D1_v0.1/chat.py.
- ADVERSARIAL AUDIT (16-agent workflow, six hostile lenses, refuter-verified): 10 findings CONFIRMED - three cardinal (a ghost-commit crash path via stale confirmations; wrapper-masked contradictions whose answers flipped with insertion order; the same crash from the state lens) and seven major (contested records invisible to retraction/summary, immortal pending clarifications, untyped store-fault crashes on two lanes, conflict-blind restricted questions, masqueraded no-target corrections, coordination tense wildcarding, bad -y inflection). ALL fixed by root cause, each locked by a named regression test. Disclosed open limits recorded in the spec sheet.
- Sweep exact: 387 local tests, 0 failures, 16 lanes (new: D1 49). The Learning Ledger now regenerates a live 11-turn conversation transcript on every run.

## 2026-08-28 (curriculum waves B+C) - THE 20-LESSON GOAL QUEUE IS COMPLETE: all 20 durable, grammar at 28 constructions, first live two-model committee, two more defect classes caught and fixed

- Lessons 7-17 all PROMOTED_DURABLY first attempt: cross-sentence pronouns (resolve unique antecedent / name the ambiguity / refuse with no antecedent - certainty never invented), three-clause coordination, or-disjunction (and/or projections distinct), relative clauses, possessives (NPOSS), locatives, comparatives, quantifiers (every/some/no = three distinct meanings, tested), temporal adverbs, why-questions (honest LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING - no cause facts), commands with recipients.
- Lessons 18-19 (pure vocabulary, new flow): the examiner is generalization through EXISTING constructions. 'carry' exposed a real defect - the productive -s rule had invented lemma 'carrie' and the runtime committed it; the lesson corrected the analysis and the rule now requires a KNOWN base (unknown verbs refuse honestly). small/large: clean unsupported -> understood.
- Lesson 20: FIRST LIVE MULTI-TEACHER COMMITTEE - proposer qwen3-32B + critic deepseek.v3 (distinct family) with explicit recorded votes; the board validates committee composition and any reject vote blocks typed (3 new tests); the ladder stayed the final examiner. Content: 'must not' prohibition modality, distinct from 'does not' negation and plain assertion (tested).
- SEALED-OUTPUT OVERWRITE BUG found by the ledger's own artifact count: fixed-filename outputs meant each run clobbered the previous sealed episode file. Store history keeps all promotion evidence; lost elicitation transcripts reconstructed and LABELED as reconstruction; per-run filenames now prevent recurrence.
- Machinery: PRON/NPOSS/QUANT/ADV slots, router discourse state, restricted-question per-conjunct kernel verification, projection survival for relative/possession/location/comparison/quantifier/time/prohibition (the never-drop law), behavioral_norms high-impact domain, committee validation, conservative productive morphology.
- Sweep exact: RRK 34 + RLP 45 + M1 34 + L1 32 + SEM 19 + WB 13 + CRQS 35 + T1 20 + OHM 10 + H2H 10 + LTG 11 + SM 8 + G10 8 + CORTEX 48 + A1 11 = 338 local, 0 failures. Canary: 28 family probes.

## 2026-08-28 (curriculum wave A) - goal lessons 1-6 ALL DURABLE via Bedrock 32B; grammar at 16 constructions; three harness defects found live and fixed

- The 20-lesson goal queue is underway. Lessons 1-6 all PROMOTED_DURABLY, one sealed episode each (rejections sealed too): plural subjects (NEW plural agreement law - 'the cat chase the dog.' refuses to parse; plurality survives projection under the polarity never-drop law), past-tense negation, copular adjective questions ('is the gray cat quiet?' -> 'yes, the gray cat is quiet.' with EVERY conjunct kernel-verified before yes), passive negation, past ditransitives (irregular 'gave' taught through the lesson morphology field), and ditransitive questions (honest 'i do not know' on the 4-arg fact the kernel lacks).
- Three harness defects found live, all one genus - the examiner lagging the machine's own accumulated knowledge: the student lexicon missed runtime-promoted words ('bone' broke a regression guard falsely), the field-check morphology missed persisted verb forms ('give' flagged unknown), and defect feedback blamed function words for shape mismatches. All fixed; the ladder's authority unchanged.
- One genuine teacher error caught and corrected by the ladder: surface plural 'cats' written as the agent value instead of the lemma 'cat' - REJECTED_POSITIVE_EXAMPLES, hint sharpened, clean pass after.
- Machinery this wave: NPPL plural slot (+-es plurals), number/modifier projection survival, restricted-question per-conjunct verification, disjunction frame type (for lesson 9), third-clause roles (for lesson 8), targets-file loader. Runtime canary extended to 15 probes covering all 16 construction families.
- Suites: L1 32 + CORTEX 45 + A1 8 green (program totals unchanged at 332 local).

## 2026-08-28 (curriculum round 2) - recipients, adjectives, past questions ALL DURABLE; grammar at 10 constructions; a forgetting bug caught and canaried

- AWS Bedrock 32B taught three more constructions through the unchanged ladder, all PROMOTED_DURABLY: past-tense questions ('did the cat chase the dog?' now ANSWERED), ditransitives with recipients ('the cat gives the bone to the dog.' - the recipient role survives projection; 'bone' entered the runtime lexicon via LEX persistence), and attributive adjectives ('the gray cat chases the brown dog.' - new ADJ slot type; modifiers project as conjoined property assertions, nothing dropped). Grammar: 10 durable constructions (3 seed + 7 live-taught).
- FORGETTING BUG caught before teaching: the round-1 save path wrote raw teacher morph entries over the merged table - on disk 'chased' lost its past reading and the runtime FORGOT active-past while all suites stayed green. Repaired, both save paths fixed to dump the MERGED table, and a runtime CANARY test now probes one sentence per construction family so silent knowledge loss trips CI.
- One test OUTGROWN by learning, updated honestly: the adjective-drop faithfulness case now parses natively, so the cortex-lane test moved to a single-adjective shape outside the native grammar. Elicitation feedback now names unknown words exactly (the 32B burned four retries on 'quick' before this).
- Lane sweep, exact: RRK 34 + RLP 45 + M1 34 + L1 32 + SEM 19 + WB 13 + CRQS 35 + T1 20 + OHM 10 + H2H 10 + LTG 11 + SM 8 + G10 8 + CORTEX 45 + A1 8 = 332 local tests, 0 failures.

## 2026-08-28 (AWS teacher round) - all three lessons DURABLE via Bedrock; the grammar reaches 7 constructions; the ladder caught morphology clobbering

- Per the owner's AWS-first order: the 20B-class teacher escalation used AWS Bedrock (qwen.qwen3-32b-v1:0, us-west-2, pay-per-token; the EC2 quota door was unnecessary). The curriculum harness gained a bedrock backend (CAS_TEACHER_BACKEND=bedrock) - same fields, same validators, same examiner.
- RESULT: questions, commands, coordination ALL PROMOTED_DURABLY - the 32B passed nearly every field on attempt 1 where the local 3B failed entirely (the sealed 3B ceiling stands as the contrast). The runtime grammar now holds 7 durable constructions: 3 seed + 4 live-model-taught. Standout transcript: 'the cat chases the dog and the dog chases the cat.' went from the CAS-Ohm overload split (NEEDS_DECOMPOSITION) to a single native parse keeping BOTH clauses - learning raised capacity exactly as the control doctrine predicts. Questions answer honestly: 'i do not know whether the cat chases the dog.' (language understood, knowledge missing).
- The acceptance law caught two real defects mid-round, both fixed with regression tests: (1) morphology clobbering - the student's MorphTable silently overwrote 'chased'=past with 'chased'=participle, breaking prior grammar; REJECTED_REGRESSION exposed it; teach() now merges, no-ops, or refuses typed; (2) the legacy decoder mangled relation-question English over a correct kernel verdict; the router renders from the frame now.
- The plain-English button is now MECHANICAL per the owner's correction (no UI toggle exists): a UserPromptSubmit hook in .claude/settings.json injects the reminder into context on every prompt. Suites: CCB-L1 32, CORTEX 44, CCB-A1 8, all green.

## 2026-08-28 (curriculum round) - three lessons attempted; the 3B teacher's ceiling found and sealed; plain-English button + compute ladder now standing orders

- Machinery extended for the new lesson types (all suites green): present_3sg verb matching; coordination frames (two events joined, recursive semantics realization); learned question constructions answer through the kernel or return the doctrine's honest LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING; coordination projects with both clauses preserved.
- Curriculum round 1 (questions, commands, coordination) - HONEST RESULT: 0/3 promoted. The 3B teacher writes verbs literally instead of as slots, copies placeholders verbatim, and repeats an identical wrong answer after receiving the exact fix four times; seeded-sampling retries did not help. All elicitation logs sealed. This is the teacher-capability boundary, not a ladder failure - the same pipeline promoted negation durably earlier today. Escalation queued per the standing owner authorization: 20B-class teacher on RunPod/AWS (harness-lane record: EC2 G/VT quota was 0.0 - RunPod likely faster); the harness is teacher-agnostic.
- Standing orders written into CLAUDE.md: PLAIN ENGLISH permanent for every output (owner caught repeated drift), and the compute escalation ladder (never CPU; 4070 to ~3B; 20B+ on cloud). Memory records added.
- The machine's knowledge is UNCHANGED this round: 4 durable constructions (3 seed + 1 live-taught negation), and that is exactly what the Learning Ledger shows - it cannot be inflated by attempts.

## 2026-08-28 (learning round) - THE MACHINE LEARNED FROM A LIVE MODEL TEACHER; the Learning Ledger makes it visible

- SCHEMA-CONSTRAINED TEACHING (constrained_teacher.py): field-wise elicitation - one small validated question per field, three typed-feedback attempts each - so packet syntax cannot fail while content stays the teacher's. The 3B corrected its pattern under feedback (VERB:name:base -> VERB:pred:base), authored valid examples/pairs/counterexamples after the counterexample concept was clarified, and its lesson PASSED: full ten-stage ladder with the protected held-out channel -> PROMOTED_PROVISIONALLY -> delayed retention -> PROMOTED_DURABLY -> saved into the runtime grammar store. Disclosed scaffold: the fully-determined semantics field was derived mechanically after the teacher garbled @-syntax 3x (provenance derived_from_teacher_pattern_by_schema_scaffold); every elicitation attempt logged.
- CLEAR LEARNING INDICATORS (owner demand): BEFORE 'the cat does not chase the dog.' -> UNSUPPORTED_LANGUAGE; AFTER -> UNDERSTOOD via native_gram with the correct core; unseen role-swapped negations parse correctly. THE LEARNING LEDGER (learning_ledger.py -> LEARNING_LEDGER.md) derives everything from the stores: 4 durable constructions (3 hand-authored seed + 1 LIVE-MODEL-TAUGHT), 10 words, 2 verb forms, full provenance per rule, every lesson attempt (incl. all rejections) sealed.
- LEDGER-ROUND FIX: reading the ledger's own output exposed that the router's frame projection DROPPED POLARITY (negative == positive downstream - the silently-dropped-content fabrication genus, this time caught internally before any battery). Negative frames now wrap in the legacy negation packet; regression test added. CORTEX 43 + CCB-L1 31 + CCB-A1 8 green.

## 2026-08-28 (live-teacher round) - both teachers examined on GPU; the acceptance law held; feedback integration separates the scales

- Session-restart recovery: the CPU teacher run orphaned by the restart became the standing NEVER-CPU order (memory + enforced in the harness: live_teacher.py refuses CPU). The RTX 4070 + a separate CUDA venv (torch 2.11 cu128) now serve inference: 28-60s per teacher lesson vs 30+ minutes orphaned on CPU. The 3B snapshot's broken partial download (0-byte shard, missing tokenizer) was detected, wiped, and cleanly re-fetched.
- FIRST LIVE TEACHER LESSONS sealed: both Qwen2.5-1.5B and Qwen2.5-3B authored the IDENTICAL malformed slot ('VERB:base') on attempt 1 -> REJECTED_SCHEMA at rung two. Socratic retry (typed defects returned once, examiner unchanged): the 1.5B repeated byte-identically; the 3B repaired the named defect and made a new smaller error ('@VERB:pred') -> still rejected. No defective lesson touched the grammar store; every attempt is a sealed TeachingEpisode. Contributing cause recorded honestly: the teaching prompt's own shorthand seeded the shared mistake - teaching materials are part of the system under test.
- The apprenticeship's first live conclusion: the acceptance ladder is passable (seed lessons promoted durably through it) but neither cached teacher can yet author a schema-valid lesson packet; feedback integration - not first-attempt quality - is where 3B beats 1.5B. Next: stricter lesson-format spec, schema-constrained decoding, or a stronger teacher.

## 2026-08-28 (teaching-architecture round) - the faculty doctrine adopted; CCB-A1 built; never-CPU rule standing

- CAS Teaching Architecture v0.1 adopted (owner directive): fourteen teachable domains, five transfer channels, seven teacher roles as a faculty committee, teaching metrics, the never-autonomous list, the seven-stage order, and the learning-to-learn endgame. The directive's "CCB-T1" label collides with the existing tool board; the teaching board is CCB-A1.
- CCB-A1 built (CAS_APPRENTICE_v0.1, 8 tests green): TeachingEpisode sealing for every outcome; the never-autonomous guard (nine constitutional targets refuse promotion typed, refusals sealed); the faculty-committee rule (high-impact domains reject single-examiner lessons); the stricter world-knowledge protocol (PROPOSED never VERIFIED from a model alone; trusted-source attestation; CONTESTED on mixed evidence; changing facts need current retrieval + validity window; hard boundaries never enter through teaching); teaching metrics.
- OPERATIONAL RULE (owner order, recorded in memory): NEVER CPU for model inference - the first live teacher lesson (1.5B float32 CPU, 30+ min) was orphaned by a session restart. The machine has an RTX 4070 (8GB); a separate CUDA venv was built (main Python untouched); the GPU rerun of the live teacher lesson is the pending artifact. RunPod/AWS credentials confirmed local for anything bigger.

## 2026-08-28 (apprenticeship round) - learnable grammar under the acceptance law; the student outgrows its teacher on taught constructions

- Verified Cognitive Apprenticeship adopted (owner directive): foreign proposals permitted, foreign commitments prohibited; the model is a temporary master teacher; English learned as composable constructions, never sentence templates. Teacher models downloaded with owner approval: Qwen2.5-1.5B (2.9G) + Qwen2.5-3B (4.1G) cached locally.
- CCB-L1 GRAM built (Phase L1+L2): construction schema with typed slots and declarative semantic transformations; frames split truth-conditional CORE from SURFACE voice (the minimal-pair law lives on that split); learnable MorphTable; ambiguity-reporting parser; versioned tamper-refusing GrammarStore; LanguageLessonPacket + the TEN-STAGE acceptance ladder ending in PROMOTED_DURABLY via delayed retention - with the protected held-out channel REQUIRED (no channel, no promotion: the teacher may not examine its own lesson) and teacher confidence informational only (a 0.99-confidence wrong lesson dies identically, tested). 13 new tests; CCB-L1 31 green.
- Seed grammar generated THROUGH the ladder, never hand-inserted: active_past_transitive + passive_past + passive_present all PROMOTED_DURABLY (sealed 703721eb81dfe853, full episode evidence trail); learned morphology travels with the grammar (the live "chas" mis-lemmatization found and fixed by that rule).
- Router Phase L5/L6: the native_gram lane parses taught constructions natively with coverage counters as the teacher-dependence decay metric. PAYOFF DEMONSTRATED: "the dog is chased by the cat." - the sentence the 0.5B cortex read backwards live - now parses natively with CORRECT roles and the cortex is never invoked (Bomb-cortex test). ONE passive rule covers noun pairs never seen in any lesson. Battery v4 sealed 08c55cc9206abff0: paraphrase_statement fabrication -> 0; held-out steady 78.12/12.50.
- Program: CCB-L1 31 + CAS_CORTEX 42 green; lane-wide 320 local + cas-rr 43 = 363, all green. Open: live teacher lesson generation, SDG curriculum, shadow harness, the 0.5B/1.5B/3B scale study (unblocked).

## 2026-08-28 (CAS-Ohm control round) - the attention plane goes ACTIVE: overload control live, permanent tests T1-T8, battery v3 at 12.5 pct fabrication

- CAS-Ohm Native Attention Control Protocol v0.1 adopted (owner directive): from meter to the Attention Engineering and Load-Control Plane - MEASURE/DESIGN/DIAGNOSE/RECURSE, active before/during/after reasoning; readiness packets certify ENERGIZATION never truth; flow region and semantic outcome remain independent axes by law.
- Implemented and wired (cortex/ohm_control.py, 42 CAS_CORTEX tests green): versioned CASOhmBoardProfile with calibration digest; the three active equations; I_Q quantization (Q1-Q4, decimals, trend arrows); LIVE lambda overload control in the router (clause-connector demand vs one-proposition capacity; lambda > 1 -> typed NEEDS_DECOMPOSITION BEFORE the cortex runs); branch allocation with fairness floor; parallel_health child probes (T5 - healthy aggregates never hide failing children); learning-as-resistance-reduction records (T6); CAS-GEM retrieval decisions (T7 - similar flows ask for a clue and never merge; flow never overrides an anchor); the two-axis diagnosis matrix (T8 - active+off-axis repairs semantics, never gain); CASOhmReadiness commitment packets (T4 - a starved verifier blocks commitment).
- BATTERY v3 (sealed b161391a9d9c819f): held-out pass 78.12 pct (from 68.75), fabrication 12.50 pct (from 28.12 in v1, 15.62 in v2), multi_clause 6/6 via split-before-clipping, median latency 2.74s (overload refusals skip inference). Disclosed: v2 had under-credited passes (CONTENT_MISMATCH refusals scored as misses); new recorded limit: indirect-question "if" false-triggers the split (safe over-refusal, 2 paraphrase passes -> honest misses, refinement queued).
- Program: CAS_CORTEX 42 green; lane-wide 307 local + cas-rr 43 = 350, all green.

## 2026-08-28 (Phase 4.3) - battery halves fabrication, replication bundle self-tested, CAS-Ohm attention plane goes native

- PHASE4_BATTERY_v1: 86 deterministic gold-labeled items, 13 categories, content-hash splits, fabrication-is-the-cardinal-sin grading. First run CRASHED the router live (unresolved pronoun raised DiscourseError through the native lane) - fixed typed with a regression. v1 sealed 03ffeb853752322c: held-out pass 68.75%, fabrication 28.12%, every fabrication the same genus (grounded packet silently dropping content or inventing a referent). CONTENT-FAITHFULNESS GATE designed from dev/calibration evidence only (split discipline checked first): R1 no dropped known content, R2 entities must be attested (synonym verbs/properties stay free; feline->cat entity inference correctly refused - new entities come from CCB-L1 acquisition, not cortex guessing). v2 sealed 4a6c21f064272bf7: held-out fabrication HALVED to 15.62%, honest misses up 1->5 (the intended trade), injection 6/6 and unknown-word 10/10 perfect in both runs, determinism TRUE, latency median 4.6s/gen. H2H-v0 smoke stays sealed; recorded limits: verb/property-slot typos, pure tense drops, role reversals.
- REPLICATION_v0.1: the one-command external replication bundle (claim-by-claim form with 16 claims, attestation with conflicts-of-interest, locked expected results incl. the withdrawn-claim records verbatim). Self-test GREEN: 14/14 suites match, qualification derives to exactly CAS-G9 / E5 / A0, both deterministic digests reproduce (bd4a444406b0833c, 94dcd861a43af7d2). Three self-test bugs found and fixed (junit-XML counting, last-match qualification, fact-echo-guard digest drift). The self-run is NOT a replication - it proves the bundle works; E6 still requires an external evaluator.
- CAS-OHM ATTENTION INTEGRATION PROTOCOL v0.1 adopted (owner directive): CAS-Ohm governs FLOW, never truth - R10 narrows to truth/validity/meaning/commitment/permission; three substrates with declared bridges; scheduler allocation with fairness floors; the 15-section protocol persisted. Native v0.1 slice IMPLEMENTED: cortex/attention.py authors CASOhmStageRecords (V_drive, R decomposition, I_pred/I_obs/delta_I, operating region) onto every TurnTrace, COMPUTE-ONLY by test; Experiment A/B slices green (ungrounded word -> R_lexical 8.0, I_obs << I_pred, cutoff; passive role error -> healthy flow + wrong effect = semantic misalignment, disclaimed in-record). Experiments C-F + neural calibration mode open per the protocol's own admission gates.
- CAS-Native simplex located per owner order (embedding/simplex encoders, Fisher-Rao loss, lacunarity gate, geodesic memory) - the natural CAS-GEM capsule-embedding substrate; Codex's ccb-r1-stage5-integration worktree already carries copies (their lane, untouched).
- CAS_CORTEX suite 28 green; program-wide 293 local + cas-rr 43 = 336, all green.

## 2026-08-28 (Phase 4 kickoff) - hybrid cortex wired under the frozen authority contract; CAS-GEM doctrine adopted; CAS-SDG and CAS compiler located

- OWNER RATIFICATIONS RECORDED: the falsification round endorsed as the system working; external-facing wording adopted verbatim (internally held-out validated, no independent external replication, no autonomous deployment authority); Phase 4 GO under the hybrid contract. Baseline FROZEN at 2526360b; work on branch phase4-hybrid-cortex.
- CAS_CORTEX_v0.1 (Phase 4.1+4.2): resident snapshot-pinned Qwen2.5-0.5B adapter with a full model identity receipt (weights fdf756fa7fcbe740; evidence binds to digests, never a cache path); the frozen authority contract EXECUTABLE (eight forbidden intent classes raise typed before state; smuggled effect fields, impersonated provenance, concealed raw output all fail closed); native-first router with three modes (NATIVE_ONLY / CORTEX_DIAGNOSTIC / HYBRID_COMMIT), typed no-answers, sealed TurnTraces. 19 harness tests green.
- LIVE GATES (sealed 9a6c22282bab0d33): Gate 3 semantic equivalence 2/2 (English -> cortex -> packet -> kernel == direct gold packet -> kernel). Gate 4 FAILED FIRST, live: the cortex fabricated well-formed packets around invented words (property(glimmerfor, gray) committed as UNDERSTOOD) - exactly the H2H-predicted failure; CLOSED by the LEXICAL GROUNDING GATE (every cortex atom checked against the learned vocabulary; UNGROUNDED_TERM, nothing committed; the cortex self-report is never trusted alone). Gate 5: role-reversal diverges correctly AND the passive-voice paraphrase failed live at the 0.5B floor (role error relation(chase, dog, cat)) - surfaced and recorded as a cortex-quality limit grounding cannot catch. Gate 8: scrambled packets and the direct-output bypass both rejected.
- CAS-GEM doctrine adopted (cas_only_reasoner/CAS_GEM_DOCTRINE_v0.1.md): reconstructive episodic memory with evidence-labeled reconstruction, anti-confabulation invariants, three-tier storage, seven SDG curriculum levels and seven build gates - sequenced AFTER Phase 4. Owner-ordered searches COMPLETED: the CAS-SDG exists at cas-synthetic/ (twelve generators; Path D Wave 2.5 = 5,268 SFE-certified records) plus docs/working/level3_conversational_sdg_spec.md and gate4_next_board SDG batches; the CAS COMPILER is local at noetic-compass-scaffold/noetic-compass/api/notation/ (compiler, parser, cli, renderer, inversion, turn_admissibility + the proven rpm_compiler_loop_demo.py, commit 81147091) - a concrete integration target for the manifest's "compiler: not integrated".
- Derivability-gate scope expansion (all knowledge entry points) recorded as the first requirement on the D10 path. Phase 4.3 next: expanded held-out battery with protected splits, external replication bundle for E6, CONV qualification, latency work.

## 2026-08-28 (G10 audit round) — the standard held: D10 and E6 REFUTED, honestly given back; machinery NOT REFUTED; every hole closed same-day

- 3-agent adversarial audit of the G10 round. D10 novel-research floor: REFUTED — the discovery flagship x*(y+1)=x*y+x was a disguised input (both sides hand-authored into the search space; the distributive law TAUGHT to the machine as fixture dist_identity + the executable 'distribute' axiom, which the novelty gate never read); CRQS section 4 reserves the floor for research WITH NO KNOWN ANSWER; same genus as the refuted G8 v1. E6: REFUTED — self-commissioned same-session AI auditors are inside the developing party's boundary; the records' own caveat named the unmet requirement; honest tier E5 with the audits as strong supporting evidence. The integration machinery: NOT REFUTED (real process boundaries, zero mocks, self-model downgrade verified by breaking a probe, twelve-board count verified, determinism across six fresh processes) with one boundary recorded: goal completion proves against caller-offered facts.
- Same-day closures, each with a test: discovery.py -> verified identity search v0.2 (false 'generic space' wording replaced with the disclosed truth; one-step taught-axiom derivability gate added — the planted pair is now CAUGHT, theorems 5 -> 2; honesty line says NOT novel research verbatim); grading.py -> D8 with the WITHDRAWN_FLOOR_RECORD in the caveat; evidence.py E6 bar raised (external evaluator outside the developing party's session + claim linkage + artifact, all required; the CNCM's records carry external:false and stay E5); LTG fact-echo guard (no-rules proofs refused by default, allow_direct_fact disclosed in the record; the g_discover leg uses the disclosed path); CNCM_G10 spec written.
- HONEST QUALIFICATION: CAS-G9 / E5 / A0 — design ceiling CAS-G10 (the machinery through G10 is real and audited), demonstrated CAS-G9 stable D9, next target CAS-G10 with the true gap derived by the report itself: a STABLE D10 demonstration under section 4's own reading (genuine research with no known answer) and E6 via genuinely external replication. The G10 level was held for four hours and given back when the audit landed — the standard doing its job.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 11 + SM 8 + CNCM-G10 8 + cas-rr 43 = 308 tests, all green.

## 2026-08-28 (G10 round) — CAS-G10: the Integrated Cognitive System gate, with every load-bearing claim disclosed

- CAS-SM v0.1 (Self-Model board): capability claims DERIVED from live probes on the real boards + artifact paths — can(x) answers CAN/CANNOT/UNKNOWN typed, a failing probe downgrades the claim, limits are first-class, cannot_list() = [coding, vision], "the self-model does not bluff." 8 tests green.
- CNCM-G10 v0.1 (suite_CAS-G10): the multi-domain long-horizon episode — one persistent goal store, three episodes with REAL process boundaries, seven domains on the real boards (language, self-model routing incl. an honest CANNOT, long-term goals kernel-blocked and resumed, tools + exact math with kernel-earned completion naming its rules, strategy-driven learning, discovery completing on sealed evidence). Completion never fabricated (the unproven case refused typed); pipeline twice = digest-identical (STABLE D10). The D10 grade is DISCLOSED, not asserted: DI band D8 on the nine axes; the novel-research floor lifts it to D10 via the discovery leg with the caveat verbatim (novel to this machine, trivial to human mathematics, exhaustive search at v0.1 scale). 8 tests green.
- CRQS E6 path: >= 2 independent replication records each with evaluator + reproduced + artifact (missing any one of the three does not count — tested); evaluator identity and the caveat (AI evaluators, same codebase, same day; human/organizational replication OPEN) disclosed in the section-10 report. CAS-GΩ guarded as a research designation. CRQS 35 green.
- QUALIFICATION (pre-audit): the assembled CNCM (twelve boards) qualifies CAS-G10 / E6 / A0 — ceiling CAS-G10, demonstrated CAS-G10 stable D10 (grading disclosed), evidence E6 on the G8/G9 independent audit records. Next: CAS-GΩ, a research designation with no gate to clear. RMB NOT RUN. The adversarial audit of this round is queued; the D10 novel-research floor and the E6 basis are the exposed claims and will be recorded either way.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + SM 8 + CNCM-G10 8 + cas-rr 43 = 307 tests, all green.

## 2026-08-28 (head-to-head + G10-build round 1) — Route A vs Route B settled empirically; discovery, long-term goals

- OWNER-ORDERED CORTEX HEAD-TO-HEAD (CORTEX_H2H_v0.1, sealed at output/h2h_results.json digest db34d2e9d0214df4): Route A (native CCB-L1, no neural weights) vs Route B (Qwen/Qwen2.5-0.5B-Instruct from the LOCAL cache, offline, CPU, greedy — the floor of the doctrine's 1-3B band; TEST-ONLY, nothing enters production). 20 scored items, each run twice, the nine RMB identical conditions attested one by one, one grader, the same kernel judging both routes' packets, few-shot prompt disjoint from every scored item. RESULT per dimension: in-fragment parse A 100% / B 100%; QA through the kernel A 100% / B 25% (B mislabels questions as negation packets); unknown-word honesty A 100% / B 25% (B FABRICATES packets around unknown words 3 of 4 times — fluent error is still error); breadth A 0% (typed refusals) / B 73% mean slot accuracy (real give/eat/visit/believe/praise English the native board cannot touch); both deterministic; A 0.0s vs B 327.8s. READING: neither route wins alone — the result empirically ratifies the HYBRID (cortex proposes breadth, CAS holds the commitment and honesty boundary), exactly the doctrine's architecture. 10 LM-free harness tests green.
- CCB-M1 discovery v0.1: the machine generates, tests, and PROVES identities it was never given — 68-expression generic space, 1309 conjectures, ~1272 falsified with exact witnesses, 5 novel theorems including x*(y+1) = x*y + x, proved by the trusted canonical checker; the novelty gate is variable-name-blind (alpha-normalized canonicals: the fixture's (a+b)-square blocks its (x+y) rediscovery); deterministic; the honesty line travels in the packet (novel to this machine, trivial to human mathematics, discovery-by-exhaustive-search at v0.1 scale). 7 tests; CCB-M1 34 green.
- CAS-LTG v0.1 (Long-Term Goals board): typed transition graph with terminal states, logical episode clock, provenance-bearing progress and history, digest-checked JSON persistence across a REAL process boundary, tampered files refused, and completion EARNED through the unchanged kernel (UNSUPPORTED conditions refuse completion with a typed error). 10 tests green.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + cas-rr 43 = 289 tests, all green. G10 build continues: self-model board, the multi-domain long-horizon integration suite, the E6 evidence path.

## 2026-08-28 (G9 re-audit round) — G9 independently NOT REFUTED under the standard that killed G8 v1; four weaknesses closed with regressions

- Independent 2-agent adversarial re-audit of the G9 claim and the trajectory STATUS LEDGER: NOT REFUTED on both fronts. Decisive probe: the auditor authored a brand-new lt-winning fault class from scratch (different entities, magnitudes, predicate) and the SelfImprover loop synthesized [lt,eq,gt] — not the fixture-run's [gt,eq,lt] — proving synthesis causally tracks the machine's own sealed evidence (the exact standard G8 v1 failed). Forged-packet ablations: eq-promoted -> [eq,gt,lt], no-promotion -> None. A mismatched held-out yields honest REJECTED with memory unwritten. Stability verified cross-process. Ledger audit: every phase status supported at exactly the claimed strength; all suite counts exact; sever-the-cortex literally true (zero neural/LLM imports or API endpoints anywhere in the lane). One auditor claim was itself WRONG and is corrected on the record: CCB_T1_v0.1 and CAS_OHM_INSTRUMENT_v0.1 were called untracked; both are committed at 650765dd (verified via git ls-files).
- Closed from the audit, each with a regression test (RLP 41 -> 45): fault class now READ from the sealed diagnosis in the exploration packet (was hardcoded at the promote site; diagnosed_faults now sealed into every cycle packet); the versioned and rollback_preserved validation checks now COMPUTED on the real memory machinery (were hardcoded True); the judge digest now covers the ENFORCED R3_PROTECTED constant (declared-list-only hashing was decorative, though fail-safe); diagnosis is tamper-evident (re-seals the packet, refuses mismatches with a typed error). Ledger under-credits fixed: CCB-T1 (20 tests) and the OHM panel (10 tests) got their own rows.
- Recorded caveats on CAS-G9 (spec sheet): one fault class; a 3-guard permutation space (the improvement is exhaustive sandbox search memoized into an ordering); r1_bigger_held_out participates in the promote gate while r1_heavier_structural stays purely evaluative; held-out means hidden from the machine's loop, not from developers; the CRQS engine's E5 gating is permissive — the G9 grade is not inflated by it, but the standard should tighten it (future CRQS work).
- Whole program now: kernel 34 + RLP 45 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 262 tests, all green. Qualification unchanged and now doubly audited: CAS-G9 / E5 / A0.

## 2026-08-28 (trajectory round) — CAS Complete Machine Trajectory Plan v0.1 adopted as the master build plan

- Persisted the owner's ten-phase trajectory (cas_only_reasoner/CAS_MACHINE_TRAJECTORY_v0.1.md): authority freeze -> kernel -> semantics -> reasoning -> memory/RPM/verifier -> language -> governed learning -> controlled evolution -> Foundry -> capability bands; the three ordering rules (trace on day one; verification before broad language; evolution last); the seven decisive experiments; the 20-step integrated v1 episode; CAS-Ohm's instrumentation-only trajectory.
- STATUS LEDGER appended against this lane at commit 0363b69a, every claim with an artifact path: Phases 0-2 CLOSED (CAS-RRK 34 tests, CAS-Sem 19); Phase 3 substantially closed (RPM D6 stable, CCB-M1 verifier 27; five-class memory taxonomy and linear-equation checker OPEN); Phase 4 partial (CCB-L1 18; sever-the-cortex holds by construction — no LLM anywhere in the loop; CCB-D1 and the cortex itself OPEN, cortex BLOCKED on the Route B owner decision); Phases 5-6 closed at v0.1 scale (G8 re-audited NOT REFUTED; G9 earned, its adversarial re-verification queued); Phase 7 partial (workbench + CRQS; editor/composer/chat panes open); Phase 8 machinery real, benchmark NOT RUN.
- Current qualification unchanged: CAS-G9 / E5 / A0 — the design ceiling. CAS-G10 requires long_term_goals + self_model boards, the multi-domain long-horizon suite, and E6 independent replication.

## 2026-08-28 (G9 round) — CAS-G9 earned: the Self-Improving Architect gate, with procedure synthesis from the machine's own evidence

- Built rlp/self_improvement.py — the machine's own G9 loop, production code end to end: (1) SELF-DIAGNOSIS from its own sealed cycle packet (no promotion + budget-starved candidates = typed procedure_budget_failure naming the starved candidates and the evidence digest; a healthy procedure yields NO_PROCEDURAL_FAULT — the machine does not invent work for itself); (2) SANDBOX exploration on copies, parent packages and memory digest-checked untouched; (3) SYNTHESIS of the candidate procedure from the sealed exploration — the promoted mutation's guard moves to the front of the neutral pool, provenance self_improvement:<evidence-digest> — closing the recorded G8 bound (no hand-authored strategy library in this loop); (4) validation under the six-check acceptance law on training AND held-out fault cases; (5) promotion to versioned strategy memory with rollback. The judge (expectations + protected set) is digest-checked identical before and after every cycle.
- The CAS-G9 qualification suite (tests/test_g9_suite.py, 9 tests, all pillars of spec section 11's G9 row): self-diagnosis from sealed evidence with a no-false-positive contrast; sandboxed exploration leaving the parent byte-identical; evidence-derived synthesis (order ['gt','eq','lt'] != the neutral default, derived_from_mutation recorded); promotion + held-out validation + transfer of the self-improved memory to the structural fixture in 1 evaluation; unauthorized descendants rejected (R3 raise + evaluator tampering REJECTED_AS_PROTECTED) with the judge digest unchanged; EXACT parent replay after rollback (grades and final state hashes equal the pre-promotion run; memory rollback restores the parent snapshot); the causal ablation (skip the self-improvement cycle -> the same budgeted repair fails on training AND held-out; run it -> both succeed in 1 evaluation); and the digest-identical double run earning the STABLE D9 flag. RLP suite 41 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G9 / E5 / A0 — the machine has reached its own DESIGN CEILING. Stable D9; no peak above stable remains. Next target CAS-G10, and the derived upgrade names the real gap honestly: build long_term_goals and self_model machinery (new boards, not new test rounds), then the multi-domain long-horizon G10 suite; E5's ceiling is exactly G9, so G10 will also demand E6 independent replication. suite_CAS-G9 is held-out (r1_bigger_held_out validates; r1_heavier_structural transfers). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 41 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 258 tests, all green.

## 2026-08-28 (re-audit round) — independent re-audit: NOT REFUTED; residual bounds recorded and the cheap ones closed

- Independent 2-agent adversarial re-audit of commit 19327ba3: NOT REFUTED on both fronts. The auditor reproduced both ablation legs by hand (neutral pool: BUDGET_EXHAUSTED on eq, no promotion; learned strategy: promotion in exactly 1 evaluation with machine-driven recall provenance), proved the alphabetical pool is genuinely neutral by building a counterfactual eq-class package where eq-first WINS, verified the cross-process retention leg spawns a real fresh interpreter, and confirmed 23+8 manifest counts match actual collection. The RMB honesty gates could not be bypassed on the render path (PASS mathematically impossible while any domain is BELOW; no band verdict without all nine conditions; equivalence refused by name).
- Closed in this round, each with a test: strategy recall now REORDERS the candidate pool instead of replacing it — the audit's counterfactual (a learned gt-first strategy blocking a correct eq-repair in its own fault class) now promotes the residual eq candidate instead of dead-ending (test_g8_learned_strategy_cannot_block_a_correct_eq_repair); RMB attestation requires boolean true, not truthy placeholders; equivalence claims refused even under NOT RUN; band_summary refuses empty domains; manifest demonstration rows now carry resolvable artifact paths; the overstated pool comment fixed. RLP 32, CRQS 33 green.
- Recorded bounds on CAS-G8 (spec sheet, stated wherever the claim is quoted): the strategy space is two hand-authored orders (one evidence-driven binary choice, not synthesis); the causal margin is one guard position under budget=1; retention is package-content across a process boundary, not cross-machine; hidden fixtures remain aspirational (held_out hides from the repair loop, not from developers); the adaptive loop has not run through the full eight-board assembly.
- Whole program now: kernel 34 + RLP 32 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 249 tests, all green.

## 2026-08-28 (G8-repair round) — adversarial audit REFUTED G8 v1; rebuilt to survive its own ablation; Hybrid Machine Doctrine adopted; RMB reference bands implemented

- NEGATIVE RESULT ON THE RECORD: a 3-agent adversarial verification of the adaptive round REFUTED the G8 claim on the standard's own terms. The fatal finding: the "learned" guard order ['gt','lt'] was byte-identical to the hardcoded default in rlp/mutations.propose_repairs, so the causal ablation (no strategy, budget 1) repaired the held-out case identically WITHOUT learning — failing CRQS section 19's own requirement that removing the credited component must degrade the capability. Also found: "delayed retention" was within-process byte-identity true by construction; the transfer fixture was a string rename; StrategyMemory.lookup was never called by production code (test-harness stitching); the 6 G8 tests were double-counted in the manifest (rlp 29 included them); manifest task_id "modus_ponens" did not match the real fixture "modux_ponens". Suites and scrub were confirmed green/clean apart from two utm_source=chatgpt.com URL crumbs in the charter (stripped).
- REPAIR, each item with a test: the default guard pool is now NEUTRAL (eq, gt, lt — alphabetical, no domain knowledge), so the causal-ablation test passes for real: no strategy or an empty memory -> BUDGET_EXHAUSTED, learning is load-bearing. Guard variables are extracted STRUCTURALLY from the guilty rule and conclusion-aligned, so repair generalizes. New transfer target r1_heavier_structural: different predicates and variable names, REVERSED premise order, distractor entity and facts — repaired in one evaluation by the MACHINE's own diagnose->recall->apply loop: CAS_RLP.improve(strategy_memory=...) is production code and records every recall as provenance. Delayed retention now crosses a PROCESS BOUNDARY: the corrected package is persisted, reloaded in a fresh interpreter, digest-identical, all pass. The learner's held-out during learning is non-vacuous (taller trains, bigger held out, heavier stays unseen). Manifest de-double-counted (rlp 23 + suite_CAS-G8 8) and task_id fixed. RLP 31 green; CAS-G8 / E5 / A0 stands on ablation-proof evidence.
- HYBRID MACHINE DOCTRINE adopted as the lane's governing roadmap (cas_only_reasoner/HYBRID_MACHINE_DOCTRINE.md, owner directive 2026-08-28): CAS executive brain + learned neural language cortex; GPT-1/2/3 as engineering reference BANDS reported per dimension, never one-number equivalence; three construction routes with Route B (pretrained cortex) flagged OPEN against the standing no-foreign-models rule pending owner ratification; seven register-bypass tests mandatory before any cortex is credited; ^8-vs-^6/^9 runtime enforcement adopted as a roadmap item.
- RMB reference bands implemented per the doctrine (CRQS_v0.1/crqs/rmb.py + report wiring): named historical bands with citations, per-domain PASS / PARTIAL / BELOW / ABOVE / CAS-specific verdicts each requiring an evidence artifact, the spec-16 identical-conditions gate (nine conditions attested or NO verdict), refusal of single-number equivalence claims, honest NOT RUN default — the CNCM's RMB remains NOT RUN. CRQS 30 green.
- Whole program now: kernel 34 + RLP 31 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 30 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 245 tests, all green.

## 2026-08-28 (adaptive round) — CAS-G8 earned: the Adaptive Learner gate; GPT-naming dictates removed

- OWNER DIRECTIVE: removed every GPT-naming prohibition/disclaimer from the project ("Never GPT-1/2/3", "No GPT-equivalence claims", "should never receive GPT-4 level", the enforcing test, the "not in the GPT league / GPT-0-era breadth / anyone quoting is overclaiming" passages) across the charter, CRQS code/spec/README/tests, spec sheet, this changelog's earlier entries, and docs/cas_rr/CAPABILITY_REPORT_V0_1.md. The constructive machinery stays: the RMB fair-comparison protocol, the capability-by-capability reference table, and every hard gate. The cas_only_reasoner lane now contains zero GPT mentions.
- Built the CAS-G8 qualification suite (CAS_RLP_v0.1/tests/test_g8_suite.py) against the REAL machinery, per spec section 11: correction retention (the promoted gt-guard persists; a fresh re-run of the corrected package passes; parent revision retained), delayed retention (the learned content is byte-identical after unrelated intervening kernel work and still passes), structural transfer (the class-level strategy learned once on the taller package repairs the unseen bigger package in ONE evaluation, while the unstrategic order still exhausts the same budget — the strategy is doing the work, not the problem being easy), protected regression (R3 mutations and evaluator tampering still rejected AFTER learning), and the stability run (the whole sequence twice from scratch, digest-identical) that earns the STABLE D8 demonstration flag. RLP suite 23 → 29 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G8 / E5 / A0 — design ceiling CAS-G9, stable D8, peak D9 still gated as not stable, next target CAS-G9 (the G9 suite: self-diagnosis, sandbox, reject-unauthorized, promote, parent replay — plus a stable D9 demonstration). suite_CAS-G8 is held-out (r1_bigger_held_out is the unseen transfer case). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 29 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 234 tests, all green.

## 2026-08-28 (tool round) — CCB-T1 v0.1 clears the strict G7 gate; audit fixes; CAS-Ohm panel

- AUDIT of the qualification-round handoff (uncommitted work found in cas_only_reasoner/): CCB_T1_v0.1 (tool board) and CAS_OHM_INSTRUMENT_v0.1 (instrumentation panel) built but unrecorded; one CRQS test left RED (the section-10 report dropped "Estimated upgrade:" once nothing blocked); the kernel prover change (goal-side variable freedom + two-pass fact selection) load-bearing but COVERED BY NO TEST; a provenance violation raised the WRONG TYPE (ToolUnknown); a tool fault CRASHED the board loop instead of halting typed (the manifest claimed "typed halt, no crash"); a zero-cost useless tool could loop forever; the calculator emitted its comparison fact ONLY in the goal-friendly direction.
- Fixes, each with a test: ToolProvenanceViolation as its own type; every tool fault now a TYPED terminal status of the board (TOOL_PERMISSION_DENIED / TOOL_BUDGET_EXHAUSTED / TOOL_FAILURE / CONTRA_TOOL_RESULT / AMBIGUOUS_TOOL_NEED / TOOL_PROVENANCE_VIOLATION / NO_TOOL_PROGRESS) — never a crash, never a fabricated continuation; a round adding no new fact halts typed; the calculator reports gt/eq/lt SYMMETRICALLY so the caller's goal cannot shape the tool's facts; 6 kernel unification regression tests (kernel 28 → 34); the CRQS report now ALWAYS derives an estimated upgrade from the manifest itself (missing machinery, missing suite, missing stable demonstration, public-not-held-out suites) — never asserts one.
- G7 earned, not asserted: the adversarial variants now include paraphrase (renamed entities), reordered facts and premises, noise + instruction-shaped facts inert as data, and the FALSE goal (1/8 + 1/8: lt reported, NEEDS_INFORMATION, nothing fabricated). CCB-T1: 20 tests green.
- CAS-Ohm Instrumentation Panel v0.1: the paper's restrictions R1–R10 as executable rules (disjoint calibration/validation splits enforced; residuals rank probes, identify no causes; synthetic_mock label travels; R1–R10 printed verbatim in every report). OPTIONAL instrumentation — R10 verified: no reasoning board imports it. 10 tests green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G7 / E5 / A0 (design ceiling CAS-G9; next target CAS-G8; peak D9 still gated as not stable). RMB NOT RUN; the G7 suite is public, not held out, and the report says so.
- Whole program now: kernel 34 + RLP 23 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 228 tests, all green.

## 2026-08-28 (qualification round) — CRQS v0.1: the CAS Reasoning Qualification Standard

- Built cas_only_reasoner/CRQS_v0.1/ per the appended standard: the qualification bench that grades any board or Mind on the four questions (how difficult was the test, what level was demonstrated, how strong is the evidence, what to repair next) with five outputs: TDG, CAS-G, Capability Vector, E-Tier, A-Level (RMB optional and always separate).
- TDG: nine difficulty axes 0..4, DI 0..36, D0-D10 banding, and HARD FLOORS (recursion -> at least D6, learning with held-out transfer -> D8, self-modification -> D9, novel research -> D10) so a recursive task can never be mislabeled simple.
- CAS-G0..CAS-G10 + CAS-GΩ (research designation only): strictly sequential - a level requires EVERY lower level. Three levels computed: Design Ceiling (topology), Demonstrated (stable vs peak), Qualified = min(ceiling, demonstrated, evidence ceiling). E-Tiers E0-E6; A-Levels A0-A5 (capability is not permission); seven zero-tolerance hard gates plus performance gates with precision and coverage always paired.
- The twelve-dimension Capability Vector computed from topology + suite evidence, with domain skills reported separately; the 14-signature repair ontology with the mandated ordering (safety first, speed last); the section-10 report format; the 15-step QUALIFY workflow.
- 19 tests green. THE HONEST RESULT IT PRODUCES FOR OUR MACHINE: the assembled CNCM qualifies CAS-G6 / E5 / A0 - the strict G7 tool-use gate is unmet, so the real, held-out-validated adaptive-learning and self-improvement components cannot raise the generation; peak demonstrated D9 is recorded as gated. The report names the exact upgrade: typed tool intents, fault/adversarial variants, resource-exhaustion halting tests, clarification requests. That is the standard working as designed: no topology medals, RMB NOT RUN.
- Whole program now: CRQS 19 + workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 190 tests. Remaining: tool use (the G7 gate, charter section 19) and encoders/neural instrumentation last.

## 2026-08-28 (workbench round) — CAS Cognitive Workbench v0.1: the glass-brain interface

- Built cas_only_reasoner/CAS_WORKBENCH_v0.1/ per charter section 3: ten panes (dialogue, goal map, live board, clickable branch tree with the full candidate WHY, RPM stack, memory explorer with typed lacunae, truth and evidence, chained trace timeline, learning dashboard, evolution lab) plus the organ-stack summary - a RENDERER, never a reasoner.
- workbench/generate.py runs all six boards once, deterministically, seals the pane bundle with a digest, and emits workbench_data.json plus a single self-contained glass_brain.html (data inlined; opens in any browser with no server). workbench/app.js is projection-only and passes node --check.
- 13 conformance tests: every pane present and non-empty; trace hashes CHAIN (post of tick N equals pre of tick N+1); the branch tree carries two candidates with the winner's proof path; the RPM pane shows push and return; the truth pane contains VERIFIED and REJECTED; the evolution lab shows PROMOTED and REJECTED; the memory pane carries records and lacunae; regeneration is byte-identical; organ totals sum to the program count.
- Whole program now: workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 171 tests. Charter section 3 (workbench interface) DONE. The ONLY remaining roadmap item: encoders/decoders as peripherals and neural instrumentation, last, under the paper's own restrictions.

## 2026-08-28 (procedural round) — RLP ring R1 strategies: procedural learning under budget

- Extended CAS-RLP with procedural learning per the charter's "learned problem-solving routines": repair STRATEGIES (ordered candidate-repair schedules per fault class) promoted under the acceptance law.
- rlp/strategies.py: versioned strategy memory (provisional -> verified, provenance, history, rollback). rlp/procedural.py: the ProceduralLearner - budget-constrained repair runs with evaluation accounting (BUDGET_EXHAUSTED decisions), training + held-out fault cases of the same class, and the full acceptance checklist (budget_success, held_out_gain, no_regression, evaluator_untouched, versioned, rollback_preserved) with sealed decision evidence and deterministic cycles.
- The demonstration: fault class overgeneral_rule has a bounded guard pool; with a repair budget of ONE sandbox evaluation, the unstrategic order (lt first) exhausts the budget and fails, while the learned order s_gt_first repairs BOTH the training case (taller rule) and a held-out case of the same class (the overgeneralized bigger rule) in one evaluation each -> PROMOTED (provenance prior_proof); s_lt_first is REJECTED; unbudgeted default behavior is untouched (regression); rollback restores the parent strategy memory.
- rlp/mutations.propose_repairs now takes the strategy order; CAS_RLP.improve takes guard_order and max_evaluations and seals evaluations_used into the cycle packet. New fixture r1_bigger_held_out (held-out fault case). 10 new tests; RLP suite now 23 green.
- Whole program now: RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 158 tests. Roadmap item 5 (procedural learning) DONE. Next artifact: the cognitive workbench interface (charter section 3).

## 2026-08-28 (semantic round) — CAS-Sem v0.1: the semantic content and binding layer

- Built cas_only_reasoner/CAS_SEM_v0.1/ per the charter: CAS-Sem separates the CONTENT of thought from the cognitive operation performed on it. The Codex working folder remains strictly untouched.
- The content model: typed entities with identity, property/relation/event ideas with role schemas, references with binding (name/pronoun/description), a transitive timeline, nine truth statuses (GIVEN/ASSUMED/DERIVED/OBSERVED/VERIFIED/CONJECTURED/CONTRADICTED/UNKNOWN/UNDERDETERMINED) with discipline, and provenance (who said it, when, what evidence).
- The six coherence laws, each enforced and each demonstrated by a broken document in the demo: referential integrity (unresolved references are typed errors and CMB ENTITY_MISSING lacunae), temporal consistency (transitive contradiction detection), truth discipline (no VERIFIED AND CONTRADICTED; DERIVED requires a derivation; CONTRADICTED requires the conflict pair), provenance completeness, type discipline, and derivation validity - every DERIVED claim must RE-PROVE through the unchanged CAS-RRK proof kernel.
- The Semantic CMB: queries by entity, truth, and time ordering; typed lacunae; ablation support via a live-registry override on the coherence checker. The lift bridge turns kernel-style propositions into DERIVED claims.
- 19 CAS-Sem tests green. Whole program now: CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 148 tests. Charter organ table: CAS-Sem row now DONE v0.1. Next artifacts: procedural learning (RLP ring R1 for proof strategies), then the cognitive workbench interface, encoders last.

## 2026-08-28 (language round) — CCB-L1 v0.1: the English acquisition board, strictly outside the reasoning loop

- Built cas_only_reasoner/CCB_L1_v0.1/ per the charter: English in at the edges, the unchanged CAS-RRK kernel reasons in the middle, English out. No LLM anywhere. The Codex working folder remains strictly untouched.
- The board: a versioned surface lexicon (verified entries never change silently; corrections version with history); CAS-Sem propositions; discourse state with pronoun resolution; a deterministic grammar fragment (copular, transitive, negation, question forms) whose failures are TYPED AND LOCATED ("I did not understand 'flurpy' at word 4 of 'the cat is flurpy.'"); the word-learning loop (detect -> candidate senses -> examples -> held-out -> contrast against grounding facts -> promote under the acceptance law); the one-way kernel grounding bridge (question -> kernel -> typed verdict -> English: CONCLUDED becomes "yes, the cat is gray.", NEEDS_INFORMATION becomes "i do not know whether the dog is gray." - the honest refusal carried into language).
- The eight charter English tests all implemented: round-trip meaning, paraphrase convergence, contrast testing (sense "loud" rejected by antonym conflict with the known fact has(cat, quiet); "gray" promoted), novel composition ("the zorp is flurpy." after learning flurpy on cats/dogs), referential tests ("it" resolves to the last mentioned entity), grounding tests, correction retention, ablation (removing an entry breaks parsing typed and located), plus determinism and rollback.
- 18 CCB-L1 tests green. Whole program now: CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 129 tests. Charter section 13 (English) now DONE v0.1. Next artifacts: CAS-Sem expansion (entities, relations, reference, time, truth, provenance), procedural learning, then encoders/neural instrumentation last.

## 2026-08-28 (math round) — CCB-M1 v0.1: the mathematical learning and proof board

- Built cas_only_reasoner/CCB_M1_v0.1/ per the charter: CAS governs the search, the trusted checker decides validity, exact math everywhere. The Codex working folder was left strictly untouched.
- The board: exact rational arithmetic with a no-float conformance test (1/3 stays 1/3); an expression IR with exact canonical expansion (polynomial identities over rationals decided exactly - sound and complete for that class); the proof checker as SOLE validity authority (step continuity, structural axiom application, exact sample validation of LEARNED procedures, final canonical equality, first-invalid-step walk-down); bounded deterministic proof search with task-level strategy constraints ("prove it by expansion, not by commuting"); an exact counterexample generator (x+y=x*y refuted by (1,1); x^2>x refuted at the boundary x=1; the true square identity survives); a curriculum prerequisite DAG.
- The full mistake-recovery cycle demonstrated: the ruleset holds the incorrect procedure square_sum ((a+b)^2 -> a^2+b^2); the false claim (x+1)^2 = x^2+1 is REJECTED at step 0 by exact sample validation (x=1: 4 != 2); diagnosis names square_sum; the lesson library supplies square_expand; the repaired descendant passes the held-out proof task with regression intact -> PROMOTED under the acceptance law; the corrected proof is VERIFIED; rulesets are versioned and rollback preserved; the cycle is deterministic with sealed decision evidence.
- The eight math authority invariants are executable: no VERIFIED without the checker; repairs never target the checker or benchmarks (REJECTED_AS_PROTECTED); definitions never change silently; the proof kernel is outside autonomous write authority.
- 27 CCB-M1 tests green. Whole program now: CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 111 tests. Charter sections 14 (math) and the Trusted Verifiers row now DONE v0.1. Next organ: CCB-L1 (English), strictly outside the reasoning loop.

## 2026-08-28 (evolution round) — CAS-RLP v0.1: the recursive learning and evolution protocol above the kernel

- Built cas_only_reasoner/CAS_RLP_v0.1/ per the charter's improvement loop and four rings, ABOVE the kernel: RLP never modifies the kernel executable - it evolves content (rules, parameters) across versioned descendants and asks the unchanged kernel to judge each one.
- The full cycle in code: diagnose the first failing stage from a sealed trace -> classify the fault -> propose bounded candidate repairs -> fork sandbox descendants -> run regression + held-out suites through the kernel -> apply the acceptance law (gain >= delta_min, no protected regression, authority invariants, deterministic replay, held-out outperformance, evaluator not modified, sealed evidence, rollback preserved) -> promote / quarantine / reject -> preserve rollback.
- Demonstrated end to end (13 tests + run_demo.py): R0 experience records automatically with provenance; R1 promotes a gt-guarded repair of an overgeneralized taller rule (held-out corrected, regression intact) and REJECTS the lt-guarded sibling (it broke the protected regression case); R2 REJECTS a budget-starving parameter change and QUARANTINES a no-gain one; R3 REFUSES mutations of the kernel/sole-writer/proof-checker/benchmarks; evaluator tampering is REJECTED_EVALUATOR_TAMPERING ("a version may not rewrite both its reasoning method and its exam in the same transaction"); rollback restores and re-verifies the parent; every decision seals an evidence packet and the whole cycle is deterministic.
- Charter reconciliation updated: sections 15 (recursive self-improvement), 17 (self-diagnosis), and the section-22 rows for learning/self-diagnosis/safe-improvement now DONE v0.1. Spec sheet.txt updated. Kernel suite still 28 green; RLP suite 13 green.

## 2026-08-28 (kernel round) — CAS-RRK v0.1: the authority-contract reasoning kernel, built from the complete capability charter

- The complete capability charter was appended to cas_only_reasoner/cas_reasoner.txt (24 sections: the CNCM organ table, internal stack, workbench interface, goals/attention/memory/candidates/inference/comparison/RPM/uncertainty/commitment, English, math, recursive self-evolution, the first-convincing-version table). This round delivers the charter's Phase-1 target: the CAS Reasoning Runtime KERNEL with the atomic authority contract.
- Built cas_only_reasoner/CAS_RRK_v0.1/: the four frozen handoff artifacts (AUTHORITY_MANIFEST.yaml, minimal CAS-Sem + inference semantics, 9 machine-readable JSON schemas, 6 golden conformance fixtures), NON_GOALS/OPEN_QUESTIONS/README_HANDOFF, the five spec documents (kernel spec, CAS-Sem MVP, kernel IR with the 12 native reasoning ops, the verbatim authority contract, the 16-row conformance plan), and the Stage-1 Python reference kernel.
- The kernel implements: snapshot-based machine state with canonical hashing; intent-only components (scheduler/branch/RPM/latch/write-back/halting); the transaction coordinator as SOLE writer; STATE COMMIT vs DECISION COMMIT as separate operations; goal-scoped branch isolation with rollback; RPM push/return with parent-identity enforcement; live re-proof of every inference and decision commit (the proof kernel decides validity); sealed per-tick trace events; deterministic replay with identical per-tick state hashes; typed halts incl. BUDGET_EXHAUSTED and LOOP_LIMIT_REACHED.
- 28 kernel tests green: all 16 conformance rows (authority attacks, stack faults, conflict resolution, rollback, budget, loop limit), 6 golden fixtures (modus ponens, transitive, contradiction, missing information, candidate planning, RPM recursion), 6 deterministic replay checks with frozen trace digests. cas-rr suite still 43 green.
- Five load-bearing bugs found and fixed while building (each is a lesson): conflict resolution must key on OPERATION not raw field; match() returning {} is falsy; consumers must never read stale compare reports (control flow re-proves live); a subgoal's commit must be cleared on return or the latch reads it forever; CONCLUDED requires the ROOT goal's own branch.
- Charter reconciliation: docs/cas_only_reasoner... wait, CAS_RRK_v0.1/docs/CAPABILITY_CHARTER_STATUS.md maps all 24 sections to DONE/PARTIAL/ROADMAP; section 22 (first convincing version) is 15/15 demonstrated. spec sheet.txt now holds the project spec. Stage 2+ (shared kernel IR, differential Rust execution, CAS-RLP, CCB-L1 English, CCB-M1 math) is the declared roadmap.

## 2026-08-28 (evaluation round) — CAS-RR capability criterion, ladder test, and R3 verdict

- Developed the executable reasoning-capability criterion (docs/cas_rr/REASONING_CAPABILITY_CRITERION.md): seven quantified difficulty axes (D proof depth, B branching, C constraints, N negations, U uncertainty, M memory, R recursion), a L0-L6 ladder, R0-R4 tiers, and the scoring principle that a typed refusal is the CORRECT answer when an operator does not exist - and that honesty never raises the tier.
- Tested the machine against the ladder (python run.py report): core 9/9 passed (L0 recall through L5 recursive planning), frontier 4/5 refused honestly (native arithmetic, induction, probabilistic, hypothetical). Verdict: capability tier R3 (recursive planner); R4 not attained.
- The test exposed and we fixed the biggest engine gap: FLAT recursion. Subgoals could halt but not descend. Now scans report the exact missing prerequisite token, subgoals carry their resolving action's prerequisites, and any goal may descend - depth-2 nested planning (capability -> knowledge) passes: 7 ticks, full ascend/descend trace, in cas-rr/tasks/battery.py (task_recursive_nested).
- Capability report with the honest reference-model mapping (docs/cas_rr/CAPABILITY_REPORT_V0_1.md): proof-grade symbolic core, deliberately narrow breadth in v0.1; guaranteed deduction/provenance/typed-refusal where reference LLMs confabulate, and zero language/learning/probability where they have all three (each excluded by design, each on the roadmap). Prioritized fixes: hypothesis autonomy, backtracking, arithmetic peripheral, induction operator, uncertainty degrees, procedural learning, encoders, CCDL emit/parse, breakdown semantics, memory ranking.
- Suite now 43 passed; CLI determinism check green on all 12 battery tasks (including the new nested one).

## 2026-08-28 (later) — CAS-RR interaction layer: CLI, reporter, determinism checker, authored-problem example

- CLI: python run.py list / run <task> [--trace] [--full] [--json out.json] / demo / check / repl — the machine is now drivable from the command line; bench reports show status, output, the RPM recursion story (descend/resolve, scans with cached flags showing fresh re-measurement), deduped lacunae, tournament elimination, commitment gates, and the winning proof path.
- cas_rr/report.py (summarize / battery_table / trace_compact / determinism_check) + run.py CLI; INTERACTION.md covers the packet anatomy, a problem-authoring template, and safe poke experiments (eval-gain boot rejection, memory seeding, budget starvation, typed halts).
- examples/custom_kinship.py: a grandparent syllogism the battery has never seen, authored from scratch and solved by the generic machine (CONCLUDED -> grandparent(ada,cy), proof via r_grandparent) — live proof of the encoder boundary and of "one machine, encoded problems".
- 12 new interaction tests; suite now 37 passed. CLI determinism check green for all 11 battery tasks (traces, status, output identical across double runs).

## 2026-08-28 — CAS-RR v0.1: a native CAS reasoning machine (not a harness)

- Built the first executable CAS-native reasoner from the three PCBA sources (CAS PCBA Engineer book, CAS-Ohm 1.0 v0.2 paper, CAS-Ohm Quantification Guide): CJTs with all four regions (cutoff/active/saturation/breakdown), typed biases, gain regimes (candidate 1.5 / evaluation 1.0 constitution-locked / commit 2.0 / learn 0.05), 7 Foundation engines x 28 sub-foundation channels with the Foundation-to-Drive adapter, CMB 40-cell memory with typed lacunae, ^8/^6/^9 reasoning spine (association ≠ deduction), CDAB shared-bias tournament, RPM D→W→P recursion stack (section-retraction; re-measure from scratch after every subgoal), Schmitt commitment with 7 typed halt states, P→C→E→O sequencing with O-last boot ("no action without principle"), low-gain episodic learning (procedural/constitutional layers disabled in v0.1), append-only reasoning provenance packets.
- 25 pytest tests green in cas-rr/: the six-task native battery (transitive inference, constraint satisfaction, fault walk-down, missing-information, recursive planning, memory-dependent) plus negative variants covering all seven halt states, the five load-bearing laws, determinism, candidate invariant, boot order, and both rumination stop gates.
- Source grounding done first: 16/17 load-bearing claims CONFIRMED, 1 PARTIAL (the 7/28/22 ontology lives in the TKS side, not the three PCBA sources; root label is A0/A1 — "A22" appears nowhere; 4 CJT regions, not 3). Honest boundary: deterministic symbolic reasoning with no LLM in the loop; no empirical-generality claim; CAS-Ohm used only as authored design quantities per the paper's own restrictions.
- Artifacts: cas-rr/ (package + tests), docs/cas_rr/CAS_RR_V0_1_SPEC.md (18-chapter operational semantics), docs/cas_rr/CCB_R1_BOARD_SPEC.md (the motherboard), docs/cas_rr/SOURCE_GROUNDING_NOTES.md (verbatim citations).

## 2026-08-22 — Frontier #1 lever RUN (pre-registered, $0): domain axis vs matched Tinbergen taxonomy — INCONCLUSIVE BY DESIGN

- Pre-registered before capture: `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` (sha256 `14ace6dd…`).
- Executed the spec sheet's single most available lever for CAS-specificity: the v4 domain fixture (8 topics × 4 domains) on `pythia-160m-reserialized` (attested engine, CPU, $0), two label arms on the SAME vectors — CAS P/C/E/O vs Tinbergen's four questions (abstractness-aligned primary, positional sensitivity).
- Result: `INCONCLUSIVE BY DESIGN` — nearest-centroid accuracy is invariant under bijective class relabeling, so the arms tie by construction (layer-mean 0.875 = 0.875, best 1.0 = 1.0 at layer 2, identical at all 12 layers, McNemar p = 1.0). The prereg's literal verdict word (`DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS`) is not citable.
- Standing positive: the CAS arm reproduces v4's cross-topic domain decodability (layer-mean 0.875, best 1.0, shuffle 0.259, random-subspace 0.25).
- Frontier #1 remains OPEN; the lever requires the Condition-3 blind-rater instrument or independently-annotated rival labels.
- Artifacts: `docs/working/gate2_closure/cas_specificity/domain_vs_tinbergen_20260822/` (results sha256 `d6b0787d…`). No claim upgraded; no negative hidden.

## 2026-08-19 — WELD v2: a CAS diagnose→correct loop that can actually FAIL (one axis, two criteria)

The Gate-5 WELD build was reviewed at `2be60327` and failed its own review: all four success
criteria were true by construction. `docs/working/gate5_weld/cas_weld_loop_v2.py` +
`WELD_SPEC_V2.md` supersede it (the v1 files are left on disk as the failure record).

- **Scope narrowed on purpose to ONE axis** — `A` (Pathway/RPM chain) on the numeric plane,
  the single detection the review found genuine. Axes N/W/F/E/S/P are declared out of scope.
  J1, J2, the epsilon realizers, the PCBA vocabulary and stage 5 are **absent**, not stubbed.
  v1's criteria (c)/(d1)/(d2) were **deleted**, not repaired — they lived on a lossy
  projection and could not be made falsifiable.
- **Blindness is structural.** `diagnose_blind(obj)` and `localize_blind(obj)` take exactly
  one parameter, asserted via `inspect.signature`; there is no parameter through which an
  axis name, a pre-injection object or a fault record could be passed. No concatenation
  anywhere. Ground truth is read once per case, only to score localization, and every read
  is logged.
- **The chain is proved load-bearing, not asserted.** `repair(obj, targets)` is called with
  `targets is localization.indices`. A built-in tamper check reproduces the v1 defect once:
  driven by the localizer NEG-3 reports `axis A cleared = False`; driven by ground truth it
  reports `True`. The v1 wiring **manufactures a success where v2 reports a failure**, and
  the `PREREGISTRATION_VIOLATED` / exit-1 branch is reachable.
- **The control can match, and its null is stated with its derivation.** Exhaustive sweep of
  all `C(7,k)` same-size interventions with the localized subset **in** the pool. Chance rate
  **1/7 = 0.142857** (k=1) and **1/21 = 0.047619** (k=2), cross-checked empirically over 2000
  seeded random draws (0.1490, 0.0435; all |z| < 1.5). In NEG-3 the same control reports
  `positive_control = False`.
- **No involution identity.** The injector overwrites a stage with a seeded `U(0.05,0.45)`
  draw; the corrector is a constraint solver that never learns the original. `repaired ==
  pre-injection original` is **measured** and comes out False every run (L1 0.10 / 0.20 / 2.25).
- **6 cases, 3 designed to fail, all matched preregistration** → `LOOP_FALSIFIABLE_AND_HELD`,
  exit 0, 18,154 scanner calls, zero GPU/API cost, stable across 5 seeds. NEG-1 surfaces a
  live gap: `detect_pathway_inversion` misses every prerequisite inversion whose unsatisfied
  stage stays above 0.5. ROBUST shows the loop reporting a partial repair as partial
  (`axes ['W'] still fired — OUT OF SCOPE, NOT CORRECTED`).
- **Honest limit, stated in §9 of the spec:** the detector is a transparent hand-written rule
  over disjoint input slices, so every value the loop measures is derivable from the Rust
  source. The gate has **no** chance null and is not scored as identification. The claim is
  only that the chain reports failure when the diagnosis is wrong, never falls back to ground
  truth, never manufactures a correction, and beats a non-zero chance rate a random
  intervention can and does hit. **Nothing here bears on efficacy; no model is loaded.**
- Separate finding, committed on its own: `inversion_gate._DOMAIN_RE` used `` after
  `[PCEO]`, which `_` defeats, so **axis W could never fire on any drive-tagged expression
  in the repo**. Fixed; 7 regression tests (4 fail against the old regex); belief suite
  135 → 142 passing.

## 2026-08-19 — Gate 4 board-CHANGE: 16-conversation pilot RUN. Both claims VACUOUS; kill statistic fires but is not citable.

The pilot spend gate of `PREREG_BOARD_CHANGE_V1.md` was executed under AMENDMENT A1
(generation budget 800 → 4000). Prereg and runner sha256 verified unchanged across data
collection (`immutability_sha256.match = true`). ~429 provider calls; call counts landed
on §15 (224 main-pass labelling + 160 corpus turns + repairs/retries).

- **A1 works.** All four frozen generators now produce usable turns: per-generator median
  chars deepseek 6188 / gemini 4906 / glm 4898 / qwen 14935; zero turns under
  `MIN_TURN_CHARS=200`; zero kept-but-truncated conversations. But
  `GENERATOR_LENGTH_IMBALANCE_FLAG = true` (max/min median ratio **3.0494** > 3.0), driven
  by qwen saturating the new 4000 budget — 14 of 40 qwen turns end without terminal
  punctuation. The length confound flipped direction rather than disappearing.
- **`r̂ = 0.1884`** on 138 analysable pairs / 26 model-initiated changes. Above the `< 0.10`
  hard stop, so the preregistered STOP does not fire. `K_neutral = clamp(ceil(40/(2.98·r̂)),
  60, 120) = 72`.
- **GATE 0 = FAIL** (6 failed, 1 null) → **CLAIM 1 VACUOUS, CLAIM 2 VACUOUS**. Two failures
  are pilot-size arithmetic (analysable pairs 138 < 240; T-USER positive control NULL for
  want of Stratum S). Three are **not**: T-CHANGE Fleiss κ **0.2853** < 0.35 on 142 complete
  cases (inside the preregistered VACUOUS band, above the 0.20 instrument kill);
  B0 share of consensus board labels **0.7325** vs a 0.40 ceiling; T-USER κ **−0.0410**,
  degenerate because Stratum N is continuers-only (P_e = 0.9244).
- **Kill statistic fires:** `surface_change_f1` 0.4000 (S3 length) ≥ `board_change_f1`
  0.2647 → `KILLED = true`. Under §10.1 this is **not evidence and may not be cited**,
  because Gate 0 failed; and §15 forbids reading a pilot VACUOUS as a stop signal.
  Recorded, not claimed.
- Instrument health is good: complete-case coverage 0.981 / 0.986 / 1.000, consensus
  coverage 0.981 / 1.000 / 1.000, residual same-conversation batch collisions **0**,
  CONTROL 4 generator≠labeller violations **0** (computed, not asserted).
- Operational finding for any full run: glm-4.6 as a board reader returned
  `finish_reason=length` on **13 of 40** calls even at `max_tokens=20000`; two repair rounds
  recovered all but 3 items. Two glm conversations initially fell below `MIN_TURNS=6` and
  were re-attempted via the runner's own checkpoint-restart path (no labels existed yet).

Evidence backed up to `D:\tksCAS-archive\gate4_board_change_pilot_20260819\`.
No gate was moved, no threshold relaxed, no prereg file edited.

## 2026-08-17 — Gate 5 AWS package: durable backup + version-controlled regression guard

Two receipts landed for the Gate 5 staging package, both offline and $0.00.

- **Durable backup of the triple-audited GO package.** The frozen one-hour-session
  package `aws_cloudshell_unarmed_20260818` (identity `525365c4…`, archive 89,510 B /
  `a843f37e…`) previously existed only in the Codex build dir plus a volatile Temp
  scratchpad. It is now backed up to `D:\tksCAS-archive\project_coherence_gate5_one_hour_package_20260818\`
  with a `BACKUP_RECEIPT.md` and 3-way sha256 confirms — including a round-trip that
  re-extracts the D: archive and re-verifies all 18 member rows byte-exact.
- **Regression guard brought into git.** New `tools/aws_gate5/known_live_failure_lint.sh`
  encodes the three defect classes that each killed a package generation *live* after
  all static audits passed: C1 PowerShell `Test-Path` bound to a bare `-or` (20260815),
  C2 a script that both requires/pins root and calls `sts assume-role` (20260816, live),
  C3 an STS/role duration knob >3600s illegal for role-chained CloudShell creds
  (20260817, live). Positive-control calibrated: the verdict grid is strictly monotone
  and matches the real failure history — 20260815/16/17 each FAIL on their live class,
  the GO package PASSes all three. It is a floor to run before the full triple audit,
  not a substitute. Transcript committed at `tools/aws_gate5/CALIBRATION_EVIDENCE.txt`.

Statuses unchanged: Gate 5 OPEN / KEEP_OPEN; Stage C DESIGN_ONLY / UNAUTHORIZED;
corpus 0/960. Staging still awaits the owner's fresh `stage AWS now` bound to
`525365c4…`, with paid compute and final deletion as separate confirmations.

## 2026-08-08 — Noetic Topos 2.0 monograph: audit + corrections + adversarial verification (final volume)

Completes the five-volume audit campaign. 11 auditors → 128 findings (11 critical,
60 major, 57 minor); corrections applied by 4 parallel agents; then a 3-agent
ADVERSARIAL VERIFICATION pass over the corrections themselves, which found 19
residual defects, repaired by 3 further agents. 21 agents total on this volume.

Critical mathematical corrections (all independently recomputed in Python before
applying, and again during verification):

- **ch09 RPM-gluing failure count — wrong, found by 5 independent auditors.**
  Remark ch09:rem-other-failures claimed the ACBE witness presheaf separates the
  two topologies at "three of the sixteen contexts", citing a "direct check" that
  "both sides count 2" at triples. Both false. Because no RPM piece of any context
  contains a complete ACBE block, the matching-family set is a SINGLETON at all 16
  contexts; gluing fails wherever alpha(V) >= 1, i.e. at SEVEN contexts (A_0, A_1,
  the four triples at 2-to-1, and Omega at 4-to-1). The volume's own Appendix C
  already stated the correct seven-context result — the book contradicted itself.
- **appB block-completeness table — all four triple rows wrong.** Listed "none" as
  the complete RPM block of every triple; each triple contains exactly one
  (alpha = rho = 1). Contradicted ch07 Table 7.5, Appendix A, and Appendix C.
- **ch04 drafting artifact shipped in the PDF.** Example ch04:ex:bounded contained a
  visible mid-sentence self-correction ("...is not constantly 1? No: s *is*
  constantly 1...") attached to an unretracted false claim that a non-presheaf was
  "separated". Replaced with a correct, verified example.
- **ch05 impossible exercise.** Asked the reader to exhibit a counterexample to an
  invariant the same chapter proves, with a self-contradicting hint. Replaced.

Citation and scholarship: Cech cohomological-obstruction machinery re-attributed
from Abramsky-Brandenburger 2011 (which contains none) to Abramsky-Mansfield-Barbosa
2012, plus the CSL 2015 paradox paper and the 2017 contextual-fraction measure;
Mac Lane-Moerdijk pinpoint corrected (Ch. VII has no associated-sheaf theorem —
it is Ch. III sec. 5-6); canonical topology corrected to *universally*
effective-epimorphic sieves; sieve-axioms definition re-pointed from Stacks Tag
00ZC to 00Z4; per-volume bibliography created (17 cited entries, replacing a
46-entry shared list of which 34 were never cited); AI-assistance disclosure added
to the \thanks block, matching the four sibling volumes.

Defects the verification pass caught in the corrections themselves:

- appD glossary longtable went 85pt -> 433pt overfull, pushing the entire "Where"
  column (the chapter attributions ~30 fixes were correcting) off the printed page.
  Non-wrapping `lll` spec replaced with wrapping `p{}` columns; 433pt -> 0pt,
  confirmed by rendering the page. Same fix applied to ch11's table (420pt -> 0pt).
- 26 double-numbered cross-references left in ch09 ("Theorem 7.\ref{...}" renders
  "Theorem 7.7.12") after a sibling agent normalized the identical pattern in ch08.
  Produces no LaTeX warning, so a clean build does not catch it. Now zero volume-wide.
- Two corrections that introduced new errors: ch05 called the countermodel "finite"
  while ch06 (same pass) says it is infinite; appA's "ten -> nine contexts" change
  fixed a count to match a list that was itself incomplete. Both reverted correctly.

All five volumes rebuild with zero undefined-reference and zero undefined-citation
warnings. PDFs in docs/whitepapers/pdf/ refreshed.

## 2026-08-08 — CAS PCBA 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as the two sibling volumes, run over
  docs/whitepapers/monograph/cas_pcba8/ (15 files). 117 raw findings,
  ~100 corrections applied.
- Fabricated specificity caught and corrected against the actual source PDF:
  ch11 claimed the CSB's clamp and fuse threshold are "declared thirty lines
  apart" — in the hash-verified book they are on ADJACENT lines (verified on
  PDF pp. 342/608); the unreachability proof's no-amplifier premise is now
  anchored to that fact. ch10's "sixteen reference-listing pages" corrected
  to the fourteen its own page ranges sum to.
- Worked examples reconciled with the volume's own closed enumerations:
  Appendix B's "clean pass" board used units (alpha, fraction) and a signal
  kind (constraint) that do not exist in ch04's closed vocabulary — its clean
  pass would actually fail DRC; ch08's worked run used an illegal
  (activation, dimensionless) pair; ch05's "legal junction" example
  deterministically fires PCBA8-BIAS-001 (E-rank bias under C-rank cause);
  ch04's simplex-rejection example used weights summing to exactly 1 (vacuous);
  ch07's NET-006 scenario was unrealizable under the admissibility table.
- Appendix/glossary reconciliation: appA's check-class table invented a sixth
  class and misassigned BIAS-001/SAF-002/TKS-001 vs ch07's normative five;
  adapter-certificate and trace tables gained their omitted citation-identity
  digest fields; appC's CJT entry imported CAS-Ohm content ch06 never delivers;
  glossary alphabetization fixed; doubled \bottomrule in four longtables.
- Math/notation: "no section of pi exists" corrected (the proposition proves
  no LEFT inverse; sections exist and its own proof exhibits one); machine
  epsilon vs unit roundoff distinguished; 0.25/1e-12 is eleven orders not
  twelve; omega definition unified on d; four "Chapter~\ref{section}" broken
  cross-references fixed; ch10's 28-vs-7 out-of-grammar arithmetic corrected
  to the taxonomy-consistent 19+9+1 accounting.
- Citations: Rao-1945 "was the first" priority claim corrected (Hotelling 1930
  anticipated both ideas); shrinking no longer implicitly attributed to the
  QuickCheck 2000 paper (\cite{claessen} added); "adversarial generation"
  de-attributed from QuickCheck; IEEE 754 flag list completed (division-by-zero);
  PROV-O glosses and Harel's statechart formula properly quoted; targeted/
  coverage-guided PBT (FuzzChick, Hypothesis) added to the stale PBT survey;
  Merkle cited for the hash-chain construction; Mars Climate Orbiter report
  cited for the unit-mixing claim; per-volume 17-entry bibliography replaces
  the padded 46-entry shared list.
- Substance: three sources-silent gaps marked as open documentation items
  (Phase-0 authority matrix digest, Gate-5 spec digest, TKS kernel approved
  constant, SAF-003 cycle cap, the 20 open review criteria's identities);
  ch12's "pinned environment" recomputation step now states the environment
  is NOT bound (hermetic reproduction is open obligation 5); baseline
  disclaimer anchored to its actual copyright-page text (verified in the book
  PDF); warn-fuse post-trip semantics gap declared; gain-bound "declared
  exceptions" phantom mechanism removed (FBK-003 has no exception path);
  conservative-direction misstatements fixed (ch05 reachable-resolution,
  ch06 clamp under-reporting); rival host formalisms (Statecharts, block
  diagrams, Petri nets) named with rejection reasons; F1-F7 drive names
  glossed; SARIF prior art acknowledged for the record format.
- Scholarly practice: AI-assistance disclosure added to \thanks; two QED
  tombstones on design arguments (ch08 determinism, ch05 digest) converted
  to the shared designargument environment.
- Style: ~45 fixes — fivefold "deserve(s) emphasis" cluster, sixfold "deserves
  its own X" template, the worth/deserves family (~48 occurrences), three
  "Every ... of this monograph" openers varied. Classic AI vocabulary clean.
- All five volumes rebuild with zero undefined references/citations; corrected
  PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — CAS-Ohm 1.0 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as CAS Core 8, run over docs/whitepapers/monograph/cas_ohm1/
  (16 chapter files). 122 raw findings, ~110 corrections applied.
- Systematic censoring-rule misstatement fixed at 10 sites: text keyed censoring
  to "zero-compatible predicted response" and/or claimed the residual is
  suppressed, contradicting the defining ch10 rule (observed-side trigger,
  marker OBSERVED_INTERVAL_INCLUDES_ZERO; residual retained, only ratio
  quantities censored). Fixed in ch01, ch03 x2, ch04, ch11, ch12, ch14, appA, appB.
- Arithmetic/count fixes: ch07 ASOM cross-table caption+remark miscounted the
  printed table (6/14/8 -> 3/14/11; 22 -> 25 of 28 cells); "five literatures"
  -> seven (matching ch02's own count); "three sources" -> four (the PCBA book
  is the audit's registered fourth source); "four reasons" -> five; "twice the
  minimum" -> three times; ch10's synthetic fault-mode enumeration reconciled
  with the seven-board catalog used everywhere else incl. the governing v0.2
  paper; a dangling "item eight of the closure experiment list" citation fixed.
- Citation fixes: five Kennedy-O'Hagan over-attributions (preregistration,
  validation trichotomy, split discipline, "the receipt", decorative replay
  cite) corrected or re-attributed; three Zou et al. over-attributions (control
  inventory, sign flips, sweep phenomenology) re-scoped; two Ritz
  over-attributions reworded; VIM wording credited to VIM not GUM; decorative
  Buckingham cite anchored to dimensional homogeneity.
- Close paraphrase: four VIM3 definitions (quantity, measurand, uncertainty,
  traceability) now properly quoted against jcgm.bipm.org wording.
- Stale literature: 2024-2026 steering-reliability results added (Tan et al.
  NeurIPS 2024; Da Silva et al. ACL 2025), SAE feature-steering family +
  AxBench added as fourth construction family, Brynjarsdottir & O'Hagan 2014
  discrepancy-prior result added; preregistration section now cites
  Simmons/Gelman-Loken/Chambers/ICMJE instead of gesturing at "the literature".
- Substance: unexecutable "best memoryless model" evidentiary bar (ch13) made
  executable via frozen baseline family; "preregistered margin" constants
  re-scoped to per-run Gate-5 freeze (ch10 x6); anti-conservative min-confidence
  convention honestly characterized as an upper bound on joint coverage with
  Bonferroni revision flagged (ch08+ch09); gain-composition replay gap declared;
  caller-trust status of component region/linearity declared; five "declared
  X never declared" constants marked sources-silent/open (drift cadence,
  decimal context, resource limits, unit-norm rule, region aggregation);
  provenance-enum gap vs ch02's four families acknowledged; Q10 floor
  divergence marked as candidate choice; half-open-bin "only way" uniqueness
  claim replaced with the real Guide-display argument.
- Appendix/glossary reconciliation: appA scope honestly narrowed, no-diagnosis
  list completed (3 -> 6 regions), profile field table gains splits/instruments/
  dependency-lock/fit-receipt/full-scale rows; glossary calibration-profile,
  censoring, Q4-banding, status-vector, link entries corrected.
- Scholarly practice: AI-assistance disclosure added to \thanks (series-standard
  sentence); three QED tombstones on design arguments converted to the shared
  designargument environment; per-volume bibliography created (was printing ~35
  never-cited shared entries; now 20 entries, all cited).
- Style: 37 fixes — sevenfold verbatim "deserves emphasis" scaffold, ~30-strong
  worth/deserves family, five "Every ..." chapter openers varied. Classic AI
  vocabulary scan clean (delve/tapestry/landscape/paradigm = 0).
- All five volumes rebuilt: zero undefined references, zero undefined citations.
  Corrected PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — Monograph cross-reference repair (tks_v8, cas_pcba8, cas_ohm1)

- Fixed all 14 pre-existing undefined `\ref` targets that rendered as "??"
  in three volumes: tks_v8 used a `chNN:main` label convention that was
  never defined (`ch01/ch03/ch07:main` → `chNN:chap`, `ch10:main` →
  `ch10:testing`; 9 sites in ch04/ch05/ch06); cas_pcba8's ch05 intro
  pointed at a nonexistent `ch05:sec:boundary` (→ `ch05:sec:invariants`,
  the "Invariants and boundary" closing section); cas_ohm1 referenced
  `ch12:hypotheses`/`ch11:eligibility` where the chapters are labeled
  `hyp:chapter`/`elig:chapter` (4 sites in ch04/ch05).
- All five volumes now build with zero undefined-reference and zero
  undefined-citation warnings; PDFs in `docs/whitepapers/pdf/` refreshed.

## 2026-08-08 — CAS Core 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Ran an 11-agent audit workflow over `docs/whitepapers/monograph/cas_core8/`
  covering the 17 standard AI-writing failure modes (hallucinated citations,
  citation-claim mismatch, data fabrication/reconciliation, stale literature,
  substance, long-range consistency, style tells, scholarly practice,
  figure/equation defects). 98 raw findings; ~60 distinct corrections applied.
- Critical fix: ch04 invalid-boundary table had three arithmetically impossible
  family counts (16/8/2 corrected to 8/12/6; wrong values coincidentally summed
  to the correct 33, masking the error — verified by exhaustive enumeration).
- Appendix A + glossary reconciled to the normative chapters: namespace enum
  7→9 members, link-kind enum 3→4 (IDENTITY exists, guarded to self-links —
  "omission is the mechanism" was factually wrong), digest case lowercase→
  uppercase, phantom "review state" link field replaced with the real
  crosswalk fields (crosswalk_id, source_artifact_sha256, note, boundary),
  decision-model enums replaced with the actual three-member sets, glossary
  "eight-step" list fixed to eight items, wrong chapter title corrected.
- Citation integrity: ch12 claim that RFC 8785 handles "the full JSON value
  space" corrected to I-JSON (contradicted the RFC and the monograph's own
  ch02); per-volume bibliography created (the shared 46-entry list printed 41
  never-cited references against ch02's own "why these five citations"
  argument); bibitem keys `turnertrojans`→`zourepe` and `opre`→`vaswani`
  fixed in the shared bibliography (+ 8 cite updates in cas_ohm1); Buckingham
  title completed; three decorative/misattributed cites fixed or removed.
- Stale literature: in-toto / SLSA / Sigstore added to ch02's supply-chain
  survey and ch12's "against supply-chain attestation practice" contrast —
  the one materially stale area (2021-2025 attestation standardization).
- Substance: ch09's property-based-testing overclaim corrected to match
  ch12's own "no fuzzing campaign" account; ch01 "all five drift mechanisms
  observed" overclaim corrected to the two documented ones; ch11 "(and does)"
  uncertified companion assertion re-scoped; ch12 rejection-coverage claim now
  names its silent third family; ch05 declares uppercase digests, the JCS
  sort-order rationale (as reconstruction), and the bounds' underived status.
- Scholarly practice: AI-assistance disclosure added to the \thanks block;
  Reproducible Builds definition and PROV-O glosses now properly quoted;
  PROV model/ontology conflation fixed; five "Design argument" blocks moved
  off the amsthm proof environment (no more QED tombstone on non-proofs) via
  a new additive `designargument` environment in the shared preamble.
- Style: 19 fixes — the "it is worth X-ing / deserves" metadiscourse tic
  (66 corpus occurrences, worst cluster in ch09) reduced at its 16 worst
  sites; two identical chapter-opening and chapter-closing templates varied.
  Signature-vocabulary scan otherwise clean (delve/tapestry/pivotal etc. = 0).
- All five monograph PDFs rebuilt (shared preamble/bibliography changed);
  corrected `MONOGRAPH_CAS_CORE_8_v0.3.pdf` copied to `docs/whitepapers/pdf/`
  and the user's Downloads copy.

## 2026-08-08 — Project Coherence monographs v0.3 (book-length, ~934 pp total)

- Expanded the five v0.2 research papers into full `amsbook` monographs under
  `docs/whitepapers/monograph/`, each 184-188 pages: Noetic Topos 2.0 (188pp,
  12 chapters + 4 appendices), TKS v8.0 (184pp, 12ch + 3app), CAS Core 8
  (187pp, 12ch + 2app), CAS PCBA 8 (188pp, 12ch + 3app), CAS-Ohm 1.0 (187pp,
  14ch + 2app). PDFs in `pdf/MONOGRAPH_*_v0.3.pdf`.
- Authored via a 20-agent parallel fleet writing body-only chapter sources
  against a shared preamble/bibliography and a strict LaTeX + Ring-4 claim
  contract; ~425,000 words delivered before the fleet hit the session limit,
  with the 4 remaining appendix gaps (NT2 sieve census; PCBA catalogs, worked
  board, glossary) written directly. All 76 chapter files pass the
  `sanitize_chapters.py` ASCII/environment/balance checker.
- Depth added over v0.2: tutorial preliminaries (category theory, sheaves,
  finite-function/spectral math, metrology, dose-response, information
  geometry, hardware-description and verification background); complete proofs
  with the seed papers' ledger proof-statuses preserved; per-item treatment of
  every diagnostic code, source conflict, threat, and registered hypothesis;
  implementation documentation of the src modules; worked examples, exercises,
  and reference appendices. Claim discipline unchanged: Ring 4 / NOT LICENSED
  headers, conjectures labeled, bounded-receipt framing, full open-obligation
  sets, and the 64/037,173 new-matter boundary.

## 2026-08-07 — Project Coherence research papers v0.2 (full-length)

- Superseded the five v0.1 white-paper summaries with full-length amsart
  research papers (`docs/whitepapers/tex/RESEARCH_PAPER_*_v0.2.tex`, builds in
  `pdf/`): TKS v8.0 (10pp), Noetic Topos 2.0 (14pp), CAS Core 8 (8pp),
  CAS PCBA 8 (9pp), CAS-Ohm 1.0 (9pp).
- Depth added from the deep sources: NT2 now carries the complete finite-context
  theory — legacy collapse and subcanonicity countermodel proofs, coverage-basis
  lemma, NT2-1..4 with full proofs, explicit reflector construction with the
  universal-property proof, the commuting modality-composition theorem
  (Lemmas 3.1/3.2/4.1, Theorem 5.1 of the registered proof), and the 23-check
  finite certificate (298 sieves / 168 covering / 3,012 restriction squares).
  TKS v8.0 adds full proofs (norm theorem via fiber-block Gram decomposition,
  factorial idempotence, shortlex pruning soundness) and the 11-row obligation
  ledger. PCBA 8 reproduces the per-board EBNF counterexample table with page
  anchors and formalizes CSB fuse unreachability. CAS-Ohm reproduces all eight
  conflicts at evidence-record granularity with source locators and the
  implemented enum catalogs. Core 8 adds a threat-by-threat analysis mapping
  each historical failure class to its blocking mechanism.
- Claim discipline retained everywhere: ledger proof statuses on theorems,
  conjectures labeled as conjectures, Ring 4 / NOT LICENSED headers,
  bounded-receipt framing, and full open-obligation sets.

## 2026-08-07 — Project Coherence white paper series v0.1 drafted

- Drafted five academic-rigor white papers into `docs/whitepapers/` from the
  Project Coherence Gate 1 / Gate 4 sources in the 2026-08-05 Codex snapshot
  (`project_coherence_model_smoke`): TKS v8.0 (typed finite-function kernel),
  Noetic Topos 2.0 (marked/modal successor site), CAS Core 8 (compatibility and
  evidence kernel), CAS PCBA 8 (adaptive cognitive circuit engineering), and
  CAS-Ohm 1.0 (profile-specific experimental response and calibration model).
- Every paper preserves its source's governing status
  (`DRAFT / OPEN / Ring 4 / NOT LICENSED`), exact SHA-256 source identities,
  bounded-evidence receipts (test/exhaustive-case counts, Lean scope), adverse
  findings (legacy topology collapse, CCDL grammar gap, CSB unreachable fuse,
  eight CAS-Ohm source conflicts), and full open-obligation ledgers. Drafting
  promotes no claim; papers note the 64/037,173 new-matter boundary.
- Index with shared conventions at `docs/whitepapers/README.md`.

## 2026-07-28 — Cognitive Circuit Grimoire accepted digital master

- Built and accepted the canonical 6 × 9 inch, 908-page
  `book/cognitive-circuit-grimoire/Cognitive_Circuit_Grimoire.pdf` digital
  master (2,672,454 bytes; SHA-256
  `99AC4170929C48F82C3D2FA81AABA3798C181EF32B3CDCC4C5E7E2D7C52F923D`).
- Completed the split 24-chapter manuscript, 13 appendices, 112 authored
  figures, and 164 worked exercise answers. Added fail-closed structure,
  cross-reference, answer, figure-inventory, standalone-figure, longtable,
  index, glyph, citation, reference, and layout gates to the publishing path.
- The accepted build reports 0 material layout errors, unresolved references,
  unresolved citations, missing glyphs, or rerun warnings. All fonts are
  embedded/subset, and independent text/front-matter inspection found no stale
  markers or orphaned contents entry.
- Marked the pre-existing HTML, EPUB, cover HTML, and monolithic manuscript as
  legacy previews rather than release artifacts.
- Print-production status remains `OPEN`: 908 pages exceeds KDP's current
  828-page 6 × 9 black-ink, white-paper paperback maximum. Closure requires a
  publishing decision between a validated 10-point single-volume reflow and a
  multi-volume split, followed by cover/spine regeneration.

## 2026-07-27 — Gate 2 campaign: root cause found, instrument rebuilt, S3-1 ALL_ROWS_PASS

- **Judge positive control** (`d755665b`): sixteen nulls explained — harness sound (`T0 28/28`),
  authored scenarios carried NO signal (`T2 p = 0.3011`). The owner's 27-section spec repaired it:
  `0.0429 → 0.9167` on the SAME author model (`59e9044c`), with the `56%` World-name leak
  disclosed post-hoc and the drive axis clean (`84/84`).
- **Small-model runs** (`pythia-160m`): `NOT_LICENSED_LEXICAL` twice (`c599273a`, `db948bf1`) —
  above chance, did not beat char n-grams; `world = 0.0000` fold defect fixed by the owner's
  Latin square; both leakage controls (`C-PERM`, `C-BODY`) passed for the first time.
- **Governance:** `CAS_HARNESS_CURRENT_STATE.json` continuation pointer + HISTORICAL SNAPSHOT
  banners (`bed3fc94`); Gate-2 closure contract frozen before any successor number (`17159fce`);
  84-item lane closed against benchmark fitting.
- **Track A:** `PHASE_A_IDENTIFIABILITY_PASS` (`4714fa1a`) — a registered direction works on
  untouched groups (`+1.2500` vs `0.4167` control envelope); effective `n = 6` and the non-zero
  sham floor disclosed. CJT/J-space Phase B unlocked.
- **Track B pilots:** corpora v1/v2 failed authoring yield (World-label leak `18–56%`; cohort
  confound avoided by full regeneration); realization-grammar pilot v1
  `VOID_APPARATUS_PROMPT_CONTAMINATION` (the prompt printed the forbidden word); S2 silent
  enforcement + E-arm universal target-blind instruction → `0.0094`; confirmatory `R1–R6` with
  full byte-replayability logging — low leakage replicates cross-family (`claude-haiku 0.0063`).
- **Attribution chain, one variable at a time:** thin judge key `joint 0.2222` → full canon on
  identical texts `0.6181` (`S3-0`, `536f6a89`) → motive repair with the rejected close rival
  `0.7569`, the campaign's first joint pass; `P74` (generative vs companionship)
  `0.5833 → 0.9375`. **All 13 mechanical rows green**, including `R6` arms regenerated under the
  repaired prompt (`0.0125` / `0.0187`).
- **v3 budget** from the frozen rule (worst-cell Wilson LCB `0.6990`, rule-of-three family
  rejection, sibling dependence): `13` plans/cell → `P(all 28 cells reach 8 families) = 0.9987`,
  `2,912` candidates.
- **Gate 2 remains OPEN at `0.38`.** Next: `TKS_672_V3` lock under the motive-repaired
  instrument, then the small-model readout ladder on the frozen corpus under
  `GATE_2_SUCCESSOR_CLOSURE_CONTRACT` — final equivalence decision is the owner's.
