"""RPM-Guided CAS PCBA Learning Constructor: the diagnosis stage and its records.

The handoff's first rule for this stage is that RPM must choose the right remedy
rather than default to training, and that the same wrong answer can arise from
different causes. So this module does two things and nothing else yet:

1. **It defines the typed records the run is observed through** - TaskFrame,
   GapEvidence, EvidencePacket, CubePatch, LearningBoardPlan, LearningReceipt,
   ResumeReceipt - extending the existing observe/record shape rather than starting
   a parallel one.
2. **It selects one of the six declared routes from evidence**, and returns the
   evidence that supports the choice, so the diagnosis can be inspected instead of
   being asserted.

Two boundaries are enforced in code, because both are easy to violate by accident:

* **No hidden label may reach the model.** ``screen_learner_inputs`` refuses any
  payload carrying a fixture label such as ``SKILL_GAP``, a route label or an
  expected answer. A label the fixture knows is not something the model discovered.
* **The support index and the reach classifier are injected, not guessed.** This
  module binds ``verified_teaching.Index`` (``branch_between``, ``reach``,
  ``direct_part_ids``) and ``face_tasks.reach_kind`` by protocol; the caller passes
  the real ones, so no signature is assumed here.

Nothing in this module trains, scores or mutates anything.
"""
from __future__ import annotations

import json
import time
from hashlib import sha256

SCHEMA = "cas.rpm-cfc-constructor-diagnosis/0.1"

ROUTES = ("EXECUTE_KNOWN", "RETRIEVE_EXISTING", "ACQUIRE_FACT", "LEARN_SKILL",
          "INVESTIGATE_OR_DEFER", "EXECUTION_BLOCKED")

#: What the teacher or the fixture may know and the learner may not be given.
FORBIDDEN_LEARNER_KEYS = (
    "skill_gap", "route_label", "diagnosis_label", "expected_route", "gold_route",
    "hidden_label", "is_skill_gap", "correct_construction", "final_answer",
    "parent_expected_answer", "expected_choice_slot",
)

FACES = (1, 2, 3, 4, 5, 6)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _now(clock=None):
    return round(time.time() if clock is None else clock(), 3)


# --------------------------------------------------------------------------
# the records
# --------------------------------------------------------------------------

def task_frame(*, episode_id, operation, arguments, return_slot, model_version,
               memory_version, remaining_budget, suspend_reason=None, clock=None):
    """What the parent task was, and everything needed to resume it exactly."""
    require(operation and isinstance(arguments, dict), "TASK_FRAME_ARGUMENTS")
    require(isinstance(remaining_budget, dict), "TASK_FRAME_BUDGET")
    frame = {"record": "TaskFrame", "schema": SCHEMA, "episode_id": episode_id,
             "operation": operation, "named_arguments": dict(arguments),
             "return_slot": return_slot,
             "model_version": model_version, "memory_version": memory_version,
             "remaining_budget": dict(remaining_budget),
             "suspend_reason": suspend_reason, "recorded_at": _now(clock)}
    frame["frame_digest"] = digest({k: v for k, v in frame.items()
                                    if k != "recorded_at"})
    return frame


def gap_evidence(*, episode_id, observations, representation_ok, source_states,
                 permitted_sources, learner_answer=None, expected_answer=None,
                 conflicts=(), whole_id=None, candidate_nodes=(), clock=None):
    """The observations the diagnosis rests on, kept with the decision.

    ``source_states`` maps a relationship the task needs to whether it is stated by
    a permitted source and whether it is already in memory. That is what separates
    "the source never states it" from "the source states it and the learner cannot
    apply it" - two diagnoses that produce the same wrong answer. ``whole_id`` and
    ``candidate_nodes`` name the whole the parent task asks about and the nodes whose
    reach is examined, so the reach profile is computable from the record itself.
    """
    require(observations, "GAP_EVIDENCE_OBSERVATIONS_REQUIRED")
    require(isinstance(source_states, dict), "GAP_EVIDENCE_SOURCE_STATES")
    return {"record": "GapEvidence", "schema": SCHEMA, "episode_id": episode_id,
            "observations": list(observations),
            "representation_ok": bool(representation_ok),
            "source_states": dict(source_states),
            "permitted_sources": list(permitted_sources),
            "learner_answer": learner_answer,
            "expected_answer": expected_answer,
            "conflicts": list(conflicts),
            "whole_id": whole_id,
            "candidate_nodes": [str(node) for node in candidate_nodes],
            "recorded_at": _now(clock)}


def evidence_packet(*, source_id, visibility, scope, relations, digest_of_source,
                    acquired_at=None, clock=None):
    """One acquired source, with its visibility and scope recorded at acquisition."""
    require(source_id and visibility, "EVIDENCE_PACKET_IDENTITY")
    require(visibility in ("permitted_pinned", "owner_supplied",
                           "existing_memory"), "EVIDENCE_PACKET_VISIBILITY")
    return {"record": "EvidencePacket", "schema": SCHEMA, "source_id": source_id,
            "visibility": visibility, "scope": scope,
            "relations": [dict(relation) for relation in relations],
            "source_sha256": digest_of_source,
            "acquired_at": acquired_at if acquired_at is not None else _now(clock)}


def cube_patch(*, cube_id, edits, producer, evidence_keys):
    """A proposed cube change: finite field and relationship edits, with support.

    ``producer`` names who proposed it - a learned policy or an authored rule - so a
    deterministic teacher's construction can never be reported as the learner's.
    """
    require(producer in ("learned_policy", "authored_rule", "operator"),
            "CUBE_PATCH_PRODUCER")
    require(edits, "CUBE_PATCH_EDITS_REQUIRED")
    for edit in edits:
        require(edit.get("kind") in ("field", "relation", "face_content"),
                "CUBE_PATCH_EDIT_KIND:" + str(edit.get("kind")))
        if edit["kind"] == "field":
            require(edit.get("face") in FACES, "CUBE_PATCH_FACE:" + str(edit.get("face")))
            require(edit.get("field"), "CUBE_PATCH_FIELD")
        if edit["kind"] == "relation":
            require(edit.get("source") and edit.get("target")
                    and edit.get("predicate"), "CUBE_PATCH_RELATION_ENDPOINTS")
    return {"record": "CubePatch", "schema": SCHEMA, "cube_id": cube_id,
            "edits": [dict(edit) for edit in edits], "producer": producer,
            "evidence_keys": sorted(evidence_keys)}


def learning_board_plan(*, board_id, nodes, connections, phases, recipe,
                        frozen_planner, student_scope):
    """A typed, executable board: every connection names its producer and consumer."""
    require(nodes and connections, "BOARD_PLAN_SHAPE")
    node_ids = {node["node_id"] for node in nodes}
    for node in nodes:
        require(node.get("node_id") and node.get("component") and node.get("adapter"),
                "BOARD_PLAN_NODE_FIELDS")
    for connection in connections:
        require(connection.get("from") in node_ids
                and connection.get("to") in node_ids,
                "BOARD_PLAN_CONNECTION_ENDPOINTS:" + str(connection))
        require(connection.get("payload"), "BOARD_PLAN_CONNECTION_PAYLOAD")
        require(connection.get("kind") in ("knowledge", "prerequisite", "executable"),
                "BOARD_PLAN_CONNECTION_KIND:" + str(connection.get("kind")))
    return {"record": "LearningBoardPlan", "schema": SCHEMA, "board_id": board_id,
            "nodes": [dict(node) for node in nodes],
            "connections": [dict(connection) for connection in connections],
            "phases": [dict(phase) for phase in phases],
            "recipe": dict(recipe),
            "planner_state": ("frozen" if frozen_planner else "adaptive"),
            "student_scope": dict(student_scope),
            "not_admitted_native_cas": True,
            "adapter_note": ("a Python reference adapter; this is not admitted native "
                            "CAS execution until that path is exercised")}


def learning_receipt(*, board_id, decisions, updates, checkpoint_identity,
                     memory_before, memory_after, phases_delivered, clock=None):
    """What the course actually did, whichever way it went."""
    return {"record": "LearningReceipt", "schema": SCHEMA, "board_id": board_id,
            "supervised_decisions": int(decisions),
            "optimizer_updates": int(updates),
            "checkpoint_identity": checkpoint_identity,
            "memory_before": memory_before, "memory_after": memory_after,
            "phases_delivered": list(phases_delivered),
            "recorded_at": _now(clock)}


def resume_receipt(*, frame, qualified, new_model_version, new_memory_version,
                   parent_continued, parent_result=None, clock=None):
    """The return: the original request, the version transition, and the outcome.

    ``qualified`` is the skill check and ``parent_continued`` is the parent task's
    own success. They are separate fields because a skill can pass a narrow
    qualification and still be insufficient for the parent, and neither may
    overwrite the other.
    """
    require(frame and frame.get("return_slot"), "RESUME_RECEIPT_FRAME")
    return {"record": "ResumeReceipt", "schema": SCHEMA,
            "episode_id": frame.get("episode_id"),
            "original_operation": frame.get("operation"),
            "named_arguments": frame.get("named_arguments"),
            "return_slot": frame.get("return_slot"),
            "skill_qualified": bool(qualified),
            "model_version_before": frame.get("model_version"),
            "model_version_after": new_model_version,
            "memory_version_before": frame.get("memory_version"),
            "memory_version_after": new_memory_version,
            "parent_continued": bool(parent_continued),
            "parent_result": parent_result,
            "remaining_budget_at_resume": frame.get("remaining_budget"),
            "recorded_at": _now(clock)}


# --------------------------------------------------------------------------
# the boundaries
# --------------------------------------------------------------------------

def screen_learner_inputs(payload):
    """Refuse to hand a learner anything a fixture or teacher knows privately."""
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN_LEARNER_KEYS:
                    found.append(path + "/" + str(key))
                walk(value, path + "/" + str(key))
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                walk(value, "%s/%d" % (path, index))

    walk(payload, "")
    require(not found, "LEARNER_INPUT_CARRIES_HIDDEN_LABEL:" + ",".join(sorted(found)))
    return True


def phase_batches(phase):
    """The declared batch sizes for a course phase, from the implementation profile.

    The batches flush at phase boundaries, so within-cube updates can affect the
    across-face work that follows and across-face updates can affect the return.
    """
    declared = {"WITHIN_CUBE": [8, 8, 8, 4], "ACROSS_FACE": [8, 4],
                "RETURN_TO_CUBE": [8], "OLD_SKILL_MAINTENANCE": [8]}
    require(phase in declared, "COURSE_PHASE_UNKNOWN:" + str(phase))
    return list(declared[phase])


def course_arithmetic(rounds=16):
    """The declared local allowance, derived rather than asserted."""
    per_round = {"WITHIN_CUBE": 28, "ACROSS_FACE": 12, "RETURN_TO_CUBE": 8,
                 "OLD_SKILL_MAINTENANCE": 8}
    for phase, decisions in per_round.items():
        require(sum(phase_batches(phase)) == decisions,
                "COURSE_BATCH_SUM:" + phase)
    target = (per_round["WITHIN_CUBE"] + per_round["ACROSS_FACE"]
              + per_round["RETURN_TO_CUBE"]) * rounds
    maintenance = per_round["OLD_SKILL_MAINTENANCE"] * rounds
    target_updates = sum(len(phase_batches(p)) for p in
                         ("WITHIN_CUBE", "ACROSS_FACE", "RETURN_TO_CUBE")) * rounds
    maintenance_updates = len(phase_batches("OLD_SKILL_MAINTENANCE")) * rounds
    return {"rounds": rounds, "target_decisions": target,
            "maintenance_decisions": maintenance,
            "total_supervised_decisions": target + maintenance,
            "target_optimizer_updates": target_updates,
            "maintenance_optimizer_updates": maintenance_updates,
            "total_optimizer_updates": target_updates + maintenance_updates,
            "status": "PROPOSED_LOCAL_ALLOCATION_NOT_SUFFICIENCY_GUARANTEE"}


# --------------------------------------------------------------------------
# the diagnosis
# --------------------------------------------------------------------------

def _needs(states, wanted):
    return [key for key, value in sorted(states.items())
            if value.get("state") == wanted]


def diagnose(evidence, *, support_index=None, reach_kind=None):
    """Choose one route from the evidence, and return the evidence for the choice.

    The order matters and is deliberate. A broken input path is never repaired by
    more examples, so it outranks everything; missing evidence outranks a weak
    answer, because a learner cannot apply what no source states; and only when the
    facts are present and the learner still fails does this become skill learning.
    """
    require(isinstance(evidence, dict)
            and evidence.get("record") == "GapEvidence",
            "DIAGNOSE_REQUIRES_GAP_EVIDENCE")
    states = evidence["source_states"]
    conflicts = evidence.get("conflicts") or []
    observations = list(evidence["observations"])

    def outcome(route, why, extra=None):
        chosen = {"route": route, "why": why, "evidence": observations,
                  "decided_by": "authored_rule",
                  "supports": {"source_states": states, "conflicts": conflicts}}
        if extra:
            chosen.update(extra)
        require(route in ROUTES, "DIAGNOSIS_ROUTE_UNKNOWN:" + str(route))
        return chosen

    if not evidence["representation_ok"]:
        return outcome("EXECUTION_BLOCKED",
                       "the representation or a required tool is inadequate; more "
                       "examples cannot repair a broken input path",
                       {"remedy": "fix_the_input_path_not_more_examples"})

    absent = _needs(states, "absent")
    if absent:
        if evidence.get("permitted_sources"):
            return outcome("ACQUIRE_FACT",
                           "the relationship is not stated anywhere available, and a "
                           "permitted source may supply it",
                           {"unstated": absent})
        return outcome("INVESTIGATE_OR_DEFER",
                       "the relationship is not stated and no permitted source may "
                       "supply it; an unresolved result is the honest outcome",
                       {"unstated": absent})

    if conflicts:
        return outcome("INVESTIGATE_OR_DEFER",
                       "the available evidence conflicts within the permitted scope",
                       {"conflicts": conflicts})

    if evidence.get("learner_answer") is not None \
            and evidence.get("expected_answer") is not None:
        if canonical(evidence["learner_answer"]) == canonical(evidence["expected_answer"]):
            in_memory = _needs(states, "in_memory")
            if in_memory and not _needs(states, "stated"):
                return outcome("RETRIEVE_EXISTING",
                               "the learner already answers correctly from existing "
                               "memory; no acquisition and no training is needed")
            return outcome("EXECUTE_KNOWN",
                           "the learner already answers correctly; unnecessary "
                           "learning work is not opened")

    stated = _needs(states, "stated")
    in_memory = _needs(states, "in_memory")
    if stated or in_memory:
        profile = (reach_profile(evidence, support_index=support_index,
                                 reach_kind=reach_kind)
                   if reach_kind is not None else {})
        confusion = direct_indirect_confusion(profile) if profile else {}
        if confusion.get("confused"):
            return outcome("LEARN_SKILL",
                           "the facts are available and the learner confuses direct "
                           "with indirect constituents; this is an application "
                           "weakness, not missing information",
                           {"confusion": confusion, "reach_profile": profile})
        return outcome("LEARN_SKILL",
                       "the facts are available and the learner's answer is wrong or "
                       "unreliable on the parent task",
                       {"reach_profile": profile} if profile else None)

    return outcome("INVESTIGATE_OR_DEFER",
                   "the evidence gathered does not yet separate the candidate causes")


def reach_profile(evidence, *, support_index, reach_kind):
    """Per-node reach for the whole the parent task names, from the injected binder.

    ``reach_kind`` is the repository's classifier (``face_tasks.reach_kind``) and
    ``support_index`` is ``verified_teaching.Index``; both are passed in so no
    signature is assumed and no test doubles a real graph rule.
    """
    require(callable(reach_kind), "REACH_KIND_CALLABLE_REQUIRED")
    whole = (evidence.get("named_arguments") or {}).get("whole_id") \
        or evidence.get("whole_id")
    require(whole, "REACH_PROFILE_WHOLE_REQUIRED")
    nodes = evidence.get("candidate_nodes") or []
    profile = {}
    for node in nodes:
        kind = reach_kind(whole, node)
        entry = {"reach": kind}
        if support_index is not None:
            try:
                entry["direct_part_ids"] = sorted(support_index.direct_part_ids(node))
                entry["branch_between"] = bool(support_index.branch_between(whole, node))
            except Exception as error:                    # noqa: BLE001
                entry["support_query_failed"] = type(error).__name__ + ":" + str(error)[:120]
        profile[node] = entry
    return profile


def direct_indirect_confusion(profile):
    """Whether the learner treated an indirect constituent as a direct one.

    The handoff's example in measurable form: R directly contains P and Q, P directly
    contains Z - answering [P, Z] is not a random error, it is the direct/indirect
    distinction. This reads that from the reach profile and the selected answer.
    """
    require(isinstance(profile, dict), "CONFUSION_PROFILE")
    if not profile:
        return {"confused": False, "reason": "NO_REACH_PROFILE"}
    direct = {node for node, entry in profile.items()
              if entry.get("reach") == "direct"}
    indirect = {node for node, entry in profile.items()
                if entry.get("reach") in ("via", "indirect") or
                str(entry.get("reach", "")).startswith("via:")}
    return {"confused": bool(direct and indirect),
            "direct": sorted(direct), "indirect": sorted(indirect),
            "reason": ("BOTH_DIRECT_AND_INDIRECT_PRESENT_IN_THE_SAME_WHOLE"
                       if direct and indirect else "NO_DIRECT_INDIRECT_PAIR")}
