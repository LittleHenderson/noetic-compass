# CAS Harness incident-response runbook

## Purpose and claim boundary

Use this runbook for a suspected or confirmed security event, credential
exposure, production control failure, or Evidence Packet integrity concern.
It is an operator procedure, not legal advice. It does not establish that a
compromise occurred, satisfy a notification duty, or make CAS Harness
customer-production `ACCEPT`. Record facts, inferences, and unknowns
separately. Preserve `OPEN` and `FLAG_FOR_HUMAN_REVIEW` until their own gates
are actually closed.

The machine-readable control is
[`incident_response_checklist.json`](incident_response_checklist.json). Validate
the control and every checked-in incident record with:

```powershell
python scripts/validate_incident_response_package.py
python -m pytest -q tests/test_incident_response_package.py
```

Never paste a secret into either command, an incident record, a pull request,
or an Evidence Packet.

## First 15 minutes

1. Create an incident ID: `IR-YYYY-MM-DD-NNN` and start a UTC timeline.
2. Assign an Incident Commander, Security/Forensics Lead, Infrastructure Lead,
   and Recorder. Keep `[ASSIGN]` visible rather than silently leaving a role
   empty.
3. Set an initial severity from the taxonomy below and write one sentence of
   evidence-based rationale. Severity can change as facts change.
4. Define the affected accounts, environments, credentials, tenants, and time
   window. Write `unknown` where scope is not established.
5. Pause non-incident production changes in the affected lane. Do not delete,
   overwrite, rewrite Git history, or rotate everything blindly before logs
   and provider event IDs are preserved.
6. Contain the narrowest credible authority: revoke/rotate the affected
   credential, invalidate hooks or sessions, restrict access, and keep a
   known-safe recovery path.
7. Start the notification decision gate early. A notification clock can begin
   before forensics is complete; only the assigned privacy/legal decision
   owner may determine the applicable duty.

If a raw credential is visible, stop copying it. Rotate it through the
provider's secret UI/API, preserve only non-secret event/version identifiers,
and continue from a clean terminal or browser surface.

## Severity and escalation targets

These are provisional operating targets until named on-call owners and an
approved company policy replace them.

| Severity | Use when | Initial acknowledgement | Update target |
|---|---|---:|---:|
| `SEV-0` Critical | Confirmed active destructive access, broad secret compromise, material customer-data exfiltration, or loss of trust in retained Evidence Packet integrity | 5 min | 30 min |
| `SEV-1` High | Confirmed/strongly evidenced unauthorized production access, critical auth bypass, or material customer outage without a safe workaround | 15 min | 60 min |
| `SEV-2` Material | Production security dependency degradation, credential-integrity anomaly, or control exposure with no established unauthorized use and a bounded containment path | 30 min | 120 min |
| `SEV-3` Low | Low-risk weakness or near miss without material degradation, unauthorized-access evidence, or customer impact | 1 business day | Daily |

Escalate immediately when any of these becomes true:

- evidence of unauthorized data access, secret use, deletion, policy change,
  account takeover, or persistence;
- customer or regulated data may be involved;
- an immutable Evidence Packet or its retention boundary may be untrustworthy;
- containment would destroy evidence or materially interrupt customers;
- a contractual, insurer, privacy, regulator, or law-enforcement notification
  clock may apply.

## Roles and on-call placeholders

| Role | On-call / escalation | Authority during incident |
|---|---|---|
| Incident Commander | `[ASSIGN: primary / backup / contact]` | Severity, priorities, cadence, change freeze, recovery and closure decision |
| Security/Forensics Lead | `[ASSIGN: primary / backup / contact]` | Evidence collection, scoping, investigative statements |
| Infrastructure Lead | `[ASSIGN: primary / backup / contact]` | RunPod, Render, AWS, GitHub, Vercel containment and recovery |
| Customer Operations Lead | `[ASSIGN: primary / backup / contact]` | Tenant impact, support queue, customer action tracking |
| Privacy/Legal Advisor | `[ASSIGN: counsel / privacy owner / insurer contact]` | Contractual and legal notification decisions; preservation instructions |
| Communications Lead | `[ASSIGN: primary / backup / contact]` | Approved internal/customer/public messages |
| Incident Recorder | `[ASSIGN: primary / backup / contact]` | UTC timeline, evidence index, decisions, actions and handoffs |

No one role should both make and silently record a high-impact decision. The
Recorder captures who decided, when, on which facts, and the next review time.

## Response lifecycle

### 1. Declare and stabilize

- Record incident ID, discovery source, UTC declaration time, severity,
  affected lane, and known customer impact.
- Start a change log. Every provider mutation gets a UTC time, actor, purpose,
  provider event/deploy/version ID, and observed result.
- Freeze unrelated changes in the affected lane. Emergency containment is
  allowed but must be recorded.
- Capture current exact commit SHA, deploy IDs, workflow run URLs, service/pod
  IDs, health outcomes, and the provider audit-log window.
- Do not infer compromise from a rejected or invalid credential. `Invalid`,
  `expired`, `deleted`, `disabled`, and `used by an unauthorized actor` are
  different facts.

### 2. Contain

- Revoke or rotate the narrowest affected credential first; preserve a
  break-glass recovery path under the Incident Commander.
- Remove superseded copies from every authorized caller and secret store.
- End affected sessions, invalidate hooks, and restrict provider membership if
  the evidence supports doing so.
- Prove the old authority no longer works without recording its value. Use a
  provider revocation event, a controlled rejection, or a version/status query.
- Keep Blueprint Auto Sync disabled and do not bypass exact-SHA CI during an
  incident recovery.

### 3. Scope and investigate

For each provider, record:

- identities and roles present before and after containment;
- credential/session/hook creation, use, rotation, and deletion events;
- configuration, environment, policy, repository, domain, deploy, and object
  access changes;
- source IP/user agent or geography only when lawfully available and useful;
- customer/tenant/data resources touched;
- the earliest and latest credible event time, plus audit-log retention limits;
- confirmed facts, reasonable inferences, alternative explanations, and
  unknowns.

Absence of a log entry is not proof that no access occurred when the provider
does not retain or expose the relevant log class.

### 4. Eradicate

- Remove the exposure path, stale secret copies, unauthorized membership,
  unneeded hooks, and excessive permissions.
- Replace shared, long-lived authority with least-privilege, scoped authority
  where supported.
- Verify repositories and client bundles do not contain the secret or a full
  hook URL. If Git history contains a secret, rotate first; history cleanup is
  a separate evidence-preserving decision.
- Add a durable prevention/detection control and a regression check. A manual
  cleanup alone is not closure.

### 5. Recover

Recover each affected lane independently:

1. Identify the exact 40-character source SHA.
2. Require the root `cas-ci-gate` and, where applicable,
   `cas-postgres-live-gate` for that exact SHA.
3. Deploy through the normal controlled path and record the deploy ID.
4. Run health, authorization, feature, persistence, and integrity smokes.
5. For Evidence Packets, report payload digest, append-only hash log, hash
   chain, external anchor, object re-read, and retention as separate checks.
6. Scale or reopen customer access only after the Incident Commander records
   the recovery evidence and outstanding risk.

Passing health or CI is deployment evidence, not customer-production `ACCEPT`.

### 6. Decide notifications

The Privacy/Legal Advisor owns the notification conclusion. The technical team
supplies facts and does not invent legal clearance or fixed deadlines.

Record these gates even when the decision is `not required on current facts`:

1. Was customer, employee, authentication, payment, or regulated data
   accessed, altered, lost, unavailable, or disclosed?
2. Which tenants, contracts, vendor terms, insurance conditions, and
   jurisdictions apply?
3. Do the facts start a customer, authority, insurer, vendor, or
   law-enforcement notice clock while the investigation remains open?
4. Does the message distinguish confirmed facts, inference, unknowns,
   containment, requested customer action, and the next update time?
5. Who approved the decision, at what UTC time, from which source material,
   and when will it be reviewed again?

Do not say “no breach” merely because compromise is not yet established. Use
`no evidence of compromise found in the reviewed sources as of <UTC>` and name
the sources and limitations.

### 7. Close and learn

Closure requires:

- containment and recovery evidence for every affected provider;
- notification decision recorded by the assigned owner;
- customer impact and evidence-integrity claims resolved or explicitly handed
  to an open problem owner;
- postmortem with facts/inferences/unknowns separated;
- corrective actions with owners, due dates, tests, and closure approvers;
- credentials and recovery factors absent from the record;
- a tabletop or live re-test demonstrating the new controls.

An incident may be operationally stable while remaining `OPEN` for an audit,
notification, MFA, hook invalidation, or WORM recovery action.

## Credential-exposure playbooks

### RunPod

Contain:

1. Rotate the worker credential in the RunPod Secret and every authorized
   caller. Never print it or pass it as a command-line argument.
2. Reset/restart the pod so the secret is applied.
3. Prove a request without `X-Atlas-Worker-Token` returns HTTP `401` and a
   request using the currently deployed secret succeeds.
4. If a RunPod API key or SSH authority may be exposed, revoke it and review
   account activity, pods, templates, secrets, SSH keys, and network changes.

Recover:

- require `REAL_PYTHIA_WEIGHTS_LOADED`, the intended model ID,
  `model_loaded=true`, `fake_runtime_env=false`, and the strict worker suite;
- remove the old value from RunPod and all Render callers;
- have the account owner enable RunPod MFA personally. Record only that MFA is
  enabled and the verification time—never the factor or recovery codes.

### Render

Contain:

1. Rotate affected service environment credentials and redeploy every caller.
2. Regenerate an exposed service deploy hook and invalidate the prior hook.
   Record the provider action ID/time, never the full hook URL.
3. Request server-side Blueprint sync-hook rotation. Until old-hook rejection
   is evidenced, keep the item `pending`, keep Blueprint Auto Sync disabled,
   use dashboard **Manual Sync** only, and inspect Blueprint sync history.
4. Rotate a Render API key/session if it may be exposed and inspect members,
   environment changes, deploys, services, and Blueprint actions.

Recover:

- require exact-SHA CI before any production deploy;
- verify the current worker secret succeeds and the superseded secret is no
  longer stored;
- reconfirm Blueprint Auto Sync is `No` and service
  `autoDeployTrigger: checksPass` remains active.

### AWS

Contain:

1. Disable/delete the affected application IAM access key. Do not create or
   deploy a root access key.
2. Review CloudTrail, the IAM credential report, S3 data events where enabled,
   bucket policy/versioning/Object Lock changes, and access to the affected
   prefix.
3. Restore IAM administration through the approved account recovery path. Root
   password and MFA entry remain a personal account-owner action.
4. Create a new least-privilege `cas-harness-render-production` application key
   and deliver it directly into Render's secret store.

Recover:

- require STS `GetCallerIdentity` and least-privilege policy simulation;
- issue a unique S3 Object Lock write, re-read it, and verify active retention;
- run a new hosted audit and require `/verify overall: all_match`;
- keep production WORM `OPEN` while any external-anchor check is
  `partial_mismatch`, unavailable, or unverified.

An AWS `InvalidClientTokenId` or S3 `InvalidAccessKeyId` proves the configured
authority is invalid. It does not, by itself, prove why or establish
unauthorized use.

### GitHub

Contain:

1. Revoke affected PATs, GitHub App tokens, deploy keys, Actions secrets, or
   sessions; rotate downstream copies.
2. Review repository/organization audit logs, workflow runs, environments,
   hooks, collaborators, deploy keys, refs, releases, and secret changes.
3. Preserve suspicious commits and workflow artifacts by ID and digest. Do not
   rewrite history during evidence collection.

Recover:

- require workflows under repository-root `.github/workflows`;
- require exact-SHA aggregate CI evidence and least-privilege workflow
  permissions;
- verify deployment-environment controls and branch/ruleset enforcement where
  the current repository plan supports them.

### Vercel

Contain:

1. Revoke affected team/user tokens, sessions, deploy hooks, integrations, and
   environment values, then rotate upstream credentials they could access.
2. Review team audit logs, project members, domains, deployments, environment
   changes, integrations, and Git connections.
3. Inspect build output, client bundles, source maps, and browser-visible
   configuration for secret or hook leakage.

Recover:

- redeploy from an exact green Git commit;
- verify production domains, rewrites, headers, and the intended account/API
  dark-or-enabled posture;
- keep preview and production credentials separated.

## WORM preservation versus secret redaction

WORM preserves evidence; it is not a safe secret vault.

Never put these into WORM, Git, tickets, screenshots, chat, or incident JSON:
raw passwords, tokens, API/access keys, session cookies, recovery codes,
private keys, seed phrases, or complete deploy/sync-hook URLs.

Preserve instead:

- provider event IDs and audit-log export digests;
- non-secret credential version IDs or masked provider identifiers when safe;
- pod/service/deploy/sync/workflow IDs;
- exact commit SHAs, timestamps, status codes, response classes, and artifact
  SHA-256 digests;
- a statement that a secret was rotated and that the old authority was
  rejected, without including either value.

If secret material was already written into an immutable object:

1. rotate/revoke it immediately;
2. restrict access to the object and record its bucket/key/version or artifact
   ID without copying the secret;
3. retain the original evidence where the retention policy requires it;
4. add a redaction/access manifest pointing to the original;
5. obtain the retention/privacy decision owner before any Object Lock
   `GOVERNANCE` bypass, deletion, or legal-hold change.

Do not silently replace historical evidence. Do not claim WORM if retention is
absent, expired, or not re-read and verified.

## Evidence checklist

- Incident ID, UTC times, severity changes, roles, and decisions.
- Exact 40-character Git SHA and required workflow run URLs.
- Provider account/project/service/pod/deploy/sync/event IDs.
- Audit-log source, query window, export time, digest, and retention limit.
- Credential version/rotation/revocation event—not the credential value.
- Old-authority rejection and new-authority success results.
- Health, auth, feature, persistence, and multi-replica results as separate
  facts.
- Evidence Packet payload/hash-log/hash-chain/external-anchor/retention results
  as separate facts.
- Customer/tenant/data impact and notification decision, including unknowns.
- Corrective actions, owners, due dates, tests, and closure approver.

Use
[`incident_postmortem_template.md`](incident_postmortem_template.md) after
stabilization. The 2026-07-13 non-secret record/tabletop is under
`docs/working/incident_response/` and remains `OPEN` while its named actions
are pending.
