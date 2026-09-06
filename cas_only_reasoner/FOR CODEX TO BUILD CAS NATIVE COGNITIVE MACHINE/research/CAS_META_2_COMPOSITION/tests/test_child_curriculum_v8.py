"""Pure construction/public-meaning checks; no native/neural/provider work."""
from collections import Counter
from copy import deepcopy
import math
import struct
import sys

import pytest

from cas_meta2 import child_curriculum_v8 as curriculum, codec, grammar_v3
from cas_meta2.curriculum import graph_signature
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.features_v3 import encode_public_with_spans
from cas_meta2.ir import validate_program
from cas_meta2.native import admit_action


@pytest.fixture(scope="module")
def dataset():
    return curriculum.generate_dataset()


def _changed(dataset):
    changed = deepcopy(dataset)
    changed.pop("manifest")
    return changed


def test_import_and_generation_do_not_load_neural_or_provider_modules(dataset):
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(
        name.split(".")[0] for name in sys.modules)
    assert not dataset["manifest"]["native_outcomes_checked"]
    assert not dataset["manifest"]["training_allowed_by_this_package"]


def test_exact_counts_depths_and_independent_context_denominators(dataset):
    report = curriculum.validate_dataset(dataset)
    assert {split: len(tasks) for split, tasks in dataset["splits"].items()} == curriculum.COUNTS
    assert {split: row["independent_context_groups"] for split, row in report["splits"].items()} == curriculum.GROUP_COUNTS
    assert report["independent_observation_context_count"] == 112
    assert report["unique_float32_observation_payload_count"] == 336
    for split, count in curriculum.COUNTS.items():
        assert report["splits"][split]["depth_counts"] == {"2": count}
    assert report["splits"]["train"]["combination_counts"] == {"B_C": 64, "B_CR": 64, "R_C": 64}
    assert report["splits"]["validation"]["combination_counts"] == {"B_C": 24, "B_CR": 24, "R_C": 24}
    assert report["splits"]["test"]["combination_counts"] == {"B_C": 8, "B_CR": 8, "R_C": 8, "R_CR": 24}


def test_fresh_graph_and_unseen_combination_are_separate_claims(dataset):
    report = dataset["manifest"]
    assert report["held_out_unseen_to"] == ["training", "validation"]
    assert report["held_out_not_unseen_to"] == ["builder", "runtime_development_qualification"]
    assert report["familiar_graph_overlap_intentional"]
    assert not report["validation_unseen_combinations"]
    assert report["splits"]["test"]["evaluation_target_counts"] == {
        "fresh_instances_familiar_graphs": 24, "unseen_composition": 24}
    signatures = {split: {graph_signature(t["target"]["program"]) for t in tasks}
                  for split, tasks in dataset["splits"].items()}
    assert signatures["train"] == signatures["validation"]
    assert len(signatures["test"] - signatures["train"]) == 1


def test_every_public_task_reconstructs_its_prior_formal_target(dataset):
    for tasks in dataset["splits"].values():
        for task in tasks:
            assert curriculum.parse_problem(task["public"]) == task["target"]
            assert curriculum.validate_task(task) is task
            assert task["provenance"]["target_source"] == "formal_public_constraints"


def test_rule_gets_only_public_not_target_ids_seed_or_provenance(dataset):
    public = dataset["splits"]["train"][0]["public"]
    assert set(public) == {"problem", "observations"}
    for key in ("target", "task_id", "seed", "provenance"):
        with pytest.raises(ValueError):
            curriculum.parse_problem({**public, key: "not permitted"})
    with pytest.raises(ValueError):
        curriculum.parse_problem(dataset["splits"]["train"][0])


def test_public_has_both_children_full_input_scope_no_selected_call():
    task = curriculum.qualification_tasks()[0]
    text = task["public"]["problem"]
    info = curriculum._read_public(task["public"])
    names, children = info["parent_names"], info["child_names"]
    assert all(f"Child {child}:" in text for child in children)
    assert "Available CALL inputs: " + ", ".join(["arg", *names[:4]]) in text
    assert "Available parent returns: " + ", ".join(["arg", *names]) in text
    assert '"kind": "CALL"' not in text and '"procedures"' not in text
    assert "second committed prelude result" in text
    assert "authored" in text and "not new numerical meanings" in text


def test_qualification_tasks_are_development_only_and_share_context():
    tasks = curriculum.qualification_tasks()
    assert tasks == curriculum.qualification_tasks()
    assert len(tasks) == 4
    assert [t["provenance"]["combination"] for t in tasks] == list(curriculum.COMBINATIONS)
    assert len({codec.canonical_sha256(t["public"]["observations"]) for t in tasks}) == 1
    assert len({t["public"]["problem"] for t in tasks}) == 4
    assert all(t["target"]["binding"] == 0 and t["provenance"]["split"] == "qualification" for t in tasks)
    assert all(t["provenance"]["evaluation_target"] == "development_native_qualification" for t in tasks)
    assert [validate_program(t["target"]["program"])["expanded_run_count"] for t in tasks] == [5, 6, 5, 6]


def test_all_four_panel_choices_remain_available_regardless_of_requested_answer():
    tasks = curriculum.qualification_tasks()
    panels = [curriculum.candidate_choices(t["public"]) for t in tasks]
    assert all(panel == panels[0] for panel in panels)
    for task in tasks:
        actions = [curriculum.compile_candidate(task["public"], choice) for choice in panels[0]]
        assert sum(action == task["target"] for action in actions) == 1
        assert len({graph_signature(action["program"]) for action in actions}) == 4
        for action in actions:
            admit_action(task["public"], action)


def test_compiler_preserves_wrong_binding_and_full_scope_not_a_gold_mask():
    task = curriculum.qualification_tasks()[0]
    info = curriculum._read_public(task["public"])
    choice = curriculum.candidate_choices(task["public"])[0]
    wrong_binding = curriculum.compile_candidate(task["public"], {**choice, "binding": 2})
    assert wrong_binding["binding"] == 2 != task["target"]["binding"]
    wrong_return = curriculum.compile_candidate(task["public"], {**choice, "return": info["parent_names"][0]})
    assert wrong_return["program"]["procedures"]["main"]["return"] == info["parent_names"][0]
    arg_input = curriculum.compile_candidate(task["public"], {**choice, "input": "arg"})
    assert arg_input["program"]["procedures"]["main"]["steps"][-1]["input"] == "arg"
    invalid_edge = curriculum.compile_candidate(task["public"], {**choice, "input": info["parent_names"][0]})
    with pytest.raises(ValueError, match="NATIVE_TOPOLOGY_MISMATCH"):
        admit_action(task["public"], invalid_edge)


def test_b_r_request_changes_only_call_input_not_the_prelude_or_child():
    left, _, right, _ = curriculum.qualification_tasks()
    a, b = deepcopy(left["target"]), right["target"]
    astep = a["program"]["procedures"]["main"]["steps"][-1]
    bstep = b["program"]["procedures"]["main"]["steps"][-1]
    assert astep["input"] != bstep["input"]
    astep["input"] = bstep["input"]
    assert a == b
    assert left["public"]["problem"].replace("second committed", "fourth committed") == right["public"]["problem"]


def test_child_request_changes_actual_cjt_sequence_not_an_alias():
    short, long, _, _ = curriculum.qualification_tasks()
    for task, sequence in ((short, ["C"]), (long, ["C", "R"])):
        program = task["target"]["program"]
        child = program["procedures"]["main"]["steps"][-1]["procedure"]
        assert set(program["procedures"]) == {"main", child}
        assert [step["cjt_id"] for step in program["procedures"][child]["steps"]] == sequence
    assert short["public"]["problem"].replace("desired authored child label is L2", "desired authored child label is L1") == long["public"]["problem"]


def test_public_catalog_parser_does_not_share_renderer_acceptance(monkeypatch):
    task = curriculum.qualification_tasks()[0]
    monkeypatch.setattr(curriculum, "_catalog_line", lambda name, kind: f"Child {name}: BROKEN RENDERER.")
    assert curriculum.parse_problem(task["public"]) == task["target"]
    with pytest.raises(ValueError, match="CHILD_CATALOG_INVALID"):
        curriculum.qualification_tasks()


@pytest.mark.parametrize("old,new", [
    ("C(arg)->v0; RETURN v0; authored result L2", "B(arg)->v0; RETURN v0; authored result L2"),
    ("R(v0)->v1; RETURN v1", "R(arg)->v1; RETURN v1"),
    ("R(v0)->v1; RETURN v1", "R(v0)->v1; RETURN v0"),
    ("RETURN v0; authored result L2", "RETURN v0; authored result L1"),
])
def test_actual_public_catalog_steps_return_and_label_are_checked(old, new):
    public = deepcopy(curriculum.qualification_tasks()[0]["public"])
    assert old in public["problem"]
    public["problem"] = public["problem"].replace(old, new)
    with pytest.raises(ValueError, match="CHILD_CATALOG_INVALID"):
        curriculum.parse_problem(public)


def test_parent_return_is_disclosed_fixed_not_a_learning_discrimination(dataset):
    assert dataset["manifest"]["learned_choices"] == ["observation_binding", "child_selection", "child_input_source"]
    assert dataset["manifest"]["parent_return"] == "fixed_child_call_output_not_a_varied_learning_target"
    for tasks in dataset["splits"].values():
        for task in tasks:
            main = task["target"]["program"]["procedures"]["main"]
            assert main["return"] == main["steps"][-1]["output"]


def test_names_catalog_order_tags_and_observation_order_vary(dataset):
    for split, tasks in dataset["splits"].items():
        infos = [curriculum._read_public(t["public"]) for t in tasks]
        assert {info["reverse_catalog"] for info in infos} == {False, True}
        assert len({info["parent_names"] for info in infos}) == curriculum.GROUP_COUNTS[split]
        assert len({info["child_names"] for info in infos}) > 10
        assert {t["target"]["binding"] for t in tasks} == {0, 1, 2}
        assert len({tuple(row["slot"] for row in t["public"]["observations"]) for t in tasks}) > 1
        assert len({next(row["tag"] for row in t["public"]["observations"] if row["slot"] == t["target"]["binding"])
                    for t in tasks}) == 8


def test_float32_payloads_reused_only_within_context_not_across_groups_or_splits(dataset):
    owners = {}
    for split, tasks in dataset["splits"].items():
        for task in tasks:
            owner = (split, task["provenance"]["group_id"])
            for row in task["public"]["observations"]:
                key = struct.pack("<8f", *row["values"])
                assert owners.setdefault(key, owner) == owner
    assert len(owners) == 112 * 3
    qualification = {struct.pack("<8f", *row["values"]) for row in curriculum.qualification_tasks()[0]["public"]["observations"]}
    assert not qualification.intersection(owners)


def test_frozen_grammar_and_lossless_copy_encoder_need_no_changes(dataset):
    tokenizer = LosslessPublicTokenizer.fit_train([t["public"] for t in dataset["splits"]["train"]], max_length=1024)
    lengths = set()
    for tasks in dataset["splits"].values():
        for task in tasks:
            encoded = encode_public_with_spans(task["public"], tokenizer)
            assert encoded
            ids = codec.action_to_ids(task["target"], max_length=256)
            state = grammar_v3.GrammarState(max_length=256)
            for token in ids:
                state = state.advance_id(token)
            assert state.complete and state.to_action() == task["target"]
            lengths.add(len(ids))
    assert lengths == {49, 53}


def test_observation_selection_follows_tag_not_list_position():
    task = curriculum.qualification_tasks()[0]
    public = deepcopy(task["public"])
    public["observations"].reverse()
    assert curriculum.parse_problem(public) == task["target"]
    tag0 = next(row["tag"] for row in public["observations"] if row["slot"] == 0)
    tag2 = next(row["tag"] for row in public["observations"] if row["slot"] == 2)
    public["problem"] = public["problem"].replace("observation " + tag0, "observation " + tag2)
    changed = curriculum.parse_problem(public)
    assert changed["binding"] == 2 and changed["program"] == task["target"]["program"]


@pytest.mark.parametrize("old,new", [
    ("second committed", "third committed"),
    ("authored child label is L2", "authored child label is L9"),
    ("ONE-CHILD TASK / 8", "ONE-CHILD TASK / 9"),
    ("Available CALL inputs: arg,", "Available CALL inputs:"),
    ("Parent return: the child CALL output.", "Parent return: the first result."),
])
def test_unsupported_or_incomplete_public_contract_is_rejected(old, new):
    public = deepcopy(curriculum.qualification_tasks()[0]["public"])
    assert old in public["problem"]
    public["problem"] = public["problem"].replace(old, new)
    with pytest.raises(ValueError):
        curriculum.parse_problem(public)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "0.1"])
def test_nonfinite_or_non_numeric_observation_is_rejected(value):
    public = deepcopy(curriculum.qualification_tasks()[0]["public"])
    public["observations"][0]["values"][0] = value
    with pytest.raises(ValueError):
        curriculum.parse_problem(public)


def test_float64_distinct_but_float32_aliased_observations_rejected():
    public = deepcopy(curriculum.qualification_tasks()[0]["public"])
    public["observations"][1]["values"] = [v + 1e-13 for v in public["observations"][0]["values"]]
    with pytest.raises(ValueError, match="FLOAT32_ALIASED"):
        curriculum.parse_problem(public)


def test_wrong_formal_target_rejected_without_native_execution():
    left, _, right, _ = curriculum.qualification_tasks()
    left["target"] = right["target"]
    with pytest.raises(ValueError, match="PUBLIC_TARGET_MISMATCH"):
        curriculum.validate_task(left)


@pytest.mark.parametrize("key,value", [("native_outcomes_checked", True), ("depth", 3),
    ("target_source", "stored_record"), ("combination", "R_CR"), ("evaluation_target", "arithmetic_reasoning")])
def test_unearned_or_wrong_provenance_rejected(key, value):
    task = curriculum.qualification_tasks()[0]
    task["provenance"][key] = value
    with pytest.raises(ValueError):
        curriculum.validate_task(task)


def test_bad_manifest_duplicate_task_and_count_rejected(dataset):
    changed = deepcopy(dataset)
    changed["manifest"]["native_outcomes_checked"] = True
    with pytest.raises(ValueError, match="STORED_MANIFEST_MISMATCH"):
        curriculum.validate_dataset(changed)
    changed = _changed(dataset)
    changed["splits"]["train"][1] = deepcopy(changed["splits"]["train"][0])
    with pytest.raises(ValueError, match="DUPLICATE_TASK_OR_PUBLIC"):
        curriculum.validate_dataset(changed)
    changed = _changed(dataset)
    changed["splits"]["test"].pop()
    with pytest.raises(ValueError, match="SPLIT_COUNTS_CHANGED"):
        curriculum.validate_dataset(changed)


def test_cross_split_input_reuse_rejected_even_with_new_names_and_requests(dataset):
    changed = _changed(dataset)
    source = changed["splits"]["train"][0]["public"]["observations"][0]["values"]
    task = changed["splits"]["validation"][0]
    task["public"]["observations"][0]["values"] = deepcopy(source)
    with pytest.raises(ValueError, match="INPUT_CROSS_GROUP_OR_SPLIT_REUSE"):
        curriculum.validate_dataset(changed)


def test_group_context_change_and_wrong_group_assignment_rejected(dataset):
    changed = _changed(dataset)
    task = changed["splits"]["train"][0]
    group = task["provenance"]["group_id"]
    later = next(t for t in changed["splits"]["train"][1:] if t["provenance"]["group_id"] == group)
    later["public"]["observations"].reverse()
    with pytest.raises(ValueError, match="GROUP_CONTEXT_CHANGED"):
        curriculum.validate_dataset(changed)


def test_out_of_neighborhood_values_are_not_silently_claimed_qualified(dataset):
    changed = _changed(dataset)
    changed["splits"]["train"][0]["public"]["observations"][0]["values"][0] = 0.2
    with pytest.raises(ValueError, match="OUTSIDE_NARROW_PREPARATION_NEIGHBORHOOD"):
        curriculum.validate_dataset(changed)


def test_private_final_targets_export_separately_without_file_writes(dataset):
    exported = curriculum.export_parts(dataset)
    assert set(exported) == {"train.json", "validation.json", "test_public.json", "test_private.json", "manifest.json"}
    assert all(set(public) == {"problem", "observations"} for public in exported["test_public.json"])
    assert exported["test_public.json"] == [t["public"] for t in exported["test_private.json"]]
    exported["test_public.json"][0]["problem"] = "changed exported copy"
    assert dataset["splits"]["test"][0]["public"]["problem"] != "changed exported copy"


def test_generation_reproducible_and_seed_changes_instances(dataset):
    assert curriculum.generate_dataset() == dataset
    another = curriculum.generate_dataset(917)
    assert another["manifest"]["graph_signatures"] == dataset["manifest"]["graph_signatures"]
    assert another["splits"]["train"][0]["public"] != dataset["splits"]["train"][0]["public"]


@pytest.mark.parametrize("seed", [True, -1, 2**63, "7"])
def test_invalid_seed_rejected(seed):
    with pytest.raises(ValueError, match="SEED_INVALID"):
        curriculum.generate_dataset(seed)
