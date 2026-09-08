# Binding-fit training check — AWS launcher

Owner-authorized run for this check directory
(`records/teaching_cycle_001/binding_fit_training_check_001/`, see
`OWNER_AUTHORIZATION.json`). This document describes the minimal launcher and
the exact execution the integrator will run. Nothing here executes any AWS
call, reserves money, runs neural work, or commits.

## What it is

`aws/binding_fit_launch.py` is one self-contained module that does four jobs:

1. **Frozen plan + request/authority validation** — the run scope is frozen
   (account, region, AMI, instance type, GPU, rate ceiling, budget).
2. **Source package builder** — builds the package from exact Git objects at a
   pinned 40-hex commit (never the working tree), carries the teaching mode and
   its real transitive closure, the two frozen wheels, `requirements-gpu.txt`,
   and a rendered worker script. The manifest stays `launch_enabled: false`.
3. **Worker script** — rendered into the package; on the instance it creates or
   discovers a venv, installs `torch==2.11.0` from
   `https://download.pytorch.org/whl/cu128`, installs the two wheels with
   `--no-deps`, runs `cas_meta2.binding_fit_training.mode.launch(...)` with real
   torch and the real policy/tokenizer/model construction, then writes
   `results/result.json` + a sha256 sidecar and uploads both to the job bucket.
   Evidence is written on failure too.
4. **AWS launch lifecycle** — plan-only by default; `--execute` reserves exactly
   once through `aws/budget.reserve_budget` and runs the instance with
   `ClientToken=job` and IMDSv2 `HttpTokens: required`, waits for
   `results/result.json`, collects, cleans up, and persists the result on every
   exit.

`boto3`/`botocore` are imported lazily, only inside `build()`. The module import
imports no tensor or provider library, and tests inject fake client stacks and
fake git objects.

## Frozen budget (verbatim)

```text
max_optimizer_steps = 48
max_wall_seconds    = 600.0
learning_rate       = 0.003
reservation_usd     = "4.00"
```

These are the exact mode declaration points: `48 = 24 cases × 1 step × 2
families`. The authority validation refuses any authority whose
`learning_rate`, `max_optimizer_steps`, or `max_wall_seconds` differ from these
frozen values.

## Frozen preflight facts

```text
account                = 807562639912
region                 = us-west-2
ami                    = ami-0fbbd0facbc9e3cff
instance_type          = g7.2xlarge  (one instance)
gpu_name_contains      = RTX PRO 4500
t4_rejected            = true
on_demand_rate_ceiling = 2.52 USD/hr
```

## Package member list

| Member | Source |
|---|---|
| `cas_meta2/binding_fit_training/**` | exact git objects |
| `cas_meta2/teaching_cycle/**.py` | exact git objects |
| `cas_meta2/codec.py` | exact git objects |
| `cas_meta2/__init__.py` | exact git objects |
| `cas_meta2/features_v2.py` | exact git objects (transitive dep: `LosslessPublicTokenizer`) |
| `cas_meta2/policy.py` | exact git objects (transitive dep: real policy construction) |
| the two frozen wheels under `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/` | exact git objects |
| `requirements-gpu.txt` | exact git objects |
| `binding_fit_worker.py` | rendered into the package |

`features_v2.py` and `policy.py` are required by
`mode.launch` (`guided_application.fit_tokenizer` and
`policy.build_matched_policies`) and are included in addition to the minimum
named in the authorization so the mode actually runs.

## Build the source package

```text
python -B -m aws.binding_fit_launch  --build?   (no; the builder is a library)
```

The package builder is `aws/binding_fit_launch.build_package(output,
source_sha=COMMIT)`. Run it once the freeze commit is pinned:

```text
python -B -c "import json; from aws import binding_fit_launch as L; \
r = L.build_package('records/teaching_cycle_001/binding_fit_training_check_001/package', \
source_sha='<40-hex freeze commit>'); print(json.dumps(r, sort_keys=True))"
```

`receipt.json` in that output directory records `archive_sha256` and
`manifest_sha256`; both go into the launch request and authority files.

## Launch request and authority files

The `--execute` path requires two hash-bound JSON files, both validated
strictly (exact fields, no extras).

Request (`REQUEST_SCHEMA = "cas-teaching-binding-fit-launch-request/1"`):

```json
{
  "schema": "cas-teaching-binding-fit-launch-request/1",
  "job": "cas-meta2-teaching-binding-<14-digit> -<8-hex>",
  "source_sha": "<40-hex freeze commit>",
  "archive_sha256": "<64-hex>",
  "manifest_sha256": "<64-hex>",
  "launch_authorized": false
}
```

Authority (`AUTHORITY_SCHEMA = "cas-teaching-binding-fit-launch-authority/1"`):

```json
{
  "schema": "cas-teaching-binding-fit-launch-authority/1",
  "job": "<same job as request>",
  "source_sha": "<same as request>",
  "archive_sha256": "<same as request>",
  "manifest_sha256": "<same as request>",
  "owner_authorization_sha256": "<sha256 of OWNER_AUTHORIZATION.json bytes>",
  "learning_rate": 0.003,
  "max_optimizer_steps": 48,
  "max_wall_seconds": 600.0,
  "reservation_usd": "4.00"
}
```

## Exact `--execute` invocation

```text
python -B -m aws.binding_fit_launch --execute \
  --request records/teaching_cycle_001/binding_fit_training_check_001/launch_request.json \
  --request-sha256 <sha256 of launch_request.json> \
  --authority records/teaching_cycle_001/binding_fit_training_check_001/launch_authority.json \
  --authority-sha256 <sha256 of launch_authority.json> \
  --receipt-dir records/teaching_cycle_001/binding_fit_training_check_001/receipt_<job> \
  --profile <aws-profile>
```

`--receipt-dir` must be a fresh (not yet existing) directory; the launcher
refuses to run otherwise. Without `--execute`, the module prints
`PLAN_ONLY_NOT_EXECUTED` and performs no provider call, reservation, model
import, or output mutation.

## Lifecycle discipline

- One reservation only, `"4.00"`, through `aws/budget.reserve_budget`; a job id
  already in the ledger is refused (`JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY`).
- One instance, `ClientToken=job`, IMDSv2 `HttpTokens: required`.
- Wait is a bounded poll for `results/result.json`.
- Cleanup terminates the instance, deletes objects (including `results/*`),
  deletes the bucket, deletes the security group, and removes roles/profiles and
  the schedule — tolerating resources that are already absent.
- The result (with any cleanup failure) is persisted to `result.json` in the
  receipt directory on every exit; an incomplete cleanup fails the status but
  is recorded, never raised away.

## Tests

`tests/test_binding_fit_launch.py` — 38 pure tests with fake client stacks and
fake git objects: plan-only inertness, request/authority validation (including
the frozen-budget match), package build + zip readback + `launch_enabled:false`,
worker-script text, budget single-reservation refusal, cleanup already-absent
tolerance, security-group deletion, cleanup detach ordering
(`test_cleanup_detaches_role_before_deleting`), the pricing-client region check
(`test_build_prices_client_from_us_east_1`), the bounded IAM profile
verification wait (`test_await_instance_profile_waits_until_role_visible`,
`test_await_instance_profile_times_out`), and evidence persistence on cleanup
failure. No real tensor or provider library is imported.

## Attempt log

| Attempt | Job | Outcome |
|---|---|---|
| 001 | `cas-meta2-teaching-binding-20260908120635-035f9ac7` | REFUSED_AT_PREFLIGHT, `$0.00` spent — `AccessDeniedException` on `pricing.get_products` issued from `us-west-2`. See `PREFLIGHT_REFUSAL_ATTEMPT_001.md`. |
| 002 | `cas-meta2-teaching-binding-20260908191109-dcf939ab` | AWS_BINDING_FIT_FAILED — preflight and the `$4.00` reservation succeeded, then `RunInstances` refused the just-created instance-profile ARN (IAM eventual consistency; no verification wait existed) and cleanup hit `DeleteConflict` on the role/profile. Adapter fixed (bounded verified wait before the single launch attempt; cleanup detach + inline-policy removal). IAM leftovers remediated and verified absent. See `ATTEMPT_002_LAUNCH_FAILURE.md`. |
