# Condition-skill v9 launch adapter — independent read-only audit (Lane B)

- Schema: `cas-meta2-condition-skill-v9-adapter-audit/1`
- Recorded UTC: `2026-09-07T20:25:58Z`
- Status: `ADVISORY_ONLY`
- Auditor: Lane B (independent, read-only). No file outside `records/condition_skill_v9_001/audit_001/` was created, modified, moved, or deleted. Nothing was committed or pushed. No neural work, AWS call, or reservation was made. `pytest` was NOT run (the integrator owns the guarded capture).

## Scope reviewed

- `aws/condition_skill_v9_resource_plan.py`
- `aws/condition_skill_v9_package.py`
- `aws/condition_skill_v9_remote.py`
- `aws/condition_skill_v9_launch.py`
- `aws/budget.py` (usage inside the launch modules)
- `cas_meta2/condition_skill_v9/train.py` (pre-seal target boundary and `adjudicate` only — frozen learning design not reopened)
- `cas_meta2/condition_skill_v9/bundle.py` (traced for the sealed-target file-access sequence)
- `tools/check_condition_skill_v9.py`
- `tools/verify_condition_skill_v9_publication_packet.py`
- Tests: `tests/test_condition_skill_v9_launch.py`, `tests/test_condition_skill_v9_remote.py`, `tests/test_condition_skill_v9_packet_verifier.py`, `tests/test_condition_skill_v9_resource_plan.py`, `tests/test_condition_skill_v9_train_boundary.py`
- Reference: `AGENT_LANE_BOARD.md`, `PROTOCOL.md`, `INTEGRATION_CORRECTION_2026-09-07.md`, `OWNER_PHASE_APPROVAL.json`, `OWNER_METRIC_AMENDMENT.json`

Note on Lane A: `aws/condition_skill_v9_provider.py` and `tests/test_condition_skill_v9_provider.py` do **not** exist yet. The provider adapter is in-flight and was treated as absent; findings that depend on the provider are marked as such.

## Findings by severity

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| MAJOR | 1 |
| MINOR | 6 |
| INFO | 7 |

---

## MAJOR

### F1 — Reservation exactly-once is verification-only; the real reservation is performed by the (absent) provider
- **Check:** 2 (reservation exactly-once).
- **Evidence:** `aws/condition_skill_v9_launch.py:206-216` (read ledger → preflight → `provider.reserve(RESERVATION_USD)` → `provider.calls == ["reserve"]` → re-read ledger → `validate_reserved_transition`); `aws/condition_skill_v9_launch.py:143-177` (transition check: exactly one new entry, matching job/source/archive/plan); `aws/budget.py:272-284` (`reserve_budget` refuses duplicate job under the lock); `INTEGRATION_CORRECTION_2026-09-07.md:76-80` ("`launch_child_qualification_v8._run_authorized()` already owns its reservation. It must not be called behind the injectable v9 launcher's `provider.reserve()` path, which would reserve twice.").
- **Analysis:** The launcher itself cannot double-reserve: it checks `JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY` before reserving (line 208-210) and requires the ledger to advance by exactly one matching append-only entry afterward (lines 146-150). The second-attempt refusal is sound (`tests/test_condition_skill_v9_launch.py:284-291`, and the `budget.reserve_budget` lock at `budget.py:277`). **However**, the launcher only *verifies* the transition — it does not perform the reservation. The reservation is performed by `provider.reserve()` (the in-flight Lane A module). Two failure modes remain outside the launcher's control:
  1. A provider that creates an AWS-side reservation/instance *before or without* appending the ledger entry would be detected (`RESERVATION_REVISION_MISMATCH`), but only **after** the spend; the `no_automatic_refund` budget policy (`aws/budget.py:24`, `STATUS = "RESERVED_NO_AUTOMATIC_REFUND"`) means that spend is then permanently unrecorded.
  2. A provider that double-reserves by internally calling `launch_child_qualification_v8._run_authorized()` (which owns its own reservation) would produce a second AWS-side reservation the ledger check cannot see if the second reservation targets a different ledger.
- **Suggestion (integrator decision):** Before the paid run, pin the provider contract: `provider.reserve()` must be exactly `budget.reserve_budget(job, source_sha, archive_sha256, RESERVATION_USD, reservation_plan(), canonical_ledger)` and nothing else; it must not invoke `launch_child_qualification_v8._run_authorized()` or any other reservation path. Verify this by reading Lane A's provider once it lands. This finding is advisory-only because the provider does not exist yet.

---

## MINOR

### F2 — Launch preflight enforces a subset of the frozen provider identity
- **Check:** 5 (provider identity) and 6 (drift).
- **Evidence:** `aws/condition_skill_v9_launch.py:180-193` (`validate_preflight` checks account, region, ami, instance_type, instance_count, gpu_name_contains, t4_rejected, rate_ceiling_usd, conflicting_resources — but **not** `torch_version`, `cuda_version`, `visible_gpu_count`, or `actual_cuda_operation`); `aws/condition_skill_v9_resource_plan.py:27-29` (plan defines `visible_gpu_count`, `torch_version`, `cuda_version`); `cas_meta2/condition_skill_v9/train.py:193-199` (`PROVIDER_ATTESTATION_KEYS` includes all of them).
- **Analysis:** `visible_gpu_count == 1` is an AWS-visible fact knowable from the instance type before launch, yet it is not checked in preflight. `torch_version`/`cuda_version`/`actual_cuda_operation` are runtime facts, so their absence from preflight is partly by design — but the protocol's paid-run gate ("provider identity attested outside the trainer execution guard (IMDSv2, GPU name, torch/CUDA, one instance)") is therefore only fully satisfied **after** the run by re-adjudication, while the $4.00 is reserved **before** that identity is confirmed. The trainer's own runtime checks (`torch.cuda.is_available()`, `device_count()==1`, `"T4" not in gpu_name`, `train.py:386-390`) fail closed and mitigate this, but the reservation is already made.
- **Suggestion:** Add `visible_gpu_count` to `validate_preflight`, and make explicit (in the launch receipt) that torch/CUDA/actual-CUDA-operation identity is attested only by the outer post-run receipt + re-adjudication, not by preflight.

### F3 — `provider.calls` instrumentation is a test-hook contract in the production execution path
- **Check:** 2 and 5.
- **Evidence:** `aws/condition_skill_v9_launch.py:211-214` (`provider.calls.clear()` then `require(provider.calls == ["reserve"], "RESERVATION_MUST_BE_FIRST_AND_SINGLE")`).
- **Analysis:** The production `execute()` depends on the real provider self-reporting a mutable `calls` list. `clear()` erases any call record made during `preflight()`, so a provider whose `preflight()` has a side effect would have that side effect hidden from the `== ["reserve"]` check. The authoritative guard is the ledger transition (`validate_reserved_transition`), so this is not a correctness hole, but the `calls` protocol is fragile and untyped for the real adapter.
- **Suggestion:** Document the `calls`-list contract as part of the provider adapter interface, or drop the `calls == ["reserve"]` assertion in favor of relying solely on the ledger transition check (which is already stronger).

### F4 — Authority's `owner_approval_record_sha256` is never cross-checked against the owner record
- **Check:** 5 (is every launch-side claim attributable to an outer receipt) and 6 (drift).
- **Evidence:** `aws/condition_skill_v9_launch.py:73-77` (only `re.fullmatch(r"[a-f0-9]{64}", ...)` is checked); `tests/test_condition_skill_v9_launch.py:66` uses the placeholder `"d" * 64` and is accepted. No launch code reads or hashes `OWNER_PHASE_APPROVAL.json`.
- **Analysis:** The standing authority *claims* to bind the owner phase-approval record, but the launch module never verifies that `owner_approval_record_sha256` equals the SHA-256 of `OWNER_PHASE_APPROVAL.json`. The authority itself is hash-bound at invocation (`--authority-sha256`, `launch.py:265-266`), but its internal binding to the owner record is a self-assertion.
- **Suggestion:** Either verify `owner_approval_record_sha256` against the actual `OWNER_PHASE_APPROVAL.json` bytes at execute time, or remove the field and bind the owner record hash explicitly in the launch request path.

### F5 — Adjudicator's provider attestation omits `instance_count`
- **Check:** 6 (drift).
- **Evidence:** `cas_meta2/condition_skill_v9/train.py:193-199` (`PROVIDER_ATTESTATION_KEYS` has `instance_type`, `visible_gpu_count`, etc., but no `instance_count`); `PROTOCOL.md:149-153` ("one `g7.2xlarge`"); `aws/condition_skill_v9_resource_plan.py:24` (`instance_count: 1`).
- **Analysis:** The protocol PASS gate says "one g7.2xlarge". The launcher's preflight enforces `instance_count == 1`, but the re-adjudication attestation would accept an attestation carrying `instance_type: "g7.2xlarge"` with (or without) an `instance_count` of anything, because missing/extra keys are ignored (`adjudicate` only compares the fixed key set, `train.py:299-301`).
- **Suggestion:** Add `"instance_count": 1` to `PROVIDER_ATTESTATION_KEYS` (or otherwise require it in the attestation) so re-adjudication enforces the same single-instance bound the launcher preflight does.

### F6 — Publication-packet verifier does not enforce the LF-only invariant at verify time
- **Check:** 7.
- **Evidence:** `tools/verify_condition_skill_v9_publication_packet.py:172-173` (build rejects `b"\r" not in raw`), but `verify_packet` (lines 177-202) never checks CRLF. `json.loads` accepts CRLF whitespace, so a CRLF re-serialization of an otherwise exact packet would verify `PACKET_EXACT` with a **different** `packet_sha256` than the bound LF-only packet (`OWNER_PHASE_APPROVAL.json:18`, `publication_packet_sha256: c69f7158...`).
- **Suggestion:** In `verify_packet`, add `require(b"\r" not in packet_raw, "PACKET_CRLF_REJECTED")` (or document that LF-only is a build-time-only property and require the caller to compare the reported `packet_sha256` against the bound value).

### F7 — Trainer stdout/stderr logs have no write-side size bound
- **Check:** 4 (worker single-run semantics).
- **Evidence:** `aws/condition_skill_v9_remote.py:250-256` (stdout/stderr redirected to sibling files with no cap) and `309-326` (`collect_logs` reads only a `LOG_BYTES_MAX` = 1 MiB prefix).
- **Analysis:** A runaway trainer can write unbounded output to the log files before the 600 s wall-clock kill (`WORKER_SECONDS_MAX`, `remote.py:34`), potentially filling the 75 GiB EBS volume. Only a 1 MiB prefix is ever collected. This is bounded by the fixed deterministic trainer in practice, but it is not enforced.
- **Suggestion:** Add a write-side bound (e.g., a streaming wrapper that stops at `LOG_BYTES_MAX` or a fixed multiplier) or rely on and document the instance-level EBS + 600 s bound as the only log cap.

---

## INFO

### F8 — Private targets are extracted to worker disk before training and re-hashed pre-train (byte-integrity only; seal is sound)
- **Check:** 1. **File-access sequence traced:**
  1. Package build (host): `resolve_members` reads `test_instances.targets.json` / `test_direction_pair.targets.json` from Git objects and hashes them (`aws/condition_skill_v9_package.py:59-95`, `284-288`). Byte integrity only.
  2. Worker `orchestrate`: `inspect_archive` → `extract_archive` (writes private targets to `records/condition_skill_v9_001/dataset_001/*.targets.json`) → `verify_extracted_package` re-hashes every member, including private targets (`aws/condition_skill_v9_remote.py:336-341`). Byte integrity only.
  3. Trainer `run()`: reads only `train.json`/`validation.json` first (`cas_meta2/condition_skill_v9/train.py:350`); seals selection at line 624; reads `.public.json` and writes blind predictions (`628-640`); only then reads `.targets.json` (`641-643`) and cross-checks against `data.oracle(public)` (`648`). `read_partitions` hashes each requested partition immediately before parsing (`cas_meta2/condition_skill_v9/bundle.py:146-191`).
- **Conclusion:** No launcher/package/remote path reads private target bytes into the learner before the seal. The seal boundary itself lives in trainer code and is correctly ordered. Hashing by the package/worker is byte-integrity only, consistent with `PROTOCOL.md:102-103`. The private targets are physically present on the worker before training, so the seal is enforced purely by trainer-code discipline (which is sound).

### F9 — Frozen resource plan embeds a budget snapshot that will be stale after the run
- **Check:** 6.
- **Evidence:** `aws/condition_skill_v9_resource_plan.py:47-54` (`campaign_ledger_revision: 16`, `campaign_reserved_usd: "98.00"`, `campaign_unreserved_usd: "302.00"`). The plan is frozen into each reservation entry via `reservation_plan()` (`launch.py:116-125`, `condition_skill_v9: frozen`).
- **Analysis:** After the $4.00 reservation the live ledger becomes revision 17 / $102 reserved. The plan's frozen 16/98/302 values become stale, and they are also copied into the reservation entry's `plan["condition_skill_v9"]["budget"]`. They are informational (enforcement reads the live ledger via `validate_reservation_scope`, `launch.py:128-140`), so this is cosmetic, but it is easy to misread as a live state.
- **Suggestion:** Label the embedded budget snapshot explicitly as "as-of-pre-run" in the plan, or omit it from the plan output.

### F10 — Checker's hash set references an untracked, un-packaged tool
- **Check:** 3 and 7.
- **Evidence:** `tools/check_condition_skill_v9.py:20` lists `tools/check_condition_skill_v9_package_reproduction.py`; that file is untracked (`??` in `git status`) and is **not** in `condition_skill_v9_package.py` `EXPLICIT_FILES`.
- **Suggestion:** Reconcile: either package the reproduction tool or remove it from the checker's hashed-file set before the guarded capture.

### F11 — Trainer imports `cas_meta1` from source while `casformer`/`cas_cjt` come from wheels
- **Check:** 3 (wheels vs PYTHONPATH shadowing).
- **Evidence:** `cas_meta2/condition_skill_v9/train.py:369-373` (`sys.path.insert(0, str(meta1))` → `from cas_meta1.baseline import verify_baseline, verify_installed_wheels`); `aws/condition_skill_v9_remote.py:210-214` (PYTHONPATH = pilot dir only, all `PYTHON*` stripped, `PYTHONNOUSERSITE=1`).
- **Analysis:** `casformer`/`cas_cjt` source dirs are packaged as siblings of the pilot dir and are **not** on PYTHONPATH, so those imports resolve to the installed wheels (enforced further by the frozen `verify_installed_wheels`, which is outside this audit's scope). `cas_meta1` is imported from the frozen META-1 source directory by design. The "isolated venv" is therefore augmented by one intentional source dir at runtime.
- **Suggestion:** None required (by design); recorded so the wheel-shadowing claim is precise about the one intentional source import.

### F12 — Packet verifier allows a bare monorepo-root `CHANGELOG.md` outside the CNCM prefix
- **Check:** 7.
- **Evidence:** `tools/verify_condition_skill_v9_publication_packet.py:29` (`EXPLICITLY_ALLOWED_PATHS = ("CHANGELOG.md",)`).
- **Suggestion:** Confirm this is intended (it broadens the packet's allowed scope beyond the `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/` prefix).

### F13 — `git_is_ancestor` conflates a Git failure with "not an ancestor"
- **Check:** 7.
- **Evidence:** `tools/verify_condition_skill_v9_publication_packet.py:130-135` (catches `ValueError` from `_run_git` and returns `False`). A malformed commit hash fails `merge-base` and is reported as `SOURCE_COMMIT_NOT_ANCESTOR_OF_HEAD`.
- **Suggestion:** Distinguish "git command failed" (invalid commit/repo) from "verified non-ancestor" for clearer diagnostics.

### F14 — `verify_extracted_package` passes `imported_paths=()` (import-path guard unused)
- **Check:** 3.
- **Evidence:** `aws/condition_skill_v9_remote.py:153-160` (`verify_extracted(destination, manifest, imported_paths=())`).
- **Suggestion:** Either use the `imported_paths` guard to assert the pilot is the sole import root, or remove the dead parameter to avoid implying a check that is not performed.

---

## Confirmed sound (no defect found)

1. **Sealed-target boundary (check 1):** sound. Trainer reads train/validation → seals → public → blind predictions (hash-bound) → private targets, with per-partition hash pinning. See F8.
2. **Second-attempt refusal (check 2):** sound and double-barreled — launcher job-in-ledger check (`launch.py:208-210`) plus `budget.reserve_budget` under-lock duplicate refusal (`budget.py:277`).
3. **Package path/symlink/duplicate/size safety (check 3):** sound. `safe_name`, `checked_names` (casefold + file/dir collision), `no_links`, `file_metadata`/`read_file` (fstat dev/ino/nlink/size re-checks), `archive_members` (symlink/encrypted/non-regular rejection, size + expanded bounds), Git-object-only sourcing with the corrected `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/` prefix.
4. **Worker single-run semantics (check 4):** sound. Single `Popen`, `process_attempts: 1`, `automatic_retries: 0`, independent `taskkill /T /F` / `killpg(SIGKILL)` kill, failure receipts always written, allowlisted collection covering every trainer output name.
5. **No false provider-proof claim (check 5):** the remote receipt sets `provider_identity_proved: False` (`remote.py:368-370`) and the trainer's execution guard sets `provider_identity_proved_by_execution_guard: False` (`train.py:77-78`); the adapter does not claim provider proof it does not have.
6. **Plan/approval constant agreement (check 6):** all `RESOURCE_PLAN` values match `OWNER_PHASE_APPROVAL.json` (account/region/ami/instance/GPU/torch/CUDA/bounds/$4.00/seed/scope), and `train.py` SHA-256 `bfbd3989c2d8d42b322efcd67ecfc766af61846f2a759187518bc0ef16af486e` matches `OWNER_METRIC_AMENDMENT.json` `bound_state_after.trainer_sha256` (frozen trainer).
7. **Adjudicator gate coverage (check 6):** all protocol PASS gates (status, sealed, targets parsed, source pins, constant 0.25, oracle 1.0, joint > 0.25, per-bit > 0.5, trained-beats-untrained, control joint == 1.0, 2400 steps, provider attestation with well-formed job) are present in `adjudicate`.

## Methodology / non-execution notes

- Read-only: every file above was read with the `read` tool; no source file was modified. Only `records/condition_skill_v9_001/audit_001/` was written (this file and `audit_receipt.json`).
- `pytest` was deliberately not run; the integrator owns the guarded capture (`tools/check_condition_skill_v9.py`).
- The in-flight Lane A provider was treated as absent; F1 (and parts of F2/F3) therefore rest on the launcher contract and must be re-checked against the provider once it exists.
