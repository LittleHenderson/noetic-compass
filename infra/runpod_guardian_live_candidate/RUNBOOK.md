# Guardian Deployment and Recovery Runbook

This runbook is fail-closed. `INERT` is the normal deployment state. Do not
interpret “stack created” as permission to create a RunPod Pod.

## 1. Human/operator gate

1. Do not deploy as the AWS account root user. Sign out of root.
2. Sign in as the reviewed non-root administrator `cas-g5-operator` (or a
   separately reviewed non-root deployment role) and complete MFA yourself.
3. In CloudShell, run `aws sts get-caller-identity`. STOP if the ARN ends in
   `:root`, the account is wrong, or the region is not `us-west-2`.
4. Do not paste an AWS credential, MFA value, RunPod key, secret payload, card
   detail, or signed session token into chat, a Git command, a test fixture, or
   shell history.
5. Immediately before creating the stack, show the exact 48-resource list and
   current AWS price estimate to the owner and obtain action-time confirmation.

## 2. Freeze and build offline

The guardian core must first be declared frozen by its independent core and
hostile audits. Then update `core-lock.json` with lowercase SHA-256 values for
the core, runtime, ASL, template, build script, binding tool, and adapter test
file, plus both frozen core/pre-create test files. Do not relax a hash to make
a build pass.

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tools\runpod_open_weight_canary_v2\test_aws_production_guardian_core.py
python -B -m pytest -p no:cacheprovider -q tools\runpod_open_weight_canary_v2\test_precreate_guardian_offline.py
python -B -m pytest -p no:cacheprovider -q infra\runpod_guardian_live_candidate\tests\test_guardian_runtime.py
cfn-lint infra\runpod_guardian_live_candidate\template.yaml
pwsh -NoProfile -File infra\runpod_guardian_live_candidate\build.ps1
pwsh -NoProfile -File infra\runpod_guardian_live_candidate\build.ps1 -VerifyOnly
```

Independently inspect `dist/build-manifest.json`, the ZIP entry list, every
source hash, compiled core-lock hash, `git diff --check`, and the current
commit. The ZIP contains only `aws_production_guardian_core.py`, generated
`guardian_build_identity.py`, and `guardian_runtime.py` at its root.

## 3. Private artifact and secret

Use an existing private, versioned, Block-Public-Access S3 bucket. Upload the
exact ZIP once, capture its object version ID and SHA-256, and never deploy an
unversioned key.

Use an existing Secrets Manager secret in `us-west-2`. Enter its value only in
the AWS Secrets Manager editor. Its exact JSON keyset is:

```json
{
  "schema_version": "cas_aws_runpod_guardian_secret.v1",
  "provider_account_id": "EXACT_RUNPOD_ACCOUNT_BINDING",
  "api_key": "ENTER_ONLY_IN_AWS_SECRETS_MANAGER",
  "deployment_binding_sha256": "EXACT_64_LOWERCASE_HEX_BINDING"
}
```

Do not put this JSON in the repository, CloudFormation parameters, Lambda
environment variables, Step Functions input/history, command arguments, or
evidence. The template takes only the secret ARN.

## 4. Deploy INERT first

The only permitted ledger name in this account/region is
`cas-runpod-guardian-global-v1-<12-digit-AWS-account-id>`. Before creating a
stack, use a read-only `dynamodb describe-table` for that exact name. If it
exists, STOP: do not create a second guardian stack or select another table.
Identify and update the stack that owns the retained table. Disaster recovery
must use a separately reviewed restore/import procedure that preserves the
canonical name and signed ledger history; ordinary replacement is prohibited.
If a failed/deleted stack retained the table, reconcile or import that exact
resource instead of working around the name collision.

Deploy `template.yaml` in `us-west-2` with:

- `ActivationMode=INERT`
- zero core-lock hash
- zero timing-validation evidence hash
- `RecoveryEnabled=FALSE`
- `RecoveryScheduleState=DISABLED`
- zero deployment binding
- exact non-secret provider account ID
- exact existing secret ARN
- exact private artifact bucket, key, and object version

CloudFormation must finish without rollback. Re-run `cfn-lint` and inspect the
resolved change set before execution. Confirm that no VPC, NAT gateway,
interface endpoint, EC2 resource, new secret, or RunPod resource is in it.

While inert, invoke each Lambda with a synthetic event and require
`GUARDIAN_FAIL_CLOSED:ACTIVATIONERROR` before any store/provider activity.
Confirm the recovery rule is disabled, the HTTP route requires `AWS_IAM`, the
state machine is `STANDARD`, execution-data logging is false, the table has
deletion protection and PITR, and the KMS key is asymmetric
`ECC_NIST_P256 / SIGN_VERIFY`.

## 5. Bind the materialized stack

Collect the exact stack ID, account, region, table ARN, KMS key ARN, state
machine ARN, nine Lambda ARNs (including the three provider proxies), secret
ARN, artifact bucket/key/version, compiled core-lock hash, timing-evidence
hash, and source/build hashes. Put those non-secret fields in the exact input
keyset accepted by `create_deployment_binding.py` and generate the canonical
binding document offline.

Two reviewers must compare the document with live read-only AWS descriptions.
Upload the reviewed timing-evidence document and canonical binding document to
the same private versioned artifact bucket, capture each exact S3 version ID
and SHA-256, and prohibit unversioned reads. Update only the Secrets Manager
value so it carries that same binding hash. Never include the API key in either
document.

## 6. Service validation before LIVE

Use a separate test authorization namespace and no provider mutation to prove:

- two simultaneous DynamoDB transactions yield one winner;
- the immutable receipt resolves by its content ID;
- KMS `Sign` and `Verify` use `ECDSA_SHA_256`, `MessageType=DIGEST`, and the
  retained exact 32-byte digest;
- a stale execution cannot heartbeat or mutate after a fenced takeover;
- the global single-active pointer rejects a second authorization, independent
  of issuer/account/key spelling;
- recovery performs exactly two strongly consistent reads (pointer and head),
  never a table scan or evidence-index query;
- an expired ownerless `AUTHORIZED` head receives signed zero-POST safe loss,
  releases only its matching pointer, and permits the next authorization;
- a first-claim/finalizer race has one durable CAS outcome;
- a crash or delete outage after terminal head/evidence commit is repaired by
  the next recovery tick;
- an unresolved post-dispatch possible CREATE retains the pointer and blocks a
  second authorization;
- every scheduled recovery event gets an event-ID-derived, async-retry-stable
  attempt name; a RUNNING collision suppresses a duplicate, while a terminal
  pre-claim collision derives a bounded new name and a later worker takes the
  fence;
- the create proxy independently consumes a current-owner/fence/lease/window
  capability exactly once, including duplicate and acknowledgement-loss races;
- the API denies unsigned/non-IAM calls;
- control has neither secret access nor provider-proxy invoke authority, while
  observe/create/stop can invoke only their exact method proxy;
- secret bytes and common encodings do not appear in Lambda, state machine,
  API, or CloudWatch logs;
- S3 outage after ambiguous CREATE does not block reconciliation/containment;
- STS time failure after possible CREATE forces STOP, remains sticky, and
  prevents a positive deadline/SLA receipt;
- cold proxy access to Secrets Manager, reserved-concurrency quota, Lambda
  throttling, DNS/TLS, and provider faults satisfy the containment budget.

Before LIVE, retain empirical timing evidence from an equivalent version- and
hash-locked preproduction deployment. It must include at least one consecutive
missed-tick scenario, the largest observed recovery gap, worker startup, and
the total exact-ID STOP transport path. EventBridge is best-effort: neither the
one-minute schedule nor the observed maximum is a deterministic service bound.
The core abstract model is `5 + 60 + 8 + 8 + 5 = 86` seconds, strictly below
its 90-second minimum, but this deployment requires a 300-second STOP lead:
STOP begins by minute 25 of the 30-minute hard wall. The retained evidence must
also show that the two-attempt/60-second-per-layer recovery retry envelope, reserved
recovery/control/STOP/observe chain, cold secret retrieval, DNS, TLS, and proxy
invocation fit inside that lead. Put only the approved evidence manifest SHA-256 in
`TimingValidationEvidenceSha256`. If those bounds are not observed, LIVE is
`NO_GO`; do not invent or self-attest the hash.

Perform and record a DynamoDB PITR restore drill to a disposable table. Until
that drill and an external immutable evidence export are observed, their gates
remain `OPEN`.

## 7. LIVE activation

LIVE requires a reviewed CloudFormation change set with the same artifact
version and only these intended binding changes:

- `ActivationMode=LIVE`
- exact non-zero deployment binding
- exact compiled core-lock document hash
- exact non-zero reviewed timing-validation evidence hash
- exact runtime ZIP SHA-256 and immutable artifact object version
- exact deployment-binding object key, version, and SHA-256
- exact timing-evidence object key and version
- `RecoveryEnabled=TRUE`
- `RecoveryScheduleState=ENABLED`

Obtain the owner's action-time confirmation immediately before executing that
change set. After update, verify function code SHA, environment bindings, IAM
roles, recovery schedule, table, KMS key, state machine, and API route again.

Register one exact authorization by directly invoking only the observe Lambda.
The registration event contains the complete `AuthorizationSpec` and canonical
base64 create request but no provider credential. Confirm the signed immutable
registration receipt resolves from DynamoDB. Then use the IAM-authenticated
HTTP route to start the Standard workflow.

The request must still be stopped before CREATE if inventory, price, capacity,
image, storage, port, SSH key, deadline, binding, recovery, secret, KMS, or
receipt verification differs. Once the durable dispatch marker exists, never
manually retry CREATE.

## 8. Containment and rollback

If no target ID is bound, disable new starts and let recovery reconcile through
the proof deadline. Do not send a second create request.

If an exact new target ID is bound, keep the guardian and recovery schedule
alive until exact-ID STOP and an authoritative `EXITED` or `TERMINATED` GET are
recorded. STOP occurs before any due-time GET. Never STOP a pre-arm inventory ID
or a protected ID. Never UPDATE, START, or DELETE a Pod from this guardian.

After every authorization is terminal:

1. Update the stack to `ActivationMode=INERT`, `RecoveryEnabled=FALSE`, and
   `RecoveryScheduleState=DISABLED`.
2. Revoke the IAM caller's permission to invoke the start route.
3. Rotate or revoke the RunPod API key in RunPod, then create a new Secrets
   Manager version if future use is intended.
4. Export signed receipts, body hashes/lengths, and allowlisted semantic
   projections to the approved immutable evidence location before any
   retention change. Raw provider bodies are deliberately not retained.

Do not delete the stack while a target is running, ambiguous, bound, STOPPING,
missing terminal proof, or in `UNRESOLVED_TERMINAL_FAILURE`. That unresolved
state deliberately keeps the global pointer because an unbound Pod may exist.

## 9. Cleanup and retained costs

CloudFormation deletion intentionally retains the DynamoDB ledger, asymmetric
KMS key, log groups, and recovery DLQ. The external secret and versioned
artifact are also outside stack deletion. This preserves evidence but can
continue charges.

Because the retained DynamoDB table owns the one account/region-global name,
do not deploy a fresh stack around it or restore into a parallel LIVE table.
Use a reviewed CloudFormation resource import/update of the exact canonical
table after a recovery drill; a second table is never an acceptable shortcut.

Any later cleanup is a separate destructive decision:

- verify every authorization is terminal and evidence is exported;
- take and verify a DynamoDB backup before deleting the retained table;
- schedule (do not immediately erase) KMS key deletion with the retained
  30-day window, understanding that old receipts then lose AWS online verify;
- retain the exported KMS public key and receipt manifest;
- delete only exact named log groups/artifact versions/secrets after their
  retention obligations are reviewed;
- do not delete or mutate the stopped evidence Pod `vernmyfb3ck9po`, protected
  Pods, or protected network volumes under this runbook.

Report what was removed, what remains billable, and whether each item can be
recovered.

## 10. Claim language

Use these exact statements until live evidence says otherwise:

- Guardian candidate: `ENGINEERED / INERT / NOT_DEPLOYED / NOT_LIVE_VALIDATED`.
- Real experiment: `NOT RUN` — neither PASS nor FAIL.
- Gate 5: `OPEN / KEEP_OPEN`.
- Stage C: `DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`.
- A KMS receipt proves AWS-key signing of the retained guardian bytes only. It
  does not prove RunPod truth, billing settlement, model execution, scientific
  validity, WORM anchoring, or human approval.
