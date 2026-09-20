"""Cube Node Schema v0.1 — data contract, example bundle, and lesson compiler.

STATUS: design-only data work. This module trains nothing, reserves nothing,
launches nothing, and touches no network. The current contrast investigation,
the accepted models, the retained checkpoints, the registered curricula and
panels, and every paid-run decision are left exactly as they were.

What the cube is (owner design, ``Cube_Node_Schema_v0.1.md``):

- one **core** per node: stable identity/meaning in a declared context;
- six **faces** per node: technical identity, context, analogy, explicit
  correspondence, decomposition, recomposition;
- one **branch** per stored connector: ``source --predicate--> target`` with a
  declared commonality;
- **repetition** is the activity around the cube, not a seventh stored face.

What this module implements, and nothing more:

- the data contract of ``cas.cube-node/0.1`` as executable validation
  (``validate_bundle``), including the §12 invariants;
- the delivered illustrative bundle, pinned under ``records/`` and loaded by
  ``load_bundle`` (source identity recorded in that directory);
- a compiler that turns the cube into the three EXISTING whole-part exercises
  (``LIST_PARTS``, ``FIND_SHARED_PART``, ``REACHED_VIA``), computed by the
  unchanged deterministic reference checker, with the learner view and the
  teacher target as separate objects (``compile_lesson``);
- one complete seven-stage teaching cycle exactly as a learner would receive
  it, with per-stage visibility and an explicit completion count
  (``compile_cycle``, ``cycle_counts``);
- the §12 contrast set: consistent renaming, harmless reordering, rewiring, and
  the two consistency rejections (``contrast_report``);
- the §9 leakage boundary: what the learner's encoded input is, and the proof
  that changing the private target does not change it (``leakage_report``).

Two boundaries this module keeps:

- **The bundle is never a learner input.** ``validate_bundle`` refuses a bundle
  that does not declare an explicit visibility profile, and ``compile_lesson``
  never returns authoring fields wholesale: a lesson carries a ``learner_view``
  (public) and a separate ``teacher_target`` (private).
- **The mask is scoped to the asked cubes.** Only the faces of the nodes the
  question asks about can make that question assisted. Other cubes' faces stay
  visible as teaching context.

Nothing here claims that any adapter or module can use a cube. Section 10 of
the schema says the numeric adapter remains a separate, versioned change; this
module produces no adapter and no encoding beyond calling the frozen public
record extraction to measure the leakage boundary.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .graph import Graph, Node, Relation, canonical, digest, require
from .lessons import EXERCISE_SCHEMA
from . import adapter, fresh_panel, reference

CUBE_BUNDLE_SCHEMA = "cas.cube-bundle/0.1"
CUBE_NODE_SCHEMA = "cas.cube-node/0.1"
LESSON_SCHEMA = "cas-cube-lesson/1"
CYCLE_SCHEMA = "cas-cube-teaching-cycle/1"
CHECK_SCHEMA = "cas-cube-node-check/1"

CUBE_STATUS = "DESIGN_ONLY_ILLUSTRATIVE_DATA"

FACE_KEYS = ("face_1", "face_2", "face_3", "face_4", "face_5", "face_6")

# §2 of the schema: the stored role of each face.
FACE_ROLES = {
    "face_1": "technical_identity",
    "face_2": "context_and_environment",
    "face_3": "analogy_and_metaphor",
    "face_4": "explicit_correspondence",
    "face_5": "decomposition",
    "face_6": "recomposition_and_story",
}

# §3: minimum structured content when a face is populated.
FACE_STRUCTURED_MINIMUM = {
    "face_1": ("canonical_name", "definition", "function"),
    "face_2": ("view_refs", "fact_refs", "context_scope"),
    "face_3": ("view_refs", "mapping_refs", "analogy_scope", "analogy_limits"),
    "face_4": ("mapping_refs",),
    "face_5": ("direct_branch_refs", "completeness"),
    "face_6": ("steps", "sequence_kind"),
}

AVAILABILITY = ("populated", "unknown", "not_applicable")
COMPLETENESS = ("complete", "partial", "unknown")
SEQUENCE_KINDS = ("explanatory", "temporal", "causal")
CORE_KINDS = ("concept", "instance", "event", "procedure")
ASSISTANCE_LEVELS = ("worked", "guided", "hinted", "unassisted")
CUBE_OPS = ("LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA")

# §4: the initial whole-part profile stores exactly this predicate. Other
# predicates are data semantics that must be declared before use.
DEFAULT_PREDICATES = ("contains",)
FORBIDDEN_PREDICATES = ("answer", "correct", "solution", "expected")
FORBIDDEN_FIELD_NAMES = ("correct", "correct_index", "answer", "solution",
                         "expected_answer")

# §7: the seven stages. Stage 1 uses the core together with face 1; stage 7 is
# an operation over the cube, not a seventh stored component.
SEVEN_STAGES = (
    {"stage": 1, "stage_id": "name_and_function", "content_keys": ("core", "face_1")},
    {"stage": 2, "stage_id": "context", "content_keys": ("face_2",)},
    {"stage": 3, "stage_id": "analogy", "content_keys": ("face_3",)},
    {"stage": 4, "stage_id": "explicit_mapping", "content_keys": ("face_4",)},
    {"stage": 5, "stage_id": "guided_decomposition", "content_keys": ("face_5",)},
    {"stage": 6, "stage_id": "recomposition", "content_keys": ("face_6",)},
    {"stage": 7, "stage_id": "reinforcement",
     "content_keys": ("core",) + FACE_KEYS},
)

# §9 (the task table and its statuses) and §7 (the cycle): which stage exercise
# the current three-choice interface can already express, and which need a
# separately specified output, loss, and training profile.
STAGE_EXERCISE_STATUS = {
    1: ("new_task_profile_required",
        "select the definition/function that matches the presented concept"),
    2: ("new_task_profile_required",
        "select the supplied contextual relation relevant to the question"),
    3: ("new_task_profile_required",
        "select the analogy that preserves the same directed relationship"),
    4: ("new_task_profile_required",
        "select the correct role correspondence between two views"),
    5: ("existing_three_choice_interface",
        "LIST_PARTS / FIND_SHARED_PART / REACHED_VIA over the public graph"),
    6: ("new_task_profile_required",
        "select a valid recomposition or complete explanation from supplied parts"),
    7: ("existing_three_choice_interface",
        "repeat the connected lesson with declared variations of the same three ops"),
}

WITHHELD = "[withheld: answer-bearing for this question]"

RECORDS_DIR = (Path(__file__).resolve().parents[2] / "records" / "teaching_cycle_001"
               / "graph_first_candidate_001" / "training_mode_001")
CUBE_RECORD_DIR = RECORDS_DIR / "cube_node_001"
PINNED_BUNDLE_NAME = "Cube_Node_Example_v0.1.json"


# --------------------------------------------------------------------------
# bundle location and loading
# --------------------------------------------------------------------------

def pinned_bundle_path():
    """The delivered illustrative bundle, pinned inside this homebase."""
    return CUBE_RECORD_DIR / PINNED_BUNDLE_NAME


def load_bundle(path=None):
    """Load and fully validate a cube bundle. Fails closed on any violation."""
    path = Path(pinned_bundle_path() if path is None else path)
    require(path.is_file(), "CUBE_BUNDLE_FILE_MISSING:" + str(path))
    bundle = json.loads(path.read_text(encoding="utf-8"))
    validate_bundle(bundle)
    return bundle


def bundle_digest(bundle):
    return digest(canonical(bundle))


# --------------------------------------------------------------------------
# §12 validation
# --------------------------------------------------------------------------

def _require_string(value, code):
    require(type(value) is str and value.strip() != "", code)


def _records(items, key, code):
    index = {}
    for item in items:
        require(type(item) is dict, code + ":NOT_AN_OBJECT")
        identifier = item.get(key)
        _require_string(identifier, code + ":IDENTIFIER")
        require(identifier not in index, code + ":DUPLICATE:" + identifier)
        index[identifier] = item
    return index


def _outgoing(bundle):
    outgoing = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    incoming = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    incident = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    for branch in bundle["branches"]:
        outgoing[branch["source_node_id"]].append(branch)
        incoming[branch["target_node_id"]].append(branch)
        incident[branch["source_node_id"]].append(branch)
        incident[branch["target_node_id"]].append(branch)
    for mapping in (outgoing, incoming, incident):
        for key in mapping:
            mapping[key] = tuple(sorted(mapping[key], key=lambda item: item["branch_id"]))
    return outgoing, incoming, incident


def _direct_branch_refs(bundle, node_ref):
    outgoing, _, _ = _outgoing(bundle)
    return sorted(branch["branch_id"] for branch in outgoing[node_ref]
                  if branch["predicate"] == "contains")


def _contains_cycle(bundle):
    outgoing, _, _ = _outgoing(bundle)
    state = {}

    def visit(node_ref):
        state[node_ref] = "open"
        for branch in outgoing[node_ref]:
            if branch["predicate"] != "contains":
                continue
            target = branch["target_node_id"]
            if state.get(target) == "open":
                return True
            if state.get(target) is None and visit(target):
                return True
        state[node_ref] = "closed"
        return False

    return any(visit(node_ref) for node_ref in sorted(outgoing) if state.get(node_ref) is None)


def _validate_node(bundle, node, context_id, source_ids):
    require(node.get("schema_version") == CUBE_NODE_SCHEMA,
            "CUBE_NODE_SCHEMA:" + str(node.get("node_id")))
    revision = node.get("revision")
    require(type(revision) is int and revision > 0, "CUBE_NODE_REVISION")
    require(node.get("context_id") == context_id, "CUBE_NODE_CONTEXT_MISMATCH")
    core = node.get("core")
    require(type(core) is dict, "CUBE_CORE_REQUIRED")
    require(set(core) == {"label", "kind", "identity_statement"}, "CUBE_CORE_FIELDS")
    _require_string(core["label"], "CUBE_CORE_LABEL")
    require(core["kind"] in CORE_KINDS, "CUBE_CORE_KIND:" + str(core["kind"]))
    _require_string(core["identity_statement"], "CUBE_CORE_IDENTITY_STATEMENT")
    faces = node.get("faces")
    require(type(faces) is dict, "CUBE_FACES_REQUIRED")
    require(tuple(sorted(faces)) == tuple(sorted(FACE_KEYS)), "CUBE_FACE_KEYS")
    for key in FACE_KEYS:
        face = faces[key]
        require(type(face) is dict, "CUBE_FACE_OBJECT:" + key)
        availability = face.get("availability")
        require(availability in AVAILABILITY, "CUBE_FACE_AVAILABILITY:" + key)
        _require_string(face.get("human_text"), "CUBE_FACE_HUMAN_TEXT:" + key)
        structured = face.get("structured")
        require(type(structured) is dict, "CUBE_FACE_STRUCTURED:" + key)
        if availability == "populated":
            require(structured, "CUBE_FACE_POPULATED_EMPTY:" + key)
            for name in FACE_STRUCTURED_MINIMUM[key]:
                require(name in structured,
                        "CUBE_FACE_STRUCTURED_MINIMUM:%s:%s" % (key, name))
        else:
            # §3: unknown and not_applicable carry an explanation and no content.
            require(structured == {}, "CUBE_UNKNOWN_FACE_MUST_BE_EMPTY:" + key)
        _require_provenance(face.get("provenance_refs"), source_ids,
                            "CUBE_FACE_PROVENANCE:" + key)
    _require_provenance(node.get("provenance_refs"), source_ids, "CUBE_NODE_PROVENANCE")


def _require_provenance(refs, source_ids, code):
    require(type(refs) is list and refs, code + ":REQUIRED")
    for ref in refs:
        _require_string(ref, code + ":REFERENCE")
        require(ref in source_ids, code + ":UNRESOLVED:" + ref)


def _validate_branch(bundle, branch, context_id, node_index, source_ids,
                     predicates):
    require(branch.get("context_id") == context_id, "CUBE_BRANCH_CONTEXT_MISMATCH")
    _require_string(branch.get("predicate"), "CUBE_BRANCH_PREDICATE")
    predicate = branch["predicate"]
    require(predicate not in FORBIDDEN_PREDICATES, "CUBE_ANSWER_EDGE_FORBIDDEN")
    require(predicate in predicates,
            "CUBE_BRANCH_PREDICATE_NOT_DECLARED:" + predicate)
    for key in ("source_node_id", "target_node_id"):
        require(branch.get(key) in node_index,
                "CUBE_BRANCH_ENDPOINT_UNRESOLVED:" + str(branch.get(key)))
    require(branch["source_node_id"] != branch["target_node_id"], "CUBE_SELF_CONTAINMENT")
    commonality = branch.get("commonality")
    require(type(commonality) is dict and set(commonality) == {"kind", "referent"},
            "CUBE_BRANCH_COMMONALITY")
    _require_string(commonality["kind"], "CUBE_BRANCH_COMMONALITY_KIND")
    require(commonality["referent"] in node_index,
            "CUBE_BRANCH_COMMONALITY_REFERENT_UNRESOLVED:" + str(commonality["referent"]))
    if predicate == "contains":
        # §4: the shared constituent is the target for the containment profile.
        require(commonality["referent"] == branch["target_node_id"],
                "CUBE_BRANCH_COMMONALITY_NOT_TARGET")
    _require_provenance(branch.get("provenance_refs"), source_ids,
                        "CUBE_BRANCH_PROVENANCE")
    key = (predicate, branch["source_node_id"], branch["target_node_id"])
    require(all((item["predicate"], item["source_node_id"], item["target_node_id"]) != key
                for item in bundle["branches"] if item is not branch),
            "CUBE_BRANCH_DUPLICATE")


def _validate_view(bundle, view, node_index, branch_index, context_id):
    require(type(view.get("node_labels")) is dict, "CUBE_VIEW_NODE_LABELS")
    labels = view["node_labels"]
    for ref in labels:
        require(ref in node_index, "CUBE_VIEW_NODE_UNRESOLVED:" + ref)
    require(sorted(labels) == sorted(node_index), "CUBE_VIEW_LABELS_INCOMPLETE")
    values = list(labels.values())
    require(len(values) == len(set(values)), "CUBE_VIEW_LABEL_DUPLICATE")
    for ref, label in labels.items():
        _require_string(label, "CUBE_VIEW_LABEL:" + ref)
    require(type(view.get("branch_refs")) is list, "CUBE_VIEW_BRANCH_REFS")
    for ref in view["branch_refs"]:
        require(ref in branch_index, "CUBE_VIEW_BRANCH_UNRESOLVED:" + str(ref))
    _require_string(view.get("relation_label"), "CUBE_VIEW_RELATION_LABEL")
    _require_string(view.get("scope"), "CUBE_VIEW_SCOPE")
    _require_string(view.get("kind"), "CUBE_VIEW_KIND")
    require(view.get("context_id", context_id) == context_id,
            "CUBE_VIEW_CONTEXT_MISMATCH")


def _validate_mapping(bundle, mapping, node_index, branch_index, views, family_id,
                      source_ids):
    require(mapping.get("lesson_family_id") == family_id,
            "CUBE_MAPPING_FAMILY_MISMATCH")
    require(type(mapping.get("view_ids")) is list and mapping["view_ids"],
            "CUBE_MAPPING_VIEWS")
    for view_id in mapping["view_ids"]:
        require(view_id in views, "CUBE_MAPPING_VIEW_UNRESOLVED:" + str(view_id))
    kinds = {views[view_id]["kind"]: view_id for view_id in mapping["view_ids"]}
    require(set(kinds) == {"technical", "context", "analogy"},
            "CUBE_MAPPING_VIEW_KINDS")
    rows = mapping.get("node_role_rows")
    require(type(rows) is list and rows, "CUBE_MAPPING_ROLE_ROWS")
    seen_roles, seen_nodes = set(), set()
    for row in rows:
        require(type(row) is dict, "CUBE_MAPPING_ROLE_ROW")
        require(set(row) == {"role_id", "node_ref", "technical", "contextual",
                             "analogical"}, "CUBE_MAPPING_ROLE_ROW_FIELDS")
        require(row["node_ref"] in node_index, "CUBE_MAPPING_NODE_UNRESOLVED")
        require(row["node_ref"] not in seen_nodes, "CUBE_MAPPING_NODE_REPEATED")
        require(row["role_id"] not in seen_roles, "CUBE_MAPPING_ROLE_REPEATED")
        seen_roles.add(row["role_id"])
        seen_nodes.add(row["node_ref"])
        # §5: a role row must agree with each view's own label for that node,
        # otherwise an old explanation stays attached to a changed presentation.
        for kind, field in (("technical", "technical"), ("context", "contextual"),
                            ("analogy", "analogical")):
            require(views[kinds[kind]]["node_labels"][row["node_ref"]] == row[field],
                    "CUBE_MAPPING_ROLE_LABEL_MISMATCH:%s:%s"
                    % (kinds[kind], row["node_ref"]))
    require(seen_nodes == set(node_index), "CUBE_MAPPING_COVERAGE_INCOMPLETE")
    relation_rows = mapping.get("relation_rows")
    require(type(relation_rows) is list, "CUBE_MAPPING_RELATION_ROWS")
    covered = set()
    for row in relation_rows:
        require(set(row) == {"branch_ref", "technical_predicate",
                             "contextual_predicate", "analogical_predicate"},
                "CUBE_MAPPING_RELATION_ROW_FIELDS")
        require(row["branch_ref"] in branch_index, "CUBE_MAPPING_BRANCH_UNRESOLVED")
        covered.add(row["branch_ref"])
        # §5: the declared relation must be preserved across the views, and the
        # statement stays scoped to the authored fixture.
        for kind, field in (("technical", "technical_predicate"),
                            ("context", "contextual_predicate"),
                            ("analogy", "analogical_predicate")):
            require(row[field] == views[kinds[kind]]["relation_label"],
                    "CUBE_MAPPING_RELATION_NOT_PRESERVED:%s" % row["branch_ref"])
    if mapping.get("coverage") == "exact_on_declared_scope":
        require(covered == set(branch_index), "CUBE_MAPPING_BRANCH_UNMAPPED")
    require(mapping.get("coverage") in ("exact_on_declared_scope", "partial"),
            "CUBE_MAPPING_COVERAGE")
    require(type(mapping.get("unmapped_items")) is list, "CUBE_MAPPING_UNMAPPED_ITEMS")
    require(type(mapping.get("limits")) is list and mapping["limits"],
            "CUBE_MAPPING_LIMITS_REQUIRED")
    _require_provenance(mapping.get("provenance_refs"), source_ids,
                        "CUBE_MAPPING_PROVENANCE")


def _require_face5_inventory(bundle, node):
    """§13: a face must not keep describing a graph it no longer matches."""
    face_5 = node["faces"]["face_5"]
    if face_5["availability"] != "populated":
        return
    structured = face_5["structured"]
    if structured.get("completeness") != "complete":
        return
    # §4: a complete inventory inside a context that declares the relation
    # inventory incomplete would license a negative answer the authoring data
    # does not support.
    require(bundle["context"]["contains_inventory_complete"],
            "CUBE_FACE5_COMPLETE_IN_INCOMPLETE_CONTEXT:" + node["node_id"])
    expected = _direct_branch_refs(bundle, node["node_id"])
    require(sorted(structured.get("direct_branch_refs", ())) == expected,
            "CUBE_FACE5_DIRECT_BRANCH_MISMATCH:" + node["node_id"])


def _validate_faces_against_branches(bundle, node, node_index, branch_index):
    """Face content must agree with the stored branches (§13, §12 scope)."""
    node_ref = node["node_id"]
    outgoing, _, incident = _outgoing(bundle)
    expected = _direct_branch_refs(bundle, node_ref)
    incident_refs = sorted(branch["branch_id"] for branch in incident[node_ref])
    face_2 = node["faces"]["face_2"]
    if face_2["availability"] == "populated":
        for ref in face_2["structured"]["fact_refs"]:
            require(ref in branch_index, "CUBE_FACE2_FACT_UNRESOLVED:" + str(ref))
            require(ref in incident_refs, "CUBE_FACE2_FACT_NOT_INCIDENT:" + str(ref))
    face_5 = node["faces"]["face_5"]
    _require_face5_inventory(bundle, node)
    if face_5["availability"] == "populated":
        structured = face_5["structured"]
        require(structured["completeness"] in COMPLETENESS, "CUBE_FACE5_COMPLETENESS")
        for ref in structured["direct_branch_refs"]:
            require(ref in branch_index, "CUBE_FACE5_BRANCH_UNRESOLVED:" + str(ref))
    face_6 = node["faces"]["face_6"]
    if face_6["availability"] == "populated":
        structured = face_6["structured"]
        require(structured["sequence_kind"] in SEQUENCE_KINDS, "CUBE_FACE6_SEQUENCE_KIND")
        for step in structured["steps"]:
            require(set(step) == {"step_id", "text", "uses_branch_refs"},
                    "CUBE_FACE6_STEP_FIELDS")
            _require_string(step["step_id"], "CUBE_FACE6_STEP_ID")
            _require_string(step["text"], "CUBE_FACE6_STEP_TEXT")
            for ref in step["uses_branch_refs"]:
                require(ref in branch_index, "CUBE_FACE6_BRANCH_UNRESOLVED:" + str(ref))
                require(ref in expected, "CUBE_FACE6_BRANCH_NOT_OUTGOING:" + str(ref))


def _validate_no_answer_fields(bundle):
    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                require(key.lower() not in FORBIDDEN_FIELD_NAMES,
                        "CUBE_ANSWER_FIELD_FORBIDDEN:" + path + "." + key)
                walk(item, path + "." + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, "%s[%d]" % (path, index))

    walk({"cube_nodes": bundle["cube_nodes"], "branches": bundle["branches"]},
         "bundle")


def validate_bundle(bundle):
    """Every §12 invariant that the data alone can decide. Returns a report."""
    require(type(bundle) is dict, "CUBE_BUNDLE_OBJECT")
    require(bundle.get("schema_version") == CUBE_BUNDLE_SCHEMA, "CUBE_BUNDLE_SCHEMA")
    context = bundle.get("context")
    require(type(context) is dict, "CUBE_CONTEXT_REQUIRED")
    context_id = context.get("context_id")
    _require_string(context_id, "CUBE_CONTEXT_ID")
    require(type(context.get("contains_inventory_complete")) is bool,
            "CUBE_CONTEXT_COMPLETENESS_FLAG")
    sources = bundle.get("sources")
    require(type(sources) is list and sources, "CUBE_SOURCES_REQUIRED")
    source_ids = set()
    for source in sources:
        _require_string(source.get("source_id"), "CUBE_SOURCE_ID")
        source_ids.add(source["source_id"])
    require(len(source_ids) == len(sources), "CUBE_SOURCE_ID_DUPLICATE")
    nodes = bundle.get("cube_nodes")
    require(type(nodes) is list and nodes, "CUBE_NODES_REQUIRED")
    node_index = _records(nodes, "node_id", "CUBE_NODE")
    predicates = tuple(bundle.get("relation_profiles", {}).get(
        "stored_predicates", DEFAULT_PREDICATES))
    for predicate in predicates:
        require(predicate not in FORBIDDEN_PREDICATES, "CUBE_ANSWER_EDGE_FORBIDDEN")
    branches = bundle.get("branches")
    require(type(branches) is list and branches, "CUBE_BRANCHES_REQUIRED")
    branch_index = _records(branches, "branch_id", "CUBE_BRANCH")
    for node in nodes:
        _validate_node(bundle, node, context_id, source_ids)
    for branch in branches:
        _validate_branch(bundle, branch, context_id, node_index, source_ids,
                         predicates)
    require(not _contains_cycle(bundle), "CUBE_CONTAINS_CYCLE")
    for node in nodes:
        _validate_faces_against_branches(bundle, node, node_index, branch_index)
    views = bundle.get("views")
    require(type(views) is list and views, "CUBE_VIEWS_REQUIRED")
    view_index = _records(views, "view_id", "CUBE_VIEW")
    for view in views:
        _validate_view(bundle, view, node_index, branch_index, context_id)
    mappings = bundle.get("mappings")
    require(type(mappings) is list and mappings, "CUBE_MAPPINGS_REQUIRED")
    _records(mappings, "mapping_id", "CUBE_MAPPING")
    family_id = bundle.get("lesson_family_id")
    _require_string(family_id, "CUBE_LESSON_FAMILY_ID")
    for mapping in mappings:
        _validate_mapping(bundle, mapping, node_index, branch_index, view_index,
                          family_id, source_ids)
    requirement = bundle.get("learner_view_requirement")
    require(type(requirement) is dict, "CUBE_LEARNER_VIEW_REQUIREMENT")
    require(requirement.get("must_compile_explicit_visibility_profile") is True,
            "CUBE_LEARNER_VIEW_PROFILE_REQUIRED")
    require(requirement.get("teacher_targets_included") is False,
            "CUBE_BUNDLE_MUST_NOT_BE_A_LEARNER_INPUT")
    _validate_no_answer_fields(bundle)
    return {"schema_version": bundle["schema_version"], "context_id": context_id,
            "lesson_family_id": family_id, "nodes": len(nodes),
            "branches": len(branches), "views": len(views),
            "mappings": len(mappings), "context_complete":
                bool(context["contains_inventory_complete"]),
            "bundle_digest": bundle_digest(bundle)}


def error_code(call):
    """Run ``call`` and return the full CUBE_ error message, or None."""
    try:
        call()
    except ValueError as error:
        return str(error)
    return None


def face_consistency_code(bundle):
    """The first face-versus-branch violation, with nothing else checked.

    Validation fails closed on the first violation it finds, so a bundle can be
    rejected for several reasons at once. This probe isolates the §13 rule that
    a face must not keep describing a graph it no longer matches.
    """
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    branch_index = {branch["branch_id"]: branch for branch in bundle["branches"]}
    for node in bundle["cube_nodes"]:
        code = error_code(lambda node=node: _validate_faces_against_branches(
            bundle, node, node_index, branch_index))
        if code is not None:
            return code
    return None


def face_inventory_code(bundle):
    """Only the decomposition-face inventory rule, probed on its own."""
    for node in bundle["cube_nodes"]:
        code = error_code(lambda node=node: _require_face5_inventory(bundle, node))
        if code is not None:
            return code
    return None


# --------------------------------------------------------------------------
# structure: the containment graph, its signature, and its answers
# --------------------------------------------------------------------------

def view_labels(bundle, view_id):
    for view in bundle["views"]:
        if view["view_id"] == view_id:
            return dict(view["node_labels"])
    raise ValueError("CUBE_VIEW_UNKNOWN:" + str(view_id))


def label_index(bundle):
    """label -> {node_ref}, across every view (used for disclosure scanning)."""
    index = {}
    for view in bundle["views"]:
        for ref, label in view["node_labels"].items():
            index.setdefault(label, set()).add(ref)
    return index


def containment_graph(bundle, view_id="view_context"):
    """The public graph for one presentation: nodes and contains branches."""
    labels = view_labels(bundle, view_id)
    nodes = tuple(Node(labels[ref], "idea", ()) for ref in sorted(labels))
    relations = tuple(
        Relation("contains", labels[branch["source_node_id"]],
                 labels[branch["target_node_id"]],
                 content=("constituent", labels[branch["target_node_id"]]))
        for branch in sorted(bundle["branches"], key=lambda item: item["branch_id"]))
    return Graph(nodes=nodes, relations=relations).validate()


def graph_record(bundle, view_id="view_context"):
    return containment_graph(bundle, view_id).to_record()


def _structural_ids(bundle, view_id):
    """Label-invariant node types of the containment structure.

    Reuses the frozen label-invariant refinement used by the panels, so a cube
    renamed consistently cannot look like a new arrangement.
    """
    record = {"graph": graph_record(bundle, view_id)}
    return fresh_panel._structural_ids(record)


def containment_signature(bundle, view_id="view_context"):
    """(node type multiset, typed edge multiset): the arrangement without names."""
    node_ids = _structural_ids(bundle, view_id)
    edges = sorted((relation["kind"], node_ids[relation["source"]],
                    node_ids[relation["target"]])
                   for relation in graph_record(bundle, view_id)["relations"])
    return {"node_types": sorted(node_ids.values()), "edges": edges,
            "digest": digest(canonical([sorted(node_ids.values()), edges]))}


def answer_cases(bundle, view_id="view_context"):
    """Every scorable question this cube can ask, with the reference answer.

    Ambiguous questions are rejected, not silently scored (§9): a shared-part
    question with more than one shared constituent has no single correct
    option in the three-choice interface.
    """
    graph = containment_graph(bundle, view_id)
    complete = bool(bundle["context"]["contains_inventory_complete"])
    labels = sorted(node.identifier for node in graph.nodes)
    cases, rejected = [], []

    def case(op, question, correct, answer_refs, basis):
        return {"op": op, "question": question, "correct": correct,
                "answer_refs": sorted(answer_refs), "completeness_basis": basis}

    refs_by_label = {label: ref for ref, label in
                     view_labels(bundle, view_id).items()}
    all_parts = {label: reference.direct_parts(graph, label) for label in labels}
    for label in labels:
        parts = all_parts[label]
        if not parts and not complete:
            rejected.append({"op": "LIST_PARTS", "question": {"idea": label},
                             "code": "CUBE_NEGATIVE_ANSWER_REQUIRES_COMPLETENESS"})
            continue
        cases.append(case("LIST_PARTS", {"idea": label}, parts,
                          {refs_by_label[part] for part in parts},
                          "declared_complete" if complete else "not_needed"))
    for first in labels:
        for second in labels:
            if first >= second:
                continue
            shared = reference.shared_parts(graph, first, second)
            if len(shared) > 1:
                rejected.append({"op": "FIND_SHARED_PART",
                                 "question": {"a": first, "b": second},
                                 "code": "FIND_SHARED_PART_MULTI_ANSWER"})
                continue
            if not shared and not complete:
                rejected.append({"op": "FIND_SHARED_PART",
                                 "question": {"a": first, "b": second},
                                 "code": "CUBE_NEGATIVE_ANSWER_REQUIRES_COMPLETENESS"})
                continue
            answer = shared[0] if shared else "none"
            cases.append(case("FIND_SHARED_PART", {"a": first, "b": second}, answer,
                              {refs_by_label[answer]} if shared else set(),
                              "declared_complete" if complete else "not_needed"))
    for idea in labels:
        for part in labels:
            if part == idea:
                continue
            kind = reference.reach_kind(graph, part, idea)
            if kind == "absent" and not complete:
                rejected.append({"op": "REACHED_VIA",
                                 "question": {"part": part, "idea": idea},
                                 "code": "CUBE_NEGATIVE_ANSWER_REQUIRES_COMPLETENESS"})
                continue
            if kind == "direct":
                answer_refs = {refs_by_label[part]}
            elif kind.startswith("via:"):
                answer_refs = {refs_by_label[kind[4:]]}
            else:
                answer_refs = set()
            cases.append(case("REACHED_VIA", {"part": part, "idea": idea}, kind,
                              answer_refs,
                              "declared_complete" if complete else "not_needed"))
    for item in cases:
        item["case_key"] = digest(canonical({"op": item["op"],
                                             "question": item["question"]}))
        item["derivation"] = reference.derivation_for(item["op"], graph,
                                                     item["question"])
        item["view_id"] = view_id
    return {"cases": cases, "rejected": rejected, "counts": _count_by_op(cases)}


def _count_by_op(cases):
    counts = {op: 0 for op in CUBE_OPS}
    for item in cases:
        counts[item["op"]] += 1
    return counts


def answer_signature(bundle, view_id="view_context"):
    """Label-invariant signature of every answer the cube can be asked for."""
    case_set = answer_cases(bundle, view_id)["cases"]
    node_ids = _structural_ids(bundle, view_id)
    graph = containment_graph(bundle, view_id)
    by_label = {node.identifier: node_ids[node.identifier] for node in graph.nodes}

    def role(value):
        if isinstance(value, list):
            return ["list"] + sorted((role(item) for item in value), key=canonical)
        if isinstance(value, str) and value.startswith("via:"):
            return ["via", by_label[value[4:]]]
        if value in ("none", "absent", "direct"):
            return ["literal", value]
        return ["node", by_label[value]]

    def question_roles(item):
        if item["op"] == "FIND_SHARED_PART":
            # A shared part is symmetric in its two wholes, so the pair is
            # canonicalised: otherwise the same typed pair could be listed in
            # either slot depending on which label happened to sort first.
            pair = sorted((role(item["question"]["a"]), role(item["question"]["b"])),
                          key=canonical)
            return [["pair"] + pair]
        return sorted((key, role(item["question"][key]))
                      for key in ("idea", "a", "b", "part")
                      if key in item["question"])

    signature = sorted(
        [[item["op"], question_roles(item), role(item["correct"])]
         for item in case_set], key=canonical)
    return {"digest": digest(canonical(signature)), "cases": len(case_set),
            "counts": _count_by_op(case_set)}


def select_cases(bundle, view_id="view_context"):
    """The handoff's one question per operation, chosen by a stated rule.

    LIST_PARTS: the whole with the most direct parts (ties by label).
    FIND_SHARED_PART: the first pair with exactly one shared constituent.
    REACHED_VIA: a supported indirect path if the scene has one, else a direct
    edge. Every choice is deterministic and derived from the public structure.
    """
    cases = answer_cases(bundle, view_id)["cases"]
    chosen = {}
    list_cases = [item for item in cases if item["op"] == "LIST_PARTS"]
    chosen["LIST_PARTS"] = sorted(
        list_cases, key=lambda item: (-len(item["correct"]), item["question"]["idea"]))[0]
    shared_cases = [item for item in cases
                    if item["op"] == "FIND_SHARED_PART" and item["correct"] != "none"]
    chosen["FIND_SHARED_PART"] = (sorted(
        shared_cases, key=lambda item: (item["question"]["a"], item["question"]["b"]))[0]
        if shared_cases else None)
    reach_cases = [item for item in cases if item["op"] == "REACHED_VIA"]
    indirect = [item for item in reach_cases
                if isinstance(item["correct"], str) and item["correct"].startswith("via:")]
    chosen["REACHED_VIA"] = (sorted(indirect, key=lambda item: (
        item["question"]["idea"], item["question"]["part"]))[0] if indirect else
        sorted(reach_cases, key=lambda item: (item["question"]["idea"],
                                              item["question"]["part"]))[0])
    return chosen


# --------------------------------------------------------------------------
# visibility: which face paths would make a question assisted
# --------------------------------------------------------------------------

def _is_scalar_list(value):
    return isinstance(value, list) and all(
        not isinstance(item, (dict, list)) for item in value)


def node_paths(node):
    """Every addressable leaf path of one cube, core and faces included."""
    paths = []

    def walk(value, prefix):
        if isinstance(value, dict):
            for key in sorted(value):
                walk(value[key], prefix + "." + key)
        elif _is_scalar_list(value):
            paths.append(prefix)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, "%s[%d]" % (prefix, index))
        else:
            paths.append(prefix)

    walk(node["core"], node["node_id"] + ".core")
    for key in FACE_KEYS:
        walk(node["faces"][key], "%s.%s" % (node["node_id"], key))
    return sorted(paths)


def _branch_targets(bundle, refs):
    index = {branch["branch_id"]: branch for branch in bundle["branches"]}
    return {index[ref]["target_node_id"] for ref in refs if ref in index}


def _mentioned_refs(text, index):
    found = set()
    for label, refs in index.items():
        if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(label), text):
            found.update(refs)
    return found


def disclosure_candidates(bundle, node):
    """Face content on one cube that could hand over this cube's own answer.

    Two kinds are candidates, both from the decomposition-bearing faces:

    * reference fields (``face_2.fact_refs``, ``face_5.direct_branch_refs``,
      ``face_6...uses_branch_refs``), individually and as the whole face's
      union — a face-6 story enumerating the answer is the union of its steps;
    * any text leaf that names another cube by label, in any view — a
      cross-view mention is exactly how a solution leaks between views.

    The mask built from this list is deliberately conservative: a field that
    references any node of the answer is withheld, even when the public graph
    would let the learner derive that node anyway. The graph itself is the
    exercise and always stays visible; a precomputed inventory is not the
    exercise.
    """
    index = label_index(bundle)
    own = {node["node_id"]}
    candidates = []

    def add(path, refs, source, leaf_paths):
        useful = refs - own
        if useful:
            candidates.append({"path": path, "refs": sorted(useful),
                               "source": source, "leaf_paths": sorted(leaf_paths)}) 

    face_2 = node["faces"]["face_2"]["structured"]
    if node["faces"]["face_2"]["availability"] == "populated":
        path = "%s.face_2.structured.fact_refs" % node["node_id"]
        add(path, _branch_targets(bundle, face_2["fact_refs"]), "references", [path])
    face_5 = node["faces"]["face_5"]["structured"]
    if node["faces"]["face_5"]["availability"] == "populated":
        path = "%s.face_5.structured.direct_branch_refs" % node["node_id"]
        add(path, _branch_targets(bundle, face_5["direct_branch_refs"]),
            "references", [path])
    face_6 = node["faces"]["face_6"]["structured"]
    if node["faces"]["face_6"]["availability"] == "populated":
        refs_union, text_union, ref_leaves, text_leaves = set(), set(), [], []
        for index_, step in enumerate(face_6["steps"]):
            base = "%s.face_6.structured.steps[%d]" % (node["node_id"], index_)
            ref_path = base + ".uses_branch_refs"
            text_path = base + ".text"
            ref_leaves.append(ref_path)
            text_leaves.append(text_path)
            refs_union.update(_branch_targets(bundle, step["uses_branch_refs"]))
            text_union.update(_mentioned_refs(step["text"], index))
            add(ref_path, _branch_targets(bundle, step["uses_branch_refs"]),
                "references", [ref_path])
            add(text_path, _mentioned_refs(step["text"], index), "text", [text_path])
        add("%s.face_6.structured.steps[*].uses_branch_refs" % node["node_id"],
            refs_union, "references", ref_leaves)
        add("%s.face_6.structured.steps[*].text" % node["node_id"],
            text_union, "text", text_leaves)
    for key in FACE_KEYS:
        face = node["faces"][key]
        path = "%s.%s.human_text" % (node["node_id"], key)
        add(path, _mentioned_refs(face["human_text"], index), "text", [path])
    return candidates


def answer_bearing_paths(bundle, case, view_id="view_context"):
    """The face paths of the asked cubes that would hand over this answer."""
    node_refs = _asked_nodes(bundle, case, view_id)
    wanted = set(case["answer_refs"])
    if not wanted:
        return []
    index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    found = []
    for node_ref in sorted(node_refs):
        for candidate in disclosure_candidates(bundle, index[node_ref]):
            matched = sorted(wanted & set(candidate["refs"]))
            if matched:
                found.append({"path": candidate["path"], "matched": matched,
                              "source": candidate["source"],
                              "leaf_paths": candidate["leaf_paths"]})
    return found


def _asked_nodes(bundle, case, view_id):
    """The cubes a question is about: their faces can assist the answer."""
    labels = view_labels(bundle, view_id)
    by_label = {label: ref for ref, label in labels.items()}
    refs = set()
    for key in ("idea", "a", "b"):
        if key in case["question"]:
            refs.add(by_label[case["question"][key]])
    if "part" in case["question"]:
        refs.add(by_label[case["question"]["part"]])
        refs.add(by_label[case["question"]["idea"]])
    return refs


def _join(prefix, key):
    return key if not prefix else prefix + "." + key


def _withhold(value, prefix, masked, replaced):
    if isinstance(value, dict):
        return {key: _withhold(value[key], _join(prefix, key), masked, replaced)
                for key in sorted(value)}
    if _is_scalar_list(value):
        if prefix in masked:
            replaced.append(prefix)
            return WITHHELD
        return list(value)
    if isinstance(value, list):
        return [_withhold(item, prefix + "[%d]" % index, masked, replaced)
                for index, item in enumerate(value)]
    if prefix in masked:
        replaced.append(prefix)
        return WITHHELD
    return value


# --------------------------------------------------------------------------
# lesson compilation
# --------------------------------------------------------------------------

def _choice_distractors(bundle, case, view_id):
    graph = containment_graph(bundle, view_id)
    labels = sorted(node.identifier for node in graph.nodes)
    correct = case["correct"]
    if case["op"] == "LIST_PARTS":
        idea = case["question"]["idea"]
        nested = [part for part in reference.transitive_parts(graph, idea)
                  if part not in correct]
        options = []
        if nested:
            options.append(sorted(correct + nested[:1]))
        if len(correct) > 1:
            options.append(sorted(correct[:-1]))
        others = [sorted(reference.direct_parts(graph, other)) for other in labels
                  if other != idea]
        options.extend(item for item in others if item != correct)
        return options
    if case["op"] == "FIND_SHARED_PART":
        options = [label for label in labels if label != correct]
        options.append("none")
        return options
    distractors = ["direct", "absent"]
    for constituent in reference.direct_parts(graph, case["question"]["idea"]):
        distractors.append("via:" + constituent)
    return [item for item in distractors if item != correct]


def _public_order(choices, public_key):
    """Deterministic choice order from PUBLIC content only.

    The order never depends on which choice is declared correct, so changing the
    private target cannot move a choice between slots. This is the boundary the
    §8 leakage rule needs: the public exercise fixes the choices; the private
    target only marks one of them and is never part of the learner's input.
    """
    ordered = sorted(choices, key=canonical)
    seed = int(digest(canonical(public_key))[:8], 16)
    random.Random(seed).shuffle(ordered)
    return ordered


def _render_prompt(bundle, case, choices, view_id):
    labels = view_labels(bundle, view_id)
    by_label = {label: ref for ref, label in labels.items()}
    lines = ["Facts (labels as presented in %s):" % view_id]
    for branch in sorted(bundle["branches"], key=lambda item: item["branch_id"]):
        lines.append("%s %s %s" % (labels[branch["source_node_id"]],
                                   branch["predicate"],
                                   labels[branch["target_node_id"]]))
    if case["op"] == "LIST_PARTS":
        request = ("LIST_PARTS(%s): what does it directly contain?"
                   % case["question"]["idea"])
    elif case["op"] == "FIND_SHARED_PART":
        request = ("FIND_SHARED_PART(%s, %s): which constituent do they share?"
                   % (case["question"]["a"], case["question"]["b"]))
    else:
        request = ("REACHED_VIA(%s, %s): directly inside, reached through "
                   "another constituent, or absent?" % (case["question"]["part"],
                                                        case["question"]["idea"]))
    lines.append(request)
    lines.append("Choose one of the three supplied options.")
    require(len(choices) == 3, "CUBE_CHOICES_NOT_THREE")
    return "\n".join(lines) + "\n"


def compile_lesson(bundle, case, *, assistance="unassisted", view_id="view_context"):
    """One scored task: a public learner view and a separate teacher target."""
    require(assistance in ASSISTANCE_LEVELS, "CUBE_ASSISTANCE_UNKNOWN:" + str(assistance))
    require(case["op"] in CUBE_OPS, "CUBE_OPERATION_UNKNOWN:" + str(case["op"]))
    correct = case["correct"]
    raw_choices = [correct] + _choice_distractors(bundle, case, view_id)
    unique, seen = [], set()
    for item in raw_choices:
        key = canonical(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    choices = unique[:3]
    require(len(choices) == 3, "CUBE_CHOICES_NOT_THREE")
    require(sum(1 for item in choices if item == correct) == 1,
            "CUBE_CORRECT_CHOICE_MISSING")
    public_key = {"family_id": bundle["lesson_family_id"], "view_id": view_id,
                  "op": case["op"], "question": case["question"],
                  "choices": sorted(choices, key=canonical)}
    ordered = _public_order(choices, public_key)
    task_id = digest(canonical({"family_id": bundle["lesson_family_id"],
                                "view_id": view_id, "op": case["op"],
                                "question": case["question"]}))
    bearing = answer_bearing_paths(bundle, case, view_id)
    bearing_leaves = sorted({path for item in bearing for path in item["leaf_paths"]})
    asked = sorted(_asked_nodes(bundle, case, view_id))
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    all_paths = sorted({path for ref in asked for path in node_paths(node_index[ref])})
    # Visibility depends on the task, not on the information: during guided
    # instruction the answer-bearing faces ARE the instruction, so nothing is
    # withheld and the score is labelled assisted; an unassisted test withholds
    # every path that hands the answer over and is scored separately.
    withheld = set(bearing_leaves) if assistance == "unassisted" else set()
    visible, masked = [], []
    for path in all_paths:
        (masked if path in withheld else visible).append(path)
    # The claim itself: with the public exercise fixed, changing the private
    # target leaves the learner's bytes unchanged.
    public_core = {"schema": EXERCISE_SCHEMA, "split": "design_only",
                   "op": case["op"], "graph": graph_record(bundle, view_id),
                   "question": case["question"], "options": ordered,
                   "framings": {"cas": _render_prompt(bundle, case, ordered, view_id),
                                "generic": _render_prompt(bundle, case, ordered, view_id)},
                   "cube": {"task_id": task_id, "view_id": view_id,
                            "assistance_level": assistance,
                            "record_id_basis": "public_projection"}}
    record_id = digest(canonical(public_core))
    record = {**public_core, "record_id": record_id, "correct": correct,
              "reference": case["derivation"]}
    public = adapter.public_records(record, "cas")
    tokens = adapter.build_task(record, "cas")["tokens"]
    learner_view = {
        "family_id": bundle["lesson_family_id"], "task_id": task_id,
        "view_id": view_id, "operation": case["op"],
        "assistance_level": assistance, "question": case["question"],
        "choices": ordered,
        "graph_scope": {"nodes": [{"node_ref": node["node_id"],
                                   "label": view_labels(bundle, view_id)[node["node_id"]],
                                   "revision": node["revision"]}
                                  for node in bundle["cube_nodes"]],
                        "branches": [{"branch_id": branch["branch_id"],
                                      "source": view_labels(bundle, view_id)[branch["source_node_id"]],
                                      "predicate": branch["predicate"],
                                      "target": view_labels(bundle, view_id)[branch["target_node_id"]],
                                      "commonality": branch["commonality"]["kind"]}
                                     for branch in sorted(bundle["branches"],
                                                          key=lambda item: item["branch_id"])]},
        "visible_field_paths": visible, "masked_field_paths": masked,
        "provenance_refs": sorted({ref for node in bundle["cube_nodes"]
                                   for ref in node["provenance_refs"]}),
    }
    require(not (set(learner_view) & set(FORBIDDEN_FIELD_NAMES)),
            "CUBE_LEARNER_VIEW_TARGET_LEAK")
    target = {
        "task_id": task_id, "expected_answer": correct,
        "declared_correct_choice_index": ordered.index(correct),
        "worked_solution": [
            "%s(%s) = %s" % (case["op"], _question_text(case), canonical(correct)),
            "derived by the deterministic reference checker from the stored "
            "contains branches only"],
        "corrective_feedback": ("The direct constituents are exactly the targets of "
                                "the outgoing contains branches: %s."
                                % ", ".join(map(str, correct)) if case["op"] == "LIST_PARTS"
                                else "The checker derives %s from the stored branches."
                                % canonical(correct)),
        "delivered": assistance != "unassisted",
        "delivery_note": ("shown as worked teaching during this lesson"
                          if assistance != "unassisted" else
                          "recorded for scoring only; not delivered to the learner"),
    }
    return {
        "schema": LESSON_SCHEMA, "status": "DESIGN_ONLY_NOT_REGISTERED",
        "task_id": task_id, "family_id": bundle["lesson_family_id"],
        "view_id": view_id, "operation": case["op"],
        "assistance_level": assistance, "case_key": case["case_key"],
        "assisted": assistance != "unassisted",
        "scored_separately_from_assisted_lessons": True,
        "completeness_basis": case["completeness_basis"],
        "asked_nodes": asked, "learner_view": learner_view,
        "learner_view_digest": digest(canonical(learner_view)),
        "teacher_target": target, "teacher_target_digest": digest(canonical(target)),
        "answer_bearing_paths": bearing,
        "masked_field_paths": masked, "visible_field_paths": visible,
        "record": record,
        "encoding": {"public_digest": digest(canonical(public["public"])),
                     "public": public["public"],
                     "encoded_options": public["encoded_options"],
                     "encoded_correct_index": public["encoded_correct_index"],
                     "tokens": len(tokens)},
    }


def _question_text(case):
    return canonical(case["question"])


def compile_lessons(bundle, view_id="view_context"):
    """The handoff set: one guided and one unassisted lesson per operation."""
    chosen = select_cases(bundle, view_id)
    lessons = []
    for op in CUBE_OPS:
        case = chosen[op]
        require(case is not None, "CUBE_NO_CASE_FOR_OPERATION:" + op)
        for assistance in ("guided", "unassisted"):
            lessons.append(compile_lesson(bundle, case, assistance=assistance,
                                          view_id=view_id))
    return lessons


# --------------------------------------------------------------------------
# the seven-stage cycle
# --------------------------------------------------------------------------

def compile_cycle(bundle, case, *, assistance="guided", view_id="view_context"):
    """One complete seven-stage cycle, exactly as a learner would receive it."""
    lesson = compile_lesson(bundle, case, assistance=assistance, view_id=view_id)
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    asked = lesson["asked_nodes"]
    bearing_leaves = {path for item in lesson["answer_bearing_paths"]
                      for path in item["leaf_paths"]}
    stages = []
    for stage in SEVEN_STAGES:
        status, basis = STAGE_EXERCISE_STATUS[stage["stage"]]
        visible, masked, replaced = [], [], []
        selected_all = {}
        for ref in asked:
            node = node_index[ref]
            selected = {}
            if "core" in stage["content_keys"]:
                selected["core"] = node["core"]
            for key in stage["content_keys"]:
                if key in FACE_KEYS:
                    selected[key] = node["faces"][key]
            selected_all[ref] = selected
            for path in node_paths(node):
                if not any(path.startswith("%s.%s" % (ref, key))
                           for key in stage["content_keys"]):
                    continue
                masked_here = bearing_leaves if assistance == "unassisted" else set()
                (masked if path in masked_here else visible).append(path)
        masked_here = bearing_leaves if assistance == "unassisted" else set()
        content = _withhold(selected_all, "", masked_here, replaced)
        delivered = assistance != "unassisted"
        stages.append({
            "stage": stage["stage"], "stage_id": stage["stage_id"],
            "content_keys": list(stage["content_keys"]),
            "assistance_level": assistance,
            "learner_payload": {"content": content,
                                "visible_field_paths": sorted(visible),
                                "masked_field_paths": sorted(masked)},
            "teacher_payload": ({"worked_solution": lesson["teacher_target"]["worked_solution"],
                                 "corrective_feedback":
                                     lesson["teacher_target"]["corrective_feedback"]}
                                if delivered and stage["stage"] in (5, 6) else None),
            "teacher_content_withheld": not delivered,
            "exercise": {"status": status, "basis": basis,
                         "representable_in_current_interface":
                             status == "existing_three_choice_interface"},
            "scored_task": lesson if stage["stage"] == 5 else None,
        })
    cycle = {"schema": CYCLE_SCHEMA, "family_id": bundle["lesson_family_id"],
             "view_id": view_id, "operation": case["op"],
             "assistance_level": assistance, "task_id": lesson["task_id"],
             "stages": stages, "lesson": lesson}
    cycle["counts"] = cycle_counts(cycle)
    cycle["cycle_digest"] = digest(canonical({key: cycle[key] for key in
                                              ("schema", "family_id", "view_id",
                                               "operation", "assistance_level",
                                               "task_id", "counts")}))
    return cycle


def cycle_counts(cycle):
    """Every count the schema asks for, kept separate and never merged.

    A presentation is not an optimizer update, and a paragraph that never
    reaches a learner is not a neural lesson: this draft delivers no neural
    lesson at all, and says so with an explicit zero.
    """
    stages = cycle["stages"]
    delivered = [stage for stage in stages if stage["teacher_payload"]]
    return {
        "stages_delivered": len(stages),
        "assistance_states_recorded": sum(1 for stage in stages
                                          if stage["assistance_level"]),
        "complete_cycles": 1 if len(stages) == len(SEVEN_STAGES) else 0,
        "presentations": len(stages),
        "corrective_examples": len(delivered),
        "optimizer_updates": 0,
        "delivered_neural_lessons": 0,
        "distinct_graph_families": 1,
        "scored_task_tokens": cycle["lesson"]["encoding"]["tokens"],
        "stage_visible_paths": sum(len(stage["learner_payload"]["visible_field_paths"])
                                   for stage in stages),
        "stage_masked_paths": sum(len(stage["learner_payload"]["masked_field_paths"])
                                  for stage in stages),
        "elapsed_seconds": None,
        "elapsed_note": "not measured in this data-only draft",
    }


# --------------------------------------------------------------------------
# the §12 contrast set
# --------------------------------------------------------------------------

def _rename_text(text, mapping):
    for old in sorted(mapping, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(old),
                      mapping[old], text)
    return text


def rename_bundle(bundle, mapping, *, update_mapping=True):
    """Consistent renaming of the presented labels: meaning must be preserved.

    With ``update_mapping=False`` the view labels move while the correspondence
    table keeps the old names, which is the stale-explanation case §13 forbids.
    """
    renamed = json.loads(canonical(bundle))
    for view in renamed["views"]:
        if view["view_id"] != "view_context":
            continue
        view["node_labels"] = {ref: mapping.get(label, label)
                               for ref, label in view["node_labels"].items()}
    for node in renamed["cube_nodes"]:
        node["core"]["label"] = mapping.get(node["core"]["label"], node["core"]["label"])
        node["core"]["identity_statement"] = _rename_text(node["core"]["identity_statement"],
                                                          mapping)
        for key in FACE_KEYS:
            face = node["faces"][key]
            face["human_text"] = _rename_text(face["human_text"], mapping)
            if key == "face_1" and face["availability"] == "populated":
                face["structured"]["canonical_name"] = mapping.get(
                    face["structured"]["canonical_name"],
                    face["structured"]["canonical_name"])
                face["structured"]["definition"] = _rename_text(
                    face["structured"]["definition"], mapping)
            if key == "face_6" and face["availability"] == "populated":
                for step in face["structured"]["steps"]:
                    step["text"] = _rename_text(step["text"], mapping)
    if update_mapping:
        for mapping_record in renamed["mappings"]:
            for row in mapping_record["node_role_rows"]:
                row["contextual"] = mapping.get(row["contextual"], row["contextual"])
    return renamed


def reorder_bundle(bundle):
    """Harmless reordering: identical facts, presented in a different order."""
    reordered = json.loads(canonical(bundle))
    reordered["cube_nodes"] = list(reversed(reordered["cube_nodes"]))
    reordered["branches"] = list(reversed(reordered["branches"]))
    for view in reordered["views"]:
        view["branch_refs"] = list(reversed(view["branch_refs"]))
    for node in reordered["cube_nodes"]:
        face_5 = node["faces"]["face_5"]["structured"]
        face_5["direct_branch_refs"] = list(reversed(face_5["direct_branch_refs"]))
        face_2 = node["faces"]["face_2"]["structured"]
        if face_2.get("fact_refs"):
            face_2["fact_refs"] = list(reversed(face_2["fact_refs"]))
        face_6 = node["faces"]["face_6"]["structured"]
        for step in face_6["steps"]:
            step["uses_branch_refs"] = list(reversed(step["uses_branch_refs"]))
    return reordered


def rewire_bundle(bundle, *, branch_id, new_source, new_target, rebuild=True):
    """Rewiring one contains branch: the representation must change.

    With ``rebuild=False`` the dependent faces keep the old inventory, which is
    the stale-face case §13 forbids (a face must not describe a graph it no
    longer matches).
    """
    rewired = json.loads(canonical(bundle))
    for branch in rewired["branches"]:
        if branch["branch_id"] != branch_id:
            continue
        branch["source_node_id"] = new_source
        branch["target_node_id"] = new_target
        branch["commonality"]["referent"] = new_target
    if rebuild:
        rebuild_derived_content(rewired)
    return rewired


def rebuild_derived_content(bundle):
    """Recompute the faces and mapping rows that depend on the branch table."""
    labels = view_labels(bundle, "view_context")
    outgoing = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    incident = {node["node_id"]: [] for node in bundle["cube_nodes"]}
    for branch in bundle["branches"]:
        outgoing[branch["source_node_id"]].append(branch)
        incident[branch["source_node_id"]].append(branch)
        incident[branch["target_node_id"]].append(branch)
    complete = bool(bundle["context"]["contains_inventory_complete"])
    for node in bundle["cube_nodes"]:
        ref = node["node_id"]
        out = sorted((branch for branch in outgoing[ref]
                      if branch["predicate"] == "contains"),
                     key=lambda item: item["branch_id"])
        face_2 = node["faces"]["face_2"]
        if face_2["availability"] == "populated":
            face_2["structured"]["fact_refs"] = sorted(
                branch["branch_id"] for branch in incident[ref])
        face_5 = node["faces"]["face_5"]
        if face_5["availability"] == "populated":
            face_5["structured"]["direct_branch_refs"] = [b["branch_id"] for b in out]
            face_5["structured"]["completeness"] = "complete" if complete else "partial"
        face_6 = node["faces"]["face_6"]
        if face_6["availability"] == "populated" and face_6["structured"]["steps"]:
            steps = [{"step_id": "step_01",
                      "text": "Identify the %s concept in this authored scene."
                              % labels[ref],
                      "uses_branch_refs": []}]
            for index, branch in enumerate(out):
                steps.append({"step_id": "step_%02d" % (index + 2),
                              "text": "Inspect its direct connection to %s."
                                      % labels[branch["target_node_id"]],
                              "uses_branch_refs": [branch["branch_id"]]})
            if len(steps) == 1:
                steps.append({"step_id": "step_02",
                              "text": ("This complete authored scene declares no "
                                       "direct constituents for this node."),
                              "uses_branch_refs": []})
            face_6["structured"]["steps"] = steps
    for mapping_record in bundle["mappings"]:
        rows = {row["branch_ref"]: row for row in mapping_record["relation_rows"]}
        rebuilt = []
        for branch in sorted(bundle["branches"], key=lambda item: item["branch_id"]):
            row = rows.get(branch["branch_id"], {})
            rebuilt.append({key: row.get(key, "contains") for key in
                            ("branch_ref", "technical_predicate",
                             "contextual_predicate", "analogical_predicate")}
                           | {"branch_ref": branch["branch_id"]})
        mapping_record["relation_rows"] = rebuilt
    return bundle


def contrast_report(bundle, view_id="view_context"):
    """Renaming, reordering, rewiring, and the two rejections §13 requires."""
    original_signature = containment_signature(bundle, view_id)
    original_answers = answer_signature(bundle, view_id)
    labels = view_labels(bundle, view_id)
    renaming = {label: "renamed_%02d" % (index + 1)
                for index, label in enumerate(sorted(set(labels.values())))}
    renamed = rename_bundle(bundle, renaming)
    stale_mapping = rename_bundle(bundle, renaming, update_mapping=False)
    reordered = reorder_bundle(bundle)
    rewired = rewire_bundle(bundle, branch_id="branch_05", new_source="node_003",
                            new_target="node_006")
    stale_faces = rewire_bundle(bundle, branch_id="branch_05", new_source="node_003",
                               new_target="node_006", rebuild=False)
    report = {"view_id": view_id, "original": _contrast_entry(bundle, view_id)}
    entries = {}
    for name, variant, expected_equal in (("renamed", renamed, True),
                                          ("reordered", reordered, True),
                                          ("rewired", rewired, False)):
        code = error_code(lambda variant=variant: validate_bundle(variant))
        require(code is None, "CUBE_CONTRAST_VARIANT_INVALID:%s:%s" % (name, code))
        entry = _contrast_entry(variant, view_id)
        entry["arrangement_preserved"] = (
            entry["containment_signature"] == original_signature["digest"])
        entry["answers_preserved"] = (
            entry["answer_signature"] == original_answers["digest"])
        entry["as_expected"] = (entry["arrangement_preserved"] == expected_equal
                                and entry["answers_preserved"] == expected_equal)
        if not expected_equal:
            entry["changed_answers"] = _changed_answers(bundle, variant, view_id)
        entries[name] = entry
    entries["renamed_stale_mapping_rejected"] = error_code(
        lambda: validate_bundle(stale_mapping))
    entries["rewired_stale_faces_rejected"] = error_code(
        lambda: validate_bundle(stale_faces))
    entries["rewired_stale_faces_face_check"] = face_consistency_code(stale_faces)
    entries["rewired_stale_faces_inventory_check"] = face_inventory_code(stale_faces)
    entries["stale_variant_note"] = (
        "validation fails closed on the first violation found, so the two stale "
        "variants report the first code each one hits; the face check is probed "
        "separately so the face-versus-branch rule is visible on its own")
    report["variants"] = entries
    report["analogy_view_same_arrangement"] = (
        containment_signature(bundle, "view_analogy")["digest"]
        == original_signature["digest"])
    report["analogy_view_same_answers"] = (
        answer_signature(bundle, "view_analogy")["digest"]
        == original_answers["digest"])
    report["original_signature"] = original_signature
    report["original_answers"] = original_answers
    return report


def _contrast_entry(bundle, view_id):
    signature = containment_signature(bundle, view_id)
    answers = answer_signature(bundle, view_id)
    return {"containment_signature": signature["digest"],
            "node_types": signature["node_types"], "edges": signature["edges"],
            "answer_signature": answers["digest"], "cases": answers["cases"],
            "counts": answers["counts"]}


def _changed_answers(before, after, view_id):
    def table(bundle):
        return {item["case_key"]: (item["op"], item["question"], item["correct"])
                for item in answer_cases(bundle, view_id)["cases"]}

    first, second = table(before), table(after)
    changed = []
    for key in sorted(set(first) | set(second)):
        if first.get(key) != second.get(key):
            changed.append({"case_key": key, "before": first.get(key),
                            "after": second.get(key)})
    return changed


# --------------------------------------------------------------------------
# the §9 leakage boundary
# --------------------------------------------------------------------------

def leakage_report(bundle, view_id="view_context"):
    """What reaches the learner, and the proof the private target does not (§8)."""
    lessons = compile_lessons(bundle, view_id)
    entries = []
    for lesson in lessons:
        record = lesson["record"]
        base_view = lesson["learner_view_digest"]
        base_public = lesson["encoding"]["public_digest"]
        alternatives, invariant = [], True
        for choice in lesson["learner_view"]["choices"]:
            if canonical(choice) == canonical(record["correct"]):
                continue
            moved = dict(record)
            moved["correct"] = choice
            public = adapter.public_records(moved, "cas")
            same_view = (digest(canonical(lesson["learner_view"])) == base_view)
            same_public = (digest(canonical(public["public"])) == base_public)
            invariant = invariant and same_view and same_public
            alternatives.append({"declared_correct": choice,
                                 "learner_view_unchanged": same_view,
                                 "encoded_public_unchanged": same_public})
        bearing_leaves = {path for item in lesson["answer_bearing_paths"]
                          for path in item["leaf_paths"]}
        masked = set(lesson["masked_field_paths"])
        if lesson["assistance_level"] == "unassisted":
            masking_ok = bearing_leaves <= masked
        else:
            masking_ok = not masked
        entries.append({
            "task_id": lesson["task_id"], "operation": lesson["operation"],
            "assistance_level": lesson["assistance_level"],
            "learner_view_digest": base_view,
            "encoded_public_digest": base_public,
            "answer_bearing_paths": lesson["answer_bearing_paths"],
            "masked_field_paths": lesson["masked_field_paths"],
            "answer_bearing_paths_masked": masking_ok,
            "learner_input_invariant_under_target_change": invariant,
            "target_alternatives_tested": alternatives,
            "target_keys_absent_from_learner_view":
                not ({key for key in lesson["learner_view"]
                      if key in FORBIDDEN_FIELD_NAMES}),
            "teacher_target_delivered": lesson["teacher_target"]["delivered"],
        })
    return {
        "view_id": view_id, "lessons": entries,
        "bundle_is_never_a_learner_view": {
            "learner_view_requirement": bundle["learner_view_requirement"],
            "authoring_only_fields": ["face_2.structured.fact_refs",
                                      "face_5.structured.direct_branch_refs",
                                      "face_6.structured.steps",
                                      "mappings[].node_role_rows"],
            "note": ("the delivered bundle carries worked teaching content; "
                     "compile_lesson returns a learner_view and a separate "
                     "teacher_target, and validate_bundle rejects a bundle that "
                     "does not demand an explicit visibility profile"),
        },
    }


# --------------------------------------------------------------------------
# interface report and the six design-review questions
# --------------------------------------------------------------------------

def semantic_nulls():
    """§12: empty, unknown, missing, and masked must stay different meanings."""
    return {
        "unknown_face": ("availability='unknown', a non-empty human_text as the "
                         "explanation, and an empty structured object"),
        "not_applicable_face": ("availability='not_applicable', same envelope, a "
                                "different meaning: the face does not apply here"),
        "missing_face_key": "refused: all six face keys must exist (CUBE_FACE_KEYS)",
        "empty_direct_part_list": ("an answer only when the relation inventory is "
                                   "declared complete "
                                   "(CUBE_NEGATIVE_ANSWER_REQUIRES_COMPLETENESS)"),
        "masked": ("a learner-view marker; the authoring face still holds the value "
                   "(%s)" % WITHHELD),
        "no_parts_vs_not_recorded": ("context.contains_inventory_complete decides: "
                                     "complete means 'declares no direct parts', "
                                     "incomplete means 'not recorded'"),
    }


def scope_of_updates():
    """§12: parameter changes, data edits, and presentations are counted apart."""
    return {
        "permitted_parameter_changes": "none: no module was constructed or updated",
        "optimizer_updates": 0,
        "data_edits": ("the contrast variants (renamed, reordered, rewired) are data "
                       "edits made to a copy in memory; they change no parameter and "
                       "no stored record"),
        "presentations": "7 stage deliveries per compiled cycle",
        "delivered_neural_lessons": 0,
        "measured_by": "cycle_counts(), which never merges these counts",
    }


def interface_report():
    """Which stages the current three-choice interface can already express."""
    stages = []
    for stage in SEVEN_STAGES:
        status, basis = STAGE_EXERCISE_STATUS[stage["stage"]]
        stages.append({"stage": stage["stage"], "stage_id": stage["stage_id"],
                       "content_keys": list(stage["content_keys"]),
                       "exercise_status": status, "basis": basis,
                       "representable_in_current_interface":
                           status == "existing_three_choice_interface"})
    representable = [item["stage"] for item in stages
                     if item["representable_in_current_interface"]]
    return {
        "operations_available_now": list(CUBE_OPS),
        "stages": stages,
        "stages_representable_now": representable,
        "stages_requiring_new_task_profile": [item["stage"] for item in stages
                                              if not item["representable_in_current_interface"]],
        "new_profile_detail": ("a new profile must specify output vocabulary, loss, "
                               "and training adapter before execution"),
        "unchanged_by_this_draft": [
            "the zero-update contrast probe", "the accepted models",
            "the retained checkpoints", "the registered curricula and panels",
            "every paid-run decision and the campaign reservation allowance"],
    }


def design_review_report(bundle, view_id="view_context"):
    """The six questions §14 says a design review must be able to answer."""
    labels = view_labels(bundle, view_id)
    node_index = {node["node_id"]: node for node in bundle["cube_nodes"]}
    chosen = select_cases(bundle, view_id)
    cycle = compile_cycle(bundle, chosen["LIST_PARTS"], assistance="guided",
                          view_id=view_id)
    faces = {}
    for ref, node in node_index.items():
        faces[labels[ref]] = {
            "core_label": node["core"]["label"], "kind": node["core"]["kind"],
            "faces": {key: {"role": FACE_ROLES[key],
                            "availability": node["faces"][key]["availability"],
                            "structured_keys": sorted(node["faces"][key]["structured"])}
                      for key in FACE_KEYS}}
    branches = [{"branch_id": branch["branch_id"],
                 "asserts": "%s %s %s" % (labels[branch["source_node_id"]],
                                          branch["predicate"],
                                          labels[branch["target_node_id"]]),
                 "commonality": branch["commonality"]}
                for branch in sorted(bundle["branches"], key=lambda item: item["branch_id"])]
    unassisted = [lesson for lesson in compile_lessons(bundle, view_id)
                  if lesson["assistance_level"] == "unassisted"]
    return {
        "schema": CHECK_SCHEMA, "status": CUBE_STATUS,
        "what_idea_is_stored": {label: item["faces"] for label, item in faces.items()},
        "what_each_face_contributes": FACE_ROLES,
        "what_each_branch_asserts": branches,
        "what_reaches_the_learner": [
            {"task_id": lesson["task_id"], "operation": lesson["operation"],
             "visible_field_paths": lesson["visible_field_paths"],
             "masked_field_paths": lesson["masked_field_paths"],
             "encoded_public_digest": lesson["encoding"]["public_digest"],
             "tokens": lesson["encoding"]["tokens"]}
            for lesson in unassisted],
        "what_the_learner_predicts": [
            {"operation": lesson["operation"],
             "asks": lesson["learner_view"]["question"],
             "choices": lesson["learner_view"]["choices"]}
            for lesson in unassisted],
        "what_feedback_teaches": [
            {"task_id": lesson["task_id"],
             "worked_solution": lesson["teacher_target"]["worked_solution"],
             "corrective_feedback": lesson["teacher_target"]["corrective_feedback"],
             "delivered": lesson["teacher_target"]["delivered"]}
            for lesson in compile_lessons(bundle, view_id)
            if lesson["assistance_level"] == "guided"],
        "complete_cycle_demonstrated": {
            "operation": cycle["operation"], "view_id": cycle["view_id"],
            "counts": cycle["counts"],
            "stages": [{"stage": stage["stage"], "stage_id": stage["stage_id"],
                        "assistance_level": stage["assistance_level"],
                        "visible": stage["learner_payload"]["visible_field_paths"],
                        "masked": stage["learner_payload"]["masked_field_paths"],
                        "teacher_payload_present": bool(stage["teacher_payload"]),
                        "exercise_status": stage["exercise"]["status"]}
                       for stage in cycle["stages"]],
            "cycle_digest": cycle["cycle_digest"]},
        "interface": interface_report(),
        "evidence_state": ("schema valid -> lesson delivered -> practice improved -> "
                           "fresh transfer demonstrated -> accepted integration; "
                           "this draft reaches the first state only"),
    }


def check(bundle=None, bundle_path=None, view_id="view_context"):
    """The full deterministic reading: validation, contrasts, leakage, interface."""
    if bundle is None:
        bundle = load_bundle(bundle_path)
    report = {"schema": CHECK_SCHEMA, "status": CUBE_STATUS,
              "bundle_path": str(bundle_path or pinned_bundle_path()),
              "validation": validate_bundle(bundle),
              "cases": {op: count for op, count in
                        answer_cases(bundle, view_id)["counts"].items()},
              "rejected_cases": answer_cases(bundle, view_id)["rejected"],
              "selected_cases": {op: (None if case is None else
                                      {"question": case["question"],
                                       "answer": case["correct"]})
                                 for op, case in select_cases(bundle, view_id).items()},
              "containment_signature": containment_signature(bundle, view_id),
              "answer_signature": answer_signature(bundle, view_id),
              "contrasts": contrast_report(bundle, view_id),
              "leakage": leakage_report(bundle, view_id),
              "semantic_nulls": semantic_nulls(),
              "scope_of_updates": scope_of_updates(),
              "interface": interface_report(),
              "design_review": design_review_report(bundle, view_id)}
    return report
