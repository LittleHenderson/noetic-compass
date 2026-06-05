# ADR-0001 — Edge layers: reverse proxy, load balancing, API gateway

- **Status:** Accepted (beta posture) — Jun 5, 2026
- **Scope:** How the Noetic Compass / CAS Harness backend handles the "what sits in front of the
  server" layers (reverse proxy, load balancer, API gateway), and what must change before we scale
  horizontally.
- **Audience:** engineering. Plain-language by design; terms defined inline.

---

## Context

The product is approaching paid-beta launch. The recurring system-design question — *do we need a
reverse proxy / load balancer / API gateway?* — came up. This ADR records the decision against the
**actual** deployment, not a generic diagram, so it is not re-litigated each time traffic grows.

What we actually run today (from `render.yaml`, `Dockerfile.api`, `api/main.py`):

- **One** Render web service, `noetic-compass-api` (Docker; FastAPI + the cas-engine Rust crate),
  **`plan: free`** → **a single instance**, `healthCheckPath: /health`, auto-deploy on commit to
  `master`.
- A separate Render **static site** `atlas-viewer-app.onrender.com` (the CAS Harness console) tracking
  `master`.
- The **dashboard** ships its own `nginx.conf` (serves the static SPA; also has a `vercel.json`).
- A **RunPod** `live-trace-worker` (GPU) for live model tracing, reached *behind* the API — the
  browser never hits RunPod directly.
- LLM provider in prod is currently `mock` (`NC_MOCK_LLM=true`) — the live model is not yet wired.
- In-app cross-cutting middleware is already present: `JWTAuthMiddleware`, `RateLimitMiddleware`
  (tiers community/professional/enterprise, wired at `api/main.py:105`), the account/session **RBAC**
  spine, conditional public-path gating, tenant isolation, and the per-tenant quota engine.

## Decision

### 1. Reverse proxy — we already have one; do **not** run our own
A reverse proxy terminates TLS, hides the origin server, and routes/handles the messy internet edge.
On Render, the FastAPI container never faces the raw internet — **Render's edge is the reverse proxy**
(managed HTTPS/TLS termination, origin hiding, routing, `X-Forwarded-*`). The dashboard additionally
serves its SPA via its own `nginx.conf`. Running our own nginx/Envoy in front of the API would only
duplicate Render. **Decision: rely on Render's edge (+ the dashboard nginx). No bespoke reverse
proxy.**

### 2. Load balancer — none today, and not the bottleneck
A load balancer spreads requests across multiple backend instances and reroutes around dead ones.
We run **one** free-plan instance, so there is nothing to balance, and there is **no true high
availability** (one restart = brief downtime; `/health` lets Render *restart* a dead box, which is
recovery, not HA).

Crucially: **the moment we run ≥2 instances, Render's platform load balancer distributes across them
with health checks + failover, for free.** We do **not** hand-pick round-robin vs least-connections vs
weighted vs IP-hash, and we do **not** stand up HAProxy / AWS ALB-NLB / a Layer-4 balancer. Those
knobs only exist when you run your *own* load balancer, which we have no reason to do at beta scale.

**Explicitly rejected: IP-hashing / sticky sessions.** That is a band-aid to pin each user to one box
to hide server-side state. The correct fix for us is to remove the state (see #4), per the standard
"stateless scales more cleanly" principle.

### 3. API gateway — keep it in-app; no dedicated product yet
An API gateway centralizes API concerns (auth, rate limits, quotas, versioning, analytics,
request transformation). We have **no** dedicated gateway product (Kong / AWS API Gateway), but we
have already built the gateway's *jobs* into the FastAPI app (JWT auth, `RateLimitMiddleware` tiers,
RBAC, tenant isolation, quota engine). For **one service** (a modular monolith, not microservices)
that is the right call — a separate gateway's value is removing duplication across *many* services,
which we do not have.

**Revisit a dedicated gateway only when** either (a) we split into independently-deployed
microservices, or (b) we expose a broad public API to external developers needing centralized API
keys / quotas / `/v1`→`/v2` versioning / analytics. Not before.

### 4. The real prerequisite for horizontal scale + HA: become **stateless**
The blocker to scaling is **not** any edge layer — it is that the app keeps state in process memory
on a single box. Known in-memory state today:

- **Audit-run sessions** — `_SESSIONS` dict in `api/services/cas_harness_audit_sessions.py` (this is
  also why the tenant-iso evidence-ownership write is currently deferred — the session/owner data is
  not durable).
- **Assessment store** fallback — `api/store.py` (in-memory when no DB).
- **Idea Atlas** store fallback — `api/routes/idea_atlas.py`.
- **Visual grounding** stub — `api/routes/visual_grounding.py`.

With ≥2 instances behind Render's LB, a request landing on instance B would not see state created on
instance A → broken sessions/data. **Decision: before any real scale push, move this state onto the
durable StateStore / Postgres we already support (`NC_DATABASE_URL`), making the app stateless.** Then
scaling and HA become "set instances ≥ 2" — no load-balancer engineering required. This work also
**closes the deferred tenant-iso ownership-write** (durable audit sessions carry the server-derived
owner), so it pays for itself twice.

## Consequences

- **Beta launch: nothing changes here.** A single Render instance + in-app gateway concerns is correct
  for a handful of beta users. Adding nginx / HAProxy / Kong now would be premature complexity.
- **Pre-scale checklist (in order), before promoting beyond a handful of concurrent users:**
  1. Move off the free single instance to a paid multi-instance Render plan.
  2. Make the app stateless — relocate the in-memory stores above onto Postgres / StateStore.
  3. Then raise instance count; Render's LB + health checks + failover handle distribution.
- **Free-plan caveat:** Render free web services are single-instance and sleep on inactivity (cold
  starts). Acceptable for beta; not for SLA-bearing traffic.
- **No new infrastructure to operate** (no nginx/HAProxy/Kong to patch, secure, monitor) until a real
  requirement (microservices or a public developer API) forces it.

## Revisit triggers

- Sustained concurrent traffic that one instance cannot serve → do the pre-scale checklist.
- Split into microservices, OR open a public external-developer API with tiers/quotas/versioning →
  evaluate a dedicated API gateway.
- An HA/uptime SLA commitment → multi-instance (requires statelessness first).
