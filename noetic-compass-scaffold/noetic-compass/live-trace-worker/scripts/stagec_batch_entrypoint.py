#!/usr/bin/env python3
"""Sealed Stage C batch entrypoint.

The image lane intentionally has no batch executor yet.  This entrypoint only
checks that externally frozen inputs and the exact GPU runtime are present,
then exits fail-closed.  It never imports the worker application, loads model
weights, starts FastAPI, opens a socket, or calls a provider API.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXIT_FAIL_CLOSED = 78
SEALED_ARGUMENT = "sealed"
INPUT_ROOT = Path("/run/cas-stagec/input")
EXPECTED_UID = 10_001
EXPECTED_GID = 10_001
EXPECTED_TORCH_VERSION = "2.13.0+cu126"
EXPECTED_CUDA_RUNTIME = "12.6"
EXPECTED_MODEL_KEY = "qwen2.5-0.5b-instruct"
EXPECTED_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
EXPECTED_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


@dataclass(frozen=True, slots=True)
class RequiredInput:
    role: str
    filename: str
    digest_env: str


REQUIRED_INPUTS = (
    RequiredInput(
        "authorization",
        "authorization.canonical.json",
        "CAS_STAGEC_AUTHORIZATION_SHA256",
    ),
    RequiredInput(
        "corpus",
        "corpus.canonical.jsonl",
        "CAS_STAGEC_CORPUS_SHA256",
    ),
    RequiredInput(
        "dependencies",
        "dependencies.canonical.json",
        "CAS_STAGEC_DEPENDENCIES_SHA256",
    ),
    RequiredInput(
        "trust",
        "trust.canonical.json",
        "CAS_STAGEC_TRUST_SHA256",
    ),
    RequiredInput(
        "execution_image_receipt",
        "execution-image-receipt.canonical.json",
        "CAS_STAGEC_EXECUTION_IMAGE_RECEIPT_SHA256",
    ),
    RequiredInput(
        "network_guard_receipt",
        "network-guard-receipt.canonical.json",
        "CAS_STAGEC_NETWORK_GUARD_RECEIPT_SHA256",
    ),
    RequiredInput(
        "no_spend_preflight",
        "no-spend-preflight.canonical.json",
        "CAS_STAGEC_NO_SPEND_PREFLIGHT_SHA256",
    ),
)


class FailClosed(RuntimeError):
    """Expected refusal carrying only a non-sensitive reason code."""

    def __init__(self, reason: str, role: str = "none") -> None:
        super().__init__(reason)
        self.reason = reason
        self.role = role


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_input_bundle(
    *,
    root: Path = INPUT_ROOT,
    environ: Mapping[str, str] | None = None,
    expected_uid: int = 0,
    expected_gid: int = 0,
) -> dict[str, tuple[int, str]]:
    """Validate exact mounted members without parsing or executing content."""

    env = os.environ if environ is None else environ
    try:
        root_stat = root.lstat()
    except FileNotFoundError as exc:
        raise FailClosed("REQUIRED_INPUT_ROOT_MISSING") from exc
    if not stat.S_ISDIR(root_stat.st_mode) or root.is_symlink():
        raise FailClosed("REQUIRED_INPUT_ROOT_NOT_DIRECTORY")
    if root_stat.st_mode & 0o222:
        raise FailClosed("REQUIRED_INPUT_ROOT_WRITABLE")
    if os.name == "posix" and (
        root_stat.st_uid != expected_uid or root_stat.st_gid != expected_gid
    ):
        raise FailClosed("REQUIRED_INPUT_ROOT_NOT_ROOT_OWNED")

    expected_names = {item.filename for item in REQUIRED_INPUTS}
    observed_names = {path.name for path in root.iterdir()}
    if observed_names != expected_names:
        raise FailClosed("REQUIRED_INPUT_MEMBERSHIP_MISMATCH")

    observations: dict[str, tuple[int, str]] = {}
    for item in REQUIRED_INPUTS:
        path = root / item.filename
        try:
            observed = path.lstat()
        except FileNotFoundError as exc:
            raise FailClosed("REQUIRED_INPUT_MISSING", item.role) from exc
        if not stat.S_ISREG(observed.st_mode) or path.is_symlink():
            raise FailClosed("REQUIRED_INPUT_NOT_REGULAR", item.role)
        if os.name == "posix" and (
            observed.st_uid != expected_uid or observed.st_gid != expected_gid
        ):
            raise FailClosed("REQUIRED_INPUT_NOT_ROOT_OWNED", item.role)
        if observed.st_size <= 0:
            raise FailClosed("REQUIRED_INPUT_EMPTY", item.role)
        if observed.st_mode & 0o222:
            raise FailClosed("REQUIRED_INPUT_WRITABLE", item.role)

        expected_digest = env.get(item.digest_env, "")
        if re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
            raise FailClosed("REQUIRED_INPUT_DIGEST_UNBOUND", item.role)
        observed_digest = _sha256(path)
        if observed_digest != expected_digest:
            raise FailClosed("REQUIRED_INPUT_DIGEST_MISMATCH", item.role)
        observations[item.role] = (observed.st_size, observed_digest)
    return observations


def validate_runtime_contract(
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Check the frozen runtime without loading tokenizer or model weights."""

    env = os.environ if environ is None else environ
    required_env = {
        "ATLAS_WORKER_PROFILE": "production",
        "ATLAS_WORKER_MODEL": EXPECTED_MODEL_KEY,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TORCH_DISABLE_NATIVE_JIT": "1",
        "ATLAS_WORKER_REQUIRE_READ_ONLY_ROOTFS": "1",
        "CAS_STAGEC_BATCH_ACTIVATION": "DISABLED_NOT_IMPLEMENTED",
    }
    for name, expected in required_env.items():
        if env.get(name) != expected:
            raise FailClosed("RUNTIME_ENVIRONMENT_MISMATCH", name)

    if not hasattr(os, "getuid") or os.getuid() != EXPECTED_UID:
        raise FailClosed("RUNTIME_UID_MISMATCH")
    if not hasattr(os, "getgid") or os.getgid() != EXPECTED_GID:
        raise FailClosed("RUNTIME_GID_MISMATCH")
    if not hasattr(os, "statvfs"):
        raise FailClosed("ROOT_FILESYSTEM_READ_ONLY_UNOBSERVABLE")
    read_only_flag = getattr(os, "ST_RDONLY", 1)
    if not bool(os.statvfs("/").f_flag & read_only_flag):
        raise FailClosed("ROOT_FILESYSTEM_NOT_READ_ONLY")

    # Importing Torch is intentionally delayed until every external input has
    # passed its byte identity check.  No model/Tokenizer import occurs here.
    import torch

    torch_version = str(getattr(torch, "__version__", ""))
    cuda_runtime = str(getattr(getattr(torch, "version", None), "cuda", ""))
    if torch_version != EXPECTED_TORCH_VERSION:
        raise FailClosed("TORCH_VERSION_MISMATCH")
    if cuda_runtime != EXPECTED_CUDA_RUNTIME:
        raise FailClosed("CUDA_RUNTIME_MISMATCH")
    if not bool(torch.cuda.is_available()):
        raise FailClosed("CUDA_DEVICE_UNAVAILABLE")
    if not bool(torch.cuda.is_bf16_supported(including_emulation=False)):
        raise FailClosed("NATIVE_BF16_UNAVAILABLE")

    return {
        "torch_version": torch_version,
        "cuda_runtime": cuda_runtime,
        "cuda_bf16": True,
        "model_id": EXPECTED_MODEL_ID,
        "model_revision": EXPECTED_MODEL_REVISION,
    }


def _emit(status: str, reason: str, role: str = "none") -> None:
    # Do not echo paths, digests, environment variables, file content, or
    # provider data.  These fixed vocabulary fields are safe for container logs.
    print(
        json.dumps(
            {"reason": reason, "role": role, "status": status},
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != [SEALED_ARGUMENT]:
        _emit("STAGEC_BATCH_FAIL_CLOSED", "UNRECOGNIZED_ENTRYPOINT_ARGUMENT")
        return EXIT_FAIL_CLOSED
    try:
        validate_input_bundle()
        validate_runtime_contract()
    except FailClosed as exc:
        _emit("STAGEC_BATCH_FAIL_CLOSED", exc.reason, exc.role)
        return EXIT_FAIL_CLOSED
    except Exception:
        _emit("STAGEC_BATCH_FAIL_CLOSED", "UNEXPECTED_PREFLIGHT_FAILURE")
        return EXIT_FAIL_CLOSED

    # Positive activation is deliberately absent.  This remains true even if
    # all mounted prerequisites and the A40 runtime satisfy the preflight.
    _emit(
        "STAGEC_BATCH_FAIL_CLOSED",
        "RUNTIME_ACTIVATION_NOT_IMPLEMENTED",
    )
    return EXIT_FAIL_CLOSED


if __name__ == "__main__":
    raise SystemExit(main())
