from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "noetic-compass-scaffold/noetic-compass/api/services"
    / "cas_harness_pythia160m_layer_specificity_v4.py"
)
LOCK_PATH = (
    REPO_ROOT
    / "docs/working/research_intervention_pythia160m_v4"
    / "PYTHIA160M_RESEARCH_SUCCESSOR_LOCK_V4.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("pythia_v4_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lock_and_split(module):
    lock = module.load_json(LOCK_PATH)
    prompt_split = module.load_json(
        REPO_ROOT / lock["frozen_files"]["prompt_split"]["path"]
    )
    return lock, prompt_split


def _synthetic_packet(module, *, wrong_layer_ratio: float = 0.1):
    lock, prompt_split = _lock_and_split(module)
    plan = module.build_request_plan(lock, prompt_split)
    records = []
    for request in plan:
        row = dict(request)
        dose = float(row["dose"])
        condition = row["condition"]
        layer = row["effective_layer"]
        effect = 0.0
        if condition == "target_layer_direction":
            effect = dose
        elif condition == "off_target_layer_direction":
            effect = dose * (wrong_layer_ratio if layer == 2 else 0.05)
        elif condition == "layer2_projection_patchback":
            effect = dose * wrong_layer_ratio * 0.1
        elif condition in {
            "same_norm_random_direction",
            "wrong_token",
            "wrong_axis",
        }:
            effect = dose * 0.02
        row.update(
            {
                "final_readout_margin": (
                    1.0
                    if row["label"] == "^0|C"
                    else -1.0 if row["label"] == "^0|E" else 0.0
                ),
                "final_readout_margin_delta": effect,
                "downstream_logit_max_abs_delta": (
                    0.0
                    if condition
                    in {
                        "no_op",
                        "layer2_full_state_patchback",
                        "target_layer_full_state_patchback",
                    }
                    else abs(effect) * 0.01
                ),
                "finite_logits": True,
                "top1_preserved": True,
                "generated_tokens": 0,
            }
        )
        records.append(row)
    return lock, prompt_split, {"records": records}


def test_v4_lock_validates_model_free(monkeypatch):
    module = _load_module()
    monkeypatch.delenv(module.FEATURE_FLAG, raising=False)
    monkeypatch.delenv(module.LIVE_FLAG, raising=False)
    before = {name for name in ("torch", "transformers") if name in sys.modules}
    result = module.validate_v4_lock(REPO_ROOT, LOCK_PATH)
    after = {name for name in ("torch", "transformers") if name in sys.modules}
    assert result["status"] == "V4_MODEL_FREE_LOCK_VALIDATION_PASS / RUN_NOT_AUTHORIZED"
    assert result["request_count"] == 1536
    assert result["model_loads"] == 0
    assert result["output_writes"] == 0
    assert after == before


def test_v4_is_disabled_and_live_flag_fails_closed(monkeypatch):
    module = _load_module()
    monkeypatch.setenv(module.FEATURE_FLAG, "true")
    with pytest.raises(module.V4PreparationError, match="cannot execute"):
        module.assert_preparation_only()
    monkeypatch.delenv(module.FEATURE_FLAG, raising=False)
    monkeypatch.setenv(module.LIVE_FLAG, "true")
    with pytest.raises(module.V4PreparationError, match="Live research mode"):
        module.assert_preparation_only()


def test_request_plan_covers_every_layer_and_has_exact_cap():
    module = _load_module()
    lock, prompt_split = _lock_and_split(module)
    plan = module.build_request_plan(lock, prompt_split)
    assert len(plan) == lock["compute_cap"]["max_forward_passes"] == 1536
    heldout = [row for row in plan if row["split"] == "heldout"]
    first_id = heldout[0]["prompt_id"]
    first = [row for row in heldout if row["prompt_id"] == first_id]
    assert len(first) == 40
    compared_layers = {
        row["effective_layer"]
        for row in first
        if row["condition"] in {"target_layer_direction", "off_target_layer_direction"}
    }
    assert compared_layers == set(range(12))


def test_synthetic_localized_packet_passes_bounded_audit():
    module = _load_module()
    lock, prompt_split, packet = _synthetic_packet(module)
    result = module.audit_result_mapping(
        lock=lock, prompt_split=prompt_split, packet=packet
    )
    assert result["audit_status"] == "AUDIT_PASS_RESEARCH_ONLY"
    assert result["gates"]["layer_specificity"] is True
    assert (
        result["transport_diagnostic"]
        == "ADJACENT_TARGET_PROJECTION_MEDIATION_SUPPORTED_RESEARCH_ONLY"
    )
    assert result["transport_diagnostic_decision_authority"] == "NONE"


def test_synthetic_v3_like_wrong_layer_effect_fails_closed():
    module = _load_module()
    lock, prompt_split, packet = _synthetic_packet(
        module, wrong_layer_ratio=0.6146572083234787
    )
    result = module.audit_result_mapping(
        lock=lock, prompt_split=prompt_split, packet=packet
    )
    assert result["audit_status"] == "FAIL_CLOSED"
    assert result["gates"]["layer_specificity"] is False
    assert any(
        finding.startswith("LAYER_SPECIFICITY_") for finding in result["findings"]
    )


def test_v3_terminal_packet_is_hash_bound_and_not_modified():
    module = _load_module()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    for record in lock["preserved_v3_evidence"].values():
        path = REPO_ROOT / record["path"]
        assert path.stat().st_size == record["byte_count"]
        assert module.sha256_file(path) == record["sha256"]
