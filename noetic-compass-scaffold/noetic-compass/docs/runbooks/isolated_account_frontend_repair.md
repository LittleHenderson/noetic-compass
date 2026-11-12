# Isolated account frontend repair candidate

Status: PREPARATION ONLY. No production release, restart, secret retrieval, infrastructure change,
spending, or customer-production acceptance is included. Publication of the test branch and
isolated fictional-data checks was approved on November 12, 2026. The AWS API remains
paused. This document proposes staging steps; it does not authorize or execute them.

## Scope and compatibility boundary

Base: `b574170436a73db707453a1e165012d934695240` in `LittleHenderson/noetic-compass`.
The candidate uses the existing React 18 / router 6 `atlas-viewer` account application. It does not
port the React 19 / router 7 legacy dashboard, widen the API account allowlist, alter the account
storage policy, or relax any API startup requirement.

- Atlas: account login/invite redemption, model selection, account security, audit console, and
  cockpit retain their existing routes and server permissions. A route existing is not proof that
  its entire hosted journey has passed production acceptance.
- Legacy dashboard: `/login` is a non-authenticating retirement notice. `/how-it-works` and `/faq`
  remain public with their existing informational content. Separately, the pinned claim-surface
  prerender contract remains `/` and `/audit-console` in both frontends; its tests cover those exact
  routes, not the informational pages. All other dashboard runtime routes redirect to the notice,
  even with a cached legacy JWT. The prior private page source is preserved.
- Unsupported by this account release: legacy assessments/benchmarks, history/details/cohorts,
  scenarios, config, validation/leaderboard/reproducibility, compiler, Idea Atlas, forecast,
  visualization, tutorial, and AI challenges. These need separate scoped migrations and backend
  authorization review. There is no `/scenarios` compatibility exception.
- Existing links from public information pages to retired tools land at the retirement notice.
  No account URL is guessed, no production host is changed, and no claims pages are silently moved
  into the Atlas SPA. Keep the existing public site/claims host distinct until routing is reviewed.

## Security behavior

The browser no longer has a shared mint-secret input or random-identity recovery. Both frontends'
Vite builds reject shared-mint environment variables, source references, or emitted bundle markers
without printing their value. `build:accounts` additionally requires the public account-mode flag.
Synthetic tests prove the guard rejects a deliberately contaminated build and accepts a clean one.
The guard covers the known mint mechanism, not every conceivable secret or an arbitrary malicious
source rewrite; secret scanning and release review remain necessary.

The API's anonymous, no-store `/public/capabilities` response must match the build before account
UI or stored sessions are available. Account credentials go to the configured API only, with no
browser cookies, redirects, or referrer. Persisted JWTs carry an exact normalized API URL binding;
unbound legacy browser state and tokens bound to another API are discarded. This browser binding
is not cryptographic JWT verification. The backend remains responsible for account, tenant, role,
session, signature, and quota enforcement.

A 401 clears only the session that made that request and returns the user to login through AuthGate.
A 429 retains that identity and shows a limit notice. Neither response mints a token or retries.
A new login, logout, page dismissal, provider teardown, or API-mode rebind cancels stale auth work.
Retained callbacks from an older verified API epoch cannot send credentials or the current token.
Local logout clears immediately; failed server revocation still displays the existing explicit
warning. Cancellation prevents stale browser installation, but cannot undo a request the server
already accepted. An interrupted login can therefore leave an inaccessible server session until
expiry. Interrupted invite redemption retains the existing exact-credential retry guidance.

## Local verification commands

Run from `noetic-compass-scaffold/noetic-compass`, in a clean checkout without production `.env`
files. Use local test dependencies only. Never load Vercel/AWS secret values for these tests.

```sh
(cd atlas-viewer && npm ci --ignore-scripts)
(cd dashboard && npm ci --ignore-scripts)
(cd atlas-viewer && npm test && npm run test:claim-surfaces && npm run test:auth-build)
(cd atlas-viewer && npm run build && npm run build:accounts)
(cd dashboard && npm test && npm run test:claim-surfaces && npm run test:auth-build)
(cd dashboard && npm run lint && npm run build)
python -m pytest -q tests/test_middleware.py tests/test_accounts_invites.py \
  tests/test_account_lifecycle_config.py tests/test_public_capabilities.py \
  tests/test_audit_identity_scope.py tests/test_evidence_ownership.py
make test
(cd atlas-viewer && npm run test:e2e:accounts)
```

The isolated Playwright config serves localhost and mocks every API response; external browser
requests are blocked. It is separate from the existing live API E2E suite, which must not be invoked
for this repair. `CHROMIUM_EXECUTABLE_PATH` may select an already supported local browser. If the
runtime cannot launch it, report that limit rather than changing security settings or claiming
browser assertions passed. Full backend and aggregate suites require the native `cas_engine`
extension and Rust toolchain. Focused test success does not replace those checks.

## Proposed staging and return-to-service gates

1. Review this patch and the explicit legacy feature boundary. Reproduce test results on a permitted
   local/CI executor, including Rust/native backend tests and the isolated browser suite. Pin the
   exact repaired commit and dependency lockfiles. The approved test branch is `noetic/account-repair-tests-20261112`; publication and CI
   outcomes must be verified from the remote commit and run, not inferred from this document.
   No production deployment is authorized.
2. Verify the actual AWS image revision and deployment configuration using non-secret metadata.
   Leave the API paused until a separately approved rollout. Do not infer account readiness from a
   frontend flag or from the current unknown backend image.
3. Prepare an account-enabled backend using all existing hosted startup requirements: durable
   PostgreSQL, immutable S3 evidence requirements, distinct required pseudonym keyrings, account
   session storage, HS256 and a sufficiently strong JWT signing key, and the existing tenant/role
   authorization boundaries. Provisioning or credential changes require their mandatory approvals.
   Do not turn off validation to make a restart succeed.
4. Treat any shared mint value previously shipped in a browser bundle as exposed. Prepare its
   revocation/rotation and legacy token invalidation through an authorized operator workflow before
   public return to service. Do not retrieve the old value. Existing downloaded bundles/service
   worker caches cannot be made secret by a new build; server rejection is mandatory.
5. Build Atlas with `npm run build:accounts`. Proposed settings are `VITE_ACCOUNTS_ENABLED=true`
   and `VITE_ATLAS_API_BASE_URL=<verified account API root>/atlas`; no shared mint variable is
   allowed. Confirm HTTPS, allowed CORS origins, exact proxy routes, capabilities `no-store`, and
   API audience binding. Keep public claims routes on their reviewed host. These are proposals,
   not edits to live Vercel/AWS settings.
6. In a separately authorized staging lane, verify real invite/login/logout/revocation, repeated and
   interrupted requests, account/tenant isolation, ownership, quota durability across restart, 401,
   429, and mismatch failure. Do not repoint or invoke the historical private-canary proof for this
   work. Check the current authoritative runbooks before choosing any canary or public destination.
7. Recheck the full customer-production acceptance contract and its independent hosted gates.
   `docs/runbooks/customer_production_acceptance.md` remains authoritative and OPEN. An auth repair,
   a frontend build, or a private canary is not an ACCEPT decision.
8. Only after the separate release decision and required approvals: deploy the pinned backend and
   account frontend, confirm no mint material in served artifacts, and perform the approved hosted
   smoke test. Keep a safe maintenance rollback; never restore the unsafe username-only mint flow.

No automatic future deployment or monitoring has been scheduled by this candidate.

## Approved public test branch, November 12, 2026

The branch adds `.github/workflows/noetic-account-repair-isolated.yml`, triggered only by pushes
to `noetic/account-repair-tests-20261112`. It uses standard public-repository Ubuntu runners,
read-only repository permissions, nonpersistent checkout credentials, no repository secrets,
no cache or artifact uploads, and no deployment steps. Dependency installation uses official
registries; tests use clean process environments and fictional data. The backend checks block
external sockets, and PostgreSQL is a temporary runner-local service, never the customer database.
The browser suite explicitly blocks service workers and retains Chromium's sandbox.

The root and dashboard Vercel configs disable automatic deployments only for this exact branch
using `git.deploymentEnabled`. Other branch behavior, public routing, DNS and live settings are
unchanged. See https://vercel.com/docs/project-configuration/git-configuration .

These are focused auth/frontend/PostgreSQL checks, not the full Rust/Python aggregate suite or
hosted customer-production acceptance. Passing them is preparation, not deployment approval.
GitHub logs are the test receipt; no passing result is asserted before the workflow completes.
