"""Pure cube-to-ordered-learner preparation; no neural execution or authority.

The caller configures the canonical cas_meta2 research import root explicitly.
A supplied ordered profile/checkpoint identifies claimed bytes, not observed GPU
state. Public validation does not consult a source, teacher, solver or answer.
Source-grounded target admission is a different, explicit operation.
"""
from __future__ import annotations

from copy import deepcopy
import re

from cas_meta2.codec import validate_public
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder

from .canonical import canonical_json, digest
from .model import ContractError
from .rpa_model import require
from . import rpa_cube_adapter as cube

PREPARED_SCHEMA = "cncm.rpa-learning-prepared/0.1"
LESSON_SCHEMA = "cncm.rpa-learning-lesson/0.1"
RENDERING_SCHEMA = "cncm.cube-contains-node-rel/0.1"
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_TOKENIZER_BYTES = 4 * 1024 * 1024
MAX_INPUT_TOKENS = 1024
IDENTITY_EVIDENCE = "SUPPLIED_METADATA_WITH_PURE_TOKENIZER_AND_FRAME_CHECKS"
CHECKPOINT_SCOPE = "RUN_INITIAL_MODEL_ORIGIN_FIXED_DURING_CANDIDATE_TRAINING"
_LABEL = r"[A-Za-z][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*"
_LABEL_RE = re.compile(_LABEL + r"\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RESERVED = {"none", "direct", "absent", "none_of_the_above"}
_CHOICE_LINE = "Choose one of the three supplied options."
_SHAPES = {"LIST_PARTS": {"idea"}, "FIND_SHARED_PART": {"a", "b"},
           "REACHED_VIA": {"part", "idea"}}
_PREPARED_KEYS = {"schema_version", "public", "encoded_options", "request",
                  "teacher_sidecar", "source_binding", "prepared_id"}
_LESSON_KEYS = {"schema_version", "learner_input", "teacher_sidecar",
                "provenance", "binding"}
_BINDING_KEYS = {"ordered_profile", "model_context", "tokenizer_digest",
                 "public_input_digest", "teacher_sidecar_digest", "tokenization",
                 "identity_evidence", "checkpoint_context_scope",
                 "worker_observed", "projection_bytes_verified",
                 "checkpoint_bytes_verified", "numeric_encoder_calls",
                 "neural_calls", "optimizer_updates", "cached_vectors_verified"}


def _bounded(value, label, maximum=MAX_PACKET_BYTES):
    try:
        return cube._bounded(value, maximum, label)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise ContractError(label + ": " + str(exc)[:200]) from exc


def _same(left, right):
    return canonical_json(left) == canonical_json(right)


def _sha(value, label):
    require(type(value) is str and _SHA.fullmatch(value) is not None, label + " invalid")


def _label(value):
    require(type(value) is str and 0 < len(value) <= 128 and _LABEL_RE.fullmatch(value) is not None
            and value not in _RESERVED, "unsupported or ambiguous graph label")


def _request_text(operation, question):
    require(type(operation) is str and operation in _SHAPES
            and type(question) is dict and set(question) == _SHAPES[operation],
            "request fields invalid")
    for value in question.values():
        _label(value)
    if operation == "LIST_PARTS":
        return "LIST_PARTS(%s): what does it directly contain?" % question["idea"]
    if operation == "FIND_SHARED_PART":
        return ("FIND_SHARED_PART(%s, %s): which constituent do they share?"
                % (question["a"], question["b"]))
    return ("REACHED_VIA(%s, %s): directly inside, reached through another "
            "constituent, or absent?" % (question["part"], question["idea"]))


def _parse_public(public, options):
    """Check the closed rendering grammar, without solving its question."""
    _bounded({"public": public, "encoded_options": options}, "public input")
    validate_public(public)
    problem = public["problem"]
    require(problem.endswith("\n") and "\r" not in problem, "noncanonical problem lines")
    lines = problem[:-1].split("\n")
    require(len(lines) >= 3 and lines[-1] == _CHOICE_LINE, "problem framing invalid")
    nodes, edges = [], []
    in_relations = False
    for line in lines[:-2]:
        node = re.fullmatch(r"node (" + _LABEL + r") kind=idea", line)
        relation = re.fullmatch(r"rel (" + _LABEL + r") --contains--> (" + _LABEL + r")", line)
        if node is not None:
            require(not in_relations, "node after relation")
            _label(node[1])
            nodes.append(node[1])
        elif relation is not None:
            in_relations = True
            _label(relation[1])
            _label(relation[2])
            edges.append((relation[1], relation[2]))
        else:
            raise ContractError("unsupported structural rendering")
    require(0 < len(nodes) <= cube.MAX_CUBES and len(nodes) == len(set(nodes)),
            "duplicate or invalid node inventory")
    require(len(edges) <= 1024 and len(edges) == len(set(edges))
            and all(a in nodes and b in nodes for a, b in edges),
            "duplicate or dangling relation")
    question_line = lines[-2]
    match = re.match(r"(LIST_PARTS|FIND_SHARED_PART|REACHED_VIA)\(([^()]*)\):", question_line)
    require(match is not None, "question rendering invalid")
    operation = match[1]
    arguments = match[2].split(", ")
    keys = ("idea",) if operation == "LIST_PARTS" else (
        ("a", "b") if operation == "FIND_SHARED_PART" else ("part", "idea"))
    require(len(arguments) == len(keys), "question arity invalid")
    question = dict(zip(keys, arguments))
    require(_request_text(operation, question) == question_line
            and all(value in nodes for value in arguments), "question/source label mismatch")
    require(type(options) is list and len(options) == 3, "three ordered options required")
    for option in options:
        if option == "none_of_the_above":
            continue
        if operation == "LIST_PARTS":
            require(type(option) is list and all(type(x) is str and x in nodes for x in option)
                    and option == sorted(set(option)), "invalid list option")
        elif operation == "FIND_SHARED_PART":
            require(type(option) is str and option in nodes + ["none"], "invalid shared option")
        else:
            require(type(option) is str and (
                option in ("direct", "absent")
                or option.startswith("via:") and option[4:] in nodes), "invalid reach option")
    require(len({canonical_json(x) for x in options}) == 3, "duplicate choices")
    for position, row in enumerate(public["observations"]):
        require(type(row["slot"]) is int and row["slot"] == position
                and row["tag"] == str(options[position])
                and _same(row["values"], [0.0] * 8),
                "lossy, marked or reordered observation")
    require(len({row["tag"] for row in public["observations"]}) == 3,
            "ambiguous visible options")
    graph = {"schema": "cas-meta2-graph-teaching-graph/1",
             "nodes": [{"identifier": label, "kind": "idea", "fields": []} for label in nodes],
             "relations": [{"kind": "contains", "source": a, "target": b,
                            "content": ["constituent", b]} for a, b in edges]}
    return operation, question, graph


def prepare_public_lesson(document, *, operation, question, assistance="unassisted"):
    """Prepare public text before tokenizer fitting; privately retain teacher evidence."""
    cube._revalidate_document(document)
    wire = document.to_dict()
    bundle, view = wire["catalog"]["bundle"], wire["view_id"]
    labels = cube.cube_node.view_labels(bundle, view)
    for label in labels.values():
        _label(label)
    request_text = _request_text(operation, question)
    require(all(value in labels.values() for value in question.values()), "question label unresolved")
    legacy = cube.compile_atlas_lesson(document, bundle=bundle,
        expected_bundle_digest=wire["source_receipt"]["canonical_bundle_digest"],
        operation=operation, question=question, assistance=assistance)
    graph = cube.cube_node.containment_graph(bundle, view)
    # Independent declared inventory prevents a faulty graph helper or render
    # method from silently omitting, reversing, adding or changing structure.
    expected_nodes = [{"identifier": labels[ref], "kind": "idea", "fields": []}
                      for ref in sorted(labels)]
    expected_edges = [{"kind": "contains", "source": labels[row["source_node_id"]],
                       "target": labels[row["target_node_id"]],
                       "content": ["constituent", labels[row["target_node_id"]]]}
                      for row in sorted(bundle["branches"], key=lambda row: row["branch_id"])]
    expected_graph = {"schema": "cas-meta2-graph-teaching-graph/1",
                      "nodes": expected_nodes, "relations": expected_edges}
    require(_same(graph.to_record(), expected_graph), "graph helper differs from declared source")
    rendered = graph.render()
    expected_lines = ["node %s kind=idea" % row["identifier"] for row in expected_nodes]
    expected_lines += ["rel %s --contains--> %s" % (row["source"], row["target"])
                       for row in expected_edges]
    require(rendered == "\n".join(expected_lines) + "\n", "lossy or altered graph rendering")
    public = deepcopy(legacy["learner_input"]["public"])
    public["problem"] = rendered + request_text + "\n" + _CHOICE_LINE + "\n"
    options = deepcopy(legacy["learner_input"]["encoded_options"])
    parsed_op, parsed_question, parsed_graph = _parse_public(public, options)
    require(parsed_op == operation and _same(parsed_question, question)
            and _same(parsed_graph, expected_graph), "public rendering changed source semantics")
    teacher = legacy["teacher_sidecar"]
    # Recheck the receiver join and teacher consequence from the source, rather
    # than accepting an arbitrary compiler sidecar or an offered-index alias.
    index = teacher["encoded_correct_index"]
    source_answer = cube.cube_profile.derived_answer(
        bundle, {"op": operation, "question": deepcopy(question)}, view)
    require(type(index) is int and 0 <= index < 3
            and _same(teacher["expected_answer"], source_answer)
            and _same(options[index], source_answer)
            and teacher["record_id"] == legacy["learner_input"]["record_id"]
            and teacher["source_bundle_digest"] == wire["source_receipt"]["canonical_bundle_digest"]
            and teacher["operation"] == operation and _same(teacher["question"], question)
            and teacher["assistance_level"] == assistance,
            "teacher receipt/source/option binding mismatch")
    prepared = {"schema_version": PREPARED_SCHEMA, "public": public, "encoded_options": options,
        "request": {"operation": operation, "question": deepcopy(question),
                    "assistance": assistance, "view_id": view},
        "teacher_sidecar": {key: deepcopy(teacher[key]) for key in (
            "expected_answer", "encoded_correct_index", "reference_branch_ids",
            "reference_paths", "witness_basis", "answer_status")},
        "source_binding": {
            "source_file_sha256": wire["source_receipt"]["source_file_sha256"],
            "source_bundle_digest": wire["source_receipt"]["canonical_bundle_digest"],
            "source_receipt_digest": digest(wire["source_receipt"]),
            "source_namespace": wire["source_receipt"]["source_namespace"],
            "source_context_id": bundle["context"]["context_id"],
            "base_current_state_id": wire["atlas"]["current_state_id"],
            "legacy_input_id": legacy["learner_input"]["record_id"],
            "rendering_schema": RENDERING_SCHEMA,
            "source_authorship_authenticated": False, "world_truth_established": False}}
    prepared["prepared_id"] = "rpa-prepared-" + digest({
        key: value for key, value in prepared.items() if key != "teacher_sidecar"})
    _bounded(prepared, "prepared lesson")
    return prepared


def _identity(tokenizer, ordered_profile, model_context):
    require(type(tokenizer) is LosslessPublicTokenizer
            and set(vars(tokenizer)) == {"vocabulary", "fitted_public_sha256",
                                         "fitted_examples", "max_length"},
            "exact immutable LosslessPublicTokenizer required")
    wire = tokenizer.to_dict()
    _bounded(wire, "tokenizer", MAX_TOKENIZER_BYTES)
    checked = LosslessPublicTokenizer.from_dict(wire)
    require(checked.max_length == MAX_INPUT_TOKENS, "unsupported learner token ceiling")
    _bounded(ordered_profile, "ordered profile")
    require(type(ordered_profile) is dict
            and set(ordered_profile) == ordered_encoder._IDENTITY_FIELDS,
            "ordered profile fields invalid")
    expected = ordered_encoder.profile_identity(checked,
        d_model=ordered_profile["d_model"], seed=ordered_profile["permutation_seed"],
        projection_sha256=ordered_profile["projection_sha256"])
    require(_same(ordered_profile, expected), "ordered profile differs from tokenizer or contract")
    ordered_encoder.validate_checkpoint_identity({"encoder_identity": ordered_profile}, expected)
    _bounded(model_context, "model context")
    require(type(model_context) is dict and set(model_context) == {"model_id", "checkpoint_sha256"},
            "model context fields invalid")
    require(type(model_context["model_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", model_context["model_id"]) is not None,
            "model identity invalid")
    _sha(model_context["checkpoint_sha256"], "run-initial checkpoint SHA-256")
    return checked, deepcopy(expected), deepcopy(model_context)


def _public_id(public, options, ordered_profile, model_context):
    return "rpa-learning-input-" + digest({"schema_version": LESSON_SCHEMA,
        "public": public, "encoded_options": options,
        "ordered_profile": ordered_profile, "model_context": model_context})


def _tokenization(public, tokenizer):
    tokenizer.check_round_trip(public)
    encoded = tokenizer.encode_public(public)
    frames = ordered_encoder.compile_frames(public, tokenizer)
    frame_rows = [{"kind": row.kind, "ordinal": row.ordinal, "token_ids": list(row.token_ids)}
                  for row in frames]
    return {"encoded_token_count": len(encoded["ids"]), "ordered_frame_count": len(frames),
            "structural_frame_count": sum(row.kind in ("node", "rel") for row in frames),
            "text_round_trip": True, "framing_digest": digest(frame_rows)}


def validate_prediction_packet(packet, *, tokenizer, ordered_profile, model_context):
    """Validate/copy public input only. No teacher, source reconstruction or solver."""
    _bounded(packet, "prediction packet")
    require(type(packet) is dict and set(packet) == {"record_id", "public", "encoded_options"},
            "closed prediction packet required")
    checked, profile, context = _identity(tokenizer, ordered_profile, model_context)
    _parse_public(packet["public"], packet["encoded_options"])
    _tokenization(packet["public"], checked)
    require(type(packet["record_id"]) is str and packet["record_id"] == _public_id(
        packet["public"], packet["encoded_options"], profile, context), "stale public input identity")
    return deepcopy(packet)


def _bind_verified(prepared, *, tokenizer, ordered_profile, model_context):
    checked, profile, context = _identity(tokenizer, ordered_profile, model_context)
    public, options = deepcopy(prepared["public"]), deepcopy(prepared["encoded_options"])
    packet = {"record_id": _public_id(public, options, profile, context),
              "public": public, "encoded_options": options}
    validate_prediction_packet(packet, tokenizer=checked, ordered_profile=profile, model_context=context)
    teacher = {"record_id": packet["record_id"], **deepcopy(prepared["teacher_sidecar"])}
    binding = {"ordered_profile": profile, "model_context": context,
        "tokenizer_digest": checked.digest, "public_input_digest": digest(packet),
        "teacher_sidecar_digest": digest(teacher), "tokenization": _tokenization(public, checked),
        "identity_evidence": IDENTITY_EVIDENCE, "checkpoint_context_scope": CHECKPOINT_SCOPE,
        "worker_observed": False, "projection_bytes_verified": False,
        "checkpoint_bytes_verified": False, "numeric_encoder_calls": 0,
        "neural_calls": 0, "optimizer_updates": 0, "cached_vectors_verified": False}
    return {"schema_version": LESSON_SCHEMA, "learner_input": packet,
            "teacher_sidecar": teacher,
            "provenance": {key: deepcopy(prepared[key]) for key in (
                "request", "source_binding", "prepared_id")}, "binding": binding}


def _reprepare(prepared, document):
    _bounded(prepared, "prepared lesson")
    require(type(prepared) is dict and set(prepared) == _PREPARED_KEYS
            and prepared["schema_version"] == PREPARED_SCHEMA, "prepared lesson fields invalid")
    request = prepared["request"]
    require(type(request) is dict and set(request) == {"operation", "question", "assistance", "view_id"},
            "prepared request fields invalid")
    expected = prepare_public_lesson(document, operation=request["operation"],
                                    question=request["question"], assistance=request["assistance"])
    require(_same(prepared, expected), "prepared lesson differs from checked source reconstruction")
    return expected


def bind_prepared_lesson(prepared, *, document, tokenizer, ordered_profile, model_context):
    """Bind checked source text to supplied identities; never claim worker observation."""
    expected = _reprepare(prepared, document)
    result = _bind_verified(expected, tokenizer=tokenizer, ordered_profile=ordered_profile,
                            model_context=model_context)
    _bounded(result, "bound lesson")
    return result


def prediction_packet(lesson, *, tokenizer, ordered_profile, model_context):
    """Extract the closed packet; private teacher mutations cannot change this output.

    This checks public consistency, not source authenticity or teacher correctness.
    Use check_source_target separately before admitting training supervision.
    """
    _bounded(lesson, "bound lesson")
    require(type(lesson) is dict and set(lesson) == _LESSON_KEYS
            and lesson["schema_version"] == LESSON_SCHEMA, "bound lesson fields invalid")
    binding = lesson["binding"]
    require(type(binding) is dict and set(binding) == _BINDING_KEYS, "binding fields invalid")
    packet = validate_prediction_packet(lesson["learner_input"], tokenizer=tokenizer,
        ordered_profile=ordered_profile, model_context=model_context)
    checked, profile, context = _identity(tokenizer, ordered_profile, model_context)
    expected = {"ordered_profile": profile, "model_context": context,
        "tokenizer_digest": checked.digest, "public_input_digest": digest(packet),
        "tokenization": _tokenization(packet["public"], checked),
        "identity_evidence": IDENTITY_EVIDENCE, "checkpoint_context_scope": CHECKPOINT_SCOPE,
        "worker_observed": False, "projection_bytes_verified": False,
        "checkpoint_bytes_verified": False, "numeric_encoder_calls": 0,
        "neural_calls": 0, "optimizer_updates": 0, "cached_vectors_verified": False}
    _sha(binding["teacher_sidecar_digest"], "private sidecar digest")
    require(_same({key: value for key, value in binding.items() if key != "teacher_sidecar_digest"},
                  expected), "public binding changed")
    return packet


def _source_checked_lesson(lesson, *, document, tokenizer, ordered_profile, model_context):
    prediction_packet(lesson, tokenizer=tokenizer, ordered_profile=ordered_profile,
                      model_context=model_context)
    provenance = lesson["provenance"]
    require(type(provenance) is dict and set(provenance) == {"request", "source_binding", "prepared_id"},
            "provenance fields invalid")
    request = provenance["request"]
    require(type(request) is dict and set(request) == {"operation", "question", "assistance", "view_id"},
            "source request fields invalid")
    prepared = prepare_public_lesson(document, operation=request["operation"],
                                    question=request["question"], assistance=request["assistance"])
    expected = _bind_verified(prepared, tokenizer=tokenizer, ordered_profile=ordered_profile,
                              model_context=model_context)
    require(_same(lesson, expected), "lesson differs from source-grounded teacher reconstruction")
    return expected


def check_source_target(lesson, *, document, tokenizer, ordered_profile, model_context):
    """Recompute source teacher agreement; mathematical graph facts only."""
    checked = _source_checked_lesson(lesson, document=document, tokenizer=tokenizer,
                                    ordered_profile=ordered_profile, model_context=model_context)
    return deepcopy(checked["teacher_sidecar"])


def training_record(lesson, *, document, tokenizer, ordered_profile, model_context):
    """Source-check a record for trainer.run_training, not legacy public_records.

    Initialize GraphLearner separately from learner_input plus the private index.
    Reapplying the old codec would reshuffle choices under the new record_id.
    """
    checked = _source_checked_lesson(lesson, document=document, tokenizer=tokenizer,
                                    ordered_profile=ordered_profile, model_context=model_context)
    packet, teacher = checked["learner_input"], checked["teacher_sidecar"]
    operation, question, graph = _parse_public(packet["public"], packet["encoded_options"])
    return {"schema": "cas-meta2-graph-teaching-exercise/1", "split": "rpa_learning_candidate",
            "record_id": packet["record_id"], "op": operation, "graph": graph,
            "question": {"op": operation, **question}, "options": deepcopy(packet["encoded_options"]),
            "correct": deepcopy(teacher["expected_answer"]),
            "framings": {arm: packet["public"]["problem"] for arm in ("cas", "generic")},
            "reference": deepcopy(teacher)}
