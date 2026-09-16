"""Closed public source worlds without query options or teacher answers.

Every supplied fact is published equally. Kind/function/setting are declarations,
not independently established world truth. Participants are an explicit legacy
presentation convention over the first three primary labels. Containment order
is recorded for custody and serialization; it never implies temporal process
order. The full bank is frozen before a focus is selected.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

SCHEMA = "cas.typed-teaching-source/0.1"
BANK_SCHEMA = "cas.typed-teaching-public-bank/0.1"
MAX_NODES, MAX_BANK_WORLDS, MAX_WORLD_UNION = 10, 64, 65
MAX_BYTES = 4 * 1024 * 1024
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = PACKAGE_ROOT / "graph_teaching/face_corpus.py"
FAMILY_FIELDS = {"family_id", "domain", "archetype", "rendering", "kind", "labels",
                 "branches", "split", "setting", "function"}
PARTICIPANTS_BASIS = "PRIMARY_AUTHORED_LABELS_FIRST_THREE"
ORDER_BASIS = "SERIALIZATION_ONLY_NOT_TEMPORAL"
INVENTORY_SCOPE = "EXACT_SUPPLIED_CONTAINS_SNAPSHOT_NOT_WIDER_WORLD"
SOURCE_STATUS = {
    "authorship_authenticated": False,
    "world_truth_established": False,
    "declaration_basis": "CALLER_SUPPLIED_SOURCE",
    "field_origins": {
        "domain": "AUTHORED_DOMAIN_DECLARATION",
        "kind": "AUTHORED_KIND_DECLARATION",
        "function": "DECLARED_PHRASE_OR_RENDERED_AUTHORED_DOMAIN_TEMPLATE",
        "setting": "AUTHORED_DOMAIN_DECLARATION",
        "primary_labels": "FIRST_THREE_CALLER_SUPPLIED_LABELS",
        "participants": "PRESENTATION_DERIVED_PRIMARY_THREE_LABELS",
        "contains": "SUPPLIED_GRAPH_DECLARATIONS_MAY_BE_TEMPLATE_DERIVED",
        "branch_order": "PRESENTATION_CONVENTIONS_ONLY",
    },
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _closed(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)


def _bounded(value, *, allow_tuples=False):
    count = 0
    active = set()
    def walk(item, depth):
        nonlocal count
        count += 1
        require(count <= 100000 and depth <= 20, "TYPED_SOURCE_TREE_BOUND")
        kinds = (dict, list, tuple, str, int, bool, type(None)) if allow_tuples else (dict, list, str, int, bool, type(None))
        require(type(item) in kinds, "TYPED_SOURCE_JSON_TYPE")
        if type(item) in (dict, list, tuple):
            require(id(item) not in active, "TYPED_SOURCE_CYCLE")
            active.add(id(item))
            if type(item) is dict:
                require(all(type(key) is str for key in item), "TYPED_SOURCE_JSON_KEY")
                children = item.values()
            else:
                children = item
            for child in children:
                walk(child, depth + 1)
            active.remove(id(item))
        elif type(item) is str:
            require(len(item) <= 4096, "TYPED_SOURCE_TEXT_BOUND")
    walk(value, 0)
    require(len(canonical(value).encode()) <= MAX_BYTES, "TYPED_SOURCE_BYTE_BOUND")


def _text(value, maximum=256):
    require(type(value) is str and 0 < len(value) <= maximum
            and value == value.strip() and all(ord(c) >= 32 for c in value), "TYPED_SOURCE_TEXT")
    return value


def source_profile():
    files = []
    for name in ("typed_teaching/__init__.py", "typed_teaching/source.py", "graph_teaching/face_corpus.py"):
        path = PACKAGE_ROOT / name
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(PACKAGE_ROOT), "TYPED_SOURCE_CODE_SCOPE")
        raw = path.read_bytes()
        require(len(raw) <= 1024 * 1024, "TYPED_SOURCE_CODE_BOUND")
        files.append({"path": "cas_meta2/" + name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema": "cas.typed-teaching-source-profile/0.1", "files": files,
            "data_files": [], "pin_role": "ON_DISK_GENERATOR_AND_CONTRACT_BYTES_NOT_LOADED_RUNTIME_ATTESTATION",
            "final_target_files_read": False}
    return {**body, "profile_digest": digest(body)}


def training_families(*, expected_source_profile_digest=None):
    """Construct only the first 64 families directly from pinned source literals.

    No corpus/task/evaluation module is imported and no all-split constructor is
    called. Nontraining domain label/extra literals are never evaluated.
    """
    profile = source_profile()
    if expected_source_profile_digest is not None:
        require(type(expected_source_profile_digest) is str
                and expected_source_profile_digest == profile["profile_digest"], "TYPED_SOURCE_PROFILE_CHANGED")
    raw = CORPUS_PATH.read_bytes()
    constants = {}
    for node in ast.parse(raw, str(CORPUS_PATH)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            require(name not in constants, "TYPED_SOURCE_DUPLICATE_CORPUS_CONSTANT")
            constants[name] = node.value
    literal = lambda name: ast.literal_eval(constants[name])
    count, domains = literal("TRAINING_FAMILIES"), literal("DOMAIN_ORDER")
    require(type(count) is int and count == 64 and count % 16 == 0, "TYPED_SOURCE_TRAINING_BOUND")
    order, archetypes = literal("ARCHETYPE_ORDER"), literal("ARCHETYPES")
    renderings, split = literal("RENDERINGS"), literal("TRAINING")
    require(renderings == 4 and type(renderings) is int and split == "training", "TYPED_SOURCE_TRAINING_CONTRACT")
    def domain_literal(name, domain):
        node = constants[name]
        require(isinstance(node, ast.Dict), "TYPED_SOURCE_CORPUS_DOMAIN_TABLE")
        matches = [value for key, value in zip(node.keys, node.values)
                   if ast.literal_eval(key) == domain]
        require(len(matches) == 1, "TYPED_SOURCE_CORPUS_DOMAIN_KEY")
        return ast.literal_eval(matches[0])
    result = []
    for domain in domains[:count // 16]:
        authored = domain_literal("_AUTHORED", domain)
        extras = domain_literal("_EXTRAS", domain)
        function = domain_literal("_FUNCTION", domain)
        setting = domain_literal("_SETTING", domain)
        require(len(authored) == len(extras) == 16, "TYPED_SOURCE_DOMAIN_COUNT")
        for position, (primary, kind) in enumerate(authored):
            archetype = order[position % len(order)]
            labels = tuple(primary) if archetype == "chain2" else tuple(primary) + (extras[position],)
            family = {"family_id": "family:%s:%02d" % (domain, position),
                "domain": domain, "archetype": archetype, "rendering": len(result) % renderings,
                "kind": kind, "labels": labels,
                "branches": tuple({"source": labels[a], "target": labels[b]} for a, b in archetypes[archetype]),
                "split": split, "setting": setting,
                "function": function % {"whole": labels[0], "child": labels[1]}}
            _material(family)
            result.append(family)
    require(len(result) == count and source_profile() == profile, "TYPED_SOURCE_CHANGED_DURING_TRAINING_READ")
    return tuple(deepcopy(result))


def _material(family):
    _bounded(family, allow_tuples=True)
    _closed(family, FAMILY_FIELDS, "TYPED_SOURCE_FAMILY_FIELDS")
    for key in ("family_id", "domain", "archetype", "kind", "setting", "function"):
        _text(family[key], 512 if key == "function" else 256)
    require(family["split"] == "training" and type(family["split"]) is str, "TYPED_SOURCE_TRAINING_ONLY")
    require(type(family["rendering"]) is int and 0 <= family["rendering"] < 4, "TYPED_SOURCE_RENDERING")
    labels = family["labels"]
    require(type(labels) in (list, tuple), "TYPED_SOURCE_NODE_BOUND")
    return _facts(labels, family["branches"], family, list(labels[:3]))


def _facts(labels, edges, declarations, primary):
    """Shared structural syntax checks; no family IDs, source files or answers."""
    require(type(labels) in (list, tuple) and 3 <= len(labels) <= MAX_NODES, "TYPED_SOURCE_NODE_BOUND")
    require(all(type(label) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*", label)
                and len(label) <= 80 for label in labels) and len(set(labels)) == len(labels), "TYPED_SOURCE_NODE_LABELS")
    require(type(primary) is list and len(primary) == 3 and len(set(primary)) == 3
            and all(label in labels for label in primary), "TYPED_SOURCE_PRIMARY_LABELS")
    for key in ("domain", "kind", "setting", "function"):
        _text(declarations[key], 512 if key == "function" else 256)
    require(type(edges) in (list, tuple) and 0 < len(edges) <= MAX_NODES * (MAX_NODES - 1), "TYPED_SOURCE_EDGE_BOUND")
    normalized = []
    for edge in edges:
        _closed(edge, {"source", "target"}, "TYPED_SOURCE_EDGE_FIELDS")
        require(type(edge["source"]) is str and type(edge["target"]) is str
                and edge["source"] in labels and edge["target"] in labels
                and edge["source"] != edge["target"], "TYPED_SOURCE_EDGE_ENDPOINT")
        normalized.append((edge["source"], edge["target"]))
    require(len(set(normalized)) == len(normalized), "TYPED_SOURCE_DUPLICATE_EDGE")
    # Bounded schema validation only. This neither computes nor stores answers.
    graph = {label: [] for label in labels}
    for source, target in normalized:
        graph[source].append(target)
    def visit(node, active, finished):
        require(node not in active, "TYPED_SOURCE_CONTAINS_CYCLE")
        if node in finished:
            return
        for child in graph[node]:
            visit(child, active | {node}, finished)
        finished.add(node)
    finished = set()
    for node in labels:
        visit(node, set(), finished)
    return {"labels": sorted(labels), "whole": primary[0], "primary_labels": list(primary),
            "domain": declarations["domain"], "kind": declarations["kind"], "function": declarations["function"],
            "setting": declarations["setting"], "edges": [list(edge) for edge in normalized]}


def _world(material):
    world_id = "world-" + digest({"schema": SCHEMA, "material": material, "source_status": SOURCE_STATUS})
    node_refs = {label: world_id + "/n%d" % index for index, label in enumerate(material["labels"])}
    ordered_edges = sorted(tuple(edge) for edge in material["edges"])
    edge_refs = {edge: world_id + "/e%d" % index for index, edge in enumerate(ordered_edges)}
    primary = [node_refs[label] for label in material["primary_labels"]]
    return {"world_id": world_id,
        "nodes": [{"ref": node_refs[label], "label": label, "kind": "idea"} for label in material["labels"]],
        "declared_whole": node_refs[material["whole"]],
        "declarations": {key: material[key] for key in ("domain", "kind", "function", "setting")}
                        | {"primary_labels": primary, "participants": list(primary), "participants_basis": PARTICIPANTS_BASIS},
        "contains": [{"ref": edge_refs[tuple(edge)], "source": node_refs[edge[0]], "target": node_refs[edge[1]]}
                     for edge in material["edges"]],
        "contains_inventory_complete": True, "inventory_scope": INVENTORY_SCOPE,
        "branch_order": {"source_order": [edge_refs[tuple(edge)] for edge in material["edges"]],
                         "canonical_account_order": [edge_refs[edge] for edge in ordered_edges],
                         "process_order": None, "order_basis": ORDER_BASIS},
        "source_status": deepcopy(SOURCE_STATUS)}


def _validate_world(world):
    require(type(world) is dict, "TYPED_SOURCE_WORLD")
    nodes, declarations = world.get("nodes"), world.get("declarations")
    require(type(nodes) is list and 3 <= len(nodes) <= MAX_NODES and type(declarations) is dict, "TYPED_SOURCE_WORLD_FIELDS")
    labels = {}
    for node in nodes:
        _closed(node, {"ref", "label", "kind"}, "TYPED_SOURCE_NODE_FIELDS")
        require(type(node["ref"]) is str and node["ref"] not in labels, "TYPED_SOURCE_NODE_REF")
        labels[node["ref"]] = node["label"]
    primary = declarations.get("primary_labels")
    require(type(primary) is list and len(primary) == 3 and all(type(ref) is str and ref in labels for ref in primary)
            and len(set(primary)) == 3, "TYPED_SOURCE_PRIMARY_REFS")
    require(world.get("declared_whole") == primary[0], "TYPED_SOURCE_WHOLE_REF")
    contains = world.get("contains")
    require(type(contains) is list and len(contains) <= 90, "TYPED_SOURCE_CONTAINS_FIELDS")
    edges = []
    for edge in contains:
        _closed(edge, {"ref", "source", "target"}, "TYPED_SOURCE_SCOPED_EDGE_FIELDS")
        require(type(edge["source"]) is str and type(edge["target"]) is str
                and edge["source"] in labels and edge["target"] in labels, "TYPED_SOURCE_FOREIGN_ENDPOINT")
        edges.append({"source": labels[edge["source"]], "target": labels[edge["target"]]})
    expected = _world(_facts(list(labels.values()), edges, declarations, [labels[ref] for ref in primary]))
    require(canonical(world) == canonical(expected), "TYPED_SOURCE_WORLD_RECONSTRUCTION")
    return deepcopy(expected)


def _bank_record(worlds):
    body = {"world_ids": sorted(world["world_id"] for world in worlds),
            "complete_within_supplied_bank": True,
            "coverage": "ALL_AND_ONLY_CALLER_SUPPLIED_MEMBERS",
            "selection": "NO_COMPILER_TARGET_FILTERING_OR_FOCUS_DEPENDENCE"}
    return {**body, "bank_digest": digest(body)}


def freeze_bank(families):
    """Freeze all supplied members without a focus, query, or target argument."""
    require(type(families) in (list, tuple) and 0 < len(families) <= MAX_BANK_WORLDS, "TYPED_SOURCE_BANK_BOUND")
    worlds = [_world(_material(family)) for family in families]
    require(len({world["world_id"] for world in worlds}) == len(worlds), "TYPED_SOURCE_BANK_DUPLICATE_WORLD")
    worlds.sort(key=lambda world: world["world_id"])
    body = {"schema": BANK_SCHEMA, "worlds": worlds, "bank": _bank_record(worlds)}
    _bounded(body)
    return deepcopy(body)


def validate_bank(bank):
    _bounded(bank)
    _closed(bank, {"schema", "worlds", "bank"}, "TYPED_SOURCE_BANK_FIELDS")
    require(bank["schema"] == BANK_SCHEMA and type(bank["worlds"]) is list
            and 0 < len(bank["worlds"]) <= MAX_BANK_WORLDS, "TYPED_SOURCE_BANK_SCHEMA")
    worlds = [_validate_world(world) for world in bank["worlds"]]
    require(len({world["world_id"] for world in worlds}) == len(worlds)
            and worlds == sorted(worlds, key=lambda world: world["world_id"]), "TYPED_SOURCE_BANK_WORLD_ORDER")
    require(canonical(bank["bank"]) == canonical(_bank_record(worlds)), "TYPED_SOURCE_BANK_IDENTITY")
    return deepcopy(bank)


def compile_source(family, *, bank):
    frozen = validate_bank(bank)
    focus = _world(_material(family))
    worlds = {world["world_id"]: world for world in frozen["worlds"]}
    worlds[focus["world_id"]] = focus
    require(len(worlds) <= MAX_WORLD_UNION, "TYPED_SOURCE_WORLD_UNION_BOUND")
    public = {"focus_world_id": focus["world_id"], "worlds": [worlds[key] for key in sorted(worlds)],
              "bank": deepcopy(frozen["bank"])}
    provenance = {"source_profile": source_profile(), "input_family_digest": digest(family),
                  "input_family_id": family["family_id"], "input_archetype": family["archetype"],
                  "input_rendering": family["rendering"], "input_split": family["split"],
                  "authority": "CALLER_SUPPLIED_DECLARATIONS_SYNTAX_CHECKED_ONLY",
                  "authorship_authenticated": False, "world_truth_established": False,
                  "teacher_answer_or_query_used": False}
    body = {"schema": SCHEMA, "public": public, "provenance": provenance}
    result = {**body, "source_digest": digest(body)}
    _bounded(result)
    return deepcopy(result)


def validate_public_source(public):
    """Closed source syntax/identity only; no teacher, task, or source file reads."""
    _bounded(public)
    _closed(public, {"focus_world_id", "worlds", "bank"}, "TYPED_SOURCE_PUBLIC_FIELDS")
    require(type(public["worlds"]) is list and 0 < len(public["worlds"]) <= MAX_WORLD_UNION, "TYPED_SOURCE_WORLD_UNION_BOUND")
    worlds = [_validate_world(world) for world in public["worlds"]]
    ids = [world["world_id"] for world in worlds]
    require(ids == sorted(set(ids)) and type(public["focus_world_id"]) is str
            and public["focus_world_id"] in ids, "TYPED_SOURCE_FOCUS_OR_WORLD_ORDER")
    record = public["bank"]
    require(type(record) is dict and type(record.get("world_ids")) is list
            and 0 < len(record["world_ids"]) <= MAX_BANK_WORLDS
            and all(type(ref) is str and ref in ids for ref in record["world_ids"]), "TYPED_SOURCE_PUBLIC_BANK_REFS")
    require(set(ids) == set(record["world_ids"]) | {public["focus_world_id"]}, "TYPED_SOURCE_UNDECLARED_WORLD")
    bank_worlds = [world for world in worlds if world["world_id"] in record["world_ids"]]
    require(canonical(record) == canonical(_bank_record(bank_worlds)), "TYPED_SOURCE_PUBLIC_BANK_IDENTITY")
    return deepcopy(public)


def public_source(envelope):
    _bounded(envelope)
    _closed(envelope, {"schema", "public", "provenance", "source_digest"}, "TYPED_SOURCE_ENVELOPE_FIELDS")
    require(envelope["schema"] == SCHEMA and type(envelope["source_digest"]) is str
            and envelope["source_digest"] == digest({key: value for key, value in envelope.items() if key != "source_digest"}),
            "TYPED_SOURCE_ENVELOPE_IDENTITY")
    _closed(envelope["provenance"], {"source_profile", "input_family_digest", "input_family_id",
        "input_archetype", "input_rendering", "input_split", "authority", "authorship_authenticated",
        "world_truth_established", "teacher_answer_or_query_used"}, "TYPED_SOURCE_PROVENANCE_FIELDS")
    provenance = envelope["provenance"]
    require(provenance["authorship_authenticated"] is False
            and provenance["world_truth_established"] is False
            and provenance["teacher_answer_or_query_used"] is False
            and provenance["authority"] == "CALLER_SUPPLIED_DECLARATIONS_SYNTAX_CHECKED_ONLY",
            "TYPED_SOURCE_UNSUPPORTED_AUTHORITY")
    for field in ("input_family_id", "input_archetype"):
        _text(provenance[field])
    require(type(provenance["input_rendering"]) is int and 0 <= provenance["input_rendering"] < 4
            and provenance["input_split"] == "training", "TYPED_SOURCE_PROVENANCE_VALUES")
    require(type(provenance["input_family_digest"]) is str and
            re.fullmatch(r"[a-f0-9]{64}", provenance["input_family_digest"]), "TYPED_SOURCE_PROVENANCE_DIGEST")
    profile = provenance["source_profile"]
    _closed(profile, {"schema", "files", "data_files", "pin_role", "final_target_files_read", "profile_digest"},
            "TYPED_SOURCE_PROFILE_FIELDS")
    require(profile["schema"] == "cas.typed-teaching-source-profile/0.1" and profile["data_files"] == []
            and profile["final_target_files_read"] is False
            and profile["pin_role"] == "ON_DISK_GENERATOR_AND_CONTRACT_BYTES_NOT_LOADED_RUNTIME_ATTESTATION",
            "TYPED_SOURCE_PROFILE_SCOPE")
    expected_paths = ["cas_meta2/typed_teaching/__init__.py", "cas_meta2/typed_teaching/source.py",
                      "cas_meta2/graph_teaching/face_corpus.py"]
    require(type(profile["files"]) is list and len(profile["files"]) == len(expected_paths), "TYPED_SOURCE_PROFILE_FILES")
    for row, path in zip(profile["files"], expected_paths):
        _closed(row, {"path", "bytes", "sha256"}, "TYPED_SOURCE_PROFILE_ROW")
        require(row["path"] == path and type(row["bytes"]) is int and 0 < row["bytes"] <= 1024 * 1024
                and type(row["sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", row["sha256"]), "TYPED_SOURCE_PROFILE_ROW_VALUE")
    require(profile["profile_digest"] == digest({key: value for key, value in profile.items() if key != "profile_digest"}),
            "TYPED_SOURCE_PROFILE_DIGEST")
    return validate_public_source(envelope["public"])


def validate_public(public):
    """Public-only alias used by the typed question and answer contracts."""
    return validate_public_source(public)


def public_digest(public):
    return digest(validate_public_source(public))
