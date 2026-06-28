# CAS Harness Launch Agent Fleet - 2026-06-05

Purpose: divide the remaining launch blockers into parallel workstreams while preserving the product-readiness boundary. A local dev link or research artifact is not launch evidence; a launch gate closes only after source integration, tests, hosted deployment where applicable, and an honest smoke result.

## Fleet Assignments

| Agent | Workstream | Starting Branches / Evidence | Finish Line |
|---|---|---|---|
| Agent 1 - Launch Integration Captain | Branch consolidation and merge order | `master`, `launch/scoped-beta`, `launch/ui-audit-bench`, paid-security branches, `wave5.5/harness-launch-declutter` | Exact merge/cherry-pick plan, conflict list, verification commands, and do-not-ship gaps |
| Agent 2 - Auth/Sessions/RBAC | Paid-user auth spine | `launch/paid-security-spine`, `launch/paid-security-sessions`, `launch/paid-audit-identity`, `launch/paid-tenant-isolation` | Durable sessions/revocation/disabled-account recheck and central `require_role` / tenant dependency status with tests or patch |
| Agent 3 - Audit Console + Guide UI | CAS Harness branded audit surface and floating Guide | `launch/ui-audit-bench`, local Gemini Guide work | Hosted-ready audit console with Guide widget, route clarity, frontend tests |
| Agent 4 - Production Worker Route | No-SSH worker execution path | `master`, `launch/worker-token-send`, live worker code | Env matrix, health proof, hosted audit proof commands, any code/test gap closed |
| Agent 5 - Quotas/Billing/Account Boundary | Server-side usage and paid-user controls | `launch/paid-quotas`, paid-security branches, billing stubs | Durable per-account/tenant quota gate at audit choke points, default-off where needed, tests |
| Agent 6 - Compliance/CRM/Support | Launch minimum paperwork and operator workflow | compliance drafts, CRM code, production TODO | Privacy/terms or beta agreement checklist, WORM/retention disclosure, support/security contact, CRM activation proof |

## Current Critical Path

1. Consolidate launch work onto a `master`-based branch. Do not ship `wave5.5/harness-launch-declutter` directly.
2. Merge/deploy scoped-beta auth only after `NC_AUTH_MINT_SECRET` and dashboard `VITE_AUTH_MINT_SECRET` are set to matching values.
3. Bring the Guide/audit-console UI from `launch/ui-audit-bench` onto the launch branch and prove the hosted route.
4. Prove the production worker route without SSH tunnel using real worker URL/token env.
5. Close or explicitly defer paid-user gates: accounts, sessions, tenant isolation, RBAC, quotas, billing.
6. Publish compliance/support/CRM minimum before external users.

## Honest Status Boundary

- Internal demo can use local/dev auth and local Vite only.
- Private alpha can use scoped-beta auth if env secrets are set and hosted smoke passes.
- Paid/public launch requires real account/session/quota/billing boundaries and must not rely on frontend-held shared secrets as the paywall.
- `ACCEPT` remains unavailable unless proof gates pass; unresolved proof remains `FLAG_FOR_HUMAN_REVIEW`, `OPEN`, `unavailable`, or `present` exactly as emitted by the verifier.
