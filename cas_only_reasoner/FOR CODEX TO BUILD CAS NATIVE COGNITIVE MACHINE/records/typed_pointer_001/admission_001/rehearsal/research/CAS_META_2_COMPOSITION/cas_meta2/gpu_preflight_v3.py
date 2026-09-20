"""Future, unwired AWS-only preflight with an enforced workspace-cleanup gate.

This does not replace v2, amend its receipts, or run a learning experiment. The
geometry routine is reused from exact frozen source bytes. It requires an idle,
single-visible-GPU process: other live tensors are a refusal, not something to
delete. Cold, warm-cache and repeated calls must end with zero live allocations.

Workspace clearing is version-bound to the documented PyTorch 2.11 API:
https://docs.pytorch.org/docs/2.11/notes/cuda.html#cublas-workspaces
https://github.com/pytorch/pytorch/blob/v2.11.0/aten/src/ATen/cuda/CublasHandlePool.cpp

No environment or deterministic numerical setting is changed here. The caller
must already have established the registered settings. Flags alone do not prove
AWS identity or spending approval; the separate launcher must bind those.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gc
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parent
GEOMETRY_SOURCE_SHA = "410bce98307a5644db51928459b73391c7066b72"
PINNED_GEOMETRY_FILES = {
    "__init__.py": "07b7b2f1a52806b819e3820655fa578f3e5241ce2327695f157e542ce06a63da",
    "gpu_preflight_v2.py": "afe77f0ff9b5fa57952de6d0740c6a1ce9cec80da57973ecccb2713c9b3444d0",
    "policy.py": "6d5f3cbfc455c65ef9000c5145f8f5b691668fb355339eeebd61e4aa2b8d26d0",
    "features_v2.py": "79dd26ad6183cde7e586dda2cd1b65d812e601e793d5c60e0658ad886c09b4dc",
    "codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
    "ir.py": "02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637",
    "train_v2.py": "882976ac24fb808c2da8ab5e1a5f80388946693077e7dfdfd7a00d4e029c0665",
}
TORCH_VERSION = "2.11.0+cu128"
CUDA_VERSION = "12.8"
WORKSPACE_API = "torch._C._cuda_clearCublasWorkspaces"
WORKSPACE_DOCUMENTATION = "https://docs.pytorch.org/docs/2.11/notes/cuda.html#cublas-workspaces"
SCHEMA = "cas-meta2-gpu-preflight/3"


class GPUPreflightError(RuntimeError):
    pass


def _require(condition, reason):
    if not condition:
        raise GPUPreflightError(reason)


def _time_left(deadline):
    _require(type(deadline) in (int, float) and math.isfinite(deadline)
             and time.monotonic() < deadline, "V3_GPU_PREFLIGHT_DEADLINE")


def _source_identity():
    """Literal committed hashes work in an archive without claiming a Git query."""
    for name, expected in PINNED_GEOMETRY_FILES.items():
        path = ROOT / name
        _require(path.is_file() and not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
                 for item in (path, *path.parents)), "V3_GEOMETRY_SOURCE_PATH_INVALID:" + name)
        _require(sha256(path.read_bytes()).hexdigest() == expected, "V3_FROZEN_GEOMETRY_SOURCE_CHANGED:" + name)
        module_name = "cas_meta2" if name == "__init__.py" else "cas_meta2." + path.stem
        module = sys.modules.get(module_name)
        if module is not None:
            _require(getattr(module, "__file__", None) is not None
                     and Path(module.__file__).resolve() == path.resolve(),
                     "V3_LOADED_GEOMETRY_MODULE_PATH_MISMATCH:" + module_name)
    return {"declared_source_sha": GEOMETRY_SOURCE_SHA,
            "files_sha256": dict(PINNED_GEOMETRY_FILES),
            "verification": "Literal pinned file hashes; no runtime Git-object query."}


def _load_runtime():
    # This is the only Torch import in this module, after caller authorization.
    import torch
    return torch


def _settings(torch):
    return {"CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "tf32_matmul": torch.backends.cuda.matmul.allow_tf32,
            "tf32_cudnn": torch.backends.cudnn.allow_tf32,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic}


def _checked_runtime(torch, receipt):
    versions = {"torch": str(torch.__version__), "cuda": torch.version.cuda}
    receipt["runtime_versions"] = versions
    _require(versions == {"torch": TORCH_VERSION, "cuda": CUDA_VERSION},
             "V3_WORKSPACE_API_UNSUPPORTED_RUNTIME_VERSION")
    clear = getattr(getattr(torch, "_C", None), "_cuda_clearCublasWorkspaces", None)
    _require(callable(clear), "V3_DOCUMENTED_WORKSPACE_CLEAR_API_UNAVAILABLE")
    receipt["workspace_cleanup_api"] = {"name": WORKSPACE_API, "callable_verified": True,
        "documented_version": "2.11", "documentation": WORKSPACE_DOCUMENTATION}
    _require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
             "V3_ONE_VISIBLE_CUDA_DEVICE_REQUIRED_NO_CPU_FALLBACK")
    device = torch.device("cuda:0")
    properties = torch.cuda.get_device_properties(device)
    _require("T4" not in properties.name.upper(), "V3_T4_FORBIDDEN")
    receipt.update(device=str(device), gpu_name=properties.name,
                   gpu_total_memory_bytes=int(properties.total_memory))
    settings = _settings(torch)
    _require(settings == {"CUBLAS_WORKSPACE_CONFIG": ":4096:8", "deterministic_algorithms": True,
        "tf32_matmul": False, "tf32_cudnn": False, "cudnn_benchmark": False, "cudnn_deterministic": True},
        "V3_REGISTERED_DETERMINISTIC_SETTINGS_REQUIRED")
    receipt["numerical_settings_before"] = settings
    return device


def _memory(torch, device):
    values = {"allocated_bytes": torch.cuda.memory_allocated(device),
              "reserved_bytes": torch.cuda.memory_reserved(device)}
    _require(all(type(value) is int and value >= 0 for value in values.values()), "V3_INVALID_MEMORY_COUNTER")
    return values


def _cleanup(torch, device, receipt, phase):
    record = {"completed": False, "steps": [], "before": _memory(torch, device)}
    receipt.setdefault("cleanup", {})[phase] = record
    # No model or exception frame is alive here. Synchronize before freeing
    # shared BLAS workspaces; this contract does not permit concurrent GPU work.
    torch.cuda.synchronize(device)
    record["steps"].append("synchronize_before")
    gc.collect()
    record["steps"].append("collect_python_cycles")
    torch._C._cuda_clearCublasWorkspaces()
    record["steps"].append("clear_documented_cublas_and_cublaslt_workspaces")
    torch.cuda.empty_cache()
    record["steps"].append("empty_cuda_allocator_cache")
    torch.cuda.synchronize(device)
    record["steps"].append("synchronize_after")
    record["after"] = _memory(torch, device)
    record["completed"] = True
    return record["after"]


def _run_geometry(train_tasks, config, receipt, deadline, torch, device):
    _source_identity()
    frozen = importlib.import_module("cas_meta2.gpu_preflight_v2")
    _source_identity()
    frozen._execute(train_tasks, config, receipt, deadline, torch, device)


def _failure(receipt, stage, error):
    receipt.setdefault("failures", []).append({"stage": stage, "type": type(error).__name__,
        "message": str(error), "traceback": traceback.format_exc()})


def _save(path, receipt):
    # Serialize before opening the new file, so a serialization failure cannot
    # leave half of a JSON receipt that looks like a completed result.
    payload = json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _safe_diagnostics(value, path="receipt", failures=None):
    """Preserve invalid metric types as labelled data, never as valid numbers."""
    failures = [] if failures is None else failures
    if value is None or type(value) in (str, bool, int):
        return value, failures
    if type(value) is float:
        if math.isfinite(value):
            return value, failures
        failures.append(path)
        return {"invalid_nonfinite_float": str(value)}, failures
    if type(value) is list:
        return [_safe_diagnostics(item, path + "/" + str(index), failures)[0]
                for index, item in enumerate(value)], failures
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _safe_diagnostics(item, path + "/" + key, failures)[0]
                for key, item in value.items()}, failures
    failures.append(path)
    return {"invalid_metric_type": type(value).__name__}, failures


def run_preflight(train_tasks, config, output, deadline):
    """Future candidate only; return success after exact zero-allocation cleanup.

    Uses only caller-designated training tasks. No checkpoint, private test
    label, native result, optimizer update, or external provider API is used.
    CUDA cleanup does not replace the launcher's independent wall-clock cutoff.
    """
    raw_path = Path(output).absolute() / "gpu_preflight_v3.json"
    _require(not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
             for item in (raw_path, *raw_path.parents)), "V3_RECEIPT_LINK_REFUSED")
    directory = raw_path.parent.resolve()
    path = directory / raw_path.name
    _require(directory.is_dir() and not path.exists(), "V3_NEW_RECEIPT_IN_EXISTING_OUTPUT_REQUIRED")
    started = time.monotonic()
    receipt = {"schema": SCHEMA, "status": "CAS_META_2_V3_GPU_PREFLIGHT_RUNNING", "completed": False,
        "stage": "authorization", "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "candidate_only": True, "wired_into_frozen_v2": False,
        "model_training_performed": False, "optimizer_updates": 0, "native_execution_performed": False,
        "held_out_labels_accessed": False, "geometry_checks_completed": False,
        "memory_contract": "Idle single-device process; zero live allocations after symmetric workspace/cache cleanup, not a warmed baseline allowance.",
        "boundary": "Forward/backward preflight only. No learning result or full-run acceptance. Peak memory excludes optimizer state, open generation and native evaluation."}
    runtime, device = None, None
    try:
        job = os.environ.get("CAS_META2_AWS_JOB_ID", "")
        _require(os.environ.get("CAS_META2_RUN_GPU_TESTS") == "1"
                 and re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", job) is not None,
                 "V3_AWS_PREFLIGHT_AUTHORIZATION_REQUIRED")
        receipt["aws_job_id"] = job
        _time_left(deadline)
        receipt["geometry_source"] = _source_identity()
        receipt["stage"] = "runtime_guard"
        runtime = _load_runtime()
        device = _checked_runtime(runtime, receipt)
        receipt["stage"] = "baseline_cleanup"
        receipt["entry_memory"] = _memory(runtime, device)
        baseline = _cleanup(runtime, device, receipt, "baseline")
        receipt["cuda_allocated_bytes_before"] = baseline["allocated_bytes"]
        receipt["cuda_reserved_bytes_before"] = baseline["reserved_bytes"]
        _require(baseline["allocated_bytes"] == 0, "V3_PREFLIGHT_PROCESS_NOT_IDLE_LIVE_ALLOCATIONS")
        runtime.cuda.reset_peak_memory_stats(device)
        _time_left(deadline)
        receipt["stage"] = "geometry_checks"
        _run_geometry(train_tasks, config, receipt, deadline, runtime, device)
        receipt["geometry_checks_completed"] = True
        _time_left(deadline)
        _require(_source_identity() == receipt["geometry_source"], "V3_GEOMETRY_SOURCE_CHANGED_DURING_CHECK")
    except BaseException as error:
        _failure(receipt, receipt["stage"], error)
    # Exception references and the geometry frame have now gone out of scope.
    if runtime is not None and device is not None:
        receipt["stage"] = "final_cleanup"
        try:
            receipt["peak_cuda_allocated_bytes"] = int(runtime.cuda.max_memory_allocated(device))
            receipt["peak_cuda_reserved_bytes"] = int(runtime.cuda.max_memory_reserved(device))
            final = _cleanup(runtime, device, receipt, "final")
            receipt["cuda_allocated_bytes_after_cleanup"] = final["allocated_bytes"]
            receipt["cuda_reserved_bytes_after_cleanup"] = final["reserved_bytes"]
            _require(final["allocated_bytes"] == receipt.get("cuda_allocated_bytes_before") == 0,
                     "V3_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED")
            receipt["memory_cleanup_confirmed"] = True
            after = _settings(runtime)
            receipt["numerical_settings_after"] = after
            _require(after == receipt["numerical_settings_before"], "V3_NUMERICAL_SETTINGS_CHANGED")
            _time_left(deadline)
        except BaseException as error:
            _failure(receipt, receipt["stage"], error)
    passed = (receipt["geometry_checks_completed"] and receipt.get("memory_cleanup_confirmed") is True
              and not receipt.get("failures"))
    receipt["completed"] = passed
    receipt["status"] = "CAS_META_2_V3_GPU_PREFLIGHT_PASSED" if passed else "CAS_META_2_V3_GPU_PREFLIGHT_FAILED"
    receipt["stage"] = "completed" if passed else "failed"
    receipt["wall_seconds"] = time.monotonic() - started
    receipt, invalid_metrics = _safe_diagnostics(receipt)
    if invalid_metrics:
        passed = False
        receipt.update(completed=False, stage="failed", status="CAS_META_2_V3_GPU_PREFLIGHT_FAILED")
        receipt.setdefault("failures", []).append({"stage": "receipt_serialization", "type": "ValueError",
            "message": "V3_INVALID_DIAGNOSTIC_METRIC", "metric_paths": invalid_metrics})
    _save(path, receipt)
    if not passed:
        reason = receipt.get("failures", [{"message": "V3_PREFLIGHT_INCOMPLETE"}])[0]["message"]
        raise GPUPreflightError(reason) from None
    return receipt
