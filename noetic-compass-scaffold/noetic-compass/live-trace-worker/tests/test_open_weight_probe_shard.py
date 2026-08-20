"""Offline contract tests for the real open-weight probe-shard command."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_open_weight_probe_shard as shard  # noqa: E402


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    env = {
        "CAS_FLEET_MODEL_ID": "EleutherAI/gpt-neox-20b",
        "CAS_FLEET_MODEL_REVISION": "1" * 40,
        "CAS_FLEET_WORKER_ID": "probe-worker-001",
        "CAS_FLEET_AUDIT_ID": "cas-dist-large",
        "CAS_FLEET_JOB_ID": "fleet-job-001",
        "CAS_FLEET_LAYER_START": "0",
        "CAS_FLEET_LAYER_END": "3",
        "CAS_FLEET_SHARD_ID": "layers-000-003",
        "CAS_FLEET_ASSIGNED_METHODS_JSON": json.dumps(
            ["foundation_probe", "blindspot_detection"]
        ),
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
    }
    env.update(overrides)
    return env


def test_config_requires_prompt_or_scenario_path(tmp_path: Path):
    env = _env(tmp_path)
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    with pytest.raises(RuntimeError, match="CAS_FLEET_SCENARIO_PATH or CAS_FLEET_PROMPT"):
        shard.load_scenarios(config)


def test_scenario_parse_and_hash_use_same_byte_snapshot(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(
        '{"scenarios":[{"id":"original","prompt":"Original prompt"}]}',
        encoding="utf-8",
    )
    original = scenario_path.read_bytes()
    env = _env(tmp_path, CAS_FLEET_SCENARIO_PATH=str(scenario_path))
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    scenarios, snapshot = shard.load_scenarios_snapshot(
        config,
        after_read_hook=lambda: scenario_path.write_text(
            '{"scenarios":[{"id":"swapped","prompt":"Swapped prompt"}]}',
            encoding="utf-8",
        ),
    )

    assert [scenario.scenario_id for scenario in scenarios] == ["original"]
    assert snapshot["content_sha256"] == hashlib.sha256(original).hexdigest()
    assert snapshot["content_sha256"] != hashlib.sha256(scenario_path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("CAS_FLEET_MAX_SCENARIOS", "0", "at least 1"),
        ("CAS_FLEET_MAX_LENGTH", "0", "at least 1"),
        ("CAS_FLEET_TOP_K", "0", "at least 1"),
        ("CAS_FLEET_LAYER_START", "-1", "non-negative"),
    ],
)
def test_config_rejects_empty_or_invalid_capture_contract(
    tmp_path: Path, key: str, value: str, message: str
):
    with pytest.raises(ValueError, match=message):
        shard.ProbeShardConfig.from_env(_env(tmp_path, **{key: value}))


def test_config_rejects_unpinned_revision_and_remote_code(tmp_path: Path):
    with pytest.raises(ValueError, match="pinned lowercase"):
        shard.ProbeShardConfig.from_env(
            _env(tmp_path, CAS_FLEET_MODEL_REVISION="main")
        )
    with pytest.raises(ValueError, match="must remain false"):
        shard.ProbeShardConfig.from_env(
            _env(tmp_path, CAS_FLEET_TRUST_REMOTE_CODE="true")
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"CAS_FLEET_ASSIGNED_METHODS_JSON": "[]"}, "must not be empty"),
        ({"CAS_FLEET_EXPECTED_OUTPUTS_JSON": "[]"}, "must not be empty"),
        (
            {"CAS_FLEET_ASSIGNED_METHODS_JSON": '["foundation_probe","foundation_probe"]'},
            "must be unique",
        ),
        (
            {"CAS_FLEET_EXPECTED_OUTPUTS_JSON": '["worker_evidence_manifest"]'},
            "missing required base outputs",
        ),
        (
            {"CAS_FLEET_ASSIGNED_METHODS_JSON": '["foundation_probe"]'},
            "must be declared together",
        ),
    ],
)
def test_config_rejects_empty_duplicate_or_inconsistent_contracts(
    tmp_path: Path, overrides: dict[str, str], message: str
):
    with pytest.raises(ValueError, match=message):
        shard.ProbeShardConfig.from_env(_env(tmp_path, **overrides))


def test_layer_assignment_never_silently_truncates_requested_end():
    with pytest.raises(RuntimeError, match="layer_end 4 is outside"):
        shard.select_assigned_layers([object(), object()], 0, 4)


def test_blindspot_overlay_remains_disabled_without_admitted_typed_schema(
    tmp_path: Path,
):
    path = tmp_path / "cover.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "cas_blindspot_cover_map.v1",
                "model_id": "org/model",
                "model_revision": "1" * 40,
                "covers": [{"bogus": 1}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="blindspot_overlay is disabled"):
        shard.load_blindspot_cover_map(
            path,
            model_id="org/model",
            model_revision="1" * 40,
        )


@pytest.mark.parametrize("name", ["mlp", "ffn", "feed_forward"])
def test_capture_module_selection_supports_registered_architecture_names(name: str):
    class Hookable:
        def register_forward_hook(self, _callback):
            return None

    layer = type("Layer", (), {})()
    setattr(layer, name, Hookable())

    module, observed_name = shard.select_mlp_capture_module(layer)

    assert observed_name == name
    assert module is getattr(layer, name)


def test_capture_module_never_falls_back_to_whole_decoder_block():
    class HookableBlock:
        def register_forward_hook(self, _callback):
            return None

    with pytest.raises(RuntimeError, match="exactly one registered"):
        shard.select_mlp_capture_module(HookableBlock())


def test_classify_outputs_does_not_invent_probe_or_cover_outputs():
    expected = (
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    )
    payload = {
        "activation_summary": [
            {"scenario_id": "alpha_001", "layers": [{"layer": 0}]}
        ]
    }

    produced, missing = shard.classify_outputs(expected, payload)

    assert produced == ["layer_activation_summary", "worker_evidence_manifest"]
    assert missing == ["cas_axis_readout", "blindspot_overlay"]


def test_classify_outputs_rejects_empty_layer_rows():
    produced, missing = shard.classify_outputs(
        ("layer_activation_summary", "worker_evidence_manifest"),
        {"activation_summary": [{"scenario_id": "alpha_001", "layers": []}]},
    )

    assert produced == ["worker_evidence_manifest"]
    assert missing == ["layer_activation_summary"]


def test_legacy_probe_readout_rejects_lossy_top_k_magnitudes(tmp_path: Path):
    weights_path = tmp_path / "probe.json"
    weights_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_probe_linear_v1",
                "probe_id": "tiny-test-probe",
                "axes": ["F1"],
                "weights": {"F1": [1.0, 0.0]},
                "bias": {"F1": 0.1},
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
                            {"index": 8, "activation": -0.2, "abs_activation": 0.2},
                            {"index": 2, "activation": 0.4, "abs_activation": 0.4},
                        ]
                    }
                ]
            }
        ]
    }

    with pytest.raises(RuntimeError, match="lossy top-k diagnostic"):
        shard.compute_cas_axis_readout(evidence, weights_path)


def test_non_v1_probe_schema_is_not_silently_interpreted(tmp_path: Path):
    weights_path = tmp_path / "probe.json"
    weights_path.write_text(json.dumps({"schema_version": "unknown"}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema_version=cas_probe_linear_v1"):
        shard.compute_cas_axis_readout({"activation_summary": [{}]}, weights_path)


def test_main_writes_failure_result_instead_of_faking_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    env = _env(tmp_path)
    result_path = Path(env["CAS_FLEET_RESULT_PATH"])
    monkeypatch.setattr(shard.os, "environ", env)
    monkeypatch.setattr(
        shard,
        "load_open_weight_model",
        lambda _config: (_ for _ in ()).throw(RuntimeError("no GPU")),
    )

    assert shard.main() == 2
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert (
        payload["evidence_payload"]["schema_version"]
        == "cas_harness_open_weight_probe_shard.v2"
    )
    assert payload["produced_outputs"] == []
    assert "no GPU" in payload["error_message"]
    assert payload["missing_outputs"] == [
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    ]


def test_classify_outputs_rejects_unknown_output_name():
    with pytest.raises(RuntimeError, match="unsupported expected_outputs"):
        shard.classify_outputs(("invented_proof",), {"activation_summary": []})


def test_adapter_plan_is_required_before_hook_paths_can_run(tmp_path: Path):
    config = shard.ProbeShardConfig.from_env(_env(tmp_path))

    with pytest.raises(RuntimeError, match="CAS_FLEET_ADAPTER_PLAN_PATH is required"):
        shard.bind_adapter_plan(
            config=config,
            model=object(),
            model_info={},
            selected_layers=[],
        )


def test_worker_reverifies_and_consumes_exact_adapter_mlp_paths(tmp_path: Path):
    adapter, _source_sha256 = shard._load_adapter_verifier()

    class Hookable:
        def register_forward_hook(self, _callback):
            return None

    class Layer(Hookable):
        def __init__(self):
            self.attention = Hookable()
            self.mlp = Hookable()

    model = type("Model", (), {})()
    model.config = type(
        "Config",
        (),
        {
            "model_type": "gpt_neox",
            "num_hidden_layers": 2,
            "hidden_size": 16,
            "num_attention_heads": 4,
        },
    )()
    model.gpt_neox = type("NeoX", (), {"layers": [Layer(), Layer()]})()
    config_sha = "A" * 64
    weight_manifest_sha = "B" * 64
    plan = adapter.build_interpretability_adapter_plan(
        model=model,
        identity=adapter.ModelIdentity(
            model_id="EleutherAI/gpt-neox-20b",
            revision="1" * 40,
            config_sha256=config_sha,
            weights_manifest_sha256=weight_manifest_sha,
        ),
        declaration=adapter.ArchitectureDeclaration(
            model_type="gpt_neox",
            num_hidden_layers=2,
            hidden_size=16,
            num_attention_heads=4,
        ),
    )
    plan_path = tmp_path / "adapter-plan.json"
    plan_path.write_text(json.dumps(plan.to_dict()), encoding="utf-8")
    config = shard.ProbeShardConfig.from_env(
        _env(tmp_path, CAS_FLEET_ADAPTER_PLAN_PATH=str(plan_path))
    )
    model_info = {
        "model_type": "gpt_neox",
        "num_hidden_layers": 2,
        "hidden_size": 16,
        "num_attention_heads": 4,
        "normalized_config_payload_sha256": config_sha.lower(),
        "parameter_name_shape_dtype_manifest_sha256": weight_manifest_sha.lower(),
    }

    binding, hook_paths = shard.bind_adapter_plan(
        config=config,
        model=model,
        model_info=model_info,
        selected_layers=[(0, model.gpt_neox.layers[0]), (1, model.gpt_neox.layers[1])],
    )

    assert hook_paths == {0: "gpt_neox.layers.0.mlp", 1: "gpt_neox.layers.1.mlp"}
    assert binding["adapter_plan_sha256"] == plan.plan_sha256
    assert binding["binding_status"].endswith("SELECTED_HOOK_PATHS_VERIFIED")


def test_main_returns_nonzero_when_expected_outputs_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    env = _env(tmp_path)
    monkeypatch.setattr(shard.os, "environ", env)
    monkeypatch.setattr(
        shard,
        "run_probe_shard",
        lambda _config: {
            "produced_outputs": ["worker_evidence_manifest"],
            "missing_outputs": ["layer_activation_summary"],
            "error_message": None,
            "evidence_payload": {"schema_version": shard.SCHEMA_VERSION},
        },
    )

    assert shard.main() == 3
