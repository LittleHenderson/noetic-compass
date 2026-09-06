# Current AWS read-only readiness and price check

The existing default AWS profile reached account `807562639912` in `us-west-2`.
No resource was created, changed, reserved, started, or deleted.

## Result

- `g7.2xlarge`: one NVIDIA RTX PRO 4500, 32,768 MiB GPU memory, eight vCPUs.
- Current Linux shared On-Demand list price: `$2.52/hour`.
- Account G/VT On-Demand quota: eight vCPUs. No pending/running G/VT instances were returned.
- No active or stopped `cas_meta_job`-tagged instances were returned.
- Existing subnet `subnet-0eb3ca4bf5ca98f24` in `us-west-2c` is available, with public-IP mapping, working DNS settings, an active route to its attached internet gateway, and a permissive default network ACL.
- Amazon AMI `ami-0fbbd0facbc9e3cff` is available and lists G7 support. Its root volume is 75 gp3.
- G7 is offered in the selected zone. Neither this nor the quota proves spare GPU capacity or resource-creation permission.

The parent-declared ceilings produce a conservative known-resource estimate of
`$2.569242828761600000000000000` before tax. Charging the full `$1.00` ancillary
allowance instead gives `$3.52`, below the proposed `$4.00` reservation.

The ceilings include the entire one-hour instance lifetime, at most 1,800 worker
seconds, 75 gp3 at baseline performance, one public IPv4 address, 16 MiB of inputs,
256 MiB of results/downloads, eight days of storage costed for the seven-day
lifecycle, 2,000 S3 requests all conservatively costed at Tier1, and one Scheduler
invocation. See `readiness_summary.json` for every rate, equation, and assumption.
These limits must be enforced by the dedicated parent. They were not executed here.
Taxes, support allocation, and delayed provider shutdown are not established by
list-price reads; this is not an AWS-enforced account billing cap.

## Evidence

`01_*.json` through `31_*.json` retain exact service/method/filter arguments,
sanitized responses, request IDs, statuses, and times. No credential values or
signed request headers are stored. The main 27-query capture exited zero with an
empty stderr. Four not-found responses are expected previous-resource cleanup
observations, not failed access checks.

The initial S3-specific transfer query returned no product and remains preserved.
The supplemental `AWSDataTransfer` query found the current Oregon internet rate
of `$0.09/GB`. The Scheduler-specific product filter was also empty; the official
[AWS Scheduler pricing example](https://aws.amazon.com/eventbridge/pricing/)
supports the conservative `$0.000001` per-invocation ceiling. No free-tier discount
is counted.

The old V7 instance no longer returns a record. Its earlier provider-confirmed
termination at `2026-09-06T11:24:22+00:00` is separately bound to the existing
`cleanup_cost_check_001.json` hash. Do not describe the new empty response as a
fresh terminated-state observation. The old job's volumes, schedule, worker/timer
roles, and profile are absent in the new queries.

## Exact execution

Working directory: the `CAS_META_2_COMPOSITION` directory containing this record.

```powershell
python -B records/child_call_v8_launch_connection_001/readiness_001/capture.py
python -B records/child_call_v8_launch_connection_001/readiness_001/supplement.py
python -B records/child_call_v8_launch_connection_001/readiness_001/summarize.py
```

The first supplemental attempt failed before any provider call because its sibling
helper was not importable by a bare name. `SUPPLEMENT_IMPORT_FAILURE.md` preserves
that failure and the original script hash. The successful version loads the exact
sibling path. Primary records were not replaced. These capture scripts deliberately
refuse to overwrite existing observation files; any future observation needs a new
record directory.

The saved receipts bind the Python/SDK versions, exact absolute commands, query
times, source hashes, and raw main stdout/stderr. `readiness_summary.json` binds all
31 numbered response records and the historical termination receipt.

Still required: explicit launch approval; tested dedicated parent; immediate price,
identity, and quota recheck before reservation; confirmed independent shutdown;
real reservation and instance-bound worker plan; on-instance installation, CUDA,
checkpoint, and generation checks. This record contains no neural execution.
