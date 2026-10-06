"""Tests for the real open-weight probe-shard command contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_open_weight_probe_shard as shard  # noqa: E402


class _FakeCuda:
    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


class _FakeTorch:
    float16 = "float16"
    bfloat16 = "bfloat16"
    float32 = "float32"

    def __init__(self, *, cuda_available: bool) -> None:
        self.cuda = _FakeCuda(cuda_available)


class _FakeDevice:
    def __init__(self, kind: str) -> None:
        self.type = kind


class _FakeParameter:
    def __init__(self, *, device: str, dtype: str) -> None:
        self.device = _FakeDevice(device)
        self.dtype = dtype


class _FakeModel:
    def __init__(self, parameters: list[_FakeParameter]) -> None:
        self._parameters = parameters

    def parameters(self):
        return iter(self._parameters)


class _FakeFiniteResult:
    def __init__(self, value: bool) -> None:
        self._value = value

    def all(self):
        return self

    def item(self) -> bool:
        return self._value


class _FakeTensor:
    def __init__(self, *, finite: bool) -> None:
        self._finite = finite

    def isfinite(self) -> _FakeFiniteResult:
        return _FakeFiniteResult(self._finite)


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    env = {
        "CAS_FLEET_MODEL_ID": "EleutherAI/gpt-neox-20b",
        "CAS_FLEET_WORKER_ID": "probe-worker-001",
        "CAS_FLEET_AUDIT_ID": "cas-dist-large",
        "CAS_FLEET_JOB_ID": "fleet-job-001",
        "CAS_FLEET_LAYER_START": "0",
        "CAS_FLEET_LAYER_END": "3",
        "CAS_FLEET_SHARD_ID": "layers-000-003",
        "CAS_FLEET_ASSIGNED_METHODS_JSON": json.dumps(["foundation_probe", "targeted_ablation"]),
        "CAS_FLEET_EXPECTED_OUTPUTS_JSON": json.dumps(
            [
                "layer_activation_summary",
                "cas_axis_readout",
                "blindspot_overlay",
                "worker_evidence_manifest",
            ]
        ),
        "CAS_FLEET_RESULT_PATH": str(tmp_path / "result.json"),
        "CAS_FLEET_PROMPT": "A clinician must decide whether to discharge a patient.",
        "CAS_FLEET_MODEL_REVISION": "a" * 40,
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH": str(tmp_path / "model-artifacts.json"),
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256": "b" * 64,
    }
    env.update(overrides)
    return env


def test_config_from_env_requires_prompt_or_scenario_path(tmp_path: Path):
    env = _env(tmp_path)
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    with pytest.raises(RuntimeError, match="CAS_FLEET_SCENARIO_PATH or CAS_FLEET_PROMPT"):
        shard.load_scenarios(config)


@pytest.mark.parametrize(
    "revision",
    ["main", "abc123", "A" * 40, "g" * 40, "a" * 39, "a" * 41],
)
def test_config_from_env_rejects_mutable_or_malformed_revision(
    tmp_path: Path,
    revision: str,
):
    with pytest.raises(RuntimeError, match="40-character lowercase commit SHA"):
        shard.ProbeShardConfig.from_env(_env(tmp_path, CAS_FLEET_MODEL_REVISION=revision))


def test_config_from_env_requires_caller_artifact_manifest(tmp_path: Path):
    env = _env(tmp_path)
    env.pop("CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH")

    with pytest.raises(ValueError, match="CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH is required"):
        shard.ProbeShardConfig.from_env(env)


def test_config_from_env_requires_caller_artifact_manifest_digest(tmp_path: Path):
    env = _env(tmp_path)
    env.pop("CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256")

    with pytest.raises(
        ValueError,
        match="CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256 is required",
    ):
        shard.ProbeShardConfig.from_env(env)


def test_config_from_env_rejects_malformed_artifact_manifest_digest(tmp_path: Path):
    with pytest.raises(RuntimeError, match="64 lowercase hexadecimal characters"):
        shard.ProbeShardConfig.from_env(
            _env(tmp_path, CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256="B" * 64)
        )


def test_config_from_env_rejects_remote_code_enablement(tmp_path: Path):
    with pytest.raises(ValueError, match="CAS_FLEET_TRUST_REMOTE_CODE must be false"):
        shard.ProbeShardConfig.from_env(
            _env(tmp_path, CAS_FLEET_TRUST_REMOTE_CODE="true")
        )


def test_load_scenarios_accepts_alpha_scenario_file(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(
        json.dumps(
            {
                "scenarios": [
                    {"id": "alpha_001", "prompt": "Should the assistant comply?"},
                    {"scenario_id": "alpha_002", "text": "Explain the safety issue."},
                ]
            }
        ),
        encoding="utf-8",
    )
    env = _env(tmp_path, CAS_FLEET_SCENARIO_PATH=str(scenario_path))
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    scenarios = shard.load_scenarios(config)

    assert [scenario.scenario_id for scenario in scenarios] == ["alpha_001", "alpha_002"]
    assert scenarios[0].prompt == "Should the assistant comply?"


def test_classify_outputs_does_not_fake_probe_or_cover_outputs():
    expected = (
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    )
    payload = {
        "activation_summary": [{"scenario_id": "alpha_001", "layers": []}],
    }

    produced, missing = shard.classify_outputs(expected, payload)

    assert produced == ["layer_activation_summary", "worker_evidence_manifest"]
    assert missing == ["cas_axis_readout", "blindspot_overlay"]


def test_compute_cas_axis_readout_requires_compatible_probe_weights(tmp_path: Path):
    weights_path = tmp_path / "probe.json"
    weights_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_probe_linear_v1",
                "probe_id": "tiny-test-probe",
                "axes": ["F1", "F2"],
                "weights": {
                    "F1": [1.0, 0.0],
                    "F2": [0.0, 1.0],
                },
                "bias": {"F1": 0.1, "F2": -0.1},
            }
        ),
        encoding="utf-8",
    )
    evidence = {
        "activation_summary": [
            {
                "layers": [
                    {
                        "top_neurons": [
                            {"index": 0, "abs_activation": 0.2},
                            {"index": 1, "abs_activation": 0.4},
                        ]
                    }
                ]
            }
        ]
    }

    readout = shard.compute_cas_axis_readout(
        evidence,
        shard.load_cas_probe_weights(weights_path),
    )

    assert readout["scores"] == {"F1": 0.3, "F2": 0.3}


def test_blindspot_cover_map_must_match_model_id(tmp_path: Path):
    cover_path = tmp_path / "covers.json"
    cover_path.write_text(
        json.dumps({"model_id": "other/model", "covers": []}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="model_id does not match"):
        shard.load_blindspot_cover_map(cover_path, model_id="EleutherAI/gpt-neox-20b")


def test_invalid_optional_proof_input_fails_before_model_allocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    cover_path = tmp_path / "covers.json"
    cover_path.write_text(
        json.dumps({"model_id": "other/model", "covers": []}),
        encoding="utf-8",
    )
    config = shard.ProbeShardConfig.from_env(
        _env(tmp_path, CAS_FLEET_COVER_MAP_PATH=str(cover_path))
    )
    model_load_called = False

    def _unexpected_model_load(_config):
        nonlocal model_load_called
        model_load_called = True
        raise AssertionError("model allocation must not start")

    monkeypatch.setattr(shard, "load_open_weight_model", _unexpected_model_load)
    with pytest.raises(RuntimeError, match="model_id does not match"):
        shard.run_probe_shard(config)
    assert model_load_called is False


def test_main_writes_failure_result_instead_of_faking_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    env = _env(tmp_path)
    result_path = Path(env["CAS_FLEET_RESULT_PATH"])
    monkeypatch.setattr(shard.os, "environ", env)
    monkeypatch.setattr(shard, "load_open_weight_model", lambda _config: (_ for _ in ()).throw(RuntimeError("no GPU")))

    assert shard.main() == 0
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["produced_outputs"] == []
    assert "no GPU" in payload["error_message"]
    assert payload["missing_outputs"] == [
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    ]


@pytest.mark.parametrize("requested", ["auto", "float16", "bfloat16", "float32"])
def test_resolve_torch_dtype_forces_cpu_float32(requested: str):
    torch = _FakeTorch(cuda_available=False)

    assert shard.resolve_torch_dtype(torch, requested, "auto") == torch.float32
    assert shard.resolve_torch_dtype(torch, requested, "cpu") == torch.float32


def test_resolve_torch_dtype_rejects_unavailable_cuda():
    torch = _FakeTorch(cuda_available=False)

    with pytest.raises(RuntimeError, match="CUDA device_map requested"):
        shard.resolve_torch_dtype(torch, "float16", "cuda:0")


def test_resolve_torch_dtype_preserves_gpu_selection():
    torch = _FakeTorch(cuda_available=True)

    assert shard.resolve_torch_dtype(torch, "auto", "cuda:0") is None
    assert shard.resolve_torch_dtype(torch, "float16", "cuda:0") == torch.float16


def test_validate_loaded_model_rejects_cpu_half_parameters():
    torch = _FakeTorch(cuda_available=False)
    model = _FakeModel([_FakeParameter(device="cpu", dtype=torch.float16)])

    with pytest.raises(RuntimeError, match="CPU parameters outside float32"):
        shard.validate_loaded_model_execution(torch, model)


def test_validate_loaded_model_accepts_cpu_float32_parameters():
    torch = _FakeTorch(cuda_available=False)
    model = _FakeModel([_FakeParameter(device="cpu", dtype=torch.float32)])

    shard.validate_loaded_model_execution(torch, model)


def test_require_finite_tensor_rejects_nonfinite_values():
    with pytest.raises(RuntimeError, match="model logits contains NaN or infinity"):
        shard.require_finite_tensor(_FakeTensor(finite=False), label="model logits")


def test_require_finite_tensor_accepts_finite_values():
    shard.require_finite_tensor(_FakeTensor(finite=True), label="model logits")
