# M2 — real Pythia-160M on RunPod GPU. Base image ships CUDA-aware torch
# so we don't pay torch's 2 GB wheel download as a separate layer.
#
# pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime — runtime variant (no
# build tools), keeps the image under 6 GB. Pythia-160M fits in ~700 MB
# of VRAM; any RunPod GPU from the smallest tier (e.g. RTX A4000) works.

FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

WORKDIR /worker

# Install Python deps. torch is already in the base; we only add the HF +
# FastAPI stack on top.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# RunPod and most reverse proxies use $PORT. 8080 is the canonical default
# matching our local-dev setup.
ENV PORT=8080

# Pre-download Pythia-160M weights into the HF cache during the image
# build. This adds ~700 MB to the image but turns the first session
# request from "cold-load + run" into just "run" — exactly the kind of
# first-click responsiveness we picked the always-on pod for.
RUN python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
  AutoTokenizer.from_pretrained('EleutherAI/pythia-160m'); \
  AutoModelForCausalLM.from_pretrained('EleutherAI/pythia-160m')" || \
  echo "Pre-cache failed (network?); model will load on first warm_load instead."

# Single uvicorn worker — concurrency comes from async event streams,
# not OS processes. Two workers on the same GPU would race for hooks.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
