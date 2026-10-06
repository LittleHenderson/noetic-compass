"""Focused fail-closed tests for auxiliary open-weight model identity."""

from __future__ import annotations

from argparse import Namespace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import capture_open_weight_probe_dataset as capture  # noqa: E402
from open_weight_artifact_guard import (  # noqa: E402
    ArtifactPolicyError,
    MANIFEST_SCHEMA_VERSION,
    verify_open_weight_artifact_manifest,
)
import run_open_weight_probe_shard as shard  # noqa: E402


MODEL_ID = "example/exact-open-weight-model"
REVISION = "a" * 40


def _write_manifest(
    tmp_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    model_root = tmp_path / "model"
    model_root.mkdir()
    contents = {
        "config.json": b'{"model_type":"fixture"}',
        "tokenizer.json": b'{"version":"1.0"}',
        "model.safetensors": b"SAFE-TENSOR-FIXTURE",
    }
    artifacts = []
    for relative_path, content in contents.items():
        path = model_root / relative_path
        path.write_bytes(content)
        artifacts.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "byte_count": len(content),
            }
        )
    payload: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "model_id": MODEL_ID,
        "model_revision": REVISION,
        "model_root": "model",
        "artifacts": artifacts,
    }
    payload.update(overrides or {})
    manifest_path = tmp_path / "model-artifacts.json"
    manifest_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return manifest_path, model_root, payload


def _manifest_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_materialized_snapshot_verifies(tmp_path: Path):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)

    verified = verify_open_weight_artifact_manifest(
        manifest_path=manifest_path,
        expected_manifest_sha256=_manifest_sha256(manifest_path),
        model_id=MODEL_ID,
        model_revision=REVISION,
        trust_remote_code=False,
    )

    assert verified.model_root == model_root.resolve()
    assert verified.artifact_count == 3
    assert verified.evidence()["all_artifacts_hash_verified"] is True
    assert len(verified.evidence()["artifacts"]) == 3
    assert verified.evidence()["local_files_only"] is True
    assert verified.evidence()["trust_remote_code"] is False


def test_wrong_caller_manifest_digest_is_rejected_before_json_parse(tmp_path: Path):
    manifest_path = tmp_path / "model-artifacts.json"
    manifest_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="caller binding"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256="0" * 64,
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_hardlinked_snapshot_artifact_is_rejected(tmp_path: Path):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    try:
        (tmp_path / "outside-config-hardlink.json").hardlink_to(
            model_root / "config.json"
        )
    except OSError as exc:  # pragma: no cover - filesystem dependent
        pytest.skip(f"host cannot create a test hardlink: {exc}")

    with pytest.raises(ArtifactPolicyError, match="hard-linked"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_model_inputs_must_be_at_snapshot_root(tmp_path: Path):
    manifest_path, model_root, payload = _write_manifest(tmp_path)
    nested = model_root / "nested"
    nested.mkdir()
    (model_root / "config.json").replace(nested / "config.json")
    payload["artifacts"][0]["path"] = "nested/config.json"
    manifest_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="root-level config.json"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_probe_shard_supports_clean_package_import():
    worker_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-c", "import scripts.run_open_weight_probe_shard"],
        cwd=worker_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    "revision",
    [None, "main", "abc123", "A" * 40, "g" * 40, "a" * 39, "a" * 41],
)
def test_revision_must_be_full_lowercase_commit_sha(
    tmp_path: Path,
    revision: str | None,
):
    manifest_path, _model_root, _payload = _write_manifest(tmp_path)

    with pytest.raises(ArtifactPolicyError, match="40-character lowercase commit SHA"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=revision,
            trust_remote_code=False,
        )


def test_remote_code_true_is_rejected(tmp_path: Path):
    manifest_path, _model_root, _payload = _write_manifest(tmp_path)

    with pytest.raises(ArtifactPolicyError, match="trust_remote_code must be exactly false"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=True,
        )


def test_one_byte_artifact_tamper_fails_closed(tmp_path: Path):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    (model_root / "config.json").write_bytes(b'{"model_type":"forged"}')

    with pytest.raises(ArtifactPolicyError, match="SHA-256 mismatch"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_unmanifested_snapshot_file_fails_closed(tmp_path: Path):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    (model_root / "mutable-extra.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="does not exactly match"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_parent_path_in_manifest_is_rejected_before_hashing(tmp_path: Path):
    manifest_path, _model_root, payload = _write_manifest(tmp_path)
    payload["artifacts"][0]["path"] = "../config.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="parent segments"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_safetensors_index_cannot_escape_verified_snapshot(tmp_path: Path):
    manifest_path, model_root, payload = _write_manifest(tmp_path)
    (model_root / "model.safetensors").unlink()
    (model_root / "model-00001-of-00001.safetensors").write_bytes(b"VERIFIED-SHARD")
    index = {"metadata": {}, "weight_map": {"layer.weight": "../outside.safetensors"}}
    (model_root / "model.safetensors.index.json").write_text(
        json.dumps(index),
        encoding="utf-8",
    )
    (tmp_path / "outside.safetensors").write_bytes(b"UNVERIFIED-SHARD")
    payload["artifacts"] = []
    for path in sorted(model_root.iterdir()):
        content = path.read_bytes()
        payload["artifacts"].append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "byte_count": len(content),
            }
        )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="parent segments"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


def test_symlinked_snapshot_input_is_rejected(tmp_path: Path):
    manifest_path, model_root, payload = _write_manifest(tmp_path)
    target = tmp_path / "outside-config.json"
    target.write_bytes((model_root / "config.json").read_bytes())
    (model_root / "config.json").unlink()
    try:
        (model_root / "config.json").symlink_to(target)
    except OSError as exc:  # pragma: no cover - host privilege dependent
        pytest.skip(f"host cannot create a test symlink: {exc}")
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactPolicyError, match="symlink or junction"):
        verify_open_weight_artifact_manifest(
            manifest_path=manifest_path,
            expected_manifest_sha256=_manifest_sha256(manifest_path),
            model_id=MODEL_ID,
            model_revision=REVISION,
            trust_remote_code=False,
        )


class _FakeCuda:
    @staticmethod
    def is_available() -> bool:
        return False


class _FakeDevice:
    type = "cpu"


class _FakeParameter:
    device = _FakeDevice()
    dtype = "float32"

    @staticmethod
    def numel() -> int:
        return 7


class _FakeModel:
    def __init__(self) -> None:
        self.eval_called = False

    def eval(self) -> None:
        self.eval_called = True

    @staticmethod
    def parameters():
        return iter([_FakeParameter()])


def _install_fake_model_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, str, dict[str, Any]]], _FakeModel]:
    calls: list[tuple[str, str, dict[str, Any]]] = []
    fake_torch = ModuleType("torch")
    fake_torch.cuda = _FakeCuda()
    fake_torch.float16 = "float16"
    fake_torch.bfloat16 = "bfloat16"
    fake_torch.float32 = "float32"

    model = _FakeModel()

    class FakeConfigLoader:
        @staticmethod
        def from_pretrained(source: str, **kwargs: Any):
            calls.append(("config", source, kwargs))
            return SimpleNamespace(
                architectures=["FixtureForCausalLM"],
                model_type="fixture",
                hidden_size=8,
                num_hidden_layers=1,
                num_attention_heads=1,
                vocab_size=16,
            )

    class FakeTokenizerLoader:
        @staticmethod
        def from_pretrained(source: str, **kwargs: Any):
            calls.append(("tokenizer", source, kwargs))
            return object()

    class FakeModelLoader:
        @staticmethod
        def from_pretrained(source: str, **kwargs: Any):
            calls.append(("model", source, kwargs))
            return model

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoConfig = FakeConfigLoader
    fake_transformers.AutoTokenizer = FakeTokenizerLoader
    fake_transformers.AutoModelForCausalLM = FakeModelLoader
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    return calls, model


def _assert_local_verified_loader_calls(
    calls: list[tuple[str, str, dict[str, Any]]],
    model_root: Path,
) -> None:
    assert [kind for kind, _source, _kwargs in calls] == ["config", "tokenizer", "model"]
    assert all(Path(source) == model_root.resolve() for _kind, source, _kwargs in calls)
    assert all(kwargs["revision"] == REVISION for _kind, _source, kwargs in calls)
    assert all(kwargs["local_files_only"] is True for _kind, _source, kwargs in calls)
    assert all(kwargs["trust_remote_code"] is False for _kind, _source, kwargs in calls)
    model_kwargs = calls[-1][2]
    assert model_kwargs["use_safetensors"] is True


def test_shared_loader_uses_only_verified_local_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    calls, model = _install_fake_model_runtime(monkeypatch)
    config = shard.ProbeShardConfig(
        model_id=MODEL_ID,
        worker_id="worker",
        audit_id="audit",
        job_id="job",
        layer_start=0,
        layer_end=0,
        shard_id="shard",
        assigned_methods=("probe",),
        expected_outputs=("worker_evidence_manifest",),
        result_path=tmp_path / "result.json",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=_manifest_sha256(manifest_path),
        device_map="cpu",
    )

    loaded_model, _tokenizer, model_info = shard.load_open_weight_model(config)

    assert loaded_model is model
    assert model.eval_called is True
    _assert_local_verified_loader_calls(calls, model_root)
    assert model_info["artifact_identity"]["all_artifacts_hash_verified"] is True
    assert model_info["artifact_identity"]["post_load_reverified"] is True
    assert model_info["artifact_identity"]["verification_timing"] == (
        "pre_parse_and_post_load"
    )
    assert model_info["artifact_identity"]["toctou_reversion_resistance"] == "OPEN"
    assert model_info["artifact_identity"]["durable_snapshot_immutability_established"] is False
    assert model_info["artifact_identity"][
        "symlinks_junctions_and_hardlinks_rejected"
    ] is True
    assert {artifact["path"] for artifact in model_info["artifact_identity"]["artifacts"]} == {
        "config.json",
        "model.safetensors",
        "tokenizer.json",
    }


def test_capture_loader_uses_same_fail_closed_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    calls, model = _install_fake_model_runtime(monkeypatch)
    args = Namespace(
        model_id=MODEL_ID,
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=_manifest_sha256(manifest_path),
        trust_remote_code=False,
        torch_dtype="auto",
        device_map="cpu",
    )

    loaded_model, _tokenizer, model_info = capture.load_model(args)

    assert loaded_model is model
    _assert_local_verified_loader_calls(calls, model_root)
    assert model_info["artifact_identity"]["manifest_sha256"]


def test_invalid_manifest_prevents_any_transformers_parser_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    calls, _model = _install_fake_model_runtime(monkeypatch)
    (model_root / "model.safetensors").write_bytes(b"tampered")
    config = shard.ProbeShardConfig(
        model_id=MODEL_ID,
        worker_id="worker",
        audit_id="audit",
        job_id="job",
        layer_start=0,
        layer_end=0,
        shard_id="shard",
        assigned_methods=("probe",),
        expected_outputs=("worker_evidence_manifest",),
        result_path=tmp_path / "result.json",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=_manifest_sha256(manifest_path),
        device_map="cpu",
    )

    with pytest.raises(ArtifactPolicyError, match="mismatch"):
        shard.load_open_weight_model(config)

    assert calls == []


def test_snapshot_mutation_during_transformers_load_is_detected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    manifest_path, model_root, _payload = _write_manifest(tmp_path)
    calls, model = _install_fake_model_runtime(monkeypatch)

    class MutatingModelLoader:
        @staticmethod
        def from_pretrained(source: str, **kwargs: Any):
            calls.append(("model", source, kwargs))
            (model_root / "config.json").write_bytes(b'{"model_type":"changed-after-parse"}')
            return model

    sys.modules["transformers"].AutoModelForCausalLM = MutatingModelLoader
    config = shard.ProbeShardConfig(
        model_id=MODEL_ID,
        worker_id="worker",
        audit_id="audit",
        job_id="job",
        layer_start=0,
        layer_end=0,
        shard_id="shard",
        assigned_methods=("probe",),
        expected_outputs=("worker_evidence_manifest",),
        result_path=tmp_path / "result.json",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=_manifest_sha256(manifest_path),
        device_map="cpu",
    )

    with pytest.raises(ArtifactPolicyError, match="SHA-256 mismatch"):
        shard.load_open_weight_model(config)

    assert [kind for kind, _source, _kwargs in calls] == ["config", "tokenizer", "model"]
