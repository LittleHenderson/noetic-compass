"""Complete typed course construction with a separate private target release.

Preparation authors public questions without calling the semantic teacher.
Worked supports are then enriched from OTHER source families. Main-query
targets can be released only from a checked, durably saved completed course.
This is pure curriculum construction, not a learner or an execution permit.
"""
from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

from . import answers, source, course_plan, focal

PREPARED_SCHEMA = "cas.typed-teaching-prepared-course/0.1"
COURSE_SCHEMA = "cas.typed-teaching-course/0.1"
PACKET_SCHEMA = "cas.typed-teaching-model-packet/0.1"
TARGETS_SCHEMA = "cas.typed-teaching-course-targets/0.1"
MAX_COURSE_BYTES = 32 * 1024 * 1024
PACKAGE = Path(__file__).resolve().parents[1]
CANONICAL = source.canonical
DIGEST = source.digest
REQUIRE = source.require
REQUESTS = {
    "role_set": "Classify only the focal controlled-language excerpt. Return every applicable role from the fixed six-role catalog, with its ambiguity status. These forms are explicit instructional cues, not unrestricted natural-language understanding.",
    "definition": "Return the declared whole and that focused world's own kind and function declaration references. Equal text declared in another world is a different reference.",
    "context": "Return that focused world's own setting declaration reference and its declared participant set. Participants use the stated presentation convention. This question does not establish additional interaction facts.",
    "analogy": "Choose any world in the entire supplied bank with a distinct declared domain and an isomorphic complete directed contains graph. Compare all nodes and edges, without a required root match. Return no match only if none qualifies.",
    "correspondence": "Map every focus node bijectively to the specified target world, preserving exactly all directed contains edges. Every valid map is accepted. Return NO_MATCH only when none exists.",
    "parts": "Return exactly the nodes directly contained by the specified whole in this complete supplied snapshot.",
    "edge_account": "Return every declared directed contains pair in the focus world, canonically serialized. This is a static structural account; no temporal process order has been supplied.",
    "reach": "Classify the specified part as DIRECT, ABSENT or VIA. Direct edges take precedence. Apply the exact public rule ID to select the intermediate node; the two reach rule IDs have different meanings.",
}
ROLE_CATALOG = {
    "1": "declared whole kind and function",
    "2": "declared setting and participants",
    "3": "cross-domain containment-pattern comparison",
    "4": "explicit node correspondence",
    "5": "constituents and structural relations",
    "6": "complete static structural account; temporal process requires additional evidence",
}
KIND_FACE = {"definition": 1, "context": 2, "analogy": 3, "correspondence": 4,
             "parts": 5, "reach": 5, "edge_account": 6}
SEMANTIC_POLICY = {
    "answer_construction": "PUBLIC_TYPED_UNIVERSES_NEVER_LEGACY_CORRECT_PLUS_NEGATIVES",
    "comparison_target_selection": "TRAINING_ONLY_AUTHORED_SAME_ARCHETYPE_DIFFERENT_DOMAIN_CYCLIC_PARTNER",
    "selection_scope": "CURRICULUM_GRAPH_PAIR_SELECTION_NOT_ANSWER_BIJECTION_FILTERING",
    "recognition": "CONTROLLED_LANGUAGE_PUBLIC_CONTENT_CHECKED_WITHOUT_HIDDEN_EVENT_FACE",
    "recognition_face5_change": "DIRECT_INVENTORY_FOCAL_CONTENT_REPLACES_LEGACY_INVENTORY_OR_REACH_COMMENTARY",
    "question_distribution": "AUTHORED_TEACHING_ITEMS_NOT_TARGET_BALANCED_OR_UNBIASED_SAMPLING",
    "face5_question_selection": "LEGACY_DIRECT_INVENTORY_OR_REACH_INTENT_FROM_PUBLIC_GRAPH_ONLY",
    "face2_boundary": "DECLARED_SETTING_AND_PARTICIPANTS_NO_NEW_INTERACTION_SKILL_CLAIM",
    "face6_boundary": "STATIC_FULL_EDGE_ACCOUNT_NOT_TEMPORAL_PROCESS",
    "support_example_selection": "LEXICAL_FIRST_VALID_WORKED_EXAMPLE_NOT_UNIQUENESS_CLAIM",
    "legacy_parity": "LOGICAL_EVENTS_GROUPS_AND_SUPPORT_SELECTORS_NOT_OLD_TEXT_OPTIONS_OR_DIFFICULTY",
}
READINESS = {
    "status": "PURE_FULL_COURSE_NOT_NUMERICALLY_ADMITTED",
    "learner_decoder_implemented": False, "tokenizer_bound": False,
    "numeric_scoped_encoder_verified": False, "paired_initialization_verified": False,
    "actual_compute_matching_measured": False, "study_frozen": False,
    "neural_calls": 0, "optimizer_updates": 0,
}


def profile():
    names = ("typed_teaching/__init__.py", "typed_teaching/source.py", "typed_teaching/answers.py",
             "typed_teaching/focal.py", "typed_teaching/checker.py",
             "typed_teaching/course_plan.py", "typed_teaching/course.py",
             "graph_teaching/face_corpus.py", *course_plan.LEGACY_FILES)
    rows = []
    for name in sorted(set(names)):
        path = PACKAGE / name
        raw = path.read_bytes()
        rows.append({"path": "cas_meta2/" + name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema": "cas.typed-teaching-course-source-profile/0.1", "files": rows,
            "plan_source_profile": course_plan.source_profile(),
            "data_files": [], "identity_scope": "ON_DISK_SOURCE_NOT_LOADED_WORKER_ATTESTATION"}
    return {**body, "profile_digest": DIGEST(body)}


def _public(bank, focus):
    return {"focus_world_id": focus, "worlds": bank["worlds"], "bank": bank["bank"]}


def _world(public, focus):
    return next(w for w in public["worlds"] if w["world_id"] == focus)


def _node(world, label):
    return next(n["ref"] for n in world["nodes"] if n["label"] == label)


def _partners(families):
    result = {}
    for family in families:
        pool = [f for f in families if f["archetype"] == family["archetype"]]
        at = next(i for i, f in enumerate(pool) if f["family_id"] == family["family_id"])
        candidates = pool[at + 1:] + pool[:at + 1]
        partner = next(f for f in candidates if f["domain"] != family["domain"])
        result[family["family_id"]] = partner["family_id"]
    return result


def _face5_request(world):
    """Public item selection only; no output candidates or target labels."""
    whole = world["declared_whole"]
    edges = [(e["source"], e["target"]) for e in world["contains"]]
    direct = {b for a, b in edges if a == whole}
    seen, queue = set(), deque([whole])
    while queue:
        current = queue.popleft()
        for a, b in edges:
            if a == current and b not in seen:
                seen.add(b); queue.append(b)
    indirect = sorted(seen - direct - {whole})
    foreign = {b for _, b in edges} - seen - {whole}
    if indirect and not foreign:
        return "reach", "bfs_immediate_predecessor_lexical_v1", {"whole": whole, "part": indirect[0]}
    return "parts", None, {"whole": whole}


def _request(public, intent, worlds, partners):
    focus = worlds[intent["family_id"]]
    world = _world(public, focus)
    task, face = intent["profile"], intent["face"]
    cue, args, rule = None, {}, None
    if task == "ROLE_FROM_CONTENT":
        kind = "role_set"
        args = {"focal_excerpt": focal.render_excerpt(public, template=face, focus_world_id=focus,
                    comparison_world_id=worlds[partners[intent["family_id"]]] if face in (3, 4) else None)}
    elif task == "LIST_PARTS":
        kind, args = "parts", {"whole": world["declared_whole"]}
    elif task == "REACHED_VIA":
        kind, rule = "reach", "first_direct_constituent_lexical_v1"
        args = {"whole": world["declared_whole"], "part": _node(world, intent["part_label"])}
    else:
        REQUIRE(task == "FACE_APPLY", "TYPED_COURSE_REQUEST_PROFILE")
        cue = "CUBE_FACE_%d" % face
        kind = {1: "definition", 2: "context", 3: "analogy", 4: "correspondence",
                5: "parts", 6: "edge_account"}[face]
        if face == 4:
            REQUIRE(intent.get("training_partner_family_id") == partners[intent["family_id"]],
                    "TYPED_COURSE_PARTNER_INTENT_MISMATCH")
            args = {"target_world_id": worlds[partners[intent["family_id"]]]}
        if face == 5:
            kind, rule, args = _face5_request(world)
    query = answers.compile_query(public, kind=kind, rule=rule, arguments=args, focus_world_id=focus)
    return {"query": query, "cue": cue, "instruction": REQUESTS[kind]}


@lru_cache(maxsize=9)
def _prepare(seed, condition, source_profile_digest):
    current = profile()
    REQUIRE(current["profile_digest"] == source_profile_digest, "TYPED_COURSE_SOURCE_CHANGED")
    plan = course_plan.compile_plan(seed, condition)
    families = source.training_families()
    bank = source.freeze_bank(families)
    worlds = {family["family_id"]: source.compile_source(family, bank=bank)["public"]["focus_world_id"]
              for family in families}
    partners = _partners(families)
    registry, presentations, intents = {}, [], {}
    for occurrence in plan["occurrences"]:
        intent = occurrence["intent"]
        selector = CANONICAL(intent)
        if selector not in intents:
            focus = worlds[intent["family_id"]]
            public = _public(bank, focus)
            request = _request(public, intent, worlds, partners)
            supports = [_request(public, support, worlds, partners) for support in intent["support_intents"]]
            REQUIRE(all(s["query"]["focus_world_id"] != focus for s in supports), "TYPED_COURSE_SELF_SUPPORT")
            body = {"source_world_id": focus, **request, "supports": supports}
            request_id = "typed-request-" + DIGEST(body)
            intents[selector] = request_id
            registry[request_id] = {"request_id": request_id, **body}
        presentations.append({"occurrence_id": occurrence["occurrence_id"],
                              "request_id": intents[selector]})
    body = {"schema": PREPARED_SCHEMA, "source_profile": current, "plan": plan, "bank": bank,
            "registry": [registry[key] for key in sorted(registry)], "presentations": presentations,
            "semantic_policy": deepcopy(SEMANTIC_POLICY),
            "teacher_boundary": "QUESTIONS_AND_SUPPORT_REQUESTS_AUTHORED_WITHOUT_SEMANTIC_TEACHER"}
    REQUIRE(profile() == current, "TYPED_COURSE_SOURCE_CHANGED")
    return {**body, "prepared_digest": DIGEST(body)}


def prepare_course(seed, condition):
    """No import or invocation of the private answer checker."""
    return deepcopy(_prepare(seed, condition, profile()["profile_digest"]))


def validate_prepared(prepared):
    REQUIRE(type(prepared) is dict and "plan" in prepared, "TYPED_PREPARED_FIELDS")
    expected = prepare_course(prepared["plan"]["source_seed"], prepared["plan"]["condition"])
    REQUIRE(CANONICAL(prepared) == CANONICAL(expected), "TYPED_PREPARED_RECONSTRUCTION")
    return expected


@lru_cache(maxsize=4096)
def _worked_target(public_json, query_json, source_profile_digest):
    # Called only for a worked support, never by prepare_course or inference.
    from . import checker
    public, query = json.loads(public_json), json.loads(query_json)
    target = checker.derive_target(public, query)
    return deepcopy(target["admissible_answers"][0])


@lru_cache(maxsize=9)
def _complete(seed, condition, source_profile_digest):
    prepared = _prepare(seed, condition, source_profile_digest)
    records, joins = {}, {}
    publics = {item["source_world_id"]: _public(prepared["bank"], item["source_world_id"])
               for item in prepared["registry"]}
    public_json = {focus: CANONICAL(value) for focus, value in publics.items()}
    for item in prepared["registry"]:
        public = publics[item["source_world_id"]]
        supports = []
        for support in item["supports"]:
            REQUIRE(support["query"]["focus_world_id"] != item["query"]["focus_world_id"],
                    "TYPED_COURSE_SELF_SUPPORT")
            answer = _worked_target(public_json[item["source_world_id"]], CANONICAL(support["query"]), source_profile_digest)
            supports.append({**deepcopy(support), "worked_answer": deepcopy(answer),
                             "selection_rule": SEMANTIC_POLICY["support_example_selection"]})
        body = {"schema": PACKET_SCHEMA, "source_digest": source.public_digest(public),
                "source_world_id": item["source_world_id"], "query": item["query"],
                "cue": item["cue"], "instruction": item["instruction"],
                "role_catalog": deepcopy(ROLE_CATALOG), "supports": supports}
        record_id = "typed-input-" + DIGEST(body)
        records[record_id] = {"record_id": record_id, **body}
        joins[item["request_id"]] = record_id
    presentations = [{"occurrence_id": item["occurrence_id"], "record_id": joins[item["request_id"]]}
                     for item in prepared["presentations"]]
    by_id = {p["occurrence_id"]: p["record_id"] for p in presentations}
    plan = prepared["plan"]
    counts = {**plan["counts"], "unique_public_packets": len(records),
              "presented_kinds": dict(Counter(records[p["record_id"]]["query"]["kind"] for p in presentations)),
              "source_bank_bytes": len(CANONICAL(prepared["bank"]).encode()),
              "materialized_input_bytes_max": max(len(CANONICAL(
                  {"source": _public(prepared["bank"], row["source_world_id"]), "record": row}).encode())
                                                  for row in records.values()),
              "numeric_input_tokens": None, "neural_decoder_work": None}
    body = {"schema": COURSE_SCHEMA, "source_profile": prepared["source_profile"],
            "source_seed": seed, "condition": condition, "bank": prepared["bank"],
            "plan": plan, "prepared_digest": prepared["prepared_digest"],
            "registry": [records[key] for key in sorted(records)], "presentations": presentations,
            "batches": [{**deepcopy(batch), "record_ids": [by_id[key] for key in batch["occurrence_ids"]]}
                        for batch in plan["batches"]],
            "counts": counts, "semantic_policy": deepcopy(SEMANTIC_POLICY), "readiness": deepcopy(READINESS),
            "teacher_boundary": "WORKED_SUPPORTS_BOUND_MAIN_QUERY_TARGETS_NOT_RELEASED"}
    REQUIRE(profile()["profile_digest"] == source_profile_digest, "TYPED_COURSE_SOURCE_CHANGED")
    REQUIRE(len(CANONICAL(body).encode()) <= MAX_COURSE_BYTES, "TYPED_COURSE_BYTE_BOUND")
    return {**body, "course_digest": DIGEST(body)}


def compile_course(seed, condition):
    """Enrich other-family worked supports; main targets remain separate."""
    return deepcopy(_complete(seed, condition, profile()["profile_digest"]))


def validate_course(course):
    REQUIRE(type(course) is dict and len(CANONICAL(course).encode()) <= MAX_COURSE_BYTES,
            "TYPED_COURSE_FIELDS_OR_BOUND")
    expected = compile_course(course.get("source_seed"), course.get("condition"))
    REQUIRE(CANONICAL(course) == CANONICAL(expected), "TYPED_COURSE_RECONSTRUCTION")
    return expected


def model_packet(course, record_id):
    """Materialize a closed public view, without private occurrence/face lineage."""
    REQUIRE(type(record_id) is str, "TYPED_COURSE_RECORD_ID")
    row = next((row for row in course["registry"] if row["record_id"] == record_id), None)
    REQUIRE(row is not None, "TYPED_COURSE_RECORD_UNKNOWN")
    result = {"source": deepcopy(_public(course["bank"], row["source_world_id"])), "record": deepcopy(row)}
    validate_model_packet(result)
    return result


def validate_model_packet(packet):
    """Syntax/binding only. No semantic teacher or graph solving at inference."""
    REQUIRE(type(packet) is dict and set(packet) == {"source", "record"}, "TYPED_MODEL_PACKET_FIELDS")
    public = source.validate_public(packet["source"])
    row = packet["record"]
    REQUIRE(type(row) is dict and set(row) == {"record_id", "schema", "source_digest", "source_world_id",
        "query", "cue", "instruction", "role_catalog", "supports"}, "TYPED_MODEL_RECORD_FIELDS")
    body = {k: v for k, v in row.items() if k != "record_id"}
    REQUIRE(row["schema"] == PACKET_SCHEMA and row["record_id"] == "typed-input-" + DIGEST(body),
            "TYPED_MODEL_RECORD_ID")
    REQUIRE(row["source_digest"] == source.public_digest(public)
            and row["source_world_id"] == public["focus_world_id"] == row["query"]["focus_world_id"],
            "TYPED_MODEL_SOURCE_BINDING")
    answers.validate_query(public, row["query"])
    REQUIRE(row["role_catalog"] == ROLE_CATALOG and row["instruction"] == REQUESTS[row["query"]["kind"]],
            "TYPED_MODEL_REQUEST_CONTRACT")
    REQUIRE(row["cue"] is None or type(row["cue"]) is str and row["cue"] in {"CUBE_FACE_%d" % i for i in range(1, 7)},
            "TYPED_MODEL_CUE")
    if row["query"]["kind"] == "role_set":
        REQUIRE(row["cue"] is None, "TYPED_MODEL_HIDDEN_ROLE_CUE")
    elif row["cue"] is not None:
        REQUIRE(row["cue"] == "CUBE_FACE_%d" % KIND_FACE[row["query"]["kind"]],
                "TYPED_MODEL_CUE_KIND_MISMATCH")
    REQUIRE(type(row["supports"]) is list and len(row["supports"]) in (0, 3), "TYPED_MODEL_SUPPORT_COUNT")
    for support in row["supports"]:
        REQUIRE(type(support) is dict and set(support) == {"query", "cue", "instruction", "worked_answer",
                                                          "selection_rule"}, "TYPED_MODEL_SUPPORT_FIELDS")
        answers.validate_query(public, support["query"])
        answers.validate_answer(public, support["query"], support["worked_answer"])
        REQUIRE(type(support["cue"]) is str and support["cue"] in {"CUBE_FACE_%d" % i for i in range(1, 7)}
                and support["query"]["kind"] != "role_set", "TYPED_MODEL_SUPPORT_CUE")
        REQUIRE(support["cue"] == "CUBE_FACE_%d" % KIND_FACE[support["query"]["kind"]],
                "TYPED_MODEL_SUPPORT_CUE_KIND_MISMATCH")
        REQUIRE(support["query"]["focus_world_id"] != row["query"]["focus_world_id"],
                "TYPED_MODEL_SELF_SUPPORT")
        REQUIRE(support["instruction"] == REQUESTS[support["query"]["kind"]]
                and support["selection_rule"] == SEMANTIC_POLICY["support_example_selection"],
                "TYPED_MODEL_SUPPORT_CONTRACT")
    return deepcopy(packet)


def seal_course(course, path):
    """Save teaching/audit bundle before main-target release.

    The bundle includes private lineage; only model_packet is learner-visible.
    Main answer keys are absent, while legitimate worked supports are present.
    """
    checked = validate_course(course)
    target = Path(path)
    raw = (CANONICAL(checked) + "\n").encode()
    with target.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    REQUIRE(target.read_bytes() == raw, "TYPED_COURSE_SEAL_READBACK")
    return {"schema": "cas.typed-teaching-course-seal/0.1", "path": str(target.resolve()),
            "bytes": len(raw), "sha256": sha256(raw).hexdigest(), "course_digest": course["course_digest"]}


def derive_targets_from_seal(path, *, expected_sha256):
    """Private phase: verify durable public bytes, then derive main targets."""
    from . import checker
    raw = Path(path).read_bytes()
    REQUIRE(len(raw) <= MAX_COURSE_BYTES and sha256(raw).hexdigest() == expected_sha256,
            "TYPED_COURSE_SEAL_IDENTITY")
    course = json.loads(raw)
    REQUIRE(raw == (CANONICAL(course) + "\n").encode(), "TYPED_COURSE_SEAL_CANONICAL")
    validate_course(course)
    targets = {}
    for row in course["registry"]:
        public = _public(course["bank"], row["source_world_id"])
        targets[row["record_id"]] = checker.derive_target(public, row["query"])
    REQUIRE(Path(path).read_bytes() == raw, "TYPED_COURSE_SEAL_CHANGED_DURING_TARGETS")
    body = {"schema": TARGETS_SCHEMA, "course_file_sha256": expected_sha256,
            "course_digest": course["course_digest"], "targets": targets,
            "presentations": deepcopy(course["presentations"]), "neural_calls": 0,
            "boundary": "Private corrections after durable public-course seal; no model prediction, optimizer or learning result."}
    return {**body, "targets_digest": DIGEST(body)}
