"""Public-only development transfer packets from six retained topology IDs.

No legacy task/answer constructor is imported. Public graph selection and
question authorship are separated from later, sealed-prediction scoring.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from itertools import combinations, permutations, product
import json
from math import factorial
from pathlib import Path

from . import answers, binding, course, input_frames, slots, source, tokenization

SCHEMA = "cas.typed-development-public-packets/0.1"
PILOT = "research/CAS_META_2_COMPOSITION/"
SUPPLY_PATH = PILOT + "records/learning_panel_001/supply.json"
EXCLUSIONS_PATH = PILOT + "records/complementary_teaching_001/preparation_20260916/historical_exclusions.json"
COURSE_PATH = "records/typed_course_001/checks_002/public_course.json"
SUPPLY_SHA = "6290e13a4f40e0b61da6ede65c55b90939380f1ef79bcfe6a5b98269dde8d193"
EXCLUSIONS_SHA = "e00cc95d59b17fd36a8c478a0497257e5355e071348d4f4c833d9d3a470a3aa8"
COURSE_SHA = "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"
TOKENIZER_PATH = "records/typed_interface_001/checks_002/training_tokenizer.json"
TOKENIZER_SHA = "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c"
TOKENIZER_DIGEST = "5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798"
REFERENCE_FILES = {
    PILOT + "cas_meta2/graph_teaching/final_panel.py": "cae5428a6d2e91237b9a6d48775b5ec6a9b0082cca51506dcf1a57daacc24e31",
    PILOT + "tools/check_structural_supply_20260916.py": "a78d24c5469d95937a1d49ec6827cef213eabbb0b4811defe3ae370bd75852e0",
}
POLICY = {
    "split": "development", "supports": "NONE_EQUAL_FOR_BOTH_STUDY_ARMS",
    "bank": "ALL_64_RETAINED_TRAINING_WORLDS_PLUS_ONE_NONBANK_DEVELOPMENT_FOCUS",
    "root": "LEXICAL_FIRST_AUTHORED_NODE_WITH_ZERO_INDEGREE",
    "questions": "PARTS_ROOT_AND_REACH_FROM_ROOT_TO_EVERY_OTHER_PUBLIC_NODE",
    "reach_rule": "first_direct_constituent_lexical_v1",
    "labels": "Dev<family-index>Node<sorted-structural-node-index>; no legacy labels or target menus",
    "selection": "EXACT_SIX_RETAINED_PUBLIC_DEVELOPMENT_TOPOLOGY_IDS; NO_ANSWER_CLASS_QUERY_SELECTION",
    "comparison": "Parts/reach development structure-and-size transfer only; not all-eight-kind transfer",
    "legacy_parity": "Topology identities only; not legacy18-question/text/difficulty/answer parity",
    "novelty": "Excluded under pinned historical inventory; not authenticated absolute historical nonexposure",
    "target_boundary": "NO_MAIN_TARGETS_IN_FACTORY; SCORE_ONLY_AFTER_DURABLE_PUBLIC_PREDICTION_SEALS",
    "tokenizer": "UNCHANGED_RETAINED_TRAINING_FIT_UTF8_BYTE_FALLBACK_32768_NO_TRUNCATION",
    "semantics": "Complete supplied DAG snapshot; authored declarations; no world truth or temporal-process claim",
}
require, canonical, digest = source.require, source.canonical, source.digest


def _read(root, relative, expected):
    path = Path(root).resolve() / relative
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(Path(root).resolve()), "TYPED_DEV_INPUT_PATH")
    raw = path.read_bytes()
    require(len(raw) <= 8 * 1024 ** 2 and sha256(raw).hexdigest() == expected, "TYPED_DEV_INPUT_PIN:" + relative)
    return raw, {"path": relative, "bytes": len(raw), "sha256": expected}


def profile():
    files = []
    for name in ("development.py", "source.py", "answers.py", "course.py", "input_frames.py", "slots.py", "binding.py", "tokenization.py"):
        path = Path(__file__).with_name(name)
        raw = path.read_bytes()
        files.append({"path": "cas_meta2/typed_teaching/" + name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema": "cas.typed-development-profile/0.1", "files": files, "policy": POLICY,
            "course_profile": course.profile(), "source_authority": "PINNED_FILES_NOT_EXTERNAL_AUTHENTICITY"}
    return {**deepcopy(body), "profile_digest": digest(body)}


def topology_key(nodes, edges):
    """Exact small directed graph identity; same retained audit convention."""
    nodes, edges = tuple(nodes), tuple(tuple(e) for e in edges)
    require(3 <= len(nodes) <= 10 and len(set(nodes)) == len(nodes), "TYPED_DEV_NODE_BOUND")
    require(len(set(edges)) == len(edges) and all(len(e) == 2 and all(v in nodes for v in e) for e in edges), "TYPED_DEV_EDGES")
    groups = defaultdict(list)
    for node in nodes:
        groups[(sum(b == node for a, b in edges), sum(a == node for a, b in edges))].append(node)
    groups = [tuple(groups[key]) for key in sorted(groups)]
    work = 1
    for group in groups: work *= factorial(len(group))
    require(work <= 500000, "TYPED_DEV_TOPOLOGY_WORK_BOUND")
    best = None
    for orders in product(*(permutations(group) for group in groups)):
        indexes = {node: index for index, node in enumerate(node for group in orders for node in group)}
        value = tuple(sorted((indexes[a], indexes[b]) for a, b in edges))
        if best is None or value < best: best = value
    return digest({"nodes": len(nodes), "edges": best})


def _stats(shape):
    nodes = sorted(set(shape) | {v for values in shape.values() for v in values})
    depths = []
    for whole in shape:
        depth, frontier, seen = 0, [whole], {whole}
        while frontier:
            depth += 1
            frontier = [part for node in frontier for part in shape.get(node, ()) if part not in seen]
            seen.update(frontier)
        depths.append(depth)
    edge_count = sum(len(v) for v in shape.values())
    return {"nodes": len(nodes), "relations": edge_count, "wholes": len(shape), "max_depth": max(depths),
        "max_direct_parts": max(map(len, shape.values())),
        "has_nested_whole": any(v in shape for values in shape.values() for v in values),
        "has_shared_part": len({v for values in shape.values() for v in values}) < edge_count}


@lru_cache(maxsize=1)
def _enumerated_shapes():
    """Independent topology-only reproduction of the pinned enumerator loops.

    No final module import, question, label assignment, task, option or answer.
    The exact topology key replaces the source's preliminary dedup key; the
    retained public supply below verifies the resulting92 identities and stats.
    """
    found = {}
    for wholes in (3, 4):
        for counts in product((1, 2, 3), repeat=wholes):
            for nested_slots in range(3):
                for indexes in combinations(range(wholes), nested_slots):
                    for nested_sizes in product((1, 2), repeat=nested_slots):
                        for shared in (False, True):
                            shape = {"w%d" % i: tuple("p%d_%d" % (i, j) for j in range(count)) for i, count in enumerate(counts)}
                            for slot, index in enumerate(indexes):
                                shape[shape["w%d" % index][0]] = tuple("n%d_%d" % (index, j) for j in range(nested_sizes[slot]))
                            if shared:
                                keys = sorted(shape)
                                shape[keys[1]] += (shape[keys[0]][0],)
                            stats = _stats(shape)
                            if not (8 <= stats["nodes"] <= 10 and 6 <= stats["relations"] <= 9
                                    and 2 <= stats["max_direct_parts"] <= 3 and stats["has_nested_whole"] and stats["max_depth"] <= 3):
                                continue
                            nodes = sorted(set(shape) | {v for values in shape.values() for v in values})
                            key = topology_key(nodes, [(a, b) for a, values in shape.items() for b in values])
                            found.setdefault(key, shape)
    require(len(found) == 92, "TYPED_DEV_ENUMERATOR_IDENTITY_COUNT")
    return tuple((key, tuple((a, tuple(b)) for a, b in shape.items())) for key, shape in sorted(found.items()))


def _selected(root, expected_supply_sha256, expected_exclusions_sha256):
    require(expected_supply_sha256 == SUPPLY_SHA and expected_exclusions_sha256 == EXCLUSIONS_SHA, "TYPED_DEV_CANONICAL_INPUT_IDENTITY")
    supply_raw, supply_pin = _read(root, SUPPLY_PATH, expected_supply_sha256)
    exclusions_raw, exclusions_pin = _read(root, EXCLUSIONS_PATH, expected_exclusions_sha256)
    supply, exclusions = json.loads(supply_raw), json.loads(exclusions_raw)
    pins = [supply_pin, exclusions_pin]
    for path, sha in REFERENCE_FILES.items():
        _, pin = _read(root, path, sha)
        pins.append(pin)
    require(exclusions["complete"] is True and exclusions["failures"] == [], "TYPED_DEV_EXCLUSIONS_INCOMPLETE")
    banned = set(exclusions["excluded_topologies"])
    selected = sorted(row["topology"] for row in supply["rows"] if row["current_allocation"] == "development")
    require(len(selected) == len(set(selected)) == 6 and not banned.intersection(selected), "TYPED_DEV_SELECTED_TOPOLOGIES")
    all_shapes = {key: dict(shape) for key, shape in _enumerated_shapes()}
    require(set(all_shapes) == {r["topology"] for r in supply["rows"]}, "TYPED_DEV_SUPPLY_IDENTITY")
    for row in supply["rows"]:
        require(_stats(all_shapes[row["topology"]]) == row["stats"], "TYPED_DEV_SUPPLY_STATS")
    for row in supply["rows"]:
        if row["topology"] in selected:
            require(row["historically_excluded"] is False and row["candidate_pool"] is True,
                    "TYPED_DEV_PUBLIC_ALLOCATION")
    return [(key, all_shapes[key]) for key in selected], pins


def _development_world(shape, index):
    structural = sorted(set(shape) | {v for values in shape.values() for v in values})
    labels = {node: "Dev%dNode%d" % (index + 1, at) for at, node in enumerate(structural)}
    incoming = {b for values in shape.values() for b in values}
    roots = sorted(node for node in structural if node not in incoming)
    require(roots, "TYPED_DEV_DAG_ROOT")
    root = roots[0]
    primary = [labels[root], *[labels[n] for n in structural if n != root][:2]]
    declarations = {"domain": "development_structure", "kind": "authored directed containment example",
        "function": "supplies a complete declared containment snapshot for a development question",
        "setting": "development transfer without answer-bearing supports"}
    edges = [{"source": labels[a], "target": labels[b]} for a, values in shape.items() for b in values]
    # _facts/_world admit source syntax only; no fake training-family wrapper.
    world = source._world(source._facts(list(labels.values()), edges, declarations, primary))
    return world, labels[root]


def _packet(public, *, kind, arguments):
    query = answers.compile_query(public, kind=kind, arguments=arguments,
        rule=POLICY["reach_rule"] if kind == "reach" else None)
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
        "source_world_id": public["focus_world_id"], "query": query, "cue": None,
        "instruction": course.REQUESTS[kind], "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": []}
    packet = {"source": deepcopy(public), "record": {**body, "record_id": "typed-input-" + digest(body)}}
    return course.validate_model_packet(packet)


def build_development(*, root, expected_supply_sha256=SUPPLY_SHA, expected_exclusions_sha256=EXCLUSIONS_SHA, tokenizer=None):
    before = profile()
    selected, pins = _selected(root, expected_supply_sha256, expected_exclusions_sha256)
    raw, pin = _read(root, COURSE_PATH, COURSE_SHA)
    pins.append(pin)
    retained = json.loads(raw)
    bank = source.validate_bank(retained["bank"])
    require(len(bank["worlds"]) == 64, "TYPED_DEV_FULL_TRAINING_BANK")
    if tokenizer is None:
        raw, pin = _read(root, TOKENIZER_PATH, TOKENIZER_SHA)
        pins.append(pin)
        tokenizer = tokenization.FrameTokenizer.from_dict(json.loads(raw))
    require(type(tokenizer) is tokenization.FrameTokenizer and tokenizer.digest == TOKENIZER_DIGEST
            and tokenizer.max_tokens == 32768, "TYPED_DEV_FROZEN_TOKENIZER")
    packets, families, admission = [], [], []
    for index, (key, shape) in enumerate(selected):
        world, root_label = _development_world(shape, index)
        require(world["world_id"] not in bank["bank"]["world_ids"], "TYPED_DEV_FOCUS_ALREADY_IN_BANK")
        public = {"focus_world_id": world["world_id"], "worlds": sorted([*deepcopy(bank["worlds"]), world], key=lambda w: w["world_id"]),
                  "bank": deepcopy(bank["bank"])}
        source.validate_public(public)
        root_ref = next(n["ref"] for n in world["nodes"] if n["label"] == root_label)
        requests = [("parts", {"whole": root_ref})] + [("reach", {"whole": root_ref, "part": n["ref"]})
            for n in world["nodes"] if n["ref"] != root_ref]
        ids = []
        for kind, arguments in requests:
            packet = _packet(public, kind=kind, arguments=arguments)
            frame = input_frames.compile_packet(packet)
            sequence = tokenizer.encode_frame(frame)  # exact32768 bound; overflow is an error, never truncation
            require(tokenizer.decode_text(sequence["ids"][1:-1]) == frame["text"], "TYPED_DEV_TEXT_ROUNDTRIP")
            plan = slots.compile_slots(packet)
            require(slots.compile_slots(packet) == plan, "TYPED_DEV_CACHE_PARITY")
            record_id = packet["record"]["record_id"]
            ids.append(record_id)
            packets.append(packet)
            admission.append({"record_id": record_id, "kind": kind, "family_index": index,
                "topology": key, "packet_sha256": digest(packet), "source_digest": source.public_digest(public),
                "frame_digest": frame["frame_digest"], "sequence_digest": sequence["sequence_digest"],
                "token_count": len(sequence["ids"]), "slot_plan_digest": plan["plan_digest"], "slots": len(plan["slots"])})
        families.append({"index": index, "split": "development", "topology": key, "shape": {a: list(b) for a, b in shape.items()},
            "stats": _stats(shape), "world_id": world["world_id"], "root_ref": root_ref,
            "declared_root_label": root_label, "record_ids": ids, "declarations_authority": "NEW_CALLER_AUTHORED_DEVELOPMENT_FACTS_NOT_WORLD_TRUTH"})
    require(len(packets) == sum(row["stats"]["nodes"] for row in families)
            and len({p["record"]["record_id"] for p in packets}) == len(packets), "TYPED_DEV_PACKET_COUNTS")
    require(profile() == before, "TYPED_DEV_SOURCE_CHANGED")
    body = {"schema": SCHEMA, "status": "PUBLIC_DEVELOPMENT_PREPARED_NOT_MODEL_EVALUATED", "policy": deepcopy(POLICY),
        "profile": before, "inputs": pins, "tokenizer_digest": tokenizer.digest,
        "training_bank_digest": bank["bank"]["bank_digest"], "families": families,
        "packets": packets, "admission": admission, "counts": {"families": 6, "parts": 6,
            "reach": len(packets) - 6, "packets": len(packets), "bank_worlds": 64, "worlds_per_packet": 65},
        "max_token_count": max(r["token_count"] for r in admission), "main_targets_constructed": 0,
        "final_questions_constructed": 0, "neural_calls": 0, "provider_calls": 0}
    return {**body, "development_digest": digest(body)}


def validate_development(document, *, root, tokenizer=None):
    expected = build_development(root=root, tokenizer=tokenizer)
    require(canonical(document) == canonical(expected), "TYPED_DEV_RECONSTRUCTION")
    return deepcopy(expected)


def compact_development(document):
    """Factor repeated public worlds without changing one expanded packet byte."""
    require(type(document) is dict and document.get("schema") == SCHEMA, "TYPED_DEV_DOCUMENT")
    require(document.get("development_digest") == digest({k: v for k, v in document.items()
        if k != "development_digest"}), "TYPED_DEV_DOCUMENT_DIGEST")
    worlds, records, bank = {}, [], None
    for packet in document["packets"]:
        checked = course.validate_model_packet(packet)
        public = checked["source"]
        if bank is None: bank = deepcopy(public["bank"])
        require(bank == public["bank"], "TYPED_DEV_BANK_CHANGED")
        ids = []
        for world in public["worlds"]:
            key = world["world_id"]
            require(key not in worlds or worlds[key] == world, "TYPED_DEV_WORLD_COLLISION")
            worlds[key] = deepcopy(world); ids.append(key)
        records.append({"focus_world_id": public["focus_world_id"], "world_ids": ids,
            "record": deepcopy(checked["record"]), "packet_digest": digest(checked)})
    body = {"schema": "cas.typed-development-compact/0.1", "bank": bank,
        "worlds": [worlds[key] for key in sorted(worlds)], "records": records,
        "document_metadata": {k: deepcopy(v) for k, v in document.items() if k != "packets"}}
    require(len(canonical(body).encode()) < 4 * 1024 ** 2, "TYPED_DEV_COMPACT_BOUND")
    compact = {**body, "compact_digest": digest(body)}
    require(canonical(expand_development(compact)) == canonical(document), "TYPED_DEV_COMPACT_ROUNDTRIP")
    return compact


def expand_development(compact):
    """Expand pinned public material only; no selection, targets or tokenizer fit."""
    require(type(compact) is dict and set(compact) == {"schema", "bank", "worlds", "records",
        "document_metadata", "compact_digest"}, "TYPED_DEV_COMPACT_FIELDS")
    require(compact["schema"] == "cas.typed-development-compact/0.1"
        and len(canonical(compact).encode()) <= 4 * 1024 ** 2, "TYPED_DEV_COMPACT_BOUND")
    require(compact["compact_digest"] == digest({k: v for k, v in compact.items()
        if k != "compact_digest"}), "TYPED_DEV_COMPACT_DIGEST")
    worlds = {w["world_id"]: w for w in compact["worlds"]}
    require(len(worlds) == len(compact["worlds"]) == 70
        and len(compact["records"]) == 59, "TYPED_DEV_COMPACT_COUNTS")
    packets = []
    for row in compact["records"]:
        require(type(row) is dict and set(row) == {"focus_world_id", "world_ids", "record", "packet_digest"},
            "TYPED_DEV_COMPACT_RECORD")
        require(len(row["world_ids"]) == len(set(row["world_ids"])) == 65
            and set(row["world_ids"]) <= set(worlds), "TYPED_DEV_COMPACT_WORLD_JOIN")
        public = {"focus_world_id": row["focus_world_id"], "worlds": [worlds[key] for key in row["world_ids"]],
            "bank": compact["bank"]}
        packet = course.validate_model_packet({"source": public, "record": row["record"]})
        require(digest(packet) == row["packet_digest"] and packet["record"]["supports"] == [], "TYPED_DEV_COMPACT_PACKET")
        packets.append(packet)
    document = {**deepcopy(compact["document_metadata"]), "packets": packets}
    require(document.get("schema") == SCHEMA and document.get("development_digest") == digest({
        k: v for k, v in document.items() if k != "development_digest"}), "TYPED_DEV_EXPANDED_DIGEST")
    require(len({p["record"]["record_id"] for p in packets}) == 59, "TYPED_DEV_EXPANDED_UNIQUE")
    return document
