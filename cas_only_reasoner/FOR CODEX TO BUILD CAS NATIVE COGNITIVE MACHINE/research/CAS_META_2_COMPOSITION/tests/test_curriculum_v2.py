"""Pure synthetic-seed curriculum tests, never the reserved20260917 holdout.

Every inspected target here belongs to an explicit fixture seed. No neural
model, saved candidate checkpoint, AWS call or native execution is used.
"""
from copy import deepcopy
from hashlib import sha256
import ast
import json
from pathlib import Path
import sys

import pytest

from cas_meta2 import curriculum_v2 as v2
from cas_meta2.codec import action_to_tokens, tokens_to_action
from cas_meta2.curriculum import check_native_topology, graph_signature, parse_problem, permitted_view
from cas_meta2.ir import validate_program


pytestmark = pytest.mark.not_gpu
FIXTURE_SEED = 884421
SMALL_COUNTS = {"train": 48, "validation": 6, "test": 6}


@pytest.fixture(scope="module")
def dataset():
    assert FIXTURE_SEED != v2.DEFAULT_SEED
    return v2.generate_dataset(seed=FIXTURE_SEED)


def triplets(dataset):
    groups = {}
    for task in dataset["splits"]["test"]:
        groups.setdefault(task["provenance"]["triplet_id"], {})[task["provenance"]["evaluation_group"]] = task
    return groups


def refresh(task):
    program = task["target"]["program"]
    task["provenance"]["graph_signature"] = graph_signature(program)
    task["provenance"]["depth"] = validate_program(program)["max_call_depth"]
    tag = next(row["tag"] for row in task["public"]["observations"] if row["slot"] == task["target"]["binding"])
    task["public"]["problem"] = v2.render_problem(program, tag, task["provenance"]["wording_combination"])


def test_default_size_synthetic_fixture_has_preregistered_proportions(dataset):
    manifest = dataset["manifest"]
    assert v2.DEFAULT_SEED == 20260917
    assert dataset["seed"] == FIXTURE_SEED
    assert dataset["schema"] == "cas-meta2-curriculum/2"
    assert manifest["schema"] == "cas-meta2-dataset-manifest/2"
    assert manifest["counts"] == {"train": 768, "validation": 48, "test": 72}
    assert manifest["splits"]["train"]["depth_counts"] == {"1": 192, "2": 288, "3": 288}
    assert manifest["splits"]["validation"]["depth_counts"] == {"1": 16, "2": 16, "3": 16}
    assert manifest["splits"]["test"]["depth_counts"] == {"3": 48, "4": 24}
    assert manifest["evaluation_group_counts"] == {name: 24 for name in v2.GROUPS}
    assert manifest["triplets"] == 24
    assert sum(manifest["splits"]["train"]["binding_counts"]) == 768
    assert all("binding_counts" not in manifest["splits"][split] for split in ("validation", "test"))
    assert manifest["native_outcomes_checked"] is False
    assert manifest["training_or_neural_execution_performed"] is False


def test_positive_identity_control_and_sentence_primitive_coverage(dataset):
    coverage = dataset["manifest"]["training_coverage"]
    assert all(coverage["procedure_declarations"][name] > 0 and coverage["procedure_call_targets"][name] > 0
               for name in v2.PROCEDURE_NAMES[1:])
    assert coverage["programs_with_child_calls"] == 288
    assert coverage["calls_from_child_procedures"] >= 288
    assert all(coverage["instructions"][key] > 0 for key in ("RUN", "CALL", "RETURN"))
    assert all(coverage[key] > 0 for key in ("earlier_value_inputs", "earlier_value_returns", "repeated_callee_uses"))
    assert all(coverage["sentence_primitives"][role][str(family)] > 0
               for role in ("start", "declaration", "RUN", "CALL", "RETURN") for family in range(3))
    tokens = dataset["manifest"]["positive_target_token_coverage"]
    assert tokens["missing_validation_tokens"] == tokens["missing_test_tokens"] == []
    assert tokens["validation_tokens_covered"] is True and tokens["test_tokens_covered"] is True
    assert set(tokens) == {"training_counts", "validation_tokens_covered", "test_tokens_covered",
                           "missing_validation_tokens", "missing_test_tokens"}
    fixture_held_out_tokens = {token for split in ("validation", "test") for task in dataset["splits"][split]
                              for token in action_to_tokens(task["target"])}
    assert fixture_held_out_tokens <= set(tokens["training_counts"])
    assert "v8" in tokens["training_counts"] and "v31" not in tokens["training_counts"]


def test_all_fixture_targets_use_unchanged_codec_parser_and_pure_native_admission(dataset, monkeypatch):
    from cas_meta2 import native

    def forbidden(*args, **kwargs):
        pytest.fail("PURE_CURRICULUM_TEST_REACHED_NATIVE_MODEL")

    for name in ("_frozen", "NativeBackend", "execute_task", "reference_task"):
        monkeypatch.setattr(native, name, forbidden)
    for tasks in dataset["splits"].values():
        for task in tasks:
            assert parse_problem(permitted_view(task)) == task["target"]
            tokens = action_to_tokens(task["target"], max_length=256)
            assert tokens_to_action(tokens, max_length=256) == task["target"]
            plan = native.admit_action(task["public"], task["target"])
            assert 1 <= len(plan["runs"]) <= 15
            assert {row["cjt_id"] for row in plan["runs"]} <= {"A", "B", "C"}
            assert all(any(step["kind"] == "RUN" for step in proc["steps"])
                       for proc in task["target"]["program"]["procedures"].values())


def test_paired_triplets_isolate_wording_and_preserve_native_work_at_extra_depth(dataset):
    for group in triplets(dataset).values():
        same, wording, deep = (group[name] for name in v2.GROUPS)
        assert same["target"] == wording["target"]
        assert same["public"]["observations"] == wording["public"]["observations"] == deep["public"]["observations"]
        assert same["target"]["binding"] == deep["target"]["binding"]
        assert same["public"]["problem"] != wording["public"]["problem"]
        assert same["provenance"]["wording_combination"] == deep["provenance"]["wording_combination"]
        assert (same["provenance"]["depth"], deep["provenance"]["depth"]) == (3, 4)
        assert v2._native_work(same["target"]["program"]) == v2._native_work(deep["target"]["program"])
        assert len(action_to_tokens(same["target"])) == len(action_to_tokens(deep["target"]))
        v2._validate_pair(same["target"]["program"], deep["target"]["program"])


def test_graph_and_input_sets_never_overlap_across_splits_or_legacy(dataset):
    graphs = {split: {graph_signature(task["target"]["program"]) for task in tasks}
              for split, tasks in dataset["splits"].items()}
    vectors = {split: {tuple(observation["values"]) for task in tasks for observation in task["public"]["observations"]}
               for split, tasks in dataset["splits"].items()}
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert not graphs[first] & graphs[second]
        assert not vectors[first] & vectors[second]
    assert [len(graphs[split]) for split in ("train", "validation", "test")] == [768, 48, 48]
    assert [len(vectors[split]) for split in ("train", "validation", "test")] == [2304, 144, 72]
    assert not set.union(*graphs.values()) & set(v2.legacy_graph_signatures())
    exclusions = dataset["manifest"]["exclusions"]
    assert exclusions["legacy_constructor_seed"] == 20260906
    assert exclusions["count"] == 376
    assert exclusions["sha256"] == v2.digest(sorted(v2.legacy_graph_signatures()))


def test_only_new_deterministic_fixture_seeds_are_exercised():
    first = v2.generate_dataset(seed=711, counts=SMALL_COUNTS)
    second = v2.generate_dataset(seed=711, counts=SMALL_COUNTS)
    other = v2.generate_dataset(seed=712, counts=SMALL_COUNTS)
    assert first == second
    assert first["manifest"]["splits"]["train"]["sha256"] != other["manifest"]["splits"]["train"]["sha256"]


def test_extra_exclusions_are_applied_and_independently_bound():
    old_fixture = v2.generate_dataset(seed=811, counts=SMALL_COUNTS)
    excluded = {task["provenance"]["graph_signature"] for tasks in old_fixture["splits"].values() for task in tasks}
    new_fixture = v2.generate_dataset(seed=812, counts=SMALL_COUNTS, excluded_graph_signatures=excluded)
    assert not excluded & {task["provenance"]["graph_signature"] for tasks in new_fixture["splits"].values() for task in tasks}
    assert new_fixture["manifest"]["exclusions"]["additional_sha256"] == v2.digest(sorted(excluded))
    assert v2.validate_dataset(new_fixture, excluded_graph_signatures=excluded) == new_fixture["manifest"]
    with pytest.raises(ValueError, match="OLD_GRAPH_REUSED"):
        v2.validate_dataset(old_fixture, excluded_graph_signatures=excluded)


@pytest.mark.parametrize("extra", [["a" * 64], {"bad"}, {1}, {"A" * 64}])
def test_malformed_exclusions_are_rejected(extra):
    with pytest.raises(ValueError):
        v2.generate_dataset(seed=13, counts=SMALL_COUNTS, excluded_graph_signatures=extra)


def test_unseen_positive_target_token_is_rejected_even_when_structure_is_unchanged(dataset):
    changed = deepcopy(dataset)
    group = next(iter(triplets(changed).values()))
    for task in group.values():
        main = task["target"]["program"]["procedures"]["main"]
        previous = main["steps"][0]["output"]
        main["steps"][0]["output"] = "v31"
        for step in main["steps"]:
            if step["input"] == previous:
                step["input"] = "v31"
        if main["return"] == previous:
            main["return"] = "v31"
        refresh(task)
    with pytest.raises(ValueError, match="V2_UNSEEN_POSITIVE_TARGET_TOKEN"):
        v2.validate_dataset(changed)


def test_actual_wording_cannot_hide_behind_unmodified_metadata(dataset):
    changed = deepcopy(dataset)
    task = changed["splits"]["train"][0]
    original = task["provenance"]["wording_combination"]
    alternative = next(combo for combo in v2.wording_combinations(0) if list(combo) != original)
    tag = next(row["tag"] for row in task["public"]["observations"] if row["slot"] == task["target"]["binding"])
    task["public"]["problem"] = v2.render_problem(task["target"]["program"], tag, alternative)
    assert parse_problem(task["public"]) == task["target"]
    with pytest.raises(ValueError, match="V2_ACTUAL_WORDING_OR_MEANING_MISMATCH"):
        v2.validate_dataset(changed)


def test_sentence_primitive_training_gaps_are_rejected(dataset):
    changed = deepcopy(dataset)
    for task in changed["splits"]["train"]:
        task["provenance"]["wording_combination"] = [0, 0, 0, 0]
        refresh(task)
    with pytest.raises(ValueError, match="V2_SENTENCE_PRIMITIVE_TRAINING_GAP"):
        v2.validate_dataset(changed)


@pytest.mark.parametrize("mutation", ["graph", "input", "triplet", "binding", "depth", "scope"])
def test_invalid_split_or_pair_conditions_are_rejected(dataset, mutation):
    changed = deepcopy(dataset)
    if mutation == "graph":
        task = changed["splits"]["validation"][0]
        task["target"]["program"] = deepcopy(changed["splits"]["train"][0]["target"]["program"])
        refresh(task)
    elif mutation == "input":
        changed["splits"]["validation"][0]["public"]["observations"][0]["values"] = deepcopy(
            changed["splits"]["train"][0]["public"]["observations"][0]["values"])
    elif mutation == "triplet":
        changed["splits"]["test"][0]["provenance"]["triplet_id"] = "triplet-9999"
    elif mutation == "binding":
        task = next(iter(triplets(changed).values()))["wording_shift"]
        task["target"]["binding"] = (task["target"]["binding"] + 1) % 3
        refresh(task)
    elif mutation == "depth":
        changed["splits"]["test"][0]["provenance"]["depth"] = 99
    else:
        task = changed["splits"]["train"][0]
        for proc in task["target"]["program"]["procedures"].values():
            proc["allowed_cjts"].append("R")
    with pytest.raises(ValueError):
        v2.validate_dataset(changed)


def test_changed_deeper_final_return_fails_matched_native_work(dataset):
    changed = deepcopy(dataset)
    task = next(iter(triplets(changed).values()))["deeper_calls"]
    main = task["target"]["program"]["procedures"]["main"]
    main["return"] = main["steps"][0]["output"]
    refresh(task)
    with pytest.raises(ValueError, match="V2_PAIRED_NATIVE_WORK_MISMATCH"):
        v2.validate_dataset(changed)


def test_empty_wrapper_does_not_count_as_deeper_skill(dataset):
    program = deepcopy(next(iter(triplets(dataset).values()))["deeper_calls"]["target"]["program"])
    name = next(name for name, proc in program["procedures"].items()
                if name != "main" and any(step["kind"] == "CALL" for step in proc["steps"]))
    proc = program["procedures"][name]
    call = next(deepcopy(step) for step in proc["steps"] if step["kind"] == "CALL")
    call["output"] = "v0"
    proc["steps"], proc["return"] = [call], "v0"
    with pytest.raises(ValueError, match="EMPTY_WRAPPER_PROCEDURE_FORBIDDEN"):
        v2._target_stats({"program": program, "binding": 0})


@pytest.mark.parametrize("counts", [{"train": 32, "validation": 6, "test": 6},
                                    {"train": 49, "validation": 6, "test": 6},
                                    {"train": 48, "validation": 7, "test": 6},
                                    {"train": 48, "validation": 6, "test": 7},
                                    {"train": 800, "validation": 48, "test": 72}])
def test_invalid_or_expanded_counts_are_rejected(counts):
    with pytest.raises(ValueError):
        v2.generate_dataset(seed=10, counts=counts)


def test_writer_separates_public_fields_hashes_every_partition_and_does_not_overwrite(tmp_path, monkeypatch):
    path = tmp_path / "fixture_only_dataset"
    manifest = v2.write_dataset(path, seed=901, counts=SMALL_COUNTS)
    assert set(manifest["sha256"]) == {"train.json", "validation.json", "test_public.json", "test_private.json"}
    assert set(item.name for item in path.iterdir()) == set(manifest["sha256"]) | {"dataset_manifest.json"}
    for name, checksum in manifest["sha256"].items():
        assert sha256((path / name).read_bytes()).hexdigest() == checksum
    public = json.loads((path / "test_public.json").read_bytes())
    assert len(public) == 6 and all(set(row) == {"problem", "observations"} for row in public)
    before = {item.name: item.read_bytes() for item in path.iterdir()}
    with pytest.raises(ValueError, match="V2_DATASET_OUTPUT_MUST_BE_NEW"):
        v2.write_dataset(path, seed=902, counts=SMALL_COUNTS)
    assert {item.name: item.read_bytes() for item in path.iterdir()} == before
    monkeypatch.setattr(v2, "validate_dataset", lambda *_a, **_k: pytest.fail("PUBLIC_MANIFEST_OPENED_PRIVATE_VALIDATION"))
    checked = v2.validate_manifest(manifest, expected_counts=SMALL_COUNTS)
    assert checked["private_partition_opened"] is False
    with pytest.raises(ValueError, match="INVALID_V2_PUBLIC_MANIFEST"):
        v2.validate_manifest(manifest)


def test_manifest_rejects_forged_coverage_and_neural_claims(tmp_path):
    manifest = v2.write_dataset(tmp_path / "fixture_only_manifest", seed=903, counts=SMALL_COUNTS)
    changed = deepcopy(manifest)
    changed["positive_target_token_coverage"]["missing_test_tokens"] = ["v31"]
    with pytest.raises(ValueError, match="V2_MANIFEST_POSITIVE_TRAINING_COVERAGE_MISSING"):
        v2.validate_manifest(changed, SMALL_COUNTS)
    changed = deepcopy(manifest)
    changed["native_outcomes_checked"] = True
    with pytest.raises(ValueError, match="V2_CONSTRUCTION_MUST_NOT_CLAIM_NEURAL_RESULTS"):
        v2.validate_manifest(changed, SMALL_COUNTS)


@pytest.mark.parametrize("field", ["validation_counts", "test_counts"])
def test_public_manifest_rejects_held_out_target_frequencies(dataset, field):
    manifest = deepcopy(dataset["manifest"])
    manifest["sha256"] = {name: "a" * 64 for name in
                          ("train.json", "validation.json", "test_public.json", "test_private.json")}
    manifest["positive_target_token_coverage"][field] = {"v0": 1}
    with pytest.raises(ValueError, match="V2_PUBLIC_TARGET_COVERAGE_FIELDS_INVALID"):
        v2.validate_manifest(manifest)


@pytest.mark.parametrize("field", ["validation_tokens_covered", "test_tokens_covered"])
def test_public_manifest_requires_actual_coverage_assertions(dataset, field):
    manifest = deepcopy(dataset["manifest"])
    manifest["sha256"] = {name: "a" * 64 for name in
                          ("train.json", "validation.json", "test_public.json", "test_private.json")}
    manifest["positive_target_token_coverage"][field] = False
    with pytest.raises(ValueError, match="V2_MANIFEST_POSITIVE_TRAINING_COVERAGE_MISSING"):
        v2.validate_manifest(manifest)


@pytest.mark.parametrize("split", ["validation", "test"])
def test_public_manifest_rejects_held_out_binding_frequencies(dataset, split):
    manifest = deepcopy(dataset["manifest"])
    manifest["sha256"] = {name: "a" * 64 for name in
                          ("train.json", "validation.json", "test_public.json", "test_private.json")}
    manifest["splits"][split]["binding_counts"] = [1, 2, 3]
    with pytest.raises(ValueError, match="V2_PUBLIC_HELD_OUT_BINDING_COUNTS_FORBIDDEN"):
        v2.validate_manifest(manifest)


def test_module_is_data_only_and_does_not_modify_the_old_compiler_or_executor():
    tree = ast.parse(Path(v2.__file__).read_text(encoding="utf-8"))
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("torch", "numpy", "pickle", "casformer", "cas_cjt")) for name in imports)
    assert "torch" not in sys.modules
    assert {"codec", "curriculum", "ir"} <= imports
