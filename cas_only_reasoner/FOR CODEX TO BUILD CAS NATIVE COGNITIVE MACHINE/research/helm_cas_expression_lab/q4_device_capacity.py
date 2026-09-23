"""Bounded admission for one smoke job on an explicitly shared Windows GPU.

This policy allows display contexts under measured headroom; it does not claim
exclusive access, identify human owners, authorize a job, or run/kill a worker.
Thresholds are conservative operational choices, not measured model requirements
or manufacturer safety limits. No torch/CUDA runtime is imported.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import os
import platform
import re
import subprocess
import time
import xml.etree.ElementTree as ET

SCHEMA = "helm-cas-expression-lab.q4-shared-display-capacity/0.1"
QUERY_FIELDS = ("index,uuid,driver_model.current,display_active,memory.total,"
                "memory.free,memory.used,utilization.gpu,temperature.gpu")
_UUID = re.compile(r"GPU-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_QUERY_TIMEOUT_SECONDS = 10
_MAX_QUERY_BYTES = 1024 * 1024


class CapacityError(ValueError):
    """Capacity metadata or the bound shared-display policy refused launch."""


def shared_display_policy(expected_uuid: str) -> dict:
    if type(expected_uuid) is not str or _UUID.fullmatch(expected_uuid) is None:
        raise CapacityError("CAPACITY_POLICY_INVALID: exact NVIDIA GPU UUID required")
    return {
        "schema": SCHEMA, "mode": "WINDOWS_WDDM_SHARED_DISPLAY_NOT_EXCLUSIVE",
        "expected_gpu_uuid": expected_uuid, "device": "cuda:0",
        "physical_gpu_count": 1, "driver_model": "WDDM",
        "display_active": "Enabled", "display_attached": "Yes",
        "prelaunch_samples": 3, "sample_interval_seconds": 1,
        "max_start_utilization_percent": 10, "min_start_free_mib": 4096,
        "max_start_temperature_c": 75, "stop_temperature_c": 80,
        "running_check_interval_seconds": 2,
        "allowed_prelaunch_context_types": ["G", "C+G"],
        "query_timeout_seconds": _QUERY_TIMEOUT_SECONDS,
    }


def validate_policy(policy: dict) -> dict:
    if type(policy) is not dict:
        raise CapacityError("CAPACITY_POLICY_INVALID: object required")
    expected = shared_display_policy(policy.get("expected_gpu_uuid"))
    if set(policy) != set(expected):
        raise CapacityError("CAPACITY_POLICY_INVALID: exact policy fields required")
    for key, value in expected.items():
        if type(policy[key]) is not type(value) or policy[key] != value:
            raise CapacityError("CAPACITY_POLICY_INVALID: fixed threshold or mode changed")
    return expected


def _check_host(policy, device):
    validate_policy(policy)
    if platform.system() != "Windows":
        raise CapacityError("CAPACITY_HOST_UNSUPPORTED: Windows WDDM policy only")
    if device != policy["device"]:
        raise CapacityError("CAPACITY_DEVICE_MISMATCH: exactly cuda:0 required")
    if os.environ.get("CUDA_VISIBLE_DEVICES"):
        raise CapacityError("GPU_MAPPING_UNSUPPORTED: no CUDA_VISIBLE_DEVICES remapping")


def _query(arguments):
    try:
        result = subprocess.run(
            ["nvidia-smi", *arguments], capture_output=True, text=True,
            timeout=_QUERY_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise CapacityError("GPU_CAPACITY_UNAVAILABLE: telemetry query failed") from error
    if (result.returncode != 0 or type(result.stdout) is not str
            or not result.stdout.strip() or len(result.stdout.encode("utf-8")) > _MAX_QUERY_BYTES):
        raise CapacityError("GPU_CAPACITY_UNAVAILABLE: empty, failed, or oversized telemetry")
    return result.stdout


def _integer(text, field, maximum):
    value = text.strip()
    if len(value) > 10 or not re.fullmatch(r"[0-9]+", value):
        raise CapacityError("GPU_CAPACITY_INVALID: non-integer " + field)
    result = int(value)
    if not 0 <= result <= maximum:
        raise CapacityError("GPU_CAPACITY_INVALID: out-of-range " + field)
    return result


def _parse_telemetry(raw, policy):
    try:
        rows = list(csv.reader(io.StringIO(raw), strict=True))
    except (csv.Error, TypeError) as error:
        raise CapacityError("GPU_CAPACITY_INVALID: malformed telemetry CSV") from error
    if len(rows) != 1 or len(rows[0]) != 9:
        raise CapacityError("GPU_CAPACITY_INVALID: exactly one GPU and nine fields required")
    values = [field.strip() for field in rows[0]]
    if values[0] != "0" or values[1] != policy["expected_gpu_uuid"]:
        raise CapacityError("GPU_IDENTITY_CHANGED: ordinal or UUID differs")
    if values[2] != "WDDM" or values[3] != "Enabled":
        raise CapacityError("GPU_DISPLAY_CHANGED: WDDM active display required")
    total = _integer(values[4], "memory.total", 2**31)
    free = _integer(values[5], "memory.free", 2**31)
    used = _integer(values[6], "memory.used", 2**31)
    util = _integer(values[7], "utilization.gpu", 100)
    temperature = _integer(values[8], "temperature.gpu", 150)
    if total == 0 or free > total or used > total or free + used > total:
        raise CapacityError("GPU_CAPACITY_INVALID: inconsistent memory totals")
    return {
        "gpu_index": 0, "gpu_uuid": values[1], "driver_model": values[2],
        "display_active": values[3], "memory_total_mib": total,
        "memory_free_mib": free, "memory_used_mib": used,
        "utilization_gpu_percent": util, "temperature_c": temperature,
        "observed_utc": datetime.now(timezone.utc).isoformat(), "raw_csv": raw,
    }


def _parse_inventory(raw, policy):
    if "<!ENTITY" in raw.upper():
        raise CapacityError("GPU_CAPACITY_INVALID: XML entities forbidden")
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, TypeError, ValueError) as error:
        raise CapacityError("GPU_CAPACITY_INVALID: malformed inventory XML") from error
    gpus = root.findall("gpu")
    if root.tag != "nvidia_smi_log" or len(gpus) != 1 or root.findtext("attached_gpus") != "1":
        raise CapacityError("GPU_CAPACITY_INVALID: exactly one physical GPU required")
    gpu = gpus[0]
    if (gpu.findtext("uuid") != policy["expected_gpu_uuid"]
            or gpu.findtext("driver_model/current_dm") != "WDDM"
            or gpu.findtext("display_attached") != "Yes"
            or gpu.findtext("display_active") != "Enabled"):
        raise CapacityError("GPU_IDENTITY_CHANGED: inventory identity/display differs")
    processes = gpu.find("processes")
    if processes is None:
        raise CapacityError("GPU_CAPACITY_INVALID: missing process inventory")
    children = list(processes)
    if not children and (processes.text or "").strip() != "None":
        raise CapacityError("GPU_CAPACITY_INVALID: unexplained empty process inventory")
    parsed, seen = [], set()
    for item in children:
        if item.tag != "process_info":
            raise CapacityError("GPU_CAPACITY_INVALID: unknown process metadata")
        pid = _integer(item.findtext("pid") or "", "pid", 2**32 - 1)
        kind = item.findtext("type")
        if pid == 0 or pid in seen:
            raise CapacityError("GPU_CAPACITY_INVALID: missing or duplicate PID")
        if kind not in policy["allowed_prelaunch_context_types"]:
            raise CapacityError("GPU_COMPETING_CONTEXT: pure compute or unknown context " + str(kind))
        seen.add(pid)
        parsed.append({"pid": pid, "type": kind,
                       "process_name": item.findtext("process_name") or None,
                       "used_memory": item.findtext("used_memory")})
    return {"contexts": parsed, "raw_xml": raw,
            "interpretation": "SHARED_DISPLAY_CONTEXTS_PRESENT_NOT_EXCLUSIVE_IDLE"}


def _telemetry(policy):
    return _parse_telemetry(_query([
        "--query-gpu=" + QUERY_FIELDS, "--format=csv,noheader,nounits"]), policy)


def check_prelaunch(policy: dict, device: str) -> dict:
    """Return retained shared-capacity observations, or refuse before launch."""
    _check_host(policy, device)
    samples = []
    for index in range(policy["prelaunch_samples"]):
        if index:
            time.sleep(policy["sample_interval_seconds"])
        sample = _telemetry(policy)
        inventory = _parse_inventory(_query(["-q", "-x"]), policy)
        if sample["utilization_gpu_percent"] > policy["max_start_utilization_percent"]:
            raise CapacityError("GPU_BUSY: prelaunch utilization exceeds policy")
        if sample["memory_free_mib"] < policy["min_start_free_mib"]:
            raise CapacityError("GPU_MEMORY_HEADROOM: prelaunch free memory below policy")
        if sample["temperature_c"] > policy["max_start_temperature_c"]:
            raise CapacityError("GPU_TOO_WARM: prelaunch temperature exceeds policy")
        samples.append({"telemetry": sample, "inventory": inventory})
    return {"schema": SCHEMA, "admission": "SHARED_DISPLAY_CAPACITY_ACCEPTED",
            "exclusive_idle": False, "policy": validate_policy(policy), "samples": samples,
            "limitation": "Snapshots do not reserve resources or exclude later external activity."}


def check_running(policy: dict, device: str) -> dict:
    """Observe device identity and temperature; caller stops only its own worker."""
    _check_host(policy, device)
    sample = _telemetry(policy)
    if sample["temperature_c"] >= policy["stop_temperature_c"]:
        raise CapacityError("GPU_THERMAL_STOP: temperature reached policy stop threshold")
    # Own worker may legitimately consume the startup headroom and utilization.
    return sample
