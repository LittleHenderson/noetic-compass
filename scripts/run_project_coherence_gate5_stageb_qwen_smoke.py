#!/usr/bin/env python3
"""Bind and execute one local Stage-B Qwen joined run with one Packet v2.

This is a create-once, local Ring-4 engineering runner.  It preserves the
frozen prospective protocol and activates it only through the one exact
``EXECUTION_IDENTITY_ADDITION`` amendment the protocol allows.  Execution is
one local Docker invocation with ``--network none`` and no automatic retry.

Success establishes only that the bounded software path completed and that a
structurally complete, scientifically ineligible Evidence Packet v2 was
retained.  It does not establish prompt-injection detection, steering efficacy,
authenticated execution, scientific validity, product readiness, licensing,
or disclosure authority.  Gate 5 remains OPEN / KEEP_OPEN.
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
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
from typing import Any, BinaryIO, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
SCAFFOLD = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
for _candidate in reversed((REPO_ROOT / "src", SCAFFOLD, SCRIPTS_ROOT)):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from cas_harness_v2 import (  # noqa: E402
    ArtifactRef,
    ControlResultInput,
    EvidencePacketBuildInputs,
    FalsifierResultInput,
    MetricResultInput,
    PreregistrationChain,
    RetainedArtifactInput,
    RetainedFileArtifactInput,
    SplitResultInput,
    build_evidence_packet,
    build_worker_authorization,
    load_preregistration,
)
from api.services.cas_harness_v2_joined_executor import (  # noqa: E402
    JoinedGate5Executor,
    JoinedGate5RunPlan,
    JoinedGate5RunResult,
    PacketRecordingAcceptance,
    ReconciliationAcceptance,
    SUCCESS_PACKET_RECORDED,
)
from api.services.cas_harness_v2_live_worker_join import (  # noqa: E402
    ExpectedRealWorkerManifest,
    QWEN_OBSERVATION_ONLY_HOOK_PROFILE,
    validate_real_worker_dump_request,
)
from api.services.cas_harness_v2_run_lifecycle import (  # noqa: E402
    ArtifactBinding,
    DurableProspectiveRunLifecycle,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot  # noqa: E402
from api.services.production.state_substrate.sqlite_store import SqliteStateStore  # noqa: E402

import run_project_coherence_gate5_joined_local_gpu_smoke as joined  # noqa: E402


PACKAGE_ROOT = (
    REPO_ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate5"
    / "stageb_qwen_model_smoke_v0.1"
)
PROTOCOL_PATH = PACKAGE_ROOT / "GATE5_STAGEB_QWEN_JOINED_ENGINEERING_PROTOCOL_v0.1.json"
PREREG_PATH = PACKAGE_ROOT / "preregistration.json"
LEDGER_PATH = PACKAGE_ROOT / "claim_ledger.noncanonical.json"
AMENDMENT_PATH = PACKAGE_ROOT / "execution_identity_amendment.json"
EXECUTION_CLAIM_PATH = PACKAGE_ROOT / "execution_claim.json"
RUNS_ROOT = PACKAGE_ROOT / "runs"

PARENT_IMAGE_REFERENCE = "atlas-live-trace-worker:gate5-stageb-qwen05b-instruct-v0.1"
PARENT_IMAGE_ID = "sha256:373ac33e26c4e3e82ac34690c08e7af58b4b925fe0410e6a0a175b10b9fd2139"
RUNTIME_IMAGE_REFERENCE = "atlas-live-trace-worker:gate5-stageb-qwen05b-runtime-v0.1"
RUNTIME_DOCKERFILE = (
    SCAFFOLD / "live-trace-worker" / "Dockerfile.qwen-stageb-runtime-overlay"
)
WORKER_ROOT = SCAFFOLD / "live-trace-worker"

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
EXPECTED_GPU_NAME = "NVIDIA GeForce RTX 4070 Laptop GPU"
EXPECTED_GPU_CAPABILITY = "8.9"
WEIGHTS_FILENAME = "model.safetensors"
WEIGHTS_SHA256 = "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
WEIGHTS_BYTES = 988_097_824
WEIGHTS_ARTIFACT_ID = "qwen25-05b-instruct-model-safetensors"
WEIGHTS_CONTAINER_PATH = (
    "/worker/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
    "snapshots/7ae557604adf67be50417f59c2c2f167def9a775/model.safetensors"
)
WEIGHTS_STREAM_CHUNK_BYTES = 4 * 1024 * 1024
WEIGHTS_ARCHIVE_ROOT = Path(
    r"D:\tksCAS-archive\project_coherence_stageb_retained_blobs"
)
WEIGHTS_ARCHIVE_PATH = WEIGHTS_ARCHIVE_ROOT / (
    f"sha256-{WEIGHTS_SHA256}.model.safetensors"
)
MODEL_BINDING_KEY = "qwen2.5-0.5b-instruct"
PROTOCOL_SHA256 = "7DD9F543059692B292F08FBC510817F8BF181615468911DAD8CA773B7D5F6A11"
REQUEST_SHA256 = "D4127311457CF48F474D5D262D69910DE934FEE2D1B47150764992C0FBC3C6D3"

PACKET_ID = "epv2-stageb-qwen-joined-001"
PACKET_ARTIFACT_ID = "stageb-qwen-evidence-packet-001"
OUTPUT_NAME = "stageb_qwen_joined_worker_dump"
OUTPUT_ARTIFACT_ID = "stageb-qwen-joined-worker-dump-001"
TERMINAL_RECEIPT_ID = "stageb-qwen-terminal-receipt-001"
INVOCATION_ID = "stageb-qwen-joined-invocation-0001"
JOB_ID = "stageb-qwen-joined-job-001"

BOUNDARY = (
    "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION / RESEARCH ONLY / "
    "ONE MODEL INVOCATION / ONE PACKET MAXIMUM / NO INTERVENTION / "
    "REPORTED_CRITERIA_NOT_MET / INELIGIBLE / GATE 5 OPEN / RING 4 / "
    "NOT LICENSED / HELD"
)

RUNTIME_IMAGE_RECEIPT = PACKAGE_ROOT / "final_runtime_image_identity.json"
FINAL_SOURCE_MANIFEST = PACKAGE_ROOT / "final_executable_source_manifest.json"
QWEN_TEST_RECEIPT = PACKAGE_ROOT / "qwen_probe_adapter_test_receipt.json"
PACKET_TEST_RECEIPT = PACKAGE_ROOT / "evidence_packet_builder_test_receipt.json"
FINAL_CODE_IDENTITY = PACKAGE_ROOT / "final_executable_code_identity.json"
ACTIVATION_RECEIPT = PACKAGE_ROOT / "execution_activation_receipt.json"

ADDITIONAL_ARTIFACT_FILES: tuple[tuple[str, Path, str], ...] = (
    (
        "stageb-final-executable-code-identity",
        FINAL_CODE_IDENTITY,
        "application/json",
    ),
    (
        "stageb-final-executable-source-manifest",
        FINAL_SOURCE_MANIFEST,
        "application/json",
    ),
    (
        "stageb-qwen-probe-adapter-test-receipt",
        QWEN_TEST_RECEIPT,
        "application/json",
    ),
    (
        "stageb-evidence-packet-builder-test-receipt",
        PACKET_TEST_RECEIPT,
        "application/json",
    ),
    (
        "stageb-final-runtime-image-identity",
        RUNTIME_IMAGE_RECEIPT,
        "application/json",
    ),
)

SOURCE_PATHS = (
    "src/cas_harness_v2/__init__.py",
    "src/cas_harness_v2/artifacts.py",
    "src/cas_harness_v2/evidence_packet_builder.py",
    "src/cas_harness_v2/evidence_packet.py",
    "src/cas_harness_v2/preregistration.py",
    "src/cas_harness_v2/worker_protocol.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_joined_executor.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_live_worker_join.py",
    "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_run_lifecycle.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/routes/health.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/routes/live_trace.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/__init__.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/manifest.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/event_stream.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/ablation_probe.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/knob_resolution.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/model_loader.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/probe_runner.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/pythia_runner.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/Dockerfile.qwen-instruct-overlay",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/Dockerfile.qwen-stageb-runtime-overlay",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_container_preflight.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_qwen_probe_adapter.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_ablation_probe.py",
    "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_health.py",
    "tests/cas_harness_v2/test_evidence_packet_builder.py",
    "noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_joined_executor.py",
    "noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_live_worker_join.py",
    "scripts/run_project_coherence_gate5_stageb_qwen_smoke.py",
    "tests/model_smoke/test_gate5_stageb_qwen_smoke.py",
)

GENERATED_BINDING_PATHS = {
    path.relative_to(REPO_ROOT).as_posix()
    for path in (
        RUNTIME_IMAGE_RECEIPT,
        FINAL_SOURCE_MANIFEST,
        QWEN_TEST_RECEIPT,
        PACKET_TEST_RECEIPT,
        FINAL_CODE_IDENTITY,
        AMENDMENT_PATH,
        ACTIVATION_RECEIPT,
    )
}
GENERATED_BINDING_PATHS.add(
    "docs/working/project_coherence/gate5/GATE5_ARTIFACT_MANIFEST_v0.1.json"
)

SHA256_LOWER_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256_UPPER_RE = re.compile(r"^[0-9A-F]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class StageBSmokeError(RuntimeError):
    """Fail-closed Stage B binding or execution error."""


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _sha_lower(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_upper(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def _run(
    command: Sequence[str],
    *,
    cwd: Path = REPO_ROOT,
    timeout: float = 120.0,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=None if env is None else dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        tail = completed.stdout[-4000:].decode("utf-8", errors="replace")
        raise StageBSmokeError(
            f"command failed ({completed.returncode}): {list(command)!r}\n{tail}"
        )
    return completed


def _git_head() -> str:
    value = _run(["git", "rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    if GIT_SHA_RE.fullmatch(value) is None:
        raise StageBSmokeError("current Git HEAD is not an exact commit SHA")
    return value


def _git_status() -> str:
    return _run(["git", "status", "--porcelain=v1"]).stdout.decode(
        "utf-8", errors="strict"
    )


def _require_clean_source_paths(commit: str) -> None:
    for raw_path in SOURCE_PATHS:
        path = REPO_ROOT / Path(*PurePosixPath(raw_path).parts)
        if not path.is_file() or path.is_symlink():
            raise StageBSmokeError(f"required Stage B source is absent or unsafe: {raw_path}")
        committed = _run(["git", "show", f"{commit}:{raw_path}"]).stdout
        if path.read_bytes() != committed:
            raise StageBSmokeError(f"Stage B source differs from clean commit: {raw_path}")


def _write_create_only(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    if path.read_bytes() != raw:
        raise StageBSmokeError(f"create-only artifact reread failed: {path}")


def _has_reparse_attribute(value: os.stat_result) -> bool:
    attributes = int(getattr(value, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _require_regular_file_no_links(path: Path) -> os.stat_result:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise StageBSmokeError(f"retained file cannot be inspected: {path}") from exc
    if (
        path.is_symlink()
        or _has_reparse_attribute(observed)
        or not stat.S_ISREG(observed.st_mode)
        or int(getattr(observed, "st_nlink", 1)) != 1
    ):
        raise StageBSmokeError(f"retained file is not a regular non-reparse file: {path}")
    return observed


def _require_directory_no_links(path: Path) -> os.stat_result:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise StageBSmokeError(f"retained directory cannot be inspected: {path}") from exc
    if (
        path.is_symlink()
        or _has_reparse_attribute(observed)
        or not stat.S_ISDIR(observed.st_mode)
    ):
        raise StageBSmokeError(f"retained directory is not a real local directory: {path}")
    return observed


def _ensure_directory_tree_no_links(path: Path) -> Path:
    if not path.is_absolute() or not path.anchor:
        raise StageBSmokeError("external archive root must be a lexical absolute path")
    current = Path(path.anchor)
    _require_directory_no_links(current)
    for part in path.parts[1:]:
        candidate = current / part
        if os.path.lexists(candidate):
            _require_directory_no_links(candidate)
        else:
            try:
                candidate.mkdir(mode=0o700)
            except FileExistsError:
                pass
            _require_directory_no_links(candidate)
        current = candidate
    resolved = path.resolve(strict=True)
    if os.path.normcase(str(path)) != os.path.normcase(str(resolved)):
        raise StageBSmokeError("external archive root resolves through an alternate path")
    return resolved


def _read_only_file_observation(path: Path) -> dict[str, Any]:
    observed = _require_regular_file_no_links(path)
    write_mask = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    mode_read_only = not bool(stat.S_IMODE(observed.st_mode) & write_mask)
    attributes = int(getattr(observed, "st_file_attributes", 0))
    readonly_flag = int(getattr(stat, "FILE_ATTRIBUTE_READONLY", 0x1))
    attribute_read_only = (
        bool(attributes & readonly_flag)
        if hasattr(observed, "st_file_attributes")
        else None
    )
    if not mode_read_only and attribute_read_only is not True:
        raise StageBSmokeError("external weight archive is not read-only")
    sha256, byte_length, _found = _stream_file_observation(path)
    return {
        "sha256": sha256,
        "byte_length": byte_length,
        "mode_octal": f"{stat.S_IMODE(observed.st_mode):04o}",
        "mode_read_only": mode_read_only,
        "file_attribute_read_only": attribute_read_only,
        "st_nlink": int(getattr(observed, "st_nlink", 1)),
    }


def _freeze_file_read_only(path: Path) -> dict[str, Any]:
    _require_regular_file_no_links(path)
    os.chmod(path, stat.S_IREAD)
    return _read_only_file_observation(path)


def _stream_file_observation(
    path: Path,
    *,
    secret: bytes | None = None,
) -> tuple[str, int, bool]:
    """Hash and optionally scan one regular file without loading it into RAM."""

    before = _require_regular_file_no_links(path)
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    byte_count = 0
    found = False
    overlap = b""
    try:
        opened = os.fstat(descriptor)
        if not os.path.samestat(before, opened):
            raise StageBSmokeError(f"retained file changed while opening: {path}")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            while True:
                chunk = handle.read(WEIGHTS_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
                byte_count += len(chunk)
                if secret is not None and not found:
                    scan = overlap + chunk
                    found = secret in scan
                    if len(secret) > 1:
                        overlap = scan[-(len(secret) - 1) :]
            opened_after = os.fstat(handle.fileno())
        after = _require_regular_file_no_links(path)
        if (
            not os.path.samestat(opened, opened_after)
            or not os.path.samestat(opened, after)
            or opened_after.st_size != byte_count
        ):
            raise StageBSmokeError(f"retained file changed during streaming: {path}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return digest.hexdigest(), byte_count, found


def _extract_exact_weight_tar_stream(
    tar_stream: BinaryIO,
    destination: Path,
    *,
    expected_sha256: str = WEIGHTS_SHA256,
    expected_bytes: int = WEIGHTS_BYTES,
    expected_filename: str = WEIGHTS_FILENAME,
) -> dict[str, Any]:
    """Create one exact regular file from a ``docker cp ... -`` tar stream."""

    if type(expected_sha256) is not str or SHA256_LOWER_RE.fullmatch(expected_sha256) is None:
        raise StageBSmokeError("weight-stream SHA-256 expectation is invalid")
    if type(expected_bytes) is not int or expected_bytes <= 0:
        raise StageBSmokeError("weight-stream byte expectation is invalid")
    _require_directory_no_links(destination.parent)
    if os.path.lexists(destination):
        raise FileExistsError(f"create-only weight destination already exists: {destination}")

    created = False
    member_count = 0
    streamed_sha256 = ""
    streamed_bytes = 0
    try:
        with tarfile.open(fileobj=tar_stream, mode="r|*") as archive:
            for member in archive:
                member_count += 1
                member_path = PurePosixPath(member.name)
                if (
                    member_count != 1
                    or member_path.is_absolute()
                    or not member_path.parts
                    or any(part in {"", ".", ".."} for part in member_path.parts)
                    or member_path.name != expected_filename
                    or not member.isreg()
                    or member.size != expected_bytes
                ):
                    raise StageBSmokeError(
                        "Docker weight stream is not one exact safe regular-file member"
                    )
                source = archive.extractfile(member)
                if source is None:
                    raise StageBSmokeError("Docker weight stream member cannot be opened")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                flags |= int(getattr(os, "O_BINARY", 0))
                descriptor = os.open(destination, flags, 0o600)
                created = True
                digest = hashlib.sha256()
                try:
                    with os.fdopen(descriptor, "wb", closefd=True) as target:
                        while True:
                            chunk = source.read(WEIGHTS_STREAM_CHUNK_BYTES)
                            if not chunk:
                                break
                            streamed_bytes += len(chunk)
                            if streamed_bytes > expected_bytes:
                                raise StageBSmokeError(
                                    "Docker weight stream exceeded the frozen byte length"
                                )
                            digest.update(chunk)
                            target.write(chunk)
                        target.flush()
                        os.fsync(target.fileno())
                finally:
                    source.close()
                streamed_sha256 = digest.hexdigest()
        if member_count != 1:
            raise StageBSmokeError("Docker weight stream did not contain exactly one member")
        if streamed_bytes != expected_bytes or streamed_sha256 != expected_sha256:
            raise StageBSmokeError("Docker weight stream identity differs from the frozen artifact")
        persisted_sha256, persisted_bytes, _found = _stream_file_observation(destination)
        if persisted_bytes != expected_bytes or persisted_sha256 != expected_sha256:
            raise StageBSmokeError("persisted weight artifact failed streamed exact-byte replay")
        return {
            "sha256": persisted_sha256,
            "byte_length": persisted_bytes,
            "source_member": expected_filename,
            "regular_file": True,
            "symlink_or_reparse": False,
        }
    except BaseException:
        if created:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _copy_weight_tar_from_created_container(
    container: str,
    destination: Path,
    *,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Stream ``docker cp`` stdout with a watchdog and bounded stderr storage."""

    command = ["docker", "cp", f"{container}:{WEIGHTS_CONTAINER_PATH}", "-"]
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        if process.stdout is None:
            process.kill()
            process.wait()
            raise StageBSmokeError("Docker weight stream has no stdout pipe")
        timed_out = threading.Event()

        def kill_after_timeout() -> None:
            timed_out.set()
            try:
                process.kill()
            except OSError:
                pass

        watchdog = threading.Timer(timeout_seconds, kill_after_timeout)
        watchdog.daemon = True
        watchdog.start()
        try:
            observation = _extract_exact_weight_tar_stream(process.stdout, destination)
            return_code = process.wait()
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
        finally:
            watchdog.cancel()
            process.stdout.close()
        if timed_out.is_set():
            destination.unlink(missing_ok=True)
            raise StageBSmokeError("Docker weight streaming exceeded its local timeout")
        if return_code != 0:
            destination.unlink(missing_ok=True)
            stderr.seek(0, os.SEEK_END)
            end = stderr.tell()
            stderr.seek(max(0, end - 4000))
            detail = stderr.read().decode("utf-8", errors="replace")
            raise StageBSmokeError(f"Docker weight streaming failed: {detail}")
    return observation


def _materialize_weight_artifact_from_image() -> tuple[Path, dict[str, Any]]:
    """Reuse or materialize the content-addressed external weight archive."""

    if WEIGHTS_ARCHIVE_PATH.parent != WEIGHTS_ARCHIVE_ROOT:
        raise StageBSmokeError("content-addressed weight path escaped its archive root")
    archive_root = _ensure_directory_tree_no_links(WEIGHTS_ARCHIVE_ROOT)
    destination = archive_root / WEIGHTS_ARCHIVE_PATH.name
    if os.path.lexists(destination):
        stable = _read_only_file_observation(destination)
        if stable["sha256"] != WEIGHTS_SHA256 or stable["byte_length"] != WEIGHTS_BYTES:
            raise StageBSmokeError(
                "existing content-addressed weight archive differs; overwrite is forbidden"
            )
        return destination, {
            "schema_version": "cas_harness_gate5_stageb_weight_materialization.v0.1",
            "source_image_id": PARENT_IMAGE_ID,
            "source_container_path": WEIGHTS_CONTAINER_PATH,
            "helper_container_id": None,
            "helper_container_started": False,
            "helper_network": "NONE",
            "transport": "STABLE VERIFIED CONTENT-ADDRESSED ARCHIVE REUSE",
            "artifact_id": WEIGHTS_ARTIFACT_ID,
            "sha256": stable["sha256"],
            "byte_length": stable["byte_length"],
            "retained_path": destination.as_posix(),
            "storage_scope": "EXTERNAL CONTENT-ADDRESSED ARCHIVE / OUTSIDE PACKAGE_ROOT",
            "reused_existing": True,
            "regular_file": True,
            "symlink_or_reparse": False,
            "mode_octal": stable["mode_octal"],
            "mode_read_only": stable["mode_read_only"],
            "file_attribute_read_only": stable["file_attribute_read_only"],
            "st_nlink": stable["st_nlink"],
            "helper_container_absence_verified": True,
            "model_execution": "NOT STARTED",
            "provider_calls": 0,
            "provider_spend_usd": "0.00",
        }

    helper = "cas-g5-stageb-weight-copy-" + secrets.token_hex(6)
    container_id: str | None = None
    cleanup_ok = False
    observation: dict[str, Any] | None = None
    try:
        created = _run(
            [
                "docker",
                "create",
                "--name",
                helper,
                "--network",
                "none",
                "--entrypoint",
                "/bin/false",
                PARENT_IMAGE_ID,
            ],
            timeout=120,
        )
        container_id = created.stdout.decode("ascii", errors="strict").strip()
        if re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
            raise StageBSmokeError("Docker returned no exact helper-container identity")
        inspected = json.loads(_run(["docker", "inspect", helper], timeout=30).stdout)
        if (
            type(inspected) is not list
            or len(inspected) != 1
            or inspected[0].get("Id") != container_id
            or inspected[0].get("Image") != PARENT_IMAGE_ID
            or inspected[0].get("HostConfig", {}).get("NetworkMode") != "none"
            or inspected[0].get("State", {}).get("Running") is not False
            or inspected[0].get("State", {}).get("Status") != "created"
        ):
            raise StageBSmokeError("weight-copy helper is not the pinned never-started container")
        observation = _copy_weight_tar_from_created_container(helper, destination)
        frozen = _freeze_file_read_only(destination)
        if (
            frozen["sha256"] != observation["sha256"]
            or frozen["byte_length"] != observation["byte_length"]
        ):
            raise StageBSmokeError("read-only weight freeze changed the exact artifact")
        observation.update(frozen)
    finally:
        if container_id is not None:
            removed, _remove_error = joined._run_best_effort(
                ["docker", "rm", helper], timeout=60
            )
            absent, _inspect_error = joined._run_best_effort(
                ["docker", "inspect", helper], timeout=30
            )
            cleanup_ok = bool(
                removed is not None
                and removed.returncode == 0
                and joined._docker_inspect_proves_absence(absent)
            )
    if observation is None:
        raise StageBSmokeError("weight-copy helper retained no exact artifact")
    if not cleanup_ok:
        raise StageBSmokeError("weight-copy helper container cleanup was not proven")
    receipt = {
        "schema_version": "cas_harness_gate5_stageb_weight_materialization.v0.1",
        "source_image_id": PARENT_IMAGE_ID,
        "source_container_path": WEIGHTS_CONTAINER_PATH,
        "helper_container_id": container_id,
        "helper_container_started": False,
        "helper_network": "NONE",
        "transport": "DOCKER CP TAR STDOUT / STREAMED",
        "artifact_id": WEIGHTS_ARTIFACT_ID,
        "sha256": observation["sha256"],
        "byte_length": observation["byte_length"],
        "retained_path": destination.as_posix(),
        "storage_scope": "EXTERNAL CONTENT-ADDRESSED ARCHIVE / OUTSIDE PACKAGE_ROOT",
        "reused_existing": False,
        "regular_file": observation["regular_file"],
        "symlink_or_reparse": observation["symlink_or_reparse"],
        "mode_octal": observation["mode_octal"],
        "mode_read_only": observation["mode_read_only"],
        "file_attribute_read_only": observation["file_attribute_read_only"],
        "st_nlink": observation["st_nlink"],
        "helper_container_absence_verified": True,
        "model_execution": "NOT STARTED",
        "provider_calls": 0,
        "provider_spend_usd": "0.00",
    }
    return destination, receipt


def _artifact_ref(artifact_id: str, raw: bytes, media_type: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": _sha_upper(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


def _app_tree_identity() -> tuple[str, int, list[dict[str, Any]]]:
    root = WORKER_ROOT / "app"
    rows: list[dict[str, Any]] = []
    tree = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if not path.is_file() or path.is_symlink():
            raise StageBSmokeError("worker app source contains an unsafe path")
        raw = path.read_bytes()
        relative = path.relative_to(WORKER_ROOT).as_posix()
        digest = _sha_lower(raw)
        tree.update(f"{relative}\t{len(raw)}\t{digest}\n".encode("utf-8"))
        rows.append({"path": relative, "sha256": digest, "byte_length": len(raw)})
    if not rows:
        raise StageBSmokeError("worker app source tree is empty")
    return tree.hexdigest(), len(rows), rows


def _inspect_image(reference: str) -> dict[str, Any]:
    raw = _run(["docker", "image", "inspect", reference], timeout=60).stdout
    value = json.loads(raw)
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise StageBSmokeError("Docker returned an invalid image inspection")
    return value[0]


def _image_identity(reference: str, *, parent_reference: str) -> dict[str, Any]:
    image = _inspect_image(reference)
    parent = _inspect_image(parent_reference)
    image_id = image.get("Id")
    parent_id = parent.get("Id")
    size = image.get("Size")
    labels = image.get("Config", {}).get("Labels")
    layers = image.get("RootFS", {}).get("Layers")
    parent_layers = parent.get("RootFS", {}).get("Layers")
    if (
        type(image_id) is not str
        or IMAGE_ID_RE.fullmatch(image_id) is None
        or type(parent_id) is not str
        or IMAGE_ID_RE.fullmatch(parent_id) is None
        or type(size) is not int
        or size <= 0
        or type(labels) is not dict
        or type(layers) is not list
        or type(parent_layers) is not list
        or layers[: len(parent_layers)] != parent_layers
        or len(layers) <= len(parent_layers)
    ):
        raise StageBSmokeError("runtime image does not prove an additive parent-layer prefix")
    return {
        "reference": reference,
        "image_id": image_id,
        "config_digest": image_id,
        "config_digest_note": "Docker local image ID is the SHA-256 of the image configuration JSON.",
        "size_bytes": size,
        "parent_reference": parent_reference,
        "parent_image_id": parent_id,
        "parent_layer_count": len(parent_layers),
        "total_layer_count": len(layers),
        "added_layer_count": len(layers) - len(parent_layers),
        "parent_rootfs_is_exact_prefix": True,
        "labels": {str(key): str(value) for key, value in sorted(labels.items())},
        "authority": "LOCAL DOCKER IMAGE INSPECTION / NOT A SIGNED REGISTRY ATTESTATION",
    }


def _build_runtime_image() -> Path:
    if RUNTIME_IMAGE_RECEIPT.exists():
        raise StageBSmokeError("runtime image identity already exists; rebuild/retry is forbidden")
    commit = _git_head()
    if _git_status():
        raise StageBSmokeError("runtime image must be built from a completely clean worktree")
    _require_clean_source_paths(commit)
    tree_sha, file_count, rows = _app_tree_identity()
    _run(
        [
            "docker",
            "build",
            "--network=none",
            "--file",
            str(RUNTIME_DOCKERFILE),
            "--build-arg",
            f"PARENT_IMAGE={PARENT_IMAGE_REFERENCE}",
            "--build-arg",
            f"STAGEB_SOURCE_COMMIT={commit}",
            "--build-arg",
            f"STAGEB_APP_TREE_SHA256={tree_sha}",
            "--build-arg",
            f"STAGEB_APP_FILE_COUNT={file_count}",
            "--tag",
            RUNTIME_IMAGE_REFERENCE,
            ".",
        ],
        cwd=WORKER_ROOT,
        timeout=900,
    )
    identity = _image_identity(
        RUNTIME_IMAGE_REFERENCE,
        parent_reference=PARENT_IMAGE_REFERENCE,
    )
    if identity.get("parent_image_id") != PARENT_IMAGE_ID:
        raise StageBSmokeError("runtime image parent differs from the frozen Qwen image")
    labels = identity["labels"]
    expected_labels = {
        "org.opencontainers.image.revision": commit,
        "io.cas-harness.runtime-overlay.source": commit,
        "io.cas-harness.runtime-overlay.app-tree-sha256": tree_sha,
        "io.cas-harness.runtime-overlay.app-file-count": str(file_count),
        "io.cas-harness.stageb.model-id": MODEL_ID,
        "io.cas-harness.stageb.model-revision": MODEL_REVISION,
        "io.cas-harness.gate5-status": "OPEN",
        "io.cas-harness.license-status": "NOT_LICENSED",
        "io.cas-harness.disclosure-status": "HELD",
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise StageBSmokeError("runtime image labels do not bind the final source/model boundary")
    receipt = {
        "schema_version": "cas_harness_gate5_stageb_runtime_image_identity.v0.1",
        "created_at": _iso(),
        "source_commit": commit,
        "worker_app_tree_sha256": tree_sha,
        "worker_app_file_count": file_count,
        "worker_app_files": rows,
        "image": identity,
        "model": {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "weights_filename": WEIGHTS_FILENAME,
            "weights_sha256": WEIGHTS_SHA256,
            "weights_bytes": WEIGHTS_BYTES,
        },
        "provider_calls": 0,
        "provider_spend_usd": "0.00",
        "model_invocations": 0,
        "joined_request_invocations": 0,
        "runtime_validation": "DEFERRED TO THE AUTHORIZED JOINED EXECUTION",
        "execution_status": "NOT_STARTED",
        "gate5_status": "OPEN",
        "admission_ring": 4,
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "boundary": BOUNDARY,
    }
    _write_create_only(RUNTIME_IMAGE_RECEIPT, _pretty_json_bytes(receipt))
    return RUNTIME_IMAGE_RECEIPT


def _load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if not 1 <= len(raw) <= 2_000_000:
        raise StageBSmokeError(f"JSON artifact is absent or out of bounds: {path}")
    value = json.loads(raw)
    if type(value) is not dict:
        raise StageBSmokeError(f"JSON artifact is not an object: {path}")
    return value


def _validate_base_package() -> tuple[dict[str, Any], PreregistrationChain]:
    protocol_raw = PROTOCOL_PATH.read_bytes()
    if _sha_upper(protocol_raw) != PROTOCOL_SHA256:
        raise StageBSmokeError("frozen Stage B protocol identity drifted")
    protocol = _load_json(PROTOCOL_PATH)
    model_and_image = protocol.get("model_and_image", {})
    if (
        protocol.get("schema_version")
        != "cas_harness_gate5_stageb_qwen_joined_engineering_protocol.v0.1"
        or protocol.get("protocol_freeze_status") != "FROZEN PROSPECTIVE DESIGN"
        or protocol.get("experimental_execution_status") != "NOT_STARTED"
        or protocol.get("gate5_status") != "OPEN"
        or protocol.get("product_route_authorized") is not False
        or protocol.get("authorization", {}).get("current_state")
        != "INACTIVE / EXECUTION UNAUTHORIZED / NOT_STARTED"
        or model_and_image.get("image_reference") != PARENT_IMAGE_REFERENCE
        or model_and_image.get("image_id") != PARENT_IMAGE_ID
    ):
        raise StageBSmokeError("prospective Stage B protocol boundary drifted")
    bindings = protocol.get("artifact_bindings")
    if type(bindings) is not list or not bindings:
        raise StageBSmokeError("prospective protocol artifact bindings are missing")
    observed_paths: set[str] = set()
    for row in bindings:
        if type(row) is not dict or set(row) != {"path", "sha256", "byte_length"}:
            raise StageBSmokeError("prospective protocol artifact row is malformed")
        raw_path = row.get("path")
        digest = row.get("sha256")
        byte_length = row.get("byte_length")
        if (
            type(raw_path) is not str
            or not raw_path
            or Path(raw_path).is_absolute()
            or ".." in PurePosixPath(raw_path).parts
            or raw_path in observed_paths
            or type(digest) is not str
            or SHA256_LOWER_RE.fullmatch(digest) is None
            or type(byte_length) is not int
            or byte_length < 1
        ):
            raise StageBSmokeError("prospective protocol artifact row is unsafe")
        path = PACKAGE_ROOT / Path(*PurePosixPath(raw_path).parts)
        raw = path.read_bytes()
        if len(raw) != byte_length or _sha_lower(raw) != digest:
            raise StageBSmokeError(f"prospective protocol artifact drifted: {raw_path}")
        observed_paths.add(raw_path)

    prereg_raw = PREREG_PATH.read_bytes()
    ledger_raw = LEDGER_PATH.read_bytes()
    base = load_preregistration(prereg_raw, claim_ledger_bytes=ledger_raw)
    if (
        base.sha256 != "4F7D32A9364FC5A470B0FEE575D53C15D027D52CB013AB3EDBBD059A3CCED57D"
        or base.protected_design_sha256
        != "41ECD9E07637F457ED4A4832ED436A8A425675DD2B24C6A15EC1033B5E90D59F"
    ):
        raise StageBSmokeError("prospective preregistration identity drifted")
    chain = PreregistrationChain(base)
    if chain.outcome_access is not None or chain.amendments:
        raise StageBSmokeError("prospective preregistration is not an unaccessed base chain")
    return protocol, chain


def _test_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    return env


def _run_test_command(command: Sequence[str], cwd: Path) -> dict[str, Any]:
    started = _iso()
    completed = _run(
        command,
        cwd=cwd,
        timeout=600,
        env=_test_environment(),
    )
    completed_at = _iso()
    output = completed.stdout
    return {
        "command": list(command),
        "working_directory": cwd.relative_to(REPO_ROOT).as_posix()
        if cwd != REPO_ROOT
        else ".",
        "started_at": started,
        "completed_at": completed_at,
        "exit_code": completed.returncode,
        "stdout_stderr_sha256": _sha_upper(output),
        "stdout_stderr_byte_length": len(output),
        "output_tail": output[-2000:].decode("utf-8", errors="replace"),
        "result": "PASSED",
    }


def _source_manifest(commit: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw_path in SOURCE_PATHS:
        committed = _run(["git", "show", f"{commit}:{raw_path}"]).stdout
        current = REPO_ROOT / Path(*PurePosixPath(raw_path).parts)
        if current.read_bytes() != committed:
            raise StageBSmokeError(f"final source path is not clean: {raw_path}")
        rows.append(
            {
                "path": raw_path,
                "sha256": _sha_lower(committed),
                "byte_length": len(committed),
            }
        )
    return {
        "schema_version": "cas_harness_gate5_stageb_final_source_manifest.v0.1",
        "source_commit": commit,
        "dirty_source_paths": False,
        "files": rows,
        "boundary": BOUNDARY,
    }


def _binding_status_paths() -> set[str]:
    status = _git_status().splitlines()
    paths: set[str] = set()
    for line in status:
        if len(line) < 4:
            raise StageBSmokeError("cannot parse Git worktree status")
        raw_path = line[3:].strip().replace("\\", "/")
        if " -> " in raw_path:
            raise StageBSmokeError("renamed paths are forbidden during binding")
        paths.add(raw_path)
    return paths


def _prepare_execution_binding() -> Path:
    protocol, chain = _validate_base_package()
    if AMENDMENT_PATH.exists() or any(
        path.exists()
        for path in (FINAL_SOURCE_MANIFEST, QWEN_TEST_RECEIPT, PACKET_TEST_RECEIPT, FINAL_CODE_IDENTITY)
    ):
        raise StageBSmokeError("execution identity was already prepared; replacement is forbidden")
    if not RUNTIME_IMAGE_RECEIPT.is_file():
        raise StageBSmokeError("build the exact runtime image before preparing the amendment")

    commit = _git_head()
    _require_clean_source_paths(commit)
    status_paths = _binding_status_paths()
    expected_uncommitted = {RUNTIME_IMAGE_RECEIPT.relative_to(REPO_ROOT).as_posix()}
    if status_paths != expected_uncommitted:
        raise StageBSmokeError(
            "binding preparation permits only the new runtime-image receipt; "
            f"observed={sorted(status_paths)}"
        )

    image_receipt = _load_json(RUNTIME_IMAGE_RECEIPT)
    if (
        image_receipt.get("source_commit") != commit
        or image_receipt.get("execution_status") != "NOT_STARTED"
        or image_receipt.get("provider_calls") != 0
        or image_receipt.get("provider_spend_usd") != "0.00"
        or image_receipt.get("model_invocations") != 0
        or image_receipt.get("joined_request_invocations") != 0
        or image_receipt.get("runtime_validation")
        != "DEFERRED TO THE AUTHORIZED JOINED EXECUTION"
    ):
        raise StageBSmokeError("runtime image receipt is not bound to this clean source commit")
    observed_image = _image_identity(
        RUNTIME_IMAGE_REFERENCE,
        parent_reference=PARENT_IMAGE_REFERENCE,
    )
    if (
        observed_image != image_receipt.get("image")
        or observed_image.get("parent_image_id") != PARENT_IMAGE_ID
    ):
        raise StageBSmokeError("local runtime image differs from its retained identity")
    qwen_test = {
        "schema_version": "cas_harness_gate5_stageb_qwen_adapter_test_receipt.v0.1",
        "created_at": _iso(),
        "source_commit": commit,
        "commands": [
            _run_test_command(
                [sys.executable, "-B", "-m", "pytest", "tests", "-q"],
                WORKER_ROOT,
            )
        ],
        "covered_contracts": [
            "Qwen selected-binding runtime canary",
            "model.layers[i].mlp.down_proj probe capture at 4864 to 896",
            "pinned tokenizer chat template applied once with no raw fallback",
            "Qwen refusal of Pythia Stage-27F coordinates",
            "historical Pythia default behavior retained",
        ],
        "authority": "LOCAL UNATTESTED REGRESSION / NOT SCIENTIFIC EVIDENCE",
        "result": "PASSED",
    }
    _write_create_only(QWEN_TEST_RECEIPT, _pretty_json_bytes(qwen_test))

    packet_test = {
        "schema_version": "cas_harness_gate5_stageb_packet_path_test_receipt.v0.1",
        "created_at": _iso(),
        "source_commit": commit,
        "commands": [
            _run_test_command(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "tests/cas_harness_v2/test_evidence_packet_builder.py",
                    "-q",
                ],
                REPO_ROOT,
            ),
            _run_test_command(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "tests/test_cas_harness_v2_joined_executor.py",
                    "-q",
                ],
                SCAFFOLD,
            ),
            _run_test_command(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "tests/model_smoke/test_gate5_stageb_qwen_smoke.py",
                    "-q",
                ],
                REPO_ROOT,
            ),
        ],
        "covered_contracts": [
            "exact authorization and completed terminal-receipt replay",
            "structural-only execution manifest derivation",
            "complete exact-byte Evidence Packet inventory",
            "streamed external file-backed weight retention without a full-RAM load",
            "create-only content-addressed weight materialization and read-only reuse",
            "outcome access before packet recording",
            "pre-claim weight preparation and post-outcome Packet reservation ordering",
            "packet reservation, record, and reconciliation without a second invocation",
            "INVALID controls retained as REPORTED_CRITERIA_NOT_MET / INELIGIBLE",
        ],
        "authority": "LOCAL UNATTESTED REGRESSION / NOT SCIENTIFIC EVIDENCE",
        "result": "PASSED",
    }
    _write_create_only(PACKET_TEST_RECEIPT, _pretty_json_bytes(packet_test))

    source_manifest_raw = _pretty_json_bytes(_source_manifest(commit))
    _write_create_only(FINAL_SOURCE_MANIFEST, source_manifest_raw)

    supporting_refs = {
        artifact_id: _artifact_ref(artifact_id, path.read_bytes(), media_type)
        for artifact_id, path, media_type in ADDITIONAL_ARTIFACT_FILES
        if path != FINAL_CODE_IDENTITY
    }
    final_identity = {
        "schema_version": "cas_harness_gate5_stageb_final_executable_code_identity.v0.1",
        "created_at": _iso(),
        "source_commit": commit,
        "dirty_worktree_at_source_commit": False,
        "source_manifest": supporting_refs["stageb-final-executable-source-manifest"],
        "qwen_probe_adapter_test_receipt": supporting_refs[
            "stageb-qwen-probe-adapter-test-receipt"
        ],
        "evidence_packet_builder_test_receipt": supporting_refs[
            "stageb-evidence-packet-builder-test-receipt"
        ],
        "runtime_image_identity": supporting_refs["stageb-final-runtime-image-identity"],
        "model": {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "weights_filename": WEIGHTS_FILENAME,
            "weights_sha256": WEIGHTS_SHA256,
            "weights_bytes": WEIGHTS_BYTES,
        },
        "execution_limits": {
            "maximum_runs": 1,
            "maximum_model_invocations": 1,
            "maximum_packets": 1,
            "automatic_retry": False,
            "network": "NONE",
            "interventions": 0,
            "provider_calls": 0,
            "provider_spend_usd": "0.00",
        },
        "gate5_status": "OPEN",
        "admission_ring": 4,
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "boundary": BOUNDARY,
    }
    _write_create_only(FINAL_CODE_IDENTITY, _pretty_json_bytes(final_identity))

    additional_refs = [
        _artifact_ref(artifact_id, path.read_bytes(), media_type)
        for artifact_id, path, media_type in ADDITIONAL_ARTIFACT_FILES
    ]
    expected_ids = protocol["authorization"]["activation_precondition"]
    if "EXECUTION_IDENTITY_ADDITION" not in expected_ids:
        raise StageBSmokeError("prospective protocol no longer requires the exact amendment")

    base_created = datetime.fromisoformat(
        chain.base.payload["created_at"].replace("Z", "+00:00")
    ).astimezone(UTC)
    now = datetime.now(UTC)
    amendment_time = max(now, base_created + timedelta(microseconds=1))
    amendment_value = {
        "schema_version": "cas_harness_v2.preregistration_amendment.v1",
        "amendment_id": "AMD-G5-STAGEB-QWEN-EXECUTION-001",
        "created_at": _iso(amendment_time),
        "base_preregistration_sha256": chain.base.sha256,
        "previous_amendment_sha256": None,
        "reason": (
            "Prospectively add the final clean executable source, Qwen adapter tests, "
            "Packet-path tests, and exact local runtime image identities required by "
            "the frozen Stage B protocol."
        ),
        "change_class": "EXECUTION_IDENTITY_ADDITION",
        "changes": {"additional_artifacts": additional_refs},
        "outcome_access": {"accessed": False, "evidence_ref": None},
    }
    amendment_raw = _json_bytes(amendment_value)
    amendment = chain.append_amendment(amendment_raw)
    if len(chain.amendments) != 1 or chain.outcome_access is not None:
        raise StageBSmokeError("execution identity amendment did not create one pre-outcome link")
    _write_create_only(AMENDMENT_PATH, amendment_raw)

    activation_receipt = {
        "schema_version": "cas_harness_gate5_stageb_execution_activation_receipt.v0.1",
        "created_at": _iso(),
        "protocol_sha256": _sha_upper(PROTOCOL_PATH.read_bytes()),
        "base_preregistration_sha256": chain.base.sha256,
        "amendment_sha256": amendment.sha256,
        "amended_chain_sha256": chain.chain_sha256,
        "source_commit": commit,
        "runtime_image_id": observed_image["image_id"],
        "activation_status": "ELIGIBLE_FOR_ONE LOCAL EXECUTION AFTER COMMITTING THIS RECEIPT SET",
        "execution_started": False,
        "maximum_model_invocations": 1,
        "maximum_packets": 1,
        "provider_calls": 0,
        "provider_spend_usd": "0.00",
        "boundary": BOUNDARY,
    }
    _write_create_only(ACTIVATION_RECEIPT, _pretty_json_bytes(activation_receipt))
    return AMENDMENT_PATH


@dataclass(frozen=True, slots=True)
class PreparedExecution:
    protocol: Mapping[str, Any]
    protocol_raw: bytes
    chain: PreregistrationChain
    request_raw: bytes
    model_manifest_raw: bytes
    expected_manifest: ExpectedRealWorkerManifest
    job: FleetJobSnapshot
    source_commit: str
    execution_commit: str
    source_to_execution_paths: tuple[str, ...]
    chain_artifact_bytes: Mapping[str, bytes]
    chain_artifact_files: Mapping[str, Path]
    runtime_image: Mapping[str, Any]


def _require_tracked(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise StageBSmokeError(f"execution artifact is not tracked: {relative}")


def _resolve_chain_artifact_bytes(chain: PreregistrationChain) -> dict[str, bytes]:
    observations: dict[tuple[str, int], list[bytes]] = {}
    for path in sorted(PACKAGE_ROOT.glob("*.json")):
        if path in {PREREG_PATH, AMENDMENT_PATH, EXECUTION_CLAIM_PATH}:
            continue
        raw = path.read_bytes()
        observations.setdefault((_sha_upper(raw), len(raw)), []).append(raw)
    resolved: dict[str, bytes] = {}
    deferred_weight_refs = 0
    for reference in chain.artifact_refs:
        if reference.artifact_id == WEIGHTS_ARTIFACT_ID:
            deferred_weight_refs += 1
            if (
                reference.sha256 != WEIGHTS_SHA256.upper()
                or reference.byte_length != WEIGHTS_BYTES
                or reference.media_type != "application/vnd.safetensors"
            ):
                raise StageBSmokeError("deferred weight reference differs from the frozen pin")
            continue
        matches = observations.get((reference.sha256, reference.byte_length), [])
        if len(matches) != 1 or not reference.verify_bytes(matches[0]):
            raise StageBSmokeError(
                f"chain artifact bytes are absent or ambiguous: {reference.artifact_id}"
            )
        resolved[reference.artifact_id] = matches[0]
    if deferred_weight_refs != 1:
        raise StageBSmokeError("chain must contain exactly one deferred Qwen weight artifact")
    return resolved


def _validate_source_manifest(value: Mapping[str, Any], source_commit: str) -> None:
    if (
        value.get("schema_version")
        != "cas_harness_gate5_stageb_final_source_manifest.v0.1"
        or value.get("source_commit") != source_commit
        or value.get("dirty_source_paths") is not False
    ):
        raise StageBSmokeError("final source manifest header drifted")
    rows = value.get("files")
    if type(rows) is not list or len(rows) != len(SOURCE_PATHS):
        raise StageBSmokeError("final source manifest inventory differs")
    observed: list[str] = []
    for row in rows:
        if type(row) is not dict or set(row) != {"path", "sha256", "byte_length"}:
            raise StageBSmokeError("final source manifest row is malformed")
        raw_path = row["path"]
        if raw_path in observed or raw_path not in SOURCE_PATHS:
            raise StageBSmokeError("final source manifest path differs")
        current = (REPO_ROOT / Path(*PurePosixPath(raw_path).parts)).read_bytes()
        if row["sha256"] != _sha_lower(current) or row["byte_length"] != len(current):
            raise StageBSmokeError(f"final executable source drifted: {raw_path}")
        committed = _run(["git", "show", f"{source_commit}:{raw_path}"]).stdout
        if committed != current:
            raise StageBSmokeError(f"final source no longer matches its commit: {raw_path}")
        observed.append(raw_path)
    if tuple(observed) != SOURCE_PATHS:
        raise StageBSmokeError("final source manifest order differs")


def _load_prepared_execution() -> PreparedExecution:
    if _git_status():
        raise StageBSmokeError("Stage B execution requires a completely clean worktree")
    if EXECUTION_CLAIM_PATH.exists():
        raise StageBSmokeError("the one Stage B execution attempt was already claimed")
    protocol, chain = _validate_base_package()
    required_paths = [
        PROTOCOL_PATH,
        PREREG_PATH,
        LEDGER_PATH,
        AMENDMENT_PATH,
        ACTIVATION_RECEIPT,
        *(path for _artifact_id, path, _media_type in ADDITIONAL_ARTIFACT_FILES),
    ]
    for path in required_paths:
        if not path.is_file() or path.is_symlink():
            raise StageBSmokeError(f"required execution binding is absent or unsafe: {path}")
        _require_tracked(path)

    amendment_raw = AMENDMENT_PATH.read_bytes()
    amendment = chain.append_amendment(amendment_raw)
    plan = _load_json(PACKAGE_ROOT / "execution_identity_amendment_plan.json")
    expected_ids = plan.get("required_additional_artifact_ids")
    if (
        amendment.change_class != "EXECUTION_IDENTITY_ADDITION"
        or type(expected_ids) is not list
        or [ref.artifact_id for ref in amendment.artifact_refs] != expected_ids
        or len(chain.amendments) != 1
        or chain.outcome_access is not None
    ):
        raise StageBSmokeError("execution identity amendment differs from the one-link plan")

    expected_file_map = {artifact_id: (path, media_type) for artifact_id, path, media_type in ADDITIONAL_ARTIFACT_FILES}
    for reference in amendment.artifact_refs:
        path, media_type = expected_file_map[reference.artifact_id]
        raw = path.read_bytes()
        if reference.media_type != media_type or not reference.verify_bytes(raw):
            raise StageBSmokeError(
                f"execution amendment artifact drifted: {reference.artifact_id}"
            )

    final_identity = _load_json(FINAL_CODE_IDENTITY)
    source_commit = final_identity.get("source_commit")
    if type(source_commit) is not str or GIT_SHA_RE.fullmatch(source_commit) is None:
        raise StageBSmokeError("final code identity has no exact source commit")
    execution_commit = _git_head()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, execution_commit],
        cwd=REPO_ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        raise StageBSmokeError("execution commit does not descend from the bound source")
    changed_raw = _run(
        ["git", "diff", "--name-only", source_commit, execution_commit]
    ).stdout.decode("utf-8", errors="strict")
    changed_paths = tuple(line for line in changed_raw.splitlines() if line)
    unpermitted = set(changed_paths).difference(GENERATED_BINDING_PATHS)
    if unpermitted:
        raise StageBSmokeError(
            f"source-to-execution diff contains unbound paths: {sorted(unpermitted)}"
        )
    _validate_source_manifest(_load_json(FINAL_SOURCE_MANIFEST), source_commit)

    image_receipt = _load_json(RUNTIME_IMAGE_RECEIPT)
    runtime_image = _image_identity(
        RUNTIME_IMAGE_REFERENCE,
        parent_reference=PARENT_IMAGE_REFERENCE,
    )
    if (
        image_receipt.get("source_commit") != source_commit
        or image_receipt.get("image") != runtime_image
        or runtime_image.get("parent_image_id") != PARENT_IMAGE_ID
        or runtime_image.get("image_id")
        != _load_json(ACTIVATION_RECEIPT).get("runtime_image_id")
    ):
        raise StageBSmokeError("runtime image no longer matches the activated identity")

    activation = _load_json(ACTIVATION_RECEIPT)
    if (
        activation.get("base_preregistration_sha256") != chain.base.sha256
        or activation.get("amendment_sha256") != amendment.sha256
        or activation.get("amended_chain_sha256") != chain.chain_sha256
        or activation.get("source_commit") != source_commit
        or activation.get("execution_started") is not False
        or activation.get("maximum_model_invocations") != 1
        or activation.get("maximum_packets") != 1
        or activation.get("provider_calls") != 0
        or activation.get("provider_spend_usd") != "0.00"
    ):
        raise StageBSmokeError("execution activation receipt drifted")

    request_raw = (PACKAGE_ROOT / "request.json").read_bytes()
    if _sha_upper(request_raw) != REQUEST_SHA256:
        raise StageBSmokeError("frozen Stage B request byte identity drifted")
    request = json.loads(request_raw)
    if (
        type(request) is not dict
        or request.get("model_id") != MODEL_ID
        or request.get("max_new_tokens") != 2
        or request.get("temperature") != 0.0
        or request.get("seed") != 1729
        or request.get("probes") != ["active_trace", "confidence_margin"]
        or request.get("method_config")
        != {
            "enabled_methods": ["foundation_probe"],
            "knobs": {
                "foundation_probe": {
                    "layer_range": [0, 23],
                    "top_k": 8,
                }
            },
        }
        or any(key in request for key in ("ablation_target", "billing_measurement_context"))
        or "<|im_" in str(request.get("prompt", ""))
    ):
        raise StageBSmokeError("Stage B request is not the exact no-intervention carrier")

    model_manifest_raw = (PACKAGE_ROOT / "model_artifact_manifest.json").read_bytes()
    model_manifest = json.loads(model_manifest_raw)
    if (
        model_manifest.get("model_id") != MODEL_ID
        or model_manifest.get("model_revision") != MODEL_REVISION
    ):
        raise StageBSmokeError("Stage B model artifact manifest identity drifted")
    artifacts = model_manifest.get("artifacts")
    if type(artifacts) is not list:
        raise StageBSmokeError("Stage B model artifact manifest is incomplete")
    weights = [row for row in artifacts if row.get("path") == WEIGHTS_FILENAME]
    if (
        len(weights) != 1
        or weights[0].get("sha256") != WEIGHTS_SHA256
        or weights[0].get("byte_count") != WEIGHTS_BYTES
    ):
        raise StageBSmokeError("Stage B weights identity drifted")

    expected_manifest = ExpectedRealWorkerManifest(
        model_id=MODEL_ID,
        revision=MODEL_REVISION,
        weights_filename=WEIGHTS_FILENAME,
        weights_sha256=WEIGHTS_SHA256,
        weights_bytes=WEIGHTS_BYTES,
        hook_contract_profile=QWEN_OBSERVATION_ONLY_HOOK_PROFILE,
    )
    validate_real_worker_dump_request(
        request_raw=request_raw,
        expected_manifest=expected_manifest,
    )
    job = FleetJobSnapshot(
        fleet_id="fleet-stageb-local",
        job_id=JOB_ID,
        audit_id="audit-stageb-qwen-joined-001",
        assigned_worker_id="worker-stageb-local-gpu-001",
        layer_start=0,
        layer_end=23,
        shard_id="shard-stageb-qwen-all-layers",
        assigned_methods=("foundation_probe",),
        expected_outputs=(OUTPUT_NAME,),
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        model_artifact_manifest_path=str(
            (PACKAGE_ROOT / "model_artifact_manifest.json").resolve()
        ),
        model_artifact_manifest_sha256=_sha_lower(model_manifest_raw),
        execution_mode="external_probe_command",
    )
    chain_artifact_bytes = _resolve_chain_artifact_bytes(chain)
    return PreparedExecution(
        protocol=protocol,
        protocol_raw=PROTOCOL_PATH.read_bytes(),
        chain=chain,
        request_raw=request_raw,
        model_manifest_raw=model_manifest_raw,
        expected_manifest=expected_manifest,
        job=job,
        source_commit=source_commit,
        execution_commit=execution_commit,
        source_to_execution_paths=changed_paths,
        chain_artifact_bytes=chain_artifact_bytes,
        chain_artifact_files={},
        runtime_image=runtime_image,
    )


METRIC_EVIDENCE_IDS = {
    "stageb-exactly-one-run": "stageb-qwen-metric-run-count-001",
    "stageb-exactly-one-model-invocation": "stageb-qwen-worker-response-001",
    "stageb-exactly-one-packet": "stageb-qwen-metric-packet-count-001",
    "stageb-zero-interventions": "stageb-qwen-metric-intervention-count-001",
    "stageb-zero-provider-calls": "stageb-qwen-metric-provider-call-count-001",
    "stageb-zero-provider-spend": "stageb-qwen-metric-provider-spend-usd-001",
    "stageb-output-bytes-reported": "stageb-qwen-metric-output-byte-count-001",
}

CONTROL_EVIDENCE_IDS = {
    "stageb-matched-taxonomy-not-performed": (
        "stageb-qwen-control-matched-taxonomy-invalid-001"
    ),
    "stageb-wrong-layer-not-performed": (
        "stageb-qwen-control-wrong-layer-invalid-001"
    ),
    "stageb-clean-null-not-performed": (
        "stageb-qwen-control-clean-null-invalid-001"
    ),
}

SPLIT_EVIDENCE_IDS = {
    "stageb-engineering-confirmatory": "stageb-qwen-confirmatory-accounting-001",
    "stageb-schema-held-out": "stageb-qwen-heldout-exclusion-001",
}


class StageBPacketPorts(joined._LocalPorts):
    """Local lifecycle ports plus one fail-closed Packet-v2 recorder."""

    def __init__(
        self,
        lifecycle: DurableProspectiveRunLifecycle,
        store: joined.LocalExactByteStore,
        chain: PreregistrationChain,
        tenant: str,
        subject: str,
        *,
        chain_artifact_bytes: Mapping[str, bytes],
        chain_artifact_files: Mapping[str, Path],
        ephemeral_secret: bytes,
    ) -> None:
        super().__init__(lifecycle, store, chain, tenant, subject)
        self.chain_artifact_bytes = dict(chain_artifact_bytes)
        self.chain_artifact_files = {
            artifact_id: Path(path) for artifact_id, path in chain_artifact_files.items()
        }
        if set(self.chain_artifact_files) != {WEIGHTS_ARTIFACT_ID}:
            raise StageBSmokeError("packet port requires exactly one file-backed weight artifact")
        weights_path = self.chain_artifact_files[WEIGHTS_ARTIFACT_ID]
        expected_path = WEIGHTS_ARCHIVE_PATH.resolve(strict=True)
        if weights_path.resolve(strict=True) != expected_path:
            raise StageBSmokeError("file-backed weight path differs from the external archive pin")
        stable_weight = _read_only_file_observation(weights_path)
        if (
            stable_weight["sha256"] != WEIGHTS_SHA256
            or stable_weight["byte_length"] != WEIGHTS_BYTES
        ):
            raise StageBSmokeError("file-backed packet weight differs from the frozen identity")
        if type(ephemeral_secret) is not bytes or len(ephemeral_secret) < 32:
            raise StageBSmokeError("pre-Packet secret scan requires exact secret bytes")
        self.ephemeral_secret = ephemeral_secret
        self.packet_build_result = None
        self.packet_binding: ArtifactBinding | None = None
        self.packet_recording_attempts = 0

    def _make_packet_evidence(
        self,
        artifact_id: str,
        value: Mapping[str, Any],
    ) -> RetainedArtifactInput:
        raw = _json_bytes(dict(value))
        return RetainedArtifactInput(
            artifact_id=artifact_id,
            raw_bytes=raw,
            media_type="application/json",
        )

    def _prepacket_secret_scan(self) -> dict[str, Any]:
        paths = sorted(path for path in self.store.root.rglob("*") if path.is_file())
        byte_count = 0
        secret_found = False
        for path in paths:
            _sha256, observed_bytes, observed_secret = _stream_file_observation(
                path,
                secret=self.ephemeral_secret,
            )
            byte_count += observed_bytes
            secret_found = secret_found or observed_secret
        result = {
            "status": "FAIL" if secret_found else "PASS",
            "ephemeral_worker_token_found": secret_found,
            "scanned_file_count": len(paths),
            "scanned_byte_count": byte_count,
            "cutoff": "AFTER TERMINAL OUTCOME ACCESS / BEFORE PACKET CONSTRUCTION",
            "scope": "EXACT RUN-STORE FILES PRESENT AT PACKET CONSTRUCTION TIME",
        }
        if secret_found:
            raise StageBSmokeError("pre-Packet secret scan found the ephemeral token")
        return result

    async def reconcile(
        self,
        *,
        authorization: Any,
        job_snapshot: FleetJobSnapshot,
    ) -> ReconciliationAcceptance:
        del authorization, job_snapshot
        result = self.lifecycle.reconcile(tenant_id=self.tenant)
        raw = _json_bytes(asdict(result))
        self.store.put_exact(
            "reconciliation.json",
            raw,
            artifact_id="stageb-qwen-reconciliation-001",
            media_type="application/json",
        )
        if not result.structurally_valid:
            raise StageBSmokeError("local Stage B lifecycle reconciliation failed")
        snapshot = self.lifecycle.get_lifecycle(
            tenant_id=self.tenant,
            subject_id=self.subject,
        )
        if snapshot is None:
            raise StageBSmokeError("Stage B reconciliation lost the lifecycle")
        if snapshot.state != "PACKET_RECORDED":
            return ReconciliationAcceptance(
                run_id=snapshot.run_id,
                lifecycle_state=snapshot.state,
            )

        packet_events = [
            event
            for event in self.lifecycle.list_events(
                tenant_id=self.tenant,
                subject_id=self.subject,
            )
            if event.get("event_type") == "PACKET_RECORDED"
        ]
        if len(packet_events) != 1:
            raise StageBSmokeError("Stage B reconciliation found no unique Packet event")
        details = packet_events[0].get("details")
        artifact = details.get("packet_artifact") if isinstance(details, Mapping) else None
        if not isinstance(artifact, Mapping):
            raise StageBSmokeError("Stage B Packet event has no exact artifact binding")
        packet_raw = (self.store.root / "evidence_packet.v2.json").read_bytes()
        packet_value = json.loads(packet_raw)
        if (
            type(packet_value) is not dict
            or packet_value.get("packet_id") != PACKET_ID
            or artifact.get("artifact_id") != PACKET_ARTIFACT_ID
            or artifact.get("media_type") != "application/json"
            or artifact.get("sha256") != _sha_lower(packet_raw)
            or artifact.get("byte_length") != len(packet_raw)
        ):
            raise StageBSmokeError("Stage B reconciled Packet identity differs")
        return ReconciliationAcceptance(
            run_id=snapshot.run_id,
            lifecycle_state=snapshot.state,
            packet_id=PACKET_ID,
            packet_artifact_id=PACKET_ARTIFACT_ID,
            packet_sha256=_sha_upper(packet_raw),
            packet_byte_length=len(packet_raw),
            packet_media_type="application/json",
        )

    async def record_packet(
        self,
        *,
        authorization,
        job_snapshot,
        terminal_receipt,
        output_name,
        output_artifact,
        output_body,
    ) -> PacketRecordingAcceptance:
        self.packet_recording_attempts += 1
        if self.packet_build_result is not None or self.packet_binding is not None:
            raise StageBSmokeError("a second Stage B Packet is forbidden")
        if (
            output_name != OUTPUT_NAME
            or output_artifact.artifact_id != OUTPUT_ARTIFACT_ID
            or output_artifact.media_type != "application/json"
            or not output_artifact.verify_bytes(output_body)
            or terminal_receipt.terminal_status != "COMPLETED"
            or self.chain.outcome_access is None
            or job_snapshot.job_id != JOB_ID
        ):
            raise StageBSmokeError("packet continuation inputs differ from the frozen run")

        output_observation = _output_observation(output_body)
        prior_reporting_reservation = (
            self.lifecycle.get_reporting_disposition_reservation(
                tenant_id=self.tenant,
                subject_id=self.subject,
            )
        )
        falsifier_observed = {
            "identity_drift": False,
            "prompt_drift": False,
            "intervention_attempts": output_observation["intervention_event_count"],
            "provider_calls": 0,
            "provider_spend_usd": "0.00",
            "run_attempts": 1,
            "model_invocations": 1,
            "packet_recording_calls": self.packet_recording_attempts,
            "packet_carriers_constructed": 1,
            "prior_reporting_reservation_present": (
                prior_reporting_reservation is not None
            ),
            "second_packet_reservation_or_creation": False,
            "missing_terminal_completion": (
                terminal_receipt.terminal_status != "COMPLETED"
            ),
            "premature_outcome_access": self.chain.outcome_access is None,
            "claim_elevation": False,
        }
        falsifier_triggered = bool(
            falsifier_observed["identity_drift"]
            or falsifier_observed["prompt_drift"]
            or falsifier_observed["intervention_attempts"] != 0
            or falsifier_observed["provider_calls"] != 0
            or falsifier_observed["provider_spend_usd"] != "0.00"
            or falsifier_observed["run_attempts"] != 1
            or falsifier_observed["model_invocations"] != 1
            or falsifier_observed["packet_recording_calls"] != 1
            or falsifier_observed["packet_carriers_constructed"] != 1
            or falsifier_observed["prior_reporting_reservation_present"]
            or falsifier_observed["second_packet_reservation_or_creation"]
            or falsifier_observed["missing_terminal_completion"]
            or falsifier_observed["premature_outcome_access"]
            or falsifier_observed["claim_elevation"]
        )
        if falsifier_triggered:
            raise StageBSmokeError("Stage B bounded-path falsifier triggered")

        retained: list[RetainedArtifactInput | RetainedFileArtifactInput] = []
        generated_evidence: list[RetainedArtifactInput] = []
        for reference in self.chain.artifact_refs:
            if reference.artifact_id == terminal_receipt.receipt_id:
                continue
            file_path = self.chain_artifact_files.get(reference.artifact_id)
            if file_path is not None:
                retained.append(
                    RetainedFileArtifactInput.from_reference(reference, file_path)
                )
                continue
            raw = self.chain_artifact_bytes.get(reference.artifact_id)
            if raw is None:
                raise StageBSmokeError(
                    f"packet cannot resolve chain artifact {reference.artifact_id}"
                )
            retained.append(RetainedArtifactInput.from_reference(reference, raw))
        retained.append(
            RetainedArtifactInput.from_reference(output_artifact, output_body)
        )

        metric_values = {
            "stageb-exactly-one-run": "1",
            "stageb-exactly-one-model-invocation": "1",
            "stageb-exactly-one-packet": "1",
            "stageb-zero-interventions": "0",
            "stageb-zero-provider-calls": "0",
            "stageb-zero-provider-spend": "0.00",
            "stageb-output-bytes-reported": str(len(output_body)),
        }
        metrics: list[MetricResultInput] = []
        for threshold in self.chain.base.payload["thresholds"]:
            threshold_id = threshold["threshold_id"]
            artifact_id = METRIC_EVIDENCE_IDS.get(threshold_id)
            value = metric_values.get(threshold_id)
            if artifact_id is None or value is None:
                raise StageBSmokeError("unrecognized Stage B threshold")
            evidence = self._make_packet_evidence(
                artifact_id,
                {
                    "schema_version": "cas_harness_gate5_stageb_metric_evidence.v0.1",
                    "threshold_id": threshold_id,
                    "measure_id": threshold["measure_id"],
                    "value": value,
                    "unit": threshold["unit"],
                    "output_sha256": output_artifact.sha256,
                    "output_byte_length": output_artifact.byte_length,
                    "observation_scope": (
                        "ONE LOCAL JOINED ENGINEERING ATTEMPT THROUGH TERMINAL OUTCOME "
                        "ACCESS AND ONE IN-MEMORY PACKET CARRIER"
                    ),
                    "authority": "LOCAL PROCESS OBSERVATION / NOT AUTHENTICATED",
                },
            )
            retained.append(evidence)
            generated_evidence.append(evidence)
            metrics.append(
                MetricResultInput(
                    threshold_id=threshold_id,
                    value=value,
                    evidence_artifact_id=artifact_id,
                )
            )

        controls: list[ControlResultInput] = []
        for control in self.chain.base.payload["controls"]:
            control_id = control["control_id"]
            artifact_id = CONTROL_EVIDENCE_IDS.get(control_id)
            if artifact_id is None:
                raise StageBSmokeError("unrecognized Stage B control")
            evidence = self._make_packet_evidence(
                artifact_id,
                {
                    "schema_version": "cas_harness_gate5_stageb_control_evidence.v0.1",
                    "control_id": control_id,
                    "kind": control["kind"],
                    "outcome": "INVALID",
                    "performed": False,
                    "reason": (
                        "The frozen Stage B engineering smoke authorizes no scientific "
                        "intervention, adversarial comparison, wrong-layer comparator, or "
                        "paired clean-null study."
                    ),
                    "claim_effect": "REPORTED_CRITERIA_NOT_MET / INELIGIBLE",
                },
            )
            retained.append(evidence)
            generated_evidence.append(evidence)
            controls.append(
                ControlResultInput(
                    control_id=control_id,
                    outcome="INVALID",
                    evidence_artifact_id=artifact_id,
                )
            )

        falsifier_id = "stageb-bounded-path-violation"
        falsifier_artifact_id = "stageb-qwen-falsifier-report-001"
        falsifier_evidence = self._make_packet_evidence(
            falsifier_artifact_id,
            {
                "schema_version": "cas_harness_gate5_stageb_falsifier_evidence.v0.1",
                "falsifier_id": falsifier_id,
                "triggered": falsifier_triggered,
                "evaluation_cutoff": "PACKET_CONSTRUCTION_AFTER_TERMINAL_OUTCOME_ACCESS",
                "observed": falsifier_observed,
                "post_packet_reconciliation": (
                    "OUTSIDE THIS FALSIFIER CUTOFF / RETAINED IN THE RUNTIME RECEIPT"
                ),
            },
        )
        retained.append(falsifier_evidence)
        generated_evidence.append(falsifier_evidence)

        split_results: list[SplitResultInput] = []
        for split in self.chain.base.payload["splits"]:
            split_id = split["split_id"]
            artifact_id = SPLIT_EVIDENCE_IDS.get(split_id)
            if artifact_id is None:
                raise StageBSmokeError("unrecognized Stage B split")
            if split_id == "stageb-engineering-confirmatory":
                accounting = {
                    "groups": 1,
                    "enrolled_rows": 1,
                    "analyzed_rows": 1,
                    "missing_rows": 0,
                    "excluded_rows": 0,
                    "status": "ONE ENGINEERING CARRIER ACCOUNTED",
                }
            else:
                accounting = {
                    "groups": 0,
                    "enrolled_rows": 1,
                    "analyzed_rows": 0,
                    "missing_rows": 0,
                    "excluded_rows": 1,
                    "status": "HELD-OUT ROW EXCLUDED / REPLICATION NOT AUTHORIZED",
                }
            evidence = self._make_packet_evidence(
                artifact_id,
                {
                    "schema_version": "cas_harness_gate5_stageb_split_evidence.v0.1",
                    "split_id": split_id,
                    **accounting,
                },
            )
            retained.append(evidence)
            generated_evidence.append(evidence)
            split_results.append(
                SplitResultInput(
                    split_id=split_id,
                    groups=accounting["groups"],
                    enrolled_rows=accounting["enrolled_rows"],
                    analyzed_rows=accounting["analyzed_rows"],
                    missing_rows=accounting["missing_rows"],
                    excluded_rows=accounting["excluded_rows"],
                    evidence_artifact_id=artifact_id,
                )
            )

        uncertainty_id = "stageb-qwen-uncertainty-report-001"
        uncertainty = self._make_packet_evidence(
            uncertainty_id,
            {
                "schema_version": "cas_harness_gate5_stageb_uncertainty_report.v0.1",
                "method": "EXACT MECHANICS ACCOUNTING ONLY",
                "statistical_inference": "NOT PERFORMED",
                "uncertainty_interval": "NOT APPLICABLE",
                "limitations": [
                    "One local model invocation.",
                    "No scientific controls, intervention, audit, or replication.",
                    "No authenticated execution or trusted time authority.",
                ],
            },
        )
        retained.append(uncertainty)
        generated_evidence.append(uncertainty)

        prepacket_secret_scan = self._prepacket_secret_scan()
        summary_id = "stageb-qwen-result-summary-001"
        summary = self._make_packet_evidence(
            summary_id,
            {
                "schema_version": "cas_harness_gate5_stageb_result_summary.v0.1",
                "engineering_observation": (
                    "One exact Qwen joined invocation reached terminal outcome access and "
                    "produced one Packet-v2 carrier for create-only recording."
                ),
                "output_sha256": output_artifact.sha256,
                "output_byte_length": output_artifact.byte_length,
                "criteria": "REPORTED_CRITERIA_NOT_MET",
                "scientific_eligibility": "INELIGIBLE",
                "prepacket_secret_scan": prepacket_secret_scan,
                "no_claims": [
                    "No prompt-injection detection claim.",
                    "No steering or causal intervention claim.",
                    "No safety, product, licensing, disclosure, or canon claim.",
                ],
                "post_packet_reconciliation": "PENDING AT PACKET CONSTRUCTION",
            },
        )
        retained.append(summary)
        generated_evidence.append(summary)

        created_at = _iso()
        inputs = EvidencePacketBuildInputs(
            packet_id=PACKET_ID,
            created_at=created_at,
            execution_manifest_id="stageb-qwen-execution-manifest-001",
            retained_artifacts=tuple(retained),
            metrics=tuple(metrics),
            controls=tuple(controls),
            falsifiers=(
                FalsifierResultInput(
                    falsifier_id=falsifier_id,
                    triggered=falsifier_triggered,
                    evidence_artifact_id=falsifier_artifact_id,
                ),
            ),
            split_results=tuple(split_results),
            uncertainty_artifact_id=uncertainty_id,
            result_summary_artifact_id=summary_id,
            limitations=(
                "Final lifecycle reconciliation follows create-only Packet recording and is retained separately.",
                "The generated text is report-only and is not a semantic pass criterion.",
            ),
        )
        built = build_evidence_packet(
            chain=self.chain,
            authorization=authorization,
            terminal_receipt=terminal_receipt,
            inputs=inputs,
        )
        assessment = built.assessment
        if not (
            assessment.structural_completeness == "COMPLETE"
            and assessment.preregistered_criteria == "REPORTED_CRITERIA_NOT_MET"
            and assessment.scientific_eligibility == "INELIGIBLE"
            and assessment.authenticated_execution == "UNAVAILABLE"
            and assessment.admission_ring == 4
            and assessment.product_claim_status == "NOT LICENSED"
            and assessment.disclosure_status == "HELD"
            and assessment.public_release_allowed is False
            and assessment.product_route_allowed is False
        ):
            raise StageBSmokeError("built Packet exceeded or missed the frozen Ring-4 ceiling")

        packet_raw = built.packet.raw_bytes
        planned = ArtifactBinding.from_bytes(
            artifact_id=PACKET_ARTIFACT_ID,
            media_type="application/json",
            body=packet_raw,
        )
        recorded_at = datetime.now(UTC)
        request_sha = _sha_lower(
            _json_bytes(
                {
                    "packet_id": built.packet.packet_id,
                    "packet_sha256": built.packet.sha256,
                    "chain_sha256": self.chain.chain_sha256,
                }
            )
        )
        dependency_sha = _sha_lower(
            _json_bytes(
                {
                    "authorization_sha256": authorization.sha256,
                    "terminal_receipt_sha256": terminal_receipt.sha256,
                    "outcome_access_sha256": self.chain.outcome_access.sha256,
                    "assessment": asdict(assessment),
                }
            )
        )
        reservation = self.lifecycle.reserve_reporting_disposition(
            tenant_id=self.tenant,
            subject_id=self.subject,
            operation_id="packet-stageb-001",
            disposition="PACKET",
            reason_code=None,
            request_sha256=request_sha,
            dependency_binding_sha256=dependency_sha,
            planned_artifact=planned,
            observed_at=recorded_at,
        )
        registry_paths: dict[str, str] = {
            reference.artifact_id: f"chain_artifacts/{reference.artifact_id}.bin"
            for reference in self.chain.artifact_refs
            if reference.artifact_id
            not in {terminal_receipt.receipt_id, WEIGHTS_ARTIFACT_ID}
        }
        registry_external_paths = dict(self.chain_artifact_files)
        registry_paths[output_artifact.artifact_id] = "output.json"
        for evidence in generated_evidence:
            relative_path = f"packet_evidence/{evidence.artifact_id}.json"
            evidence_binding = self.store.put_exact(
                relative_path,
                evidence.raw_bytes,
                artifact_id=evidence.artifact_id,
                media_type=evidence.media_type,
            )
            if (
                evidence_binding.sha256.upper() != evidence.artifact_ref.sha256
                or evidence_binding.byte_length != evidence.artifact_ref.byte_length
            ):
                raise StageBSmokeError("packet evidence persistence identity differs")
            registry_paths[evidence.artifact_id] = relative_path
        self.store.put_exact(
            "evidence_packet_execution_manifest.json",
            built.execution_manifest.raw_bytes,
            artifact_id=built.execution_manifest.artifact_id,
            media_type=built.execution_manifest.media_type,
        )
        registry_paths[built.execution_manifest.artifact_id] = (
            "evidence_packet_execution_manifest.json"
        )
        registry_paths[authorization.authorization_id] = "authorization.json"
        registry_paths[terminal_receipt.receipt_id] = "terminal_receipt.json"
        expected_registry_refs: dict[str, ArtifactRef] = {}
        for reference in (
            *self.chain.artifact_refs,
            *built.packet.artifact_refs,
            authorization.artifact_ref,
            terminal_receipt.artifact_ref,
            built.execution_manifest.artifact_ref,
        ):
            prior = expected_registry_refs.get(reference.artifact_id)
            if prior is not None and prior != reference:
                raise StageBSmokeError(
                    "packet registry contains conflicting artifact identities"
                )
            expected_registry_refs[reference.artifact_id] = reference
        if set(expected_registry_refs) != set(built.artifact_registry.artifact_ids):
            raise StageBSmokeError(
                "packet registry identifiers differ from the complete reference inventory"
            )

        registry_index = []
        retained_registry_paths: dict[str, tuple[Path, bool]] = {}
        for artifact_id in built.artifact_registry.artifact_ids:
            external_path = registry_external_paths.get(artifact_id)
            if external_path is not None:
                retained_path = external_path
                path = external_path.as_posix()
                storage_scope = "EXTERNAL_CONTENT_ADDRESSED_ARCHIVE"
                externally_retained = True
                stable_external = _read_only_file_observation(retained_path)
                retained_sha256 = stable_external["sha256"]
                retained_bytes = stable_external["byte_length"]
            else:
                path = registry_paths.get(artifact_id)
                if path is None:
                    raise StageBSmokeError(
                        f"packet registry artifact has no retained path: {artifact_id}"
                    )
                retained_path = self.store.root / Path(*PurePosixPath(path).parts)
                storage_scope = "LOCAL_RUN_STORE"
                externally_retained = False
                retained_sha256, retained_bytes, _found = _stream_file_observation(
                    retained_path
                )
            expected_reference = expected_registry_refs[artifact_id]
            if (
                retained_sha256.upper() != expected_reference.sha256
                or retained_bytes != expected_reference.byte_length
            ):
                raise StageBSmokeError(
                    f"retained packet artifact identity differs: {artifact_id}"
                )
            retained_registry_paths[artifact_id] = (
                retained_path,
                externally_retained,
            )
            registry_index.append(
                {
                    "artifact_id": artifact_id,
                    "path": path,
                    "sha256": retained_sha256.upper(),
                    "byte_length": retained_bytes,
                    "storage_scope": storage_scope,
                }
            )
        self.store.put_exact(
            "evidence_packet_registry_index.json",
            _json_bytes(registry_index),
            artifact_id="stageb-qwen-evidence-packet-registry-index-001",
            media_type="application/json",
        )
        self.store.put_exact(
            "evidence_packet_assessment.json",
            _json_bytes(asdict(assessment)),
            artifact_id="stageb-qwen-evidence-packet-assessment-001",
            media_type="application/json",
        )
        binding = self.store.put_exact(
            "evidence_packet.v2.json",
            packet_raw,
            artifact_id=PACKET_ARTIFACT_ID,
            media_type="application/json",
        )
        # The builder assessment is point-in-time. Revalidate every retained
        # source after Packet persistence and immediately before the lifecycle
        # mutation so a post-build mutation cannot be recorded as a success.
        for artifact_id in sorted(expected_registry_refs):
            expected_reference = expected_registry_refs[artifact_id]
            retained_path, externally_retained = retained_registry_paths[artifact_id]
            if externally_retained:
                retained_valid = built.artifact_registry.verify(expected_reference)
            else:
                final_sha256, final_bytes, _found = _stream_file_observation(
                    retained_path
                )
                retained_valid = (
                    final_sha256.upper() == expected_reference.sha256
                    and final_bytes == expected_reference.byte_length
                )
            if not retained_valid:
                raise StageBSmokeError(
                    f"final retained packet artifact verification failed: {artifact_id}"
                )
        mutation = self.lifecycle.record_packet(
            tenant_id=self.tenant,
            subject_id=self.subject,
            operation_id="packet-stageb-001",
            packet_artifact=binding,
            recorded_at=recorded_at,
            reporting_reservation_id=reservation.reservation_id,
        )
        if mutation.idempotent_replay:
            raise StageBSmokeError("Stage B Packet recording replayed")
        self.packet_build_result = built
        self.packet_binding = binding
        acceptance = PacketRecordingAcceptance(
            packet_id=built.packet.packet_id,
            packet_sha256=built.packet.sha256,
            packet_byte_length=built.packet.byte_length,
            packet_media_type="application/json",
            packet_artifact_id=PACKET_ARTIFACT_ID,
        )
        return acceptance


async def _run_joined_packet_kernel(
    prepared: PreparedExecution,
    run_store: joined.LocalExactByteStore,
    sqlite_path: Path,
    live_dump: Any,
    *,
    ephemeral_secret: bytes,
) -> tuple[JoinedGate5RunResult, int, StageBPacketPorts]:
    run_store.put_exact(
        "protocol.json",
        prepared.protocol_raw,
        artifact_id="stageb-run-protocol-copy",
        media_type="application/json",
    )
    run_store.put_exact(
        "request.json",
        prepared.request_raw,
        artifact_id="stageb-qwen-request-001",
        media_type="application/json",
    )
    run_store.put_exact(
        "model_artifact_manifest.json",
        prepared.model_manifest_raw,
        artifact_id="stageb-run-model-manifest-copy",
        media_type="application/json",
    )
    run_store.put_exact(
        "preregistration.json",
        prepared.chain.base.raw_bytes,
        artifact_id="stageb-qwen-preregistration-copy-001",
        media_type="application/json",
    )
    run_store.put_exact(
        "claim_ledger.noncanonical.json",
        LEDGER_PATH.read_bytes(),
        artifact_id="stageb-qwen-claim-ledger-copy-001",
        media_type="application/json",
    )
    run_store.put_exact(
        "execution_identity_amendment.json",
        AMENDMENT_PATH.read_bytes(),
        artifact_id="stageb-run-execution-amendment-copy",
        media_type="application/json",
    )
    chain_ref_by_id = {
        reference.artifact_id: reference for reference in prepared.chain.artifact_refs
    }
    for artifact_id, raw in sorted(prepared.chain_artifact_bytes.items()):
        reference = chain_ref_by_id[artifact_id]
        run_store.put_exact(
            f"chain_artifacts/{artifact_id}.bin",
            raw,
            artifact_id=artifact_id,
            media_type=reference.media_type,
        )

    state = SqliteStateStore(sqlite_path)
    lifecycle = DurableProspectiveRunLifecycle(state)
    tenant = "tenant-local-stageb"
    subject = prepared.job.job_id
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=30)
    holder: dict[str, Any] = {}
    request_sha = _sha_lower(
        _json_bytes(
            {
                "chain_sha256": prepared.chain.chain_sha256,
                "subject_id": subject,
                "issued_at": _iso(issued_at),
                "expires_at": _iso(expires_at),
                "execution_mapping": prepared.job.execution_mapping(),
            }
        )
    )

    def build_authorization(nonce_b64: str) -> ArtifactBinding:
        nonce = base64.urlsafe_b64decode(nonce_b64 + "=")
        authorization = build_worker_authorization(
            chain=prepared.chain,
            authorization_id=subject,
            issued_at=_iso(issued_at),
            expires_at=_iso(expires_at),
            execution_mapping=prepared.job.execution_mapping(),
            run_nonce=nonce,
        )
        holder["authorization"] = authorization
        return run_store.put_exact(
            "authorization.json",
            authorization.raw_bytes,
            artifact_id=authorization.authorization_id,
            media_type="application/vnd.cas-harness.worker-authorization+json",
        )

    issuance = lifecycle.issue_with_builder(
        tenant_id=tenant,
        subject_id=subject,
        authorized_at=issued_at,
        expires_at=expires_at,
        authorization_request_sha256=request_sha,
        authorization_builder=build_authorization,
    )
    if not issuance.issued_now or issuance.run_nonce is None:
        state.close()
        raise StageBSmokeError("Stage B authorization issuance was not fresh")
    authorization = holder["authorization"]
    ports = StageBPacketPorts(
        lifecycle,
        run_store,
        prepared.chain,
        tenant,
        subject,
        chain_artifact_bytes=prepared.chain_artifact_bytes,
        chain_artifact_files=prepared.chain_artifact_files,
        ephemeral_secret=ephemeral_secret,
    )
    retaining = joined._RetainingLiveDump(live_dump, run_store)
    plan = JoinedGate5RunPlan(
        chain=prepared.chain,
        authorization=authorization,
        job_snapshot=prepared.job,
        live_request_raw=prepared.request_raw,
        expected_manifest=prepared.expected_manifest,
        model_artifact_manifest_raw=prepared.model_manifest_raw,
        output_name=OUTPUT_NAME,
        output_artifact_id=OUTPUT_ARTIFACT_ID,
        output_media_type="application/json",
        terminal_receipt_id=TERMINAL_RECEIPT_ID,
        invocation_id=INVOCATION_ID,
        expected_packet_id=PACKET_ID,
        expected_packet_artifact_id=PACKET_ARTIFACT_ID,
    )
    executor = JoinedGate5Executor(
        worker_protocol=ports,
        live_dump=retaining,
        clock=ports,
        controller=ports,
        terminal_disposition=ports,
        packet_reporting=ports,
    )
    try:
        result = await executor.execute(plan)
        run_store.put_exact(
            "joined_result.json",
            _json_bytes(asdict(result)),
            artifact_id="stageb-joined-result-001",
            media_type="application/json",
        )
        return result, retaining.invocations, ports
    finally:
        state.close()


def _qwen_health(container: str, *, timeout_seconds: float = 300.0) -> bytes:
    deadline = datetime.now(UTC) + timedelta(seconds=timeout_seconds)
    last_output = b""
    while datetime.now(UTC) < deadline:
        completed = subprocess.run(
            ["docker", "exec", container, "python", "-c", joined._DOCKER_EXEC_HEALTH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
            check=False,
        )
        last_output = completed.stdout or completed.stderr
        if completed.returncode == 0 and 1 <= len(completed.stdout) <= 2_000_000:
            try:
                value = json.loads(completed.stdout)
            except json.JSONDecodeError:
                value = None
            runtime = value.get("runtime_execution", {}) if type(value) is dict else {}
            if (
                type(value) is dict
                and value.get("verdict")
                == "REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS_LOADED"
                and value.get("is_real_model") is True
                and value.get("model_loaded") is True
                and value.get("manifest_is_real_model") is True
                and value.get("model_id") == MODEL_ID
                and value.get("requested_revision") == MODEL_REVISION
                and value.get("resolved_revision") == MODEL_REVISION
                and value.get("revision_verified") is True
                and value.get("weights_filename") == WEIGHTS_FILENAME
                and value.get("weights_sha256") == WEIGHTS_SHA256
                and value.get("weights_bytes") == WEIGHTS_BYTES
                and value.get("weights_hash_verified") is True
                and runtime.get("device") == "cuda"
                and runtime.get("dtype") == "torch.bfloat16"
                and runtime.get("torch_native_jit_disabled") is True
            ):
                return completed.stdout
        import time

        time.sleep(0.25)
    detail = last_output[-1000:].decode("utf-8", errors="replace")
    raise StageBSmokeError(f"exact offline Qwen CUDA health did not become ready: {detail}")


def _output_observation(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw)
    events = value.get("events") if type(value) is dict else None
    if type(events) is not list or not events:
        raise StageBSmokeError("joined worker output has no event list")
    manifest_events = [event for event in events if event.get("type") == "manifest"]
    complete_events = [event for event in events if event.get("type") == "complete"]
    token_events = [event for event in events if event.get("type") == "token"]
    forbidden_events = [
        event
        for event in events
        if event.get("type") in {"ablation_effect", "ablation_control"}
        or event.get("eraser_intervention_result") not in (None, {})
    ]
    if (
        len(manifest_events) != 1
        or len(complete_events) != 1
        or not 1 <= len(token_events) <= 2
        or forbidden_events
    ):
        raise StageBSmokeError("joined worker output violates the non-intervention event contract")
    manifest = manifest_events[0].get("manifest", {})
    if (
        manifest.get("model_id") != MODEL_ID
        or manifest.get("resolved_revision") != MODEL_REVISION
        or manifest.get("weights_sha256") != WEIGHTS_SHA256
        or manifest.get("weights_bytes") != WEIGHTS_BYTES
        or manifest.get("is_real_model") is not True
    ):
        raise StageBSmokeError("joined worker output manifest differs from the Qwen pin")
    if not any(event.get("top_activated_neurons") for event in token_events):
        raise StageBSmokeError("Stage B output contains no captured activation summary")
    generated_text = "".join(str(event.get("token", "")) for event in token_events)
    return {
        "event_count": len(events),
        "token_event_count": len(token_events),
        "generated_text": generated_text,
        "generated_text_role": "REPORT_ONLY / NOT A SEMANTIC PASS CRITERION",
        "activation_summary_present": True,
        "intervention_event_count": 0,
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
    }


def _joined_success(
    result: Any,
    *,
    invocations: int,
    ports: StageBPacketPorts,
    run_root: Path,
) -> tuple[bool, dict[str, Any] | None]:
    if not (
        type(result) is JoinedGate5RunResult
        and result.status == SUCCESS_PACKET_RECORDED
        and result.failure_phase is None
        and result.error_code is None
        and result.model_invocation_count == invocations == 1
        and result.packet_status == "CREATED"
        and result.packet_id == PACKET_ID
        and result.packet_artifact_id == PACKET_ARTIFACT_ID
        and result.packet_media_type == "application/json"
        and result.reconciled is True
        and result.gate_status == "OPEN"
        and result.scientific_status == "NOT_ESTABLISHED"
        and result.product_status == "RESEARCH_ONLY"
        and result.license_status == "NOT LICENSED"
        and result.disclosure_status == "HELD"
        and ports.packet_build_result is not None
        and ports.packet_binding is not None
    ):
        return False, None
    packet = ports.packet_build_result.packet
    if (
        packet.packet_id != PACKET_ID
        or result.packet_sha256 != packet.sha256
        or result.packet_byte_length != packet.byte_length
        or ports.packet_binding.sha256.upper() != packet.sha256
        or ports.packet_binding.byte_length != packet.byte_length
        or (run_root / "evidence_packet.v2.json").read_bytes() != packet.raw_bytes
    ):
        return False, None
    output_raw = (run_root / "output.json").read_bytes()
    if (
        result.output_artifact_sha256 != _sha_upper(output_raw)
        or result.response_sha256 != _sha_upper(output_raw)
        or result.response_byte_length != len(output_raw)
    ):
        return False, None
    return True, _output_observation(output_raw)


def _execute_stageb_unprotected() -> Path:
    prepared = _load_prepared_execution()
    run_id = (
        "gate5-stageb-qwen-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + secrets.token_hex(6)
    )
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    run_store = joined.LocalExactByteStore(RUNS_ROOT / run_id)
    weights_path, weight_materialization = _materialize_weight_artifact_from_image()
    if weights_path.resolve(strict=True).is_relative_to(run_store.root):
        raise StageBSmokeError("large weight artifact must remain outside PACKAGE_ROOT runs")
    run_store.put_exact(
        "weight_artifact_pointer.json",
        _json_bytes(weight_materialization),
        artifact_id="stageb-qwen-weight-artifact-pointer-001",
        media_type="application/json",
    )
    prepared = replace(
        prepared,
        chain_artifact_files={WEIGHTS_ARTIFACT_ID: weights_path},
    )
    claim_raw = _json_bytes(
        {
            "schema_version": "cas_harness_gate5_stageb_execution_claim.v0.1",
            "run_id": run_id,
            "claimed_at": _iso(),
            "protocol_sha256": _sha_upper(prepared.protocol_raw),
            "preregistration_chain_sha256": prepared.chain.chain_sha256,
            "source_commit": prepared.source_commit,
            "clean_execution_commit": prepared.execution_commit,
            "source_to_execution_changed_paths": list(
                prepared.source_to_execution_paths
            ),
            "maximum_run_attempts": 1,
            "maximum_model_invocations": 1,
            "maximum_packets": 1,
            "automatic_retry": False,
            "provider_calls": 0,
            "provider_spend_usd": "0.00",
            "preclaim_weight_artifact": {
                "artifact_id": WEIGHTS_ARTIFACT_ID,
                "sha256": WEIGHTS_SHA256.upper(),
                "byte_length": WEIGHTS_BYTES,
                "path": weights_path.as_posix(),
                "storage_scope": "EXTERNAL_CONTENT_ADDRESSED_ARCHIVE",
            },
            "boundary": BOUNDARY,
        }
    )
    _write_create_only(EXECUTION_CLAIM_PATH, claim_raw)

    token = secrets.token_urlsafe(48)
    container = "cas-g5-stageb-qwen-" + secrets.token_hex(5)
    image_id = str(prepared.runtime_image["image_id"])
    invocation_count = 0
    result: JoinedGate5RunResult | None = None
    ports: StageBPacketPorts | None = None
    output_observation: dict[str, Any] | None = None
    health_raw: bytes | None = None
    error: str | None = None
    cleanup: dict[str, bool] = {}
    secret_found = False

    with tempfile.TemporaryDirectory(prefix="cas-g5-stageb-qwen-") as temp:
        env_path = Path(temp) / "worker.env"
        descriptor = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(f"ATLAS_LIVE_WORKER_TOKEN={token}\n".encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

        live = joined.DockerExecLoopbackLiveDump(container, timeout_seconds=240.0)
        try:
            _run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--name",
                    container,
                    "--network",
                    "none",
                    "--gpus",
                    "all",
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
                    "no-new-privileges:true",
                    "--user",
                    "10001:10001",
                    "--env-file",
                    str(env_path),
                    "--env",
                    "PORT=8080",
                    "--env",
                    f"ATLAS_WORKER_MODEL={MODEL_BINDING_KEY}",
                    image_id,
                ],
                timeout=120,
            )
            inspect_raw = _run(["docker", "inspect", container], timeout=30).stdout
            inspect_value = joined._redact(json.loads(inspect_raw), token)
            if (
                type(inspect_value) is not list
                or len(inspect_value) != 1
                or not joined._container_has_exact_none_network(inspect_value[0])
                or inspect_value[0].get("Image") != image_id
            ):
                raise StageBSmokeError("Stage B container identity or network differs")
            run_store.put_exact(
                "container_inspect.redacted.json",
                _json_bytes(inspect_value),
                artifact_id="stageb-container-inspect-redacted-001",
                media_type="application/json",
            )
            health_raw = _qwen_health(container)
            run_store.put_exact(
                "realmode_health.json",
                health_raw,
                artifact_id="stageb-qwen-realmode-health-001",
                media_type="application/json",
            )
            result, invocation_count, ports = asyncio.run(
                _run_joined_packet_kernel(
                    prepared,
                    run_store,
                    run_store.root / "lifecycle.sqlite3",
                    live,
                    ephemeral_secret=token.encode("utf-8"),
                )
            )
            ok, output_observation = _joined_success(
                result,
                invocations=invocation_count,
                ports=ports,
                run_root=run_store.root,
            )
            if not ok:
                raise StageBSmokeError(
                    "joined Stage B executor did not retain one reconciled Packet success"
                )
        except Exception as exc:
            invocation_count = max(invocation_count, int(getattr(live, "calls", 0)))
            error = f"{type(exc).__name__}: {str(exc).replace(token, '[REDACTED]')}"
        finally:
            post_inspect, post_inspect_error = joined._run_best_effort(
                ["docker", "inspect", container], timeout=30
            )
            network_none_reverified = False
            if post_inspect is not None and post_inspect.returncode == 0:
                try:
                    rows = json.loads(post_inspect.stdout)
                    network_none_reverified = (
                        type(rows) is list
                        and len(rows) == 1
                        and joined._container_has_exact_none_network(rows[0])
                    )
                except (UnicodeDecodeError, json.JSONDecodeError):
                    network_none_reverified = False
            try:
                logs = _run(["docker", "logs", container], timeout=30).stdout
            except Exception as exc:
                logs = f"logs unavailable: {type(exc).__name__}\n".encode("utf-8")
            logs = logs.replace(
                token.encode("utf-8"), b"REDACTED_EPHEMERAL_WORKER_TOKEN"
            )
            removed, remove_error = joined._run_best_effort(
                ["docker", "rm", "--force", container], timeout=60
            )
            inspected, inspect_error = joined._run_best_effort(
                ["docker", "inspect", container], timeout=30
            )
            cleanup = {
                "network_none_reverified_before_removal": network_none_reverified,
                "container_remove_command_succeeded": bool(
                    removed is not None and removed.returncode == 0
                ),
                "container_absence_specifically_verified": bool(
                    joined._docker_inspect_proves_absence(inspected)
                ),
            }
            if error is None and any(
                item is not None
                for item in (post_inspect_error, remove_error, inspect_error)
            ):
                error = "CleanupError: a container cleanup command was unresolved"
            try:
                run_store.put_exact(
                    "container.log",
                    logs,
                    artifact_id="stageb-container-log-001",
                    media_type="text/plain",
                )
            except Exception as exc:
                if error is None:
                    error = f"CleanupEvidenceError: {type(exc).__name__}"

    cleanup["ephemeral_env_file_removed_after_context"] = not env_path.exists()
    if error is None and not all(cleanup.values()):
        error = "CleanupError: exact container or ephemeral-file cleanup was not proven"
    run_store.put_exact(
        "cleanup_proof.json",
        _json_bytes(cleanup),
        artifact_id="stageb-cleanup-proof-001",
        media_type="application/json",
    )
    secret_found = False
    for path in sorted(item for item in run_store.root.rglob("*") if item.is_file()):
        _sha256, _byte_length, observed_secret = _stream_file_observation(
            path,
            secret=token.encode("utf-8"),
        )
        secret_found = secret_found or observed_secret
    run_store.put_exact(
        "secret_scan.json",
        _json_bytes(
            {
                "status": "PASS" if not secret_found else "FAIL",
                "ephemeral_worker_token_found": secret_found,
            }
        ),
        artifact_id="stageb-secret-scan-001",
        media_type="application/json",
    )
    if secret_found and error is None:
        error = "SecretScanError: ephemeral worker token was retained"
    if error is not None:
        run_store.put_exact(
            "failure.json",
            _json_bytes(
                {
                    "status": "FAIL_CLOSED",
                    "error": error,
                    "model_invocation_count": invocation_count,
                    "packet_created": bool(
                        ports is not None and ports.packet_build_result is not None
                    ),
                    "automatic_retry": False,
                }
            ),
            artifact_id="stageb-failure-001",
            media_type="application/json",
        )

    artifact_manifest: list[dict[str, Any]] = []
    for path in sorted(item for item in run_store.root.rglob("*") if item.is_file()):
        observed_sha256, observed_bytes, _found = _stream_file_observation(path)
        artifact_manifest.append(
            {
                "path": path.relative_to(run_store.root).as_posix(),
                "sha256": observed_sha256,
                "byte_length": observed_bytes,
            }
        )
    pre_receipt_manifest_raw = _json_bytes(
        {
            "schema_version": "cas_harness_gate5_stageb_pre_receipt_manifest.v0.1",
            "scope": (
                "ALL RUN-STORE FILES PRESENT BEFORE THIS MANIFEST AND THE FINAL "
                "RUNTIME RECEIPT"
            ),
            "entries": artifact_manifest,
        }
    )
    pre_receipt_manifest_binding = run_store.put_exact(
        "pre_receipt_artifact_manifest.json",
        pre_receipt_manifest_raw,
        artifact_id="stageb-qwen-pre-receipt-artifact-manifest-001",
        media_type="application/json",
    )

    packet_result = ports.packet_build_result if ports is not None else None
    assessment = packet_result.assessment if packet_result is not None else None
    status = (
        SUCCESS_PACKET_RECORDED
        if error is None
        and not secret_found
        and all(cleanup.values())
        and result is not None
        and result.status == SUCCESS_PACKET_RECORDED
        and packet_result is not None
        else "FAIL_CLOSED"
    )
    receipt = {
        "schema_version": "cas_harness_gate5_stageb_qwen_local_smoke_receipt.v0.1",
        "run_id": run_id,
        "status": status,
        "error": error,
        "model_invocation_count": invocation_count,
        "joined_result": None if result is None else asdict(result),
        "output_observation": output_observation,
        "packet": (
            None
            if packet_result is None
            else {
                "packet_id": packet_result.packet.packet_id,
                "sha256": packet_result.packet.sha256,
                "byte_length": packet_result.packet.byte_length,
                "assessment": asdict(assessment),
            }
        ),
        "packet_status": "CREATED" if packet_result is not None else "NOT_CREATED",
        "scientific_status": (
            "INELIGIBLE"
            if assessment is not None
            else "NOT_ESTABLISHED"
        ),
        "authenticated_execution": "UNAVAILABLE",
        "independent_numerical_audit": "UNAVAILABLE",
        "replication": "UNAVAILABLE",
        "claim_language_review": "UNAVAILABLE",
        "gate5_status": "OPEN",
        "gate_decision": "KEEP_OPEN",
        "admission_ring": 4,
        "product_claim_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_release_authorized": False,
        "product_route_authorized": False,
        "local_storage_authority": joined.LocalExactByteStore.authority,
        "transport": joined.DockerExecLoopbackLiveDump.transport_label,
        "network": "NONE",
        "intervention_count": 0,
        "prompt_injection_study": "NOT PERFORMED",
        "steering_study": "NOT PERFORMED",
        "provider_calls": 0,
        "provider_spend_usd": "0.00",
        "runpod_used": False,
        "runtime_image_id": image_id,
        "source_commit": prepared.source_commit,
        "clean_execution_commit": prepared.execution_commit,
        "source_to_execution_changed_paths": list(
            prepared.source_to_execution_paths
        ),
        "pre_receipt_artifact_manifest": {
            "artifact_id": pre_receipt_manifest_binding.artifact_id,
            "sha256": pre_receipt_manifest_binding.sha256.upper(),
            "byte_length": pre_receipt_manifest_binding.byte_length,
            "media_type": pre_receipt_manifest_binding.media_type,
        },
        "cleanup": cleanup,
        "secret_scan": "PASS" if not secret_found else "FAIL",
        "boundary": BOUNDARY,
    }
    receipt_path = run_store.root / "runtime_receipt.json"
    run_store.put_exact(
        "runtime_receipt.json",
        _json_bytes(receipt),
        artifact_id="stageb-qwen-runtime-receipt-001",
        media_type="application/json",
    )
    if status != SUCCESS_PACKET_RECORDED:
        raise StageBSmokeError(
            f"Stage B execution failed closed without retry; receipt={receipt_path}"
        )
    return receipt_path


def _execute_stageb() -> Path:
    """Execute once and retain a fail-closed receipt after every claimed failure."""

    try:
        return _execute_stageb_unprotected()
    except Exception as exc:
        if EXECUTION_CLAIM_PATH.is_file():
            try:
                claim = _load_json(EXECUTION_CLAIM_PATH)
                run_id = claim.get("run_id")
                if type(run_id) is str and re.fullmatch(
                    r"gate5-stageb-qwen-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}",
                    run_id,
                ):
                    root = RUNS_ROOT / run_id
                    receipt_path = root / "runtime_receipt.json"
                    if not receipt_path.exists():
                        emergency = {
                            "schema_version": (
                                "cas_harness_gate5_stageb_qwen_local_smoke_"
                                "emergency_receipt.v0.1"
                            ),
                            "run_id": run_id,
                            "status": "FAIL_CLOSED",
                            "failure_kind": type(exc).__name__,
                            "failure_detail": (
                                "AN ORDINARY POST-CLAIM FAILURE OCCURRED; INSPECT THE "
                                "CREATE-ONLY PARTIAL ARTIFACT SET"
                            ),
                            "automatic_retry": False,
                            "replacement_run": False,
                            "gate5_status": "OPEN",
                            "gate_decision": "KEEP_OPEN",
                            "admission_ring": 4,
                            "product_claim_status": "NOT LICENSED",
                            "disclosure_status": "HELD",
                            "public_release_authorized": False,
                            "product_route_authorized": False,
                            "boundary": BOUNDARY,
                        }
                        joined.LocalExactByteStore(root).put_exact(
                            "runtime_receipt.json",
                            _json_bytes(emergency),
                            artifact_id="stageb-qwen-runtime-receipt-001",
                            media_type="application/json",
                        )
            except Exception:
                # The create-only execution claim remains the terminal evidence
                # when the local filesystem cannot retain even this receipt.
                pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build-runtime-image", action="store_true")
    mode.add_argument("--prepare-execution-binding", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.build_runtime_image:
        print(_build_runtime_image())
    elif args.prepare_execution_binding:
        print(_prepare_execution_binding())
    else:
        print(_execute_stageb())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
