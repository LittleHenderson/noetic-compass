"""Pure compiler and persistent execution over the existing recurrent/CFC stack.

The injected batch callable is the REAL recurrent_batch_step in runner.py. No
alternate learner, optimizer, core, head, solver or shared-budget change exists.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import time

from . import IMPLEMENTATION_ID, PROFILE_ID
from ..recurrent_cjt import course as base
from ..recurrent_cjt import recurrence
from ..graph_teaching import adapter, face_corpus, face_schedule, face_tasks
from ..graph_teaching import lessons, reference, verified_training

CONDITIONS = ("ALT_COMPONENT_WHOLE", "MIXED_SAME_ITEMS", "WHOLE_SUPPLEMENT")
SEEDS = (101, 202, 303)
MONITOR_ROUNDS = (4, 8, 12, 16)
TARGET_FIELDS = frozenset(("correct", "encoded_correct_index", "reference"))


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def public_identity(task):
    return digest({key: task[key] for key in ("public", "encoded_options")})


def semantic_identity(graph, question):
    # Presentation, role, choices and private correctness are deliberately absent.
    return digest({"graph": graph, "question": question})


def _record_task(graph, question, options, correct, family_id):
    """Public bytes/IDs fixed before private correction is attached."""
    require(len(options) == 3 and len({digest(v) for v in options}) == 3,
            "COMPLEMENTARY_THREE_DISTINCT_PUBLIC_CHOICES")
    prompt = graph.render() + verified_training._request(question) + "\nChoose one supplied option.\n"
    public = {"schema": lessons.EXERCISE_SCHEMA, "split": "complementary_training",
              "op": question["op"], "graph": graph.to_record(), "question": question,
              "options": options, "framings": {"cas": prompt, "generic": prompt}}
    record = {**public, "record_id": digest(public), "correct": correct,
              "reference": reference.derivation_for(question["op"], graph, question)}
    task = adapter.public_records(record, "cas")
    task.update({"family_id": family_id, "arm": "cas", "graph": graph.to_record(),
                 "question": question, "task_profile": PROFILE_ID,
                 "semantic_question_id": semantic_identity(graph.to_record(), question)})
    return task


def teaching_pairs(round_index, *, built=None):
    """Two connected applications per actual support cube; choices use public facts.

All candidates cycle through the PUBLIC label list, including absent/indirect
constituents. A private target mutation cannot change pairing, choices or order.
The source is the exact four-cube CFC cohort, never a final-audit family.
"""
    built = face_corpus.families() if built is None else built
    index = face_corpus.family_index(built)
    families = list(dict.fromkeys(event["family_id"] for event in
                    face_schedule.cfc_round_events(round_index, built=built)))
    pairs = []
    for family_id in families:
        family = index[family_id]
        graph = face_tasks.family_graph(family)
        whole = family["labels"][0]
        labels = sorted(label for label in family["labels"] if label != whole)
        direct = reference.direct_parts(graph, whole)
        require(direct, "COMPLEMENTARY_EMPTY_WHOLE_UNSUPPORTED")
        # Three inventory candidates authored from the public graph. The teacher
        # is consulted separately below. No target field determines these bytes.
        inventories = [sorted(direct), sorted(set(direct + labels)), [labels[0]], []]
        distinct = list({digest(value): value for value in inventories}.values())
        require(len(distinct) >= 3, "COMPLEMENTARY_LIST_CHOICES_UNAVAILABLE")
        for slot in range(2):
            candidate = labels[(round_index + slot) % len(labels)]
            # Public traversal determines a representable offered route. Private
            # teacher correction is not read while selecting the candidate.
            possible = [node for node in sorted(direct)
                        if candidate in reference.transitive_parts(graph, node)]
            via = possible[0] if possible else direct[0]
            cq = {"op": "REACHED_VIA", "idea": whole, "part": candidate}
            wq = {"op": "LIST_PARTS", "idea": whole}
            component = _record_task(graph, cq, ["direct", "via:" + via, "absent"],
                                    reference.reach_kind(graph, candidate, whole), family_id)
            whole_task = _record_task(graph, wq, distinct[:3],
                                     reference.direct_parts(graph, whole), family_id)
            pairs.append({"family_id": family_id,
                          "pair_id": digest([family_id, cq, wq]),
                          "public_relevance": {"kind": "candidate_membership_of_inventory",
                                               "whole": whole, "candidate": candidate},
                          "component": component, "whole": whole_task})
    require(len(pairs) == 8, "COMPLEMENTARY_EIGHT_PAIRS_REQUIRED")
    return pairs


def _annotate(task, role):
    task = deepcopy(task)
    task["teaching_role"] = role
    task.setdefault("semantic_question_id", task["record_id"])
    task["public_input_sha256"] = public_identity(task)
    return task


def foundation_tasks_for_round(round_index, *, built=None):
    """Unchanged inherited tasks plus semantic keys independent of rendering/options."""
    from ..graph_teaching.face_experiment import compile_event
    supplied = base.default_tasks_for_round(round_index, built=built)
    events = list(face_schedule.cfc_round_events(round_index, built=built))
    events += [event for event in face_schedule.cfc_round_events(base.maintenance_round(round_index), built=built)
               if event["movement"] == "RETURN_TO_CUBE"]
    identities = {}
    for event in events:
        record = compile_event(event, built=built)["public_record"]
        # Recognition compares a content excerpt, so its public content focus is
        # part of the question. It is selected by the schedule before the teacher
        # checks correctness. Never derive this identity from teacher_target.
        key = {"family_id": record["family_id"], "graph": record["graph"],
               "question": record["question"],
               "content_focus": event["face"] if record["op"] == "ROLE_FROM_CONTENT" else None}
        identities[record["record_id"]] = digest(key)
    for tasks in supplied.values():
        for task in tasks:
            task["semantic_question_id"] = identities[task["record_id"]]
    return supplied


def compile_complementary_course(seed, condition, built=None, public_transform=None):
    require(seed in SEEDS, "COMPLEMENTARY_SEED_NOT_DECLARED")
    require(condition in CONDITIONS, "COMPLEMENTARY_CONDITION_NOT_DECLARED")
    batches, pairs_by_round = [], []
    depths = list(recurrence.ROUND_DEPTH_SCHEDULE)
    offset = SEEDS.index(seed)
    depths = depths[offset:] + depths[:offset]
    for round_index, depth in enumerate(depths):
        supplied = foundation_tasks_for_round(round_index, built=built)
        phase_batches = []
        for phase in ("WITHIN_CUBE", "ACROSS_FACE", "RETURN_TO_CUBE"):
            cursor = 0
            for count in recurrence.phase_batches(phase):
                phase_batches.append((phase, supplied[phase][cursor:cursor + count]))
                cursor += count
        pairs = teaching_pairs(round_index, built=built)
        rotation = (seed + round_index + 1) % 8
        pairs = pairs[rotation:] + pairs[:rotation]
        pairs_by_round.append(pairs)
        component = [_annotate(pair["component"], "COMPONENT") for pair in pairs]
        whole = [_annotate(pair["whole"], "WHOLE") for pair in pairs]
        if condition == CONDITIONS[0]:
            supplements = [component, whole]
        elif condition == CONDITIONS[1]:
            supplements = [[value for position in range(start, start + 4)
                            for value in (component[position], whole[position])]
                           for start in (0, 4)]
        else:
            supplements = [whole, deepcopy(whole)]
        phase_batches.extend(("SUPPLEMENT_%d" % (i + 1), rows)
                             for i, rows in enumerate(supplements))
        phase_batches.append(("OLD_SKILL_MAINTENANCE", supplied["OLD_SKILL_MAINTENANCE"]))
        slot_index = 0
        for phase, raw in phase_batches:
            tasks = []
            for task in raw:
                task = _annotate(task, task.get("teaching_role", "MAINTENANCE" if
                                 phase == "OLD_SKILL_MAINTENANCE" else "CFC_FOUNDATION"))
                if public_transform is not None:
                    immutable = {key: deepcopy(task.get(key)) for key in
                                 ("correct", "encoded_correct_index", "encoded_options",
                                  "family_id", "semantic_question_id", "op")}
                    transformed = public_transform(deepcopy(task), round_index=round_index,
                                                   slot_index=slot_index, condition=condition)
                    require(all(transformed.get(key) == value for key, value in immutable.items()),
                            "COMPLEMENTARY_TRANSFORM_SEMANTIC_MUTATION")
                    task = transformed
                    task["public_input_sha256"] = public_identity(task)
                tasks.append(task)
                slot_index += 1
            batches.append({"cursor": len(batches), "round": round_index + 1,
                            "phase": phase, "depth": depth, "tasks": tasks})
        require(slot_index == 72, "COMPLEMENTARY_ROUND_EXPOSURE_DRIFT")
    identity = digest({"seed": seed, "condition": condition, "batches": batches})
    return {"schema": PROFILE_ID, "candidate": IMPLEMENTATION_ID, "seed": seed,
            "condition": condition, "depths": depths, "batches": batches,
            "schedule_sha256": identity, "pairs_by_round": pairs_by_round,
            "counts": schedule_counts(batches)}


def schedule_counts(batches):
    tasks = [task for batch in batches for task in batch["tasks"]]
    return {"decisions": len(tasks), "optimizer_updates": len(batches),
            "rounds": len({batch["round"] for batch in batches}),
            "batch_core_forward_calls_planned": sum(batch["depth"] for batch in batches),
            "batch_core_count_scope": "Batched-equivalent update-depth units only. Sequential production execution makes sample_core_passes_planned actual core invocations.",
            "sample_core_passes_planned": sum(batch["depth"] * len(batch["tasks"]) for batch in batches),
            "unique_semantic_questions": len({task["semantic_question_id"] for task in tasks}),
            "duplicate_semantic_exposures": len(tasks) - len({task["semantic_question_id"] for task in tasks}),
            "by_role": dict(Counter(task["teaching_role"] for task in tasks))}


def task_index(schedule):
    index = {}
    for batch in schedule["batches"]:
        for task in batch["tasks"]:
            if task["record_id"] in index:
                require(public_identity(index[task["record_id"]]) == public_identity(task),
                        "COMPLEMENTARY_RECORD_ID_PUBLIC_COLLISION")
            index[task["record_id"]] = task
    return list(index.values())


def run_complementary_course(*, learner, schedule, batch_step, observer=None,
                             checkpoint=None, next_cursor=0, prior_rows=(),
                             deadline=None, clock=time.monotonic):
    """Sequential committed updates; observer reads only declared fixed points.

Recovery starts from a coherent saved bundle whose committed cursor equals row
count. A failed update is never retried in this invocation. The caller saves the
last committed checkpoint and original error for inspection.
"""
    require(0 <= next_cursor <= len(schedule["batches"]), "COMPLEMENTARY_CURSOR_RANGE")
    require(len(prior_rows) == next_cursor, "COMPLEMENTARY_RECOVERY_CURSOR_ROWS_MISMATCH")
    rows = list(prior_rows)
    live_identity = (id(learner), id(learner.module), id(learner.optimizer))
    if observer and next_cursor == 0:
        observer(learner, {"point": "initial", "round": 0, "cursor": 0})
    for batch in schedule["batches"][next_cursor:]:
        if deadline is not None and clock() >= deadline:
            return {"status": "TEACHING_INCOMPLETE", "rows": rows, "next_cursor": len(rows)}
        require(live_identity == (id(learner), id(learner.module), id(learner.optimizer)),
                "COMPLEMENTARY_LEARNER_OR_OPTIMIZER_REPLACED")
        require(batch["cursor"] == len(rows), "COMPLEMENTARY_UPDATE_CURSOR_DRIFT")
        learner.set_depth(batch["depth"])
        before = learner.checkpoint_identity()
        started = clock()
        outcome = batch_step(learner, batch["tasks"])
        require(outcome["optimizer_steps"] == 1, "COMPLEMENTARY_ONE_UPDATE_PER_BATCH")
        require(len(outcome.get("episodes", [])) == len(batch["tasks"]),
                "COMPLEMENTARY_ACTUAL_FINAL_PREDICTIONS_REQUIRED")
        row = {key: batch[key] for key in ("cursor", "round", "phase", "depth")}
        row.update({"sample_ids": [task["record_id"] for task in batch["tasks"]],
                    "semantic_question_ids": [task["semantic_question_id"] for task in batch["tasks"]],
                    "public_input_sha256": [public_identity(task) for task in batch["tasks"]],
                    "weight_before": before, "weight_after": learner.checkpoint_identity(),
                    "optimizer_steps": 1, "episodes": outcome["episodes"],
                    "mean_loss": outcome["mean_loss"], "elapsed_seconds": clock() - started,
                    "update_sequence": ["before_snapshot", "final_forward_prediction",
                                        "teacher_release", "loss", "backward", "optimizer_step", "commit_cursor"]})
        rows.append(row)
        if checkpoint:
            checkpoint(learner, len(rows), rows, "committed")
        points = {"RETURN_TO_CUBE": "after_common_return_before_supplement",
                  "SUPPLEMENT_1": "after_supplement_update_1",
                  "SUPPLEMENT_2": "after_supplement_update_2",
                  "OLD_SKILL_MAINTENANCE": "after_maintenance"}
        if observer and batch["round"] in MONITOR_ROUNDS and batch["phase"] in points:
            observer(learner, {"point": points[batch["phase"]], "round": batch["round"],
                               "cursor": len(rows)})
    return {"status": "TEACHING_COMPLETE", "rows": rows, "next_cursor": len(rows),
            "schedule_sha256": schedule["schedule_sha256"]}
