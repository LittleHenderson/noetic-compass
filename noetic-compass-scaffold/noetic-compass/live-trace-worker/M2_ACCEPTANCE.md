# M2 acceptance gate

Per the locked spec:

> - `/health` reports model loaded
> - `/manifest` says EleutherAI/pythia-160m
> - one live session streams real token events
> - events remain deterministic enough for tests where seeded
> - provenance clearly says real model / real weights / live trace
> - tests pass
> - Docker builds for RunPod

This doc is the manual checklist the user (or whoever's promoting M2)
walks through on a RunPod box to confirm the real path actually works.
CI cannot run this — no GPU on GitHub Actions free tier — so the
checklist lives here in lockstep with the M2 code.

## Step 1 — local-dev demo-mode tests (CI also runs these)

```bash
cd noetic-compass-scaffold/noetic-compass/live-trace-worker
pip install -r requirements.txt
pytest -v
```

Expected: all tests pass. Real-model tests are skipped (no torch + no GPU);
demo-mode tests + schema-contract tests run.

## Step 2 — Docker build smoke

```bash
docker build -t atlas-live-trace-worker:m2 \
  noetic-compass-scaffold/noetic-compass/live-trace-worker/
```

Expected: build succeeds, image is roughly 6 GB (CUDA base) plus the
Pythia-160M cache (~700 MB). Pre-cache step may warn if the build
environment can't reach huggingface.co — that's fine; weights load on
first request instead.

## Step 3 — RunPod boot

Push the image to your registry; spin up an always-on pod with one of:

* GPU: RTX A4000 / A5000 / 4090 — any modern card with ≥ 8 GB VRAM
* CPU/RAM: 4 vCPU / 16 GB is plenty
* Storage: 20 GB volume

Expose port 8080 on the pod's HTTPS endpoint.

## Step 4 — `/health` reports model loaded

```bash
curl https://<pod>.proxy.runpod.net/health
```

Expected JSON:

```json
{
  "status": "ok",
  "worker_version": "m2-real-pythia",
  "model_id": "EleutherAI/pythia-160m",
  "is_real_model": true,
  "model_loaded": true,
  "load_error": null
}
```

If `is_real_model: false` or `load_error` is populated, the load failed.
Common causes:

* CUDA not visible — confirm pod has a GPU attached.
* Huggingface cache empty + no network — re-build image with pre-cache,
  or warm the cache manually inside the pod (`python -c "..."`).
* OOM during load — Pythia-160M is small (~700 MB VRAM) but if another
  process is on the GPU, free it.

## Step 5 — `/manifest` says EleutherAI/pythia-160m

```bash
curl -X POST https://<pod>.proxy.runpod.net/sessions \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"I noticed a warm coffee cup beside an open book.","seed":42,"max_new_tokens":8}'
```

Take the returned `session_id`, then:

```bash
curl https://<pod>.proxy.runpod.net/sessions/<id>/manifest
```

Expected: full ModelManifest with `is_real_model: true`.

## Step 6 — one live session streams real token events

```bash
curl -N https://<pod>.proxy.runpod.net/sessions/<id>/events
```

Expected sequence:

1. `event: manifest` with `is_real_model: true` (NOT false — that's demo mode)
2. `event: neuron_covers` with the selected Stage 27F calibrated F1-F7 cover
   sets (`scope=all_7` emits all 28 Foundation class covers)
3. `event: token` × max_new_tokens — each with:
   * `token` decoded by the Pythia tokenizer (NOT the whitespace-split
     stand-in; real BPE produces e.g. `" the"` with leading space)
   * `top_activated_neurons` with real-looking values (not the
     `random.uniform(0.30, 0.95)` ranges from demo mode — real MLP
     post-activations have a wider dynamic range, often centred near 0)
   * `mode7_attribution` with weights summing to <= 1 (real attention
     probs) and from_token_index pointing into the prompt
   * `confidence` from softmax-margin (often 0.1–0.6 for natural text;
     demo mode is always 0.55–0.95)
4. `event: complete` with total_tokens matching what was emitted

## Step 7 — determinism under seed

Run step 6 twice with the same seed + same prompt + temperature=0. The
token_text sequence MUST match exactly. The activation numbers will match
exactly too (deterministic on CPU + GPU at the same precision).

## Step 8 — provenance shows in the cockpit

When M4 (UI toggle) lands, opening a live session through the cockpit
must paint the teal "Live · EleutherAI/pythia-160m · actual weights"
badge — NOT the amber "demo fixture" badge. The cockpit reads this from
the first event's `manifest.is_real_model` field.

## Failure-mode regression — demo fallback

Force-disable torch on the pod:

```bash
LIVE_TRACE_DEMO_MODE=1 uvicorn app.main:app --port 8080
```

`/health` should now show `is_real_model: false`, `model_loaded: false`.
A live session should still stream — but with demo-mode payloads (random
activations, whitespace-split tokens). The cockpit's badge should swap
to "Live mode unavailable — replaying demo trace."

This proves the fallback works and that the cockpit will never silently
overclaim live-model status.
