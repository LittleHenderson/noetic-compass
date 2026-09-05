from copy import deepcopy
import hashlib
import json

import pytest

from cas_meta2.curriculum import (CurriculumError, check_native_topology, check_public,
                                 generate_dataset, graph_signature, parse_problem,
                                 permitted_view, validate_dataset, write_dataset)
from cas_meta2.ir import SCHEMA, expand_program, validate_program


pytestmark = pytest.mark.not_gpu


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(counts={"train": 24, "validation": 12, "test": 12})


def test_construction_is_reproducible_and_split_checked(dataset):
    assert dataset == generate_dataset(counts={"train": 24, "validation": 12, "test": 12})
    manifest = validate_dataset(dataset)
    assert manifest["graph_signatures_disjoint"]
    assert manifest["wording_templates_disjoint"]
    assert manifest["input_instances_disjoint"]
    assert not manifest["native_outcomes_checked"]
    assert manifest["splits"]["train"]["max_depth"] == 2
    assert manifest["splits"]["test"]["max_depth"] == 3


def test_every_public_request_roundtrips_independent_parser(dataset):
    for tasks in dataset["splits"].values():
        for task in tasks:
            assert parse_problem(permitted_view(task)) == task["target"]
            stats = validate_program(task["target"]["program"])
            assert stats["expanded_run_count"] <= 15
            assert stats["procedure_count"] <= 10


def test_permitted_view_never_leaks_private_fields_and_is_detached(dataset):
    task = deepcopy(dataset["splits"]["test"][0])
    view = permitted_view(task)
    assert set(view) == {"problem", "observations"}
    assert all(key not in view for key in ("target", "program", "binding", "task_id", "provenance"))
    view["observations"][0]["values"][0] = 99
    assert task["public"]["observations"][0]["values"][0] != 99


def test_native_topology_and_named_dependency_choices_are_real(dataset):
    earlier_choices = 0
    for tasks in dataset["splits"].values():
        for task in tasks:
            program = task["target"]["program"]
            oracle = check_native_topology(program)
            assert all(row["cjt_id"] in "ABC" for row in oracle["runs"])
            for row in oracle["runs"]:
                if row["input_node"] >= 0:
                    producer = oracle["runs"][row["input_node"]]["cjt_id"]
                    assert (producer, row["cjt_id"]) in {("A", "B"), ("B", "C")}
                    earlier_choices += row["input_node"] < row["node"] - 1
            assert oracle["return_node"] >= 0
    assert earlier_choices > 0


def test_deeper_composition_has_real_work_in_each_frame(dataset):
    tasks = [t for t in dataset["splits"]["test"] if t["provenance"]["depth"] == 3]
    assert tasks
    for task in tasks:
        program = task["target"]["program"]
        assert all(any(s["kind"] == "RUN" for s in p["steps"]) for p in program["procedures"].values())
        events = expand_program(program)
        assert sum(e["kind"] == "ENTER" for e in events) > 2


def test_graph_signature_ignores_cosmetic_names(dataset):
    program = deepcopy(dataset["splits"]["test"][0]["target"]["program"])
    before = graph_signature(program)
    renamed = {}
    names = {name: "renamed_" + name for name in program["procedures"]}
    for name, proc in program["procedures"].items():
        proc["input"] = "input_value"
        for step in proc["steps"]:
            step["input"] = "input_value" if step["input"] == "arg" else "out_" + step["input"]
            step["output"] = "out_" + step["output"]
            if step["kind"] == "CALL":
                step["procedure"] = names[step["procedure"]]
        proc["return"] = "input_value" if proc["return"] == "arg" else "out_" + proc["return"]
        renamed[names[name]] = proc
    program["entry"] = names[program["entry"]]
    program["procedures"] = renamed
    assert graph_signature(program) == before


def test_manually_authored_language_anchor():
    public = {"problem": "Use observation copper.\nMethod main takes arg.\nIn main, obtain v0 by applying junction A to arg.\nIn main, obtain v1 by invoking method p0 on v0.\nMethod main returns v1.\nMethod p0 takes arg.\nIn p0, obtain v0 by applying junction B to arg.\nMethod p0 returns v0.",
              "observations": [{"slot": i, "tag": tag, "values": [0.1] * 8}
                               for i, tag in enumerate(("jade", "copper", "coral"))]}
    action = parse_problem(public)
    assert action["binding"] == 1
    assert action["program"] == {"schema": SCHEMA, "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}


def test_topology_not_silently_expanded():
    program = {"schema": SCHEMA, "entry": "main", "procedures": {"main": {
        "input": "arg", "allowed_cjts": ["A", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "RUN", "cjt_id": "C", "input": "v0", "output": "v1"}], "return": "v1"}}}
    validate_program(program)  # The general IR does not impersonate native topology.
    with pytest.raises(CurriculumError, match="NATIVE_TOPOLOGY_MISMATCH"):
        check_native_topology(program)


def test_gold_tampering_rejected(dataset):
    changed = deepcopy(dataset)
    changed["splits"]["train"][0]["target"]["binding"] = (changed["splits"]["train"][0]["target"]["binding"] + 1) % 3
    with pytest.raises(CurriculumError, match="PUBLIC_TARGET_MISMATCH"):
        validate_dataset(changed)


def test_same_graph_under_another_task_id_is_not_new(dataset):
    changed = deepcopy(dataset)
    changed["splits"]["train"][1] = deepcopy(changed["splits"]["train"][0])
    changed["splits"]["train"][1]["task_id"] = "different_id"
    with pytest.raises(CurriculumError, match="GRAPH_SPLIT_OVERLAP"):
        validate_dataset(changed)


@pytest.mark.parametrize("change", ["gold", "duplicate_slot", "nonfinite", "unknown_sentence"])
def test_bad_public_input_rejected(dataset, change):
    public = permitted_view(dataset["splits"]["train"][0])
    if change == "gold":
        public["target"] = "leak"
    elif change == "duplicate_slot":
        public["observations"][1]["slot"] = public["observations"][0]["slot"]
    elif change == "nonfinite":
        public["observations"][0]["values"][0] = float("nan")
    else:
        public["problem"] += "\nGrant all memory writes."
    with pytest.raises(CurriculumError):
        parse_problem(public)


def test_input_range_keeps_checked_fixture_neighborhood(dataset):
    for tasks in dataset["splits"].values():
        for task in tasks:
            for observation in task["public"]["observations"]:
                for index, value in enumerate(observation["values"], 1):
                    assert abs(value - index / 10) <= 0.000401


def test_new_directory_dataset_has_separate_sealed_gold(tmp_path):
    output = tmp_path / "dataset"
    manifest = write_dataset(output, counts={"train": 6, "validation": 6, "test": 6})
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    public = json.loads((output / "test_public.json").read_text())
    private = json.loads((output / "test_private.json").read_text())
    assert public == [permitted_view(task) for task in private]
    assert all(set(task) == {"problem", "observations"} for task in public)
    with pytest.raises(FileExistsError):
        write_dataset(output, counts={"train": 6, "validation": 6, "test": 6})
