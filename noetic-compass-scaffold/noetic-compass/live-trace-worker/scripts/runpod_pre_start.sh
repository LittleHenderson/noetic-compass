#!/usr/bin/env bash
set +e

# RunPod's /start.sh executes /pre_start.sh if it exists. This wrapper is
# intentionally non-fatal: a worker boot failure must not take SSH access down
# with the container. The health endpoints and API proof route are responsible
# for refusing to claim LIVE real weights when the worker is unavailable.
#
# IMPORTANT — restart resilience. The pod root filesystem (/) is an ephemeral
# overlay: /pre_start.sh, the venv, and the HuggingFace cache are ALL wiped on a
# real pod restart. Only /workspace (the RunPod network volume) persists. So:
#
#   1. This hook must be RESTORED from /workspace before /start.sh runs it.
#      /start.sh is baked into the image and only does `bash /pre_start.sh` if
#      the file exists, with no env hook to point elsewhere. Set the pod's
#      RunPod start / Docker command to restore it first, e.g.:
#        bash -c '[ -f /workspace/pre_start.sh ] && cp /workspace/pre_start.sh /pre_start.sh; /start.sh'
#      (Install: cp this file to /workspace/pre_start.sh on the persistent volume.)
#
#   2. The venv and model cache are pinned to /workspace below so a cold start
#      does NOT rebuild the venv or re-download the model, and does not depend on
#      PyPI / HuggingFace being reachable at boot. Verified cold-start recovery
#      (with /root wiped) reaches REAL_PYTHIA_WEIGHTS_LOADED in ~25s.

# 8080, NOT 8888 — jupyter-lab owns 8888 in the RunPod template.
export ATLAS_LIVE_WORKER_PORT="${ATLAS_LIVE_WORKER_PORT:-8080}"
export ATLAS_LIVE_SOURCE_DIR="${ATLAS_LIVE_SOURCE_DIR:-/workspace/atlas-live-worker-current}"
# Persistent venv + model cache (survive a real pod restart).
export ATLAS_LIVE_VENV_DIR="${ATLAS_LIVE_VENV_DIR:-/workspace/atlas-live-worker-venv}"
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"

if [ ! -x /root/start-atlas-live-worker.sh ] && [ -f /workspace/start-atlas-live-worker.sh ]; then
  cp /workspace/start-atlas-live-worker.sh /root/start-atlas-live-worker.sh
  chmod +x /root/start-atlas-live-worker.sh
fi

if [ -x /root/start-atlas-live-worker.sh ]; then
  /root/start-atlas-live-worker.sh
else
  echo "Atlas live worker startup script missing; leaving pod online for SSH repair."
fi

exit 0
