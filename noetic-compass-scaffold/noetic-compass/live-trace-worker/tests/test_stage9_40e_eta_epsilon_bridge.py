from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_stage9_40e_eta_epsilon_bridge.py"
)
SPEC = importlib.util.spec_from_file_location("run_stage9_40e_eta_epsilon_bridge", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)


def _scenario_payload() -> dict:
    return {
        "schema_version": "fixture",
        "scenarios": [
            {
                "id": "pair1_A",
                "prompt": "A is mental mind; B is mental positive. Focus: A.",
                "expected_cas_axes": {"element": "^1|C", "operator": "^1", "domain": "C"},
                "metadata": {
                    "counterfactual_pair_id": "pair1",
                    "split": "test",
                    "pair_kind": "fixture",
                    "paraphrase_family": "fixture",
                },
            },
            {
                "id": "pair1_B",
                "prompt": "A is mental mind; B is mental positive. Focus: B.",
                "expected_cas_axes": {"element": "^2|C", "operator": "^2", "domain": "C"},
                "metadata": {
                    "counterfactual_pair_id": "pair1",
                    "split": "test",
                    "pair_kind": "fixture",
                    "paraphrase_family": "fixture",
                },
            },
            {
                "id": "pair2_A",
                "prompt": "A is spiritual idea; B is physical rhythm. Focus: A.",
                "expected_cas_axes": {"element": "^0|P", "operator": "^0", "domain": "P"},
                "metadata": {
                    "counterfactual_pair_id": "pair2",
                    "split": "train",
                    "pair_kind": "fixture",
                    "paraphrase_family": "fixture",
                },
            },
            {
                "id": "pair2_B",
                "prompt": "A is spiritual idea; B is physical rhythm. Focus: B.",
                "expected_cas_axes": {"element": "^7|O", "operator": "^7", "domain": "O"},
                "metadata": {
                    "counterfactual_pair_id": "pair2",
                    "split": "val",
                    "pair_kind": "fixture",
                    "paraphrase_family": "fixture",
                },
            },
        ],
    }


def test_stage9_meta_links_counterfactual_partner(tmp_path: Path):
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(_scenario_payload()), encoding="utf-8")

    meta = bridge.load_stage9_scenario_meta(path)

    assert meta["pair1_A"].element == "^1|C"
    assert meta["pair1_A"].partner_element == "^2|C"
    assert meta["pair1_B"].element == "^2|C"
    assert meta["pair1_B"].partner_element == "^1|C"


def test_split_from_scenario_meta_requires_all_fixed_splits(tmp_path: Path):
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(_scenario_payload()), encoding="utf-8")
    meta = bridge.load_stage9_scenario_meta(path)

    split = bridge.split_from_scenario_meta(
        np.asarray(["pair1_A", "pair1_B", "pair2_A", "pair2_B"], dtype=str),
        meta,
    )

    assert split["test"].tolist() == [0, 1]
    assert split["train"].tolist() == [2]
    assert split["val"].tolist() == [3]


def test_readable_prefix_uses_40e_operator_and_domain_language():
    prefix = bridge.readable_prefix("^1|C")

    assert "Element code: ^1|C" in prefix
    assert "Operator: Mind" in prefix
    assert "Domain: Mental" in prefix
    assert "mental mind" in bridge.element_phrase("^1|C")


def test_condition_prefix_keeps_raw_symbol_control_distinct():
    raw = bridge.condition_prefix("probe_raw", "^1|C", "^2|C", "^3|C")
    readable = bridge.condition_prefix("probe_readable", "^1|C", "^2|C", "^3|C")

    assert raw == "CAS 40E frame: ^2|C.\n"
    assert "CAS 40-Element realization frame" in readable
    assert "^2|C" in readable
    assert raw != readable


def test_canonical_element_rejects_bad_labels():
    assert bridge.canonical_element("^0|P") == "^0|P"
    assert bridge.canonical_element("^10|P") == ""
    assert bridge.canonical_element("^1|X") == ""
    with pytest.raises(ValueError):
        bridge.parse_element_label("^1|X")
