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

The `Dockerfile` is the preferred production artifact. For the current
always-on alpha pod, there is also a restart-safe RunPod bootstrap path in
`scripts/`:

```bash
cd /workspace/atlas-live-worker-current
cp scripts/runpod_start_atlas_live_worker.sh /root/start-atlas-live-worker.sh
cp scripts/runpod_start_atlas_live_worker.sh /workspace/start-atlas-live-worker.sh
cp scripts/runpod_pre_start.sh /pre_start.sh
chmod +x /root/start-atlas-live-worker.sh /workspace/start-atlas-live-worker.sh /pre_start.sh
/root/start-atlas-live-worker.sh
```

Why this path exists:

- RunPod's template starts `/start.sh` as PID 1, not systemd.
- `/start.sh` automatically runs `/pre_start.sh` when present.
- Long-running Python from `/workspace` can hang if the FUSE mount stalls.
- The startup script syncs source into `/root/atlas-live-worker-run`, runs
  from `/root/atlas-live-worker-venv`, forces `LIVE_TRACE_USE_FAKE=0`, and
  verifies `/health/realmode` before the API is allowed to claim real weights.

Verification:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/health/realmode
curl https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

The real-mode endpoint must show:

```json
{
  "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
  "is_real_model": true,
  "fake_runtime_env": false,
  "model_loaded": true,
  "load_error": null
}
```

If it does not, the cockpit must say the model is not connected or not
verified. It must not claim "actual weights."

## Distributed fleet worker daemon

The API fleet executor can now be driven by this worker process:

```bash
python scripts/run_fleet_worker.py \
  --api-base-url https://noetic-compass-api.onrender.com \
  --audit-id <cas-dist-id> \
  --worker-id probe-worker-001 \
  --model-id <exact-open-weight-model-id> \
  --tenant-id "$CAS_FLEET_TENANT_ID" \
  --service-credential "$CAS_FLEET_SERVICE_CREDENTIAL" \
  -- python scripts/run_open_weight_probe_shard.py
```

In account mode, an owner/admin/operator first issues that worker-scoped secret with
`POST /api/cas-harness/audit/distributed/session/{audit_id}/fleet/service-credentials`.
The request names this exact `worker_id` and only the capabilities the daemon needs:
`register_worker`, `heartbeat`, `lease_job`, and `submit_receipt`. The response returns
`api_credential` once; store it as `CAS_FLEET_SERVICE_CREDENTIAL`, keep the matching
tenant in `CAS_FLEET_TENANT_ID`, and never place either in browser code. Every daemon
callback carries a fresh timestamp and one-time nonce. Customer Bearer tokens are not
valid worker credentials when `NC_FLEET_SERVICE_AUTH_ENABLED=true`. The old
`--bearer-token` option exists only for the default-dark/legacy posture.

The command after `--` is the real probe executor. It receives the assigned
layer/shard job through environment variables such as `CAS_FLEET_LAYER_START`,
`CAS_FLEET_LAYER_END`, `CAS_FLEET_ASSIGNED_METHODS_JSON`, and
`CAS_FLEET_RESULT_PATH`. It must write:

```json
{
  "produced_outputs": ["layer_activation_summary"],
  "missing_outputs": ["cas_axis_readout"],
  "error_message": null
}
```

The daemon then writes a local Evidence Packet fragment and posts the
content-addressed `cas-fragment://.../sha256:<digest>` receipt back to the API.

For deployment smoke checks only, `--dry-run` can exercise the lease/receipt
control plane without claiming model inference:

```bash
python scripts/run_fleet_worker.py ... --dry-run
```

Do not use dry-run output as customer audit evidence. A real large-model audit
requires open weights, the actual probe command, assigned workers, receipts, a
merged Evidence Packet, and the final verifier decision layer.

The included open-weight shard command is strict about proof inputs:

```bash
CAS_FLEET_SCENARIO_PATH=/workspace/cas/scenarios/alpha_25.json \
CAS_FLEET_PROBE_WEIGHTS_PATH=/workspace/cas/probes/gpt-neox-20b_probe.json \
CAS_FLEET_COVER_MAP_PATH=/workspace/cas/covers/gpt-neox-20b_covers.json \
python scripts/run_fleet_worker.py \
  --api-base-url https://noetic-compass-api.onrender.com \
  --audit-id <cas-dist-id> \
  --worker-id probe-worker-001 \
  --model-id EleutherAI/gpt-neox-20b \
  --tenant-id "$CAS_FLEET_TENANT_ID" \
  --service-credential "$CAS_FLEET_SERVICE_CREDENTIAL" \
  -- python scripts/run_open_weight_probe_shard.py
```

If the model cannot load, the command writes a failed result. If probe weights
or cover maps are missing, it does not fake `cas_axis_readout` or
`blindspot_overlay`; it reports those outputs as missing so the verifier gate
stays blocked.

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
