# CAS Harness customer-production acceptance

This runbook governs the public CAS Harness release decision. The contract is
`.production/customer-production-acceptance.json`, trusted public keys are in
`.production/customer-production-trusted-issuers.json`, and the fail-closed
verifier is `scripts/verify_customer_production_acceptance.py`.

The checked-in contract is deliberately `OPEN`. The checked-in issuer registry
contains only the narrowly scoped root-CI signing issuer; no issuer is trusted
for any other gate. Contract CI can prove that this truthful OPEN state is well
formed; it cannot turn OPEN into ACCEPT. A real ACCEPT requires a separately
supplied evidence bundle, exact deployment bindings, and either signed receipts
from an explicitly onboarded issuer or live verification of an allowlisted
production endpoint.

## Status and authority contract

| Exact value | Meaning |
|---|---|
| `OPEN` | Evidence is absent, stale, invalid, or awaiting release approval. |
| `present` | A gate has current authoritative evidence. This is not a verdict. |
| `ACCEPT` | The final public-product decision, or a separately scoped research verdict. |

A research `ACCEPT` never implies customer-production `ACCEPT`.
`FLAG_FOR_HUMAN_REVIEW` is never rewritten as `ACCEPT`, and WORM retention
never upgrades a model verdict. The verifier rejects reuse of the scoped
research artifact as production evidence.

Production authority is limited to these exact lanes:

- repository `LittleHenderson/noetic-compass`;
- app origin `https://atlas.noeticcompass.com`;
- API origin `https://noetic-compass-api.onrender.com`;
- Render service `srv-d82ph683kofs73d210e0` / `noetic-compass-api` on
  protected `master`;
- the externally supplied protected `master` SHA and public Render deploy ID;
- the pinned GitHub repository, workflow, job, run, and GitHub Actions App
  identities encoded by the verifier.

The private accounts canary, its service, its branch, and any private-canary
environment are forbidden from satisfying a public gate.

## Evidence authority

Each `present` gate points to one dereferenceable document and its SHA-256:

```json
{
  "uri": "repo://receipts/runtime_worm.json",
  "sha256": "<sha256 of the receipt bytes>",
  "authority": {
    "mode": "signed_receipt",
    "issuer": "<pinned issuer>",
    "key_id": "<pinned key id>"
  }
}
```

`repo://` paths are resolved beneath `--evidence-root`; absolute paths and
path traversal are rejected. The verifier reads the actual bytes, verifies the
reference hash, rejects duplicate JSON keys, and then verifies the receipt's
RS256 signature against the repository's trusted-issuer registry.

A signed receipt binds all of the following under its signature:

- schema, issuer, key ID, gate, and `public-production` environment;
- repository, exact master SHA, and exact public deploy ID;
- issue and expiry timestamps;
- allowlisted HTTPS subject URI and subject SHA-256;
- the complete gate evidence payload.

The signature input is the receipt without `signature_base64url`, serialized
as UTF-8 JSON with keys sorted, no insignificant whitespace, and non-ASCII
characters preserved. Private keys belong in KMS or a signing service and must
never be committed, downloaded with the bundle, or printed in logs.

Alternatively, a reference may use `authority.mode: live_https`. This mode is
valid only when the verifier is run with `--live`; each live issuer is bound to
one exact gate endpoint, not merely to a set of origins. The verifier rejects
issuer/endpoint crossovers before any request, blocks redirects outside the
bound origin, limits response size, hashes the returned bytes, and validates
the returned evidence. Merely writing an HTTPS URL into a manifest is
self-attestation and does not count. The aggregated root-CI gate deliberately
has no live endpoint because neither the GitHub nor Render API returns the
complete gate schema at one fixed URL; use a signed receipt for that gate.

### Production JSON authority plane

The production API exposes only these exact, query-free anonymous `GET`
documents for `live_https` verification:

| Gate | Exact path |
|---|---|
| `runtime_worm` | `/internal/acceptance/runtime-worm` |
| `hosted_customer_journey` | `/internal/acceptance/customer-journey` |
| `accounts_billing` | `/internal/acceptance/accounts-billing` |
| `legal_publication_approval` | `/internal/acceptance/legal-publication-approval` |
| `support_crm` | `/internal/acceptance/support-crm` |
| `incident_tabletop` | `/internal/acceptance/incident-tabletop` |
| `alert_delivery` | `/internal/acceptance/alert-delivery` |
| `claim_honesty` | `/internal/acceptance/claim-honesty` |
| `release_decision` | `/internal/acceptance/release-decision` |

The legal endpoint is JSON from the API; `https://cascompass.ai/legal` remains
the human-facing legal page and is never JSON-parsed as authority. The auth and
rate-limit middleware share the same exact path map. `POST`, `PUT`, `PATCH`,
`DELETE`, `HEAD`, a query string, a child path, or any future sibling below
`/internal/acceptance` does not inherit anonymous access. `root_ci_protected_deploy`
is intentionally absent and remains signed-receipt-only.

The route never calculates a successful gate from current application state.
It reads a content-addressed immutable revision selected by a version-checked
head in the existing `StateStore`. The same service works over SQLite or
Postgres. When the existing immutable Evidence Packet backend is configured,
new revisions can store the exact canonical JSON bytes in S3 Object Lock and
the StateStore keeps only the exact-version pointer; a WORM-backed head never
falls back to mutable inline bytes. The revision retains the authenticated
Object-Lock verification receipt; every WORM read or reuse revalidates its
attestation, exact version, lock mode, configured retention, unexpired deadline,
backend readiness, and bytes. Policy drift or an expired receipt fails closed.
Every read rechecks the head/revision
identity, byte length, SHA-256, canonical JSON, exact gate schema, exact
authority URL, freshness, public-production binding, and secret/PII scans.

Head schema v3 also binds the exact SHA-256 and record ID of an append-only
operation record. The operation is content-addressed and written before the
head compare-and-swap; an interrupted prewrite is an unbound harmless intent,
while a serving head without its exact operation fails `503`. Each operation
records the action, previous and next version/hash/active state, timestamp,
reason enum, authorization artifact URI/SHA-256, and predecessor operation ID.
The predecessor binding preserves publish/deactivate/reactivate history instead
of letting a later head overwrite the audit trail.

There is deliberately no HTTP publish or approval route. A separately
authenticated operational collector must obtain independent receipts and any
human approvals, prepare one canonical gate document, then call the persistence
service with the current head version and previous evidence hash. The service
applies the matching single-document gate validator; only the final canonical
manifest verifier can enforce cross-gate hashes, release ordering, and the full
`ACCEPT` contract. The service does not create missing approval rows, infer
successful values, or turn an unsigned draft into authority. Deploying this
read plane creates no evidence records and closes no gate by itself.

Response behavior is fail-closed and non-cacheable:

- `200 application/json` only for the exact active, revalidated canonical bytes;
- `404` when no active revision exists;
- `503` when durable state, an immutable blob, or validation is unavailable;
- no provider error, storage pointer, Object-Lock version ID, secret, or PII is
  copied into an error response.

### Publish one verified authority document

`scripts.publish_customer_production_acceptance_authority` is the operational
write command. Its `validate` action is local and opens no database or object
store connection. Its `head`, `publish`, and `deactivate` actions fail unless
they are running inside the exact public Render API service/repository/branch at
the expected protected-master commit, with non-debug mode, the shared state
ledger, and Postgres configured.

From `noetic-compass-scaffold/noetic-compass`, validate and compute the exact
canonical document hash first:

```powershell
python -m scripts.publish_customer_production_acceptance_authority validate `
  --gate claim_honesty `
  --evidence <independently-assembled-evidence.json> `
  --expected-master-head <40-character-protected-master-sha> `
  --expected-deploy-id <public-render-deploy-id>
```

Transfer only the validated, secret-free evidence file through an authenticated
Render Shell/SSH channel to a mode-`0600` transient path. Do not put it in an
environment variable, image layer, repository commit, or command argument.
Inside the Linux Render Shell, read the current compare-and-swap head version,
active state, exact previous evidence hash, and bound operation ID/hash:

```bash
python -m scripts.publish_customer_production_acceptance_authority head \
  --gate claim_honesty \
  --expected-master-head <40-character-protected-master-sha>
```

Only after independently checking every required approval and receipt, publish
the same document. For a replacement or reactivation, also pass the exact
`evidence_sha256` returned by `head` as
`--expected-previous-evidence-sha256`; omit it only when `head_version` is `0`:

```bash
python -m scripts.publish_customer_production_acceptance_authority publish \
  --gate claim_honesty \
  --evidence /tmp/independently-assembled-evidence.json \
  --expected-master-head <40-character-protected-master-sha> \
  --expected-deploy-id <public-render-deploy-id> \
  --expected-evidence-sha256 <canonical-sha256-from-validate> \
  --expected-head-version <version-from-head> \
  --expected-previous-evidence-sha256 <hash-from-head-if-version-is-nonzero> \
  --authorization-artifact-uri <clean-api-or-landing-https-uri> \
  --authorization-artifact-sha256 <sha256-of-independent-authorization-artifact> \
  --operation-reason authorized_publication
```

If an approval is withdrawn or evidence is suspected, immediately tombstone the
exact active head. This retains its content-addressed/WORM revision for audit but
makes the public route return `404`:

```bash
python -m scripts.publish_customer_production_acceptance_authority deactivate \
  --gate claim_honesty \
  --expected-master-head <40-character-protected-master-sha> \
  --expected-evidence-sha256 <exact-active-hash-from-head> \
  --expected-head-version <version-from-head> \
  --authorization-artifact-uri <clean-api-or-landing-incident-or-session-record-uri> \
  --authorization-artifact-sha256 <sha256-of-that-record> \
  --operation-reason <incident_response|approval_withdrawn|evidence_expired|operator_safety_action>
```

Delete the transient file after the exact public `GET` body is read back and its
SHA-256 matches the local canonical hash. A command result with
`publication_state: unknown` is not success: run `head`, inspect the exact hash
and active bit, then either verify the public bytes or deactivate them.

The command applies the serving API's exact schema, freshness, secret/PII, and
gate-semantic checks before connecting to production. Publication uses the
StateStore compare-and-swap head, then reloads and byte-compares the active
revision and operation binding before reporting success. When the immutable Evidence Packet backend
is enabled, it uses that same verified Object-Lock backend and never falls back
to inline bytes. It does not collect evidence, create approvals, sign receipts,
dereference an approval artifact, or change the acceptance manifest. Its Render
runtime checks independently bind the service, repository, branch, and commit;
Render exposes no documented runtime deploy-ID variable, so the operator-supplied
deploy ID still requires provider readback and the final root-CI/protected-deploy
receipt. The final manifest verifier remains mandatory for cross-gate hashes,
product-status alignment, release timing, and authoritative `ACCEPT`.

The authorization URI/hash is an append-only audit pointer, not authentication
by itself: this command deliberately does not dereference it or manufacture an
approval. Publish access therefore remains restricted to the production Render
service's least-privilege root-operator role with provider MFA, protected
environment controls, and retained Render session/audit event evidence. The
pointed artifact must independently prove the human/provider authorization
required by the gate. Deactivation is the emergency fail-closed action: it
requires a reason and incident/session artifact pointer for audit, but never a
second approval or a live artifact fetch before tombstoning an active head.

### Onboard a signing issuer

Add only the issuer's public RSA key to
`.production/customer-production-trusted-issuers.json`. Each registry entry
must contain exactly:

- `issuer`, `key_id`, and `algorithm: RS256`;
- an RSA-2048-or-stronger `n_base64url` and exponent `e: 65537`;
- non-empty `allowed_subjects`, where every entry is one exact `{gate, uri}`
  pair;
- `valid_from_utc` and `valid_until_utc` key-validity bounds.

No Cartesian product of independent gate and origin lists is accepted. Use the
smallest exact subject grants possible. Key rotation is a reviewed repository
change. Until a valid key is onboarded, signed evidence cannot produce ACCEPT;
this is intentional.

### Produce the root-CI protected-deploy receipt

The root-CI collector is intentionally local and unsigned. It needs a GitHub
credential that can read branch protection plus `RENDER_API_KEY`; the default
Actions `GITHUB_TOKEN` does not have GitHub Administration read permission.
Never move a personal administration token into Actions or weaken the branch
protection proof. Run the collector from the exact checked-out protected
`master` SHA and bind one explicit Render deploy ID:

```powershell
$env:GITHUB_TOKEN = gh auth token
python scripts/collect_root_ci_protected_deploy_facts.py `
  --expected-master-head <40-character-protected-master-sha> `
  --expected-deploy-id <public-render-deploy-id> `
  --deploy-wait-seconds 600 `
  --output root-ci-protected-deploy.json
```

The collector queries only `/deploys/<expected-deploy-id>` while waiting; it
never substitutes the latest deploy. It fails closed on repository, workflow,
job, check, GitHub App, branch-protection, Render service, commit, trigger,
health, freshness, pagination, or local workflow-layout drift. HTTP reads are
bounded, redirects are forbidden, and response bodies and credentials are not
printed on errors. Exit zero produces only a canonical unsigned v2 facts
document; it does not create authority, mark a gate `present`, or dispatch
`ACCEPT`.

Publish those exact bytes as the stable release asset
`customer-production-evidence/root-ci-protected-deploy.json`. Then manually
dispatch `Customer Production Evidence` from that same protected `master` SHA
with the exact SHA and deploy ID. The protected `customer-production`
environment workflow downloads the asset, hashes and strict-parses it, runs
the hostile verifier/producer tests, binds the expected SHA and deploy ID, and
signs a receipt with `CUSTOMER_PRODUCTION_SIGNING_KEY_PEM`. The private key is
available only to the signing step and is never logged. The uploaded artifact
contains the receipt and the subject checksum; the checked-in manifest remains
`OPEN`, and the workflow never dispatches final `ACCEPT`.

```powershell
gh release upload customer-production-evidence `
  'root-ci-protected-deploy.json#Unsigned root CI protected deploy source facts' `
  --repo LittleHenderson/noetic-compass `
  --clobber
```

## Commands

Run from the repository root.

Validate the checked-in OPEN contract:

```powershell
python scripts/verify_customer_production_acceptance.py --validate-only
```

Emit its machine-readable report:

```powershell
python scripts/verify_customer_production_acceptance.py --validate-only --json
```

Verify a candidate public deployment from a downloaded evidence bundle:

```powershell
python scripts/verify_customer_production_acceptance.py `
  --manifest .customer-production-evidence/customer-production-acceptance.json `
  --evidence-root .customer-production-evidence `
  --expected-master-head <40-character-protected-master-sha> `
  --expected-deploy-id <public-render-deploy-id> `
  --live `
  --json `
  --report-path customer-production-archive/customer-production-acceptance-report.json `
  --sanitized-bundle-path customer-production-archive/sanitized-evidence-bundle
```

The normal command exits `0` only for an authoritative ACCEPT. It exits `1`
for either OPEN or INVALID; the JSON `result` distinguishes them. `--now` is
allowed only with `--validate-only` for deterministic tests. It is forbidden
for a normal ACCEPT so production verification always uses the real clock.
Conversely, `--sanitized-bundle-path` is forbidden with `--validate-only`, so a
test-time validation cannot emit an artifact that resembles a production
acceptance archive.

### Collect an unsigned claim-honesty draft

The machine collector reads exactly the six public URLs pinned by the
acceptance verifier. It performs credential-free `GET` requests, refuses
redirects, query strings, fragments, and embedded credentials, and hashes the
exact bounded response bytes:

```powershell
python scripts/collect_claim_honesty_evidence.py `
  --pretty `
  --output .customer-production-evidence/claim-honesty-machine-draft.json
```

The report records the exact HTTP status and raw-byte SHA-256 for every
bounded response. It scans visible UTF-8 text from the body returned by the
same exact route and applies versioned deterministic checks for misleading
production/verdict language, unsupported compliance and universal claims,
unsupported patent language, and noncanonical status vocabulary. Matched text
is not copied into the report; only the rule, offsets, and matched-text digest
are recorded.

The collector does not execute JavaScript. A client-routed application shell,
insufficient visible text, or a primary heading that does not identify the
requested route is a coverage failure. In particular, an HTTP `200` page
whose application renders or routes to a generic login screen cannot count as
a published Legal, Privacy, or Terms page. Aliases such as
`https://noeticcompass.com/legal` are not substitutes for the six URLs pinned
by this contract.

Atlas builds publish visible, route-specific HTML inside the application mount
for exactly `/` and `/audit-console`. The mount must carry both the exact
`data-cas-prerendered-route` value and the pinned
`data-cas-prerender-schema="cas_claim_surface.v1"` value. The collector accepts
that exception only when the requested route, marker, visible application-mount
text, and route-specific primary heading all agree. An unmarked application
shell, a mismatched marker, generic fallback content, or content placed only in
`hidden` or `noscript` elements remains a coverage failure. The browser hydrates
the same marked HTML before replacing it with the interactive application; all
other SPA routes use the neutral `spa.html` fallback rather than inheriting a
claim surface from `/`.

Before publishing Atlas, run its deterministic claim-surface checks and build:

```powershell
cd noetic-compass-scaffold/noetic-compass/atlas-viewer
npm run test:claim-surfaces
npm run build
```

The postbuild step must emit `dist/index.html`,
`dist/audit-console/index.html`, and the neutral `dist/spa.html`. These files
are build artifacts only; successful local generation does not establish that
the same bytes are live or change any acceptance status.

The Atlas Render static site is dashboard-managed. Deploy the new static build
under the old `/*` to `/index.html` rule first and wait for that exact deploy
to become LIVE. Before changing routes, verify that `/spa.html` is unmarked and
that `/audit-console/index.html` carries the exact audit marker. Re-read
provider state and fail closed unless it still has exactly the single current
Rewrite from `/*` to `/index.html` and production
`VITE_ATLAS_API_BASE_URL` is exactly
`https://noetic-compass-api.onrender.com/atlas`.

Only then replace the full route list, in order, with `/audit-console` to
`/audit-console/index.html`, `/audit-console/` to
`/audit-console/index.html`, and terminal `/*` to `/spa.html`. Immediately
smoke `/`, `/audit-console`, one unrelated BrowserRouter deep link, and the
absolute API path. If any smoke fails, restore the single old Rewrite from
`/*` to `/index.html` and keep claim coverage `OPEN`. If any precondition
differs, stop instead of overwriting provider state. The checked-in
`atlas-viewer/render-route-rules.json` records the exact precondition,
replacement, smoke paths, and rollback. This keeps unrelated paths neutral
without routing API calls through the static-site fallback.

Exit `0` means only that this deterministic machine scan found full static
route coverage and no configured findings. Exit `1` means the draft contains
coverage or claim blockers, and exit `2` means collection itself failed. Every
output remains an unsigned `OPEN` draft with no approval records or authority;
it can never promote a gate or final decision. Independent legal, product, and
research review plus the authoritative receipt path remain mandatory.

### Collect the operational-gate machine draft

Use the read-only operational collector to inventory the machine-visible facts
and exact remaining work for `hosted_customer_journey`, `support_crm`,
`incident_tabletop`, and `alert_delivery` together. Bind the scan to one exact
protected `master` SHA and public Render deploy. If a runtime-monitor failure
is being inspected, also pin its exact Actions run and deduplicated issue:

```powershell
$env:GITHUB_TOKEN = gh auth token
python scripts/collect_operational_acceptance_draft.py `
  --target-master-head <40-character-protected-master-sha> `
  --target-deploy-id <public-render-deploy-id> `
  --runtime-monitor-run-id <exact-run-id> `
  --alert-issue-number <exact-issue-number> `
  --pretty `
  --output .customer-production-evidence/operational-acceptance-machine-draft.json
```

The GitHub credential is used only for bounded readback from the pinned private
repository and is never written to the report. The collector performs no
customer, provider, account, issue, or CRM writes. It hashes exact response
bytes but does not copy response bodies, issue comments, operator identities,
or credentials into its output.

The report is always unsigned, non-authoritative, and `OPEN`. Route presence
does not count as a hosted journey, the checked-in incident record does not
count as closure, and a bot-authored GitHub issue does not count as primary
on-call delivery or human acknowledgement. A human-looking `ACK` or escalation
comment is recorded only as a hashed candidate; it remains unverified until an
assigned role and the required provider receipt are independently proven.

Exit `0` means only that the collector found every machine prerequisite it can
inspect. Exit `1` means one or more machine prerequisites are missing, and exit
`2` means the collection request itself was unsafe or invalid. Even exit `0`
cannot mark a manifest gate `present` or produce customer-production `ACCEPT`;
the active journey, support/CRM handling, incident/tabletop participants, alert
destinations, human acknowledgement, signed/live authority, and final release
decision remain separate evidence.

### Collect unsigned customer-readiness facts

The customer-readiness collector is a credential-free, read-only prerequisite
check for `hosted_customer_journey` and `accounts_billing`. It reads exactly
three pinned public-production JSON routes (`/health`, `/health/ready`, and
`/openapi.json`) plus the checked-out `render.yaml` and `api/config.py` source
files:

```powershell
python scripts/collect_customer_readiness_facts.py `
  --pretty `
  --output .customer-production-evidence/customer-readiness-machine-draft.json
```

The report hashes every bounded public response and both source files, records
observation timestamps, and separates deployed route capability from live
enablement. In particular, a route in OpenAPI proves only that code is
deployed. It does not prove that Postgres, accounts, quotas, the Evidence
Packet object store, anonymous shares, billing entitlements, or Stripe are
enabled or working. Dashboard-managed source slots prove only that a slot is
declared; they do not reveal whether its live value is configured.

The collector sends only credential-free `GET` requests and never calls the
account, audit, Evidence Packet, share, checkout, portal, webhook, or billing
entitlement routes. It therefore never creates an account, audit, share,
checkout, provider event, payment, approval, or authority record. A successful
collection remains an unsigned, non-authoritative `OPEN` draft and cannot mark
either gate `present` or dispatch `ACCEPT`.

Exit `1` means the public prerequisites were not established; this is the
expected result while a required fact is disabled, unavailable on the bounded
public surfaces, or still requires a real lifecycle receipt. Exit `2` means
the source contract or collection itself failed closed. Ordinary CI runs only
the collector's deterministic unit tests and performs no production network
requests.

## CI separation

Ordinary root CI runs the visibly named step
`Validate customer-production contract (OPEN permitted)` with
`--validate-only`. That step checks the contract and permits the truthful
checked-in OPEN state. It is not a production approval and is not aggregated
into a fake customer-production result.

Real acceptance runs only through the separate manual workflow
`.github/workflows/customer-production-accept.yml`. Dispatch it on `master`
with:

- the same-repository Actions run ID and exact artifact name containing the
  signed evidence bundle;
- the exact protected `master` SHA deployed publicly;
- the exact public Render deploy ID.

The workflow has no job-level condition that can turn a wrong repository or
branch into a green skipped job. Its first step fails unless the dispatch is in
the exact repository on protected `master`, the dispatch SHA equals the
externally supplied expected SHA, and the deploy ID has the required shape. It
then checks out that exact commit, downloads the supplied bundle, runs the
normal verifier (not `--validate-only`), and uses the `customer-production`
GitHub environment.

On ACCEPT, the verifier creates a sanitized archive containing only the exact
manifest bytes, dereferenced and validated evidence documents, trusted public
key registry, and a hash index. Unreferenced files from the downloaded artifact
are never copied. The workflow archives that sanitized bundle together with
the report; on failure it archives the report without promoting an unverified
bundle. Environment reviewers may govern execution, but their approval is not
a substitute for the signed release-decision receipt required by the manifest.

## Required gates

All nine gates must be `present`, current, and authoritative:

1. `runtime_worm`: public API readiness, real Pythia weights, exact deploy, and
   successful S3 Object Lock write/readback. WORM must be active at
   verification, configured for at least 31 days, and have at least 30 days
   remaining.
2. `root_ci_protected_deploy`: workflows only under repository-root
   `.github/workflows`, strict protected `master`, pinned successful GitHub
   workflow runs for the exact head and GitHub Actions App, plus exact public
   Render deploy metadata.
3. `hosted_customer_journey`: hosted tenant audit, terminal verdict, verified
   packet download, bound WORM receipt, read-only share lifecycle, and
   cross-tenant `404` checks.
4. `accounts_billing`: account lifecycle and isolation, durable quota and
   idempotency behavior, and live Stripe subscription/invoice/webhook/meter
   reconciliation using hashed provider identifiers only.
5. `legal_publication_approval`: live Legal, Privacy, and Terms pages with
   exact hashes, approved by legal, privacy, and product owners.
6. `support_crm`: real support-ticket persistence/routing/SLA/resolution and
   CRM lead persistence, deduplication, ownership, consent, and attribution.
7. `incident_tabletop`: closed incident and actions, verified recovery and
   rotation, hashed postmortem, and current cross-functional tabletop.
8. `alert_delivery`: P1 delivery to on-call and incident channel,
   acknowledgement within ten minutes, and secondary escalation receipts. All
   deliveries, acknowledgement, and escalation must follow emission; recorded
   latency must equal the actual timestamp delta and that delta must be at most
   600 seconds.
9. `claim_honesty`: fetched and hashed product/landing/legal surfaces, no
   unsupported claims, explicit research/product and verdict boundaries, and
   legal/product/research approvals.

After all gates pass, the signed or live `release_decision` must include exactly
the legal, operations, product, and security owner approvals. Its approval and
observation times must be after the newest gate observation.

## Time and freshness rules

For every evidence item, time must move forward monotonically:

`event_at_utc <= observed_at_utc <= manifest generated_at_utc <= verification time`

Every critical nested proof time—deployment, workflow run, audit, packet,
share, billing payment, publication, approval, support, CRM, incident, alert,
or claim scan—must fall between its gate's `event_at_utc` and
`observed_at_utc`. The event itself and every nested proof time must satisfy the
same gate-specific age limit, so a fresh observation cannot wrap a stale 2020
event.

Receipts must be issued at or after the evidence observation, no later than
manifest generation and verification, unexpired at verification, and within
their issuer key's validity window. Evidence older than the fixed gate limit
fails:

| Gate | Maximum age |
|---|---:|
| Runtime/WORM | 30 minutes |
| Root CI/protected deploy | 24 hours |
| Hosted customer journey | 72 hours |
| Accounts/billing | 72 hours |
| Legal publication/approval | 30 days |
| Support/CRM | 72 hours |
| Incident/tabletop | 90 days |
| Alert delivery | 24 hours |
| Claim honesty | 24 hours |

## Acceptance report and archival

Archive the exact evidence bundle and JSON report only after the normal command
returns `0`. The report records:

- verification time, verifier hash, manifest hash, and trusted-registry hash;
- repository commit, externally supplied master SHA, and public deploy ID;
- dereferenced receipt/live-document hashes and signed subject hashes;
- authority mode, issuer, key ID, exact subject URI, and origin for every gate
  and the release decision;
- final result, open gates, and all validation errors.

Those hashes make the decision reproducible without treating self-authored
metadata as proof.

## Secret-handling boundary

Never put passwords, service tokens, cookies, JWTs, AWS keys, Stripe secret or
webhook keys, signing private keys, card data, raw share links, or raw provider
and customer IDs in the manifest, evidence, receipts, registry, workflow
inputs, or report. Use hashes for sensitive identifiers. Credentialized URLs
and URLs with query strings are rejected.
