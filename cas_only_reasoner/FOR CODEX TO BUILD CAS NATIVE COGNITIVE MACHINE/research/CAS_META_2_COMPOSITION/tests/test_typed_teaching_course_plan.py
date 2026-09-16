"""Pure lineage parity: source selectors, never legacy target compilers.

The retained artifacts are training-only. Comparisons read schedule metadata,
source selectors and pair IDs only; their teacher registries are not consulted.
"""
import ast
import builtins
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import sys
from types import SimpleNamespace

import pytest

from cas_meta2.typed_teaching import course_plan as plan, source

DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}
LEGACY_DENIED = ("cas_meta2.graph_teaching", "cas_meta2.recurrent_cjt", "cas_meta2.complementary_teaching",
                 "cas_meta2.rpm_cfc_constructor", "cas_meta2.final_panel")
RETAINED = plan.ROOT / "records/matched_learning_preparation_001/checks_001"
PINS = {"course_prepared.json": "504593ab0dd9640d3485c619100e38aef3b445061dc729845936dd6e0405c495",
        "matched_schedules.json": "67e4fa06fc716063e4e75f124219e3c9485d03e21fc907182b241786e0703af0"}


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith(LEGACY_DENIED):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def plans():
    return {(seed, condition): plan.compile_plan(seed, condition)
            for seed in plan.SEEDS for condition in plan.CONDITIONS}


@pytest.fixture(scope="module")
def families():
    return list(source.training_families())


def retained(name):
    raw = (RETAINED / name).read_bytes()
    assert sha256(raw).hexdigest() == PINS[name]
    return json.loads(raw)


def scheduled_rows(value):
    by_id = {row["occurrence_id"]: row for row in value["occurrences"]}
    return [by_id[key] for batch in value["batches"] for key in batch["occurrence_ids"]]


@pytest.mark.parametrize("seed", plan.SEEDS)
@pytest.mark.parametrize("condition", plan.CONDITIONS)
def test_complete_shape_and_actual_planned_accounting(plans, seed, condition):
    value = plans[seed, condition]
    assert value["counts"] == {
        "presentations": 1152, "groups": 160, "rounds": 16,
        "by_role": {"CFC_FOUNDATION": 768, "COMPONENT": 128, "MAINTENANCE": 128, "WHOLE": 128},
        "by_profile": {"FACE_APPLY": 800, "LIST_PARTS": 128, "REACHED_VIA": 128, "ROLE_FROM_CONTENT": 96},
        "by_face": {"1": 96, "2": 96, "3": 96, "4": 224, "5": 544, "6": 96},
        "worked_support_presentations": 1152, "unique_query_families": 24,
        "batch_depth_units_planned": 600, "sample_core_passes_planned": 4320,
        "compute_measured": False}
    assert len({row["occurrence_id"] for row in value["occurrences"]}) == 1152
    assert Counter(batch["depth"] for batch in value["batches"]) == {1: 40, 2: 40, 4: 40, 8: 40}
    assert value["status"] == "TARGET_FREE_LINEAGE_PLAN_NOT_EXECUTION_ADMISSION"
    assert len(scheduled_rows(value)) == 1152
    assert source.digest({k: v for k, v in value.items() if k != "plan_digest"}) == value["plan_digest"]


@pytest.mark.parametrize("seed", plan.SEEDS)
def test_conditions_have_exact_same_occurrences_and_only_supplement_order_changes(plans, seed):
    alt, mixed, dag = (plans[seed, condition] for condition in plan.CONDITIONS)
    assert alt["occurrences"] == mixed["occurrences"] == dag["occurrences"]
    assert alt["batches"] == dag["batches"]
    changed = 0
    for left, right in zip(alt["batches"], mixed["batches"]):
        if left["phase"].startswith("SUPPLEMENT_"):
            assert left["occurrence_ids"] != right["occurrence_ids"]
            changed += 1
        else:
            assert left == right
    assert changed == 32
    assert dag["ordinary_graph_policy"]["same_order_as_alt_for_current_eight_pair_policy"] is True
    assert len(dag["ordinary_graph_policy"]["traces"]) == 16


def _selectors_only(path, names, namespace):
    """Execute only named, inspected selector ASTs; no module imports or targets."""
    tree = ast.parse(path.read_bytes(), str(path))
    picked = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in picked} == set(names)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for function in picked for node in ast.walk(function))
    exec(compile(ast.Module(body=picked, type_ignores=[]), str(path) + "#selectors-only", "exec"), namespace)


def test_exact_event_support_and_recognition_lineage_against_preserved_selector_asts(families):
    def denied(*args, **kwargs):
        raise AssertionError("ALL_SPLIT_CONSTRUCTOR_FORBIDDEN")
    corpus = SimpleNamespace(TRAINING="training", families=denied)
    tasks = {"corpus": corpus, "require": source.require}
    _selectors_only(plan.PACKAGE / "graph_teaching/face_tasks.py", {"choose_supports"}, tasks)
    roles = {"FACE_NUMBERS": tuple(range(1, 7)), "require": source.require}
    _selectors_only(plan.PACKAGE / "graph_teaching/face_roles.py", {"other_faces"}, roles)
    contract = plan._contract()
    schedule = {"corpus": corpus, "require": source.require,
        "roles": SimpleNamespace(FACE_NUMBERS=tuple(range(1, 7)), FACE_APPLY="FACE_APPLY",
                                 ROLE_FROM_CONTENT="ROLE_FROM_CONTENT", other_faces=roles["other_faces"]),
        "tasks": SimpleNamespace(choose_supports=tasks["choose_supports"], OPTIONS_PER_QUESTION=3),
        "training_families": lambda built: list(built), "CFC_COHORTS": 6, "CFC_CUBES_PER_COHORT": 4,
        "STAGE_FACES": contract["stages"], "RECOGNITION_GROUP_OFFSETS": (1, 2, 3, 4, 5),
        "planned_counts": lambda: {"cfc_decisions_per_round": 48}}
    _selectors_only(plan.PACKAGE / "graph_teaching/face_schedule.py",
                    {"_rotated", "_support_ids", "event_key", "cfc_round_events"}, schedule)
    for round_index in range(16):
        original = schedule["cfc_round_events"](round_index, built=families)
        actual = plan._events(round_index, families, contract)
        assert actual == original
        assert [plan.event_key(row) for row in actual] == [schedule["event_key"](row) for row in original]


def test_exact_1152_training_presentation_selectors_against_pinned_retained_artifact(plans):
    prior = retained("course_prepared.json")
    value = plans[101, plan.ALT]
    by_id = {row["occurrence_id"]: row for row in value["occurrences"]}
    old_rows = {row["presentation_id"]: row for row in prior["presentations"]}
    matched = 0
    assert len(prior["batches"]) == len(value["batches"]) == 160
    for before, after in zip(prior["batches"], value["batches"]):
        assert before == {key: item for key, item in after.items() if key != "occurrence_ids"}
        for slot, (presentation_id, occurrence_id) in enumerate(zip(after["presentation_ids"], after["occurrence_ids"])):
            original, actual = old_rows[presentation_id], by_id[occurrence_id]
            # Deliberately use no teacher_sidecar/public choice/private target field.
            selector = original["source_selector"]
            assert {key: selector[key] for key in ("cursor", "round", "phase", "depth")} == {
                key: after[key] for key in ("cursor", "round", "phase", "depth")}
            assert selector["slot"] == slot
            assert selector["family_id"] == actual["intent"]["family_id"]
            assert selector["teaching_role"] == actual["teaching_role"]
            assert original["operation"] == actual["intent"]["profile"]
            assert actual["occurrence_id"] != selector["source_record_id"]
            matched += 1
    assert matched == 1152


def test_all_nine_schedules_and_original_pair_ids_match_retained_training_metadata(plans):
    prior = retained("matched_schedules.json")
    assert [row["source_seed"] for row in prior] == list(plan.SEEDS)
    for seed_record in prior:
        seed = seed_record["source_seed"]
        for condition in plan.CONDITIONS:
            actual = plans[seed, condition]
            index = {row["occurrence_id"]: row for row in actual["occurrences"]}
            previous = seed_record["schedules"][condition]["batches"]
            assert len(previous) == len(actual["batches"]) == 160
            for left, right in zip(previous, actual["batches"]):
                assert [left[k] for k in ("cursor", "round", "phase")] == [right[k] for k in ("cursor", "round", "phase")]
                assert left["legacy_depth"] == right["depth"]
                assert left["operations"] == [index[key]["intent"]["profile"] for key in right["occurrence_ids"]]
                assert len(left["public_ids"]) == len(right["occurrence_ids"])
        traces = plans[seed, plan.DAG]["ordinary_graph_policy"]["traces"]
        assert traces == [{key: value for key, value in row.items() if key != "edge_scope"}
                          for row in seed_record["ordinary_graph_policy"]["traces"]]


def test_supports_and_training_comparison_partners_follow_public_authored_policy(plans, families):
    index = {family["family_id"]: family for family in families}
    for row in plans[101, plan.ALT]["occurrences"]:
        intent = row["intent"]
        assert intent["support_family_ids"] == row["source_event"]["support_ids"]
        assert [item["family_id"] for item in intent["support_intents"]] == intent["support_family_ids"]
        assert len(intent["support_intents"]) in (0, 3)
        for subject in [intent, *intent["support_intents"]]:
            assert subject["face"] == intent["face"]
            family = index[subject["family_id"]]
            if subject["face"] == 4:
                pool = [f for f in families if f["archetype"] == family["archetype"]]
                offset = next(i for i, f in enumerate(pool) if f["family_id"] == family["family_id"]) + 1
                expected = next(f["family_id"] for f in pool[offset:] + pool[:offset] if f["domain"] != family["domain"])
                assert subject["training_partner_family_id"] == expected
            else:
                assert subject["training_partner_family_id"] is None
        assert all(value != intent["family_id"] for value in intent["support_family_ids"])
        assert all(index[value]["split"] == "training" for value in intent["support_family_ids"])


def test_supplemental_queries_and_maintenance_are_public_selector_driven(plans, families):
    index = {family["family_id"]: family for family in families}
    for value in plans.values():
        for row in value["occurrences"]:
            intent, lineage, event = row["intent"], row["lineage"], row["source_event"]
            family = index[intent["family_id"]]
            assert intent["whole_label"] == family["labels"][0]
            if row["teaching_role"] == "COMPONENT":
                candidates = sorted(label for label in family["labels"] if label != family["labels"][0])
                assert intent["part_label"] == candidates[(lineage["round_index"] + event["offset"]) % len(candidates)]
            else:
                assert intent["part_label"] is None
            if row["teaching_role"] == "MAINTENANCE":
                assert lineage["maintenance_source_round_index"] == max(0, lineage["round_index"] - 6)
                assert event["round"] == lineage["maintenance_source_round_index"]
                assert event["movement"] == "RETURN_TO_CUBE"
            if intent["profile"] == "FACE_APPLY" and intent["face"] == 5:
                assert intent["question_selection"] == "PENDING_PUBLIC_SOURCE_FACE5_RULE"
            assert intent["focal_excerpt_required"] is (intent["profile"] == "ROLE_FROM_CONTENT")


def test_no_answer_fields_or_legacy_learner_ids_in_lineage(plans):
    forbidden = {"correct", "answer", "expected_answer", "encoded_correct_index", "teacher_sidecar", "options", "record_id"}
    def walk(value):
        if type(value) is dict:
            assert not forbidden.intersection(value)
            for item in value.values(): walk(item)
        elif type(value) is list:
            for item in value: walk(item)
    walk(plans[101, plan.ALT])


@pytest.mark.parametrize("seed", [True, False, 101.0, "101", -1, 404, None])
def test_seed_alias_and_unsupported_seed_refusal(seed):
    with pytest.raises(ValueError, match="TYPED_COURSE_SEED"):
        plan.compile_plan(seed, plan.ALT)


@pytest.mark.parametrize("condition", [None, True, "WHOLE_ONLY_MATCHED", "ALT", ""])
def test_undeclared_condition_refusal(condition):
    with pytest.raises(ValueError, match="TYPED_COURSE_CONDITION"):
        plan.compile_plan(101, condition)


def test_caller_source_pin_and_received_source_pin_are_enforced(plans):
    with pytest.raises(ValueError, match="SOURCE_PROFILE_CHANGED"):
        plan.compile_plan(101, plan.ALT, expected_source_profile_digest="0" * 64)
    forged = deepcopy(plans[101, plan.ALT])
    forged["source_profile"]["profile_digest"] = "0" * 64
    with pytest.raises(ValueError, match="SOURCE_PROFILE_CHANGED"):
        plan.validate_plan(forged)


@pytest.mark.parametrize("alteration", ["extra", "support", "omitted", "repeat", "depth_bool", "depth_float", "family", "face", "partner"])
def test_received_plan_reconstruction_rejects_resealed_false_lineage(plans, alteration):
    value = deepcopy(plans[101, plan.ALT])
    if alteration == "extra": value["correct"] = 0
    elif alteration == "support": value["occurrences"][0]["intent"]["support_family_ids"].reverse()
    elif alteration == "omitted": value["occurrences"].pop()
    elif alteration == "repeat": value["batches"][0]["occurrence_ids"][1] = value["batches"][0]["occurrence_ids"][0]
    elif alteration == "depth_bool": value["batches"][0]["depth"] = True
    elif alteration == "depth_float": value["batches"][0]["depth"] = 1.0
    elif alteration == "family": value["occurrences"][0]["intent"]["family_id"] = "family:organisational:00"
    elif alteration == "face": value["occurrences"][0]["intent"]["face"] = 2
    elif alteration == "partner": value["occurrences"][3]["intent"]["training_partner_family_id"] = "family:organisational:00"
    value["plan_digest"] = source.digest({k: v for k, v in value.items() if k != "plan_digest"})
    with pytest.raises(ValueError): plan.validate_plan(value)


def test_validation_reconstructs_and_returns_detached_copy(plans):
    value = deepcopy(plans[101, plan.ALT])
    checked = plan.validate_plan(value)
    assert checked == value
    value["occurrences"][0]["intent"]["support_family_ids"].clear()
    assert len(checked["occurrences"][0]["intent"]["support_family_ids"]) == 3


@pytest.mark.parametrize("bad", [None, [], {"source_seed": True}, {"source_seed": 101, "source_profile": []}])
def test_closed_plan_shape_refusal(bad):
    with pytest.raises(ValueError): plan.validate_plan(bad)


def test_cyclic_received_plan_is_bounded():
    value = {}; value["cycle"] = value
    with pytest.raises(ValueError, match="CYCLE"): plan.validate_plan(value)


@pytest.mark.parametrize("nodes", [[], [{"id": "a", "prerequisites": ["missing"]}],
    [{"id": "a", "prerequisites": ["a"]}],
    [{"id": "a", "prerequisites": []}, {"id": "a", "prerequisites": []}],
    [{"id": "a", "prerequisites": ["b"]}, {"id": "b", "prerequisites": ["a"]}],
    [{"id": "a", "prerequisites": [], "answer": 1}],
    [{"id": "a", "prerequisites": ["b", "b"]}, {"id": "b", "prerequisites": []}],
    [{"id": str(i), "prerequisites": []} for i in range(17)]])
def test_dependency_scheduler_refuses_unsupported_graphs(nodes):
    with pytest.raises(ValueError): plan.dependency_batches(nodes)


@pytest.mark.parametrize("size", [True, 1.0, 0, 17])
def test_dependency_scheduler_exact_budget(size):
    with pytest.raises(ValueError): plan.dependency_batches([{"id": "a", "prerequisites": []}], batch_size=size)


def test_dependency_release_occurs_after_whole_batch():
    nodes = [{"id": "a", "prerequisites": []}, {"id": "b", "prerequisites": ["a"]},
             {"id": "c", "prerequisites": []}]
    assert plan.dependency_batches(nodes, batch_size=2) == [["a", "c"], ["b"]]


def test_source_profile_pins_only_training_constructor_and_preserved_selector_code():
    profile = plan.source_profile()
    assert profile["source_role"].endswith("NOT_LEGACY_TASK_EXECUTION")
    for row in profile["files"]:
        path = plan.ROOT / row["path"]
        assert path.resolve().is_relative_to(plan.ROOT)
        assert sha256(path.read_bytes()).hexdigest() == row["sha256"]
        assert len(path.read_bytes()) == row["bytes"]
        assert not any(part in row["path"] for part in ("final_panel", "held_out", "final_targets"))
