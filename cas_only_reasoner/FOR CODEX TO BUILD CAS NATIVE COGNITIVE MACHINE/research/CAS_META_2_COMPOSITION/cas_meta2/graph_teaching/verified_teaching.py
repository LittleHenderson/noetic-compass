"""CUBE_VERIFIED_TEACHING_001 — a deterministic teacher over the cube graph.

STATUS: ``TEACHING_DATA_READY_NEURAL_UNTESTED``. Data structures, teacher checks,
lesson compilation, task-binding specifications and non-neural tests only. No
model loading, no neural execution, no training, no reservation, no AWS call, no
accepted-model change.

What this module adds to the cube work:

    the public graph
          -> small component questions (existing REACHED_VIA semantics)
          -> teacher-checked answers with grounded witnesses
          -> a checked explanation connecting the component decisions
          -> the original complete-answer question

Two boundaries it enforces mechanically:

* **The teacher's component answers never build the learner's final answer.**
  ``TeachingTrace.final_prediction_receives_component_answers`` is false, each
  exercise's public record carries only its own graph, question and choices
  (``prefix_mode: "none"``), and the compiler refuses to attach component
  answers to a final exercise.
* **A false intermediate explanation disqualifies a positive trace.** The trace
  verifier checks every component step; if one step is false the trace is
  rejected even when the final list answer happens to be right, and the faulty
  step is retained separately as a negative example.

Public identity follows the delivered fixture's own rule, verified against it:
``sha256`` of compact sorted-key UTF-8 JSON of the record minus its own id, with
the repository's ``canonical()`` as the working binding (identical for ASCII
content; a versioned translation is declared for non-ASCII). One authored value
is *not* reproduced — the fixture's ``public_context_digest`` — and that
mismatch is reported rather than papered over.

Nothing here is a CAS implementation supplied or validated by rStar-Math. MCTS,
learned preference models, Q-values, ranking losses and self-evolution loops are
not implemented.
"""
from __future__ import annotations

import inspect
import itertools
import json
import random
from hashlib import sha256
from pathlib import Path

from .graph import canonical, digest, require
from . import cube_node, reference

SCHEMA = "cas.cube-verified-teaching/0.1"
STATUS_READY = "TEACHING_DATA_READY_NEURAL_UNTESTED"
STATUS_AUTHORING = "DRAFT_AUTHORING_FIXTURE_NOT_REPOSITORY_VALIDATED"

TASK_PROFILES = ("component-route/0.1", "whole-answer/0.1")
VISIBILITY_PROFILE = "graph-only/0.1"
PREFIX_MODE = "none"

PHASES = ("DEMONSTRATION", "PREDICT_THEN_CORRECT", "UNASSISTED_MEASUREMENT")
ASSISTANCE_WORKED = "WORKED_SOLUTION_VISIBLE"
ASSISTANCE_NONE = "NONE"

PENDING = "PENDING_REFERENCE_CHECK"
PENDING_REASON = "PENDING_BUILDER_PREDICATE_VALIDATION"
VERIFIED = "VERIFIED"

WITNESS_KINDS = ("direct_branch", "path", "complete_scope_absence",
                 "complete_direct_inventory", "unique_shared_direct_constituent")

REASON_CODES = ("DIRECT_VS_INDIRECT", "FOREIGN_PART", "MISSING_REQUIRED_PART",
                "EXTRA_PART", "WRONG_WHOLE", "INCOMPLETE_INVENTORY")

CHECKER_IDENTITY = "cas_meta2.graph_teaching.reference@%s" % sha256(
    Path(reference.__file__).read_bytes()).hexdigest()[:16]

# §3: the named question roles and the reference function each one binds to.
# The positional order below is checked against the real signatures at import
# time; English phrasing is never used to infer argument order.
ROLE_BINDINGS = {
    "LIST_PARTS": {
        "named_roles": ("whole_id",),
        "function": "direct_parts",
        "parameters": ("graph", "idea_id"),
        "role_to_parameter": {"whole_id": "idea_id"},
    },
    "FIND_SHARED_PART": {
        "named_roles": ("first_whole_id", "second_whole_id"),
        "function": "shared_parts",
        "parameters": ("graph", "a", "b"),
        "role_to_parameter": {"first_whole_id": "a", "second_whole_id": "b"},
    },
    "REACHED_VIA": {
        "named_roles": ("whole_id", "candidate_id"),
        "function": "reach_kind",
        "parameters": ("graph", "part_id", "idea_id"),
        "role_to_parameter": {"whole_id": "idea_id", "candidate_id": "part_id"},
    },
}


def _verify_role_bindings():
    """The declared parameter names must be the real ones, in the real order."""
    for operation, binding in ROLE_BINDINGS.items():
        function = getattr(reference, binding["function"])
        actual = tuple(inspect.signature(function).parameters)
        require(actual == binding["parameters"],
                "VT_REFERENCE_SIGNATURE_CHANGED:%s:%s" % (operation, actual))
        require(sorted(binding["role_to_parameter"].values())
                == sorted(name for name in binding["parameters"] if name != "graph"),
                "VT_ROLE_BINDING_INCOMPLETE:" + operation)


_verify_role_bindings()


def reference_arguments(operation, named_arguments):
    """Positional arguments in the reference function's own order."""
    require(operation in ROLE_BINDINGS, "VT_OPERATION_UNSUPPORTED:" + str(operation))
    binding = ROLE_BINDINGS[operation]
    require(set(named_arguments) == set(binding["named_roles"]),
            "VT_NAMED_ROLES_MISMATCH:%s:%s" % (operation, sorted(named_arguments)))
    for role, node_id in named_arguments.items():
        require(type(node_id) is str and node_id, "VT_ARGUMENT_ID:" + role)
    ordered = {name: None for name in binding["parameters"]}
    for role, parameter in binding["role_to_parameter"].items():
        ordered[parameter] = named_arguments[role]
    return {"operation": operation, "function": binding["function"],
            "positional_keywords": ordered,
            "call": "%s(%s)" % (binding["function"],
                                ", ".join("%s=%s" % (name, ordered[name])
                                          for name in binding["parameters"]))}


# --------------------------------------------------------------------------
# context and the label/node-index helpers
# --------------------------------------------------------------------------

def lesson_context(bundle, view_id="view_context"):
    """The learner-readable public context, matching the delivered fixture."""
    labels = cube_node.view_labels(bundle, view_id)
    context = {
        "schema_version": SCHEMA,
        "scene_id": bundle["context"]["context_id"],
        "view_id": view_id,
        "nodes": [{"node_id": node["node_id"], "label": labels[node["node_id"]]}
                  for node in sorted(bundle["cube_nodes"],
                                     key=lambda item: item["node_id"])],
        "branches": [{"branch_id": branch["branch_id"],
                      "source_node_id": branch["source_node_id"],
                      "predicate": branch["predicate"],
                      "target_node_id": branch["target_node_id"]}
                     for branch in sorted(bundle["branches"],
                                          key=lambda item: item["branch_id"])],
        "contains_inventory": ("complete" if bundle["context"]["contains_inventory_complete"]
                               else "incomplete"),
    }
    context["candidate_universe"] = [node["node_id"] for node in context["nodes"]]
    context["context_id"] = "ctx:" + _public_digest(context)
    return context


def _public_digest(value):
    """Compact sorted-key JSON digest; the repository canonicalization profile."""
    return sha256(canonical(value)).hexdigest()


class Index:
    """Label<->node-id maps, outgoing contains branches, and answer lookups."""

    def __init__(self, bundle, context, view_id="view_context"):
        self.bundle = bundle
        self.context = context
        self.view_id = view_id
        self.graph = cube_node.containment_graph(bundle, view_id)
        self.label_of = {node["node_id"]: node["label"] for node in context["nodes"]}
        self.node_of = {label: node_id for node_id, label in self.label_of.items()}
        self.branch_of = {branch["branch_id"]: branch for branch in context["branches"]}
        self.outgoing = {node_id: sorted(
            (branch for branch in context["branches"]
             if branch["source_node_id"] == node_id
             and branch["predicate"] == "contains"),
            key=lambda item: item["branch_id"]) for node_id in self.label_of}
        self.complete = context["contains_inventory"] == "complete"

    def branch_between(self, source_id, target_id):
        found = [branch["branch_id"] for branch in self.outgoing[source_id]
                 if branch["target_node_id"] == target_id]
        require(len(found) == 1, "VT_BRANCH_NOT_UNIQUE:%s:%s" % (source_id, target_id))
        return found[0]

    def direct_parts(self, whole_id):
        """Labels, computed by the repository checker on the label graph."""
        return reference.direct_parts(self.graph, self.label_of[whole_id])

    def direct_part_ids(self, whole_id):
        return [self.node_of[label] for label in self.direct_parts(whole_id)]

    def reach(self, whole_id, candidate_id):
        """('direct'|'via:<label>'|'absent', hop_node_id_or_None)."""
        value = reference.reach_kind(self.graph, self.label_of[candidate_id],
                                    self.label_of[whole_id])
        hop = self.node_of[value[4:]] if value.startswith("via:") else None
        return value, hop

    def shared(self, first_id, second_id):
        return reference.shared_parts(self.graph, self.label_of[first_id],
                                      self.label_of[second_id])

    def path(self, whole_id, candidate_id):
        """The supported hop sequence whole -> ... -> candidate, or None."""
        _, hop = self.reach(whole_id, candidate_id)
        if hop is None:
            return None
        return [whole_id, hop, candidate_id] if hop != candidate_id else None


# --------------------------------------------------------------------------
# public exercises
# --------------------------------------------------------------------------

def choice_record(value):
    return {"choice_id": "choice:" + _public_digest(value), "value": value}


def public_exercise_digest(exercise):
    """Digest of the COMPLETE public exercise, its own id included.

    This is the scope the delivered fixture meant by its ``public_context_digest``
    field: "context" there was the whole decision context (graph, question and
    choices), not the shared graph. All sixteen authored values reproduce under
    this rule; the earlier reading of the field as a graph digest was wrong and
    is reported as such.
    """
    return _public_digest(exercise)


def public_graph_digest(context):
    """Digest of the shared graph context only: scene, view, nodes, branches.

    A different scope from :func:`public_exercise_digest`, so the two carry
    different names.
    """
    return _public_digest({key: value for key, value in context.items()
                           if key != "context_id"})


def public_exercise(context, task_profile, operation, named_arguments, choice_values,
                    view_id="view_context"):
    """One public exercise. Exactly three distinct choices; no target inside."""
    require(task_profile in TASK_PROFILES, "VT_TASK_PROFILE_UNKNOWN:" + str(task_profile))
    require(operation in ROLE_BINDINGS, "VT_OPERATION_UNSUPPORTED:" + str(operation))
    values = [list(value) if isinstance(value, (list, tuple)) else value
              for value in choice_values]
    require(len(values) == 3, "VT_EXACTLY_THREE_CHOICES:%d" % len(values))
    require(len({canonical(value) for value in values}) == 3,
            "VT_CHOICES_NOT_DISTINCT")
    reference_arguments(operation, named_arguments)
    exercise = {
        "schema_version": SCHEMA,
        "context_id": context["context_id"],
        "task_profile": task_profile,
        "question": {"operation": operation, "named_arguments": dict(named_arguments)},
        "choices": [choice_record(value) for value in values],
        "visibility_profile": VISIBILITY_PROFILE,
        "prefix_mode": PREFIX_MODE,
    }
    exercise["exercise_id"] = "exercise:" + _public_digest(exercise)
    return exercise


def exercise_choice_values(exercise):
    return [choice["value"] for choice in exercise["choices"]]


def choice_id_for_value(exercise, value):
    for choice in exercise["choices"]:
        if canonical(choice["value"]) == canonical(value):
            return choice["choice_id"]
    raise ValueError("VT_CHOICE_VALUE_ABSENT:" + canonical(value).decode("utf-8"))


def reach_choice_values(index, whole_id, candidate_id, answer, extra=None):
    """The three public values for one route question.

    The answer plus distractors from the failure families that apply: the other
    reach labels, and routes through cubes that are not constituents of the
    asked whole. A route through the candidate itself is not a route and is
    never offered. Built from the public graph only; the declared target is
    never an input.
    """
    own_label = index.label_of[candidate_id]
    fan_in = {label: 0 for label in index.label_of.values()}
    for node_id in index.label_of:
        for label in index.direct_parts(node_id):
            fan_in[label] += 1
    parts = sorted(index.direct_parts(whole_id),
                   key=lambda label: (-fan_in[label], label))
    pool = ["direct", "absent"]
    for label in parts:
        pool.append("via:" + label)
    for label in sorted(index.label_of.values()):
        pool.append("via:" + label)
    values = [answer]
    for candidate in pool:
        if len(values) == 3:
            break
        if candidate == "via:" + own_label:
            continue
        if any(canonical(candidate) == canonical(item) for item in values):
            continue
        values.append(candidate)
    if extra:
        for candidate in extra:
            if len(values) == 3:
                break
            if not any(canonical(candidate) == canonical(item) for item in values):
                values.append(candidate)
    require(len(values) == 3, "VT_REACH_CHOICE_POOL_TOO_SMALL")
    return values


def list_choice_values(index, whole_id, answer):
    """The complete list, one foreign-part substitute, one indirect substitute.

    Matches the documented illustrative set: for Bicycle that is
    ``[Frame, Wheel]``, ``[Frame, Platform]`` and ``[Rim, Wheel]``. Equal item
    counts on purpose. A foreign part belongs to another whole; an indirect part
    is reachable through a constituent.
    """
    require(answer, "VT_LIST_ANSWER_EMPTY")
    answer = sorted(answer)
    direct = set(index.direct_parts(whole_id))
    reachable = set(reference.transitive_parts(index.graph, index.label_of[whole_id]))
    part_labels = {index.label_of[branch["target_node_id"]]
                   for branch in index.context["branches"]
                   if branch["predicate"] == "contains"}
    foreign_parts = sorted(label for label in part_labels
                           if label not in direct and label not in reachable)
    indirect_parts = sorted(reachable - direct)
    substitutions = []
    if foreign_parts:
        substitutions.append(sorted(answer[:-1] + [foreign_parts[0]]))
    if indirect_parts:
        substitutions.append(sorted([indirect_parts[0]] + answer[1:]))
    values = [answer]
    for candidate in substitutions:
        if canonical(candidate) not in {canonical(item) for item in values}:
            values.append(candidate)
    if len(values) < 3:
        shorten = sorted(answer[:-1])
        if shorten and canonical(shorten) not in {canonical(item) for item in values}:
            values.append(shorten)
    require(len(values) == 3, "VT_LIST_CHOICE_POOL_TOO_SMALL")
    return values


def shared_choice_values(index, first_id, second_id, answer):
    """The shared constituent, the wrong ``none``, and a real but unshared part."""
    values = [answer, "none"]
    for label in index.direct_parts(first_id) + index.direct_parts(second_id):
        if len(values) == 3:
            break
        if canonical(label) == canonical(answer):
            continue
        if any(canonical(label) == canonical(item) for item in values):
            continue
        values.append(label)
    require(len(values) == 3, "VT_SHARED_CHOICE_POOL_TOO_SMALL")
    return values


# --------------------------------------------------------------------------
# witnesses and reference verification
# --------------------------------------------------------------------------

def witness(kind, context_id, branch_refs=(), required_completeness=None):
    require(kind in WITNESS_KINDS, "VT_WITNESS_KIND_UNKNOWN:" + str(kind))
    return {"kind": kind, "context_id": context_id,
            "branch_refs": list(branch_refs),
            "required_completeness": required_completeness}


def _check_branches_exist(index, branch_refs):
    for branch_id in branch_refs:
        require(branch_id in index.branch_of, "VT_WITNESS_BRANCH_UNKNOWN:" + str(branch_id))


def verify_direct_branch(index, whole_id, candidate_id, branch_refs):
    """A direct claim must point at the real branch, in the right direction."""
    _check_branches_exist(index, branch_refs)
    require(candidate_id in index.direct_part_ids(whole_id),
            "VT_WITNESS_BRANCH_ENDPOINT_MISMATCH:%s:%s" % (whole_id, candidate_id))
    expected = index.branch_between(whole_id, candidate_id)
    require(len(branch_refs) == 1 and branch_refs[0] == expected,
            "VT_WITNESS_BRANCH_ENDPOINT_MISMATCH:%s:%s" % (whole_id, candidate_id))
    return {"obligation": "whole directly contains candidate",
            "branch": expected,
            "source_node_id": whole_id, "target_node_id": candidate_id}


def verify_path(index, whole_id, candidate_id, branch_refs):
    """An indirect claim must identify the supported connecting path."""
    _check_branches_exist(index, branch_refs)
    expected_path = index.path(whole_id, candidate_id)
    require(expected_path is not None, "VT_WITNESS_PATH_NOT_INDIRECT")
    hops = []
    current = whole_id
    for branch_id in branch_refs:
        branch = index.branch_of[branch_id]
        require(branch["predicate"] == "contains",
                "VT_WITNESS_PATH_PREDICATE:" + branch_id)
        require(branch["source_node_id"] == current,
                "VT_WITNESS_PATH_NOT_CONTIGUOUS:%s:%s" % (branch_id, current))
        hops.append(current)
        current = branch["target_node_id"]
    hops.append(current)
    require(hops == expected_path,
            "VT_WITNESS_PATH_MISMATCH:%s:%s" % (hops, expected_path))
    return {"obligation": "candidate is reached through a supported chain",
            "hops": hops}


def verify_complete_scope_absence(index, whole_id, candidate_id, branch_refs,
                                  required_completeness):
    """Absence needs a complete inventory; otherwise the answer is unknown."""
    require(required_completeness == "complete",
            "VT_WITNESS_ABSENCE_REQUIRES_COMPLETE_INVENTORY")
    require(index.complete, "VT_WITNESS_ABSENCE_IN_INCOMPLETE_CONTEXT")
    require(not branch_refs, "VT_WITNESS_ABSENCE_CARRIES_BRANCHES")
    value, _ = index.reach(whole_id, candidate_id)
    require(value == "absent", "VT_WITNESS_ABSENCE_CONTRADICTED:" + value)
    return {"obligation": "no contains path exists in a complete inventory",
            "inventory": index.context["contains_inventory"],
            "searched_from": whole_id, "candidate": candidate_id}


def verify_complete_direct_inventory(index, whole_id, expected_labels, branch_refs):
    """Both obligations: no foreign member, and no missing member."""
    _check_branches_exist(index, branch_refs)
    direct_labels = index.direct_parts(whole_id)
    expected = sorted(expected_labels)
    for label in expected:
        require(label in direct_labels, "VT_INVENTORY_FOREIGN_MEMBER:" + str(label))
    for label in direct_labels:
        require(label in expected, "VT_INVENTORY_MISSING_MEMBER:" + str(label))
    expected_branches = [index.branch_between(whole_id, index.node_of[label])
                         for label in direct_labels]
    require(sorted(branch_refs) == sorted(expected_branches),
            "VT_INVENTORY_BRANCH_SET_MISMATCH:%s" % sorted(branch_refs))
    require(index.complete, "VT_INVENTORY_REQUIRES_COMPLETE_CONTEXT")
    return {"obligation": "every listed item is a direct constituent and every "
                          "declared direct constituent is listed",
            "listed": expected, "declared": direct_labels,
            "branches": sorted(expected_branches)}


def verify_unique_shared(index, first_id, second_id, expected_label, branch_refs):
    _check_branches_exist(index, branch_refs)
    shared = index.shared(first_id, second_id)
    require(len(shared) == 1, "VT_SHARED_PART_NOT_UNIQUE:%d" % len(shared))
    require(shared[0] == expected_label, "VT_SHARED_PART_MISMATCH:" + str(shared))
    pair = sorted([index.branch_between(first_id, index.node_of[shared[0]]),
                   index.branch_between(second_id, index.node_of[shared[0]])])
    require(sorted(branch_refs) == pair,
            "VT_SHARED_WITNESS_ENDPOINT_MISMATCH:%s" % sorted(branch_refs))
    require(index.complete, "VT_SHARED_PART_REQUIRES_COMPLETE_CONTEXT")
    return {"obligation": "exactly one shared direct constituent, witnessed by "
                          "both containment branches",
            "shared": shared[0], "branches": pair}


def teacher_target(exercise, expected_answer, worked_explanation, witness_record,
                   origin="AUTHORED_ILLUSTRATIVE_EXPECTATION"):
    """A target starts unverified; only the checker can verify it."""
    return {
        "schema_version": SCHEMA,
        "exercise_id": exercise["exercise_id"],
        "expected_answer": expected_answer,
        "expected_choice_id": choice_id_for_value(exercise, expected_answer),
        "expected_slot": next(index for index, choice in enumerate(exercise["choices"])
                              if canonical(choice["value"]) == canonical(expected_answer)),
        "worked_explanation": worked_explanation,
        "witness": witness_record,
        "origin": origin,
        "reference_verification": {"status": PENDING, "checker_identity": None},
    }


def verify_target(index, exercise, target):
    """Run the repository checker and the witness obligations; fail closed."""
    operation = exercise["question"]["operation"]
    named = exercise["question"]["named_arguments"]
    value = exercise_choice_values(exercise)
    derived = reference_answer(index, exercise)
    codes = []
    if canonical(derived) != canonical(target["expected_answer"]):
        codes.append("VT_EXPECTED_ANSWER_NOT_DERIVED:%s:%s"
                     % (canonical(target["expected_answer"]).decode("utf-8"),
                        canonical(derived).decode("utf-8")))
    witness_record = target["witness"]
    require(witness_record["context_id"] == index.context["context_id"],
            "VT_WITNESS_CONTEXT_MISMATCH")
    refs = witness_record["branch_refs"]
    detail = None
    try:
        if witness_record["kind"] == "direct_branch":
            detail = verify_direct_branch(index, named["whole_id"],
                                          named["candidate_id"], refs)
        elif witness_record["kind"] == "path":
            detail = verify_path(index, named["whole_id"], named["candidate_id"], refs)
        elif witness_record["kind"] == "complete_scope_absence":
            detail = verify_complete_scope_absence(index, named["whole_id"],
                                                   named["candidate_id"], refs,
                                                   witness_record["required_completeness"])
        elif witness_record["kind"] == "complete_direct_inventory":
            detail = verify_complete_direct_inventory(index, named["whole_id"],
                                                      target["expected_answer"], refs)
        elif witness_record["kind"] == "unique_shared_direct_constituent":
            detail = verify_unique_shared(index, named["first_whole_id"],
                                          named["second_whole_id"],
                                          target["expected_answer"], refs)
    except ValueError as error:
        # A witness that fails its obligation rejects the target; it never
        # escapes as an exception, because a rejected step must be retained as a
        # negative example rather than crash the compiler.
        codes.append(str(error))
    require(canonical(target["expected_answer"]) in
            [canonical(item) for item in value],
            "VT_TARGET_VALUE_NOT_OFFERED")
    if codes:
        return {"status": "REJECTED", "codes": codes, "witness_detail": detail,
                "target": {**target, "reference_verification": {
                    "status": "REJECTED", "checker_identity": CHECKER_IDENTITY,
                    "derived_answer": derived, "codes": codes}}}
    verified = {**target,
                "reference_verification": {"status": VERIFIED,
                                           "checker_identity": CHECKER_IDENTITY,
                                           "derived_answer": derived,
                                           "witness_obligations": detail}}
    return {"status": VERIFIED, "codes": [], "target": verified,
            "witness_detail": detail}


def reference_answer(index, exercise):
    """The repository checker's answer for one exercise, in the value space."""
    operation = exercise["question"]["operation"]
    named = exercise["question"]["named_arguments"]
    if operation == "LIST_PARTS":
        return index.direct_parts(named["whole_id"])
    if operation == "FIND_SHARED_PART":
        shared = index.shared(named["first_whole_id"], named["second_whole_id"])
        require(len(shared) <= 1, "VT_SHARED_PART_AMBIGUOUS")
        return shared[0] if shared else "none"
    value, _ = index.reach(named["whole_id"], named["candidate_id"])
    return value


# --------------------------------------------------------------------------
# step contrasts
# --------------------------------------------------------------------------

def contrast_reason(index, exercise, positive_value, negative_value):
    """The verified failed obligation behind one negative choice, or None.

    Only emitted after the predicate is checked. An equally correct answer is
    never labelled a negative.
    """
    operation = exercise["question"]["operation"]
    named = exercise["question"]["named_arguments"]
    derived = reference_answer(index, exercise)
    if canonical(negative_value) == canonical(derived):
        return None  # an equally correct alternative is not a negative
    if canonical(positive_value) != canonical(derived):
        return None  # the pair does not contrast against the verified answer
    if operation == "REACHED_VIA":
        claim = negative_value
        if not isinstance(claim, str):
            return None
        if derived == "direct":
            # claiming an indirect route or absence when the item is a direct part
            return "DIRECT_VS_INDIRECT" if claim.startswith("via:") \
                else "MISSING_REQUIRED_PART"
        if derived.startswith("via:"):
            if claim == "direct":
                return "DIRECT_VS_INDIRECT"
            if claim.startswith("via:"):
                return "DIRECT_VS_INDIRECT"
            return "MISSING_REQUIRED_PART"
        # derived == "absent": the candidate is not part of this whole at all
        return "FOREIGN_PART"
    if operation == "LIST_PARTS":
        expected = sorted(derived)
        given = sorted(negative_value)
        if not isinstance(negative_value, list):
            return "WRONG_WHOLE"
        if len(given) < len(expected) and all(item in expected for item in given):
            return "MISSING_REQUIRED_PART"
        if len(given) > len(expected) and all(item in given for item in expected):
            return "EXTRA_PART"
        foreign = [item for item in given if item not in expected]
        if foreign:
            direct_labels = index.direct_parts(named["whole_id"])
            reachable = reference.transitive_parts(index.graph,
                                                   index.label_of[named["whole_id"]])
            if any(item in reachable and item not in direct_labels for item in foreign):
                return "DIRECT_VS_INDIRECT"
            return "FOREIGN_PART"
        return "MISSING_REQUIRED_PART"
    if operation == "FIND_SHARED_PART":
        if negative_value == "none":
            return "MISSING_REQUIRED_PART"
        whole = named["first_whole_id"]
        other = named["second_whole_id"]
        if negative_value in index.direct_parts(whole) and \
                negative_value not in index.direct_parts(other):
            return "FOREIGN_PART"
        return "WRONG_WHOLE"
    return None


def step_contrasts(index, exercise, target, public_graph, view_id="view_context"):
    """Positive choice against each verified negative, same public context.

    Two digests, two names, deliberately: ``public_graph_digest`` is the shared
    graph scope, and ``public_exercise_digest`` is the complete exercise scope the
    delivered fixture meant. The older ambiguous name ``public_context_digest``
    is not emitted; the translation is recorded in the export manifest.
    """
    derived = reference_answer(index, exercise)
    positive_id = choice_id_for_value(exercise, derived)
    records = []
    for choice in exercise["choices"]:
        if choice["choice_id"] == positive_id:
            continue
        reason = contrast_reason(index, exercise, derived, choice["value"])
        record = {
            "exercise_id": exercise["exercise_id"],
            "teacher_target_ref": exercise["exercise_id"],
            "positive_choice_id": positive_id,
            "negative_choice_id": choice["choice_id"],
            "public_graph_digest": public_graph,
            "public_exercise_digest": public_exercise_digest(exercise),
            "learner_visible": False,
            "reason_code": reason,
            "reason_status": ("VALIDATED" if reason else "NO_VERIFIED_PREDICATE"),
        }
        records.append(record)
    return records


def slot_alignment_check(context, index, exercise, target, view_id="view_context"):
    """Every permitted permutation must keep the target on its own choice.

    ``expected_slot`` is derived from the position of ``expected_choice_id`` in
    the exercise's final ordered choices, so it must follow the choices through
    all six orderings of three. A balanced slot count is not what proves target
    independence; this alignment check plus the boundary readings are.
    """
    values = exercise_choice_values(exercise)
    answer = target["expected_answer"]
    readings = []
    for permutation in itertools.permutations(range(3)):
        permuted = [values[position] for position in permutation]
        rebuilt = public_exercise(context, exercise["task_profile"],
                                  exercise["question"]["operation"],
                                  exercise["question"]["named_arguments"],
                                  permuted, view_id)
        moved = teacher_target(rebuilt, answer, target["worked_explanation"],
                               target["witness"])
        slot_choice = rebuilt["choices"][moved["expected_slot"]]
        readings.append({
            "permutation": list(permutation),
            "exercise_id": rebuilt["exercise_id"],
            "expected_slot": moved["expected_slot"],
            "expected_choice_id": moved["expected_choice_id"],
            "resolves_to_expected_choice":
                slot_choice["choice_id"] == moved["expected_choice_id"]
                and canonical(slot_choice["value"]) == canonical(answer),
        })
    return {"exercise_id": exercise["exercise_id"],
            "readings": readings,
            "permutations_checked": len(readings),
            "all_permutations_align": all(item["resolves_to_expected_choice"]
                                          for item in readings),
            "rule": ("expected_slot is the position of expected_choice_id in this "
                     "exercise's final ordered choices")}


def export_manifest(report, ordering_mode):
    """One explicitly named ordering mode for one export of these artifacts."""
    require(ordering_mode in ("declared", "authored_fixture"),
            "VT_ORDERING_MODE_UNKNOWN:" + str(ordering_mode))
    slots = sorted(target["expected_slot"] for target in report["private_teacher_targets"])
    distribution = {str(slot): slots.count(slot) for slot in sorted(set(slots))}
    instruction = ("the three choices are permuted with a seed over the question "
                   "and the choice SET, so no slot depends on which choice is "
                   "correct")
    return {
        "schema_version": SCHEMA,
        "ordering_mode": ordering_mode,
        "ordering_rule": (instruction if ordering_mode == "declared" else
                          "the delivered fixture's authored choice order, adopted so "
                          "public identity reproduces; fixture reproduction only"),
        "slot_distribution_of_expected_answers": distribution,
        "expected_slot_rule": ("the position of expected_choice_id in this "
                               "exercise's final ordered choices"),
        "slot_alignment": report.get("slot_alignment_summary"),
        "field_translation": {
            "public_context_digest": ("delivered fixture's ambiguous name; it is the "
                                      "digest of the COMPLETE public exercise, "
                                      "including its exercise_id"),
            "public_exercise_digest": "the same scope under an unambiguous name",
            "public_graph_digest": "digest of the shared graph context only",
        },
        "artifacts": ["public_contexts.jsonl", "public_exercises.jsonl",
                      "teacher_targets.jsonl", "teacher_traces.jsonl",
                      "step_contrasts.jsonl", "cycle_plan.json"],
        "boundary": ("data only: no neural execution, no training, no reservation; "
                     "the graded cycle records every stage as compiled and not "
                     "delivered"),
    }


# --------------------------------------------------------------------------
# teaching trace
# --------------------------------------------------------------------------

def compile_trace(context, component_exercises, final_exercise, trace_id):
    """Component questions in order, then the complete-answer question."""
    require(component_exercises, "VT_TRACE_REQUIRES_COMPONENTS")
    require(final_exercise["context_id"] == context["context_id"],
            "VT_TRACE_CONTEXT_MISMATCH")
    for exercise in component_exercises:
        require(exercise["exercise_id"] != final_exercise["exercise_id"],
                "VT_TRACE_COMPONENT_REPEATS_FINAL")
        require(exercise["task_profile"] == "component-route/0.1",
                "VT_TRACE_COMPONENT_PROFILE")
    require(final_exercise["task_profile"] == "whole-answer/0.1",
            "VT_TRACE_FINAL_PROFILE")
    return {
        "schema_version": SCHEMA,
        "trace_id": trace_id,
        "context_id": context["context_id"],
        "component_exercise_ids": [exercise["exercise_id"]
                                   for exercise in component_exercises],
        "final_exercise_id": final_exercise["exercise_id"],
        "teacher_only": True,
        "final_prediction_receives_component_answers": False,
        "content_kind": "TEACHER_DEMONSTRATION_NOT_MODEL_INTERNAL_REASONING",
        "reference_verification": PENDING,
    }


def verify_trace(index, trace, exercises_by_id, targets_by_id):
    """Every component step must verify; a false step disqualifies the trace."""
    failures, corrections, negatives = [], [], []
    for step_number, exercise_id in enumerate(trace["component_exercise_ids"], start=1):
        exercise = exercises_by_id[exercise_id]
        target = targets_by_id.get(exercise_id)
        if target is None:
            failures.append({"step": step_number, "exercise_id": exercise_id,
                             "code": "VT_TRACE_STEP_WITHOUT_TARGET"})
            continue
        outcome = verify_target(index, exercise, target)
        if outcome["status"] != VERIFIED:
            failures.append({"step": step_number, "exercise_id": exercise_id,
                             "codes": outcome["codes"]})
            negatives.append({"step": step_number, "exercise_id": exercise_id,
                              "retained_as": "NEGATIVE_STEP_EXAMPLE",
                              "codes": outcome["codes"],
                              "target": target})
            continue
        corrections.append({"step": step_number, "exercise_id": exercise_id,
                            "expected_answer": target["expected_answer"],
                            "worked_explanation": target["worked_explanation"],
                            "witness": target["witness"],
                            "verification": outcome["target"]["reference_verification"]})
    final_id = trace["final_exercise_id"]
    final_target = targets_by_id.get(final_id)
    final_outcome = (verify_target(index, exercises_by_id[final_id], final_target)
                     if final_target else {"status": "REJECTED",
                                           "codes": ["VT_TRACE_FINAL_WITHOUT_TARGET"]})
    status = VERIFIED if (not failures and final_outcome["status"] == VERIFIED) \
        else "REJECTED"
    verified_trace = dict(trace)
    verified_trace["reference_verification"] = status
    return {"trace": verified_trace, "status": status,
            "component_corrections": corrections,
            "component_failures": failures,
            "retained_negatives": negatives,
            "final": final_outcome,
            "rule": ("a correct final answer does not excuse a false intermediate "
                     "explanation; the faulty step is retained as a negative")}


# --------------------------------------------------------------------------
# visibility and the answer boundary
# --------------------------------------------------------------------------

GRAPH_ONLY_WITHHELD = (
    "face_2.structured.fact_refs",
    "face_5.structured.direct_branch_refs",
    "face_6.structured.steps[*].uses_branch_refs",
    "face_6.structured.steps[*].text",
)


def graph_only_visibility(bundle, asked_nodes, view_id="view_context"):
    """The declared ``graph-only/0.1`` profile: keep the graph, withhold solutions.

    The withheld set reuses the single declaration list in ``cube_profile``,
    expanded over the cubes the exercise asks about. It is declared, not chosen
    from the answer, so the pattern cannot move when a target moves.
    """
    from . import cube_profile  # single declaration source, no cycle
    require(tuple(GRAPH_ONLY_WITHHELD) == tuple(cube_profile.DECOMPOSITION_AND_STORY_FIELDS),
            "VT_VISIBILITY_DECLARATION_DIVERGED")
    withheld = cube_profile.withheld_field_paths(bundle, asked_nodes, "LIST_PARTS",
                                                 "unassisted")
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    visible = sorted({path for ref in asked_nodes
                      for path in cube_node.node_paths(node_index[ref])
                      if path not in set(withheld)})
    return {"visibility_profile": VISIBILITY_PROFILE,
            "definition": ("retain the entire permitted raw graph, the question and "
                           "the three choices; withhold derived inventories, solved "
                           "intersections, worked paths and narrative solutions"),
            "visible_field_paths": visible,
            "withheld_field_paths": sorted(withheld),
            "release": ("an explicitly assisted event may release the withheld "
                        "fields afterwards; an unassisted event may not")}


def asked_nodes(exercise):
    named = exercise["question"]["named_arguments"]
    return sorted({value for value in named.values()})


def release_teacher_content(exercise, target, phase):
    """Teacher material is released only for an explicitly assisted event."""
    if phase == "UNASSISTED_MEASUREMENT":
        return {"released": False,
                "reason": "independent measurement may not read the teacher answer"}
    return {"released": True, "phase": phase,
            "expected_answer": target["expected_answer"],
            "worked_explanation": target["worked_explanation"],
            "witness": target["witness"]}


def public_bytes(exercise):
    """The bytes that must not move when a private target moves."""
    return canonical(exercise)


def answer_boundary_check(context, task_profile, operation, named_arguments,
                          choice_values, alternative_targets):
    """Compile / order / encode for several declared targets; bytes must match."""
    baseline = public_exercise(context, task_profile, operation, named_arguments,
                               choice_values)
    readings = []
    for target_value in alternative_targets:
        rebuilt = public_exercise(context, task_profile, operation, named_arguments,
                                  choice_values)
        readings.append({"declared_target": target_value,
                         "exercise_id": rebuilt["exercise_id"],
                         "identical": (rebuilt["exercise_id"] == baseline["exercise_id"]
                                       and public_bytes(rebuilt) == public_bytes(baseline))})
    return {"exercise_id": baseline["exercise_id"],
            "order_rule": ("choices are carried as {choice_id, value} objects; the "
                           "choice_id is the digest of the value alone, and the "
                           "exercise_id covers the public projection only"),
            "readings": readings,
            "all_identical": all(item["identical"] for item in readings),
            "prefix_mode": baseline["prefix_mode"],
            "carries_component_answers": False}


# --------------------------------------------------------------------------
# cycle plan, variants, observations
# --------------------------------------------------------------------------

STAGE_PLAN = (
    (1, "name/function", ("face_1",), "NOT_IMPLEMENTED", "PREPARED_PRESENTATION"),
    (2, "context", ("face_2",), "NOT_IMPLEMENTED", "PREPARED_PRESENTATION"),
    (3, "analogy", ("face_3",), "NOT_IMPLEMENTED", "PREPARED_PRESENTATION"),
    (4, "explicit mapping", ("face_4",), "NOT_IMPLEMENTED", "PREPARED_PRESENTATION"),
    (5, "guided decomposition", ("face_5",),
     "PROPOSED_BINDING_TO_EXISTING_REACHED_VIA", "PREDICT_THEN_CORRECT"),
    (6, "recomposition/story", ("face_6",),
     "RESTRICTED_FINAL_LIST_BINDING_PROPOSED; STORY_TASK_UNIMPLEMENTED",
     "DEMONSTRATION"),
    (7, "reinforcement", (),
     "PROPOSED_REUSE_OF_EXISTING_FINAL_GRAPH_TASK", "PLANNED_REPETITION"),
)


def cycle_plan(context, whole_id, component_exercises, final_exercise, trace_id,
               family_id="illustration_family_01"):
    """Seven stages, events, and the allocation fields left deliberately open."""
    face_refs = ["%s.%s" % (whole_id, face) for face in cube_node.FACE_KEYS]
    by_face = {face: ref for face, ref in zip(cube_node.FACE_KEYS, face_refs)}
    stages = []
    for number, name, faces, profile_status, event_kind in STAGE_PLAN:
        events = []
        if event_kind == "PREPARED_PRESENTATION":
            events.append({"kind": "PREPARED_PRESENTATION", "source": "pinned_cube_bundle",
                           "neural_deliveries": 0,
                           "numeric_delivery_binding": "UNIMPLEMENTED"})
        elif number == 5:
            for exercise in component_exercises:
                events.append({
                    "kind": "PREDICT_THEN_CORRECT",
                    "exercise_id": exercise["exercise_id"],
                    "teacher_target_ref": exercise["exercise_id"],
                    "feedback_release": "AFTER_RECORDED_PREDICTION",
                    "execution_status": "NOT_RUN"})
        elif number == 6:
            events.append({"kind": "DEMONSTRATION", "teacher_trace_ref": trace_id,
                           "scored_as_independent": False})
            events.append({
                "kind": "PREDICT_THEN_CORRECT",
                "exercise_id": final_exercise["exercise_id"],
                "teacher_target_ref": final_exercise["exercise_id"],
                "feedback_release": "AFTER_RECORDED_PREDICTION",
                "execution_status": "NOT_RUN"})
        else:
            events.append({
                "kind": "PLANNED_REPETITION",
                "exercise_id": final_exercise["exercise_id"],
                "execution_status": "NOT_RUN",
                "note": "Same illustrative family; no new-family or mastery claim."})
        stages.append({
            "stage": number, "name": name,
            "face_refs": [by_face[face] for face in faces],
            "status": "COMPILED_NOT_DELIVERED",
            "new_scored_profile_status": profile_status,
            "events": events})
    return {
        "family_id": family_id,
        "compiled_cycles": 1,
        "minimum_complete_guided_cycles_per_family": None,
        "maximum_optimizer_updates": None,
        "execution_enabled": False,
        "allocation_note": ("the guided-repetition minimum and the update budget are "
                            "not set here; the old 64-update allowance and the earlier "
                            "1,024-cycle allocation are not imported"),
        "stages": stages,
    }


def lesson_variants(final_exercises, targets_by_id):
    """Demonstration and unassisted variants of each final exercise."""
    variants = []
    for exercise in final_exercises:
        variants.append({
            "phase": "DEMONSTRATION",
            "exercise_id": exercise["exercise_id"],
            "assistance": ASSISTANCE_WORKED,
            "scored_as_independent": False,
            "teacher_target_ref": exercise["exercise_id"]})
        variants.append({
            "phase": "UNASSISTED_MEASUREMENT",
            "exercise_id": exercise["exercise_id"],
            "assistance": ASSISTANCE_NONE,
            "visibility_profile": VISIBILITY_PROFILE,
            "execution_status": "NOT_RUN",
            "teacher_target_ref": None})
    return variants


def practice_variants(component_exercises, targets_by_id):
    """The predict-then-correct phase for the component questions."""
    return [{
        "phase": "PREDICT_THEN_CORRECT",
        "exercise_id": exercise["exercise_id"],
        "assistance": ASSISTANCE_NONE,
        "feedback_release": "AFTER_RECORDED_PREDICTION",
        "teacher_target_ref": exercise["exercise_id"],
        "execution_status": "NOT_RUN"} for exercise in component_exercises]


def observation_contract():
    """What a future authorized run must retain; missing values stay unavailable."""
    return {
        "retained_fields": [
            "exact public exercise identity", "actual assistance state",
            "predicted option and its semantic value", "all three scores or logits",
            "corrective target and the moment it was released",
            "option token and item lengths", "option vector norms when measured",
            "checkpoint and update identity",
            "actual parameter-change observations"],
        "missing_measurement_rule": "unavailable, never zero",
        "phase_rules": {
            "DEMONSTRATION": "the worked solution is visible; any prediction is assisted",
            "PREDICT_THEN_CORRECT": ("predict, record the prediction, then release the "
                                     "checked correction"),
            "UNASSISTED_MEASUREMENT": ("no worked solution, no teacher-verified "
                                       "subanswers, no correct prefix; record the "
                                       "prediction before evaluating it; no update"),
        },
        "endpoint_rule": ("saved-state hashes compare endpoints only; they do not "
                          "establish what happened to unsaved components"),
    }


def counts(cycle, observations=()):
    """Compiled versus delivered: a plan is not a delivery."""
    compiled_stages = len(cycle["stages"])
    neural = [item for item in observations if item.get("delivered_to_module")]
    updates = [item for item in observations if item.get("optimizer_update")]
    return {
        "compiled_stages": compiled_stages,
        "presented_stages": compiled_stages,
        "neural_presentations": len(neural),
        "supervised_decisions": len([item for item in observations
                                     if item.get("correction_released")]),
        "optimizer_updates": len(updates),
        "complete_neural_cycles": 0,
        "distinct_graph_families": 1,
        "note": ("a compiled seven-stage plan is not seven neural presentations; a "
                 "passive presentation is not an update; a complete neural cycle "
                 "needs real delivery receipts"),
    }


def simulate_transport(exercise, target, phase, predicted_value=None):
    """A clearly labelled simulated transport, for compiler tests only.

    Its response is not a model prediction and cannot be counted as one.
    """
    values = exercise_choice_values(exercise)
    predicted = predicted_value if predicted_value is not None else target["expected_answer"]
    require(any(canonical(item) == canonical(predicted) for item in values),
            "VT_SIMULATED_PREDICTION_NOT_OFFERED")
    corrected = phase != "UNASSISTED_MEASUREMENT"
    return {
        "exercise_id": exercise["exercise_id"],
        "transport": "SIMULATED",
        "is_model_prediction": False,
        "counts_as_neural_delivery": False,
        "phase": phase,
        "assistance": ASSISTANCE_NONE if phase == "UNASSISTED_MEASUREMENT"
                      else ASSISTANCE_WORKED,
        "delivered_to_module": False,
        "predicted_value": predicted,
        "predicted_slot": next(index for index, choice in enumerate(exercise["choices"])
                               if canonical(choice["value"]) == canonical(predicted)),
        "scores_or_logits": "unavailable",
        "correction_released": corrected,
        "corrective_target": target["expected_answer"] if corrected else "withheld",
        "optimizer_update": False,
        "note": ("simulated: demonstrates the compiler and the recording path only"),
    }


# --------------------------------------------------------------------------
# whole-bundle compilation and fixture comparison
# --------------------------------------------------------------------------

def exercise_by_question(context, task_profile, operation, named_arguments,
                         choice_values, view_id="view_context"):
    return public_exercise(context, task_profile, operation, named_arguments,
                           choice_values, view_id)


def authored_choice_order(fixture, operation, named_arguments, choice_values):
    """The delivered fixture's own order for the same question, if it has one.

    The fixture is authored public data, so adopting its order keeps public
    identity reproducible. Slot order still never depends on the target: the
    order comes from the fixture's choice list, not from which value is correct.
    Returns None when the fixture has no matching question or a different set.
    """
    wanted = {canonical(value) for value in choice_values}
    for exercise in fixture.get("public_exercises", []):
        question = exercise["question"]
        if question["operation"] != operation:
            continue
        if {key: value for key, value in question["named_arguments"].items()} != \
                {key: value for key, value in named_arguments.items()}:
            continue
        values = [choice["value"] for choice in exercise["choices"]]
        if {canonical(value) for value in values} != wanted:
            continue
        return values
    return None


AUTHORED_COMPONENT_ORDER = ("Cart", "Frame", "Platform", "Rim", "Wheel")

# The delivered fixture's authored expectations for the canonical scene. They
# are checked against the repository checker, not trusted: a mismatch fails
# closed with VT_FIXTURE_EXPECTATION_CHANGED.
AUTHORED_EXPECTATIONS = {
    "Cart": ("absent", "Cart is another whole in this complete scene, not "
                       "reachable from Bicycle."),
    "Frame": ("direct", "Bicycle directly contains Frame."),
    "Platform": ("absent", "Platform belongs to Cart; no containment path from "
                           "Bicycle reaches Platform in this complete scene."),
    "Rim": ("via:Wheel", "The path Bicycle to Wheel to Rim makes Rim indirect, "
                         "not direct."),
    "Wheel": ("direct", "Bicycle directly contains Wheel."),
}


def explanation_for(index, whole_id, candidate_id, derived, hop):
    """A fixed explanatory template grounded in the checked graph."""
    whole = index.label_of[whole_id]
    candidate = index.label_of[candidate_id]
    if derived == "direct":
        return "%s directly contains %s." % (whole, candidate)
    if derived.startswith("via:"):
        return ("The path %s to %s to %s makes %s indirect, not direct."
                % (whole, index.label_of[hop], candidate, candidate))
    return ("%s is not reachable from %s in this complete scene."
            % (candidate, whole))


def shortcut_report(report):
    """Slot, item-count and character-length distributions, reported not judged."""
    rows = []
    for exercise in report["public_exercises"]:
        values = [choice["value"] for choice in exercise["choices"]]
        rows.append({
            "exercise_id": exercise["exercise_id"],
            "operation": exercise["question"]["operation"],
            "task_profile": exercise["task_profile"],
            "item_counts": [len(value) if isinstance(value, list) else 1
                            for value in values],
            "character_lengths": [len(value) if isinstance(value, str)
                                  else len(canonical(value).decode("utf-8"))
                                  for value in values],
            "equal_item_counts": len({len(value) if isinstance(value, list) else 1
                                      for value in values}) == 1,
            "slot_of_answer": None,
        })
    for target in report["private_teacher_targets"]:
        for row in rows:
            if row["exercise_id"] == target["exercise_id"]:
                row["slot_of_answer"] = target["expected_slot"]
    slots = [row["slot_of_answer"] for row in rows]
    return {"rows": rows,
            "slot_distribution": {str(slot): slots.count(slot) for slot in sorted(set(slots))},
            "list_alternatives_equal_length": all(
                row["equal_item_counts"] for row in rows
                if row["operation"] == "LIST_PARTS"),
            "note": ("shorter component questions do not by themselves fix or "
                     "disprove a list-scoring bias")}


def _default_whole(index):
    """The whole the lesson is about: most direct parts, ties broken by label.

    For the canonical scene that is Bicycle, and for a consistently renamed
    scene it is the renamed Bicycle, so the compiler never depends on a label.
    """
    labels = sorted(index.label_of.values())
    return index.node_of[sorted(labels, key=lambda label: (-len(index.direct_parts(
        index.node_of[label])), label))[0]]


def _first_shared_pair(index):
    """The first pair, alphabetically, with exactly one shared direct part."""
    labels = sorted(index.label_of.values())
    for first in labels:
        for second in labels:
            if first >= second:
                continue
            shared = index.shared(index.node_of[first], index.node_of[second])
            if len(shared) == 1:
                return (index.node_of[first], index.node_of[second])
    raise ValueError("VT_NO_UNIQUE_SHARED_PAIR")


def _first_indirect_candidate(index, whole_id):
    """The first candidate, by label, that is reached through a constituent."""
    for label in sorted(index.label_of.values()):
        candidate_id = index.node_of[label]
        if candidate_id == whole_id:
            continue
        value, _ = index.reach(whole_id, candidate_id)
        if value.startswith("via:"):
            return candidate_id
    raise ValueError("VT_NO_INDIRECT_CANDIDATE")


def compile_bundle(bundle=None, view_id="view_context", fixture_path=None,
                   choice_order="declared", expectations="authored",
                   whole_label=None):
    """Compile the whole verified-teaching bundle from the pinned cube bundle.

    ``choice_order`` is ``"declared"`` (this module's own public rule) or
    ``"authored_fixture"`` (adopt the delivered fixture's order where it asks
    the same question with the same choice set, so public identity reproduces).

    ``expectations`` is ``"authored"`` (the delivered fixture's documented
    answers, checked against the checker and failing closed on any change) or
    ``"derived"`` (answers and explanations computed from the graph, for any
    scene, including a rewired one). ``whole_label`` names the cube the lesson is
    about; by default the cube with the most direct parts is used, so the
    compiler never depends on a particular label.
    """
    if bundle is None:
        bundle = cube_node.load_bundle()
    require(choice_order in ("declared", "authored_fixture"),
            "VT_CHOICE_ORDER_MODE_UNKNOWN:" + str(choice_order))
    fixture = None
    fixture_file = Path(fixture_path) if fixture_path else pinned_fixture_path()
    if choice_order == "authored_fixture" and Path(fixture_file).is_file():
        fixture = json.loads(Path(fixture_file).read_text(encoding="utf-8"))
    context = lesson_context(bundle, view_id)
    index = Index(bundle, context, view_id)
    graph_digest = public_graph_digest(context)

    whole_id = _default_whole(index) if whole_label is None else index.node_of[whole_label]
    require(expectations in ("authored", "derived"),
            "VT_EXPECTATION_MODE_UNKNOWN:" + str(expectations))
    components, targets = [], {}

    def ordered(task_profile, operation, named_arguments, values):
        """Public slot order: the fixture's authored order, else a public permutation.

        The permutation seed covers the question and the *set* of choices, so a
        slot never depends on which choice is correct. Without it the answer
        would sit in slot 0 in every exercise, which is a shortcut a learner
        could exploit.
        """
        if fixture is not None:
            authored = authored_choice_order(fixture, operation, named_arguments, values)
            if authored is not None:
                return authored
        seed_material = canonical({"task_profile": task_profile,
                                   "operation": operation,
                                   "named_arguments": named_arguments,
                                   "choice_set": sorted(values, key=canonical)})
        permutation = list(values)
        random.Random(int(digest(seed_material)[:8], 16)).shuffle(permutation)
        return permutation

    if expectations == "authored":
        order = [index.node_of[label] for label in AUTHORED_COMPONENT_ORDER]
    else:
        order = [index.node_of[label] for label in
                 sorted(set(index.label_of.values()) - {index.label_of[whole_id]})]
    for candidate_id in order:
        derived, hop = index.reach(whole_id, candidate_id)
        if expectations == "authored":
            expected, explanation = AUTHORED_EXPECTATIONS[index.label_of[candidate_id]]
            require(derived == expected,
                    "VT_FIXTURE_EXPECTATION_CHANGED:%s:%s"
                    % (index.label_of[candidate_id], derived))
        else:
            explanation = explanation_for(index, whole_id, candidate_id, derived, hop)
        values = reach_choice_values(index, whole_id, candidate_id, derived)
        exercise = public_exercise(
            context, "component-route/0.1", "REACHED_VIA",
            {"whole_id": whole_id, "candidate_id": candidate_id},
            ordered("component-route/0.1", "REACHED_VIA",
                    {"whole_id": whole_id, "candidate_id": candidate_id}, values),
            view_id)
        if derived == "direct":
            witness_record = witness("direct_branch", context["context_id"],
                                     [index.branch_between(whole_id, candidate_id)])
        elif derived.startswith("via:"):
            witness_record = witness("path", context["context_id"],
                                     [index.branch_between(whole_id, hop),
                                      index.branch_between(hop, candidate_id)])
        else:
            witness_record = witness("complete_scope_absence", context["context_id"],
                                     [], "complete")
        target = teacher_target(exercise, derived, explanation, witness_record)
        outcome = verify_target(index, exercise, target)
        require(outcome["status"] == VERIFIED,
                "VT_FIXTURE_TARGET_FAILED:%s:%s" % (candidate_id, outcome["codes"]))
        components.append(exercise)
        targets[exercise["exercise_id"]] = outcome["target"]

    final_exercises, final_targets, contrasts = [], {}, []
    list_answer = index.direct_parts(whole_id)
    if expectations == "authored":
        require(sorted(list_answer) == ["Frame", "Wheel"],
                "VT_FIXTURE_EXPECTATION_CHANGED:LIST_PARTS")
        list_explanation = ("Frame and Wheel are exactly the direct Bicycle "
                            "constituents. Rim is indirect; Platform belongs elsewhere.")
    else:
        list_explanation = ("%s are exactly the direct %s constituents."
                            % (", ".join(sorted(list_answer)), index.label_of[whole_id]))
    list_values = list_choice_values(index, whole_id, list_answer)
    list_exercise = public_exercise(
        context, "whole-answer/0.1", "LIST_PARTS", {"whole_id": whole_id},
        ordered("whole-answer/0.1", "LIST_PARTS", {"whole_id": whole_id},
                list_values), view_id)
    list_witness = witness("complete_direct_inventory", context["context_id"],
                           [index.branch_between(whole_id, index.node_of[label])
                            for label in list_answer], "complete")
    list_target = teacher_target(list_exercise, sorted(list_answer),
                                 list_explanation, list_witness)
    require(verify_target(index, list_exercise, list_target)["status"] == VERIFIED,
            "VT_LIST_TARGET_FAILED")
    final_exercises.append(("LIST_PARTS", list_exercise, list_target))

    shared_pair = (index.node_of["Bicycle"], index.node_of["Cart"]) \
        if expectations == "authored" else _first_shared_pair(index)
    shared_answer = index.shared(*shared_pair)
    require(len(shared_answer) == 1, "VT_SHARED_ANSWER_NOT_UNIQUE")
    shared_exercise = public_exercise(
        context, "whole-answer/0.1", "FIND_SHARED_PART",
        {"first_whole_id": shared_pair[0], "second_whole_id": shared_pair[1]},
        ordered("whole-answer/0.1", "FIND_SHARED_PART",
                {"first_whole_id": shared_pair[0], "second_whole_id": shared_pair[1]},
                shared_choice_values(index, shared_pair[0], shared_pair[1],
                                     shared_answer[0])),
        view_id)
    shared_witness = witness(
        "unique_shared_direct_constituent", context["context_id"],
        [index.branch_between(shared_pair[0], index.node_of[shared_answer[0]]),
         index.branch_between(shared_pair[1], index.node_of[shared_answer[0]])],
        "complete")
    shared_target = teacher_target(
        shared_exercise, shared_answer[0],
        shared_answer[0] + " is the unique shared direct constituent of "
        + index.label_of[shared_pair[0]] + " and " + index.label_of[shared_pair[1]] + ".",
        shared_witness)
    require(verify_target(index, shared_exercise, shared_target)["status"] == VERIFIED,
            "VT_SHARED_TARGET_FAILED")
    final_exercises.append(("FIND_SHARED_PART", shared_exercise, shared_target))

    rim_id = index.node_of["Rim"] if expectations == "authored" else \
        _first_indirect_candidate(index, whole_id)
    rim_answer, rim_hop = index.reach(whole_id, rim_id)
    if expectations == "authored":
        require(rim_answer == "via:Wheel", "VT_FIXTURE_EXPECTATION_CHANGED:REACHED_VIA")
        route_explanation = "The reference-compatible path is Bicycle to Wheel to Rim."
    else:
        route_explanation = explanation_for(index, whole_id, rim_id, rim_answer, rim_hop)
    final_route_values = reach_choice_values(index, whole_id, rim_id, rim_answer)
    route_exercise = public_exercise(
        context, "whole-answer/0.1", "REACHED_VIA",
        {"whole_id": whole_id, "candidate_id": rim_id},
        ordered("whole-answer/0.1", "REACHED_VIA",
                {"whole_id": whole_id, "candidate_id": rim_id},
                final_route_values), view_id)
    route_target = teacher_target(
        route_exercise, rim_answer, route_explanation,
        witness("path", context["context_id"],
                [index.branch_between(whole_id, rim_hop),
                 index.branch_between(rim_hop, rim_id)]))
    require(verify_target(index, route_exercise, route_target)["status"] == VERIFIED,
            "VT_ROUTE_TARGET_FAILED")
    final_exercises.append(("REACHED_VIA", route_exercise, route_target))

    for name, exercise, target in final_exercises:
        outcome = verify_target(index, exercise, target)
        require(outcome["status"] == VERIFIED,
                "VT_FINAL_TARGET_FAILED:%s:%s" % (name, outcome["codes"]))
        final_targets[exercise["exercise_id"]] = outcome["target"]
    all_targets = {**targets, **final_targets}
    ordered_exercises = components + [item[1] for item in final_exercises]
    for exercise in ordered_exercises:
        contrasts.extend(step_contrasts(index, exercise,
                                        all_targets[exercise["exercise_id"]],
                                        graph_digest, view_id))

    slot_alignment = [slot_alignment_check(context, index, exercise,
                                           all_targets[exercise["exercise_id"]],
                                           view_id)
                      for exercise in ordered_exercises]

    trace = compile_trace(context, components, list_exercise, "toy-list-trace-001")
    trace_outcome = verify_trace(index, trace,
                                 {exercise["exercise_id"]: exercise
                                  for exercise in components + [item[1] for item in final_exercises]},
                                 all_targets)
    plan = cycle_plan(context, whole_id, components, list_exercise,
                      trace["trace_id"], bundle["lesson_family_id"])
    variants = lesson_variants([item[1] for item in final_exercises], final_targets)
    practice = practice_variants(components, targets)

    report = {
        "schema_version": SCHEMA,
        "status": STATUS_READY,
        "usage": ("contains private teacher records; never send this whole bundle to "
                  "a learner; compile permitted views only"),
        "source": {"filename": cube_node.pinned_bundle_path().name,
                   "sha256": sha256(cube_node.pinned_bundle_path().read_bytes()).hexdigest()},
        "identity_rule": ("sha256 of compact sorted-key UTF-8 JSON of the record "
                          "minus its own id, bound to the repository canonical() "
                          "profile; identical for ASCII content, and a versioned "
                          "translation must be declared for non-ASCII content"),
        "checker_identity": CHECKER_IDENTITY,
        "public_contexts": [context],
        "public_exercises": components + [item[1] for item in final_exercises],
        "private_teacher_targets": [all_targets[key] for key in
                                    [exercise["exercise_id"]
                                     for exercise in components + [item[1] for item in final_exercises]]],
        "private_step_contrasts": contrasts,
        "private_teacher_traces": [trace_outcome["trace"]],
        "trace_verification": trace_outcome,
        "lesson_variants": variants,
        "practice_variants": practice,
        "cycle_plan": plan,
        "slot_alignment": slot_alignment,
        "slot_alignment_summary": {
            "exercises": len(slot_alignment),
            "permutations_per_exercise": 6,
            "all_permutations_align": all(item["all_permutations_align"]
                                          for item in slot_alignment),
            "rule": ("expected_slot follows expected_choice_id through all six "
                     "orderings of three choices"),
        },
        "ordering_mode": choice_order,
        "public_graph_digest": graph_digest,
        "observation_contract": observation_contract(),
        "counts": counts(plan),
        "actual_execution": {"repository_reference_calls": len(components) + 3,
                             "neural_calls": 0, "optimizer_updates": 0,
                             "neural_presentations": 0, "complete_neural_cycles": 0,
                             "aws_calls": 0, "reservations": 0},
        "known_limits": [
            "Only an illustrative small scene, not a balanced dataset or held-out panel.",
            "Reference and adapter compatibility remain for the builder to verify.",
            "The stage plan does not implement numeric delivery for all seven stages.",
            "The simulated transport is not a model prediction.",
        ],
    }
    report["fixture_comparison"] = compare_with_fixture(report, fixture_path)
    report["shortcut_report"] = shortcut_report(report)
    return report


def pinned_fixture_path():
    return cube_node.CUBE_RECORD_DIR / "Cube_Verified_Step_Example_v0.1.json"


def compare_with_fixture(report, path=None):
    """Compare the compiled bundle with the delivered authoring fixture."""
    path = Path(pinned_fixture_path() if path is None else path)
    if not path.is_file():
        return {"fixture_present": False,
                "note": "the compiler does not require the delivered fixture"}
    fixture = json.loads(path.read_text(encoding="utf-8"))
    identity = {"fixture": {"bytes": path.stat().st_size,
                            "sha256": sha256(path.read_bytes()).hexdigest()}}
    counts_comparison = {
        "public_contexts": [len(report["public_contexts"]),
                            len(fixture["public_contexts"])],
        "public_exercises": [len(report["public_exercises"]),
                             len(fixture["public_exercises"])],
        "teacher_targets": [len(report["private_teacher_targets"]),
                            len(fixture["private_teacher_targets"])],
        "step_contrasts": [len(report["private_step_contrasts"]),
                           len(fixture["private_step_contrasts"])],
        "traces": [len(report["private_teacher_traces"]),
                   len(fixture["private_teacher_traces"])],
        "lesson_variants": [len(report["lesson_variants"]),
                            len(fixture["lesson_variants"])],
    }
    context_ids = [report["public_contexts"][0]["context_id"],
                   fixture["public_contexts"][0]["context_id"]]
    exercise_ids = {item["exercise_id"] for item in report["public_exercises"]}
    fixture_exercise_ids = {item["exercise_id"] for item in fixture["public_exercises"]}

    def question_key(exercise):
        return canonical({"task_profile": exercise["task_profile"],
                          "operation": exercise["question"]["operation"],
                          "named_arguments": exercise["question"]["named_arguments"]})

    fixture_by_question = {question_key(exercise): exercise
                           for exercise in fixture["public_exercises"]}
    matching_choice_sets = 0
    matching_choice_orders = 0
    compared = 0
    compared_orders = 0
    for exercise in report["public_exercises"]:
        counterpart = fixture_by_question.get(question_key(exercise))
        if counterpart is None:
            continue
        compared += 1
        mine = sorted(canonical(choice["value"]).decode("utf-8")
                      for choice in exercise["choices"])
        theirs = sorted(canonical(choice["value"]).decode("utf-8")
                        for choice in counterpart["choices"])
        if mine == theirs:
            matching_choice_sets += 1
            compared_orders += 1
            if [canonical(choice["value"]) for choice in exercise["choices"]] == \
                    [canonical(choice["value"]) for choice in counterpart["choices"]]:
                matching_choice_orders += 1
    return {
        "fixture_present": True,
        "fixture_identity": identity,
        "counts_compiled_then_fixture": counts_comparison,
        "counts_match": all(mine == theirs for mine, theirs in counts_comparison.values()),
        "context_id_reproduced": context_ids[0] == context_ids[1],
        "exercise_ids_reproduced": sorted(exercise_ids) == sorted(fixture_exercise_ids),
        "exercise_id_overlap": len(exercise_ids & fixture_exercise_ids),
        "questions_compared": compared,
        "choice_sets_matching": matching_choice_sets,
        "choice_orders_matching": matching_choice_orders,
        "choice_orders_compared": compared_orders,
        "choice_sets_compared": len(report["public_exercises"]),
        "public_context_digest_scope": "complete public exercise, including exercise_id",
        "public_context_digest_reproduced": _context_digest_matches(fixture),
        "public_context_digest_values_reproduced": _context_digest_count(fixture),
        "unreproduced_authored_values": [],
        "field_translation": {
            "public_context_digest": "delivered fixture's name; the complete public "
                                     "exercise scope",
            "public_exercise_digest": "the compiler's name for the same scope",
            "public_graph_digest": "shared graph scope only, a different value",
        },
        "note": ("exercises are compared by question, not by id, so the id is "
                 "evidence rather than a lookup key. The fixture's "
                 "public_context_digest is the digest of the COMPLETE public "
                 "exercise including its exercise_id, not of the graph alone; the "
                 "earlier reading of that ambiguous field as a graph digest was "
                 "wrong and is corrected here"),
    }


def _context_digest_count(fixture):
    """How many of the fixture's contrast digests reproduce under the right rule."""
    exercises = {exercise["exercise_id"]: exercise
                 for exercise in fixture["public_exercises"]}
    reproduced = 0
    for contrast in fixture["private_step_contrasts"]:
        exercise = exercises.get(contrast["exercise_id"])
        if exercise is not None and \
                public_exercise_digest(exercise) == contrast.get("public_context_digest"):
            reproduced += 1
    return {"reproduced": reproduced,
            "considered": len(fixture["private_step_contrasts"])}


def _context_digest_matches(fixture):
    counts = _context_digest_count(fixture)
    return counts["reproduced"] == counts["considered"] and counts["considered"] > 0


def artifact_files(report):
    """The record files as name -> text, ready to write."""
    def lines(records):
        return "".join(json.dumps(record, sort_keys=True, ensure_ascii=True,
                                  allow_nan=False) + "\n" for record in records)
    return {
        "public_contexts.jsonl": lines(report["public_contexts"]),
        "public_exercises.jsonl": lines(report["public_exercises"]),
        "teacher_targets.jsonl": lines(report["private_teacher_targets"]),
        "teacher_traces.jsonl": lines(report["private_teacher_traces"]),
        "step_contrasts.jsonl": lines(report["private_step_contrasts"]),
        "cycle_plan.json": json.dumps(report["cycle_plan"], sort_keys=True, indent=2,
                                      ensure_ascii=True, allow_nan=False) + "\n",
    }
