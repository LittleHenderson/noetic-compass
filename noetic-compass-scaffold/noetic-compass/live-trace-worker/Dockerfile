# Milestone 1 — CPU-only scaffold image. Lightweight; just FastAPI + Pydantic.
# Milestone 2 swaps the base to a CUDA-equipped pytorch image (e.g.
# pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime) once we load real weights.

FROM python:3.11-slim

WORKDIR /worker

# Install Python deps first so layer caching survives source edits.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# RunPod and most reverse proxies expect the service on $PORT. Default to
# 8080 so the local-dev defaults match production.
ENV PORT=8080

# Bind to 0.0.0.0 so RunPod's port mapping reaches the worker. We keep
# uvicorn single-worker at m1 — concurrency comes from async event streams,
# not OS processes. Milestone 2 may raise this once GPU sessions are
# bounded.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
