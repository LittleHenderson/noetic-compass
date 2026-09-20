"""Compare full teaching schedules before claiming a matched learning treatment.

Pure training-source compilation only. The legacy lessons here are not admitted
to the ordered learner by this module. No tokenizer, learner or final panel is
constructed. Instructional prerequisites describe a teaching policy, not a proof
that a component lesson is necessary to answer a whole question.
"""
from collections import Counter
from copy import deepcopy

from cas_meta2.codec import validate_public
from cas_meta2.complementary_teaching import course

from .canonical import canonical_json, digest
from .rpa_model import require

SCHEMA = "cncm.matched-teaching-schedules/0.1"
ALT, MIXED = course.CONDITIONS[:2]
DAG = "ORDINARY_DEPENDENCY_GRAPH"
CONDITIONS = (ALT, MIXED, DAG)
MAX_OCCURRENCES = 20000


def dependency_batches(nodes, *, batch_size):
    """Stable ready queue; dependencies release only after a whole batch commits.

    This compiles the planned update order. It does not execute or claim that any
    update has committed. Priorities are positions in the supplied public node
    list and do not consult target answers.
    """
    require(type(nodes) is list and 0 < len(nodes) <= MAX_OCCURRENCES,
            "MATCH_DAG_NODES_REQUIRED")
    require(type(batch_size) is int and 0 < batch_size <= 64, "MATCH_DAG_BATCH_SIZE")
    ids = []
    for node in nodes:
        require(type(node) is dict and set(node) == {"id", "prerequisites"}, "MATCH_DAG_NODE_FIELDS")
        require(type(node["id"]) is str and 0 < len(node["id"]) <= 256, "MATCH_DAG_NODE_ID")
        deps = node["prerequisites"]
        require(type(deps) is list and all(type(value) is str for value in deps)
                and len(deps) == len(set(deps)), "MATCH_DAG_PREREQUISITES")
        ids.append(node["id"])
    require(len(ids) == len(set(ids)), "MATCH_DAG_DUPLICATE_ID")
    known = set(ids)
    require(all(set(row["prerequisites"]) <= known and row["id"] not in row["prerequisites"]
                for row in nodes), "MATCH_DAG_UNKNOWN_OR_SELF_DEPENDENCY")
    committed, batches = set(), []
    while len(committed) < len(nodes):
        ready = [row["id"] for row in nodes if row["id"] not in committed
                 and set(row["prerequisites"]) <= committed]
        require(ready, "MATCH_DAG_CYCLE")
        selected = ready[:batch_size]
        batches.append(selected)
        committed.update(selected)
    return batches


def _task(task):
    require(type(task) is dict and {"record_id", "public", "encoded_options", "correct",
                                  "encoded_correct_index", "op"} <= set(task), "MATCH_SOURCE_TASK_FIELDS")
    validate_public(task["public"])
    options, index = task["encoded_options"], task["encoded_correct_index"]
    require(type(options) is list and len(options) == 3
            and len({canonical_json(value) for value in options}) == 3, "MATCH_DISTINCT_OPTIONS")
    require(type(index) is int and 0 <= index < 3
            and canonical_json(options[index]) == canonical_json(task["correct"]),
            "MATCH_CORRECTION_OPTION_BINDING")
    require(all(type(row["slot"]) is int and row["slot"] == slot
                and row["tag"] == str(options[slot])
                and canonical_json(row["values"]) == canonical_json([0.0] * 8)
                for slot, row in enumerate(task["public"]["observations"])),
            "MATCH_VISIBLE_OPTION_BINDING")
    require(type(task["record_id"]) is str and task["record_id"]
            and type(task["op"]) is str and task["op"], "MATCH_SOURCE_ID_OR_OPERATION")
    public = {key: deepcopy(task[key]) for key in ("public", "encoded_options")}
    identity = digest(public)
    correction = {"encoded_correct_index": index, "expected_answer": deepcopy(task["correct"])}
    return identity, public, correction


def _project(schedule):
    publics, corrections, batches, aliases = {}, {}, [], {}
    require(type(schedule["batches"]) is list and 0 < len(schedule["batches"]) <= MAX_OCCURRENCES,
            "MATCH_BATCH_BOUND")
    for cursor, batch in enumerate(schedule["batches"]):
        require(batch["cursor"] == cursor and type(batch["cursor"]) is int, "MATCH_BATCH_CURSOR")
        require(type(batch["round"]) is int and batch["round"] > 0
                and type(batch["depth"]) is int and 0 < batch["depth"] <= 64,
                "MATCH_BATCH_ROUND_OR_DEPTH")
        require(type(batch["tasks"]) is list and 0 < len(batch["tasks"]) <= 64, "MATCH_BATCH_TASK_BOUND")
        ids, operations, semantic_ids = [], [], []
        for task in batch["tasks"]:
            key, public, correction = _task(task)
            require(key not in publics or publics[key] == public, "MATCH_PUBLIC_COLLISION")
            require(key not in corrections or corrections[key] == correction, "MATCH_CONFLICTING_CORRECTION")
            publics[key], corrections[key] = public, correction
            alias = task["record_id"]
            require(alias not in aliases or aliases[alias] == key, "MATCH_SOURCE_ID_COLLISION")
            aliases[alias] = key
            ids.append(key)
            operations.append(task["op"])
            semantic = task.get("semantic_question_id", alias)
            require(type(semantic) is str and semantic, "MATCH_SEMANTIC_ID")
            semantic_ids.append(semantic)
        batches.append({"cursor": cursor, "round": batch["round"], "phase": batch["phase"],
                        "legacy_depth": batch["depth"], "public_ids": ids,
                        "operations": operations, "semantic_ids": semantic_ids})
    require(sum(len(row["public_ids"]) for row in batches) <= MAX_OCCURRENCES, "MATCH_PRESENTATION_BOUND")
    return {"batches": batches, "public_registry": publics, "teacher_registry": corrections,
            "source_id_aliases": aliases}


def _ordinary_dag(alt):
    result = deepcopy(alt)
    result["condition"] = DAG
    traces = []
    rounds = sorted({row["round"] for row in alt["batches"]})
    require(len(alt["pairs_by_round"]) == len(rounds), "MATCH_PAIR_ROUND_COUNT")
    for round_number, pairs in zip(rounds, alt["pairs_by_round"]):
        batches = [row for row in result["batches"] if row["round"] == round_number
                   and row["phase"].startswith("SUPPLEMENT_")]
        require(len(batches) == 2 and len(pairs) == 8
                and all(len(batch["tasks"]) == 8 for batch in batches), "MATCH_SUPPLEMENT_SHAPE")
        nodes, occurrence_tasks, pair_ids = [], {}, []
        for slot, pair in enumerate(pairs):
            component, whole = "component:%d" % slot, "whole:%d" % slot
            nodes.extend(({"id": component, "prerequisites": []},
                          {"id": whole, "prerequisites": [component]}))
            for key, role, source in ((component, "COMPONENT", pair["component"]),
                                      (whole, "WHOLE", pair["whole"])):
                occurrence_tasks[key] = course._annotate(source, role)
            pair_ids.append(pair["pair_id"])
        planned = dependency_batches(nodes, batch_size=8)
        require(len(planned) == len(batches), "MATCH_DAG_UPDATE_BUDGET_CHANGED")
        for batch, selected in zip(batches, planned):
            batch["tasks"] = [deepcopy(occurrence_tasks[key]) for key in selected]
        traces.append({"round": round_number, "nodes": nodes, "batches": planned,
                       "pair_ids": pair_ids,
                       "edge_scope": "Authored component-before-whole teaching order, not logical necessity."})
    return result, traces


def _counts(projected):
    batches = projected["batches"]
    public_ids = [key for row in batches for key in row["public_ids"]]
    return {"presentations": len(public_ids), "optimizer_updates_planned": len(batches),
            "unique_public_inputs": len(set(public_ids)),
            "unique_semantic_questions": len({key for row in batches for key in row["semantic_ids"]}),
            "operations": dict(sorted(Counter(op for row in batches for op in row["operations"]).items())),
            "batch_sizes": [len(row["public_ids"]) for row in batches],
            "legacy_sample_core_passes_planned": sum(row["legacy_depth"] * len(row["public_ids"]) for row in batches)}


def compare_projected(left, right):
    """Compare actual input/correction multisets and update membership, not labels."""
    for value in (left, right):
        require(set(value) == {"batches", "public_registry", "teacher_registry", "source_id_aliases"},
                "MATCH_PROJECTION_FIELDS")
    def occurrences(value):
        return Counter(key for row in value["batches"] for key in row["public_ids"])
    require(left["public_registry"] == right["public_registry"], "MATCH_PUBLIC_INFORMATION_DIFFERS")
    require(left["teacher_registry"] == right["teacher_registry"], "MATCH_CORRECTIONS_DIFFER")
    require(occurrences(left) == occurrences(right), "MATCH_PRESENTATION_MULTISET_DIFFERS")
    a, b = left["batches"], right["batches"]
    require(len(a) == len(b), "MATCH_UPDATE_BUDGET_DIFFERS")
    require(all(len(x["public_ids"]) == len(y["public_ids"])
                and x["legacy_depth"] == y["legacy_depth"]
                for x, y in zip(a, b)), "MATCH_PLANNED_BATCH_WORK_DIFFERS")
    ordered = [row["public_ids"] for row in a] == [row["public_ids"] for row in b]
    membership = [sorted(row["public_ids"]) for row in a] == [sorted(row["public_ids"]) for row in b]
    return {"equal_public_information": True, "equal_corrections": True,
            "equal_presentation_multisets": True, "equal_planned_batch_work": True,
            "identical_ordered_update_inputs": ordered, "identical_update_membership": membership,
            "treatment": "NO_DISTINCT_UPDATE_INPUT" if ordered else
                         ("WITHIN_BATCH_ORDER_ONLY" if membership else "LESSON_ORDER_OR_BATCH_GROUPING"),
            "actual_compute_matching": "UNMEASURED_NO_LEARNER_EXECUTION",
            "cas_architecture_advantage_established": False}


def compile_training_comparison(seed, *, built=None):
    """Keep the full inherited course and expose a real ordinary-graph control.

    The seed is one of the existing source-construction seeds, not a newly
    selected experimental initialization. No final study or outcome is frozen.
    """
    require(type(seed) is int and seed in course.SEEDS, "MATCH_SOURCE_SEED")
    alt = course.compile_complementary_course(seed, ALT, built=built)
    mixed = course.compile_complementary_course(seed, MIXED, built=built)
    dag, traces = _ordinary_dag(alt)
    projected = {ALT: _project(alt), MIXED: _project(mixed), DAG: _project(dag)}
    comparisons = {MIXED: compare_projected(projected[ALT], projected[MIXED]),
                   DAG: compare_projected(projected[ALT], projected[DAG])}
    reference = projected[ALT]
    result = {"schema_version": SCHEMA, "source_seed": seed,
        "public_registry": reference["public_registry"], "teacher_registry": reference["teacher_registry"],
        "schedules": {key: {"batches": value["batches"], "counts": _counts(value),
                           "source_id_aliases": value["source_id_aliases"]}
                      for key, value in projected.items()},
        "ordinary_graph_policy": {"priority": "stable authored occurrence order",
            "batch_size": 8, "dependency_release": "after prerequisite batch commit",
            "policy_scope": "SUPPLEMENT_OCCURRENCES_ONLY_COMMON_FOUNDATION_AND_MAINTENANCE_UNCHANGED",
            "comparison_scope": "No-treatment result applies to these eight-item supplement batches only; not a general CAS/graph equivalence.",
            "traces": traces, "execution": "PLANNED_ONLY_NO_UPDATE_COMMITTED"},
        "comparisons_to_component_whole": comparisons,
        "readiness": "LEGACY_TRAINING_SOURCE_NOT_YET_ADMITTED_TO_ORDERED_STUDY",
        "boundary": "Full exposed training curriculum. No final questions, learner, tokenizer or provider. "
                    "Matching planned work is not matching measured compute. No learning benefit is established."}
    result["comparison_id"] = digest(result)
    return result
