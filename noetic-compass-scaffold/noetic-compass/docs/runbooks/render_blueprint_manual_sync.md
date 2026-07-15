# Render Blueprint manual-sync runbook

## Purpose and claim boundary

This runbook keeps Render infrastructure changes behind the same exact-commit
CI evidence as application deploys. The repository control is
`.render/blueprint-control.json`; the executable check is
`scripts/verify_render_blueprint_control.py`.

A successful CI run, Blueprint sync, deploy, or health check is deployment
evidence only. It does **not** make an account, billing, worker, WORM,
compliance, or customer-readiness `ACCEPT` claim. Preserve any `OPEN` or
`FLAG_FOR_HUMAN_REVIEW` status until its own evidence gate is satisfied.

## Controlled Blueprints

| Environment | Blueprint | File / Blueprint branch | Service / service branch |
|---|---|---|---|
| Production | `exs-d82lpanaqgkc7399m1g0` | `render.yaml` / `master` | `noetic-compass-api` / `master` |
| Account canary | `exs-d9aknt8458ps73ftpkc0` | `render.canary.yaml` / `master` | `cas-harness-api-accounts-canary` / `release/accounts-canary-20260713` |
| Customer production | `exs-d9biqt37uimc73ajh99g` | `render.customer.yaml` / `master` | `cas-harness-customer-api` / `master` |

All three identity-locked Blueprint Settings pages must show **Auto Sync: No**.
All three stable service IDs must show their policy-bound branch, service type, repository, region, and
`autoDeployTrigger: checksPass`; production must also keep
`healthCheckPath: /health`. The required aggregate GitHub checks are:

- `cas-ci-gate`
- `cas-postgres-live-gate`

The account canary intentionally has two commit identities. The Blueprint file
comes from `master`, while its service source comes from the release branch.
Never collapse those identities into a single ambiguous `commit_sha` field.

`render.customer.yaml` is repository-controlled and provider identity is now
locked to project `prj-d9biitbtqb8s73cn3le0`, protected isolated environment
`evm-d9biitbtqb8s73cn3leg`, Blueprint `exs-d9biqt37uimc73ajh99g`, web service
`srv-d9bijbjtqb8s73cn4n20`, database URL identity
`dpg-d9biitbtqb8s73cn3mgg-a`, and service disk
`dsk-d9bijbjtqb8s73cn4o60`. The disk must remain named
`cas-harness-customer-support`, mounted at `/var/customer-support`, and exactly
1 GB while this bootstrap topology exists. A replacement, re-association, or
different provider identity requires fresh readback and a protected manifest
change before it can be trusted.

The live verifier reads the exact Postgres resource without using Render's
credential-bearing connection-info endpoint. It pins database/user name,
region, PostgreSQL version, plan, disk size, autoscaling posture, and public-IP
posture. Render's live API serializes the Blueprint's `ipAllowList: []` private
database configuration as JSON `null`; the identity manifest pins that exact
provider readback while `render.customer.yaml` still requires the empty YAML
list. The verifier also reads the disk independently and binds it back to the
exact customer service. The project/environment reads require exact project
linkage and resource membership plus `protectedStatus=protected` and
`networkIsolationEnabled=true`. The Render UI currently reports **Protected
environment** and **Block cross-environment connections** enabled; an
authenticated live-verifier pass is still required for release evidence.

Initial deploy `dep-d9bijbrtqb8s73cn4ot0` used trigger `blueprint_sync`. It is
live bootstrap lineage only and must **not** satisfy
`root_ci_protected_deploy`. The first eligible customer deploy must be a later
exact-master `new_commit` deploy that begins only after all required checks for
that same SHA pass. Provider identity lock and a live service do not change
customer-production `ACCEPT`, which remains `OPEN`.

Blueprint re-association sync `exe-d9biqtb7uimc73ajh9l0` is provider lineage
for the current `master` / `render.customer.yaml` association only. A sync
event is not a checks-gated service deploy and cannot substitute for the later
eligible `new_commit` deploy or its exact-SHA CI receipt.

### Customer source prerequisite

The public support privacy guard is protected on `master` at exact commit
`ed6a0f9fa433052fa48ce4d70dbbbc990042538e`. It makes the server-owned privacy
notice a prerequisite for both CRM and support persistence: while publication
status is `OPEN`, public intake returns `503` and persists zero PII. The current
customer-Blueprint source must contain that guard and must not be deployed
directly. Before every sync or deploy, the final `service_source_sha` must pass:

```bash
git merge-base --is-ancestor \
  ed6a0f9fa433052fa48ce4d70dbbbc990042538e \
  <service_source_sha>
```

Exit status zero plus exact-SHA CI is required. An `OPEN` privacy notice still
blocks public persistence and legal publication `ACCEPT`; containing the guard
does not convert the draft notice into `present`.

### Customer AWS principal

Create a distinct, programmatic-only IAM principal for this service. Its inline
policy must use these exact actions and resources (replace nothing in this
customer-specific policy):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CustomerEvidenceBucketReadiness",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketObjectLockConfiguration",
        "s3:GetBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::cas-harness-runpod-92754088"
    },
    {
      "Sid": "CustomerEvidencePrefixObjects",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:PutObjectRetention",
        "s3:GetObjectRetention"
      ],
      "Resource": "arn:aws:s3:::cas-harness-runpod-92754088/cas-harness/customer-production/evidence-anchors/*"
    }
  ]
}
```

Do not grant `s3:*`, bucket mutation, list, delete, version delete,
`s3:BypassGovernanceRetention`, or access to another prefix. The application
needs no `AWS_SESSION_TOKEN` for a long-lived IAM access key. If the bucket is
later moved to a customer-managed KMS key, add only `kms:GenerateDataKey` and
`kms:Decrypt`, scoped to that exact key and bucket encryption context, in a
separately reviewed policy change.

### Render secret continuity and `sync: false`

Render prompts for `sync: false` values only during initial Blueprint creation.
On later Blueprint updates it ignores those declarations and preserves the
dashboard-managed values; adding, changing, or removing a `sync: false` line in
YAML is not a provider update or rotation. Set or rotate such values in Render,
redeploy, and read back only presence/fingerprint evidence. Never copy a value
to a command argument, repository file, Actions log, artifact, issue, PR, or
chat. See Render's [Blueprint secret-value semantics](https://render.com/docs/blueprint-spec#prompting-for-secret-values).

`generateValue: true` creates a random value only when the env key is absent.
If an operator deletes a still-declared key, the next sync recreates a different
value. That breaks continuity and is a rotation, not a recovery. Before first
bootstrap or customer traffic, use a provider-side one-off path with no stdout
to copy the exact generated values into an approved encrypted secret manager
under separate records. The backup role must be distinct from the S3 runtime
principal. Preserve only secret-manager version IDs and SHA-256 fingerprints in
release evidence, then perform an exact-value restore drill without exposing
the values.

Continuity requirements are:

| Authority | Accidental rotation impact | Required recovery/rotation control |
|---|---|---|
| `NC_JWT_SECRET` | Existing JWTs stop verifying. | Restore the exact value; no deliberate rotation without a dual-key/session migration. |
| `NC_ACCOUNT_CREDENTIAL_PEPPER` | Every stored customer credential becomes unusable. | Restore exactly; a rotation requires credential re-issuance/migration first. |
| `NC_EVIDENCE_SHARE_TOKEN_PEPPER` | Every active evidence share stops verifying. | Restore exactly, or record an explicit all-shares revocation decision before rotation. |
| `NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY` | Existing serialized Object-Lock receipts fail verification. | Restore exactly; do not rotate until a receipt keyring/migration exists. |
| `NC_ACCOUNT_BOOTSTRAP_SECRET` | First-owner bootstrap/recovery authority changes. | Back up until owner login is verified; retire by removing the YAML declaration, syncing that exact SHA, then deleting the Render value. |
| `NC_BILLING_ADMIN_SECRET` | Manual entitlement administration clients lose authority. | Restore exactly or rotate in an audited client-and-server cutover while provider billing remains dark. |
| `NC_PLATFORM_TENANT_PROVISIONING_SECRET` | Platform tenant provisioning clients lose authority. | Restore exactly or rotate in an audited client-and-server cutover. |

All seven values must remain distinct. A Render service replacement must restore
the same continuity-sensitive values before traffic; letting the replacement
generate new values does not constitute recovery.

### Bootstrap capacity and availability boundary

The customer Blueprint is deliberately cheap bootstrap infrastructure:

- The attached 1 GB service disk forces `numInstances: 1`, prevents horizontal
  scaling, and disables Render zero-downtime deploys. Deploys include an outage.
- The Postgres disk is 1 GB with `storageAutoscalingEnabled: false`; the
  `basic-256mb` plan also has limited compute/memory headroom.

Wire provider alerts before any customer journey: warning at 60% and critical
at 75% for both service-disk and Postgres storage; warning/critical at 70%/85%
for Postgres CPU, memory, and connection utilization sustained for 15 minutes.
Route critical alerts through the primary on-call ACK and secondary escalation
path, and preserve one non-secret delivery/readback drill.

The following are hard prerequisites before customer-production `ACCEPT`:

1. Migrate support tickets, CRM JSONL, and the file-backed Evidence Packet/hash
   log off the attached service disk to shared Postgres/S3-backed stores, remove
   the disk, run at least two API replicas, and prove a rolling deploy plus
   replica/restart continuity with no lost records.
2. Increase Postgres storage to at least 5 GB and enable storage autoscaling.
   Start that upgrade earlier if actual storage reaches 60% or the 30-day
   forecast reaches 70% of the 1 GB bootstrap disk.
3. Upgrade from `basic-256mb` before acceptance if representative hosted load
   reaches 70% CPU, memory, or connections for 15 minutes, then repeat the load,
   restart, quota, tenant-isolation, and Evidence Packet readback proof.
4. Show all capacity alerts healthy with at least 30 days projected storage
   headroom. A quiet alert caused by missing telemetry is `unavailable`, not
   healthy.

Until those migrations, upgrades, alerts, and proofs exist, this lane may earn
bounded staging evidence only; customer-production `ACCEPT` remains `OPEN`.

## 1. Prepare exact source commits

1. Make the infrastructure change in a pull request targeting `master`.
2. Run the repository-only control locally from the repository root:

   ```bash
   python scripts/verify_render_blueprint_control.py --offline
   python -m unittest discover -s scripts/tests -p 'test_verify_render_blueprint_control.py'
   ```

3. Merge only after the PR checks pass.
4. Fetch the remote branches and capture full, 40-character commit SHAs:

   ```bash
   git fetch origin master release/accounts-canary-20260713
   git rev-parse origin/master
   git rev-parse origin/release/accounts-canary-20260713
   ```

Record them with these exact field names:

```json
{
  "blueprint_source_sha": "<40-character SHA for master>",
  "service_source_sha": "<40-character SHA for the service branch>"
}
```

For production, the two values will normally match. For the account canary,
they can differ and must remain separately evidenced.

## 2. Verify CI for the exact SHAs

Do not rely on a green check from a different commit. In GitHub, open the
commit page for each recorded SHA and confirm the check suite belongs to that
exact 40-character SHA.

- The `blueprint_source_sha` must have the repository's offline Blueprint
  control check through `cas-ci-gate`.
- The `service_source_sha` must have successful `cas-ci-gate` and
  `cas-postgres-live-gate` conclusions before a checks-passing service deploy.
- If the service branch has no check suite, dispatch both existing workflows
  on that branch and record the resulting run URLs. Do not substitute a run
  from `master` when the service source SHA differs.

Record the workflow run URL, check name, conclusion, and checked SHA. A branch
name alone is not evidence of which code passed.

## 3. Confirm Auto Sync is still disabled

Before changing Render state, run the upstream workflow **Render Blueprint
Control** on `master`, or run its live verifier in an environment where
`RENDER_API_KEY` is already stored as a masked secret:

```bash
python scripts/verify_render_blueprint_control.py --live
```

The command reports `autoSync=false` for all three stable Blueprint IDs and a
service control PASS for `srv-d82ph683kofs73d210e0`,
`srv-d9akoolaeets73bp3e7g`, and `srv-d9bijbjtqb8s73cn4n20`. It reads each stable service through Render's
authenticated service endpoint and fails closed on branch, service type,
repository, region, deploy-trigger, or production health-path drift. It
also verifies the customer service's exact origin and disk, then independently
reads the project/environment protection and isolation state, the disk, and
Postgres identities/configuration. It
suppresses Render error response bodies and never prints the key or raw API
payload. Transient transport failures and Render HTTP `408`, `429`, `500`,
`502`, `503`, and `504` responses receive at most three 30-second attempts
with 2- and 5-second backoffs; all ten live reads share one 210-second
deadline. A wall-clock watchdog covers connection, bounded body read, and JSON
parsing, and a response that completes at or after the shared deadline is
rejected. Redirects are disabled so the Render Bearer token is never forwarded
to another origin. Authentication, invalid JSON, non-object payloads, and
policy drift are never retried. Do not put the API key, a Blueprint sync hook,
or any dashboard credential in a command argument, evidence file, issue, PR,
or chat transcript.

If the optional GitHub live job says `RENDER_API_KEY` is not configured, the
offline policy still ran, but live drift has not been checked. Verify **Auto
Sync: No** directly in each Blueprint Settings page before continuing.

## 4. Perform one manual sync

1. Open the intended Blueprint in Render.
2. Reconfirm its ID, source file path, source branch, and **Auto Sync: No**.
3. Select **Manual Sync**. Do not use a private sync-hook URL.
4. Review the proposed Render actions. Stop if an unrelated resource, branch,
   plan, region, secret value, deletion, or replacement appears.
5. Apply the sync once and record its sync ID and start/completion timestamps.

Manual sync changes the infrastructure declaration. The service deploy is a
separate event and can have a separate source SHA, especially for the canary.

## 5. Capture post-sync and post-deploy evidence

For the synchronized environment, record at least:

```json
{
  "blueprint_id": "<exs-...>",
  "blueprint_path": "<render.yaml, render.canary.yaml, or render.customer.yaml>",
  "blueprint_source_sha": "<40-character SHA>",
  "service_name": "<Render service name>",
  "service_source_sha": "<40-character SHA>",
  "required_checks": {
    "cas-ci-gate": {"conclusion": "success", "run_url": "<GitHub URL>"},
    "cas-postgres-live-gate": {"conclusion": "success", "run_url": "<GitHub URL>"}
  },
  "render_auto_sync": false,
  "blueprint_sync_id": "<sync ID>",
  "service_deploy_id": "<deploy ID>",
  "post_sync_health": "<observed result, not a readiness claim>"
}
```

Then:

1. Confirm the Render deploy identifies the recorded `service_source_sha`.
2. Confirm **Auto Sync: No** remains unchanged.
3. For production, verify `/health` and `/health/ready`, followed by the
   feature-specific smoke appropriate to the change.
4. For the private canary, verify from Render Shell or another private-network
   path; do not expose it as a public Web Service for convenience.
5. Attach only non-secret IDs, URLs, timestamps, hashes, and outcomes to the
   deployment record. Never attach environment values or sync hooks.

## 6. Failure and rollback

- If exact-SHA CI is missing or failed, do not sync.
- If Auto Sync is `Yes`, set it to `No`, run the live verifier, and investigate
  any sync that may already have started before proceeding.
- If the manual sync proposes unexpected actions, cancel it and correct the
  pull request or live Blueprint mapping.
- If the service deploy fails, keep the failed deploy evidence, revert through
  a new reviewed commit, pass exact-SHA CI again, and perform another manual
  sync. Do not bypass `checksPass` with an arbitrary commit pin.
- Never label a rollback, health response, or deployment as customer `ACCEPT`
  evidence by itself.
