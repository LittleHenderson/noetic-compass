"""Authored synthetic tasks only; no held-out generation or neural execution."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SPEC = importlib.util.spec_from_file_location("record_order_adapter_tested", Path(__file__).with_name("check_records.py"))
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)
sys.path.insert(0, str(diagnostic.ROOT))
from cas_meta2.curriculum import parse_problem
from cas_meta2.curriculum_v2 import render_problem
from cas_meta2.executor import canonical


def fixture(order=("main", "p14", "p11")):
    procedures = {}
    for name, cjt, child in (("main", "A", "p14"), ("p14", "B", "p11"), ("p11", "C", None)):
        steps = [{"kind": "RUN", "cjt_id": cjt, "input": "arg", "output": "v0"}]
        if child:
            steps.append({"kind": "CALL", "procedure": child, "input": "v0", "output": "v1"})
        procedures[name] = {"input": "arg", "allowed_cjts": ["A", "B", "C"],
                            "steps": steps, "return": steps[-1]["output"]}
    program = {"schema": "cas-meta2-program/0.1", "entry": "main",
               "procedures": {name: procedures[name] for name in order}}
    public = {"problem": render_problem(program, "amber", [0, 0, 0, 0]),
              "observations": [{"slot": i, "tag": tag, "values": [0.1 * (i + 1)] * 8}
                               for i, tag in enumerate(("amber", "cobalt", "copper"))]}
    return {"task_id": "SYNTHETIC_ORDER_ONLY", "public": public,
            "target": {"binding": 0, "program": program}, "provenance": {"wording_combination": [0, 0, 0, 0]}}


@pytest.mark.parametrize("order", [("main", "p14", "p11"), ("main", "p11", "p14"), ("p11", "p14", "main")])
def test_forward_backward_definition_order_restores_without_changing_meaning(order):
    original = fixture(order)
    loaded = json.loads(json.dumps(original, sort_keys=True))
    before = canonical(loaded)
    restored, row = diagnostic.restore_public_definition_order(loaded)
    assert parse_problem(restored["public"]) == restored["target"]
    assert list(restored["target"]["program"]["procedures"]) == list(order)
    assert canonical(restored) == before == canonical(loaded)
    assert row["canonical_sha256_before"] == row["canonical_sha256_after"]
    assert render_problem(restored["target"]["program"], "amber", [0, 0, 0, 0]) == loaded["public"]["problem"]


def test_original_disk_and_in_memory_bytes_are_unchanged_and_result_is_detached(tmp_path):
    path = tmp_path / "synthetic_train.json"
    raw = json.dumps([fixture()], sort_keys=True, indent=2).encode()
    path.write_bytes(raw)
    tasks = json.loads(raw)
    presentation_before = json.dumps(tasks)
    restored, report = diagnostic.restore_dataset_order(tasks)
    assert report["affected_rows"] == 1 and report["task_count"] == 1
    assert report["canonical_sha256_before"] == report["canonical_sha256_after"]
    assert path.read_bytes() == raw and json.dumps(tasks) == presentation_before
    assert canonical(tasks) == canonical(restored)
    restored[0]["public"]["observations"][0]["values"][0] = 99
    assert tasks != restored and path.read_bytes() == raw


@pytest.mark.parametrize("change", ["meaning", "binding", "binding_type", "malformed_public"])
def test_semantic_changes_or_unrecognized_public_text_cannot_be_repaired(change):
    task = fixture()
    if change == "meaning":
        task["target"]["program"]["procedures"]["main"]["return"] = "v0"
    elif change == "binding":
        task["target"]["binding"] = 1
    elif change == "binding_type":
        task["target"]["binding"] = False
    else:
        task["public"]["problem"] += "\nUNSUPPORTED INSTRUCTION"
    before = deepcopy(task)
    with pytest.raises(ValueError):
        diagnostic.restore_public_definition_order(task)
    assert task == before


def test_matching_order_is_exact_noop_copy():
    task = fixture()
    restored, row = diagnostic.restore_public_definition_order(task)
    assert not row["changed_order"]
    assert restored == task and restored is not task
    assert json.dumps(restored) == json.dumps(task)


def test_adapter_is_limited_to_three_private_target_json_members():
    source = Path(diagnostic.__file__).read_text()
    assert 'for filename in ("train.json", "validation.json", "test_private.json")' in source
    assert 'value = stored.Extracted.json(self, name)' in source
    assert '"on_disk_bytes_changed": False' in source
    assert '"full_protocol_accepted": False' in source
    assert "CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED" in source
