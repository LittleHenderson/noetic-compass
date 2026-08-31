"""gpu_guard.py -- fail-closed GPU requirement (owner law: GPU-first / cloud-first).

Every neural entry point calls require_gpu() FIRST. There is no CPU fallback flag
on any claim-bearing path: a box without CUDA raises GpuRequiredError("GPU_REQUIRED")
before any data is touched. CPU-only SHAPE tests construct the head modules
directly with synthetic tensors and never pass through a guarded entry point --
that is the one owner-authorized CPU use (audit 2026-08-31 section 2).
"""
from __future__ import annotations


class GpuRequiredError(RuntimeError):
    """Raised when a claim-bearing neural entry point finds no CUDA device."""


def require_gpu() -> str:
    import torch
    if not torch.cuda.is_available():
        raise GpuRequiredError(
            "GPU_REQUIRED: claim-bearing neural work runs on AWS GPU only; "
            "no silent CPU fallback (owner law 2026-08-30)")
    return f"cuda:{torch.cuda.current_device()}"
