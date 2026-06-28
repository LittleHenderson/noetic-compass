from __future__ import annotations

from app.runtime.probe_runner import resolve_runtime_config
from app.runtime.pythia_runner import build_pythia_runtime_plan
from app.schemas.requests import CreateSessionRequest


def _dump(client, method_configs: dict, *, seed: int = 1) -> list[dict]:
    r = client.post(
        "/sessions/dump",
        json={
            "prompt": "alpha beta gamma",
            "seed": seed,
            "max_new_tokens": 2,
            "method_configs": method_configs,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["events"]


def _first_token(events: list[dict]) -> dict:
    return next(e for e in events if e["type"] == "token")


def test_foundation_probe_layer_range_and_top_k_change_token_activations(client):
    events = _dump(
        client,
        {
            "foundation_probe": {
                "enabled": True,
                "knobs": {"layer_range": ["2"], "top_k": 3},
            },
            "rpm_gate_check": {"enabled": False},
            "blindspot_detection": {"enabled": False},
            "verification_stack": {"enabled": False},
        },
    )

    token = _first_token(events)
    assert len(token["top_activated_neurons"]) == 3
    assert {n["layer"] for n in token["top_activated_neurons"]} == {2}
    assert len(token["foundation_probe"]) == 7


def test_rpm_strictness_and_attention_knobs_change_runtime_payload(client):
    loose = _first_token(
        _dump(
            client,
            {
                "foundation_probe": {"enabled": False},
                "rpm_gate_check": {
                    "enabled": True,
                    "knobs": {"strictness_threshold": 0.0, "emit_attention": True},
                },
                "blindspot_detection": {"enabled": False},
                "verification_stack": {"enabled": False},
            },
        )
    )
    strict = _first_token(
        _dump(
            client,
            {
                "foundation_probe": {"enabled": False},
                "rpm_gate_check": {
                    "enabled": True,
                    "knobs": {"strictness_threshold": 1.0, "emit_attention": False},
                },
                "blindspot_detection": {"enabled": False},
                "verification_stack": {"enabled": False},
            },
        )
    )

    assert loose["rpm_gate_check"]["passed"] is True
    assert loose["rpm_gate_check"]["attention_summary"]
    assert strict["rpm_gate_check"]["passed"] is False
    assert strict["rpm_gate_check"]["attention_summary"] is None


def test_blindspot_scope_drive_and_layer_range_change_covers(client):
    unfiltered_events = _dump(
        client,
        {
            "foundation_probe": {"enabled": False},
            "rpm_gate_check": {"enabled": False},
            "blindspot_detection": {
                "enabled": True,
                "knobs": {"scope": "one_drive", "drive": "F1", "layer_range": []},
            },
            "verification_stack": {"enabled": False},
        },
    )
    unfiltered = next(e for e in unfiltered_events if e["type"] == "neuron_covers")[
        "per_class_neuron_covers"
    ]
    assert set(unfiltered)
    assert all(class_id.startswith("F1") for class_id in unfiltered)

    first_label = next(label for labels in unfiltered.values() for label in labels)
    selected_layer = first_label.split("N", 1)[0].removeprefix("L")

    events = _dump(
        client,
        {
            "foundation_probe": {"enabled": False},
            "rpm_gate_check": {"enabled": False},
            "blindspot_detection": {
                "enabled": True,
                "knobs": {
                    "scope": "one_drive",
                    "drive": "F1",
                    "layer_range": [selected_layer],
                },
            },
            "verification_stack": {"enabled": False},
        },
    )

    covers = next(e for e in events if e["type"] == "neuron_covers")[
        "per_class_neuron_covers"
    ]
    assert set(covers)
    assert all(class_id.startswith("F1") for class_id in covers)
    assert {
        int(label.split("N", 1)[0].removeprefix("L"))
        for labels in covers.values()
        for label in labels
    } == {int(selected_layer)}


def test_verification_mode_changes_token_verdict_threshold(client):
    high_precision = _first_token(
        _dump(
            client,
            {
                "foundation_probe": {"enabled": False},
                "rpm_gate_check": {"enabled": False},
                "blindspot_detection": {"enabled": False},
                "verification_stack": {
                    "enabled": True,
                    "knobs": {"mode": "HIGH_PRECISION"},
                },
            },
            seed=1,
        )
    )
    coverage = _first_token(
        _dump(
            client,
            {
                "foundation_probe": {"enabled": False},
                "rpm_gate_check": {"enabled": False},
                "blindspot_detection": {"enabled": False},
                "verification_stack": {
                    "enabled": True,
                    "knobs": {"mode": "MAX_COVERAGE_TRIAGE"},
                },
            },
            seed=1,
        )
    )

    assert high_precision["confidence"] == coverage["confidence"]
    assert high_precision["verification_stack"]["mode"] == "HIGH_PRECISION"
    assert high_precision["verification_stack"]["verdict"] == "SUPPRESS"
    assert coverage["verification_stack"]["mode"] == "MAX_COVERAGE_TRIAGE"
    assert coverage["verification_stack"]["verdict"] == "ACCEPT"


def test_probe_and_pythia_plans_resolve_same_runtime_knobs():
    req = CreateSessionRequest(
        prompt="hi",
        method_configs={
            "foundation_probe": {
                "enabled": True,
                "knobs": {"layer_range": ["1", "3"], "top_k": 5},
            },
            "verification_stack": {
                "enabled": True,
                "knobs": {"mode": "HIGH_PRECISION"},
            },
        },
    )

    probe_plan = resolve_runtime_config(req.method_configs, n_layers=12)
    pythia_plan = build_pythia_runtime_plan(req)

    assert probe_plan.foundation_layer_range == (1, 3)
    assert pythia_plan.foundation_layer_range == (1, 3)
    assert pythia_plan.foundation_top_k == 5
    assert pythia_plan.verification_mode == "HIGH_PRECISION"
