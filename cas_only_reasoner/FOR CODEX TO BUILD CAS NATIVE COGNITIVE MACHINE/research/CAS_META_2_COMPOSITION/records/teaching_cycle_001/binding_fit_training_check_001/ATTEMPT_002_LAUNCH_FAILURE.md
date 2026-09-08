# Binding-fit training check — launch attempt 002 failed at RunInstances (recorded negative)

Status: AWS_BINDING_FIT_FAILED (launch stage, after a successful reservation).
The one owner-authorized `$4.00` reservation for this check is consumed
(`RESERVED_NO_AUTOMATIC_REFUND`); this job is never re-run and nothing is
refunded. A new job would need a new owner authorization.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-binding-20260908191109-dcf939ab` |
| request sha256 | `cdcfcfb18d21f3b3351dc6000ad474cfafeaa48e15380e47429ff097bff59dc6` |
| authority sha256 | `f85529c7d10fc3d707af0b70242797148d3100eed8601f0c8ad21bb0e9e596b9` |
| source_sha (freeze commit) | `31e787923390cfdfc83d2326b48e606da0fa71a1` |
| archive_sha256 | `ddf39e5ea481c74b7f14ff866969dabb814ef83fa288e657af93d5b3520e55e9` |
| manifest_sha256 | `bfb6379457ce699e43e8bca1c51357e743169ae42cfd26d328717893b2e6a94f` |
| reservation | created, `4.00` USD, ledger revision 21 → 22 (`total_reserved_usd` 134.00 → 138.00, `remaining_unreserved_usd` 266.00 → 262.00) |
| instance | never launched (RunInstances refused) |

Evidence directory:
`records/teaching_cycle_001/binding_fit_training_check_001/receipt_cas-meta2-teaching-binding-20260908191109-dcf939ab/`
(`intent.json`, `preflight.json`, `reservation.json`, `provider_0001..0023.json`,
`failure.json`, `result.json`, `source.zip`).

## What succeeded

- Preflight: all frozen facts passed, including the AWS Price List call — this
  attempt is the live confirmation that the attempt-001 fix (pricing client
  built in `us-east-1`) works against real AWS.
- Reservation: exactly one `$4.00` append through `aws.budget.reserve_budget`.
- S3: bucket created and tagged, `input/source.zip` and `input/config.json`
  uploaded.
- IAM: worker role created, inline policy `job-only` attached, instance profile
  created, role attached to the profile (`add_role_to_instance_profile` returned
  success, request id `977c34f7-…`).
- EC2: security group created with outbound-TCP-443-only egress.

## What failed

`failure.json` (verbatim):

```json
{"exception":"An error occurred (InvalidParameterValue) when calling the RunInstances operation: Value (arn:aws:iam::807562639912:instance-profile/cas-meta2-teaching-binding-20260908191109-dcf939ab-worker) for parameter iamInstanceProfile.arn is invalid. Invalid IAM Instance Profile ARN","exception_type":"ClientError"}
```

Root cause: IAM is eventually consistent. The launcher called
`RunInstances` immediately after `add_role_to_instance_profile`, so EC2's
validator could not yet resolve the just-created instance profile ARN. There
was no bounded verification wait between the attach and the launch attempt.

Cleanup additionally recorded two `DeleteConflict` failures (role and instance
profile could not be deleted) because the cleanup order lacked the mandatory
detach step (`remove_role_from_instance_profile`) and the inline-policy removal
(`delete_role_policy job-only`) before deletion. The bucket, the security
group, and the (absent) schedule were cleaned successfully.

## Live-resource remediation (performed and verified)

| Step | Result |
|---|---|
| `remove_role_from_instance_profile` (worker) | detached |
| `delete_instance_profile` (worker) | deleted |
| `delete_role_policy` (worker, `job-only`) | deleted |
| `delete_role` (worker) | deleted |
| `get_role` / `get_instance_profile` probe | `NoSuchEntity` / `NoSuchEntity` — confirmed absent |

## Adapter fixes (committed with this record)

1. `_await_instance_profile` — bounded, verified wait (defaults: 120 s timeout,
   2 s poll, 15 s settle after visibility) between
   `add_role_to_instance_profile` and the single `RunInstances` attempt. Every
   poll is recorded as provider evidence. This is a verification wait, not a
   retry of `RunInstances`.
2. Cleanup ordering — detach the role from the instance profile and drop the
   inline `job-only` policy before deleting the role or the profile
   (already-absent tolerated at each step).
3. Three new tests (launcher suite is now 38): cleanup detach ordering,
   profile-visibility wait, profile-visibility timeout.

## Policy status

- Zero automatic retries: this job id is closed and must never be re-executed.
- The `$4.00` reservation stands (no refund, no re-reservation for this job).
- The frozen budget (`48` optimizer steps, `600.0` wall seconds,
  `learning_rate 0.003`, `$4.00`) and all source identities are unchanged by
  the adapter fix (the launcher is not a package member).
- A corrected run — new job id, new request/authority, new `$4.00` reservation —
  requires a new owner authorization. The standing authorization bound a single
  reservation, which is now consumed.
