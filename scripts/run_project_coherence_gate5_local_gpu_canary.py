#!/usr/bin/env python3
"""Run the frozen, local-only Gate-5 Pythia mechanics canary.

The runner starts the already-built content-addressed worker image with no
container network, a read-only root filesystem, an ephemeral worker token, and
the local NVIDIA GPU.  Requests are sent from ``docker exec`` to the worker's
own loopback interface, so the model container has no provider or internet
path.  Every response is retained before a conservative mechanical receipt is
computed.

This is intentionally *not* the missing joined Gate-5 controller runner.  It
checks the existing real-model worker before that integration tranche and must
never be described as prompt-injection defense, steering efficacy, product
validation, Gate-5 closure, or a licensed capability.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence
import uuid


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate5"
    / "model_smoke"
    / "GATE5_LOCAL_GPU_CANARY_PROTOCOL_v0.2.json"
)
DEFAULT_RUNS_ROOT = DEFAULT_PROTOCOL.parent / "runs"
CLAIM_BOUNDARY = (
    "RESEARCH ONLY / LOCAL ENGINEERING CANARY / POST-FAILURE ADAPTED / "
    "NOT INDEPENDENT REPLICATION / NOT YET REPLICATED / "
    "NOT PRODUCT VALIDATION / NO PROMPT-INJECTION DEFENSE CLAIM / "
    "NO STEERING EFFICACY CLAIM / GATE 5 REMAINS OPEN / NOT LICENSED / "
    "DISCLOSURE HELD"
)
ERASER_CONTRACT = "harness_v2.mlp_intermediate_eraser.v2"
TARGET_INTERVENTION_STATUSES = {
    "OUTPUT_UNCHANGED",
    "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED",
}
EXPECTED_ARMS = [
    {"arm_id": "clean_baseline", "prompt_class": "clean", "intervention": "NONE"},
    {
        "arm_id": "clean_noop_hook",
        "prompt_class": "clean",
        "intervention": "DRIVE_LOCAL_ERASER",
        "drive": "F1",
        "gain": 0.0,
    },
    {
        "arm_id": "adversarial_baseline",
        "prompt_class": "adversarial",
        "intervention": "NONE",
    },
    {
        "arm_id": "adversarial_noop_hook",
        "prompt_class": "adversarial",
        "intervention": "DRIVE_LOCAL_ERASER",
        "drive": "F1",
        "gain": 0.0,
    },
    {
        "arm_id": "clean_target_intervention",
        "prompt_class": "clean",
        "intervention": "DRIVE_LOCAL_ERASER",
        "drive": "F1",
        "gain": 0.5,
    },
    {
        "arm_id": "adversarial_target_intervention",
        "prompt_class": "adversarial",
        "intervention": "DRIVE_LOCAL_ERASER",
        "drive": "F1",
        "gain": 0.5,
    },
]


class CanaryError(RuntimeError):
    """Raised when the frozen canary cannot complete mechanically."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_json_bytes(value))


def _run(
    command: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    timeout: float = 60.0,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        list(command),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        detail = stderr or stdout or f"exit {completed.returncode}"
        raise CanaryError(f"command failed: {command[0]}: {detail[:2000]}")
    return completed


def _run_best_effort(
    command: Sequence[str], *, timeout: float
) -> tuple[subprocess.CompletedProcess[bytes] | None, str | None]:
    """Run cleanup diagnostics without allowing a second exception to erase evidence."""

    try:
        return _run(command, timeout=timeout, check=False), None
    except Exception as exc:  # cleanup must retain and report every failure
        return None, f"{type(exc).__name__}: {exc}"


def _process_detail(completed: subprocess.CompletedProcess[bytes]) -> str:
    return (
        completed.stderr.decode("utf-8", errors="replace").strip()
        or completed.stdout.decode("utf-8", errors="replace").strip()
        or f"exit {completed.returncode}"
    )


def _docker_inspect_proves_absence(
    completed: subprocess.CompletedProcess[bytes],
) -> bool:
    if completed.returncode == 0:
        return False
    detail = _process_detail(completed).lower()
    return "no such object" in detail or "no such container" in detail


def _git_text(*args: str) -> str:
    return _run(
        ["git", "-C", str(REPO_ROOT), *args], timeout=30.0
    ).stdout.decode("utf-8", errors="strict").strip()


def _load_protocol(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryError(f"protocol is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CanaryError("protocol root must be an object")
    if value.get("schema_version") != "cas_harness_gate5_local_gpu_canary_protocol.v2":
        raise CanaryError("unexpected protocol schema")
    if value.get("status") != "FROZEN / EXECUTION NOT STARTED":
        raise CanaryError("protocol is not frozen in its prospective state")
    if value.get("claim_boundary") != CLAIM_BOUNDARY:
        raise CanaryError("protocol claim boundary drifted")
    arms = value.get("arms")
    maximum = value.get("execution_controls", {}).get("maximum_arms")
    if not isinstance(arms, list) or len(arms) != maximum or len(arms) != 6:
        raise CanaryError("protocol must contain exactly the frozen six arms")
    if arms != EXPECTED_ARMS:
        raise CanaryError("protocol arm matrix differs from the frozen six-arm design")
    predecessor = value.get("predecessor_failure_binding")
    if not isinstance(predecessor, dict):
        raise CanaryError("successor protocol lacks the predecessor failure binding")
    relative_receipt = Path(str(predecessor.get("runtime_receipt_path") or ""))
    if relative_receipt.is_absolute():
        raise CanaryError("predecessor receipt path must be repository-relative")
    receipt_path = (REPO_ROOT / relative_receipt).resolve()
    if not receipt_path.is_relative_to(REPO_ROOT) or not receipt_path.is_file():
        raise CanaryError("predecessor receipt is absent or escapes the repository")
    predecessor_raw = receipt_path.read_bytes()
    if (
        _sha256_bytes(predecessor_raw) != predecessor.get("runtime_receipt_sha256")
        or len(predecessor_raw) != predecessor.get("runtime_receipt_bytes")
    ):
        raise CanaryError("predecessor failure receipt bytes differ from the binding")
    try:
        predecessor_receipt = json.loads(predecessor_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryError(f"predecessor failure receipt is invalid: {exc}") from exc
    if not isinstance(predecessor_receipt, dict) or not (
        predecessor_receipt.get("run_id") == predecessor.get("run_id")
        and predecessor_receipt.get("status") == predecessor.get("terminal_status")
        and predecessor_receipt.get("mechanical_assessment", {}).get("status")
        == "FAIL_CLOSED"
        and predecessor_receipt.get("protocol", {}).get("sha256")
        == predecessor.get("protocol_sha256")
    ):
        raise CanaryError("predecessor receipt is not the exact retained v0.1 failure")
    adaptation = value.get("adaptation_evidence_binding")
    if not isinstance(adaptation, dict):
        raise CanaryError("successor protocol lacks adaptation evidence")
    relative_ledger = Path(str(adaptation.get("diagnostic_ledger_path") or ""))
    if relative_ledger.is_absolute():
        raise CanaryError("adaptation ledger path must be repository-relative")
    ledger_path = (REPO_ROOT / relative_ledger).resolve()
    if not ledger_path.is_relative_to(REPO_ROOT) or not ledger_path.is_file():
        raise CanaryError("adaptation ledger is absent or escapes the repository")
    ledger_raw = ledger_path.read_bytes()
    if (
        _sha256_bytes(ledger_raw) != adaptation.get("diagnostic_ledger_sha256")
        or len(ledger_raw) != adaptation.get("diagnostic_ledger_bytes")
    ):
        raise CanaryError("adaptation ledger bytes differ from the binding")
    try:
        ledger = json.loads(ledger_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryError(f"adaptation ledger is invalid: {exc}") from exc
    source = value.get("source_binding")
    if not isinstance(ledger, dict) or not isinstance(source, dict):
        raise CanaryError("adaptation ledger or successor source binding is invalid")
    ledger_checks = ledger.get("checks")
    if not (
        ledger.get("status") == "PASS"
        and ledger.get("adaptation_status") == adaptation.get("adaptation_status")
        and ledger.get("collector_git_head") == adaptation.get("collector_commit")
        and ledger.get("parent_image_id_and_digest")
        == source.get("parent_worker_image_id")
        and ledger.get("successor_image_id_and_digest")
        == source.get("worker_image_digest")
        and isinstance(ledger_checks, dict)
        and ledger_checks
        and all(item is True for item in ledger_checks.values())
    ):
        raise CanaryError("adaptation ledger does not bind the successful diagnostics")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) != 5:
        raise CanaryError("adaptation ledger does not contain the exact five diagnostics")
    raw_by_name: dict[str, dict[str, bytes]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise CanaryError("adaptation diagnostic entry is invalid")
        streams: dict[str, bytes] = {}
        for stream_name in ("stdout", "stderr"):
            stream = entry.get(stream_name)
            if not isinstance(stream, dict):
                raise CanaryError("adaptation diagnostic stream binding is invalid")
            relative_stream = Path(str(stream.get("path") or ""))
            if relative_stream.is_absolute():
                raise CanaryError("adaptation diagnostic stream path must be relative")
            stream_path = (REPO_ROOT / relative_stream).resolve()
            if not stream_path.is_relative_to(REPO_ROOT) or not stream_path.is_file():
                raise CanaryError("adaptation diagnostic stream is absent or escapes")
            stream_raw = stream_path.read_bytes()
            if (
                _sha256_bytes(stream_raw) != stream.get("sha256")
                or len(stream_raw) != stream.get("bytes")
            ):
                raise CanaryError("adaptation diagnostic stream bytes differ")
            streams[stream_name] = stream_raw
        raw_by_name[entry["name"]] = streams
    if set(raw_by_name) != {
        "parent_cache_redirect",
        "parent_nojit_float16",
        "parent_custom_bfloat16",
        "successor_policy_warm_load",
        "image_inspect",
    }:
        raise CanaryError("adaptation diagnostic names differ from the frozen set")
    try:
        bfloat16_observation = json.loads(
            raw_by_name["parent_custom_bfloat16"]["stdout"]
        )
        successor_observation = json.loads(
            raw_by_name["successor_policy_warm_load"]["stdout"]
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryError(f"adaptation diagnostic JSON is invalid: {exc}") from exc
    if not (
        bfloat16_observation.get("dtype") == "torch.bfloat16"
        and bfloat16_observation.get("native_bfloat16") is True
        and bfloat16_observation.get("logits_finite") is True
        and bfloat16_observation.get("attention_finite") is True
        and bfloat16_observation.get("nonfinite_logits") == 0
        and bfloat16_observation.get("attention_tensors") == 12
        and successor_observation.get("policy_effective") is True
        and successor_observation.get("policy_source_sha256")
        == adaptation.get("torch_native_policy_source_sha256")
        and successor_observation.get("triton_policy_source_sha256")
        == adaptation.get("torch_triton_policy_source_sha256")
        and successor_observation.get("compiler_paths")
        == {"cc": None, "gcc": None, "clang": None}
        and successor_observation.get("root_worker_writable") is False
        and successor_observation.get("parameter_dtypes") == ["torch.bfloat16"]
        and successor_observation.get("parameter_devices") == ["cuda"]
    ):
        raise CanaryError("adaptation diagnostic observations differ from v0.2")
    return raw, value


def _inspect_image(
    image: str,
    *,
    expected_digest: str,
    expected_source_commit: str,
    expected_user: str,
    expected_parent_image_id: str,
    expected_parent_repo_digest: str,
    expected_parent_worker_source: str,
    expected_runtime_dtype: str,
    expected_parent_rootfs_layer_count: int,
    expected_parent_rootfs_layers_sha256: str,
    expected_successor_rootfs_layer_count: int,
    expected_successor_rootfs_layers_sha256: str,
    expected_overlay_rootfs_layer_count: int,
) -> dict[str, Any]:
    raw = _run(["docker", "image", "inspect", image], timeout=30.0).stdout
    payload = json.loads(raw)
    if not isinstance(payload, list) or len(payload) != 1:
        raise CanaryError("docker returned an ambiguous image inspection")
    inspected = payload[0]
    parent_raw = _run(
        ["docker", "image", "inspect", expected_parent_image_id], timeout=30.0
    ).stdout
    parent_payload = json.loads(parent_raw)
    if not isinstance(parent_payload, list) or len(parent_payload) != 1:
        raise CanaryError("docker returned an ambiguous parent-image inspection")
    parent = parent_payload[0]
    if parent.get("Id") != expected_parent_image_id:
        raise CanaryError("parent local image ID differs from protocol")
    parent_labels = (parent.get("Config") or {}).get("Labels") or {}
    if (
        parent_labels.get("org.opencontainers.image.revision")
        != expected_parent_worker_source
    ):
        raise CanaryError("parent image source-commit label differs from protocol")
    parent_repo_digests = parent.get("RepoDigests") or []
    parent_observed_digests = {
        str(item).rsplit("@", 1)[-1] for item in parent_repo_digests
    }
    if expected_parent_repo_digest not in parent_observed_digests:
        raise CanaryError("parent repo digest differs from protocol")
    parent_layers = (parent.get("RootFS") or {}).get("Layers")
    successor_layers = (inspected.get("RootFS") or {}).get("Layers")
    if not isinstance(parent_layers, list) or not all(
        isinstance(item, str) for item in parent_layers
    ):
        raise CanaryError("parent rootfs layer chain is invalid")
    if not isinstance(successor_layers, list) or not all(
        isinstance(item, str) for item in successor_layers
    ):
        raise CanaryError("successor rootfs layer chain is invalid")
    parent_layers_sha256 = _sha256_bytes(_canonical_json_bytes(parent_layers))
    successor_layers_sha256 = _sha256_bytes(_canonical_json_bytes(successor_layers))
    if (
        len(parent_layers) != expected_parent_rootfs_layer_count
        or parent_layers_sha256 != expected_parent_rootfs_layers_sha256
    ):
        raise CanaryError("parent rootfs chain differs from protocol")
    if (
        len(successor_layers) != expected_successor_rootfs_layer_count
        or successor_layers_sha256 != expected_successor_rootfs_layers_sha256
    ):
        raise CanaryError("successor rootfs chain differs from protocol")
    if (
        successor_layers[: len(parent_layers)] != parent_layers
        or len(successor_layers) - len(parent_layers)
        != expected_overlay_rootfs_layer_count
    ):
        raise CanaryError("successor rootfs does not have the exact parent prefix")
    repo_digests = inspected.get("RepoDigests") or []
    observed = {str(item).rsplit("@", 1)[-1] for item in repo_digests}
    if expected_digest not in observed:
        raise CanaryError(
            f"local image digest mismatch: expected {expected_digest}, observed {sorted(observed)}"
        )
    config = inspected.get("Config") or {}
    labels = config.get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != expected_source_commit:
        raise CanaryError("worker image source-commit label differs from protocol")
    if labels.get("io.cas-harness.overlay.source") != expected_source_commit:
        raise CanaryError("worker overlay-source label differs from protocol")
    if labels.get("io.cas-harness.parent.local-image-id") != expected_parent_image_id:
        raise CanaryError("worker parent local-image label differs from protocol")
    if labels.get("io.cas-harness.parent.repo-digest") != expected_parent_repo_digest:
        raise CanaryError("worker parent repo-digest label differs from protocol")
    if labels.get("io.cas-harness.parent.worker-source") != expected_parent_worker_source:
        raise CanaryError("worker parent-source label differs from protocol")
    if labels.get("io.cas-harness.runtime.dtype") != expected_runtime_dtype:
        raise CanaryError("worker runtime-dtype label differs from protocol")
    if labels.get("io.cas-harness.runtime.native-jit") != "disabled":
        raise CanaryError("worker image does not bind disabled native JIT")
    if labels.get("io.cas-harness.claim-status") != "RESEARCH_ONLY_LOCAL_CANARY":
        raise CanaryError("worker image claim-status label differs")
    if config.get("User") != expected_user:
        raise CanaryError("worker image configured user differs from protocol")
    environment = config.get("Env") or []
    if "ATLAS_WORKER_PROFILE=production" not in environment:
        raise CanaryError("worker image does not bind the production profile")
    if "TORCH_DISABLE_NATIVE_JIT=1" not in environment:
        raise CanaryError("worker image does not bind TORCH_DISABLE_NATIVE_JIT=1")
    command = config.get("Cmd") or []
    if not any("uvicorn app.main:app" in str(item) for item in command):
        raise CanaryError("worker image command is not the frozen worker server")
    return {
        "image_id": inspected.get("Id"),
        "configured_user": config.get("User"),
        "configured_command": command,
        "production_profile_bound": True,
        "native_jit_disabled_bound": True,
        "repo_digests": repo_digests,
        "os": inspected.get("Os"),
        "architecture": inspected.get("Architecture"),
        "size_bytes": inspected.get("Size"),
        "labels": labels,
        "parent_image": {
            "image_id": parent.get("Id"),
            "repo_digests": parent_repo_digests,
            "source_commit": parent_labels.get("org.opencontainers.image.revision"),
            "rootfs_layer_count": len(parent_layers),
            "rootfs_layers_sha256": parent_layers_sha256,
        },
        "successor_rootfs_layer_count": len(successor_layers),
        "successor_rootfs_layers_sha256": successor_layers_sha256,
        "overlay_rootfs_layer_count": len(successor_layers) - len(parent_layers),
        "parent_rootfs_prefix_exact": True,
    }


def _inspect_started_container(
    container: str,
    *,
    expected_image_id: str,
    expected_user: str,
) -> dict[str, Any]:
    raw = _run(["docker", "inspect", container], timeout=30.0).stdout
    payload = json.loads(raw)
    if not isinstance(payload, list) or len(payload) != 1:
        raise CanaryError("docker returned an ambiguous container inspection")
    inspected = payload[0]
    config = inspected.get("Config") or {}
    host = inspected.get("HostConfig") or {}
    if inspected.get("Image") != expected_image_id:
        raise CanaryError("started container is not bound to the inspected image ID")
    if config.get("User") != expected_user:
        raise CanaryError("started container user differs from the frozen image user")
    environment = config.get("Env") or []
    if "TORCH_DISABLE_NATIVE_JIT=1" not in environment:
        raise CanaryError("started container does not retain disabled native JIT")
    tmpfs = host.get("Tmpfs") or {}
    tmp_options = {
        item.strip() for item in str(tmpfs.get("/tmp") or "").split(",") if item.strip()
    }
    required_tmp_options = {"rw", "noexec", "nosuid", "nodev"}
    if host.get("NetworkMode") != "none":
        raise CanaryError("started container does not have network mode none")
    if host.get("ReadonlyRootfs") is not True:
        raise CanaryError("started container root filesystem is not read-only")
    if not required_tmp_options.issubset(tmp_options) or not (
        {"size=64m", "size=67108864"} & tmp_options
    ):
        raise CanaryError("started container /tmp tmpfs differs from frozen controls")
    if host.get("Memory") != 6 * 1024**3 or host.get("MemorySwap") != 6 * 1024**3:
        raise CanaryError("started container memory/no-swap boundary differs")
    if host.get("PidsLimit") != 512:
        raise CanaryError("started container PID limit differs")
    if {str(item).upper() for item in (host.get("CapDrop") or [])} != {"ALL"}:
        raise CanaryError("started container capability drop differs")
    security_options = {str(item) for item in (host.get("SecurityOpt") or [])}
    if not security_options.intersection(
        {"no-new-privileges", "no-new-privileges=true", "no-new-privileges:true"}
    ):
        raise CanaryError("started container lacks no-new-privileges")
    if host.get("AutoRemove") is not False:
        raise CanaryError("started container could auto-remove before logs are retained")
    if host.get("PublishAllPorts") is True or host.get("PortBindings"):
        raise CanaryError("started container unexpectedly publishes a host port")
    return {
        "container_id": inspected.get("Id"),
        "image_id": inspected.get("Image"),
        "configured_image_reference": config.get("Image"),
        "configured_user": config.get("User"),
        "native_jit_disabled_bound": True,
        "network_mode": host.get("NetworkMode"),
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "tmpfs": tmpfs,
        "memory_bytes": host.get("Memory"),
        "memory_swap_bytes": host.get("MemorySwap"),
        "pids_limit": host.get("PidsLimit"),
        "cap_drop": host.get("CapDrop"),
        "security_opt": host.get("SecurityOpt"),
        "auto_remove": host.get("AutoRemove"),
        "publish_all_ports": host.get("PublishAllPorts"),
        "port_bindings": host.get("PortBindings"),
    }


def _build_request(protocol: Mapping[str, Any], arm: Mapping[str, Any]) -> dict[str, Any]:
    request = deepcopy(protocol["common_request"])
    prompt_class = str(arm["prompt_class"])
    request["prompt"] = protocol["prompt_classes"][prompt_class]["text"]
    if arm["intervention"] == "DRIVE_LOCAL_ERASER":
        method_config = request["method_config"]
        enabled = method_config["enabled_methods"]
        if "drive_local_eraser" in enabled:
            raise CanaryError("common request unexpectedly enables the intervention")
        enabled.append("drive_local_eraser")
        method_config["knobs"]["drive_local_eraser"] = {
            "drive": arm["drive"],
            "gain": arm["gain"],
        }
    elif arm["intervention"] != "NONE":
        raise CanaryError(f"unsupported frozen intervention {arm['intervention']!r}")
    return request


_HEALTH_CLIENT = r"""
import os, sys, urllib.request
request = urllib.request.Request(
    "http://127.0.0.1:8080/health/realmode",
    headers={"X-Atlas-Worker-Token": os.environ["ATLAS_LIVE_WORKER_TOKEN"]},
)
with urllib.request.urlopen(request, timeout=10) as response:
    sys.stdout.buffer.write(response.read())
""".strip()


_DUMP_CLIENT = r"""
import os, sys, urllib.request
body = sys.stdin.buffer.read()
request = urllib.request.Request(
    "http://127.0.0.1:8080/sessions/dump",
    data=body,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "X-Atlas-Worker-Token": os.environ["ATLAS_LIVE_WORKER_TOKEN"],
    },
)
with urllib.request.urlopen(request, timeout=300) as response:
    sys.stdout.buffer.write(response.read())
""".strip()


_BACKEND_POLICY_CLIENT = r"""
import hashlib, json, os, shutil
from pathlib import Path
from torch._native.common_utils import check_native_jit_disabled
import torch._native.common_utils as native_common
import torch._native.triton_utils as native_triton

common_path = Path(native_common.__file__)
triton_path = Path(native_triton.__file__)
payload = {
    "environment_value": os.environ.get("TORCH_DISABLE_NATIVE_JIT"),
    "policy_effective": bool(check_native_jit_disabled()),
    "policy_source_path": str(common_path),
    "policy_source_sha256": hashlib.sha256(common_path.read_bytes()).hexdigest(),
    "triton_policy_source_path": str(triton_path),
    "triton_policy_source_sha256": hashlib.sha256(triton_path.read_bytes()).hexdigest(),
    "compiler_paths": {name: shutil.which(name) for name in ("cc", "gcc", "clang")},
    "root_worker_writable": os.access("/worker", os.W_OK),
    "tmp_regular_files": sorted(
        str(path.relative_to("/tmp")) for path in Path("/tmp").rglob("*") if path.is_file()
    ),
}
print(json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":")))
""".strip()


def _wait_for_health(container: str, timeout_seconds: float) -> tuple[bytes, dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    last_detail = "worker has not responded"
    while time.monotonic() < deadline:
        completed = _run(
            ["docker", "exec", container, "python", "-c", _HEALTH_CLIENT],
            timeout=20.0,
            check=False,
        )
        if completed.returncode == 0:
            try:
                value = json.loads(completed.stdout)
            except json.JSONDecodeError as exc:
                raise CanaryError(f"real-mode health was not JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise CanaryError("real-mode health root was not an object")
            return completed.stdout, value
        last_detail = completed.stderr.decode("utf-8", errors="replace").strip()
        state = _run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container],
            timeout=10.0,
            check=False,
        )
        if state.returncode != 0 or state.stdout.strip() in {b"exited", b"dead"}:
            raise CanaryError(f"worker container exited during startup: {last_detail[:1000]}")
        time.sleep(2.0)
    raise CanaryError(f"worker readiness timed out: {last_detail[:1000]}")


def _container_backend_policy(container: str) -> tuple[bytes, dict[str, Any]]:
    completed = _run(
        ["docker", "exec", container, "python", "-c", _BACKEND_POLICY_CLIENT],
        timeout=60.0,
    )
    try:
        value = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryError(f"backend-policy attestation was not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CanaryError("backend-policy attestation root was not an object")
    return completed.stdout, value


def _backend_policy_is_exact(
    value: Any,
    adaptation: Mapping[str, Any],
) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("environment_value") == "1"
        and value.get("policy_effective") is True
        and value.get("policy_source_path")
        == "/usr/local/lib/python3.12/site-packages/torch/_native/common_utils.py"
        and value.get("policy_source_sha256")
        == adaptation.get("torch_native_policy_source_sha256")
        and value.get("triton_policy_source_path")
        == "/usr/local/lib/python3.12/site-packages/torch/_native/triton_utils.py"
        and value.get("triton_policy_source_sha256")
        == adaptation.get("torch_triton_policy_source_sha256")
        and value.get("compiler_paths") == {"cc": None, "gcc": None, "clang": None}
        and value.get("root_worker_writable") is False
        and value.get("tmp_regular_files") == []
    )


def _invoke_arm(container: str, request: Mapping[str, Any]) -> bytes:
    body = _canonical_json_bytes(request)
    completed = _run(
        ["docker", "exec", "-i", container, "python", "-c", _DUMP_CLIENT],
        input_bytes=body,
        timeout=360.0,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CanaryError(f"worker dump request failed: {detail[:3000]}")
    return completed.stdout


def _all_finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_all_finite(item) for item in value)
    if isinstance(value, dict):
        return all(_all_finite(item) for item in value.values())
    return False


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _runtime_execution_is_exact(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("profile") == "production"
        and value.get("device") == "cuda"
        and value.get("dtype") == "torch.bfloat16"
        and value.get("torch_version") == "2.13.0+cu126"
        and value.get("torch_native_jit_disabled") is True
        and value.get("cuda_bfloat16_supported") is True
        and value.get("cuda_runtime_version") == "12.6"
        and isinstance(value.get("cuda_driver_version"), int)
        and value["cuda_driver_version"] >= 12060
        and isinstance(value.get("cuda_device_name"), str)
        and bool(value["cuda_device_name"])
        and isinstance(value.get("cuda_device_capability"), str)
        and bool(value["cuda_device_capability"])
    )


def _model_identity_is_exact(value: Any, source: Mapping[str, Any]) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("model_id") == source["model_id"]
        and value.get("requested_revision") == source["model_revision"]
        and value.get("resolved_revision") == source["model_revision"]
        and value.get("revision_verified") is True
        and value.get("weights_filename") == source["weights_filename"]
        and str(value.get("weights_sha256") or "").lower()
        == source["weights_sha256"]
        and value.get("weights_bytes") == source["weights_bytes"]
        and value.get("weights_hash_verified") is True
        and value.get("model_identity_status")
        == "PINNED_REVISION_AND_WEIGHTS_SHA256"
        and value.get("is_real_model") is True
        and value.get("execution_kind") == "real_model_weights"
        and _runtime_execution_is_exact(value.get("runtime_execution"))
    )


def _health_is_exact(value: Any, source: Mapping[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    identity_view = {
        **value,
        "execution_kind": "real_model_weights" if value.get("is_real_model") else None,
        "is_real_model": value.get("is_real_model"),
    }
    return bool(
        value.get("verdict") == "REAL_PYTHIA_WEIGHTS_LOADED"
        and value.get("is_real_model") is True
        and value.get("fake_runtime_env") is False
        and value.get("model_loaded") is True
        and value.get("load_error") is None
        and value.get("manifest_is_real_model") is True
        and _model_identity_is_exact(identity_view, source)
    )


def _gpu_matches_runtime(health: Mapping[str, Any], gpu: Mapping[str, str]) -> bool:
    runtime = health.get("runtime_execution")
    return bool(
        isinstance(runtime, dict)
        and runtime.get("cuda_device_name") == gpu.get("name")
        and runtime.get("cuda_device_capability") == gpu.get("compute_capability")
    )


def _event_sequence_is_exact(
    events: Sequence[Mapping[str, Any]],
    tokens: Sequence[Mapping[str, Any]],
    completes: Sequence[Mapping[str, Any]],
    *,
    expected_tokens: int,
) -> bool:
    """Verify one ordered terminal event and contiguous emitted-token indices."""
    if not events or events[0].get("type") != "manifest":
        return False
    if events[-1].get("type") != "complete":
        return False
    if sum(item.get("type") == "manifest" for item in events) != 1:
        return False
    if len(completes) != 1:
        return False
    if any(item.get("type") == "error" for item in events):
        return False
    if not (1 <= len(tokens) <= expected_tokens):
        return False
    if [item.get("token_index") for item in tokens] != list(range(len(tokens))):
        return False
    return completes[0].get("total_tokens") == len(tokens)


def _base_intervention_receipt_is_exact(
    value: Any,
    *,
    gain: float,
) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("contract_version") == ERASER_CONTRACT
        and value.get("method_id") == "drive_local_eraser"
        and value.get("execution_kind") == "real_model_weights"
        and value.get("source_kind") == "stage27f_calibrated_cover"
        and value.get("coordinate_space") == "mlp_intermediate_post_activation"
        and value.get("requested_gain") == gain
        and value.get("effective_gain") == gain
        and value.get("structurally_valid") is False
        and isinstance(value.get("structural_status"), str)
    )


def _zero_gain_receipt_is_exact(value: Any) -> bool:
    return bool(
        _base_intervention_receipt_is_exact(value, gain=0.0)
        and value.get("structural_status") == "ACTIVATION_UNCHANGED"
        and value.get("hook_fired") is True
        and value.get("activation_changed") is False
        and value.get("output_changed") is False
        and value.get("stability_control_performed") is True
        and value.get("baseline_output_stable") is True
        and value.get("baseline_geometry_stable") is True
    )


def _target_intervention_receipt_is_exact(value: Any, *, gain: float) -> bool:
    return bool(
        _base_intervention_receipt_is_exact(value, gain=gain)
        and value.get("structural_status") in TARGET_INTERVENTION_STATUSES
        and value.get("hook_fired") is True
        and value.get("activation_changed") is True
        and isinstance(value.get("applied_coordinates"), list)
        and bool(value["applied_coordinates"])
        and value.get("stability_control_performed") is True
        and value.get("baseline_output_stable") is True
        and value.get("baseline_geometry_stable") is True
        and (
            (
                value.get("structural_status") == "OUTPUT_UNCHANGED"
                and value.get("output_changed") is False
            )
            or (
                value.get("structural_status")
                == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
                and value.get("output_changed") is True
            )
        )
    )


def _real_ablation_is_exact(value: Any, expected_target: Mapping[str, Any]) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("target")
        == {"layer": expected_target["layer"], "unit": expected_target["unit"]}
        and value.get("mode") == expected_target["mode"]
        and value.get("is_real_model") is True
        and _finite_number(value.get("logit_delta"))
        and _finite_number(value.get("confidence_delta"))
        and isinstance(value.get("baseline_top_token_id"), int)
        and isinstance(value.get("ablated_top_token_id"), int)
        and isinstance(value.get("top_token_changed"), bool)
    )


def _real_ablation_control_is_exact(
    value: Any, expected_target: Mapping[str, Any]
) -> bool:
    units = value.get("control_units") if isinstance(value, dict) else None
    return bool(
        isinstance(value, dict)
        and value.get("target")
        == {"layer": expected_target["layer"], "unit": expected_target["unit"]}
        and value.get("mode") == expected_target["mode"]
        and value.get("is_real_model") is True
        and value.get("n_controls") == 8
        and isinstance(units, list)
        and len(units) == 8
        and all(isinstance(item, int) for item in units)
        and len(set(units)) == 8
        and expected_target["unit"] not in units
        and all(
            _finite_number(value.get(field))
            for field in (
                "target_abs_logit_delta",
                "control_mean_abs_logit_delta",
                "control_max_abs_logit_delta",
                "margin_over_control_max",
            )
        )
        and isinstance(value.get("selectivity_passed"), bool)
        and isinstance(value.get("seed"), int)
    )


def _summarize_arm(
    arm: Mapping[str, Any],
    response_raw: bytes,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        response = json.loads(response_raw)
    except json.JSONDecodeError as exc:
        raise CanaryError(f"arm {arm['arm_id']} returned invalid JSON: {exc}") from exc
    events = response.get("events") if isinstance(response, dict) else None
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise CanaryError(f"arm {arm['arm_id']} did not return an event list")
    types = Counter(str(item.get("type")) for item in events)
    manifests = [item.get("manifest") for item in events if item.get("type") == "manifest"]
    tokens = [item for item in events if item.get("type") == "token"]
    errors = [item for item in events if item.get("type") == "error"]
    completes = [item for item in events if item.get("type") == "complete"]
    ablations = [item for item in events if item.get("type") == "ablation_effect"]
    controls = [
        item for item in events if item.get("type") == "ablation_control_effect"
    ]
    if len(manifests) != 1 or not isinstance(manifests[0], dict):
        raise CanaryError(f"arm {arm['arm_id']} did not return one manifest")
    manifest = manifests[0]
    source = protocol["source_binding"]
    exact_manifest = _model_identity_is_exact(manifest, source)
    inversion_risks = [
        float(item["inversion_risk"])
        for item in tokens
        if item.get("inversion_risk") is not None
    ]
    confidences = [
        float(item["confidence"])
        for item in tokens
        if item.get("confidence") is not None
    ]
    intervention_receipts = [
        item.get("eraser_intervention_result")
        for item in tokens
        if item.get("eraser_intervention_result") is not None
    ]
    expects_intervention = arm["intervention"] == "DRIVE_LOCAL_ERASER"
    intervention_explicit = (
        bool(intervention_receipts) if expects_intervention else not intervention_receipts
    )
    zero_receipts_typed_no_effect = True
    target_receipts_typed_measured = True
    if expects_intervention and float(arm["gain"]) == 0.0:
        zero_receipts_typed_no_effect = bool(intervention_receipts) and all(
            _zero_gain_receipt_is_exact(item)
            for item in intervention_receipts
        )
    if expects_intervention and float(arm["gain"]) > 0.0:
        target_receipts_typed_measured = bool(intervention_receipts) and all(
            _target_intervention_receipt_is_exact(item, gain=float(arm["gain"]))
            for item in intervention_receipts
        )
    expected_target = protocol["common_request"]["ablation_target"]
    real_ablation = len(ablations) == 1 and _real_ablation_is_exact(
        ablations[0], expected_target
    )
    real_control = len(controls) == 1 and _real_ablation_control_is_exact(
        controls[0], expected_target
    )
    expected_tokens = int(protocol["execution_controls"]["max_new_tokens"])
    complete_ok = _event_sequence_is_exact(
        events,
        tokens,
        completes,
        expected_tokens=expected_tokens,
    )
    return {
        "arm_id": arm["arm_id"],
        "prompt_class": arm["prompt_class"],
        "intervention": arm["intervention"],
        "gain": arm.get("gain"),
        "response_sha256": _sha256_bytes(response_raw),
        "response_bytes": len(response_raw),
        "event_type_counts": dict(sorted(types.items())),
        "generated_text": "".join(str(item.get("token") or "") for item in tokens),
        "emitted_tokens": len(tokens),
        "mean_inversion_risk": _mean(inversion_risks),
        "max_inversion_risk": max(inversion_risks) if inversion_risks else None,
        "mean_confidence": _mean(confidences),
        "verification_verdicts": [item.get("verification_verdict") for item in tokens],
        "intervention_receipts": intervention_receipts,
        "ablation_effect": ablations[0] if len(ablations) == 1 else None,
        "ablation_control_effect": controls[0] if len(controls) == 1 else None,
        "checks": {
            "exact_real_model_manifest": exact_manifest,
            "finite_json_values": _all_finite(response),
            "complete_without_error": complete_ok,
            "intervention_receipt_presence_correct": intervention_explicit,
            "zero_gain_receipts_typed_no_effect": zero_receipts_typed_no_effect,
            "target_receipts_typed_measured": target_receipts_typed_measured,
            "real_causal_ablation_retained": real_ablation,
            "real_matched_control_retained": real_control,
        },
    }


def _mechanical_receipt(
    arm_summaries: Sequence[Mapping[str, Any]],
    *,
    exact_health: bool = False,
    gpu_runtime_match: bool = False,
    backend_policy_exact: bool = False,
) -> dict[str, Any]:
    by_id = {str(item["arm_id"]): item for item in arm_summaries}
    expected_ids = {
        "clean_baseline",
        "clean_noop_hook",
        "clean_target_intervention",
        "adversarial_baseline",
        "adversarial_noop_hook",
        "adversarial_target_intervention",
    }
    exact_arm_set = set(by_id) == expected_ids and len(by_id) == len(arm_summaries)
    all_arm_checks = all(
        all(bool(result) for result in item["checks"].values())
        for item in arm_summaries
    )
    clean_noop_equal = bool(
        exact_arm_set
        and by_id["clean_baseline"]["generated_text"]
        == by_id["clean_noop_hook"]["generated_text"]
    )
    adversarial_noop_equal = bool(
        exact_arm_set
        and by_id["adversarial_baseline"]["generated_text"]
        == by_id["adversarial_noop_hook"]["generated_text"]
    )
    checks = {
        "exact_production_cuda_health": exact_health,
        "container_gpu_matches_worker_runtime": gpu_runtime_match,
        "effective_no_jit_no_compiler_backend_policy": backend_policy_exact,
        "exact_frozen_arm_set": exact_arm_set,
        "all_per_arm_mechanical_checks": all_arm_checks,
        "clean_baseline_equals_zero_gain_hook": clean_noop_equal,
        "adversarial_baseline_equals_zero_gain_hook": adversarial_noop_equal,
    }
    clean_risk = by_id.get("clean_baseline", {}).get("mean_inversion_risk")
    adversarial_risk = by_id.get("adversarial_baseline", {}).get(
        "mean_inversion_risk"
    )
    risk_delta = (
        float(adversarial_risk) - float(clean_risk)
        if clean_risk is not None and adversarial_risk is not None
        else None
    )
    return {
        "status": "PASS" if all(checks.values()) else "FAIL_CLOSED",
        "checks": checks,
        "report_only": {
            "adversarial_minus_clean_baseline_mean_inversion_risk": risk_delta,
            "interpretation": (
                "Signal discrimination is descriptive only. The inversion-risk "
                "heuristic is not a validated prompt-injection detector."
            ),
        },
    }


def _container_gpu_identity(container: str) -> dict[str, str]:
    query = (
        "name,driver_version,memory.total,memory.free,"
        "compute_cap"
    )
    completed = _run(
        [
            "docker",
            "exec",
            container,
            "nvidia-smi",
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits",
        ],
        timeout=30.0,
    )
    parts = [item.strip() for item in completed.stdout.decode().strip().split(",")]
    if len(parts) != 5:
        raise CanaryError("unexpected nvidia-smi identity response")
    return {
        "name": parts[0],
        "driver_version": parts[1],
        "memory_total_mib": parts[2],
        "memory_free_mib_before_requests": parts[3],
        "compute_capability": parts[4],
    }


def run_canary(protocol_path: Path, runs_root: Path) -> Path:
    if protocol_path.resolve() != DEFAULT_PROTOCOL.resolve():
        raise CanaryError("only the repository-frozen canary protocol may execute")
    protocol_raw, protocol = _load_protocol(protocol_path)
    dirty = _git_text("status", "--porcelain")
    if dirty:
        raise CanaryError(
            "worktree must be clean before execution; commit the frozen protocol/driver first"
        )
    git_head = _git_text("rev-parse", "HEAD")
    branch = _git_text("branch", "--show-current")
    source = protocol["source_binding"]
    for field, description in (
        ("controller_successor_commit", "Gate-5 successor"),
        ("worker_overlay_source_commit", "BF16 worker overlay"),
    ):
        ancestor = _run(
            [
                "git",
                "-C",
                str(REPO_ROOT),
                "merge-base",
                "--is-ancestor",
                str(source[field]),
                git_head,
            ],
            timeout=30.0,
            check=False,
        )
        if ancestor.returncode != 0:
            raise CanaryError(f"canary commit does not descend from the {description}")
    retention = str(protocol["predecessor_failure_binding"]["retention_commit"])
    retained_ancestor = _run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "merge-base",
            "--is-ancestor",
            retention,
            git_head,
        ],
        timeout=30.0,
        check=False,
    )
    if retained_ancestor.returncode != 0:
        raise CanaryError("canary commit does not retain the v0.1 terminal failure")
    collector = str(protocol["adaptation_evidence_binding"]["collector_commit"])
    collector_ancestor = _run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "merge-base",
            "--is-ancestor",
            collector,
            git_head,
        ],
        timeout=30.0,
        check=False,
    )
    if collector_ancestor.returncode != 0:
        raise CanaryError("canary commit does not retain the adaptation collector")
    image = str(source["worker_image"])
    expected_user = str(protocol["execution_controls"]["container_user"])
    image_identity = _inspect_image(
        image,
        expected_digest=str(source["worker_image_digest"]),
        expected_source_commit=str(source["worker_overlay_source_commit"]),
        expected_user=expected_user,
        expected_parent_image_id=str(source["parent_worker_image_id"]),
        expected_parent_repo_digest=str(source["parent_worker_repo_digest"]),
        expected_parent_worker_source=str(source["parent_worker_source_commit"]),
        expected_runtime_dtype=str(source["expected_runtime_dtype"]),
        expected_parent_rootfs_layer_count=int(source["parent_rootfs_layer_count"]),
        expected_parent_rootfs_layers_sha256=str(
            source["parent_rootfs_layers_sha256"]
        ),
        expected_successor_rootfs_layer_count=int(
            source["successor_rootfs_layer_count"]
        ),
        expected_successor_rootfs_layers_sha256=str(
            source["successor_rootfs_layers_sha256"]
        ),
        expected_overlay_rootfs_layer_count=int(
            source["overlay_rootfs_layer_count"]
        ),
    )
    immutable_image_id = str(image_identity["image_id"])
    if not immutable_image_id.startswith("sha256:"):
        raise CanaryError("inspected worker image has no immutable image ID")

    started = _utc_now()
    run_id = (
        "gate5-pythia-canary-"
        + started.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:12]
    )
    run_dir = (runs_root / run_id).resolve()
    if run_dir.exists():
        raise CanaryError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    (run_dir / "protocol.json").write_bytes(protocol_raw)

    driver_raw = Path(__file__).read_bytes()
    container = "cas-gate5-canary-" + uuid.uuid4().hex[:12]
    env_path: Path | None = None
    container_launch_attempted = False
    container_started = False
    container_id: str | None = None
    health_raw = b""
    health: dict[str, Any] | None = None
    backend_policy_raw = b""
    backend_policy: dict[str, Any] | None = None
    gpu_identity: dict[str, str] | None = None
    exact_health = False
    gpu_runtime_match = False
    backend_policy_exact = False
    container_image_binding: dict[str, Any] | None = None
    arm_summaries: list[dict[str, Any]] = []
    failure: str | None = None
    container_logs = b""
    cleanup_receipt: dict[str, Any] = {
        "stop_returncode": None,
        "logs_returncode": None,
        "forced_remove_attempted": False,
        "container_absence_verified": False,
    }

    token = secrets.token_urlsafe(48)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix="cas_gate5_worker_",
            suffix=".env",
            delete=False,
        ) as handle:
            handle.write(f"ATLAS_LIVE_WORKER_TOKEN={token}\n")
            env_path = Path(handle.name)
        container_launch_attempted = True
        start = _run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                container,
                "--gpus",
                "all",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=64m",
                "--memory",
                "6g",
                "--memory-swap",
                "6g",
                "--pids-limit",
                "512",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges=true",
                "--env-file",
                str(env_path),
                immutable_image_id,
            ],
            timeout=60.0,
        )
        container_started = True
        container_id = start.stdout.decode().strip()
        if not container_id:
            raise CanaryError("docker did not return a container ID")
        env_path.unlink(missing_ok=True)
        env_path = None

        container_image_binding = _inspect_started_container(
            container,
            expected_image_id=immutable_image_id,
            expected_user=expected_user,
        )
        health_raw, health = _wait_for_health(container, timeout_seconds=240.0)
        (run_dir / "realmode_health.json").write_bytes(health_raw)
        gpu_identity = _container_gpu_identity(container)
        if not _health_is_exact(health, source):
            raise CanaryError("real-mode health did not bind the exact production CUDA model")
        exact_health = True
        if not _gpu_matches_runtime(health, gpu_identity):
            raise CanaryError("worker runtime evidence differs from container GPU identity")
        gpu_runtime_match = True
        backend_policy_raw, backend_policy = _container_backend_policy(container)
        (run_dir / "backend_policy.json").write_bytes(backend_policy_raw)
        if not _backend_policy_is_exact(
            backend_policy,
            protocol["adaptation_evidence_binding"],
        ):
            raise CanaryError("worker backend policy differs from the no-JIT BF16 binding")
        backend_policy_exact = True

        for arm in protocol["arms"]:
            request = _build_request(protocol, arm)
            arm_id = str(arm["arm_id"])
            _write_json(run_dir / f"{arm_id}.request.json", request)
            response_raw = _invoke_arm(container, request)
            (run_dir / f"{arm_id}.response.json").write_bytes(response_raw)
            arm_summaries.append(_summarize_arm(arm, response_raw, protocol))
    except Exception as exc:  # retain exact terminal failure instead of erasing it
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        token = ""
        if env_path is not None:
            env_path.unlink(missing_ok=True)
        cleanup_errors: list[str] = []
        if container_launch_attempted:
            logs, logs_error = _run_best_effort(
                ["docker", "logs", container], timeout=30.0
            )
            if logs is not None:
                cleanup_receipt["logs_returncode"] = logs.returncode
                container_logs = logs.stdout + logs.stderr
                if logs.returncode != 0:
                    cleanup_errors.append(f"logs_nonzero: {_process_detail(logs)}")
            if logs_error is not None:
                cleanup_errors.append(f"logs: {logs_error}")
            stopped, stop_error = _run_best_effort(
                ["docker", "stop", "--time", "20", container], timeout=45.0
            )
            if stopped is not None:
                cleanup_receipt["stop_returncode"] = stopped.returncode
                if stopped.returncode != 0:
                    cleanup_errors.append(f"stop_nonzero: {_process_detail(stopped)}")
            if stop_error is not None:
                cleanup_errors.append(f"stop: {stop_error}")
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                inspected, inspect_error = _run_best_effort(
                    ["docker", "inspect", container], timeout=10.0
                )
                if inspect_error is not None:
                    cleanup_errors.append(f"inspect: {inspect_error}")
                    break
                assert inspected is not None
                if _docker_inspect_proves_absence(inspected):
                    cleanup_receipt["container_absence_verified"] = True
                    break
                if inspected.returncode != 0:
                    cleanup_errors.append(
                        f"inspect_nonabsence_error: {_process_detail(inspected)}"
                    )
                    break
                time.sleep(0.5)
            if not cleanup_receipt["container_absence_verified"]:
                cleanup_receipt["forced_remove_attempted"] = True
                removed, remove_error = _run_best_effort(
                    ["docker", "rm", "--force", container], timeout=30.0
                )
                if remove_error is not None:
                    cleanup_errors.append(f"force_remove: {remove_error}")
                elif removed is not None and removed.returncode != 0:
                    cleanup_errors.append(
                        f"force_remove_nonzero: {_process_detail(removed)}"
                    )
                inspected, inspect_error = _run_best_effort(
                    ["docker", "inspect", container], timeout=10.0
                )
                if inspect_error is not None:
                    cleanup_errors.append(f"post_remove_inspect: {inspect_error}")
                elif inspected is not None:
                    cleanup_receipt["container_absence_verified"] = (
                        _docker_inspect_proves_absence(inspected)
                    )
                    if (
                        inspected.returncode != 0
                        and not cleanup_receipt["container_absence_verified"]
                    ):
                        cleanup_errors.append(
                            "post_remove_inspect_nonabsence_error: "
                            + _process_detail(inspected)
                        )
            cleanup_receipt["errors"] = cleanup_errors
            if (
                container_started
                and cleanup_receipt["logs_returncode"] != 0
                and failure is None
            ):
                failure = "CanaryError: container logs could not be retained"
            if not cleanup_receipt["container_absence_verified"] and failure is None:
                failure = "CanaryError: token-bearing worker container remained present"
        else:
            cleanup_receipt["container_absence_verified"] = True
        (run_dir / "container.log").write_bytes(container_logs)

    completed = _utc_now()
    mechanical = (
        _mechanical_receipt(
            arm_summaries,
            exact_health=exact_health,
            gpu_runtime_match=gpu_runtime_match,
            backend_policy_exact=backend_policy_exact,
        )
        if failure is None and len(arm_summaries) == 6
        else {
            "status": "FAIL_CLOSED",
            "checks": {
                "all_six_arms_completed": len(arm_summaries) == 6,
                "runner_failure_absent": failure is None,
            },
            "report_only": {},
        }
    )
    artifacts: list[dict[str, Any]] = []
    for path in sorted(run_dir.iterdir(), key=lambda item: item.name):
        if path.name == "runtime_receipt.json" or not path.is_file():
            continue
        raw = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": _sha256_bytes(raw),
                "bytes": len(raw),
            }
        )
    receipt = {
        "schema_version": "cas_harness_gate5_local_gpu_canary_receipt.v2",
        "run_id": run_id,
        "status": (
            "ENGINEERING GPU CANARY COMPLETE / MECHANICAL PASS"
            if mechanical["status"] == "PASS"
            else "ENGINEERING GPU CANARY TERMINAL / FAIL_CLOSED"
        ),
        "started_at": _iso(started),
        "completed_at": _iso(completed),
        "elapsed_seconds": round((completed - started).total_seconds(), 6),
        "protocol": {
            "protocol_id": protocol["protocol_id"],
            "sha256": _sha256_bytes(protocol_raw),
            "bytes": len(protocol_raw),
        },
        "driver": {
            "path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256_bytes(driver_raw),
            "bytes": len(driver_raw),
            "git_head": git_head,
            "git_branch": branch,
            "clean_at_start": True,
        },
        "container_id": container_id,
        "started_container_image_binding": container_image_binding,
        "image": image_identity,
        "gpu": gpu_identity,
        "realmode_health": health,
        "backend_policy": backend_policy,
        "container_cleanup": cleanup_receipt,
        "arm_summaries": arm_summaries,
        "mechanical_assessment": mechanical,
        "terminal_failure": failure,
        "artifact_manifest": artifacts,
        "provider_spend": {
            "runpod_used": False,
            "provider_calls": 0,
            "known_spend_usd": "0.00",
        },
        "adaptation_evidence": {
            "status": protocol["adaptation_evidence_binding"]["adaptation_status"],
            "diagnostic_ledger_sha256": protocol["adaptation_evidence_binding"][
                "diagnostic_ledger_sha256"
            ],
            "stage27f_bfloat16_calibration_status": protocol[
                "adaptation_evidence_binding"
            ]["stage27f_bfloat16_calibration_status"],
        },
        "joined_gate5_lifecycle": "NOT_EXECUTED / REMAINS NEXT IMPLEMENTATION TRANCHE",
        "experiment_status_effect": (
            "LOCAL_CANARY_EXECUTED / GATE5 SCIENTIFIC EXPERIMENT REMAINS NOT_STARTED"
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(run_dir / "runtime_receipt.json", receipt)
    print(str(run_dir))
    print(receipt["status"])
    if mechanical["status"] != "PASS":
        if failure:
            print(failure, file=sys.stderr)
        raise CanaryError("local GPU canary failed closed; inspect retained receipt")
    return run_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument(
        "--acknowledge-unadmitted-local-canary",
        action="store_true",
        help="Required acknowledgement that this is not an admitted Gate-5 experiment.",
    )
    args = parser.parse_args(argv)
    if not args.acknowledge_unadmitted_local_canary:
        parser.error("--acknowledge-unadmitted-local-canary is required")
    try:
        run_canary(args.protocol.resolve(), args.runs_root.resolve())
    except CanaryError as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
