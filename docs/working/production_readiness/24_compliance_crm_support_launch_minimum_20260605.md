# CAS Harness Compliance/CRM/Support Launch Minimum - 2026-06-05

Status: Agent 6 docs-only package. Not published. No legal advice.

Scope: invite-only, comped NDA beta launch minimum. This package does not clear paid/public launch, does not edit backend or frontend code, and does not replace founder or qualified-counsel review.

## Sources Inspected

- Canonical TODO: `docs/working/cas_harness_production_todo.md`.
- Existing compliance drafts: `docs/working/compliance_drafts_20260604/`.
- Production-readiness track: `docs/working/production_readiness/`.
- CRM implementation on `master`: `api/routes/crm.py`, `api/services/crm/*`, `api/config.py`, `api/main.py`, `infra/render.yaml`.
- Branch posture: current checkout is `wave5.5/harness-launch-declutter`, but launch CRM routes and proven Render posture live on `master` / `launch/scoped-beta`. Do not treat the current stale branch as the launch source without consolidation.

## Launch Minimum Decision

CAS Harness can only use these materials for an invite-only beta after founder and qualified-counsel sign-off. The honest beta posture is:

- Experimental product, no charge, invite-only, NDA-backed.
- Evidence Packets are audit records, not certifications.
- `ACCEPT` is not a certification or guarantee.
- No standing production `ACCEPT` may be claimed unless proof gates pass. Open gates remain `FLAG_FOR_HUMAN_REVIEW`, `OPEN`, `unavailable`, or `present` exactly as emitted.
- WORM/Object Lock language must say S3 Object Lock `GOVERNANCE`, approximately 30-day rolling retention, tamper-evident on re-verify, operator-overridable. Do not say permanent, immutable, or Compliance mode.
- Durability claim is single-instance paid-disk restart survival only. Do not claim multi-instance, failover, geographic redundancy, host-loss durability, SOC 2, ISO, or certification.

## Documents To Approve Before External Use

| Requirement | Current draft | Launch-minimum action |
|---|---|---|
| Privacy notice | `docs/working/compliance_drafts_20260604/privacy_policy_DRAFT.md` | Founder + counsel review; remove draft markers only after approval; confirm lawful basis, transfer language, and contact address. |
| Beta agreement / terms | `docs/working/compliance_drafts_20260604/beta_terms_DRAFT.md` | Founder + counsel review; finalize warranty, liability cap, governing law, venue, NDA reference, and no-charge beta scope. |
| Retention/WORM disclosure | `docs/working/compliance_drafts_20260604/data_retention_and_worm_disclosure_DRAFT.md` | Must preserve Governance-mode, 30-day rolling, tamper-evident/operator-overridable language. |
| Rights request process | `docs/working/compliance_drafts_20260604/rights_request_process_DRAFT.md` | Confirm request mailbox, identity-verification standard, statutory response timelines, deletion handling for Object Lock Governance anchors. |
| Subprocessor list | `docs/working/compliance_drafts_20260604/subprocessors_DRAFT.md` | Confirm Render, AWS S3 region/bucket, Vercel use, Airtable activation status, and any LLM provider used in BYOK flows. |
| No-certification statement | `docs/working/compliance_drafts_20260604/no_certification_statement_DRAFT.md` | Keep public-facing language: no SOC 2, no ISO/IEC 42001, no certification, no "makes you compliant" claim. |
| Security contact | `docs/working/compliance_drafts_20260604/security_contact_DRAFT.md` | Founder must create/confirm mailbox and optional PGP key before publication. |

Missing before external use: a founder-approved public support contact line. Minimal beta wording can be a one-sentence support clause in the beta agreement and app/footer copy after the mailbox exists.

## Support And Contact Path

Minimum human support path for invite-only beta:

1. Public/beta support mailbox: founder to confirm, for example `support@noeticcompass.com` or `hello@noeticcompass.com`.
2. Security/privacy mailbox: founder to confirm/create `security@noeticcompass.com` before using the security-contact draft.
3. Data-rights requests: route to the same security/privacy mailbox during beta unless counsel selects a separate `privacy@noeticcompass.com`.
4. Operational owner: founder or named operator manually triages all support, security, privacy, and lead emails during beta.
5. Response targets: support triage within about 2 business days; security/privacy acknowledgment within about 5 business days, matching the draft security and rights-request posture.

The Gemini Guide can help users understand the product, but it is not legal support, security support, a rights-request intake channel, or a substitute for a human support mailbox.

## CRM Activation Requirements

The CRM code on `master` has the correct honesty boundary:

- Public capture endpoint: `POST /api/crm/public/leads`.
- Authenticated sales endpoints: `GET /api/crm/leads`, `GET /api/crm/leads/{lead_id}`, `PATCH /api/crm/leads/{lead_id}/pipeline-status`.
- Lead states distinguish local capture from external CRM landing: `captured`, `sync_pending`, `synced`, `sync_failed`.
- `synced` is only allowed when a real provider returns a real `external_id`.
- The implemented external provider is Airtable. HubSpot is declared but not implemented and must not be configured for launch.

Required Render env before CRM can be called active:

```text
NC_CRM_LEAD_STORE_PATH=/var/data/leads.jsonl
NC_CRM_PROVIDER=airtable
NC_AIRTABLE_TOKEN=<dashboard secret>
NC_AIRTABLE_BASE_ID=<dashboard secret>
NC_AIRTABLE_TABLE_NAME=<dashboard secret>
NC_AIRTABLE_API_BASE_URL=https://api.airtable.com/v0
NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX=5
NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS=3600
```

Required Airtable fields:

- `Lead ID`
- `Email`
- `Name`
- `Organization`
- `Message`
- `Interest`
- `Source`
- `Trace ID`
- `Pipeline Status`
- `Schema Version`
- `Metadata JSON`

CRM is launch-active only after all proof items pass:

- Render startup logs show CRM store `JsonlFileLeadStore` and provider `airtable`.
- Public hosted lead capture returns `captured: true`, `sync_status: synced`, and `synced: true`.
- Authenticated readback of that lead returns a non-empty `external_id`.
- Airtable UI/API shows the same external record and matching `Lead ID`.
- Authenticated pipeline status update moves the lead through `contacted` or `qualified` without changing `sync_status`.
- A restart/redeploy preserves the lead in `/var/data/leads.jsonl`.
- Honeypot rejection returns 400 and rate-limit posture is documented.

Still not production-complete after the above: no sales dashboard, no task/follow-up scheduler, no notes timeline, no owner assignment, no NDA flag, no deal-value workflow, and no WAF/captcha/edge rate-limit proof.

## Hosted Smoke Commands

Run from `noetic-compass-scaffold/noetic-compass` on a `master`-based launch checkout after Render env is set. These commands are PowerShell. Do not paste secrets into docs or logs.

Set common variables:

```powershell
$api = "https://noetic-compass-api.onrender.com"
$token = $env:NC_DASHBOARD_BEARER_TOKEN
if (-not $token) { throw "Set NC_DASHBOARD_BEARER_TOKEN to a scoped beta bearer token before authed smokes." }
$headers = @{ Authorization = "Bearer $token" }
```

Health and readiness:

```powershell
Invoke-RestMethod -Uri "$api/health" | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$api/health/ready" | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri "$api/api/cas-harness/live-worker/health" | ConvertTo-Json -Depth 5
```

Expected launch-minimum result:

- `/health` returns `status: ok`.
- `/health/ready` is healthy for configured subsystems.
- live worker health must say real weights only when `reachable: true` and `real_weights: true`; otherwise worker route remains open.

CRM Airtable sync proof:

```powershell
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$leadEmail = "launch-smoke+$stamp@example.com"
$leadBody = @{
  email = $leadEmail
  name = "Launch Smoke $stamp"
  organization = "Noetic Compass"
  interest = "cas_harness_beta"
  source = "agent6_launch_smoke"
  message = "CRM Airtable sync proof for CAS Harness beta launch readiness."
  metadata = @{
    smoke_run = $stamp
    purpose = "agent6_crm_activation"
  }
} | ConvertTo-Json -Depth 5

$capture = Invoke-RestMethod -Method Post -Uri "$api/api/crm/public/leads" -ContentType "application/json" -Body $leadBody
$capture | ConvertTo-Json -Depth 5
if ($capture.sync_status -ne "synced" -or -not $capture.synced) {
  throw "CRM is not active: expected sync_status=synced with synced=true."
}

$lead = Invoke-RestMethod -Uri "$api/api/crm/leads/$($capture.lead_id)" -Headers $headers
$lead | ConvertTo-Json -Depth 8
if (-not $lead.external_id) {
  throw "CRM is not active: authenticated readback has no external_id."
}

$updateBody = @{ pipeline_status = "contacted" } | ConvertTo-Json -Compress
$updated = Invoke-RestMethod -Method Patch -Uri "$api/api/crm/leads/$($capture.lead_id)/pipeline-status" -Headers $headers -ContentType "application/json" -Body $updateBody
$updated | ConvertTo-Json -Depth 8
if ($updated.pipeline_status -ne "contacted") {
  throw "CRM pipeline smoke failed: expected pipeline_status=contacted."
}
```

CRM anti-abuse honeypot proof:

```powershell
$botBody = @{
  email = "bot+$stamp@example.com"
  source = "agent6_honeypot_smoke"
  website = "https://spam.example"
} | ConvertTo-Json -Compress

try {
  Invoke-RestMethod -Method Post -Uri "$api/api/crm/public/leads" -ContentType "application/json" -Body $botBody
  throw "Expected honeypot submission to be rejected."
} catch {
  $status = $_.Exception.Response.StatusCode.value__
  if ($status -ne 400) { throw "Expected honeypot HTTP 400, got $status." }
  "Honeypot rejection passed with HTTP $status"
}
```

WORM/Object Lock smoke:

```powershell
python scripts/verify_evidence_anchor_deployed.py `
  --base-url $api `
  --bearer-token $token `
  --require-anchor-mode s3 `
  --require-object-lock
```

Expected result:

- Script exits 0.
- Packet anchor mode is `s3`.
- `/verify` returns a matching anchor.
- Object Lock retention is `present` and future-dated.
- Do not call this immutable or permanent; the beta disclosure remains Governance-mode and operator-overridable.

Known Stage 9 evidence honesty spot-check:

```powershell
Invoke-RestMethod -Uri "$api/evidence/pythia-160m-stage9-40e-readout-20260531" -Headers $headers | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri "$api/evidence/pythia-160m-stage9-40e-readout-20260531/verify" -Headers $headers | ConvertTo-Json -Depth 10
```

Expected result:

- Verdict remains `FLAG_FOR_HUMAN_REVIEW`.
- WORM retention can be `present`; it does not upgrade the verdict to `ACCEPT`.

Support contact smoke:

```text
1. Send a real email to the founder-approved support mailbox.
2. Send a real email to the founder-approved security/privacy mailbox.
3. Confirm receipt in the mailbox.
4. Record the test contact as a CRM lead or internal support record.
5. Confirm the public beta docs and app entrypoint show the same contact addresses.
```

## Remaining External-Signoff Blockers

- Founder must approve final support/security/privacy contact addresses and create the mailboxes.
- Qualified counsel must review the privacy policy, beta terms, retention/WORM disclosure, rights-request process, subprocessors, no-certification statement, and security disclosure.
- Airtable credentials must be configured in Render and a hosted lead must prove `sync_status: synced` plus a real `external_id`.
- The hosted CAS Harness product path must expose the approved support/contact route; a local `localhost` link does not count.
- Edge-level hostile-traffic controls for public lead capture remain incomplete unless explicitly deferred for invite-only beta.
- Paid/public launch still needs real accounts, sessions/revocation, RBAC, tenant isolation, quotas/billing, and support operations beyond this beta minimum.

