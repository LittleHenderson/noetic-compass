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

Both Blueprint Settings pages must show **Auto Sync: No**. Both stable service
IDs must show their policy-bound branch, service type, repository, region, and
`autoDeployTrigger: checksPass`; production must also keep
`healthCheckPath: /health`. The required aggregate GitHub checks are:

- `cas-ci-gate`
- `cas-postgres-live-gate`

The account canary intentionally has two commit identities. The Blueprint file
comes from `master`, while its service source comes from the release branch.
Never collapse those identities into a single ambiguous `commit_sha` field.

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

The command must report `autoSync=false` for both Blueprint IDs and a service
control PASS for `srv-d82ph683kofs73d210e0` and
`srv-d9akoolaeets73bp3e7g`. It reads each stable service through Render's
authenticated service endpoint and fails closed on branch, service type,
repository, region, deploy-trigger, or production health-path drift. It
suppresses Render error response bodies and never prints the key or raw API
payload. Transient transport failures and Render HTTP `408`, `429`, `500`,
`502`, `503`, and `504` responses receive at most three 30-second attempts
with 2- and 5-second backoffs; all four live reads share one 210-second
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
  "blueprint_path": "<render.yaml or render.canary.yaml>",
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
