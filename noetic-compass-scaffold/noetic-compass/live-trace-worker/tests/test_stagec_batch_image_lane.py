"""Static and unit checks for the build-only Stage C image lane."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
from typing import Any
import urllib.parse

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fetch_qwen_stagec_model as fetcher  # noqa: E402
import stagec_batch_entrypoint as entrypoint  # noqa: E402
from app.runtime import model_loader  # noqa: E402


WORKER = Path(__file__).resolve().parents[1]
REPOSITORY = WORKER.parents[2]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "stagec-qwen-batch-image.yml"


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return "https://cdn.example.invalid/exact-artifact"


def _fixture_artifacts() -> tuple[dict[str, bytes], dict[str, fetcher.Artifact]]:
    contents = {f"fixture-{index}.bin": bytes([index]) * index for index in range(1, 8)}
    artifacts = {
        name: fetcher.Artifact(len(raw), hashlib.sha256(raw).hexdigest())
        for name, raw in contents.items()
    }
    return contents, artifacts


def test_qwen_contract_exactly_matches_the_worker_binding() -> None:
    assert fetcher.MODEL_ID == model_loader.QWEN_05B_INSTRUCT_MODEL_ID
    assert fetcher.REVISION == model_loader.QWEN_05B_INSTRUCT_REVISION
    assert len(fetcher.ARTIFACTS) == 7
    assert {
        name: (artifact.sha256, artifact.byte_length)
        for name, artifact in fetcher.ARTIFACTS.items()
    } == model_loader.QWEN_05B_INSTRUCT_ARTIFACTS


def test_fetcher_materializes_only_regular_hash_verified_files(tmp_path: Path) -> None:
    contents, artifacts = _fixture_artifacts()

    def fake_open(request: Any, _timeout: float) -> _FakeResponse:
        name = urllib.parse.unquote(request.full_url.rsplit("/", 1)[-1])
        return _FakeResponse(contents[name])

    snapshot = tmp_path / "snapshot"
    observations = fetcher.fetch_snapshot(
        snapshot,
        artifacts=artifacts,
        open_url=fake_open,
    )

    assert set(observations) == set(artifacts)
    assert {path.name for path in snapshot.iterdir()} == set(artifacts)
    assert all(stat.S_ISREG(path.lstat().st_mode) for path in snapshot.iterdir())
    assert all(not path.is_symlink() for path in snapshot.iterdir())
    assert fetcher.verify_snapshot(snapshot, artifacts=artifacts) == observations


def test_fetcher_removes_partial_snapshot_after_size_violation(tmp_path: Path) -> None:
    contents, artifacts = _fixture_artifacts()
    first = sorted(contents)[0]
    contents[first] += b"too-large"

    def fake_open(request: Any, _timeout: float) -> _FakeResponse:
        name = urllib.parse.unquote(request.full_url.rsplit("/", 1)[-1])
        return _FakeResponse(contents[name])

    snapshot = tmp_path / "snapshot"
    with pytest.raises(RuntimeError, match="exceeded its frozen byte length"):
        fetcher.fetch_snapshot(
            snapshot,
            artifacts=artifacts,
            open_url=fake_open,
        )
    assert not snapshot.exists()


def _write_required_inputs(root: Path) -> dict[str, str]:
    root.mkdir(exist_ok=True)
    env: dict[str, str] = {}
    for item in entrypoint.REQUIRED_INPUTS:
        raw = (item.role + "\n").encode("utf-8")
        path = root / item.filename
        path.write_bytes(raw)
        path.chmod(0o444)
        env[item.digest_env] = hashlib.sha256(raw).hexdigest()
    root.chmod(0o555)
    return env


def test_entrypoint_validates_exact_read_only_input_membership(tmp_path: Path) -> None:
    env = _write_required_inputs(tmp_path)
    owner = tmp_path.stat()
    observations = entrypoint.validate_input_bundle(
        root=tmp_path,
        environ=env,
        expected_uid=owner.st_uid,
        expected_gid=owner.st_gid,
    )
    assert set(observations) == {item.role for item in entrypoint.REQUIRED_INPUTS}

    tmp_path.chmod(0o755)
    extra = tmp_path / "unbound-extra.json"
    extra.write_bytes(b"{}")
    extra.chmod(0o444)
    tmp_path.chmod(0o555)
    with pytest.raises(entrypoint.FailClosed) as exc_info:
        entrypoint.validate_input_bundle(
            root=tmp_path,
            environ=env,
            expected_uid=owner.st_uid,
            expected_gid=owner.st_gid,
        )
    assert exc_info.value.reason == "REQUIRED_INPUT_MEMBERSHIP_MISMATCH"


def test_entrypoint_rejects_writable_or_digest_mismatched_inputs(tmp_path: Path) -> None:
    env = _write_required_inputs(tmp_path)
    owner = tmp_path.stat()
    first = entrypoint.REQUIRED_INPUTS[0]
    first_path = tmp_path / first.filename
    tmp_path.chmod(0o755)
    first_path.chmod(0o644)
    tmp_path.chmod(0o555)
    with pytest.raises(entrypoint.FailClosed) as exc_info:
        entrypoint.validate_input_bundle(
            root=tmp_path,
            environ=env,
            expected_uid=owner.st_uid,
            expected_gid=owner.st_gid,
        )
    assert exc_info.value.reason == "REQUIRED_INPUT_WRITABLE"

    first_path.chmod(0o444)
    env[first.digest_env] = "0" * 64
    with pytest.raises(entrypoint.FailClosed) as exc_info:
        entrypoint.validate_input_bundle(
            root=tmp_path,
            environ=env,
            expected_uid=owner.st_uid,
            expected_gid=owner.st_gid,
        )
    assert exc_info.value.reason == "REQUIRED_INPUT_DIGEST_MISMATCH"


def test_runtime_contract_requires_exact_torch_cuda_bf16_and_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_torch = SimpleNamespace(
        __version__="2.13.0+cu126",
        version=SimpleNamespace(cuda="12.6"),
        cuda=SimpleNamespace(
            is_available=lambda: True,
            is_bf16_supported=lambda *, including_emulation: not including_emulation,
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setattr(os, "getuid", lambda: 10_001, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 10_001, raising=False)
    monkeypatch.setattr(os, "ST_RDONLY", 1, raising=False)
    monkeypatch.setattr(
        os,
        "statvfs",
        lambda _path: SimpleNamespace(f_flag=1),
        raising=False,
    )
    env = {
        "ATLAS_WORKER_PROFILE": "production",
        "ATLAS_WORKER_MODEL": "qwen2.5-0.5b-instruct",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TORCH_DISABLE_NATIVE_JIT": "1",
        "ATLAS_WORKER_REQUIRE_READ_ONLY_ROOTFS": "1",
        "CAS_STAGEC_BATCH_ACTIVATION": "DISABLED_NOT_IMPLEMENTED",
    }
    observed = entrypoint.validate_runtime_contract(environ=env)
    assert observed["torch_version"] == "2.13.0+cu126"
    assert observed["cuda_runtime"] == "12.6"
    assert observed["cuda_bf16"] is True

    fake_torch.cuda.is_bf16_supported = lambda *, including_emulation: False
    with pytest.raises(entrypoint.FailClosed) as exc_info:
        entrypoint.validate_runtime_contract(environ=env)
    assert exc_info.value.reason == "NATIVE_BF16_UNAVAILABLE"

    fake_torch.cuda.is_bf16_supported = (
        lambda *, including_emulation: not including_emulation
    )
    monkeypatch.setattr(
        os,
        "statvfs",
        lambda _path: SimpleNamespace(f_flag=0),
        raising=False,
    )
    with pytest.raises(entrypoint.FailClosed) as exc_info:
        entrypoint.validate_runtime_contract(environ=env)
    assert exc_info.value.reason == "ROOT_FILESYSTEM_NOT_READ_ONLY"


def test_entrypoint_has_no_positive_activation_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(entrypoint, "validate_input_bundle", lambda: {})
    monkeypatch.setattr(entrypoint, "validate_runtime_contract", lambda: {})
    assert entrypoint.main(["sealed"]) == entrypoint.EXIT_FAIL_CLOSED
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "reason": "RUNTIME_ACTIVATION_NOT_IMPLEMENTED",
        "role": "none",
        "status": "STAGEC_BATCH_FAIL_CLOSED",
    }


def test_batch_entrypoint_imports_no_network_provider_or_process_client() -> None:
    source = (SCRIPTS / "stagec_batch_entrypoint.py").read_text("utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "boto3",
            "httpx",
            "huggingface_hub",
            "requests",
            "runpod",
            "socket",
            "subprocess",
            "transformers",
            "urllib",
        }
    )


def test_batch_dockerfile_replaces_fastapi_and_retains_frozen_runtime() -> None:
    dockerfile = (WORKER / "Dockerfile.stagec-batch").read_text("utf-8")
    assert dockerfile.startswith(
        "# syntax=docker/dockerfile:1.7@sha256:"
        "a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e\n"
    )
    assert "ARG PARENT_IMAGE\nFROM ${PARENT_IMAGE}" in dockerfile
    assert 'USER 10001:10001' in dockerfile
    assert 'torch.__version__ == "2.13.0+cu126"' in dockerfile
    assert 'torch.version.cuda == "12.6"' in dockerfile
    assert "TORCH_DISABLE_NATIVE_JIT=1" in dockerfile
    assert "NATIVE_BF16_REQUIRED" in dockerfile
    assert "HF_HUB_OFFLINE=1" in dockerfile
    assert "TRANSFORMERS_OFFLINE=1" in dockerfile
    assert "ATLAS_WORKER_REQUIRE_READ_ONLY_ROOTFS=1" in dockerfile
    assert "HEALTHCHECK NONE" in dockerfile
    assert 'ENTRYPOINT ["python", "-B", "/worker/stagec_batch/entrypoint.py"]' in dockerfile
    assert 'CMD ["sealed"]' in dockerfile
    assert "uvicorn" not in dockerfile
    assert "app.main" not in dockerfile


def test_qwen_layer_is_exact_regular_file_acquisition_only() -> None:
    dockerfile = (WORKER / "Dockerfile.qwen-stagec-model").read_text("utf-8")
    assert dockerfile.startswith(
        "# syntax=docker/dockerfile:1.7@sha256:"
        "a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e\n"
    )
    assert "ARG PARENT_IMAGE\nFROM ${PARENT_IMAGE}" in dockerfile
    assert "--mount=type=bind,source=scripts/fetch_qwen_stagec_model.py" in dockerfile
    assert "chmod 0755 /worker /worker/.cache /worker/.cache/huggingface" in dockerfile
    assert "--snapshot /worker/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct" in dockerfile
    assert "-type f | wc -l)\" -eq 7" in dockerfile
    assert "-type l | wc -l)\" -eq 0" in dockerfile
    assert "chmod 0555 /worker/.cache/huggingface/hub" in dockerfile
    assert "COPY --chown=0:0 hf_cache" not in dockerfile


def test_docker_context_admits_only_the_two_stagec_helpers() -> None:
    dockerignore = (WORKER / ".dockerignore").read_text("utf-8").splitlines()
    assert "scripts/*" in dockerignore
    assert "!scripts/fetch_qwen_stagec_model.py" in dockerignore
    assert "!scripts/stagec_batch_entrypoint.py" in dockerignore
    assert "scripts/" not in dockerignore


def test_workflow_is_owner_dispatched_build_only_and_never_mutates_runpod() -> None:
    workflow = WORKFLOW.read_text("utf-8")
    assert "  workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "\n  pull_request:" not in workflow
    assert "github.actor == github.repository_owner" in workflow
    assert "BUILD STAGE C IMAGE ONLY" in workflow
    assert "PACKAGE_NAME: noetic-compass-stagec-qwen-batch" in workflow
    assert "BATCH_TAG=stagec-qwen-batch-git-%s" in workflow
    assert (
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
        in workflow
    )
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
        in workflow
    )
    assert "Dockerfile.qwen-stagec-model" in workflow
    assert "Dockerfile.stagec-batch" in workflow
    assert "--network=none" in workflow
    assert workflow.count('docker push "$batch_ref"') == 1
    assert "commit-derived tag already exists; refusing workflow overwrite" in workflow
    assert 'visibility\") != \"private\"' in workflow
    assert "manifest_media_type" in workflow
    assert "config_digest" in workflow
    assert '"execution_reference_policy": "DIGEST_ONLY"' in workflow
    assert "WORKFLOW_REFUSES_EXISTING_TAG_NOT_REGISTRY_IMMUTABILITY" in workflow
    assert "runpod_mutation_count\": 0" in workflow
    assert ":master" not in workflow
    assert ":latest" not in workflow
    assert "/pods/" not in workflow
    assert "api.runpod" not in workflow.lower()
