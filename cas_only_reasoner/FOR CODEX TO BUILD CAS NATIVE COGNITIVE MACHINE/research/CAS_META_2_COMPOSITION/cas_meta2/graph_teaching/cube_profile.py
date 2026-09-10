"""CUBE_TEACHING_PROFILE_001 — the machine-facing seven-stage cube lesson.

STATUS: specification and compilation only. Nothing here trains, updates,
reserves, or launches. Every ``update`` block reports what *would* happen if the
profile were executed under an owner GO, and the counters keep
``optimizer_updates: 0`` and ``delivered_neural_lessons: 0`` for this work.

This module answers the owner's handoff in one record per lesson:

    exact learner-facing input, any prediction target, the corrective signal,
    whether an optimizer update happens, and the recorded assistance state

It builds on ``cube_node`` (the validated ``cas.cube-node/0.1`` data contract)
and changes nothing in it. Version boundary: ``cube_node`` keeps its read-only
``cas-cube-lesson/1`` records; this module emits ``cas-cube-lesson/2``, which

* declares visibility **by task and assistance level** instead of choosing
  leaves to hide from the answer, and
* derives task identity and slot ordering from the public exercise only, with a
  target-independent ordering rule.

Two rules are enforced, not asserted:

1. **The public path cannot see the answer.** ``compile_public_exercise`` accepts
   a public case with no target field at all, so no ordering, mask, or token can
   depend on the private target.
2. **A disagreeing target is refused.** ``attach_target`` compares the declared
   target with the answer the deterministic checker derives from the public
   graph and fails closed with ``CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER``.
   The private target therefore cannot steer the learner's input even by
   accident, and the earlier "swap the target after freezing the view" test is
   replaced by a check of the whole construction path.

The three existing graph operations are the only scored tasks in this profile
(``LIST_PARTS``, ``FIND_SHARED_PART``, ``REACHED_VIA``). Analogies, correspondence
tables, and recomposition stories stay guided presentation; scoring them would
need a separately declared task profile, and this profile says so per stage
rather than inventing one.
"""
from __future__ import annotations

from .graph import canonical, digest, require
from .lessons import EXERCISE_SCHEMA
from . import adapter, cube_node, reference
from .real_framework import TARGET_CONTRACT_ID, TARGET_PLASTICITY_ROLE

PROFILE_SCHEMA = "cas-cube-teaching-profile/1"
LESSON_V2_SCHEMA = "cas-cube-lesson/2"
VISIBILITY_SCHEMA = "cas-cube-visibility/1"

CUBE_OPS = tuple(cube_node.CUBE_OPS)
ASSISTANCE_LEVELS = tuple(cube_node.ASSISTANCE_LEVELS)

# --------------------------------------------------------------------------
# 1. declared visibility, by task and assistance level
# --------------------------------------------------------------------------

# The only fields that carry a worked decomposition or recomposition summary.
# Declaring them once, for every question and every cube, is what keeps the mask
# pattern independent of the answer: the pattern cannot move when the target
# moves, because the target is not an input to the declaration.
DECOMPOSITION_AND_STORY_FIELDS = (
    "face_2.structured.fact_refs",
    "face_5.structured.direct_branch_refs",
    "face_6.structured.steps[*].uses_branch_refs",
    "face_6.structured.steps[*].text",
)

# Teaching sees the cube whole; an unassisted test retains the public graph and
# withholds the preassembled solution. `hinted` currently withholds nothing and
# is therefore recorded as assistance-bearing: this profile implements no graded
# hint policy, and inventing one here would be a policy claim, not a data rule.
VISIBILITY_DECLARATIONS = {
    (op, assistance): (() if assistance != "unassisted"
                       else DECOMPOSITION_AND_STORY_FIELDS)
    for op in CUBE_OPS for assistance in ASSISTANCE_LEVELS
}

VISIBILITY_NOTE = (
    "withheld fields are the declarations above, expanded over the cubes the "
    "question asks about; the pattern is identical for every question of a "
    "(task, assistance) pair, so it carries no answer information"
)


def visibility_version():
    """Version of the declaration table; any change to it changes this digest."""
    return digest(canonical([[list(key), list(value)]
                             for key, value in sorted(VISIBILITY_DECLARATIONS.items())]))


def visibility_profile(operation, assistance):
    require(operation in CUBE_OPS, "CUBE_OPERATION_UNKNOWN:" + str(operation))
    require(assistance in ASSISTANCE_LEVELS, "CUBE_ASSISTANCE_UNKNOWN:" + str(assistance))
    patterns = VISIBILITY_DECLARATIONS[(operation, assistance)]
    return {"schema": VISIBILITY_SCHEMA,
            "profile_id": "cas-cube-visibility/1:%s:%s:%s"
                          % (operation, assistance, visibility_version()[:12]),
            "operation": operation, "assistance_level": assistance,
            "withheld_patterns": list(patterns),
            "assisted": assistance != "unassisted",
            "note": VISIBILITY_NOTE}


def _pattern_matches(pattern, path):
    """Match a declared pattern against an addressable leaf path.

    ``steps[*].text`` matches ``steps[0].text`` and ``steps[1].text``; everything
    else matches exactly. Only the wildcard form used in the declarations is
    supported, and an unknown wildcard shape raises instead of silently matching
    nothing.
    """
    if "[*]" not in pattern:
        return pattern == path
    head, _, tail = pattern.partition("[*]")
    require(tail in (".text", ".uses_branch_refs", ".step_id"),
            "CUBE_VISIBILITY_WILDCARD_UNSUPPORTED:" + pattern)
    if not path.startswith(head) or not path.endswith(tail):
        return False
    middle = path[len(head):-len(tail)]
    return middle.startswith("[") and middle.endswith("]")


def withheld_field_paths(bundle, asked_nodes, operation, assistance):
    """Expand the declared patterns over the asked cubes' own leaf paths."""
    profile = visibility_profile(operation, assistance)
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    withheld = []
    for ref in sorted(asked_nodes):
        for path in cube_node.node_paths(node_index[ref]):
            relative = path[len(ref) + 1:]
            if any(_pattern_matches(pattern, relative)
                   for pattern in profile["withheld_patterns"]):
                withheld.append(path)
    return sorted(set(withheld))


def visibility_is_declared(bundle, asked_nodes, operation, assistance, mask):
    """The mask must be exactly the declared expansion: no more, no less."""
    return sorted(mask) == withheld_field_paths(bundle, asked_nodes, operation,
                                                assistance)


def prose_index(bundle):
    """Labels safe to look for in prose, and the ones excluded and why.

    The delivered example gives the technical view the one-letter labels A-F.
    A prose scan then finds the letter "B" inside the analogy label "Kit B",
    which resolves to a different cube and reports a disclosure that is not
    there. The new layer therefore matches prose only against labels that do not
    occur inside another label. Structured references are unaffected: they are
    resolved by identifier, not by text.

    ``cube_node`` keeps its own scanner unchanged, because its record is already
    published and old evidence is not rewritten.
    """
    index = cube_node.label_index(bundle)
    labels = sorted(index)
    excluded = sorted({label for label in labels
                       if any(other != label and label in other for other in labels)})
    safe = {label: refs for label, refs in index.items() if label not in excluded}
    return safe, excluded


def _leaf_values(node, wanted):
    """Fetch addressable leaves by path, using ``cube_node``'s own path rules."""
    found = {}

    def walk(value, prefix):
        if isinstance(value, dict):
            for key in sorted(value):
                walk(value[key], prefix + "." + key)
        elif cube_node._is_scalar_list(value):
            found[prefix] = value
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, "%s[%d]" % (prefix, index))
        else:
            found[prefix] = value

    walk(node["core"], node["node_id"] + ".core")
    for key in cube_node.FACE_KEYS:
        walk(node["faces"][key], "%s.%s" % (node["node_id"], key))
    require(set(wanted) <= set(found), "CUBE_LEAF_PATH_UNRESOLVED")
    return {path: found[path] for path in wanted}


def disclosure_candidates_v2(bundle, node):
    """``cube_node``'s candidates with the corrected prose-mention rule."""
    index, _ = prose_index(bundle)
    out = []
    for candidate in cube_node.disclosure_candidates(bundle, node):
        if candidate["source"] != "text":
            out.append(candidate)
            continue
        leaves = _leaf_values(node, candidate["leaf_paths"])
        refs = set()
        for text in leaves.values():
            if isinstance(text, str):
                refs |= cube_node._mentioned_refs(text, index)
        refs.discard(node["node_id"])
        if refs:
            out.append({**candidate, "refs": sorted(refs)})
    return out


def answer_refs(bundle, case, view_id):
    """Which cubes an answer names, recomputed from the answer itself.

    Diagnostics only. The mask never uses this: it comes from the declared
    profile, so the answer can refuse a lesson but cannot shape one.
    """
    labels = cube_node.view_labels(bundle, view_id)
    by_label = {label: ref for ref, label in labels.items()}
    correct = case["correct"]
    if case["op"] == "LIST_PARTS":
        return {by_label[label] for label in correct}
    if case["op"] == "FIND_SHARED_PART":
        return {by_label[correct]} if correct != "none" else set()
    if correct == "direct":
        return {by_label[case["question"]["part"]]}
    if correct.startswith("via:"):
        return {by_label[correct[4:]]}
    return set()


def _require_answer_refs_agree(bundle, case, view_id):
    if "answer_refs" not in case:
        return
    derived = answer_refs(bundle, case, view_id)
    require(set(case["answer_refs"]) == derived,
            "CUBE_ANSWER_REFS_MISMATCH:%s:%s"
            % (sorted(case["answer_refs"]), sorted(derived)))


def disclosure_audit(bundle, case, view_id="view_context", scope="asked_cubes"):
    """Diagnostic: does this profile still hand over the answer? (answer-derived)

    This never builds the mask. It reports, after the fact, whether the declared
    profile leaves a path that discloses the answer, so an unassisted label can
    be refused rather than trusted. ``scope='all_cubes'`` measures the wider
    question for information: a cube that is not asked about still carries the
    public graph, so its fields can only ever restate the evidence.
    """
    _require_answer_refs_agree(bundle, case, view_id)
    if scope == "asked_cubes":
        refs = sorted(cube_node._asked_nodes(bundle, case, view_id))
    elif scope == "all_cubes":
        refs = sorted(node["node_id"] for node in bundle["cube_nodes"])
    else:
        raise ValueError("CUBE_AUDIT_SCOPE_UNKNOWN:" + str(scope))
    wanted = answer_refs(bundle, case, view_id)
    if not wanted:
        return []
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    found = []
    for ref in refs:
        for candidate in disclosure_candidates_v2(bundle, node_index[ref]):
            matched = sorted(wanted & set(candidate["refs"]))
            if matched:
                found.append({"path": candidate["path"], "matched": matched,
                              "source": candidate["source"],
                              "leaf_paths": candidate["leaf_paths"]})
    return found


def raw_scanner_audit(bundle, case, view_id="view_context", scope="asked_cubes"):
    """The same audit through ``cube_node``'s scanner, for comparison.

    Reported side by side so the correction above is visible rather than
    asserted: the difference between the two counts is the prose-mention
    artifact of the one-letter technical labels.
    """
    refs = sorted(cube_node._asked_nodes(bundle, case, view_id)) if scope == "asked_cubes" \
        else sorted(node["node_id"] for node in bundle["cube_nodes"])
    wanted = answer_refs(bundle, case, view_id)
    if not wanted:
        return []
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    found = []
    for ref in refs:
        for candidate in cube_node.disclosure_candidates(bundle, node_index[ref]):
            if wanted & set(candidate["refs"]):
                found.append(candidate["path"])
    return sorted(set(found))


def visible_after_profile(bundle, case, operation, assistance, view_id="view_context"):
    """(visible, withheld, disclosures) for one question under one profile."""
    asked = sorted(cube_node._asked_nodes(bundle, case, view_id))
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    all_paths = sorted({path for ref in asked for path in cube_node.node_paths(node_index[ref])})
    withheld = set(withheld_field_paths(bundle, asked, operation, assistance))
    visible = [path for path in all_paths if path not in withheld]
    disclosures = disclosure_audit(bundle, case, view_id, "asked_cubes")
    leaked = sorted({leaf for item in disclosures for leaf in item["leaf_paths"]
                     if leaf not in withheld})
    return visible, sorted(withheld), disclosures, leaked


# --------------------------------------------------------------------------
# 2. the public exercise: identity, pool, order, mask, tokens
# --------------------------------------------------------------------------

def public_case(case):
    """The public half of a question: no answer, no derivation, no target."""
    require(case["op"] in CUBE_OPS, "CUBE_OPERATION_UNKNOWN:" + str(case["op"]))
    public = {"op": case["op"], "question": dict(case["question"])}
    require(not (set(public) & {"correct", "answer_refs", "derivation", "target"}),
            "CUBE_PUBLIC_CASE_CARRIES_TARGET")
    return public


def derived_answer(bundle, public_case_record, view_id):
    """The answer the deterministic checker derives from the public graph."""
    op, question = public_case_record["op"], public_case_record["question"]
    graph = cube_node.containment_graph(bundle, view_id)
    if op == "LIST_PARTS":
        return reference.direct_parts(graph, question["idea"])
    if op == "FIND_SHARED_PART":
        shared = reference.shared_parts(graph, question["a"], question["b"])
        require(len(shared) <= 1, "CUBE_AMBIGUOUS_SHARED_PART")
        return shared[0] if shared else "none"
    return reference.reach_kind(graph, question["part"], question["idea"])


def public_option_pool(bundle, public_case_record, view_id):
    """Candidate answers from the public graph only, in a content order.

    The pool is a function of the question and the graph. It is deliberately
    built without any reference to a declared target: the ordering rule is the
    canonical form of each candidate, so which option sits in which slot can
    never depend on which one is correct.
    """
    graph = cube_node.containment_graph(bundle, view_id)
    labels = sorted(node.identifier for node in graph.nodes)
    op, question = public_case_record["op"], public_case_record["question"]
    pool = []
    if op == "LIST_PARTS":
        parts = {label: reference.direct_parts(graph, label) for label in labels}
        for label in labels:
            nested = [part for part in reference.transitive_parts(graph, label)
                      if part not in parts[label]]
            pool.append(sorted(parts[label]))
            for index in range(len(parts[label])):
                pool.append(sorted(parts[label][:index] + parts[label][index + 1:]))
            if nested:
                pool.append(sorted(parts[label] + nested[:1]))
        pool.append([])
    elif op == "FIND_SHARED_PART":
        pool.extend(labels)
        pool.append("none")
    else:
        pool.extend(["direct", "absent"])
        for constituent in reference.direct_parts(graph, question["idea"]):
            pool.append("via:" + constituent)
        # A route through a cube that is not a direct constituent is wrong by
        # construction, so the rest of the public graph supplies the third
        # choice when the asked cube has few parts. Public structure only.
        for label in labels:
            if label != question["idea"]:
                pool.append("via:" + label)
    unique, seen = [], set()
    for candidate in sorted(pool, key=canonical):
        key = canonical(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def public_options(bundle, public_case_record, view_id):
    """The three public choices, in content order, for a public question.

    The set is a function of the question and the graph. Its order here is the
    documentation order; the order the module actually receives is the frozen
    codec's permutation of this same set (see ``slot_order_rule``).
    """
    op, question = public_case_record["op"], public_case_record["question"]
    graph = cube_node.containment_graph(bundle, view_id)
    labels = sorted(node.identifier for node in graph.nodes)
    derived = derived_answer(bundle, public_case_record, view_id)
    pool = public_option_pool(bundle, public_case_record, view_id)
    # Prefer the graph-derived answer (a question must be answerable) plus two
    # distractors built from the same public structure: one that adds an
    # indirect part, one that omits a part. All of it is a function of the
    # question and the graph, never of a declared target.
    preferred = [derived]
    if op == "LIST_PARTS":
        nested = [part for part in reference.transitive_parts(graph, question["idea"])
                  if part not in derived]
        if nested:
            preferred.append(sorted(derived + nested[:1]))
        if len(derived) > 1:
            preferred.append(sorted(derived[:-1]))
        other = [label for label in labels if label != question["idea"]]
        if other:
            preferred.append(sorted(reference.direct_parts(graph, other[0])))
    choices = []
    for candidate in preferred + pool:
        if any(canonical(candidate) == canonical(item) for item in choices):
            continue
        if len(choices) < 3:
            choices.append(candidate)
    require(len(choices) == 3, "CUBE_PUBLIC_POOL_TOO_SMALL")
    require(any(canonical(item) == canonical(derived) for item in choices),
            "CUBE_PUBLIC_POOL_MISSES_DERIVED_ANSWER")
    return choices, derived


OPTION_POOL_VERSION = "cas-cube-option-pool/1"


def public_identity(bundle, public_case_record, view_id, candidate_set):
    """Identity of the public exercise alone: no target, no assistance level.

    Excluding the assistance level is deliberate. The same question then offers
    the same three choices in the same slots whether it is delivered as guided
    teaching or as an unassisted assessment, so a guided-versus-unassisted
    comparison differs in visibility and correction only, not in layout.
    """
    core = {"family_id": bundle["lesson_family_id"], "view_id": view_id,
            "op": public_case_record["op"],
            "question": public_case_record["question"],
            "options": sorted(candidate_set, key=canonical),
            "option_pool_version": OPTION_POOL_VERSION}
    identifier = digest(canonical(core))
    return {"task_id": identifier, "public_id": identifier,
            "identity_basis": "public_projection", "identity_core": core}


def delivery_identity(task_id, operation, assistance):
    """One recorded delivery of one public exercise under one profile."""
    profile = visibility_profile(operation, assistance)
    return {"delivery_id": digest(canonical(
                {"task_id": task_id, "assistance_level": assistance,
                 "visibility_profile_id": profile["profile_id"]})),
            "task_id": task_id, "assistance_level": assistance,
            "visibility_profile_id": profile["profile_id"]}


def _prompt(bundle, public_case_record, view_id, choices):
    op, question = public_case_record["op"], public_case_record["question"]
    labels = cube_node.view_labels(bundle, view_id)
    lines = ["Facts (labels as presented in %s):" % view_id]
    for branch in sorted(bundle["branches"], key=lambda item: item["branch_id"]):
        lines.append("%s %s %s" % (labels[branch["source_node_id"]],
                                   branch["predicate"],
                                   labels[branch["target_node_id"]]))
    if op == "LIST_PARTS":
        request = "LIST_PARTS(%s): what does it directly contain?" % question["idea"]
    elif op == "FIND_SHARED_PART":
        request = ("FIND_SHARED_PART(%s, %s): which constituent do they share?"
                   % (question["a"], question["b"]))
    else:
        request = ("REACHED_VIA(%s, %s): directly inside, reached through another "
                   "constituent, or absent?" % (question["part"], question["idea"]))
    lines.append(request)
    lines.append("Choose one of the three supplied options.")
    return "\n".join(lines) + "\n"


def compile_public_exercise(bundle, case, *, assistance, view_id="view_context"):
    """Everything the learner sees, built from the public half of the question."""
    public = public_case(case)
    _require_answer_refs_agree(bundle, case, view_id)
    candidate_set, derived = public_options(bundle, public, view_id)
    identity = public_identity(bundle, public, view_id, candidate_set)
    delivery = delivery_identity(identity["task_id"], public["op"], assistance)
    asked = sorted(cube_node._asked_nodes(bundle, case, view_id))
    visible, withheld, disclosures, leaked = visible_after_profile(
        bundle, case, public["op"], assistance, view_id)
    if assistance == "unassisted":
        require(not leaked, "CUBE_UNASSISTED_PROFILE_DISCLOSES_ANSWER:" + ",".join(leaked))
    prompt = _prompt(bundle, public, view_id, candidate_set)
    record = {"schema": EXERCISE_SCHEMA, "split": "design_only",
              "op": public["op"], "graph": cube_node.graph_record(bundle, view_id),
              "question": public["question"], "options": candidate_set,
              "framings": {"cas": prompt, "generic": prompt},
              "cube": {"task_id": identity["task_id"],
                       "public_id": identity["public_id"], "view_id": view_id,
                       "assistance_level": assistance,
                       "delivery_id": delivery["delivery_id"],
                       "record_id_basis": "public_projection",
                       "visibility_profile_id": visibility_profile(
                           public["op"], assistance)["profile_id"]}}
    record = {**record, "record_id": identity["public_id"], "correct": derived,
              "encoding_target": "graph_derived_answer"}
    encoded = adapter.public_records(record, "cas")
    tokens = adapter.build_task(record, "cas")["tokens"]
    order = encoded["encoded_options"]
    require(sorted(order, key=canonical) == sorted(candidate_set, key=canonical),
            "CUBE_ENCODED_SET_MISMATCH")
    require(any(canonical(item) == canonical(derived) for item in order),
            "CUBE_ENCODED_SET_MISSES_DERIVED_ANSWER")
    require(encoded["encoded_correct_index"]
            == next(index for index, item in enumerate(order)
                    if canonical(item) == canonical(derived)),
            "CUBE_ENCODED_TARGET_INDEX_MISMATCH")
    return {
        "schema": LESSON_V2_SCHEMA, "status": cube_node.CUBE_STATUS,
        "task_id": identity["task_id"], "public_id": identity["public_id"],
        "identity_basis": identity["identity_basis"],
        "identity_core": identity["identity_core"],
        "delivery": delivery,
        "family_id": bundle["lesson_family_id"], "view_id": view_id,
        "operation": public["op"], "question": public["question"],
        "assistance_level": assistance, "assisted": assistance != "unassisted",
        "visibility": {"profile": visibility_profile(public["op"], assistance),
                       "visible_field_paths": visible,
                       "withheld_field_paths": withheld,
                       "mask_is_declared": visibility_is_declared(
                           bundle, asked, public["op"], assistance, withheld),
                       "disclosures_after_mask": leaked},
        "asked_nodes": asked,
        "derived_answer": derived,
        "candidate_set_content_order": candidate_set,
        "learner_view": {"question": public["question"], "choices": order,
                         "graph_scope": {
                             "nodes": [{"node_ref": node["node_id"],
                                        "label": cube_node.view_labels(bundle, view_id)[node["node_id"]],
                                        "revision": node["revision"]}
                                       for node in bundle["cube_nodes"]],
                             "branches": [{"branch_id": branch["branch_id"],
                                           "source": cube_node.view_labels(bundle, view_id)[branch["source_node_id"]],
                                           "predicate": branch["predicate"],
                                           "target": cube_node.view_labels(bundle, view_id)[branch["target_node_id"]],
                                           "commonality": branch["commonality"]["kind"]}
                                          for branch in sorted(bundle["branches"],
                                                               key=lambda item: item["branch_id"])]},
                         "visible_field_paths": visible,
                         "withheld_field_paths": withheld,
                         "provenance_refs": sorted({ref for node in bundle["cube_nodes"]
                                                    for ref in node["provenance_refs"]})},
        "encoding": {"public": encoded["public"],
                     "encoded_options": encoded["encoded_options"],
                     "encoded_correct_index": encoded["encoded_correct_index"],
                     "encoding_target": "graph_derived_answer",
                     "tokens": len(tokens),
                     "token_digest": digest(canonical(tokens))},
        "record": record,
        "slot_order_rule": ("the three public choices are ordered by the frozen "
                            "public-record extraction: it permutes them with a "
                            "seed derived from the public record id and the arm, "
                            "and the record id covers the public projection only, "
                            "so no slot depends on which choice is correct"),
    }


def attach_target(bundle, case, public_exercise, view_id="view_context"):
    """Attach the private target, refusing any target the graph does not derive."""
    derived = public_exercise["derived_answer"]
    declared = case["correct"]
    require(canonical(declared) == canonical(derived),
            "CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER:%s:%s"
            % (canonical(declared), canonical(derived)))
    options = public_exercise["learner_view"]["choices"]
    require(sum(1 for item in options if canonical(item) == canonical(declared)) == 1,
            "CUBE_OPTION_SET_MISSES_TARGET")
    declared_index = next(
        index for index, item in enumerate(options)
        if canonical(item) == canonical(declared))
    require(declared_index == public_exercise["encoding"]["encoded_correct_index"],
            "CUBE_TARGET_INDEX_DISAGREES_WITH_ENCODING")
    delivered = public_exercise["assistance_level"] != "unassisted"
    label = public_exercise["question"]
    return {
        "task_id": public_exercise["task_id"],
        "expected_answer": declared,
        "derived_answer": derived,
        "declared_correct_choice_index": declared_index,
        "worked_solution": [
            "%s(%s) = %s" % (public_exercise["operation"], canonical(label),
                             canonical(declared)),
            "derived by the deterministic reference checker from the stored "
            "contains branches only"],
        "corrective_feedback": (
            "The direct constituents are exactly the targets of the outgoing "
            "contains branches: %s." % ", ".join(map(str, declared))
            if public_exercise["operation"] == "LIST_PARTS"
            else "The checker derives %s from the stored branches." % canonical(declared)),
        "delivered": delivered,
        "delivery_note": ("shown as worked teaching during this lesson"
                          if delivered else
                          "recorded for scoring only; not delivered to the learner"),
        "target_can_steer_public_view": False,
        "why": ("a target that disagrees with the graph-derived answer is refused "
                "before any learner-facing object is built"),
    }


def compile_lesson(bundle, case, *, assistance, view_id="view_context"):
    """A versioned cube lesson: public exercise plus a checked private target."""
    public = compile_public_exercise(bundle, case, assistance=assistance,
                                    view_id=view_id)
    target = attach_target(bundle, case, public, view_id)
    return {**public, "target": target,
            "target_digest": digest(canonical(target))}


def residual_disclosures(bundle, case, assistance, view_id="view_context",
                         scope="asked_cubes"):
    """Disclosures that survive the declared mask, over one or every cube."""
    withheld = set(withheld_field_paths(
        bundle, cube_node._asked_nodes(bundle, case, view_id),
        case["op"], assistance))
    residual = []
    for item in disclosure_audit(bundle, case, view_id, scope):
        for leaf in item["leaf_paths"]:
            if leaf not in withheld:
                residual.append(leaf)
    return sorted(set(residual))


def audit_all_questions(bundle, view_id="view_context"):
    """Every askable question through the declared profiles, with the counters."""
    cases = cube_node.answer_cases(bundle, view_id)["cases"]
    unassisted_compiled = 0
    refused = []
    asked_residual = all_residual = 0
    for case in cases:
        try:
            compile_lesson(bundle, case, assistance="unassisted", view_id=view_id)
            unassisted_compiled += 1
        except ValueError as error:
            refused.append({"op": case["op"], "question": case["question"],
                            "code": str(error)})
        if residual_disclosures(bundle, case, "unassisted", view_id, "asked_cubes"):
            asked_residual += 1
        if residual_disclosures(bundle, case, "unassisted", view_id, "all_cubes"):
            all_residual += 1
    return {
        "questions": len(cases),
        "counts_by_operation": cube_node.answer_cases(bundle, view_id)["counts"],
        "unassisted_questions_compiled": unassisted_compiled,
        "unassisted_questions_refused": refused,
        "unassisted_residual_disclosures_asked_cubes": asked_residual,
        "unassisted_residual_disclosures_all_cubes": all_residual,
        "mask_scope": "the cubes the question asks about",
        "scope_note": ("a cube that is not asked about keeps its faces as teaching "
                       "context; its fields can only restate the public graph, and "
                       "the all-cubes number counts exactly those"),
        "visibility_version": visibility_version(),
        "prose_labels_excluded_from_matching": prose_index(bundle)[1],
    }


def build_report(bundle=None, view_id="view_context"):
    """The whole CUBE_TEACHING_PROFILE_001 reading for one demonstration question."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    chosen = cube_node.select_cases(bundle, view_id)
    case = chosen["LIST_PARTS"]
    profiles = {assistance: teaching_profile(bundle, case, assistance=assistance,
                                             view_id=view_id)
                for assistance in ("guided", "unassisted")}
    return {
        "schema": PROFILE_SCHEMA, "status": cube_node.CUBE_STATUS,
        "profile_id": "CUBE_TEACHING_PROFILE_001",
        "view_id": view_id,
        "demonstration_question": {"op": case["op"], "question": case["question"],
                                   "answer": case["correct"]},
        "scored_operations": list(CUBE_OPS),
        "profiles": profiles,
        "target_independence": target_independence_check(bundle, case, view_id),
        "legacy_ordering": legacy_ordering_demonstration(bundle, case, view_id),
        "audit_all_questions": audit_all_questions(bundle, view_id),
        "update_path": UPDATE_PATH,
        "boundary": {
            "training": "none", "reservation": "none", "launch": "none",
            "neural_calls": 0, "optimizer_updates": 0,
            "delivered_neural_lessons": 0,
            "unchanged": ["the zero-update contrast probe",
                          "the retained checkpoints and the measured negatives",
                          "the accepted models",
                          "every paid-run decision and the reservation allowance"],
        },
    }


# --------------------------------------------------------------------------
# 3. target independence over the whole construction path
# --------------------------------------------------------------------------

def target_independence_check(bundle, case, view_id="view_context"):
    """Exercise compile -> visibility -> encode for every assistance level.

    Three readings, all mechanical:

    * the public case object that the public path receives contains no target
      field, so nothing downstream can read one;
    * every learner-facing digest is identical when the same question is
      recompiled from an independently recomputed reference answer;
    * a declared target that disagrees with the graph-derived answer is refused
      with ``CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER``.
    """
    require(not (set(public_case(case)) & {"correct", "answer_refs", "derivation",
                                           "target"}),
            "CUBE_PUBLIC_CASE_CARRIES_TARGET")
    readings = []
    orders = {}
    for assistance in ASSISTANCE_LEVELS:
        first = compile_lesson(bundle, case, assistance=assistance, view_id=view_id)
        recomputed = dict(case)
        recomputed["correct"] = derived_answer(bundle, public_case(case), view_id)
        recomputed.pop("answer_refs", None)
        second = compile_lesson(bundle, recomputed, assistance=assistance,
                                view_id=view_id)
        faces = ("task_id", "public_id", "derived_answer")
        same = {name: canonical(first[name]) == canonical(second[name]) for name in faces}
        same["learner_view"] = (canonical(first["learner_view"])
                                == canonical(second["learner_view"]))
        same["withheld_field_paths"] = (canonical(first["visibility"]["withheld_field_paths"])
                                        == canonical(second["visibility"]["withheld_field_paths"]))
        same["visible_field_paths"] = (canonical(first["visibility"]["visible_field_paths"])
                                       == canonical(second["visibility"]["visible_field_paths"]))
        same["tokens"] = (first["encoding"]["token_digest"]
                          == second["encoding"]["token_digest"])
        same["encoded_public"] = (digest(canonical(first["encoding"]["public"]))
                                  == digest(canonical(second["encoding"]["public"])))
        orders[assistance] = {"order": first["learner_view"]["choices"],
                              "digest": digest(canonical(first["learner_view"]["choices"]))}
        options = first["learner_view"]["choices"]
        disagreeing = []
        for option in options:
            if canonical(option) == canonical(first["derived_answer"]):
                continue
            moved = dict(case)
            moved["correct"] = option
            moved.pop("answer_refs", None)
            code = cube_node.error_code(
                lambda moved=moved, assistance=assistance:
                    compile_lesson(bundle, moved, assistance=assistance, view_id=view_id))
            disagreeing.append({"declared_target": option, "code": code})
        readings.append({"assistance_level": assistance,
                         "identical_under_target_change": all(same.values()),
                         "digest_equal": same,
                         "disagreeing_targets": disagreeing,
                         "disagreeing_targets_refused": all(
                             (item["code"] or "").startswith(
                                 "CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER")
                             for item in disagreeing),
                         "mask_is_declared": first["visibility"]["mask_is_declared"],
                         "disclosures_after_mask": first["visibility"]["disclosures_after_mask"]})
    slot_order_shared = len({item["digest"] for item in orders.values()}) == 1
    return {"task_id": compile_lesson(bundle, case, assistance="unassisted",
                                      view_id=view_id)["task_id"],
            "view_id": view_id, "readings": readings,
            "slot_order_identical_across_assistance_levels": slot_order_shared,
            "slot_orders": orders,
            "public_case_carries_target": False,
            "rule": ("public task identity, option slots, mask, and tokens are "
                     "functions of the public exercise and the declared profile")}


def legacy_ordering_demonstration(bundle, case, view_id="view_context"):
    """Read-only reading of the legacy rule the owner asked to fix in new work.

    The existing lesson generator folds the private answer into ``record_id``
    (``lessons._record``), and the frozen public-record extraction derives slot
    order from ``record_id`` (``adapter.public_records``). This computes what
    that rule does to the same public option set under two different declared
    targets. It changes nothing and claims nothing about any model.
    """
    public = compile_public_exercise(bundle, case, assistance="unassisted",
                                     view_id=view_id)
    options = public["learner_view"]["choices"]
    orders = []
    for option in options:
        core = {"schema": EXERCISE_SCHEMA, "split": "design_only",
                "op": public["operation"], "graph": cube_node.graph_record(bundle, view_id),
                "question": public["question"], "options": options,
                "framings": {"cas": "legacy demonstration", "generic": "legacy demonstration"},
                "correct": option}
        record = {**core, "record_id": digest(canonical(core))}
        encoded = adapter.public_records(record, "cas")
        orders.append({"declared_target": option,
                       "legacy_record_id": record["record_id"],
                       "encoded_order": encoded["encoded_options"]})
    distinct = {canonical(item["encoded_order"]) for item in orders}
    return {"legacy_record_id_basis": "core_including_correct",
            "legacy_slot_order_source": "digest(record_id + arm)",
            "orders": orders,
            "slot_order_varies_with_target": len(distinct) > 1,
            "distinct_orders": len(distinct),
            "new_rule": public["slot_order_rule"],
            "action": "old records, datasets, and results are left unchanged",
            "claim": ("this is a reading of the existing data path; it is not "
                      "evidence that any model used the difference")}


# --------------------------------------------------------------------------
# 4. the seven-stage teaching profile
# --------------------------------------------------------------------------

STAGE_PLAN = (
    {"stage": 1, "stage_id": "name_and_function", "visits": ("core", "face_1"),
     "is_task": False, "scoring": "none",
     "note": "anchor the subject, its function, and the requested operation"},
    {"stage": 2, "stage_id": "context", "visits": ("face_2",),
     "is_task": False, "scoring": "none",
     "note": "show the idea inside the supplied graph"},
    {"stage": 3, "stage_id": "analogy", "visits": ("face_3",),
     "is_task": False, "scoring": "none",
     "note": ("guided presentation only in this profile: scoring an analogy "
              "needs a separately declared task profile")},
    {"stage": 4, "stage_id": "explicit_mapping", "visits": ("face_4",),
     "is_task": False, "scoring": "none",
     "note": ("the correspondence table is presented, not scored, in this profile")},
    {"stage": 5, "stage_id": "guided_decomposition", "visits": ("face_5",),
     "is_task": True, "scoring": "the three existing operations",
     "note": ("the scored question: prediction over three public slots, with the "
              "worked answer supplied only when the assistance level allows it")},
    {"stage": 6, "stage_id": "recomposition", "visits": ("face_6",),
     "is_task": False, "scoring": "none",
     "note": ("the story is presentation only; scoring a recomposition needs a "
              "separately declared task profile")},
    {"stage": 7, "stage_id": "reinforcement",
     "visits": ("core",) + tuple(cube_node.FACE_KEYS),
     "is_task": True, "scoring": "the three existing operations, declared variations",
     "note": ("repeat the connected lesson with declared variations; the same "
              "three operations, no new output contract")},
)

UPDATE_PATH = {
    "contract_id": TARGET_CONTRACT_ID,
    "plasticity_role": TARGET_PLASTICITY_ROLE,
    "would_update": "the registered module's own parameters only, through the "
                    "existing trainer allowlist",
    "excluded": ["the frozen encoder", "the frozen dot-product readout",
                 "any parameter outside the admitted plasticity role"],
    "objective": "cross-entropy over the three public slots against the declared "
                 "target index",
    "containment_check": ("trainer.containment_report must show no digest change "
                          "outside the allowlist"),
}


def stage_records(bundle, case, *, assistance, view_id="view_context"):
    """Per-stage: learner input, prediction, correction, update, assistance."""
    lesson = compile_lesson(bundle, case, assistance=assistance, view_id=view_id)
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    withheld = set(lesson["visibility"]["withheld_field_paths"])
    asked = lesson["asked_nodes"]
    supervised = assistance != "unassisted"
    records = []
    for plan in STAGE_PLAN:
        content = {}
        for ref in asked:
            node = node_index[ref]
            selected = {}
            if "core" in plan["visits"]:
                selected["core"] = node["core"]
            for key in plan["visits"]:
                if key in cube_node.FACE_KEYS:
                    selected[key] = node["faces"][key]
            replaced = []
            content[ref] = cube_node._withhold({ref: selected}, "", withheld,
                                              replaced)[ref]
        if plan["is_task"] and supervised:
            kind = "supervised_task"
        elif plan["is_task"]:
            kind = "assessment"
        else:
            kind = "presentation"
        records.append({
            "stage": plan["stage"], "stage_id": plan["stage_id"],
            "visits": list(plan["visits"]), "kind": kind,
            "assistance_level": assistance,
            "note": plan["note"],
            "learner_input": {
                "delivered_to_module": plan["is_task"],
                "public_record": lesson["encoding"]["public"] if plan["is_task"] else None,
                "tokens": lesson["encoding"]["tokens"] if plan["is_task"] else 0,
                "visible_field_paths": (lesson["visibility"]["visible_field_paths"]
                                        if plan["visits"] else []),
                "withheld_field_paths": (lesson["visibility"]["withheld_field_paths"]
                                         if plan["visits"] else []),
                "content_as_delivered": content,
                "visibility_profile_id": lesson["visibility"]["profile"]["profile_id"],
            },
            "prediction": {
                "required": bool(plan["is_task"]),
                "form": ("argmax over the three public option slots" if plan["is_task"]
                         else None),
                "slots": lesson["learner_view"]["choices"] if plan["is_task"] else None,
            },
            "correction": {
                "delivered": bool(plan["is_task"] and supervised),
                "expected_answer": lesson["target"]["expected_answer"] if plan["is_task"] else None,
                "target_index": (lesson["target"]["declared_correct_choice_index"]
                                 if plan["is_task"] else None),
                "worked_solution": (lesson["target"]["worked_solution"]
                                    if plan["is_task"] else None),
                "feedback": (lesson["target"]["corrective_feedback"]
                             if plan["is_task"] else None),
                "signal": (UPDATE_PATH["objective"] if plan["is_task"] else None),
            },
            "update": {
                "occurs_in_this_preparation": False,
                "would_occur_when_run": bool(plan["is_task"] and supervised),
                "path": UPDATE_PATH if (plan["is_task"] and supervised) else None,
                "reason_not_here": ("specification only: no module was constructed "
                                    "and no optimizer step was taken"),
            },
            "scored_task": lesson if plan["stage"] == 5 else None,
        })
    return records


def teaching_profile(bundle, case, *, assistance="guided", view_id="view_context"):
    """CUBE_TEACHING_PROFILE_001: one complete machine-facing seven-stage lesson."""
    lesson = compile_lesson(bundle, case, assistance=assistance, view_id=view_id)
    stages = stage_records(bundle, case, assistance=assistance, view_id=view_id)
    counts = {
        "stages": len(stages),
        "presentations": sum(1 for stage in stages if stage["kind"] == "presentation"),
        "supervised_tasks": sum(1 for stage in stages if stage["kind"] == "supervised_task"),
        "assessments": sum(1 for stage in stages if stage["kind"] == "assessment"),
        "module_inputs": sum(1 for stage in stages
                             if stage["learner_input"]["delivered_to_module"]),
        "predictions_required": sum(1 for stage in stages if stage["prediction"]["required"]),
        "corrective_examples": sum(1 for stage in stages if stage["correction"]["delivered"]),
        "optimizer_updates": 0,
        "delivered_neural_lessons": 0,
        "assistance_states_recorded": len({stage["assistance_level"] for stage in stages}),
        "assisted_tasks": sum(1 for stage in stages
                              if stage["kind"] == "supervised_task"),
        "unassisted_tasks": sum(1 for stage in stages if stage["kind"] == "assessment"),
        "distinct_graph_families": 1,
        "operation": lesson["operation"],
    }
    profile = {
        "schema": PROFILE_SCHEMA, "status": cube_node.CUBE_STATUS,
        "profile_id": "CUBE_TEACHING_PROFILE_001",
        "task_id": lesson["task_id"], "public_id": lesson["public_id"],
        "family_id": bundle["lesson_family_id"], "view_id": view_id,
        "operation": lesson["operation"], "question": lesson["question"],
        "assistance_level": assistance, "assisted": lesson["assisted"],
        "scored_operations": list(CUBE_OPS),
        "new_heads_required": [],
        "new_task_profiles_required_in_this_profile": [],
        "presentation_only_stages": [stage["stage"] for stage in stages
                                     if stage["kind"] == "presentation"],
        "unsupported_scorings_declined": [
            {"stage": 1, "candidate": "select the definition/function that matches"},
            {"stage": 2, "candidate": "select the relevant supplied contextual relation"},
            {"stage": 3, "candidate": "select the analogy preserving the relationship"},
            {"stage": 4, "candidate": "select the correct role correspondence"},
            {"stage": 6, "candidate": "select a valid recomposition or explanation"},
        ],
        "decline_reason": ("each needs a declared output vocabulary, loss, and "
                           "training adapter; this profile scores only the three "
                           "existing operations and presents the rest"),
        "separation": {
            "guided": "withholds nothing, labels every scored answer assisted",
            "unassisted": "retains the public graph, withholds the declared "
                          "decomposition and recomposition fields, delivers no "
                          "worked answer",
            "shared": "the same public exercise and the same three operations",
        },
        "stages": stages, "counts": counts,
        "visibility": lesson["visibility"],
        "update_path": UPDATE_PATH,
        "boundary": ("this preparation performs no optimizer step and delivers no "
                     "neural lesson; the counters above keep those at zero"),
    }
    profile["profile_digest"] = digest(canonical(
        {key: profile[key] for key in ("schema", "profile_id", "task_id", "public_id",
                                       "operation", "assistance_level", "counts",
                                       "visibility")}))
    return profile
