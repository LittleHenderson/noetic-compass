"""Historical-rule regression tests; no model execution or historical mutation."""
import ast
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trusted_rescore as T

@pytest.fixture(scope="module")
def frozen_rule():
    tree = ast.parse(T.GRADER.read_text(encoding="utf-8"))
    names = {"binomial_upper_tail", "paired", "seed_test"}
    constants = {"ALPHA", "MIN_IMPROVED_KINDS", "MIN_IMPROVED_WORLDS"}
    selected = ast.Module(body=[n for n in tree.body if
        (isinstance(n, ast.FunctionDef) and n.name in names) or
        (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets))], type_ignores=[])
    namespace = {"Fraction": Fraction, "comb": math.comb}
    exec(compile(selected, str(T.GRADER), "exec"), namespace)
    assert namespace["ALPHA"] == Fraction(T.HISTORICAL_RULE["alpha"])
    return namespace["seed_test"]

@pytest.mark.parametrize("b,c", [(b, c) for b in range(19) for c in range(19-b)])
@pytest.mark.parametrize("kind_n,world_n", [(1,1),(1,2),(2,1),(2,2)])
def test_all_transition_cells_and_breadth_match_frozen_rule(frozen_rule, b, c, kind_n, world_n):
    keys = list(range(b+c))
    before = {i: i >= b for i in keys}
    after = {i: i < b for i in keys}
    kinds = {i: str(i % kind_n) for i in keys}
    worlds = {i: str(i % world_n) for i in keys}
    expected = frozen_rule(before, after, keys, kinds, worlds)
    actual = T.historical_seed_result(b, c, [kinds[i] for i in range(b)], [worlds[i] for i in range(b)])
    assert actual["passed"] is expected["passed"]
    assert actual["p_one_sided"] == expected["p_one_sided"]
    assert actual["kinds_improved"] == expected["improved_kinds"]
    assert actual["world_ids_improved"] == expected["improved_worlds"]

@pytest.mark.parametrize("directory,expected", [
    ("admission_helm1_certified", [True, True, True]),
    ("admission_001", [True, True, False]),
])
def test_all_preserved_run_results(directory, expected):
    gate = json.loads((HERE / directory / "gate_reading.json").read_text(encoding="utf-8"))
    observed = []
    for seed in ("20260917","20260918","20260919"):
        frozen = gate["seeds"][seed]["G_LEARN_population"]
        b,c = frozen["wrong_to_right"], frozen["right_to_wrong"]
        result = {"gained": b, "broken": c, **T.historical_seed_result(
            b,c,frozen["improved_kinds"],frozen["improved_worlds"])}
        assert T.compare_seed_result(frozen,result)["agree"]
        observed.append(result["passed"])
    assert observed == expected

@pytest.mark.parametrize("field,value", [
    ("passed", False), ("passed", 1), ("p_one_sided", "1/4096"),
    ("improved_kinds", ["reach"]), ("improved_worlds", ["world0"]),
    ("wrong_to_right", 12), ("right_to_wrong", 0),
])
def test_counts_and_overall_label_cannot_hide_seed_disagreement(field, value):
    result = {"gained":11, "broken":1, **T.historical_seed_result(11,1,["parts","reach"],["world0","world1"])}
    frozen = {"wrong_to_right":11,"right_to_wrong":1,"passed":True,"p_one_sided":"13/4096",
              "improved_kinds":["parts","reach"],"improved_worlds":["world0","world1"]}
    assert T.compare_seed_result(frozen,result)["agree"]
    frozen[field] = value
    assert not T.compare_seed_result(frozen,result)["agree"]

@pytest.mark.parametrize("missing", ["passed","p_one_sided","improved_kinds","improved_worlds"])
def test_missing_run_decision_evidence_is_not_agreement(missing):
    result = {"gained":11, "broken":1, **T.historical_seed_result(11,1,["parts","reach"],["world0","world1"])}
    frozen = {"wrong_to_right":11,"right_to_wrong":1,"passed":True,"p_one_sided":"13/4096",
              "improved_kinds":["parts","reach"],"improved_worlds":["world0","world1"]}
    del frozen[missing]
    assert not T.compare_seed_result(frozen,result)["agree"]

def test_new_anchor_metadata_names_original_rule():
    assert T.HISTORICAL_RULE["alpha"] == "1/100"
    assert T.HISTORICAL_RULE["zero_loss_veto"] is False
