# AWS RunPod Guardian Candidate

Status: `ENGINEERED / INERT / NOT_DEPLOYED / NOT_LIVE_VALIDATED`.

This directory is the deployable candidate for an independently durable
guardian. AWS Step Functions Standard owns the workflow. DynamoDB owns the
global one-use authorization and fencing state. Three method-specific provider
proxy Lambdas hold the RunPod key; only the create proxy permits
`POST /v1/pods`. The control, observe, create, stop, starter, and recovery
workers have no provider credential. Their IAM roles can invoke at most their
explicit proxy set; the stop worker uses the STOP proxy and the observe proxy
for the required post-STOP exact-ID GET. The local launcher never receives the
key and never sends the create request.

The real A40/Pythia experiment is still `NOT RUN`. Code or offline tests are
not a scientific PASS.

## What is here

- `src/guardian_runtime.py`: DynamoDB atomic head/evidence adapter, global
  single-active pointer, one-use CREATE capability, KMS DIGEST signer/verifier,
  AWS-service UTC and fail-safe containment clocks, normalized credential
  guard, fixed-host RunPod transport, Lambda handlers, and O(1) recovery.
- `state_machine.asl.json`: Standard workflow. Only the pre-provider claim has
  a bounded retry for Lambda service/throttling failures; provider tasks never
  retry automatically.
- `template.yaml`: inert-by-default SAM/CloudFormation stack for `us-west-2`.
- `create_deployment_binding.py`: offline canonical binding generator.
- `build.ps1`: deterministic, hash-locked Lambda ZIP builder; it makes no
  cloud or provider call. The ZIP includes a generated compiled lock identity.
- `tests/test_guardian_runtime.py`: fake AWS/provider hostile tests.
- `RUNBOOK.md`: exact operator, activation, rollback, and cleanup procedure.

## Safety boundary

Admission, registration, and CREATE require all of these bindings:

1. `ACTIVATION_MODE=LIVE`.
2. Lambda region and frozen region are both `us-west-2`.
3. The deployment binding is a non-zero SHA-256 and matches the execution.
4. The environment lock equals the lock identity compiled into the ZIP.
5. Reviewed empirical timing evidence covers at least one missed recovery tick,
   worker startup, and the bounded provider STOP path. It is evidence, not an
   AWS scheduling guarantee.
6. The existing Secrets Manager record binds the same deployment and RunPod
   account.
7. CloudFormation LIVE rules require the independent recovery schedule.
8. The runtime ZIP is an immutable, versioned S3 object.

After a possible CREATE, containment must not depend on S3 or STS availability.
The control, recovery, post-dispatch reconciliation, STOP, observe-proxy, and
stop-proxy handlers use the compiled lock and exact local stack/function
identity. If trusted STS time becomes unavailable, uncertainty is sticky: the
runtime fails toward immediate exact-ID STOP and cannot sign a positive
deadline/SLA claim from fallback wall time.

One DynamoDB transaction writes each compact receipt-bearing head transition
and its immutable content-addressed receipt together. Registration also claims
one global single-active pointer. The table has the non-parameterized physical
name `cas-runpod-guardian-global-v1-<AWS-account-id>` in `us-west-2`; a second
stack in the account/region cannot create a parallel ledger. The canonical
binding recomputed inside every Lambda includes that exact table ARN, KMS key,
state machine, all worker/proxy ARNs, stack/account/region, and artifact hashes.
Changing an operational target without regenerating the reviewed binding fails
closed before registration, admission, or CREATE. The create-dispatch transaction mints a
ledger-, owner-, fence-, lease-, request-, and window-bound capability. The
create proxy consumes it exactly once in its own conditional transaction before
the sole provider POST. Losing the worker after the durable marker or after
request bytes leave the process never causes an automatic CREATE retry. A
unique exact-ID result can only be recovered from complete account inventory.
Workload admission requires a later authoritative exact-ID GET. A bound ID
remains eligible for late STOP even after missed proof deadlines.

The global pointer is released only after a strong read resolves signed
exact-ID terminal proof or signed zero-POST safe-loss proof. An unresolved
post-dispatch failure retains the pointer because an unbound Pod may still be
live. Provider response bodies are validated byte-for-byte in memory, but
durable receipts retain only body hashes/lengths, bounded metadata evidence,
and strict allowlisted semantic projections—not reversible raw bodies.

The current official RunPod REST contract used here is the fixed host
`rest.runpod.io`, account-wide `GET /v1/pods`, `POST /v1/pods`, exact-ID
`GET /v1/pods/{id}`, and `POST /v1/pods/{id}/stop`. See the official
[List Pods](https://docs.runpod.io/api-reference/pods/GET/pods),
[Create Pod](https://docs.runpod.io/api-reference/pods/POST/pods),
[Find Pod](https://docs.runpod.io/api-reference/pods/GET/pods/podId), and
[Stop Pod](https://docs.runpod.io/api-reference/pods/POST/pods/podId/stop)
references. The transport rejects redirects, compression, query strings, an
unexpected pagination signal, cross-host paths, and methods outside each
Lambda's allowlist.

This candidate intentionally supports one active canary, not multi-tenant
scale. Recovery strongly reads the one global pointer and its exact head, so
receipt growth cannot hide a stale lease. It can sign zero-POST safe loss for
an expired, never-claimed authorization, repair a pointer left after a terminal
delete outage, or launch a fenced successor with an EventBridge-event-unique,
async-retry-stable attempt name. A colliding execution suppresses another start
only while `RUNNING`; a terminal pre-claim collision derives a new bounded name.
It never releases an unresolved possible-CREATE pointer. EventBridge delivery
and Lambda asynchronous execution failures each have at most two retries and a
60-second event-age cap; duplicates converge through the pointer/fence.
Exhausted failures route to the retained SQS destination. Lambda error/throttle,
EventBridge delivery, and DLQ-depth alarms expose timing failures.

## Offline verification

Use bytecode- and cache-free test commands:

```powershell
python -B -m pytest -p no:cacheprovider -q infra\runpod_guardian_live_candidate\tests\test_guardian_runtime.py
python -B -m pytest -p no:cacheprovider -q tools\runpod_open_weight_canary_v2\test_aws_production_guardian_core.py
python -B -m pytest -p no:cacheprovider -q tools\runpod_open_weight_canary_v2\test_precreate_guardian_offline.py
cfn-lint infra\runpod_guardian_live_candidate\template.yaml
pwsh -NoProfile -File infra\runpod_guardian_live_candidate\build.ps1 -VerifyOnly
```

The candidate must also pass current `cfn-lint` with zero findings. A passing
fake-service suite proves only the deterministic code boundary; it does not
prove AWS IAM, DynamoDB, Lambda, KMS, Step Functions, Secrets Manager, DNS/TLS,
or RunPod behavior in the live account.

## Resource and cost surface

The template creates 48 resources: one DynamoDB on-demand/PITR table; one
retained asymmetric P-256 KMS key and alias; ten narrow IAM roles plus one
shared activation-document read policy; nine Arm64 Lambda functions; ten
retained 90-day log groups; one Standard state machine; four HTTP API
resources; two Lambda invoke permissions; one disabled-by-default EventBridge
recovery rule; one retained SQS recovery queue and policy; one Lambda async
failure configuration; and four CloudWatch alarms.

It creates no VPC, NAT gateway, paid interface endpoint, EC2 host, RunPod Pod,
secret, or artifact bucket. The secret and private versioned artifact bucket
must already exist.

At very low use, the clear fixed incremental AWS charge is the retained
customer-managed KMS key at `$1/month`, prorated hourly. A dedicated existing
Secrets Manager value is `$0.40/secret/month`, plus `$0.05/10,000` API calls.
ECC signing requests are `$0.15/10,000`; asymmetric operations are excluded
from the KMS request free tier. Standard Step Functions, Lambda, HTTP API,
DynamoDB on-demand/PITR, EventBridge, SQS, S3, and CloudWatch are usage/storage
metered; account-wide free-tier consumption can change the actual bill. Check
the live `us-west-2` calculator immediately before stack creation. Sources:
[KMS pricing](https://aws.amazon.com/kms/pricing/),
[Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/),
[Step Functions pricing](https://aws.amazon.com/step-functions/pricing/),
[Lambda pricing](https://aws.amazon.com/lambda/pricing/),
[DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/),
[HTTP API pricing](https://aws.amazon.com/api-gateway/pricing/), and
[CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/).

## Limits that remain open

- KMS proves that the configured AWS key signed the guardian receipt. It is not
  a RunPod signature, provider billing settlement, scientific result, or human
  attestation.
- The STS HTTPS `Date` header is the AWS-side UTC source. It is not a
  cryptographically signed RunPod timestamp. Loss of trusted time after a
  possible CREATE forces containment and permanently disqualifies a positive
  SLA claim for that operation.
- Lambda is intentionally outside a VPC so it can reach both AWS public
  managed-service endpoints and RunPod without a NAT gateway. Egress is
  restricted by exact proxy handlers to one TLS host and method set, not by a
  network firewall. Each proxy still holds the full RunPod key. A
  network-layer egress allowlist/provider-scoped key remains `OPEN`.
- Separate proxy handlers and IAM invoke edges enforce methods only while the
  reviewed hash-locked proxy code is intact. Arbitrary-code compromise of a
  proxy role could use its full RunPod key and public egress; an independent
  method-enforcing egress proxy or provider-scoped credentials remains `OPEN`.
- Secrets Manager availability is still needed by a cold provider-proxy
  invocation, including STOP. Live fault testing must prove the containment
  path or this remains a LIVE `NO_GO` gate.
- PITR is enabled, but a backup/restore drill, regional disaster recovery,
  CloudTrail evidence export, and external immutable/WORM anchoring remain
  `OPEN` until observed live.
- The template does not create or rotate the RunPod credential. Secret
  rotation and revocation are operator procedures.
- The IAM policies and state machine must be service-validated in the actual
  non-root account before LIVE activation.
- The compiled lock proves which reviewed source hashes the ZIP claims. The
  binding of the materialized Lambda `CodeSha256`, S3 object version, and live
  stack descriptions still depends on the reviewed deployment procedure; it
  is not a self-verifying remote attestation. That gate remains `OPEN` until
  live read-only evidence is retained.
- The core's abstract 86-second model has four seconds of mathematical margin,
  but EventBridge is best-effort and does not provide a hard 60-second wake
  guarantee. This LIVE candidate therefore requires a conservative 300-second
  STOP lead (STOP begins by minute 25 of a 30-minute hard wall). AWS scheduling,
  reserved-concurrency quota, cold-start, Secrets Manager, Lambda proxy, DNS,
  TLS, and RunPod behavior must be measured in the target account and bound by
  reviewed timing evidence. Offline tests do not prove the SLA.

Read `RUNBOOK.md` before any AWS action.
