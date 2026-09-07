# Condition-skill v9 provider — re-audit (Lane B, second pass)

- Schema: `cas-meta2-condition-skill-v9-provider-audit/1`
- Recorded UTC: `2026-09-07T22:22:05Z`
- Status: `ADVISORY_ONLY`
- Auditor: Lane B (independent, read-only). This re-audit is a follow-up to
  `records/condition_skill_v9_001/audit_001/`, which ran while the provider
  adapter did not exist. The provider has since landed (commit `f87b7d75`,
  "Incorporate two-phase reservation refinement from Lane A") and is committed.
- Nothing outside `records/condition_skill_v9_001/audit_002/` was created,
  modified, moved, or deleted. Nothing was committed or pushed. No neural work,
  no AWS/provider call, no reservation, and no `pytest` was run.

## Scope reviewed (this pass)

- `aws/condition_skill_v9_provider.py` (the landed provider; 812 lines)
- `aws/condition_skill_v9_launch.py` (interaction surface; 300 lines)
- `aws/budget.py` (canonical ledger helper, under lock)
- `aws/condition_skill_v9_resource_plan.py` (frozen constants)
- `cas_meta2/condition_skill_v9/train.py` (only `PROVIDER_ATTESTATION_KEYS`
  lines 193–199 and `adjudicate` lines 205–319)
- `records/condition_skill_v9_001/preregistration_v9_001.md`
- `tests/test_condition_skill_v9_provider.py`, `tests/test_condition_skill_v9_launch.py`

## Severity summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| MAJOR | 1 |
| MINOR | 2 |
| INFO | 5 |

Re-check verdicts: **F1 resolved (provider implements the contract), F2
resolved (preflight now returns `visible_gpu_count` and the launcher now
checks it), F3 resolved (calls contract implemented; ledger transition remains
the authoritative guard), F5 still open (attestation key set still omits
`instance_count`).**

---

## F1 (re-check) — `reserve()` appends the ledger FIRST under the lock, records AWS-side only after, no refund/retry, never delegates → RESOLVED (sound)

- **Severity:** INFO (no defect; confirmation of the previously-absent contract).
- **Evidence:** `aws/condition_skill_v9_provider.py:309-334` (`reserve()`); Phase 1
  is the single statement at lines 329–330 — `receipt = self.budget.reserve_budget(...)`
  — which runs *before* `self._reserved = True` (line 331) and *before* Phase 2
  (line 334, `_record_aws_side_reservation`). The canonical helper
  `aws/budget.py:272-284` performs the append inside `with exclusive(ledger_path)`
  (lock at line 275) and refuses a duplicate job id under that lock (line 277).
  Phase 2 (`_record_aws_side_reservation`, lines 356–379) is reached only after
  `reserve_budget` returned; it never raises (catch-all `except Exception` at
  line 377), never refunds, and never retries — it returns a status dict
  (`"RECORDED"` / `"FAILED"` / `"NOT_RECORDED"`). The provider imports only
  `budget`, `condition_skill_v9_resource_plan`, `condition_skill_v9_launch`,
  and `condition_skill_v9_remote` (lines 46–49); there is no import of
  `launch_child_qualification_v8` or any other reservation owner (asserted by
  AST test `tests/test_condition_skill_v9_provider.py:527-535`), and
  `reservation_plan()` delegates only to `self.launch_module.reservation_plan()`
  (lines 221–223), i.e. the v9 plan, not another lifecycle.
- **Conclusion:** The two failure modes audit_001 feared (reserve-before-append,
  and delegation to a second reservation owner) are both absent in the real
  provider. F1 is closed.

## F2 (re-check) — `preflight()` returns every fact `validate_preflight()` requires, including `visible_gpu_count` → RESOLVED

- **Severity:** INFO (confirmation).
- **Evidence:** `aws/condition_skill_v9_provider.py:299-304` returns all ten keys:
  `account`, `region`, `ami`, `instance_type`, `instance_count` (hardcoded `1`),
  `gpu_name_contains`, `visible_gpu_count`, `t4_rejected`, `rate_ceiling_usd`,
  `conflicting_resources`. `visible_gpu_count` is computed from the AMI's GPU
  info at lines 250–258 and asserted `== frozen["visible_gpu_count"]` at line 257.
  The current launcher `aws/condition_skill_v9_launch.py:181-202` now *checks*
  `visible_gpu_count == 1` (line 197) — this line did **not** exist in the
  audit_001 snapshot (audit_001 F2 quoted it as absent). The frozen fact set
  matches `tests/test_condition_skill_v9_provider.py:420-431`
  (`test_preflight_returns_frozen_facts`).
- **Residual note (by design, no defect):** `torch_version`, `cuda_version`,
  `actual_cuda_operation` are still not in preflight, and cannot be — they are
  worker-side runtime facts. The launcher documents this explicitly at
  `condition_skill_v9_launch.py:182-188`, and they are enforced post-run by the
  adjudicator's attestation keys, not by preflight. F2's remaining concern is
  therefore closed as by-design.

## F3 (re-check) — `provider.calls` contract is implemented by the real provider; ledger transition remains authoritative → RESOLVED (residual advisory note)

- **Severity:** INFO (confirmation + residual advisory note).
- **Evidence:** `self.calls` is initialized at `condition_skill_v9_provider.py:214`
  and appended at the head of `preflight` (229), `reserve` (323), `launch` (505),
  `wait` (633), `collect` (667), `cleanup` (690). The launcher sequence
  `condition_skill_v9_launch.py:227-230` is: `preflight()` → `provider.calls.clear()`
  (228) → `provider.reserve(...)` (229) → `require(provider.calls == ["reserve"], ...)`
  (230). Because `reserve()` appends `"reserve"` as its first statement (line 323),
  the assertion holds with the real provider. The authoritative guard is unchanged
  and still stronger than the `calls` list: `ledger_after = read_ledger(...)` and
  `validate_reserved_transition(...)` at lines 231–232, which the launcher's own
  docstring labels authoritative (lines 208–210).
- **Residual note (same as audit_001 F3, still advisory):** `calls.clear()` still
  erases any side-effect call record made during `preflight()`, so the
  `== ["reserve"]` check is not a correctness guarantee — the ledger-transition
  check is. Consider dropping the `calls` assertion or documenting it as
  advisory-only in the provider interface; neither is required for safety.

## F5 (re-check) — attestation key set still omits `instance_count` → STILL OPEN

- **Severity:** MINOR.
- **Evidence:** `cas_meta2/condition_skill_v9/train.py:193-199`
  (`PROVIDER_ATTESTATION_KEYS` = `account`, `region`, `ami`, `instance_type`,
  `gpu_name_contains`, `t4_rejected`, `visible_gpu_count`, `torch_version`,
  `cuda_version`, `actual_cuda_operation`, `automatic_retries`,
  `reservation_usd` — **no `instance_count`**). The adjudicator compares only
  these keys: `train.py:299-301` builds `mismatches` from
  `PROVIDER_ATTESTATION_KEYS.items()` and checks `provider_attestation.get(key)
  != expected`; the `job` pattern is checked separately at lines 302–305.
- **Exact consequences for re-adjudication:**
  1. A **missing** fixed key *is* caught (`.get(key)` → `None` → mismatch).
  2. `instance_count` is **not** a fixed key, so an attestation that omits it,
     or carries `instance_count: 99`, is **accepted** as long as the 12 fixed
     keys match and the job label is well-formed.
  3. Therefore the single-instance bound is enforced **only** at launch time —
     by `validate_preflight` (`condition_skill_v9_launch.py:195`,
     `instance_count == 1`) and by `run_instances` `MinCount=1, MaxCount=1,
     ClientToken=self.job` (`condition_skill_v9_provider.py:570-575`) — and
     **not** by the post-run re-adjudication. Note `preflight`'s
     `instance_count: 1` (line 301) is a plan literal, not an AWS-measured fact;
     the only measured single-instance guarantee is the `run_instances` bound.
  4. `visible_gpu_count == 1` *is* enforced (key present), but that constrains
     GPUs-per-instance, not the number of EC2 instances.
- **Three owner options (from `preregistration_v9_001.md:277-284`, §8.2):**
  (a) **Amend now** — add `"instance_count": 1` to `PROVIDER_ATTESTATION_KEYS`
  (a new owner-approved pre-run amendment); (b) **Run as frozen** — proceed with
  the current key set, `instance_count` enforced by launcher preflight only;
  (c) **Wait** — hold the run until the question is ruled. This remains an open
  gate, not a resolved item.
- **Suggestion:** Same as audit_001 — if the owner chooses option (a), add
  `"instance_count": 1` to `PROVIDER_ATTESTATION_KEYS` and the preregistration
  attestation table; otherwise record the owner's ruling so re-adjudication's
  single-instance gap is documented as accepted.

---

## N1 (new) — `cleanup()` never deletes `results/*`, so `delete_bucket` fails on a non-empty bucket and every successful run ends with `CLEANUP_INCOMPLETE_BLOCKS_RESULT`

- **Severity:** MAJOR.
- **Evidence:** `aws/condition_skill_v9_provider.py:724-741` — the
  `delete_objects` call (lines 727–731) deletes only `input/source.zip`,
  `input/remote.py`, `input/permit.json`, `reservation/reservation_receipt.json`,
  and `reservation/ledger_snapshot.json`. It does **not** delete
  `results/complete.json` or `results/artifacts.zip`, both of which exist after a
  real run: the remote driver writes `results/complete.json`
  (`condition_skill_v9_provider.py:450-453`) and the worker writes
  `results/artifacts.zip` (read back by `collect()` at lines 678/681). The next
  step, `s3.delete_bucket(Bucket=bucket)` (line 737), fails on a non-empty bucket
  (`BucketNotEmpty`), is caught (line 739), appends
  `"BUCKET_DELETION_FAILED"` (line 740), and sets `status["bucket_deleted"] =
  False` (line 741). `complete` therefore becomes `False` (lines 777–778), and the
  launcher's final guard `require(cleanup.get("complete") is True,
  "CLEANUP_INCOMPLETE_BLOCKS_RESULT")` (`condition_skill_v9_launch.py:260`) raises,
  so no `result.json` receipt is written even after a fully successful run.
- **Why the tests miss it:** `FakeS3.delete_bucket` (`tests/test_condition_skill_v9_provider.py:227-229`)
  always returns `{}` and never simulates `BucketNotEmpty`, so
  `test_full_call_sequence_and_shapes` asserts `cleaned["complete"] is True`
  against a fake that cannot fail this way.
- **Consequence:** The paid `$4.00` reservation is already committed (no refund),
  so this is fail-closed (no false PASS), but it blocks the run from producing a
  usable receipt until fixed. A real paid run would spend the reservation and
  still abort at the cleanup gate.
- **Suggestion:** Add `results/complete.json` and `results/artifacts.zip` (and any
  other allowlisted `results/*` keys) to the `delete_objects` list, and make the
  fake `delete_bucket` fail when `self.objects` is non-empty so the test reflects
  real S3 behavior.

## N2 (new) — `_ensure_bucket` memoizes a half-hardened bucket

- **Severity:** MINOR.
- **Evidence:** `aws/condition_skill_v9_provider.py:339-354` — `_ensure_bucket`
  sets `self._resources["bucket"] = bucket` at line 347, immediately after
  `create_bucket` succeeds but **before** `put_bucket_tagging`,
  `put_public_access_block`, and `put_bucket_encryption` (lines 348–353). If any
  of those three hardening steps raises, `_record_aws_side_reservation` swallows
  it (line 377) and returns `"FAILED"`, but the bucket name is already memoized.
  A later `_ensure_bucket` call (e.g. from `launch()`, line 521) hits the early
  return `if self._resources.get("bucket") == bucket` (line 343) and skips the
  unfinished tagging / public-access-block / encryption. The bucket is therefore
  left without the `cas_meta_job` tag and possibly without SSE-AES256 or the
  explicit public-access block, and never retried.
- **Suggestion:** Only memoize after all hardening steps succeed, or track a
  separate `hardened` flag; alternatively make `_ensure_bucket` idempotent against
  `BucketAlreadyOwnedByYou`/`BucketAlreadyExists` and always (re-)apply the
  hardening on first observed success.

## N3 (new) — AMI `OwnerId` is a hardcoded magic value, not a frozen-plan constant

- **Severity:** INFO.
- **Evidence:** `aws/condition_skill_v9_provider.py:239-243` hardcodes
  `OwnerId == "898082745236"` in preflight; the same value appears in the test
  fixture `tests/test_condition_skill_v9_provider.py:81`. It is not present in
  `aws/condition_skill_v9_resource_plan.py` `RESOURCE_PLAN` nor in the
  preregistration resource-plan table.
- **Consequence:** Cosmetic drift risk only — if the frozen AMI were ever
  re-derived from a different owner, preflight would fail closed. No safety
  impact.
- **Suggestion:** Promote the AMI owner to a named constant in
  `condition_skill_v9_resource_plan.py` (e.g. `"ami_owner_id"`) and reference it
  from both preflight and the test, so the frozen identity is single-sourced.

## N4 (new) — Phase-2 AWS-side reservation failure does not block the launch (by design)

- **Severity:** INFO (not a defect; recorded for the record).
- **Evidence:** `reserve()` returns
  `{**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}`
  (`condition_skill_v9_provider.py:334`). A Phase-2 failure is reported as
  `aws_side_reservation.status == "FAILED"` and does **not** stop `execute()`
  from proceeding to `provider.launch(...)` (`condition_skill_v9_launch.py:241`),
  because the authoritative ledger append already succeeded and `validate_reserved_transition`
  (lines 231–232) passes on the ledger alone.
- **Consequence:** The S3 receipt object (`reservation/reservation_receipt.json`)
  and the ledger snapshot are best-effort evidence; the ledger file itself remains
  the authoritative spend record. This matches the module docstring
  (`condition_skill_v9_provider.py:10-18`) and preregistration gate 4. No change
  required; recorded so the "AWS-side reservation record" is not mistaken for the
  authoritative reservation.

---

## Consistency check (check 6)

All frozen constants agree across provider, resource plan, preregistration,
adjudicator, and budget helper. No drift found.

| Constant | Provider | Resource plan | Preregistration | train.py attestation | budget.py |
|---|---|---|---|---|---|
| account | `frozen["account"]` (preflight 235) | `807562639912` | `807562639912` | `807562639912` | `807562639912` (validate_plan 101) |
| region | `self.region = plan[...]["region"]` (208) | `us-west-2` | `us-west-2` | `us-west-2` | `us-west-2` (101) |
| ami | `frozen["ami"]` (239) | `ami-0fbbd0facbc9e3cff` | `ami-0fbbd0facbc9e3cff` | `ami-0fbbd0facbc9e3cff` | — |
| instance_type | `frozen["instance_type"]` (245) | `g7.2xlarge` | one `g7.2xlarge` | `g7.2xlarge` | regex `g7e?` family (100) |
| GPU string | `gpu_name_contains` (255) | `RTX PRO 4500` | `RTX PRO 4500` | `RTX PRO 4500` | — |
| torch / CUDA | not in preflight (by design) | `2.11.0+cu128` / `12.8` | `2.11.0+cu128` / `12.8` | `2.11.0+cu128` / `12.8` | — |
| reservation | `plan.RESOURCE_PLAN["reservation_usd"]` (325) | `"4.00"` | `$4.00` | `"4.00"` | validated against bound (106) |
| zero retries | `ClientToken`, `RetryPolicy.MaximumRetryAttempts=0` (572, 600–601) | `automatic_retries: 0` | `0` | `0` | `AUTOMATIC_RETRIES_FORBIDDEN` (102) |

Notes: `instance_count: 1` is present in the plan (line 24) and enforced in
preflight (launch.py:195) and in `run_instances` (provider.py:572), but is the
one value still absent from the attestation key set — see F5. The plan's frozen
budget snapshot (`campaign_ledger_revision: 16`, `98.00`/`302.00`) remains a
pre-run snapshot and will be stale after the run (unchanged from audit_001 F9;
informational only).

## Drift observed in other lanes' files (while this pass worked)

All audited files are committed clean (`git status --short` empty for them), so
the drift below is committed change since the audit_001 snapshot, not a dirty
working tree.

1. **`aws/condition_skill_v9_launch.py` changed since audit_001.** Its
   `validate_preflight` now checks `visible_gpu_count == 1` (line 197) — audit_001
   F2 listed `visible_gpu_count` as *not* checked — and `execute()` now
   cross-checks `owner_approval_record_sha256` against the real
   `OWNER_PHASE_APPROVAL.json` bytes (lines 214–215) — audit_001 F4 reported this
   as never cross-checked. Both of audit_001's F2 and F4 suggestions have been
   implemented. Last commit touching this file: `c5522f45` ("Merge provider lane,
   audit fixes and reproduction tool").
2. **`aws/condition_skill_v9_provider.py` and `tests/test_condition_skill_v9_provider.py`
   are now present** (they did not exist at audit_001). Provider last commit:
   `f87b7d75` ("Incorporate two-phase reservation refinement from Lane A").
3. No concurrent modification was observed during this pass: files were read
   exactly once each and the working tree for the audited paths stayed clean.

## Confirmed sound (no defect found)

1. **Two-phase reservation order (F1):** append-then-AWS-side, under
   `budget.exclusive`, no refund, no retry, no delegation.
2. **Exactly-once is double-barreled:** provider in-process `self._reserved`
   guard (provider.py:324) plus `budget.reserve_budget` job-in-ledger refusal
   (budget.py:277) plus launcher job-in-ledger pre-check (launch.py:224–226).
3. **Permit identity validation:** `_validate_permit` (provider.py:384–399)
   re-checks job/source/archive/manifest/dataset, the reservation's job + status,
   the frozen `resource_plan`, and re-runs `validate_preflight`; it relies on the
   launcher's stronger `validate_reserved_transition` for the deep ledger binding,
   which is appropriate.
4. **No false provider-proof claim:** the launch receipt carries an
   `identity_note` (provider.py:613–615) explicitly stating in-guest identity is
   not independently proven by the provider.

## Methodology / non-execution notes

- Read-only: every file above was read with the `read` tool; no source file was
  modified. Only `records/condition_skill_v9_001/audit_002/` was written (this
  file and `audit_receipt.json`).
- `pytest` was deliberately not run (per task instruction); the integrator owns
  the guarded capture. Findings N1 and N2 rest on static tracing, not execution.
- No AWS/provider call, no reservation, no commit, no push.
