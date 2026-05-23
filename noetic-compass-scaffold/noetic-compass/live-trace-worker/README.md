# Atlas live-trace worker

Private FastAPI service that runs the model (Pythia-160M at v0.1) and the
probe pipeline, and streams trace events as Server-Sent Events for the
Atlas Viewer cockpit.

This worker lives **behind** the noetic-compass-api proxy. Browsers never
hit it directly. The flow:

```
Atlas Viewer UI
  → noetic-compass-api    (validates user / license / API key)
  → live-trace-worker     (runs Pythia + probes, streams SSE)
  → noetic-compass-api    (passes SSE through)
  → Atlas Viewer UI       (animates the cockpit in real time)
```

## Milestone status

- **M1 — scaffold + fake trace.** Merged. Routes, schemas, Dockerfile,
  fake event stream emitting schema-valid events.
- **M2 (this PR) — real Pythia + probes.** Adds `runtime/pythia_runner.run_pythia`
  driving Pythia-160M one token at a time, `runtime/probe_runner.capture_probes`
  registering forward hooks on each layer's MLP, and a real-vs-fake
  dispatcher (`runtime/event_stream.stream_trace`). Demo-mode fallback
  remains for CI / local dev (`LIVE_TRACE_DEMO_MODE=1`, missing torch, or
  failed load). `manifest.is_real_model` flips to true ONLY when weights
  are actually loaded. Acceptance gate in `M2_ACCEPTANCE.md`.
- **M3 — api proxy.** Add `POST /api/atlas/live/session` +
  `GET .../events` to `noetic-compass-api/routes/atlas_live.py`.
  Auth: invite-code allowlist + per-IP rate limit + short-lived stream token.
- **M4 — UI toggle.** Wire LIVE/REPLAY mode toggle in the Atlas Viewer
  cockpit. REPLAY stays the default + fallback.
- **v0.2 — adapters.** OLMo / Qwen adapters once Pythia path is stable.

## Local development

```bash
cd noetic-compass-scaffold/noetic-compass/live-trace-worker
python -m venv .venv
. .venv/Scripts/activate      # Windows
# . .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Then:

```bash
# Health
curl http://localhost:8080/health

# Start a session
curl -X POST http://localhost:8080/sessions \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"I noticed a warm coffee cup on the table.","seed":42}'

# Subscribe to the SSE stream (replace <id> with the returned session_id)
curl -N http://localhost:8080/sessions/<id>/events

# Or get the full event list as JSON (test/debug helper)
curl -X POST http://localhost:8080/sessions/dump \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"I noticed a warm coffee cup.","seed":42}'
```

## Tests

```bash
cd noetic-compass-scaffold/noetic-compass/live-trace-worker
pytest
```

## RunPod deploy

The `Dockerfile` is currently CPU-only (milestone 1). At milestone 2 we
swap the base to a CUDA pytorch image and update `requirements.txt` to
pull torch / transformers / accelerate.

Deploy target — TBD (always-on pod vs serverless vs on-demand). Tracked
as a decision before milestone 2 ships.

## Security posture

- **No public exposure.** The worker MUST sit on a private network or
  behind an auth gate. The noetic-compass-api proxy is the only allowed
  caller.
- **No user-identifying data.** The worker only sees session IDs +
  prompts. User identity is the API's responsibility.
- **No persistence at m1.** Sessions live in-memory; restarts clear
  state. Persistence (and Redis fanout) lands at m2 or later if needed.

## Why this folder, not its own repo

See [memory: project_atlas_live_worker_scope_2026_05_23.md]. Short
version: it's product infrastructure now, not loose research code; it
needs to stay version-aligned with `api/`, `atlas-viewer/`, the evidence
schemas, and probe manifests; one repo keeps deploy review simple.
