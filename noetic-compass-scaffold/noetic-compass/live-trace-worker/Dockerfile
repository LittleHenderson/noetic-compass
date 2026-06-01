# Atlas live-trace worker — real Pythia-160M on a RunPod GPU.
#
# Base image ships CUDA-aware torch so we don't pay torch's ~2 GB wheel
# download as a separate layer. The runtime variant (no build tools) keeps
# the image under ~6 GB. Pythia-160M fits in ~700 MB of VRAM; any RunPod GPU
# from the smallest tier (e.g. RTX A4000) works — do NOT over-provision.
#
# This image is self-contained and exposure-ready: it bakes the HF +
# FastAPI stack, pre-pulls pythia-160m, serves app.main:app on
# ${PORT:-8080}, EXPOSEs that port for the RunPod HTTP proxy, and keeps the
# demo-mode fallback when torch is absent. App-level auth is OPTIONAL and
# OFF by default (set ATLAS_LIVE_WORKER_TOKEN to require X-Atlas-Worker-Token).
# See docs/working/atlas_live_worker_launch_grade_exposure_2026_05_31.md.

FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

LABEL org.opencontainers.image.title="atlas-live-trace-worker" \
      org.opencontainers.image.description="Private FastAPI worker: Pythia-160M + probe pipeline, SSE trace stream, behind the noetic-compass-api proxy." \
      org.opencontainers.image.source="https://github.com/noetic-compass/noetic-compass"

WORKDIR /worker

# Pin the Hugging Face cache to a stable, well-known location. When the image
# is run with a RunPod network volume mounted at /workspace, point HF_HOME
# there at runtime to reuse the warmed cache across restarts; otherwise the
# weights baked below are used.
ENV HF_HOME=/worker/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install Python deps. torch is already in the base image; we only add the
# Hugging Face + FastAPI stack on top.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Pre-download Pythia-160M weights into the HF cache during the image build.
# This adds ~700 MB to the image but turns the first session request from
# "cold-load + run" into just "run" — the first-click responsiveness we chose
# the always-on pod for. Non-fatal: if the build host has no network, the
# model loads on first warm_load instead (and demo mode covers the gap).
RUN python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
  AutoTokenizer.from_pretrained('EleutherAI/pythia-160m'); \
  AutoModelForCausalLM.from_pretrained('EleutherAI/pythia-160m')" || \
  echo "Pre-cache failed (network?); model will load on first warm_load instead."

# Document the served port for the RunPod HTTP proxy / reverse proxies.
EXPOSE 8080

# Liveness probe hits /health (always reachable; exempt from the optional
# worker-token gate). Uses python's stdlib so we don't depend on curl being
# present in the runtime base image. Honors $PORT.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request,sys; \
  url='http://127.0.0.1:%s/health' % os.environ.get('PORT','8080'); \
  sys.exit(0 if urllib.request.urlopen(url, timeout=4).status==200 else 1)" || exit 1

# Single uvicorn worker — concurrency comes from async event streams, not OS
# processes. Two workers on the same GPU would race for forward hooks.
# ${PORT:-8080} so an empty/unset PORT still binds the canonical default.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
