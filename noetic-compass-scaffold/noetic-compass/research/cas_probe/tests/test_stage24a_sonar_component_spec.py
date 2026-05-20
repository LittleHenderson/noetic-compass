from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage24a = _load_module("stage24a_sonar_component_spec", ROOT / "stage24a_sonar_component_spec.py")


def test_stage24a_runs_sonar_before_component_attribution() -> None:
    payload = stage24a.stage24a_preregistration_payload()

    assert payload["execution_order"][:2] == [
        "sonar_token_signatures",
        "component_attribution_pilot",
    ]
    assert payload["tracks"][0]["name"] == "sonar_token_signatures"
    assert payload["tracks"][1]["name"] == "component_attribution_pilot"


def test_stage24a_is_locked_to_stage7_foundation_readout() -> None:
    payload = stage24a.stage24a_preregistration_payload()
    inputs = payload["required_inputs"]

    assert inputs["model"] == "EleutherAI/pythia-160m"
    assert inputs["fixture"] == "stage7_foundation_pilot_20260517.jsonl"
    assert inputs["locked_readout"] == {"name": "focus_token", "key": "X_focus", "layer": 6}
    assert inputs["foundation_classes"] == 28


def test_stage24a_defers_sae_and_forbids_exact_neuron_claims() -> None:
    payload = stage24a.stage24a_preregistration_payload()

    assert payload["sae_followup"]["status"] == "deferred_not_launch_blocker"
    assert payload["sae_followup"]["not_authorized_by_stage24a"] is True
    forbidden = "\n".join(
        claim
        for track in payload["tracks"]
        for claim in track["forbidden_claims"]
    )
    assert "exact monosemantic neurons" in forbidden
    assert "SAE" in forbidden


def test_stage24a_requires_random_controls_and_null_gates() -> None:
    payload = stage24a.stage24a_preregistration_payload()

    assert payload["required_inputs"]["random_controls_required"] is True
    assert payload["validation"] == {}
    for track in payload["tracks"]:
        assert track["pass_gate"]
        assert track["null_gate"]
        assert track["claim_if_null"]
