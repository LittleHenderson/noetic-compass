# Atlas LIVE Worker — Launch-Grade Exposure + Image Hardening (2026-05-31)

Status: design proposal. No infra was changed; no pod, RunPod account, or SSH
was accessed while writing this. Claims about RunPod product behaviour that I
could not verify from this repo are flagged **[verify]**.

## 1. Problem

Today the API reaches the private live-trace worker over a hand-run SSH tunnel:

```bash
ssh -N -L 18080:127.0.0.1:8080 <pod>      # operator runs this by hand
# API process env:
ATLAS_LIVE_WORKER_URL=http://127.0.0.1:18080
```

The worker pod only exposes port 22. The tunnel is fine for dev/smoke but is
**not launch-grade**: if the tunnel process dies (laptop sleep, network blip,
operator logout), the entire LIVE path dies and the cockpit must fall back to
REPLAY. There is no supervision, no auto-reconnect, and the transport is bound
to one operator's machine.

The current verified wiring (see
`docs/working/atlas_live_verified_alpha_state_2026_05_25.md`) is:

```text
Atlas Viewer /cockpit
  -> noetic-compass-api            (auth / license / invite-code / rate-limit)
  -> live-trace-worker (RunPod)    (Pythia-160M actual weights, probes, SSE)
  -> SSE stream back through the API
  -> Atlas Viewer cockpit
```

North-star: *"ANY DEVELOPER CAN USE CAS HARNESS TO AUDIT OPEN-WEIGHT MODELS UP
TO 1 TRILLION PARAMETERS ON OUR PLATFORM."*

## 2. Hard invariant (every option below must preserve it)

```text
Browser  ->  noetic-compass-api  ->  worker
```

The **browser must NEVER reach the worker directly.** "Exposure" here means
giving *the API* a stable, durable network path to the worker — replacing the
SSH tunnel — **not** making the worker public. The API stays the only allowed
caller; it holds the invite-code allowlist, per-IP/per-code rate limits, and
mints the short-lived `stream_token` that gates the SSE route
(`api/routes/atlas_live.py`).

### 2.1 Auth model — what the SSH tunnel gives us for free, and what we lose

The SSH tunnel provides two things at once that we must not silently drop:

1. **Transport security** — the worker port is only reachable through an
   authenticated, encrypted SSH channel bound to `127.0.0.1` on the pod.
2. **Reachability gating** — nothing on the public internet can open the worker
   port, because only port 22 is exposed.

Any replacement that opens an HTTP/TCP port to reach the worker **loses (2) and
must add app-level authentication to compensate.** Transport encryption (TLS) is
provided by RunPod's HTTP proxy **[verify]** for proxied ports, but TLS only
protects the channel — it does not prove the *caller* is our API. Therefore:

> **The worker must require a secret that only the API sends.** This proposal
> adds an optional `X-Atlas-Worker-Token` shared-secret header check in the
> worker (default OFF for backward-compatible dev; ON in production). The API
> sends the matching secret on every worker call. This is shared-secret bearer
> auth, deliberately simple; it is the app-level replacement for the
> reachability gating the tunnel gave us.

The token is a coarse "is this our API" gate. It is **not** a substitute for
keeping the worker off the public browser path, and it is **not** user identity
(the API still owns user identity, license, and invite codes). Defence in depth:
token **and** (where the option supports it) network ACL / private networking.

## 3. Options

Three options are compared against: security, durability/persistence, cost, ops
simplicity, path to the 1T-param vision, and preservation of the API-gated
invariant.

### Option A — Custom worker image, HTTP port exposed via RunPod proxy + bearer token

Keep the existing always-on RunPod **Pod** (not serverless). Expose the worker's
HTTP port (8080) through RunPod's port proxy so the API can reach it at a stable
`https://<pod-id>-8080.proxy.runpod.net` URL **[verify exact hostname format]**
instead of through an SSH tunnel. The worker requires `X-Atlas-Worker-Token`;
the API sends it. `ATLAS_LIVE_WORKER_URL` points at the proxy URL.

- **Security:** TLS via RunPod proxy **[verify]**; the proxy URL is
  internet-reachable, so app-level token auth is **mandatory** (this is exactly
  the gap §2.1 describes). The browser still never sees this URL — only the API
  env holds it. The token shim in this PR closes the "anyone who guesses the
  proxy URL can hit the worker" hole. Residual risk: a leaked proxy URL + leaked
  token = direct worker access; mitigated by treating the token as a rotatable
  secret and by the worker exposing nothing user-identifying.
- **Durability/persistence:** Strong improvement over the tunnel — no operator
  laptop in the path. The pod is always-on; the hardened `/workspace` venv + HF
  cache (cold start ~25s, per the task brief) survive restarts. RunPod restarts
  the container on crash **[verify auto-restart policy]**; `/pre_start.sh`
  re-runs the boot hook. Failure mode shifts from "tunnel died" to "pod died,"
  which is rarer and observable via `/atlas/live/health/realmode`.
- **Cost:** Same as today — one always-on small GPU (Pythia-160M fits in
  ~700 MB VRAM; smallest tier e.g. RTX A4000/A5000 is plenty). No new spend. Do
  NOT over-provision: 16-24 GB is already generous for 160M.
- **Ops simplicity:** Highest. It is the smallest delta from the verified alpha:
  expose a port that already serves, add one header check, set two env vars. No
  new managed service, no new control plane. Operators stop running the tunnel.
- **Path to 1T:** Limited on its own. A single always-on pod cannot hold a 1T
  model; but the repo's 1T story is **distributed open-weight auditing**
  (`api/routes/cas_harness_audit.py` scale-plan + fleet executor: layer-sharded
  Probe Workers, leased jobs, merged Evidence Packets). Option A is the right
  shape for **one** such worker; the 1T path is N of these workers registered
  with the fleet executor, each behind the same token gate. So A composes toward
  1T even though one pod does not reach it.
- **Invariant:** Preserved. API-only caller; browser never holds the URL.

### Option B — RunPod Serverless endpoint

Move the worker to a RunPod **Serverless** endpoint. The API calls the
serverless `/run` (or `/runsync`) HTTPS endpoint with a RunPod API key; RunPod
scales workers up/down and routes the request **[verify exact serverless API
surface and whether long-lived SSE streaming is supported]**.

- **Security:** Strong. RunPod serverless endpoints are authenticated by a
  RunPod API key by default **[verify]**, so app-level auth comes "for free" at
  the platform boundary, and there is no always-listening port we own. We would
  still add `X-Atlas-Worker-Token` as defence in depth and to keep the worker
  code identical across Pod/serverless deploys.
- **Durability/persistence:** Excellent for availability (managed, auto-scaled,
  no single pod to babysit) but introduces **cold starts**. The whole reason the
  alpha picked an always-on pod was first-click responsiveness; serverless cold
  start would reload Pythia + HF cache per cold worker. Mitigations: min-workers
  >= 1 (always-warm, which erases most of the cost advantage) or network-volume
  HF cache **[verify cold-start magnitude]**.
- **Cost:** Best when idle (scale-to-zero), worst per-request under steady alpha
  traffic if we set min-workers >= 1 to kill cold starts. For sporadic alpha
  usage, scale-to-zero is genuinely cheaper than an always-on pod.
- **Ops simplicity:** Medium. No tunnel and no pod babysitting, but a different
  deploy model (handler packaging, endpoint config) and a **streaming question**:
  our cockpit depends on long-lived SSE token streaming. Serverless request/
  response semantics may not cleanly support a minutes-long SSE stream
  **[verify — this is the load-bearing unknown for B]**. If SSE is not
  first-class, B forces a protocol change (poll/chunk), which is a much larger
  blast radius than A.
- **Path to 1T:** Best *story*. Serverless auto-scale + per-job billing is the
  natural substrate for "spin up M sharded workers for a big audit, tear them
  down after." The fleet executor's leased-job model maps onto serverless jobs.
  This is the strongest long-term answer for the 1T vision.
- **Invariant:** Preserved. API holds the RunPod key + worker token; browser
  never calls RunPod.

### Option C — Managed persistent tunnel / authenticated reverse proxy / gateway

Replace the hand-run SSH tunnel with a **supervised** durable tunnel or a small
authenticated reverse proxy in front of the worker. Concretely, one of:

- a managed tunnel (e.g. Cloudflare Tunnel / `cloudflared`, ngrok reserved
  domain, or Tailscale Funnel **[verify which are acceptable for confidential
  workloads]**) running as a service on the pod, presenting a stable hostname
  the API calls; or
- `autossh` / a systemd-style supervised SSH tunnel from a stable jump host
  (keeps SSH transport security, removes the "operator laptop" dependency); or
- VPC/VPN peering (e.g. Tailscale/WireGuard mesh) so the API host and the worker
  share a private network and the API calls the worker on a private IP.

- **Security:** Best of the three for the "not internet-reachable" property —
  with a VPN/mesh (Tailscale/WireGuard) the worker port is only reachable inside
  the private network, so we keep the tunnel's reachability gating **and** add
  the token. A public managed tunnel (Cloudflare/ngrok) is closer to Option A's
  posture (internet-reachable hostname) and leans harder on the token + the
  tunnel provider's access controls.
- **Durability/persistence:** Strong if supervised. `autossh`/systemd or a
  mesh-agent daemon reconnects automatically; this directly fixes the "tunnel
  died" failure without changing the worker. Persistence of venv/HF cache is
  unchanged (still the hardened `/workspace`).
- **Cost:** Low. Most options here are free or cheap (Tailscale free tier,
  `cloudflared` free, `autossh` free). No GPU change. Adds one more moving
  daemon to the pod.
- **Ops simplicity:** Medium-low. Introduces a third-party dependency (tunnel/
  mesh provider) and a daemon to install + supervise via the existing
  `/pre_start.sh` hook. More moving parts than A; fewer model-serving changes
  than B. A mesh (Tailscale) is operationally clean once set up; a raw
  `autossh` is the smallest conceptual change but still "another daemon."
- **Path to 1T:** Neutral. A mesh is a fine substrate for many private workers
  (each joins the mesh), but it does not provide the auto-scale/billing story
  that serverless (B) does. It is a transport fix, not a scaling architecture.
- **Invariant:** Preserved (and, with a VPN/mesh, arguably best-preserved since
  the worker is never internet-reachable at all).

## 4. Comparison summary

| Axis | A: Pod + proxy + token | B: Serverless | C: Managed tunnel / mesh |
|---|---|---|---|
| Security | Good (token mandatory; URL internet-reachable) | Strong (platform key + token) | Strongest with VPN/mesh (private) |
| Durability vs SSH tunnel | Strong | Strong (managed) | Strong (if supervised) |
| Cold-start risk | None (always-on) | **Yes** (unless min-workers>=1) | None |
| Cost (alpha traffic) | Flat, low | Lowest idle / higher if kept warm | Lowest |
| Ops simplicity / blast radius | **Highest / smallest** | Medium (deploy model + SSE risk) | Medium |
| SSE streaming today | Works (unchanged) | **Unverified / at risk** | Works (unchanged) |
| Path to 1T (distributed fleet) | Composes (N pods) | **Best** (auto-scale + billing) | Neutral (transport only) |
| API-gated invariant | Preserved | Preserved | Preserved (best w/ mesh) |

## 5. Recommendation

**Next launch step: Option A** — custom worker image with the HTTP port exposed
via the RunPod proxy, gated by a mandatory `X-Atlas-Worker-Token` shared secret
that the API sends. Rationale (2-3 sentences): A is the smallest, lowest-risk
delta from the already-verified alpha — it removes the operator laptop from the
critical path and keeps the always-on first-click responsiveness the cockpit was
designed around, while the token shim closes the reachability gap that opening a
port creates. It requires no change to the SSE streaming contract (the
load-bearing unknown that makes B risky right now) and no third-party tunnel
dependency. This PR ships the worker-side half (the optional token check + a
hardened, self-contained image); the remaining work is infra-only: expose the
port in the RunPod template, set `ATLAS_LIVE_WORKER_TOKEN` on both sides, and
point `ATLAS_LIVE_WORKER_URL` at the proxy hostname.

**If sporadic-traffic cost or the always-on pod becomes the pain point before
the 1T work begins,** add Option C (a supervised mesh, e.g. Tailscale/WireGuard)
as a transport hardening that keeps the worker fully private. C and A are
compatible: run A's token gate *inside* C's private network for defence in
depth.

**Longer-term 1T story: Option B (serverless), wired through the existing
distributed fleet executor.** The repo already models 1T-scale auditing as
layer-sharded, leased-job, evidence-merged distributed work
(`api/services/cas_harness_fleet_executor.py`, `cas_harness_scale_planner.py`,
exercised by `api/routes/cas_harness_audit.py`). Serverless is the right
substrate for spinning up M sharded Probe Workers on demand and tearing them
down — *provided* the SSE-vs-request-response streaming question is resolved
first (a worker that returns a final Evidence Packet fragment, rather than a
live SSE stream, fits serverless cleanly; the live-cockpit SSE path may stay on
always-on pods even after batch auditing moves to serverless). Treat B as the
scaling track, not the immediate launch step.

### Migration ordering (honest, low-regret)

1. **Now (this PR):** harden the image; add the optional token shim (default
   off). No behaviour change for existing dev/smoke.
2. **Launch step (infra-only, not in this PR):** turn the token ON in prod, set
   the secret on API + worker, expose the port, repoint `ATLAS_LIVE_WORKER_URL`,
   retire the manual tunnel. Verify via `/atlas/live/health/realmode`.
3. **Optional hardening:** put the worker on a private mesh (C) so the proxy URL
   is not internet-reachable.
4. **1T track:** package the worker as a RunPod serverless handler behind the
   fleet executor; resolve SSE-vs-batch streaming; keep the live cockpit on a
   warm pod if SSE must stay live.

## 6. Auth shim contract (shipped in this PR, optional + backward-compatible)

- Env var `ATLAS_LIVE_WORKER_TOKEN` (worker side).
  - **Unset or empty -> auth disabled** (current behaviour; dev/CI/local smoke
    unaffected). This is the default.
  - **Set -> every request except the health endpoints must present
    `X-Atlas-Worker-Token: <token>`** or receive `401`.
- Health endpoints (`/health`, `/health/realmode`) are intentionally
  **exempt** so RunPod health checks and the API's liveness/real-mode proxy keep
  working without the secret. They expose no user data and no inference.
- The API side already centralises worker calls in `api/routes/atlas_live.py`
  (`_create_worker_session`, `_iter_worker_events`, `_proxy_worker_get`).
  Wiring the API to send the header is a one-line addition per call site and is
  **out of scope for this PR** (the task constrains edits to the worker + docs);
  it is the infra/launch step. Until then, leaving `ATLAS_LIVE_WORKER_TOKEN`
  unset keeps the system working exactly as it does today.
- No secret is committed. The token is supplied via environment only.

## 7. Honest caveats / open questions for the human

- **[verify]** RunPod HTTP-proxy hostname format, TLS termination, and whether
  exposed-port traffic is authenticated by RunPod at all (I believe the proxy is
  open-by-URL, which is exactly why the token is mandatory) — confirm before
  relying on Option A in production.
- **[verify]** RunPod container auto-restart / crash policy, so we know whether
  "pod died" self-heals or needs paging.
- **[verify]** RunPod **serverless** SSE/long-stream support. This is the single
  biggest unknown gating Option B; if serverless cannot hold a minutes-long SSE
  stream, B is batch-only and the live cockpit stays on pods.
- **Token rotation** is manual in this design (env var on both sides). If we
  want rotation without downtime, the worker would need to accept a small set of
  valid tokens during a rollover window — deferred; flag for the launch step.
- The token is a shared secret, not per-request or per-user. User identity,
  license, invite codes, and rate limits remain entirely the API's job; the
  token only answers "is the caller our API."
- This PR does **not** touch the API routes, frontend, runner, or `CHANGELOG.md`,
  per task constraints. The API-side header send and the infra changes are the
  follow-on launch step.
