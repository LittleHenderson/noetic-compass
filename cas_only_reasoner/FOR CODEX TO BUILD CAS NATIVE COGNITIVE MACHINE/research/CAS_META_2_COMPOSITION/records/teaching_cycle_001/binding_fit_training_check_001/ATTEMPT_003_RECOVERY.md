# Binding-fit training check — attempt 003: worker failed, original inner error not preserved (recorded negative)

Status: AWS_BINDING_FIT_FAILED. The launch lifecycle worked end to end; the
training worker itself failed. No optimizer update completed, no checkpoint
exists, and no training-fit measurement was produced. The one owner-authorized
`$4.00` reservation for this job is consumed (`RESERVED_NO_AUTOMATIC_REFUND`);
this job is never re-run and nothing is refunded.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-binding-20260908203112-fb18899f` |
| request sha256 | `4cf78769276cc4b2035957af7f230f1bc03c3a4b24cb826a33edf23131a53957` |
| authority sha256 | `507aab19d2fb44356def26fe1ce5cb213bb4c1a4d437fe72fd19f0956f950eba` |
| owner record sha256 | `09032ecc684f9eb734e757b05d09e9467dcd535ea3cf77caec47d2d5ee475deb` (`OWNER_AUTHORIZATION_003.json`) |
| source_sha (freeze commit) | `31e787923390cfdfc83d2326b48e606da0fa71a1` |
| archive_sha256 | `ddf39e5ea481c74b7f14ff866969dabb814ef83fa288e657af93d5b3520e55e9` |
| manifest_sha256 | `bfb6379457ce699e43e8bca1c51357e743169ae42cfd26d328717893b2e6a94f` |
| reservation | created, `4.00` USD, ledger revision 22 → 23 (`total_reserved_usd` 138.00 → 142.00, `remaining_unreserved_usd` 262.00 → 258.00) |

Evidence directory:
`records/teaching_cycle_001/binding_fit_training_check_001/receipt_cas-meta2-teaching-binding-20260908203112-fb18899f/`
(`intent.json`, `preflight.json`, `reservation.json`, `launch.json`,
`provider_0001..0026.json`, `result.json` + `result.json.sha256` = the
collected worker report, `source.zip`).

## What succeeded

- Preflight: all frozen facts passed (pricing client in `us-east-1`).
- Reservation: exactly one `$4.00` append through `aws.budget.reserve_budget`.
- Launch: single `run_instances` attempt succeeded — instance
  `i-0dd72858329273a9b`, `ClientToken` = job, IMDSv2 `HttpTokens: required`.
  The bounded IAM readiness check worked: the instance profile was visible on
  the first verification poll, so no propagation race occurred.
- Worker bootstrap: the failure report shows the failing command was the inner
  runner under the task venv (`/opt/cas-binding-fit/package/venv/bin/python -B
  /opt/cas-binding-fit/package/_inner_runner.py`), which means the venv, the
  `torch==2.11.0` (cu128) install, the two frozen wheels, and
  `requirements-gpu.txt` all completed before the run stage.

## What failed

The collected worker report (verbatim structure):

```json
{
  "failure": {
    "message": "Command '[.../venv/bin/python -B .../_inner_runner.py ...]' returned non-zero exit status 1.",
    "type": "CalledProcessError"
  },
  "run_id": "cas-meta2-teaching-binding-20260908203112-fb18899f",
  "schema": "cas-teaching-binding-fit-training/1",
  "status": "REMOTE_WORKER_FAILED"
}
```

The inner runner (import of `cas_meta2.binding_fit_training.mode` and/or
`mode.launch`) exited 1. **The original inner error was NOT preserved**: the
worker ran the inner runner with inherited output, so the traceback went to a
bootstrap log that was destroyed with the instance (EBS
`delete_on_termination`). This violates the owner's requirement "preserve the
original error if any stage fails" and is fixed below.

Hypothesis (NOT a claim): `mode.launch` calls `gpu_adapter._cuda()`, which
fails closed with `TEACHING_GPU:CUDA_REQUIRED_NO_CPU_FALLBACK` when
`torch.cuda.is_available()` is false. A driver/CUDA mismatch on the instance is
the most plausible cause, but it is unconfirmed because the error text was
lost. Any other exception inside `mode.launch` would have produced the same
observed report.

A second, launcher-side defect also surfaced at the very end:
`execute()`'s final lifecycle write (`result.json`) collided with
`collect()`'s evidence write of the worker report under the same name
(`FileExistsError`), so the lifecycle summary for this run was never written.
The collected worker report, the reservation, the launch record, and all 26
provider events are preserved.

## Cleanup outcome and remediation

Cleanup ran before the lifecycle-write crash. Instance termination was
requested; roles/profiles were removed (the detach fix from attempt 002
worked); the bucket was deleted. The security group deletion raced the
shutdown and failed with `DependencyViolation`, leaving one group behind.

Remediated manually and verified:

| Item | Result |
|---|---|
| instance `i-0dd72858329273a9b` | confirmed `terminated` |
| security group `sg-045d8974319381fac` | deleted; 0 remaining |
| bucket (job name) | `404` absent |
| roles + instance profiles (worker/timer) | all `NoSuchEntity` absent |

## Launcher fixes (committed with this record)

1. `collect()` now writes `training_result.json` (+ sha256 sidecar) into the
   evidence directory, so the lifecycle `result.json` can never collide.
2. The rendered worker now runs the inner runner with
   `capture_output=True` and, on non-zero exit, reports
   `INNER_RUNNER_EXIT_<code>` plus the last 1800 characters of the inner
   stderr/stdout — the original error is preserved in `results/result.json`.
   **This changes the rendered worker script, so the frozen package identity
   changes: any future authorized run needs a new package build (new
   archive/manifest/request/authority/owner record).**
3. Cleanup now waits (bounded, 300 s) for instances to actually terminate
   before deleting the security group, preventing the `DependencyViolation`
   leftover. Three new tests; launcher suite is now 43.

## Deliverables requested by the owner

| Deliverable | Value |
|---|---|
| before/after training loss, CAS | NOT AVAILABLE — no optimizer update completed |
| before/after training loss, generic | NOT AVAILABLE — no optimizer update completed |
| binding accuracy, CAS | NOT AVAILABLE |
| binding accuracy, generic | NOT AVAILABLE |
| actual completed optimizer updates | 0 |
| checkpoint identities | none produced |
| execution outcome | launch + bootstrap OK; worker failed (`REMOTE_WORKER_FAILED`) |
| cleanup outcome | complete after manual SG remediation (see above) |
| original error | not preserved by the run (worker defect, now fixed); see hypothesis above |

Claims: `training_fit_claimed: false`, `composition_claimed: false`,
`final_targets_read: false`. The frozen negatives (`0/72` learned composition)
are untouched.

## Policy status

- Zero automatic retries: this job id is closed.
- The `$4.00` reservation stands; no refund, no re-reservation for this job.
- Any further run — with the corrected worker — requires the owner to authorize
  a new job, a new package build (renderer changed), and a new `$4.00`
  reservation.
