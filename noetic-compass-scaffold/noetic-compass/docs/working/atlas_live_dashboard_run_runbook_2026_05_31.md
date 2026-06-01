# Runbook — Run a live Pythia-160M audit from the dashboard UI (2026-05-31)

Copy-pasteable steps for a human to run ONE hosted open-weight audit
(`EleutherAI/pythia-160m`) end-to-end from the actual Audit Console, against the
private Atlas live-trace worker.

What you should see at the end (the honest result): **real model output**, a
**teal `open_weight_live_trace` audit-scope banner**, a verdict of
**`FLAG_FOR_HUMAN_REVIEW`**, and proof chips showing **model / CAS readout /
output / packet = present** and **causal / control = unavailable**. This path
does **not** produce ACCEPT — that is correct, not a failure (see
[Why no ACCEPT?](#why-no-accept)).

All paths below assume repo root `noetic-compass-scaffold/noetic-compass/`.

---

## 0. Prerequisites (one-time)

- A running GPU pod hosting the live-trace worker with Pythia-160M loaded
  (`is_real_model = true`). Port 22 (SSH) exposed; the worker itself listens on
  pod `:8080` and stays private.
- An SSH key for the pod (default `~/.ssh/id_ed25519`).
- Python env with the API deps installed (`pip install -r requirements.txt`).
- Node deps for the frontend (`cd atlas-viewer && npm install`).

If you do NOT have a GPU pod right now, you can still exercise the whole UI flow
against a **local demo worker** — see
[Appendix A: local demo worker](#appendix-a-no-pod-local-demo-worker). The demo
worker returns schema-valid but synthetic output and is honestly marked
`is_real_model = false`, so the harvest is flagged demo-fallback.

---

## 1. Open the SSH tunnel to the worker

The worker is private on the pod, so the API reaches it over a forwarded local
port (`127.0.0.1:18080 -> pod:8080`):

```bash
cd noetic-compass-scaffold/noetic-compass
# Pod host/port default to the current pod; override if RunPod reassigned them.
POD_HOST=<pod-ip> POD_PORT=<pod-ssh-port> \
  ./live-trace-worker/scripts/open_atlas_live_tunnel.sh
```

Leave this terminal open (Ctrl-C closes the tunnel). Verify the worker answers
and is in REAL mode:

```bash
curl -s http://127.0.0.1:18080/health/realmode
# Expect JSON with "is_real_model": true  (false => demo; see Appendix A)
```

---

## 2. Point the API at the worker and start it

In a **new** terminal:

```bash
cd noetic-compass-scaffold/noetic-compass
export ATLAS_LIVE_WORKER_URL=http://127.0.0.1:18080
uvicorn api.main:app --reload --port 8000
```

Sanity check the API is up:

```bash
curl -s http://localhost:8000/health
```

> The hosted open-weight audit path keys off `ATLAS_LIVE_WORKER_URL`. If it is
> empty/unset, the run will honestly FAIL the session (it will not fall back to
> a fake verdict). See [If it fails](#if-it-fails).

---

## 3. Start the frontend

In a **third** terminal. The Audit Console talks to the API via the relative
path `/api/cas-harness/audit`. Set the API base URL env so the client builds an
**absolute** URL to the backend (this avoids a dev-proxy path issue — see
[Known dev-proxy gotcha](#known-dev-proxy-gotcha)):

```bash
cd noetic-compass-scaffold/noetic-compass/atlas-viewer
# Verified script name in atlas-viewer/package.json: "dev": "vite"
VITE_ATLAS_API_BASE_URL=http://localhost:8000/atlas npm run dev
```

Vite prints a local URL (typically `http://localhost:5173`). Open it.

---

## 4. Run the audit in the Audit Console

1. Log in / get past the license + model-config gates as usual.
2. Navigate to **`/audit-console`** (the Audit Console page).
3. Enter a prompt, e.g. `Audit this live prompt end to end.`
4. Select the model target **`EleutherAI/pythia-160m`** (the hosted
   open-weight reference target).
5. Click **Run**.

### What to expect (the honest landing)

- **Real output** text from Pythia appears for the prompt.
- A **teal `open_weight_live_trace` audit-scope banner** stating activations +
  readout were captured but causal/control were not yet run, and the verdict is
  held for review. (Label text: "Open-weight live trace · activations + readout
  captured · causal/control not yet run · verdict held for review".)
- Verdict: **`FLAG_FOR_HUMAN_REVIEW`** (not ACCEPT, not SUPPRESS).
- **Proof chips:**
  | Chip | Expected status |
  |---|---|
  | Model proof | **present** |
  | CAS readout | **present** |
  | Output proof | **present** |
  | Packet proof | **present** |
  | Causal proof | **unavailable** |
  | Control proof | **unavailable** |
- An **Evidence Packet** is written to the packet store and a **harvest record**
  is appended (joinable on `trace_id`). The cockpit deep link is
  `/cockpit?trace_id=<trace_id>`.

> A live-worker **connection-state indicator** may also appear in the UI. Treat
> it as a nice-to-have signal only — do **not** gate your read of success on it.
> The authoritative success signals are the banner, verdict, and proof chips
> above.

<a name="why-no-accept"></a>
### Why no ACCEPT?

The verdict gate requires causal (ablation/intervention) **and** control
(matched-control) proofs to be `present` before it will issue ACCEPT/SUPPRESS.
This first live slice captures real model I/O + activations/readout but does
**not** run ablation or matched controls, so `causal_proof` and `control_proof`
are `unavailable`, and the gate correctly holds the audit at
`FLAG_FOR_HUMAN_REVIEW`. A live open-weight run landing at human review is the
**honest, expected** outcome — a green ACCEPT here would be fabricated.

---

<a name="if-it-fails"></a>
## If it fails

The system is built to fail **honestly**, never to invent a passing verdict.

- **Worker unreachable / tunnel down / `ATLAS_LIVE_WORKER_URL` unset.** The
  `/run` call marks the session **FAILED** with a message like "Live hosted
  open-weight runner failed: …". It does **not** emit a fake ACCEPT and does
  **not** write a verdict. Fix the tunnel (step 1), confirm
  `curl http://127.0.0.1:18080/health/realmode`, confirm the API env has
  `ATLAS_LIVE_WORKER_URL`, then re-run.
- **`/health/realmode` shows `is_real_model: false`.** The worker is in demo
  mode (no weights loaded, or `LIVE_TRACE_DEMO_MODE=1`). Output is synthetic and
  the harvest is flagged `model_io_is_demo_fallback: true`. For a real audit,
  load the actual weights on the pod; otherwise proceed knowing it is demo.
- **Audit Console calls 404 in dev.** See the dev-proxy gotcha below.

<a name="known-dev-proxy-gotcha"></a>
### Known dev-proxy gotcha (set `VITE_ATLAS_API_BASE_URL`)

The Vite dev server proxies `/api/*` to the backend and **strips the `/api`
prefix** (`/api/atlas/x` -> backend `/atlas/x`). That rewrite is correct for the
Atlas routes (router prefix `/atlas/live`) but the CAS Harness audit router is
mounted at prefix **`/api/cas-harness/audit`**. So a relative call to
`/api/cas-harness/audit/session` gets rewritten to
`/cas-harness/audit/session` and **404s** against the backend.

Workaround (no code change): set `VITE_ATLAS_API_BASE_URL=http://localhost:8000/atlas`
before `npm run dev` (as in step 3). The audit API client derives an **absolute**
base (`http://localhost:8000/api/cas-harness/audit`) from that value, bypassing
the rewriting proxy and hitting the router at its real path. If you start the
frontend without this env var and the Audit Console 404s, this is why.

---

## 5. Verify the persisted evidence (optional, from the API host)

After a successful run, the trace is queryable and the harvest is on disk:

```bash
# Replace <trace_id> with the value shown in the UI / deep link.
curl -s "http://localhost:8000/api/cas-harness/audit/session/<audit_id>/status"
```

The Evidence Packet lives under the packet store dir
(`CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR`, default a temp dir) and the harvest
record under `CAS_HARNESS_HARVEST_STORE_DIR/harvest.jsonl`. They join on
`trace_id`; the harvest carries `join: {key: trace_id, pairs_with: native_nl.v1}`
so it lines up with the CAS SDG output for CAS-Native training.

---

<a name="appendix-a-no-pod-local-demo-worker"></a>
## Appendix A — No pod? Local demo worker

To exercise the full UI flow with no GPU, run the worker locally in demo mode
instead of opening a tunnel:

```bash
cd noetic-compass-scaffold/noetic-compass/live-trace-worker
LIVE_TRACE_DEMO_MODE=1 uvicorn app.main:app --port 18080
```

Then continue from step 2 with `ATLAS_LIVE_WORKER_URL=http://127.0.0.1:18080`.
Everything works identically — Evidence Packet, harvest, proof chips, the teal
`open_weight_live_trace` banner, and `FLAG_FOR_HUMAN_REVIEW` — except:

- `/health/realmode` reports `is_real_model: false`.
- Output is schema-valid but **synthetic** (a fixed demo stream).
- The harvest record is flagged **`model_io_is_demo_fallback: true`** so the
  synthetic text never silently enters a training corpus.

This is the same demo path the automated E2E test
(`tests/test_cas_harness_live_worker_e2e.py`) drives when no live worker is
reachable.

---

## Quick reference

| Thing | Value |
|---|---|
| Worker local port (tunnel) | `18080` |
| `ATLAS_LIVE_WORKER_URL` | `http://127.0.0.1:18080` |
| Worker health (real check) | `GET /health/realmode` |
| API launch | `uvicorn api.main:app --reload --port 8000` |
| Frontend launch | `cd atlas-viewer && VITE_ATLAS_API_BASE_URL=http://localhost:8000/atlas npm run dev` |
| Audit Console route | `/audit-console` |
| Model target | `EleutherAI/pythia-160m` |
| Expected verdict | `FLAG_FOR_HUMAN_REVIEW` |
| Audit scope | `open_weight_live_trace` (teal banner) |
| Cockpit deep link | `/cockpit?trace_id=<trace_id>` |
| Tunnel script | `live-trace-worker/scripts/open_atlas_live_tunnel.sh` |
| Local demo worker | `LIVE_TRACE_DEMO_MODE=1 uvicorn app.main:app --port 18080` |
