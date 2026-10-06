#!/usr/bin/env python3
"""Prepare or execute one bounded local Gate-5 joined mechanics smoke.

This runner deliberately uses a single-host SQLite lifecycle and create-only
local files.  Those files are fsync'd and reread, but they are **not WORM** and
are not a production, admitted-route, trusted-time, multi-host, scientific, or
Evidence-Packet authority.  Success means only ``SUCCESS_NO_PACKET_RECORDED``.
Prompt-injection detection and steering efficacy are expressly out of scope.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
for _candidate in (REPO_ROOT / "src", SCAFFOLD):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import httpx  # noqa: E402

from cas_core_v8 import RecordRegistry  # noqa: E402
from cas_harness_v2 import (  # noqa: E402
    WORKER_AUTHORIZATION_MEDIA_TYPE,
    WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
    ArtifactRef,
    PreregistrationChain,
    build_worker_authorization,
    canonical_sha256,
    load_preregistration,
)
from api.services.cas_harness_v2_joined_executor import (  # noqa: E402
    AuthorizationConsumptionAcceptance,
    JoinedGate5Executor,
    JoinedGate5RunPlan,
    JoinedGate5RunResult,
    JoinedLiveDumpPostSendIndeterminate,
    JoinedLiveDumpPreSendFailure,
    NonreportingAcceptance,
    OutcomeSealAcceptance,
    OutputRetentionAcceptance,
    ReconciliationAcceptance,
    SUCCESS_NO_PACKET_RECORDED,
    TerminalAcceptance,
    TerminalDispositionAcceptance,
)
from api.services.cas_harness_v2_live_dump_client import (  # noqa: E402
    StrictLiveWorkerDumpClient,
    StrictLiveWorkerDumpClientConfig,
)
from api.services.cas_harness_v2_live_worker_join import (  # noqa: E402
    ExpectedRealWorkerManifest,
    validate_real_worker_dump_request,
)
from api.services.cas_harness_v2_identity import prospective_run_id  # noqa: E402
from api.services.cas_harness_v2_run_lifecycle import (  # noqa: E402
    ArtifactBinding,
    DurableProspectiveRunLifecycle,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot  # noqa: E402
from api.services.production.state_substrate.sqlite_store import (  # noqa: E402
    SqliteStateStore,
)


CLAIM_ID = "CLM-GATE5-JOINED-MECHANICS-OBSERVATION"
CLAIM_TEXT = (
    "One bounded joined Gate 5 mechanics execution can traverse strict "
    "preregistration binding, lifecycle-issued authorization, one live model "
    "invocation, exact output retention, terminal recording, outcome access, "
    "nonreporting, and reconciliation without creating an Evidence Packet; "
    "this observation excludes prompt-injection detection and steering efficacy."
)
BOUNDARY = (
    "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION / NON-ADMITTED ROUTE / POST-FAILURE ADAPTED / "
    "RESEARCH ONLY / DIAGNOSTIC_ONLY / NO EVIDENCE PACKET / "
    "NO PROMPT-INJECTION DETECTION CLAIM / NO STEERING EFFICACY CLAIM / "
    "GATE 5 OPEN / RING 4 / NOT LICENSED / HELD"
)
MODEL_ID = "EleutherAI/pythia-160m"
MODEL_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
WEIGHTS_FILE = "model.safetensors"
WEIGHTS_SHA256 = "29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270"
WEIGHTS_BYTES = 374_998_696
REQUEST_SOURCE = (
    REPO_ROOT / "docs" / "working" / "project_coherence" / "gate5"
    / "model_smoke" / "runs" / "gate5-pythia-canary-20260807T035947Z-9f81c34de1b6"
    / "adversarial_target_intervention.request.json"
)
REQUEST_SOURCE_SHA256 = "6f52c4070b2b81cb47f3b85947299109152419db98d9294fa2ec60cd2be4e115"
DEFAULT_ROOT = (
    REPO_ROOT / "docs" / "working" / "project_coherence" / "gate5"
    / "joined_model_smoke_v0.2"
)
DEFAULT_PROTOCOL = DEFAULT_ROOT / "GATE5_JOINED_LOCAL_GPU_SMOKE_PROTOCOL_v0.2.json"
DEFAULT_RUNS = DEFAULT_ROOT / "runs"
PREDECESSOR_ROOT = (
    REPO_ROOT / "docs" / "working" / "project_coherence" / "gate5"
    / "joined_model_smoke" / "runs"
    / "gate5-joined-20260807T061801Z-dae9471700c1"
)
PREDECESSOR_RECEIPT = PREDECESSOR_ROOT / "runtime_receipt.json"
PREDECESSOR_CLEANUP = PREDECESSOR_ROOT / "cleanup_proof.json"
PREDECESSOR_RUN_ID = "gate5-joined-20260807T061801Z-dae9471700c1"
PREDECESSOR_RECEIPT_SHA256 = "67f69744a6a89a7cd30c6769e2d2cdf1d840e7bb79002fdc8450ce99675b29f9"
PREDECESSOR_RECEIPT_BYTES = 2_258
PREDECESSOR_CLEANUP_SHA256 = "c0cad307977ad676199a25e19968572b6a2660190d471194965513c8b2db2706"
PREDECESSOR_CLEANUP_BYTES = 186
CLAIM_SCHEMA = REPO_ROOT / "docs" / "working" / "project_coherence" / "CLAIM_RECORD.schema.json"
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_MANIFEST_PATHS = (
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_joined_executor.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_live_dump_client.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_live_worker_join.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_run_lifecycle.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/routes/live_trace.py",
    "scripts/run_project_coherence_gate5_joined_local_gpu_smoke.py",
    "src/cas_harness_v2/preregistration.py",
    "src/cas_harness_v2/worker_protocol.py",
)
PREPARED_ARTIFACT_NAMES = (
    "analysis_manifest.json",
    "claim_ledger.noncanonical.json",
    "dependency_lock.json",
    "fixed_sample_plan.json",
    "live_dump.request.json",
    "model_artifact_manifest.json",
    "network_none_adaptation.json",
    "predecessor_cleanup_proof.json",
    "predecessor_failure_receipt.json",
    "preregistration.json",
    "source_manifest.json",
    "split_confirmatory.json",
    "split_held_out.json",
    "tokenizer_identity.json",
)
PROTOCOL_KEYS = frozenset({
    "schema_version", "protocol_id", "status", "created_at", "claim_id",
    "claim_text", "claim_ceiling", "boundary", "source_commit", "image",
    "artifact_bindings", "model", "job", "invocation_id", "output",
    "controls", "limitations", "predecessor_failure_binding",
})


class JoinedLocalSmokeError(RuntimeError):
    """Fail-closed local runner error."""


def _iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
        + b"\n"
    )


def _sha_lower(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_upper(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _artifact_value(
    artifact_id: str, raw: bytes, media_type: str
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": _sha_upper(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


class LocalExactByteStore:
    """Create-only fsync+reread store; explicitly local and non-WORM."""

    authority = "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION"

    def __init__(self, root: Path, *, create_root: bool = True) -> None:
        self.root = root.resolve()
        if create_root:
            self.root.mkdir(parents=True, exist_ok=False)
            self._fsync_directory(self.root.parent)
        elif not self.root.is_dir():
            raise JoinedLocalSmokeError("exact-byte store root is absent")

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return  # Windows cannot always open directories for fsync.
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def put_exact(
        self,
        relative_path: str,
        body: bytes,
        *,
        artifact_id: str,
        media_type: str,
    ) -> ArtifactBinding:
        if type(body) is not bytes:
            raise JoinedLocalSmokeError("exact-byte body must be immutable bytes")
        relative = Path(relative_path)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise JoinedLocalSmokeError("unsafe exact-byte relative path")
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise JoinedLocalSmokeError("exact-byte path escapes its local root")
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(target, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                target.unlink(missing_ok=True)
            finally:
                raise
        self._fsync_directory(target.parent)
        replay = target.read_bytes()
        if replay != body:
            raise JoinedLocalSmokeError("fsync+reread exact-byte verification failed")
        return ArtifactBinding.from_bytes(
            artifact_id=artifact_id, media_type=media_type, body=replay
        )


def _command(command: Sequence[str], *, timeout: float = 60.0) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).decode(
            "utf-8", errors="replace"
        ).strip()
        raise JoinedLocalSmokeError(f"command failed: {command[0]}: {detail[:1000]}")
    return completed


def _run_best_effort(
    command: Sequence[str], *, timeout: float
) -> tuple[subprocess.CompletedProcess[bytes] | None, str | None]:
    try:
        completed = subprocess.run(
            list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
        return completed, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: cleanup command did not complete"


def _docker_inspect_proves_absence(
    completed: subprocess.CompletedProcess[bytes] | None,
) -> bool:
    if completed is None or completed.returncode == 0:
        return False
    detail = (completed.stderr or completed.stdout).decode(
        "utf-8", errors="replace"
    ).strip().lower()
    return "no such object" in detail or "no such container" in detail


def _container_has_exact_none_network(inspect: Any) -> bool:
    if type(inspect) is not dict:
        return False
    host = inspect.get("HostConfig")
    network = inspect.get("NetworkSettings")
    if not isinstance(host, Mapping) or not isinstance(network, Mapping):
        return False
    if host.get("NetworkMode") != "none" or network.get("Ports") != {}:
        return False
    networks = network.get("Networks")
    if type(networks) is not dict or set(networks) != {"none"}:
        return False
    none = networks["none"]
    if not isinstance(none, Mapping):
        return False
    if (
        re.fullmatch(r"[0-9a-f]{64}", str(none.get("NetworkID") or "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(none.get("EndpointID") or "")) is None
    ):
        return False
    return all(
        none.get(field) in {None, "", 0}
        for field in (
            "Gateway", "IPAddress", "MacAddress", "IPPrefixLen",
            "IPv6Gateway", "GlobalIPv6Address",
            "GlobalIPv6PrefixLen",
        )
    )


def _git_head() -> str:
    return _command(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"]).stdout.decode().strip()


def _git_status_porcelain() -> str:
    return _command(["git", "-C", str(REPO_ROOT), "status", "--porcelain=v1", "--untracked-files=all"]).stdout.decode().strip()


def _git_is_ancestor(ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
    )
    if completed.returncode not in {0, 1}:
        raise JoinedLocalSmokeError("git could not verify the frozen source ancestry")
    return completed.returncode == 0


def _git_changed_paths(ancestor: str, descendant: str) -> tuple[str, ...]:
    completed = _command([
        "git", "-C", str(REPO_ROOT), "diff", "--name-only",
        "--diff-filter=ACDMRTUXB", f"{ancestor}..{descendant}", "--",
    ])
    paths = completed.stdout.decode("utf-8", errors="strict").splitlines()
    if any(not path or "\\" in path for path in paths) or len(paths) != len(set(paths)):
        raise JoinedLocalSmokeError("git returned a noncanonical source-to-execution diff")
    return tuple(paths)


def _require_tracked_file(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(REPO_ROOT) or not resolved.is_file():
        raise JoinedLocalSmokeError("frozen execution artifact is absent or outside the repository")
    relative = resolved.relative_to(REPO_ROOT).as_posix()
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", "--", relative],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
    )
    tracked = completed.stdout.decode("utf-8", errors="strict").splitlines()
    if completed.returncode != 0 or tracked != [relative]:
        raise JoinedLocalSmokeError("frozen execution artifact is not tracked at the clean execution HEAD")


def _inspect_image(image_reference: str) -> dict[str, Any]:
    raw = _command(["docker", "image", "inspect", image_reference], timeout=60).stdout
    try:
        rows = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JoinedLocalSmokeError("docker image inspect was not JSON") from exc
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
        raise JoinedLocalSmokeError("docker image inspect did not return one image")
    return rows[0]


def _image_summary(image_reference: str, inspect: Mapping[str, Any]) -> dict[str, Any]:
    image_id = inspect.get("Id")
    config = inspect.get("Config")
    labels = config.get("Labels") if isinstance(config, Mapping) else None
    if IMAGE_ID_RE.fullmatch(image_id or "") is None or not isinstance(labels, Mapping):
        raise JoinedLocalSmokeError("joined image lacks an exact content identity")
    required = {
        "io.cas-harness.claim-status": "RESEARCH_ONLY_LOCAL_JOINED_MECHANICS",
        "io.cas-harness.joined-binding.authority": "WORKER_PROCESS_OBSERVATION_ONLY",
        "io.cas-harness.scientific-status": "NOT_ESTABLISHED",
        "io.cas-harness.gate5-status": "OPEN",
        "io.cas-harness.license-status": "NOT_LICENSED",
        "io.cas-harness.disclosure-status": "HELD",
    }
    if any(labels.get(key) != value for key, value in required.items()):
        raise JoinedLocalSmokeError("image is not the bounded joined BF16 overlay")
    if config.get("User") not in {"10001", "10001:10001"}:
        raise JoinedLocalSmokeError("joined image user is not 10001")
    return {
        "supplied_reference": image_reference,
        "image_id": image_id,
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "size_bytes": inspect.get("Size"),
        "configured_user": config.get("User"),
        "labels": {key: labels[key] for key in sorted(required)},
        "source_revision_label": labels.get("org.opencontainers.image.revision"),
        "authority": "LOCAL_DOCKER_IMAGE_INSPECTION_ONLY",
    }


def _require_clean_source() -> str:
    status = _git_status_porcelain()
    if status:
        raise JoinedLocalSmokeError("git worktree must be clean before prepare/execute")
    head = _git_head()
    if GIT_SHA_RE.fullmatch(head) is None:
        raise JoinedLocalSmokeError("git HEAD is not a full commit")
    return head


def _source_manifest(commit: str) -> dict[str, Any]:
    files = []
    for relative in SOURCE_MANIFEST_PATHS:
        raw = (REPO_ROOT / relative).read_bytes()
        files.append({"path": relative, "sha256": _sha_lower(raw), "byte_length": len(raw)})
    return {
        "schema_version": "cas_harness_gate5_joined_source_manifest.v1",
        "git_commit": commit,
        "dirty_worktree": False,
        "files": files,
        "boundary": BOUNDARY,
    }


def _claim_record() -> dict[str, Any]:
    return {
        "id": CLAIM_ID, "version": "0.2",
        "title": "Bounded joined Gate 5 mechanics observation",
        "statement_kind": "EMPIRICAL_HYPOTHESIS", "claim_text": CLAIM_TEXT,
        "source_refs": ["RUN-LOCAL-NONCANONICAL-MECHANICS-PROTOCOL"],
        "scope": {
            "population": "One local lifecycle mechanics invocation only",
            "models": [MODEL_ID], "architectures": ["GPT-NeoX / Pythia-160M"],
            "contexts": ["Joined controller-worker mechanics; efficacy excluded"],
            "time_window": "One prepared protocol and one job only",
        },
        "controls": ["Exact request binding", "No automatic model retry", "No Evidence Packet creation"],
        "falsifier": "Any second invocation, binding mismatch, missing terminal state, Packet creation, or unresolved reconciliation defeats the mechanics observation.",
        "uncertainty": "Local SQLite and local files are not WORM, trusted time, multi-host, execution attestation, efficacy evidence, or product validation.",
        "evidence_packets": [], "review_state": "UNASSESSED",
        "product_claim_status": "NOT LICENSED", "admission_ring": 4,
        "disclosure_status": "HELD", "theorem_refs": [], "reviewers": [],
        "last_reviewed_at": None,
        "notes": [
            "Run-local and noncanonical.",
            "Post-failure successor to a retained zero-model-invocation network-verifier rejection.",
            "Prompt-injection detection and steering efficacy are expressly excluded.",
        ],
    }


def _load_predecessor_failure() -> tuple[bytes, bytes]:
    receipt_raw = PREDECESSOR_RECEIPT.read_bytes()
    cleanup_raw = PREDECESSOR_CLEANUP.read_bytes()
    if (
        _sha_lower(receipt_raw) != PREDECESSOR_RECEIPT_SHA256
        or len(receipt_raw) != PREDECESSOR_RECEIPT_BYTES
        or _sha_lower(cleanup_raw) != PREDECESSOR_CLEANUP_SHA256
        or len(cleanup_raw) != PREDECESSOR_CLEANUP_BYTES
    ):
        raise JoinedLocalSmokeError("predecessor failure evidence bytes drifted")
    receipt = json.loads(receipt_raw)
    cleanup = json.loads(cleanup_raw)
    if not (
        type(receipt) is dict
        and receipt.get("run_id") == PREDECESSOR_RUN_ID
        and receipt.get("status") == "FAIL_CLOSED"
        and receipt.get("model_invocation_count") == 0
        and receipt.get("joined_result") is None
        and receipt.get("error")
        == "JoinedLocalSmokeError: container is not attached only to the addressless none network"
        and receipt.get("packet_status") == "NOT CREATED"
        and receipt.get("scientific_efficacy") == "NOT ESTABLISHED"
        and receipt.get("provider_calls") == 0
        and receipt.get("provider_spend_usd") == "0.00"
        and cleanup == {
            "container_absence_specifically_verified": True,
            "container_remove_command_succeeded": True,
            "ephemeral_env_file_removed_after_context": True,
            "network_none_reverified_before_removal": False,
        }
    ):
        raise JoinedLocalSmokeError(
            "predecessor is not the exact retained pre-invocation verifier failure"
        )
    return receipt_raw, cleanup_raw


def _prepare(output_root: Path, *, image_reference: str) -> Path:
    commit = _require_clean_source()
    image = _image_summary(image_reference, _inspect_image(image_reference))
    created_at = _iso()
    predecessor_receipt_raw, predecessor_cleanup_raw = _load_predecessor_failure()
    store = LocalExactByteStore(output_root)

    request_raw = REQUEST_SOURCE.read_bytes()
    if _sha_lower(request_raw) != REQUEST_SOURCE_SHA256:
        raise JoinedLocalSmokeError("retained adversarial F1=0.5 request drifted")
    request = json.loads(request_raw)
    if not (
        request.get("max_new_tokens") == 1
        and request.get("method_config", {}).get("knobs", {}).get("drive_local_eraser")
        == {"drive": "F1", "gain": 0.5}
    ):
        raise JoinedLocalSmokeError("retained request is not the frozen one-token F1=0.5 arm")

    model_manifest_raw = _json_bytes({
        "schema_version": "cas_harness_open_weight_artifact_manifest.v1",
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "model_root": "/model",
        "artifacts": [{"path": WEIGHTS_FILE, "sha256": WEIGHTS_SHA256, "byte_count": WEIGHTS_BYTES}],
    })
    tokenizer_raw = _json_bytes({
        "schema_version": "cas_harness_model_tokenizer_identity.v1",
        "model_id": MODEL_ID, "revision": MODEL_REVISION,
        "status": "IMAGE_BOUND_RUNTIME_IDENTITY / NOT A SEPARATE TOKENIZER HASH CLAIM",
    })
    source_raw = _json_bytes(_source_manifest(commit))
    network_adaptation_raw = _json_bytes({
        "schema_version": "cas_harness_gate5_network_none_adaptation.v1",
        "recorded_at": created_at,
        "clock_authority": "LOCAL ORCHESTRATOR CLOCK / NOT TRUSTED TIME",
        "diagnostic_kind": "NON_MODEL_ENTRYPOINT_CONTAINER",
        "worker_image_id": image["image_id"],
        "model_invocations": 0,
        "observed_network_mode": "none",
        "observed_published_ports": {},
        "observed_attached_network_names": ["none"],
        "running_network_id_profile": "EXACT 64-CHAR LOWERCASE HEX / NON-ROUTABLE IDENTITY ONLY",
        "running_endpoint_id_profile": "EXACT 64-CHAR LOWERCASE HEX / NON-ROUTABLE IDENTITY ONLY",
        "observed_gateway": "",
        "observed_ip_address": "",
        "observed_ipv6_gateway": "",
        "observed_global_ipv6_address": "",
        "adaptation": "Accept exact none-network identity IDs while continuing to require no bridge or user-network attachment and empty IPv4/IPv6 routing fields before and after execution.",
        "claim_boundary": "DOCKER NETWORK-STATE MECHANICS ONLY / NOT MODEL EXECUTION",
    })
    analysis_raw = _json_bytes({
        "schema_version": "cas_harness_gate5_joined_analysis_plan.v2",
        "success_status": SUCCESS_NO_PACKET_RECORDED, "maximum_model_invocations": 1,
        "required_order": ["consume", "invoke_once", "retain_output", "terminal", "outcome_access", "nonreporting", "reconcile"],
        "efficacy_analysis": "EXCLUDED", "packet_creation": "FORBIDDEN",
        "predecessor_failure_receipt": _artifact_value(
            "joined-predecessor-failure-receipt-v01", predecessor_receipt_raw,
            "application/json",
        ),
        "predecessor_cleanup_proof": _artifact_value(
            "joined-predecessor-cleanup-proof-v01", predecessor_cleanup_raw,
            "application/json",
        ),
        "network_none_adaptation": _artifact_value(
            "joined-network-none-adaptation-v02", network_adaptation_raw,
            "application/json",
        ),
        "boundary": BOUNDARY,
    })
    dependency_raw = _json_bytes({
        "schema_version": "cas_harness_gate5_joined_dependency_lock.v1",
        "python": sys.version.split()[0], "runtime_image_id": image["image_id"],
        "model_revision": MODEL_REVISION, "weights_sha256": WEIGHTS_SHA256,
        "runtime_policy": "CUDA BF16 / TORCH NATIVE JIT DISABLED / RETAINED IMAGE",
    })
    confirmatory_raw = _json_bytes({"schema_version": "cas_harness_mechanics_split.v1", "split_id": "mechanics-confirmatory", "rows": ["frozen-adversarial-f1-gain-0.5"], "scientific_use": "NONE"})
    heldout_raw = _json_bytes({"schema_version": "cas_harness_mechanics_split.v1", "split_id": "mechanics-held-out", "rows": ["not-executed-in-this-smoke"], "scientific_use": "NONE"})
    fixed_raw = _json_bytes({"schema_version": "cas_harness_mechanics_fixed_plan.v1", "maximum_jobs": 1, "maximum_model_invocations": 1, "automatic_retry": False, "efficacy_power_analysis": "NOT_APPLICABLE"})

    artifacts = {
        "model_artifact_manifest.json": (model_manifest_raw, "model-open-weight-manifest", "application/json"),
        "tokenizer_identity.json": (tokenizer_raw, "pythia-tokenizer-identity", "application/json"),
        "source_manifest.json": (source_raw, "joined-source-manifest", "application/json"),
        "analysis_manifest.json": (analysis_raw, "joined-analysis-manifest", "application/json"),
        "dependency_lock.json": (dependency_raw, "joined-dependency-lock", "application/json"),
        "split_confirmatory.json": (confirmatory_raw, "mechanics-split-confirmatory", "application/json"),
        "split_held_out.json": (heldout_raw, "mechanics-split-held-out", "application/json"),
        "fixed_sample_plan.json": (fixed_raw, "mechanics-fixed-sample-plan", "application/json"),
        "live_dump.request.json": (request_raw, "joined-live-dump-request", "application/json"),
        "predecessor_failure_receipt.json": (
            predecessor_receipt_raw, "joined-predecessor-failure-receipt-v01",
            "application/json",
        ),
        "predecessor_cleanup_proof.json": (
            predecessor_cleanup_raw, "joined-predecessor-cleanup-proof-v01",
            "application/json",
        ),
        "network_none_adaptation.json": (
            network_adaptation_raw, "joined-network-none-adaptation-v02",
            "application/json",
        ),
    }
    for name, (raw, artifact_id, media_type) in artifacts.items():
        store.put_exact(name, raw, artifact_id=artifact_id, media_type=media_type)

    claim_record = _claim_record()
    ledger_raw = _json_bytes({
        "schema_version": "project_coherence_claim_ledger.v0.1",
        "record_schema": "CLAIM_RECORD.schema.json",
        "document_status": "RUN-LOCAL / NONCANONICAL / OPEN / NOT FROZEN",
        "as_of": created_at[:10], "completeness": "ONE MECHANICS-ONLY CLAIM",
        "records": [claim_record],
    })
    store.put_exact("claim_ledger.noncanonical.json", ledger_raw,
                    artifact_id="joined-noncanonical-claim-ledger", media_type="application/json")
    RecordRegistry.load(
        output_root / "claim_ledger.noncanonical.json", kind="claim",
        expected_raw_sha256=_sha_upper(ledger_raw),
        expected_schema_raw_sha256=_sha_upper(CLAIM_SCHEMA.read_bytes()),
        schema_path=CLAIM_SCHEMA,
    )

    prereg = {
        "schema_version": "cas_harness_v2.preregistration.v1",
        "preregistration_id": "prereg-gate5-joined-mechanics-002",
        "created_at": created_at,
        "claim_binding": {
            "claim_ledger": _artifact_value("joined-noncanonical-claim-ledger", ledger_raw, "application/json"),
            "claim_id": CLAIM_ID, "claim_text": CLAIM_TEXT,
            "claim_record_sha256": canonical_sha256(claim_record),
        },
        "hypothesis": {"primary": CLAIM_TEXT, "null": "The bounded joined mechanics path does not complete exactly once.", "estimand": "Binary exact mechanics completion", "direction": "GREATER"},
        "units": [
            {"measure_id": "joined-completion", "unit": "binary", "operational_definition": "One SUCCESS_NO_PACKET_RECORDED result after reconciliation", "measurement_kind": "DERIVED"},
            {"measure_id": "model-invocations", "unit": "count", "operational_definition": "Strict transport calls crossing the invoke boundary", "measurement_kind": "MEASURED"},
        ],
        "splits": [
            {"split_id": "mechanics-confirmatory", "role": "CONFIRMATORY", "source_artifact": _artifact_value("mechanics-split-confirmatory", confirmatory_raw, "application/json"), "allocation_rule": "Frozen one-row mechanics carrier", "grouping_key": "protocol-job", "minimum_groups": 1, "target_groups": 1, "target_enrolled_rows": 1, "target_analyzed_rows": 1, "maximum_missing_rows": 0, "maximum_excluded_rows": 0},
            {"split_id": "mechanics-held-out", "role": "HELD_OUT_REPLICATION", "source_artifact": _artifact_value("mechanics-split-held-out", heldout_raw, "application/json"), "allocation_rule": "Retained but not executed by this diagnostic smoke", "grouping_key": "protocol-job-heldout", "minimum_groups": 1, "target_groups": 1, "target_enrolled_rows": 1, "target_analyzed_rows": 1, "maximum_missing_rows": 0, "maximum_excluded_rows": 0},
        ],
        "fixed_sample_plan": {"stopping_rule": "FIXED_SAMPLE", "interim_outcome_access": "FORBIDDEN", "row_accounting": "DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED", "exclusion_rule": "Any binding drift fails closed before model execution", "missing_data_rule": "No imputation", "deviation_effect": "SCIENTIFICALLY_INELIGIBLE", "power_analysis": _artifact_value("mechanics-fixed-sample-plan", fixed_raw, "application/json")},
        "thresholds": [
            {"threshold_id": "one-completion", "measure_id": "joined-completion", "operator": "EQ", "value": "1", "unit": "binary", "decision_effect": "REQUIRED_FOR_REPORTED_PASS"},
            {"threshold_id": "one-invocation", "measure_id": "model-invocations", "operator": "EQ", "value": "1", "unit": "count", "decision_effect": "INVALID_IF_VIOLATED"},
        ],
        "controls": [
            {"control_id": "exact-request-binding", "kind": "MATCHED_TAXONOMY", "procedure": "Bind exact request, authorization, run, invocation, and canonical events", "expected_result": "All bindings agree", "failure_effect": "INVALID"},
            {"control_id": "wrong-layer-rejection", "kind": "WRONG_LAYER", "procedure": "Preflight rejects an ablation layer outside the job", "expected_result": "Rejected before invocation", "failure_effect": "INVALID"},
            {"control_id": "clean-null-boundary", "kind": "CLEAN_NULL", "procedure": "Do not interpret this adversarial-only mechanics request as efficacy", "expected_result": "No efficacy claim", "failure_effect": "DOWNGRADE_TO_DIAGNOSTIC"},
        ],
        "falsifiers": [{"falsifier_id": "joined-path-mismatch", "condition": "Any duplicate invocation, byte drift, missing terminal/nonreporting state, Packet creation, or reconciliation issue", "consequence": "INVALID"}],
        "uncertainty": {"method": "Exact deterministic lifecycle assertions only; no efficacy inference", "confidence_level": "0.95", "multiplicity_correction": "NOT_APPLICABLE", "permutations": 1, "seeds": [1729], "grouping_unit": "protocol-job"},
        "identities": {
            "model": {"model_id": MODEL_ID, "revision": MODEL_REVISION, "weights": {"artifact_id": "pythia-160m-model-safetensors", "sha256": WEIGHTS_SHA256.upper(), "byte_length": WEIGHTS_BYTES, "media_type": "application/vnd.safetensors"}, "tokenizer": _artifact_value("pythia-tokenizer-identity", tokenizer_raw, "application/json"), "license_basis": "Open-weight research use; no product license decision"},
            "code": {"commit_sha": commit, "dirty_worktree": False, "source_manifest": _artifact_value("joined-source-manifest", source_raw, "application/json"), "analysis_manifest": _artifact_value("joined-analysis-manifest", analysis_raw, "application/json")},
            "environment": {"environment_id": "gate5-local-joined-bf16-v2", "runtime": "Local Docker NVIDIA GPU / exact joined overlay / post-failure network-none adaptation", "dependency_lock": _artifact_value("joined-dependency-lock", dependency_raw, "application/json"), "container_image_digest": image["image_id"], "hardware_profile": "One local CUDA GPU; actual identity retained at execution"},
        },
        "permitted_wording": {"allowed": ["bounded joined mechanics observation", "SUCCESS_NO_PACKET_RECORDED", "research-only diagnostic"], "forbidden": ["prompt-injection detection validated", "steering efficacy validated", "Gate 5 closed", "production ready", "Evidence Packet created"], "claim_ceiling": "DIAGNOSTIC_ONLY"},
        "governance": {"admission_ring": 4, "product_claim_status": "NOT LICENSED", "disclosure_status": "HELD", "public_release": False, "product_route": False, "license_decision": "NONE"},
    }
    prereg_raw = _json_bytes(prereg)
    store.put_exact("preregistration.json", prereg_raw,
                    artifact_id="prereg-gate5-joined-mechanics-002",
                    media_type="application/vnd.cas-harness.preregistration+json")
    load_preregistration(prereg_raw, claim_ledger_bytes=ledger_raw)

    names = sorted([*artifacts, "claim_ledger.noncanonical.json", "preregistration.json"])
    if tuple(names) != PREPARED_ARTIFACT_NAMES:
        raise JoinedLocalSmokeError("prepared artifact inventory differs from the closed contract")
    bindings = []
    for name in names:
        raw = (output_root / name).read_bytes()
        bindings.append({"path": name, "sha256": _sha_lower(raw), "byte_length": len(raw)})
    protocol = {
        "schema_version": "cas_harness_gate5_joined_local_gpu_smoke_protocol.v2",
        "protocol_id": "gate5-joined-local-gpu-smoke-v0.2",
        "status": "FROZEN / EXECUTION NOT STARTED", "created_at": created_at,
        "claim_id": CLAIM_ID, "claim_text": CLAIM_TEXT, "claim_ceiling": "DIAGNOSTIC_ONLY",
        "boundary": BOUNDARY, "source_commit": commit, "image": image,
        "artifact_bindings": bindings,
        "model": {"model_id": MODEL_ID, "revision": MODEL_REVISION, "weights_filename": WEIGHTS_FILE, "weights_sha256": WEIGHTS_SHA256, "weights_bytes": WEIGHTS_BYTES},
        "job": {"fleet_id": "fleet-gate5-local", "job_id": "gate5-joined-mechanics-002", "audit_id": "audit-gate5-joined-mechanics-002", "assigned_worker_id": "worker-local-gpu-001", "layer_start": 0, "layer_end": 11, "shard_id": "shard-pythia-all-layers", "assigned_methods": request["method_config"]["enabled_methods"], "expected_outputs": ["joined_worker_dump"], "execution_mode": "external_probe_command"},
        "invocation_id": "invocation-gate5-joined-0002",
        "output": {"output_name": "joined_worker_dump", "artifact_id": "joined-worker-dump-output-002", "media_type": "application/json", "terminal_receipt_id": "joined-terminal-receipt-002"},
        "controls": {"maximum_protocols": 1, "maximum_jobs": 1, "maximum_model_invocations": 1, "automatic_model_retry": False, "evidence_packet": "FORBIDDEN"},
        "limitations": {"worm": "NOT ESTABLISHED", "postgres": "NOT USED", "admitted_route": "NOT USED", "scientific_efficacy": "NOT ESTABLISHED", "gate5": "OPEN", "packet": "NOT CREATED"},
        "predecessor_failure_binding": {
            "run_id": PREDECESSOR_RUN_ID,
            "status": "FAIL_CLOSED / ZERO MODEL INVOCATIONS",
            "failure_phase": "PRE-MODEL NETWORK-NONE VERIFIER",
            "failure_receipt": _artifact_value(
                "joined-predecessor-failure-receipt-v01",
                predecessor_receipt_raw, "application/json",
            ),
            "cleanup_proof": _artifact_value(
                "joined-predecessor-cleanup-proof-v01",
                predecessor_cleanup_raw, "application/json",
            ),
            "adaptation": _artifact_value(
                "joined-network-none-adaptation-v02",
                network_adaptation_raw, "application/json",
            ),
        },
    }
    store.put_exact(DEFAULT_PROTOCOL.name, _json_bytes(protocol),
                    artifact_id="gate5-joined-local-protocol-v02", media_type="application/json")
    return output_root / DEFAULT_PROTOCOL.name


@dataclass(frozen=True, slots=True)
class Prepared:
    protocol_path: Path
    protocol_raw: bytes
    protocol: Mapping[str, Any]
    chain: PreregistrationChain
    ledger_raw: bytes
    request_raw: bytes
    model_manifest_raw: bytes
    expected_manifest: ExpectedRealWorkerManifest
    job: FleetJobSnapshot
    validated_execution_commit: str | None = None
    validated_source_to_execution_paths: tuple[str, ...] = ()


def _load_prepared(protocol_path: Path) -> Prepared:
    protocol_raw = protocol_path.read_bytes()
    protocol = json.loads(protocol_raw)
    if not isinstance(protocol, dict) or set(protocol) != PROTOCOL_KEYS or protocol.get("schema_version") != "cas_harness_gate5_joined_local_gpu_smoke_protocol.v2" or protocol.get("status") != "FROZEN / EXECUTION NOT STARTED" or protocol.get("boundary") != BOUNDARY:
        raise JoinedLocalSmokeError("prepared protocol is not the exact frozen local contract")
    root = protocol_path.parent.resolve()
    rows = protocol["artifact_bindings"]
    if type(rows) is not list or len(rows) != len(PREPARED_ARTIFACT_NAMES):
        raise JoinedLocalSmokeError("prepared artifact binding inventory is incomplete")
    observed_names: list[str] = []
    for row in rows:
        if type(row) is not dict or set(row) != {"path", "sha256", "byte_length"}:
            raise JoinedLocalSmokeError("prepared artifact binding row has an open schema")
        if (
            type(row["path"]) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", row["path"]) is None
            or type(row["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or type(row["byte_length"]) is not int
            or row["byte_length"] <= 0
        ):
            raise JoinedLocalSmokeError("prepared artifact binding row is invalid")
        observed_names.append(row["path"])
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise JoinedLocalSmokeError("prepared artifact is absent or unsafe")
        raw = path.read_bytes()
        if _sha_lower(raw) != row["sha256"] or len(raw) != row["byte_length"]:
            raise JoinedLocalSmokeError("prepared artifact bytes drifted")
    if tuple(observed_names) != PREPARED_ARTIFACT_NAMES:
        raise JoinedLocalSmokeError("prepared artifact binding set or order drifted")
    ledger_raw = (root / "claim_ledger.noncanonical.json").read_bytes()
    RecordRegistry.load(root / "claim_ledger.noncanonical.json", kind="claim",
                        expected_raw_sha256=_sha_upper(ledger_raw),
                        expected_schema_raw_sha256=_sha_upper(CLAIM_SCHEMA.read_bytes()),
                        schema_path=CLAIM_SCHEMA)
    prereg_raw = (root / "preregistration.json").read_bytes()
    chain = PreregistrationChain(load_preregistration(prereg_raw, claim_ledger_bytes=ledger_raw))
    request_raw = (root / "live_dump.request.json").read_bytes()
    if _sha_lower(request_raw) != REQUEST_SOURCE_SHA256:
        raise JoinedLocalSmokeError("joined request is not the retained one-token adversarial F1=0.5 carrier")
    model_raw = (root / "model_artifact_manifest.json").read_bytes()
    model = protocol["model"]
    expected = ExpectedRealWorkerManifest(
        model_id=model["model_id"], revision=model["revision"],
        weights_filename=model["weights_filename"], weights_sha256=model["weights_sha256"],
        weights_bytes=model["weights_bytes"],
    )
    validate_real_worker_dump_request(request_raw=request_raw, expected_manifest=expected)
    request_payload = json.loads(request_raw)
    predecessor_receipt_raw = (root / "predecessor_failure_receipt.json").read_bytes()
    predecessor_cleanup_raw = (root / "predecessor_cleanup_proof.json").read_bytes()
    network_adaptation_raw = (root / "network_none_adaptation.json").read_bytes()
    if (
        predecessor_receipt_raw != PREDECESSOR_RECEIPT.read_bytes()
        or predecessor_cleanup_raw != PREDECESSOR_CLEANUP.read_bytes()
    ):
        raise JoinedLocalSmokeError("prepared predecessor bytes differ from the retained failure")
    network_adaptation = json.loads(network_adaptation_raw)
    if not (
        type(network_adaptation) is dict
        and network_adaptation.get("schema_version")
        == "cas_harness_gate5_network_none_adaptation.v1"
        and network_adaptation.get("worker_image_id") == protocol["image"]["image_id"]
        and network_adaptation.get("diagnostic_kind") == "NON_MODEL_ENTRYPOINT_CONTAINER"
        and network_adaptation.get("model_invocations") == 0
        and network_adaptation.get("observed_network_mode") == "none"
        and network_adaptation.get("observed_published_ports") == {}
        and network_adaptation.get("observed_attached_network_names") == ["none"]
        and network_adaptation.get("observed_gateway") == ""
        and network_adaptation.get("observed_ip_address") == ""
        and network_adaptation.get("observed_ipv6_gateway") == ""
        and network_adaptation.get("observed_global_ipv6_address") == ""
        and network_adaptation.get("claim_boundary")
        == "DOCKER NETWORK-STATE MECHANICS ONLY / NOT MODEL EXECUTION"
    ):
        raise JoinedLocalSmokeError("network-none successor adaptation is incomplete")
    expected_controls = {
        "maximum_protocols": 1,
        "maximum_jobs": 1,
        "maximum_model_invocations": 1,
        "automatic_model_retry": False,
        "evidence_packet": "FORBIDDEN",
    }
    expected_limitations = {
        "worm": "NOT ESTABLISHED",
        "postgres": "NOT USED",
        "admitted_route": "NOT USED",
        "scientific_efficacy": "NOT ESTABLISHED",
        "gate5": "OPEN",
        "packet": "NOT CREATED",
    }
    expected_model = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "weights_filename": WEIGHTS_FILE,
        "weights_sha256": WEIGHTS_SHA256,
        "weights_bytes": WEIGHTS_BYTES,
    }
    expected_job = {
        "fleet_id": "fleet-gate5-local",
        "job_id": "gate5-joined-mechanics-002",
        "audit_id": "audit-gate5-joined-mechanics-002",
        "assigned_worker_id": "worker-local-gpu-001",
        "layer_start": 0,
        "layer_end": 11,
        "shard_id": "shard-pythia-all-layers",
        "assigned_methods": request_payload["method_config"]["enabled_methods"],
        "expected_outputs": ["joined_worker_dump"],
        "execution_mode": "external_probe_command",
    }
    expected_output = {
        "output_name": "joined_worker_dump",
        "artifact_id": "joined-worker-dump-output-002",
        "media_type": "application/json",
        "terminal_receipt_id": "joined-terminal-receipt-002",
    }
    expected_predecessor = {
        "run_id": PREDECESSOR_RUN_ID,
        "status": "FAIL_CLOSED / ZERO MODEL INVOCATIONS",
        "failure_phase": "PRE-MODEL NETWORK-NONE VERIFIER",
        "failure_receipt": _artifact_value(
            "joined-predecessor-failure-receipt-v01",
            predecessor_receipt_raw, "application/json",
        ),
        "cleanup_proof": _artifact_value(
            "joined-predecessor-cleanup-proof-v01",
            predecessor_cleanup_raw, "application/json",
        ),
        "adaptation": _artifact_value(
            "joined-network-none-adaptation-v02",
            network_adaptation_raw, "application/json",
        ),
    }
    prereg_payload = chain.base.payload
    if not (
        protocol["protocol_id"] == "gate5-joined-local-gpu-smoke-v0.2"
        and chain.base.preregistration_id == "prereg-gate5-joined-mechanics-002"
        and protocol["claim_id"] == CLAIM_ID == chain.base.claim_id
        and protocol["claim_text"] == CLAIM_TEXT
        == prereg_payload["claim_binding"]["claim_text"]
        and protocol["claim_ceiling"] == "DIAGNOSTIC_ONLY"
        == prereg_payload["permitted_wording"]["claim_ceiling"]
        and protocol["created_at"] == prereg_payload["created_at"]
        and protocol["source_commit"]
        == prereg_payload["identities"]["code"]["commit_sha"]
        and protocol["model"] == expected_model
        and protocol["job"] == expected_job
        and protocol["invocation_id"] == "invocation-gate5-joined-0002"
        and protocol["output"] == expected_output
        and protocol["controls"] == expected_controls
        and protocol["limitations"] == expected_limitations
        and protocol["predecessor_failure_binding"] == expected_predecessor
        and type(protocol["image"]) is dict
        and set(protocol["image"]) == {
            "supplied_reference", "image_id", "architecture", "os", "size_bytes",
            "configured_user", "labels", "source_revision_label", "authority",
        }
        and protocol["image"]["image_id"]
        == prereg_payload["identities"]["environment"]["container_image_digest"]
        and protocol["image"]["authority"]
        == "LOCAL_DOCKER_IMAGE_INSPECTION_ONLY"
    ):
        raise JoinedLocalSmokeError(
            "prepared protocol invariants differ from the preregistered one-call contract"
        )
    job_data = protocol["job"]
    job = FleetJobSnapshot(
        fleet_id=job_data["fleet_id"], job_id=job_data["job_id"], audit_id=job_data["audit_id"],
        assigned_worker_id=job_data["assigned_worker_id"], layer_start=job_data["layer_start"],
        layer_end=job_data["layer_end"], shard_id=job_data["shard_id"],
        assigned_methods=tuple(job_data["assigned_methods"]), expected_outputs=tuple(job_data["expected_outputs"]),
        model_id=model["model_id"], model_revision=model["revision"],
        model_artifact_manifest_path=str((root / "model_artifact_manifest.json").resolve()),
        model_artifact_manifest_sha256=_sha_lower(model_raw), execution_mode=job_data["execution_mode"],
    )
    return Prepared(protocol_path.resolve(), protocol_raw, protocol, chain, ledger_raw,
                    request_raw, model_raw, expected, job)


def _require_frozen_commit_boundary(
    protocol_path: Path,
    prepared: Prepared,
    *,
    source_commit: str,
    execution_commit: str,
) -> tuple[str, ...]:
    execution_root = protocol_path.parent.resolve()
    if not execution_root.is_relative_to(REPO_ROOT):
        raise JoinedLocalSmokeError("frozen execution root is outside the repository")
    root_relative = execution_root.relative_to(REPO_ROOT)
    expected_changes = {
        (root_relative / name).as_posix()
        for name in (*PREPARED_ARTIFACT_NAMES, protocol_path.name)
    }
    changed_paths = _git_changed_paths(source_commit, execution_commit)
    if changed_paths != tuple(sorted(expected_changes)):
        raise JoinedLocalSmokeError(
            "source-to-execution diff is not limited to the exact frozen artifact set"
        )
    _require_tracked_file(protocol_path)
    for row in prepared.protocol["artifact_bindings"]:
        _require_tracked_file(protocol_path.parent / row["path"])
    return changed_paths


def _validate_frozen_source_manifest(path: Path, *, source_commit: str) -> None:
    source = json.loads(path.read_bytes())
    if (
        type(source) is not dict
        or set(source) != {"schema_version", "git_commit", "dirty_worktree", "files", "boundary"}
        or source.get("schema_version") != "cas_harness_gate5_joined_source_manifest.v1"
        or source.get("git_commit") != source_commit
        or source.get("dirty_worktree") is not False
        or source.get("boundary") != BOUNDARY
        or type(source.get("files")) is not list
        or len(source["files"]) != len(SOURCE_MANIFEST_PATHS)
    ):
        raise JoinedLocalSmokeError("frozen source manifest has an incomplete or open schema")
    observed_source_paths: list[str] = []
    for row in source["files"]:
        if (
            type(row) is not dict
            or set(row) != {"path", "sha256", "byte_length"}
            or type(row["path"]) is not str
            or type(row["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or type(row["byte_length"]) is not int
            or row["byte_length"] <= 0
        ):
            raise JoinedLocalSmokeError("frozen source manifest row is invalid")
        observed_source_paths.append(row["path"])
        raw = (REPO_ROOT / row["path"]).read_bytes()
        if _sha_lower(raw) != row["sha256"] or len(raw) != row["byte_length"]:
            raise JoinedLocalSmokeError("source file differs from the frozen manifest")
    if tuple(observed_source_paths) != SOURCE_MANIFEST_PATHS:
        raise JoinedLocalSmokeError("frozen source manifest path set or order drifted")


def _execute_preflight(protocol_path: Path) -> Prepared:
    commit = _require_clean_source()
    prepared = _load_prepared(protocol_path)
    source_commit = prepared.protocol["source_commit"]
    if GIT_SHA_RE.fullmatch(source_commit or "") is None or not _git_is_ancestor(
        source_commit, commit
    ):
        raise JoinedLocalSmokeError(
            "git HEAD does not descend from the frozen source commit"
        )
    changed_paths = _require_frozen_commit_boundary(
        protocol_path,
        prepared,
        source_commit=source_commit,
        execution_commit=commit,
    )
    _validate_frozen_source_manifest(
        protocol_path.parent / "source_manifest.json",
        source_commit=source_commit,
    )
    observed = _image_summary(prepared.protocol["image"]["supplied_reference"],
                              _inspect_image(prepared.protocol["image"]["supplied_reference"]))
    if observed != prepared.protocol["image"]:
        raise JoinedLocalSmokeError("joined container image identity drifted")
    if (protocol_path.parent / "execution_claim.json").exists():
        raise JoinedLocalSmokeError("this one-job protocol already has an execution claim")
    return replace(
        prepared,
        validated_execution_commit=commit,
        validated_source_to_execution_paths=changed_paths,
    )


class _LocalPorts:
    def __init__(self, lifecycle: DurableProspectiveRunLifecycle,
                 store: LocalExactByteStore, chain: PreregistrationChain,
                 tenant: str, subject: str) -> None:
        self.lifecycle, self.store, self.chain = lifecycle, store, chain
        self.tenant, self.subject = tenant, subject

    async def consume_authorization(self, *, authorization, job_snapshot):
        started = datetime.now(UTC)
        raw = _json_bytes({"schema_version": "cas_harness_gate5_local_consumption.v1", "authorization_sha256": authorization.sha256, "job_id": job_snapshot.job_id, "worker_id": job_snapshot.assigned_worker_id, "started_at": _iso(started), "authority": LocalExactByteStore.authority})
        binding = self.store.put_exact("consumption.json", raw, artifact_id="joined-consumption-001", media_type="application/json")
        mutation = self.lifecycle.consume_authorization(tenant_id=self.tenant, subject_id=self.subject,
            run_nonce=authorization.run_nonce_b64url, operation_id="consume-joined-001",
            worker_id=job_snapshot.assigned_worker_id, consumption_artifact=binding, started_at=started)
        return AuthorizationConsumptionAcceptance(authorization_sha256=authorization.sha256,
            job_id=job_snapshot.job_id, worker_started_at=_iso(started),
            idempotent_replay=mutation.idempotent_replay)

    async def retain_output(self, *, authorization, job_snapshot, output_name, artifact, artifact_body):
        del authorization, job_snapshot
        binding = self.store.put_exact("output.json", artifact_body,
            artifact_id=artifact.artifact_id, media_type=artifact.media_type)
        if not (
            binding.sha256 == artifact.sha256.lower()
            and binding.byte_length == artifact.byte_length
            and binding.media_type == artifact.media_type
        ):
            raise JoinedLocalSmokeError("retained output differs from the exact worker artifact")
        return OutputRetentionAcceptance(output_name=output_name, artifact_id=binding.artifact_id,
            artifact_sha256=artifact.sha256, artifact_byte_length=binding.byte_length,
            artifact_media_type=binding.media_type)

    async def accept_terminal(self, *, authorization, job_snapshot, terminal_receipt):
        del authorization, job_snapshot
        binding = self.store.put_exact("terminal_receipt.json", terminal_receipt.raw_bytes,
            artifact_id=terminal_receipt.receipt_id, media_type=WORKER_TERMINAL_RECEIPT_MEDIA_TYPE)
        mutation = self.lifecycle.record_terminal(tenant_id=self.tenant, subject_id=self.subject,
            operation_id="terminal-joined-001", terminal_status="SUCCESS", terminal_artifact=binding,
            terminal_at=datetime.fromisoformat(terminal_receipt.terminal_at.replace("Z", "+00:00")))
        if mutation.idempotent_replay:
            raise JoinedLocalSmokeError("terminal recording replayed")
        return TerminalAcceptance(receipt_id=terminal_receipt.receipt_id,
                                  receipt_sha256=terminal_receipt.sha256)

    async def observe_terminal_at(self):
        return _iso()

    async def seal_outcome(self, *, authorization, job_snapshot, terminal_receipt):
        del authorization, job_snapshot
        accessed = datetime.now(UTC)
        terminal_binding = ArtifactBinding.from_bytes(artifact_id=terminal_receipt.receipt_id,
            media_type=WORKER_TERMINAL_RECEIPT_MEDIA_TYPE, body=terminal_receipt.raw_bytes)
        reservation = self.lifecycle.reserve_outcome_access(tenant_id=self.tenant,
            subject_id=self.subject, operation_id="outcome-joined-001", requested_at=accessed,
            terminal_artifact=terminal_binding)
        event = self.chain.record_outcome_access(accessed_at=reservation.accessed_at,
            execution_completed_at=terminal_receipt.terminal_at,
            receipt=terminal_receipt.outcome_access_receipt_ref)
        event_binding = self.store.put_exact("outcome_access.json", event.raw_bytes,
            artifact_id="joined-outcome-access-001", media_type="application/json")
        mutation = self.lifecycle.finalize_outcome_access(tenant_id=self.tenant,
            subject_id=self.subject, reservation_id=reservation.reservation_id,
            outcome_access_artifact=event_binding)
        if mutation.idempotent_replay:
            raise JoinedLocalSmokeError("outcome recording replayed")
        return OutcomeSealAcceptance(terminal_receipt_sha256=terminal_receipt.sha256)

    async def record_nonreporting(self, *, authorization, job_snapshot,
                                  terminal_receipt, reason_code):
        del authorization, job_snapshot
        recorded = datetime.now(UTC)
        raw = _json_bytes({"schema_version": "cas_harness_gate5_local_nonreporting.v1",
            "run_id": self.lifecycle.get_lifecycle(tenant_id=self.tenant, subject_id=self.subject).run_id,
            "terminal_receipt_sha256": terminal_receipt.sha256,
            "reason_code": reason_code, "recorded_at": _iso(recorded),
            "packet_status": "NOT CREATED", "authority": LocalExactByteStore.authority})
        planned = ArtifactBinding.from_bytes(artifact_id="joined-nonreporting-001",
                                             media_type="application/json", body=raw)
        request_sha = _sha_lower(_json_bytes({"reason_code": reason_code, "subject_id": self.subject}))
        dependency_sha = _sha_lower(_json_bytes({"chain_sha256": self.chain.chain_sha256,
                                                  "terminal_sha256": terminal_receipt.sha256}))
        reservation = self.lifecycle.reserve_reporting_disposition(tenant_id=self.tenant,
            subject_id=self.subject, operation_id="nonreporting-joined-001",
            disposition="NONREPORTING", reason_code=reason_code, request_sha256=request_sha,
            dependency_binding_sha256=dependency_sha, planned_artifact=planned,
            observed_at=recorded)
        binding = self.store.put_exact("nonreporting.json", raw,
            artifact_id=planned.artifact_id, media_type=planned.media_type)
        mutation = self.lifecycle.record_nonreporting(tenant_id=self.tenant,
            subject_id=self.subject, operation_id="nonreporting-joined-001",
            nonreporting_artifact=binding, reason_code=reason_code, recorded_at=recorded,
            reporting_reservation_id=reservation.reservation_id)
        if mutation.idempotent_replay:
            raise JoinedLocalSmokeError("nonreporting recording replayed")
        return NonreportingAcceptance()

    async def record_terminal_disposition(self, *, authorization, job_snapshot,
                                          terminal_status, reason_code):
        del authorization, job_snapshot
        terminal_at = datetime.now(UTC)
        raw = _json_bytes({"schema_version": "cas_harness_gate5_local_terminal_disposition.v1",
            "terminal_status": terminal_status, "reason_code": reason_code,
            "terminal_at": _iso(terminal_at), "authority": LocalExactByteStore.authority})
        binding = self.store.put_exact("terminal_disposition.json", raw,
            artifact_id="joined-terminal-disposition-001", media_type="application/json")
        self.lifecycle.record_terminal(tenant_id=self.tenant, subject_id=self.subject,
            operation_id="terminal-disposition-joined-001", terminal_status=terminal_status,
            terminal_artifact=binding, terminal_at=terminal_at,
            disposition_reason_code=reason_code)
        return TerminalDispositionAcceptance()

    async def reconcile(self, *, authorization, job_snapshot):
        del authorization, job_snapshot
        result = self.lifecycle.reconcile(tenant_id=self.tenant)
        raw = _json_bytes(asdict(result))
        self.store.put_exact("reconciliation.json", raw,
            artifact_id="joined-reconciliation-001", media_type="application/json")
        if not result.structurally_valid:
            raise JoinedLocalSmokeError("local lifecycle reconciliation failed")
        snapshot = self.lifecycle.get_lifecycle(tenant_id=self.tenant, subject_id=self.subject)
        return ReconciliationAcceptance(run_id=snapshot.run_id)


class _RetainingLiveDump:
    def __init__(self, delegate: Any, store: LocalExactByteStore) -> None:
        self.delegate, self.store, self.invocations = delegate, store, 0

    async def invoke_once(self, **kwargs):
        self.invocations += 1
        raw = await self.delegate.invoke_once(**kwargs)
        self.store.put_exact("worker_response.raw.json", raw,
            artifact_id="joined-worker-response-raw-001", media_type="application/json")
        return raw


async def _run_joined_kernel(prepared: Prepared, run_store: LocalExactByteStore,
                             sqlite_path: Path, live_dump: Any,
                             invocation_observer: dict[str, int] | None = None):
    run_store.put_exact("protocol.json", prepared.protocol_raw,
                        artifact_id="joined-run-protocol-copy", media_type="application/json")
    run_store.put_exact("request.json", prepared.request_raw,
                        artifact_id="joined-run-request-copy", media_type="application/json")
    run_store.put_exact("model_artifact_manifest.json", prepared.model_manifest_raw,
                        artifact_id="joined-run-model-manifest-copy", media_type="application/json")
    state = SqliteStateStore(sqlite_path)
    lifecycle = DurableProspectiveRunLifecycle(state)
    tenant, subject = "tenant-local-gate5", prepared.job.job_id
    issued_at, expires_at = datetime.now(UTC), datetime.now(UTC) + timedelta(minutes=30)
    holder: dict[str, Any] = {}
    request_sha = _sha_lower(_json_bytes({"chain_sha256": prepared.chain.chain_sha256,
        "subject_id": subject, "issued_at": _iso(issued_at), "expires_at": _iso(expires_at),
        "execution_mapping": prepared.job.execution_mapping()}))

    def build(nonce_b64: str) -> ArtifactBinding:
        nonce = base64.urlsafe_b64decode(nonce_b64 + "=")
        auth = build_worker_authorization(chain=prepared.chain, authorization_id=subject,
            issued_at=_iso(issued_at), expires_at=_iso(expires_at),
            execution_mapping=prepared.job.execution_mapping(), run_nonce=nonce)
        holder["authorization"] = auth
        return run_store.put_exact("authorization.json", auth.raw_bytes,
            artifact_id=auth.authorization_id, media_type=WORKER_AUTHORIZATION_MEDIA_TYPE)

    issuance = lifecycle.issue_with_builder(tenant_id=tenant, subject_id=subject,
        authorized_at=issued_at, expires_at=expires_at,
        authorization_request_sha256=request_sha, authorization_builder=build)
    if not issuance.issued_now or issuance.run_nonce is None:
        state.close()
        raise JoinedLocalSmokeError("authorization issuance was not fresh")
    authorization = holder["authorization"]
    ports = _LocalPorts(lifecycle, run_store, prepared.chain, tenant, subject)
    retaining = _RetainingLiveDump(live_dump, run_store)
    output = prepared.protocol["output"]
    plan = JoinedGate5RunPlan(chain=prepared.chain, authorization=authorization,
        job_snapshot=prepared.job, live_request_raw=prepared.request_raw,
        expected_manifest=prepared.expected_manifest,
        model_artifact_manifest_raw=prepared.model_manifest_raw,
        output_name=output["output_name"], output_artifact_id=output["artifact_id"],
        output_media_type=output["media_type"], terminal_receipt_id=output["terminal_receipt_id"],
        invocation_id=prepared.protocol["invocation_id"])
    executor = JoinedGate5Executor(worker_protocol=ports, live_dump=retaining,
        clock=ports, controller=ports, terminal_disposition=ports)
    try:
        result = await executor.execute(plan)
        run_store.put_exact("joined_result.json", _json_bytes(asdict(result)),
            artifact_id="joined-result-001", media_type="application/json")
        return result, retaining.invocations
    finally:
        if invocation_observer is not None:
            invocation_observer["count"] = retaining.invocations
        state.close()


_DOCKER_EXEC_DUMP = r'''import hashlib,json,os,sys,urllib.request
try:
    carrier=sys.stdin.buffer.read()
    if len(carrier)<4: raise ValueError()
    n=int.from_bytes(carrier[:4],"big")
    meta=json.loads(carrier[4:4+n].decode("ascii"))
    body=carrier[4+n:]
    headers={
      "Content-Type":"application/json","Accept":"application/json",
      "Accept-Encoding":"identity","X-Atlas-Worker-Token":os.environ["ATLAS_LIVE_WORKER_TOKEN"],
      "X-CAS-Joined-Request-SHA256":hashlib.sha256(body).hexdigest().upper(),
      "X-CAS-Joined-Request-Byte-Length":str(len(body)),
      "X-CAS-Joined-Authorization-SHA256":meta["authorization_sha256"],
      "X-CAS-Joined-Run-ID":meta["prospective_run_id"],
      "X-CAS-Joined-Invocation-ID":meta["invocation_id"]}
    req=urllib.request.Request("http://127.0.0.1:8080/sessions/dump",data=body,headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=180) as response:
      if response.status!=200: raise ValueError()
      content_type=response.headers.get("Content-Type","").split(";",1)[0].strip().lower()
      length_text=response.headers.get("Content-Length","")
      if content_type!="application/json" or not length_text.isascii() or not length_text.isdigit(): raise ValueError()
      length=int(length_text)
      if length<1 or length>2000000: raise ValueError()
      raw=response.read(length+1)
      if len(raw)!=length: raise ValueError()
    sys.stdout.buffer.write(raw)
except BaseException:
    raise SystemExit(73)
'''


class DockerExecLoopbackLiveDump:
    """One-shot local transport: Docker exec -> worker loopback, network none.

    This is not the production HTTP topology.  After the docker-exec boundary
    is entered, every uncertainty is post-send and non-retryable.
    """

    transport_label = "DOCKER_EXEC_LOOPBACK / NETWORK_NONE / LOCAL_ONLY"

    def __init__(self, container: str, *, timeout_seconds: float = 210.0) -> None:
        self.container = container
        self.timeout_seconds = timeout_seconds
        self.calls = 0

    async def invoke_once(self, *, request_raw: bytes, authorization_sha256: str,
                          prospective_run_id: str, invocation_id: str) -> bytes:
        if type(request_raw) is not bytes or not 1 <= len(request_raw) <= 2_000_000:
            raise JoinedLiveDumpPreSendFailure("invalid exact request carrier")
        if re.fullmatch(r"[0-9A-F]{64}", authorization_sha256 or "") is None:
            raise JoinedLiveDumpPreSendFailure("invalid authorization carrier")
        machine = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
        invocation = r"[A-Za-z0-9][A-Za-z0-9._:-]{15,127}"
        if re.fullmatch(machine, prospective_run_id or "") is None or re.fullmatch(invocation, invocation_id or "") is None:
            raise JoinedLiveDumpPreSendFailure("invalid joined identity carrier")
        meta = json.dumps({"authorization_sha256": authorization_sha256,
                           "prospective_run_id": prospective_run_id,
                           "invocation_id": invocation_id},
                          sort_keys=True, separators=(",", ":")).encode("ascii")
        carrier = len(meta).to_bytes(4, "big") + meta + request_raw
        self.calls += 1
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "exec", "--interactive", self.container,
                "python", "-c", _DOCKER_EXEC_DUMP,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(carrier), timeout=self.timeout_seconds
            )
            if process.returncode != 0 or not 1 <= len(stdout) <= 2_000_000:
                raise JoinedLiveDumpPostSendIndeterminate(
                    "docker-exec joined execution disposition is indeterminate"
                )
            return bytes(stdout)
        except JoinedLiveDumpPostSendIndeterminate:
            raise
        except BaseException:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            raise JoinedLiveDumpPostSendIndeterminate(
                "docker-exec joined execution disposition is indeterminate"
            ) from None


_DOCKER_EXEC_HEALTH = r'''import os,sys,urllib.request
try:
  req=urllib.request.Request("http://127.0.0.1:8080/health/realmode",headers={"X-Atlas-Worker-Token":os.environ["ATLAS_LIVE_WORKER_TOKEN"]})
  with urllib.request.urlopen(req,timeout=2) as response:
    if response.status!=200: raise ValueError()
    sys.stdout.buffer.write(response.read(2000001))
except BaseException: raise SystemExit(73)
'''


def _health(container: str, *, timeout_seconds: float = 240.0) -> bytes:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        completed = subprocess.run(
            ["docker", "exec", container, "python", "-c", _DOCKER_EXEC_HEALTH],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False,
        )
        if completed.returncode == 0 and 1 <= len(completed.stdout) <= 2_000_000:
            try:
                value = json.loads(completed.stdout)
                runtime = value.get("runtime_execution", {})
                if value.get("model_id") == MODEL_ID and value.get("resolved_revision") == MODEL_REVISION and value.get("weights_sha256") == WEIGHTS_SHA256 and value.get("weights_bytes") == WEIGHTS_BYTES and value.get("model_loaded") is True and value.get("is_real_model") is True and runtime.get("device") == "cuda" and runtime.get("dtype") == "torch.bfloat16" and runtime.get("torch_native_jit_disabled") is True:
                    return completed.stdout
            except json.JSONDecodeError:
                pass
        time.sleep(0.25)
    raise JoinedLocalSmokeError("exact BF16/no-JIT CUDA health did not become ready")


def _redact(value: Any, secret: str) -> Any:
    if isinstance(value, str):
        return value.replace(secret, "REDACTED_EPHEMERAL_WORKER_TOKEN")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, secret) for key, item in value.items()}
    return value


def _joined_result_is_exact_success(
    result: Any,
    *,
    prepared: Prepared,
    invocation_count: int,
    run_root: Path,
) -> bool:
    if type(result) is not JoinedGate5RunResult:
        return False
    upper_sha = r"[0-9A-F]{64}"
    canonical_time = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z"
    if not (
        result.status == SUCCESS_NO_PACKET_RECORDED
        and result.failure_phase is None
        and result.error_code is None
        and type(invocation_count) is int
        and invocation_count == result.model_invocation_count == 1
        and re.fullmatch(upper_sha, result.authorization_sha256 or "") is not None
        and result.prospective_run_id == prospective_run_id(prepared.job.job_id)
        and result.request_sha256 == _sha_upper(prepared.request_raw)
        and re.fullmatch(upper_sha, result.response_sha256 or "") is not None
        and type(result.response_byte_length) is int
        and 1 <= result.response_byte_length <= 2_000_000
        and result.output_artifact_id
        == prepared.protocol["output"]["artifact_id"]
        and result.output_artifact_sha256 == result.response_sha256
        and re.fullmatch(canonical_time, result.worker_started_at or "") is not None
        and re.fullmatch(canonical_time, result.terminal_at or "") is not None
        and re.fullmatch(upper_sha, result.terminal_receipt_sha256 or "") is not None
        and result.terminal_disposition_recorded is False
        and result.reconciled is True
        and result.packet_status == "NOT_CREATED"
        and result.gate_status == "OPEN"
        and result.scientific_status == "NOT_ESTABLISHED"
        and result.product_status == "RESEARCH_ONLY"
        and result.license_status == "NOT LICENSED"
        and result.disclosure_status == "HELD"
    ):
        return False
    try:
        started = datetime.fromisoformat(
            result.worker_started_at.replace("Z", "+00:00")
        )
        terminal = datetime.fromisoformat(result.terminal_at.replace("Z", "+00:00"))
        authorization_raw = (run_root / "authorization.json").read_bytes()
        response_raw = (run_root / "worker_response.raw.json").read_bytes()
        output_raw = (run_root / "output.json").read_bytes()
        terminal_raw = (run_root / "terminal_receipt.json").read_bytes()
        result_raw = (run_root / "joined_result.json").read_bytes()
    except (OSError, ValueError):
        return False
    return (
        started <= terminal
        and _sha_upper(authorization_raw) == result.authorization_sha256
        and len(response_raw) == result.response_byte_length
        and _sha_upper(response_raw) == result.response_sha256
        and output_raw == response_raw
        and _sha_upper(output_raw) == result.output_artifact_sha256
        and _sha_upper(terminal_raw) == result.terminal_receipt_sha256
        and result_raw == _json_bytes(asdict(result))
    )


def _execute(protocol_path: Path, runs_root: Path) -> Path:
    prepared = _execute_preflight(protocol_path)
    execution_commit = prepared.validated_execution_commit
    if execution_commit is None:
        raise JoinedLocalSmokeError("execution commit was not retained from preflight")
    run_id = "gate5-joined-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(6)
    runs_root.mkdir(parents=True, exist_ok=True)
    run_store = LocalExactByteStore(runs_root / run_id)
    claim_store = LocalExactByteStore(protocol_path.parent, create_root=False)
    claim_store.put_exact("execution_claim.json", _json_bytes({
        "schema_version": "cas_harness_gate5_joined_execution_claim.v1",
        "protocol_sha256": _sha_lower(prepared.protocol_raw), "run_id": run_id,
        "claimed_at": _iso(), "maximum_model_invocations": 1,
        "frozen_source_commit": prepared.protocol["source_commit"],
        "clean_execution_commit": execution_commit,
        "source_to_execution_changed_paths": list(
            prepared.validated_source_to_execution_paths
        ),
        "authority": LocalExactByteStore.authority,
    }), artifact_id="joined-execution-claim-001", media_type="application/json")

    token = secrets.token_urlsafe(48)
    container = "cas-g5-joined-worker-" + secrets.token_hex(5)
    image_id = prepared.protocol["image"]["image_id"]
    invocation_count = 0
    result = None
    error: str | None = None
    cleanup: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="cas-g5-joined-") as temp:
        env_path = Path(temp) / "worker.env"
        descriptor = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(f"ATLAS_LIVE_WORKER_TOKEN={token}\n".encode())
            stream.flush(); os.fsync(stream.fileno())
        try:
            _command(["docker", "run", "--detach", "--name", container,
                "--network", "none", "--gpus", "all", "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
                "--memory", "6g", "--memory-swap", "6g", "--pids-limit", "512",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                "--user", "10001:10001", "--env-file", str(env_path),
                "--env", "PORT=8080", image_id], timeout=120)
            inspect_raw = _command(["docker", "inspect", container], timeout=30).stdout
            inspect_value = _redact(json.loads(inspect_raw), token)
            if (
                type(inspect_value) is not list
                or len(inspect_value) != 1
                or not _container_has_exact_none_network(inspect_value[0])
            ):
                raise JoinedLocalSmokeError(
                    "container is not attached only to the addressless none network"
                )
            run_store.put_exact("container_inspect.redacted.json", _json_bytes(inspect_value),
                artifact_id="joined-container-inspect-redacted", media_type="application/json")
            health_raw = _health(container)
            run_store.put_exact("realmode_health.json", health_raw,
                artifact_id="joined-realmode-health", media_type="application/json")
            async def invoke():
                nonlocal invocation_count, result
                live = DockerExecLoopbackLiveDump(container)
                observed = {"count": 0}
                try:
                    result, invocation_count = await _run_joined_kernel(
                        prepared, run_store, run_store.root / "lifecycle.sqlite3", live,
                        invocation_observer=observed)
                finally:
                    invocation_count = observed["count"]
            asyncio.run(invoke())
            if not _joined_result_is_exact_success(
                result,
                prepared=prepared,
                invocation_count=invocation_count,
                run_root=run_store.root,
            ):
                raise JoinedLocalSmokeError(
                    "joined executor did not retain one complete reconciled success"
                )
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc).replace(token, '[REDACTED]')}"
        finally:
            post_inspect, post_inspect_error = _run_best_effort(
                ["docker", "inspect", container], timeout=30
            )
            post_network_none = False
            if post_inspect is not None and post_inspect.returncode == 0:
                try:
                    post_rows = json.loads(post_inspect.stdout)
                    post_network_none = (
                        type(post_rows) is list
                        and len(post_rows) == 1
                        and _container_has_exact_none_network(post_rows[0])
                    )
                except (UnicodeDecodeError, json.JSONDecodeError):
                    post_network_none = False
            try:
                logs = _command(["docker", "logs", container], timeout=30).stdout
            except Exception as exc:
                logs = f"logs unavailable: {type(exc).__name__}\n".encode()
            logs = logs.replace(
                token.encode("utf-8"), b"REDACTED_EPHEMERAL_WORKER_TOKEN"
            )
            removed, remove_error = _run_best_effort(
                ["docker", "rm", "--force", container], timeout=60
            )
            inspected, inspect_error = _run_best_effort(
                ["docker", "inspect", container], timeout=30
            )
            cleanup = {
                "network_none_reverified_before_removal": post_network_none,
                "container_remove_command_succeeded": (
                    removed is not None and removed.returncode == 0
                ),
                "container_absence_specifically_verified": (
                    _docker_inspect_proves_absence(inspected)
                ),
            }
            if error is None and (
                post_inspect_error is not None
                or remove_error is not None
                or inspect_error is not None
            ):
                error = "CleanupError: container cleanup command was unresolved"
            try:
                run_store.put_exact("container.log", logs,
                    artifact_id="joined-container-log", media_type="text/plain")
            except Exception:
                if error is None:
                    error = "CleanupEvidenceError: container log could not be retained"
    cleanup["ephemeral_env_file_removed_after_context"] = not env_path.exists()
    if error is None and not all(cleanup.values()):
        error = "CleanupError: exact container or ephemeral-file cleanup was not proven"
    run_store.put_exact("cleanup_proof.json", _json_bytes(cleanup),
        artifact_id="joined-cleanup-proof", media_type="application/json")
    if error is not None:
        run_store.put_exact("failure.json", _json_bytes({"status": "FAIL_CLOSED",
            "error": error, "model_invocation_count": invocation_count,
            "automatic_retry": False}), artifact_id="joined-failure-001", media_type="application/json")
    secret_found = any(token.encode() in path.read_bytes() for path in run_store.root.rglob("*") if path.is_file())
    run_store.put_exact("secret_scan.json", _json_bytes({"status": "PASS" if not secret_found else "FAIL",
        "ephemeral_worker_token_found": secret_found}), artifact_id="joined-secret-scan", media_type="application/json")
    manifest = []
    for path in sorted(item for item in run_store.root.rglob("*") if item.is_file()):
        raw = path.read_bytes()
        manifest.append({"path": path.relative_to(run_store.root).as_posix(),
                         "sha256": _sha_lower(raw), "byte_length": len(raw)})
    run_store.put_exact("artifact_manifest.json", _json_bytes(manifest),
        artifact_id="joined-run-artifact-manifest", media_type="application/json")
    status = SUCCESS_NO_PACKET_RECORDED if error is None and not secret_found and all(cleanup.values()) else "FAIL_CLOSED"
    receipt = {
        "schema_version": "cas_harness_gate5_joined_local_gpu_smoke_receipt.v2",
        "run_id": run_id, "status": status, "model_invocation_count": invocation_count,
        "joined_result": None if result is None else asdict(result), "error": error,
        "packet_status": "NOT CREATED", "scientific_efficacy": "NOT ESTABLISHED",
        "gate5_status": "OPEN", "admission_ring": 4,
        "product_claim_status": "NOT LICENSED", "disclosure_status": "HELD",
        "local_storage_authority": LocalExactByteStore.authority,
        "local_runtime_transport": DockerExecLoopbackLiveDump.transport_label,
        "production_transport_dependency": "StrictLiveWorkerDumpClient / NOT USED BY THIS LOCAL RUN",
        "frozen_source_commit": prepared.protocol["source_commit"],
        "clean_execution_commit": execution_commit,
        "source_to_execution_changed_paths": list(
            prepared.validated_source_to_execution_paths
        ),
        "postgres": "NOT USED", "admitted_route": "NOT USED", "worm": "NOT ESTABLISHED",
        "provider_calls": 0, "provider_spend_usd": "0.00", "boundary": BOUNDARY,
    }
    receipt_path = run_store.root / "runtime_receipt.json"
    run_store.put_exact("runtime_receipt.json", _json_bytes(receipt),
        artifact_id="joined-runtime-receipt", media_type="application/json")
    if status != SUCCESS_NO_PACKET_RECORDED:
        raise JoinedLocalSmokeError(f"joined local smoke failed closed; receipt={receipt_path}")
    return receipt_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--image", help="already-built joined overlay image reference")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS)
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            if not args.image:
                parser.error("--prepare requires --image")
            print(_prepare(args.output_root, image_reference=args.image))
        else:
            print(_execute(args.protocol, args.runs_root))
        return 0
    except JoinedLocalSmokeError as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
