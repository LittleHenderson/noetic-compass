# Atlas LIVE Verified Alpha State — 2026-05-25

Status: verified against deployed services.

## What Was Proven

The Atlas Viewer LIVE path is wired end-to-end:

```text
Atlas Viewer /cockpit
  -> noetic-compass-api
  -> RunPod live-trace worker
  -> EleutherAI/pythia-160m actual weights
  -> SSE stream
  -> real-model manifest + token events
```

## Public Endpoint

Atlas Viewer:

```text
https://atlas-viewer-app.onrender.com/cockpit
```

Real-mode proof endpoint:

```text
https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

Expected proof body:

```json
{
  "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
  "is_real_model": true,
  "fake_runtime_env": false,
  "model_loaded": true,
  "load_error": null,
  "manifest_is_real_model": true,
  "model_id": "EleutherAI/pythia-160m",
  "worker_version": "m2-real-pythia"
}
```

## Verification Commands

From:

```text
noetic-compass-scaffold/noetic-compass/atlas-viewer
```

Run:

```powershell
npm.cmd install
npm.cmd run build:e2e
$env:ATLAS_LIVE_E2E='1'
$env:ATLAS_LIVE_INVITE_CODE='<redacted alpha invite code>'
npx.cmd playwright test e2e/live.api.spec.ts --reporter=line
```

## Result

Verified on 2026-05-25:

```text
npm.cmd run build:e2e
Result: passed

npx.cmd playwright test e2e/live.api.spec.ts --reporter=line
Result: 2 passed
```

The two deployed tests prove:

1. `/live/health/realmode` reports `REAL_PYTHIA_WEIGHTS_LOADED` before the UI may claim actual weights.
2. A gated LIVE session opens, the SSE stream returns a `manifest` event with `is_real_model: true`, and at least one `token` event arrives.

## Current Boundaries

- Pythia-160M is the verified LIVE model for alpha.
- The browser still requires a valid Atlas LIVE invite code.
- Custom domains `api.noeticcompass.com` and `atlas.noeticcompass.com` were not part of this proof; the verified hosts are the Render URLs above.
- This proof establishes the live wiring and model connection. It does not by itself prove every future module/knob, scenario, or external model adapter.
