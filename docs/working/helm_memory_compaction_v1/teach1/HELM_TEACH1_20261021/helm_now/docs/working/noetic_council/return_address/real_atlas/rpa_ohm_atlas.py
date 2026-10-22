"""Read-only CAS-Ohm atlas over checked local PCBA and compiler records.

The present is explicitly host-declared fixture state, never a measurement.
This wrapper preserves historical AtlasSnapshot schemas and cannot execute a
board, authenticate a caller's references, or infer physical/semantic meaning.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import threading
from urllib.parse import quote, urlsplit, parse_qs

from .canonical import canonical_json, digest
from .model import ContractError
from .rpa_model import (AtlasContext, AtlasNode, AtlasLink, AtlasSnapshot,
                        NodeStatus, NodeKind, LinkType, identifier, text, require)
from . import rpa_coordinates as coordinates

SCHEMA = "cas.rpa.ohm-atlas/0.1"
INPUT_SCHEMA = "cas.rpa.ohm-atlas-input/0.1"
ADDRESS_SCHEMA = "cas.rpa.ohm-address/0.1"
CURSOR_SCHEMA = "cas.rpa.ohm-navigation/0.1"
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_ITEMS = 64
MAX_CASES = 8
MAX_PATH = 32
LAB = Path(__file__).resolve().parents[1] / "research/helm_cas_expression_lab"
_LOCK = threading.RLock()
_ROLES = {"project", "board", "stage", "resistor", "calculation", "note"}
_BOUNDARY = {
    "integration_status": "READ_ONLY_ATLAS_CONNECTED",
    "present_status": "HOST_DECLARED_FIXTURE_NOT_MEASURED",
    "measurement_status": "NO_MEASUREMENT_PERFORMED",
    "provenance_status": "CALLER_REFERENCES_UNVERIFIED",
    "runtime_status": "NOT_CONNECTED",
    "authority": "INSPECTION_ONLY",
    "aggregation_status": "NONE_NO_TOTAL_INFERRED",
    "semantic_outcome": "NOT_ASSESSED",
    "learning_status": "NOT_RUN",
}
_ITEM_FIELDS = {"node_id", "item_id", "version_id", "label", "role",
                "cas_description", "status", "profile"}
_CASE_FIELDS = {"case_id", "board_node_id", "stage_node_id", "resistor_node_id",
                "calculation_node_id", "source", "resistor_name", "drive", "resistance"}


def _fields(value, names, label):
    require(type(value) is dict and set(value) == set(names), label + " fields invalid")


@contextmanager
def _connections():
    """Use only local lab imports; reject a cached sibling-checkout module."""
    with _LOCK:
        names = ("pcba_reader", "pcba_component_adapter", "pcba_check", "cas_ohm_connections")
        for name in names:
            loaded = sys.modules.get(name)
            if loaded is not None:
                require(getattr(loaded, "__file__", None) is not None and
                        Path(loaded.__file__).resolve() == LAB / (name + ".py"),
                        "lab module belongs to another checkout: " + name)
        sys.path.insert(0, str(LAB))
        try:
            adapter = importlib.import_module("cas_ohm_connections")
            yield adapter
        finally:
            # Restore only the entry we added, even if a called importer added entries.
            sys.path.remove(str(LAB))


def _bounded(value, maximum=MAX_DOCUMENT_BYTES):
    with _connections() as adapter:
        try:
            return adapter._bounded_json(value, maximum)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc


def _profile(value):
    if value is None:
        return None
    _fields(value, ("values", "order", "basis", "origin", "reference"), "profile")
    require(type(value["values"]) is list, "profile values must be a list")
    text(value["basis"], "profile basis", 512)
    text(value["reference"], "profile reference", 1024)
    require(value["origin"] == "declared", "profile origin must be declared")
    converted = coordinates.reorder_profile(tuple(value["values"]),
        source_order=value["order"], target_order=coordinates.CANONICAL_ORDER)
    return {"values": list(converted), "order": coordinates.CANONICAL_ORDER,
            "basis": value["basis"], "origin": "declared",
            "reference": value["reference"], "source_order": value["order"],
            "assignment_status": "CALLER_DECLARED_NOT_MEASURED"}


def _ohm_expression(drive, resistance, literal):
    # The compiler accepts literal UTF-8 and quote/backslash escapes, but does
    # not decode JSON's \\uXXXX escapes. Preserve non-ASCII provenance exactly.
    def scale(declaration):
        return "ohm_scale(" + ", ".join(json.dumps(declaration[key], ensure_ascii=False)
            for key in ("id", "drive_unit", "attention_unit")) + ")"
    def quantity(kind, declaration, value):
        return "ohm_" + kind + "(" + ", ".join((
            json.dumps(value, ensure_ascii=False), scale(declaration["scale"]),
            json.dumps(declaration["origin"]), json.dumps(declaration["reference"], ensure_ascii=False))) + ")"
    return "ohm_flow(" + quantity("drive", drive, drive["value"]) + ", " + quantity("constraint", resistance, literal) + ")"


def _component_expression(source, name):
    reader = importlib.import_module("pcba_reader")
    document = reader.parse_pcba_document(source)
    pending = list(document["statements"])
    found = []
    while pending:
        statement = pending.pop()
        if statement["kind"] == "layer":
            pending.extend(statement["statements"])
        if statement["kind"] == "component" and statement["name"] == name:
            found.append(statement["expression"])
    require(len(found) == 1, "selected resistor declaration must be unique")
    return found[0]


def build_ohm_atlas(declaration):
    """Build from bounded explicit declarations using the real local adapters.

    Saved items retain caller-assigned permanent item IDs and version IDs.
    Coordinates never generate identity, status, containment, or present state.
    """
    _bounded(declaration)
    _fields(declaration, ("schema_version", "atlas_id", "context", "present",
                         "items", "links", "cases"), "atlas declaration")
    require(declaration["schema_version"] == INPUT_SCHEMA, "atlas input version invalid")
    identifier(declaration["atlas_id"], "atlas")
    context = AtlasContext.from_dict(declaration["context"])
    present = declaration["present"]
    _fields(present, ("node_id", "reference", "designation"), "present")
    identifier(present["node_id"], "present")
    text(present["reference"], "present reference", 1024)
    require(present["designation"] == "HOST_DECLARED_FIXTURE", "explicit host fixture designation required")
    items = declaration["items"]
    require(type(items) is list and 1 <= len(items) <= MAX_ITEMS, "item count invalid")
    by_id, versions, profiles, item_roles = {}, set(), {}, {}
    for item in items:
        _fields(item, _ITEM_FIELDS, "item")
        for key in ("node_id", "item_id", "version_id"):
            identifier(item[key], key)
        require(item["node_id"] not in by_id, "duplicate node ID")
        key = item["item_id"], item["version_id"]
        require(key not in versions, "duplicate permanent item/version")
        versions.add(key)
        text(item["label"], "label", 512)
        text(item["cas_description"], "full CAS description", 65536)
        require(type(item["role"]) is str and item["role"] in _ROLES, "item role invalid")
        require(item["item_id"] not in item_roles or item_roles[item["item_id"]] == item["role"],
                "saved versions of a permanent item must retain its role")
        item_roles[item["item_id"]] = item["role"]
        require(type(item["status"]) is str and item["status"] in {"unknown", "hypothetical"},
                "item status must be unknown or hypothetical; present is separately declared")
        by_id[item["node_id"]] = item
        profiles[item["node_id"]] = _profile(item["profile"])
    require(present["node_id"] in by_id and by_id[present["node_id"]]["status"] == "unknown",
            "present must name an existing nonhypothetical declared item")
    require(by_id[present["node_id"]]["role"] == "project", "present must be the declared project state")
    links = declaration["links"]
    require(type(links) is list and len(links) <= 256, "link count invalid")
    typed_links, edges = [], set()
    for row in links:
        _fields(row, ("source_id", "target_id", "relation", "projection"), "link")
        for key in ("source_id", "target_id"):
            identifier(row[key], key)
            require(row[key] in by_id, "link endpoint missing")
        require(type(row["relation"]) is str and row["relation"] in
                {"contains_part", "references_same_idea"}, "unsupported atlas relation")
        edge = row["source_id"], row["target_id"], row["relation"]
        require(edge not in edges, "duplicate atlas relationship")
        edges.add(edge)
        typed_links.append(AtlasLink("link-" + digest(row), row["source_id"], row["target_id"],
            LinkType(row["relation"]), projection=row["projection"]))
    cases = declaration["cases"]
    require(type(cases) is list and 1 <= len(cases) <= MAX_CASES, "case count invalid")
    receipts, case_ids, bound_nodes = [], set(), set()
    with _connections() as adapter:
        for case in cases:
            _fields(case, _CASE_FIELDS, "case")
            identifier(case["case_id"], "case")
            require(case["case_id"] not in case_ids, "duplicate case ID")
            case_ids.add(case["case_id"])
            roles = ("board", "stage", "resistor", "calculation")
            node_ids = [case[role + "_node_id"] for role in roles]
            for role, node_id in zip(roles, node_ids):
                identifier(node_id, "case node")
                require(node_id in by_id and by_id[node_id]["role"] == role, "case role binding invalid")
                require(node_id not in bound_nodes, "case node reused across independent cases")
                bound_nodes.add(node_id)
            require(len({by_id[key]["version_id"] for key in node_ids}) == 1,
                    "case nodes must share a saved version")
            require(len({by_id[key]["status"] for key in node_ids}) == 1,
                    "case nodes must share hypothetical/unknown status")
            require(all((left, right, "contains_part") in edges for left, right in zip(node_ids, node_ids[1:])),
                    "case must declare board -> stage -> resistor -> calculation containment")
            require(case["source"] == by_id[node_ids[0]]["cas_description"], "board source/description mismatch")
            require(type(case["drive"]) is dict and type(case["drive"].get("value")) is str,
                    "drive value must be explicit decimal text")
            pcba = adapter.pcba_resistor_flow(case["source"], case["resistor_name"], case["drive"], case["resistance"])
            component = _component_expression(case["source"], case["resistor_name"])
            require(component == by_id[node_ids[2]]["cas_description"], "resistor full expression mismatch")
            expression = _ohm_expression(case["drive"], case["resistance"], pcba["resistance_literal"])
            require(expression == by_id[node_ids[3]]["cas_description"], "calculation full expression mismatch")
            compiler = adapter.make_synthetic_demo(expression, case["case_id"])
            require(canonical_json(compiler["target"]["quantity_report"]) == canonical_json(pcba["quantity_report"]),
                    "PCBA/compiler exact quantity or provenance mismatch")
            projection = adapter.project_cas_rpa([{"node_id": node_ids[3], "parent_id": None,
                                                 "quantity_report": pcba["quantity_report"]}])
            body = {"case_id": case["case_id"], "node_ids": node_ids,
                    "pcba": pcba, "compiler": compiler, "projection": projection,
                    "board_source_sha256": hashlib.sha256(case["source"].encode("utf-8")).hexdigest(),
                    "expression_sha256": hashlib.sha256(expression.encode("utf-8")).hexdigest()}
            receipts.append({**body, "receipt_sha256": digest(body)})
    require(all(item["role"] in {"project", "note"} or item["node_id"] in bound_nodes for item in items),
            "board/stage/resistor/calculation requires a bound case")
    typed_nodes = []
    receipt_by_node = {key: row["receipt_sha256"] for row in receipts for key in row["node_ids"]}
    for item in items:
        node_id, profile = item["node_id"], profiles[item["node_id"]]
        fields = {"item_id": item["item_id"], "version_id": item["version_id"],
                  "role": item["role"], "cas_description": item["cas_description"],
                  "identity_status": "CALLER_ASSIGNED_PERMANENT_ITEM",
                  "record_status": "DECLARED_SAVED_VERSION"}
        evidence = ()
        if node_id in receipt_by_node:
            fields["case_receipt_sha256"] = receipt_by_node[node_id]
            evidence = ("receipt-" + receipt_by_node[node_id],)
        if node_id == present["node_id"]:
            fields["present_designation"] = present["designation"]
            fields["present_reference"] = present["reference"]
        typed_nodes.append(AtlasNode(node_id, item["item_id"], item["label"], context,
            NodeStatus.OBSERVED if node_id == present["node_id"] else NodeStatus(item["status"]),
            tuple(sorted(fields.items())), profile40=None if profile is None else tuple(profile["values"]),
            profile_basis=None if profile is None else profile["basis"],
            kind=NodeKind.STATE if node_id == present["node_id"] else NodeKind.IDEA_CONTEXT,
            evidence_refs=evidence))
    atlas = AtlasSnapshot(tuple(typed_nodes), tuple(typed_links), present["node_id"], present["node_id"])
    expansion = atlas.expand(max_depth=32, max_nodes=MAX_ITEMS,
                             relations=(LinkType.CONTAINS_PART,), root_id=present["node_id"])
    require(set(expansion.visited_node_ids) == set(by_id), "all declared nodes must be reachable from present by containment")
    body = {"schema_version": SCHEMA, "declaration": deepcopy(declaration), "atlas": atlas.to_dict(),
            "receipts": sorted(receipts, key=lambda row: row["case_id"]),
            "profiles": {key: profiles[key] for key in sorted(profiles)},
            "boundary": dict(_BOUNDARY)}
    _bounded(body)
    return {**body, "document_sha256": digest(body)}


def validate_ohm_atlas(document):
    """Replay every supplied case and compare the complete canonical wrapper."""
    _bounded(document)
    _fields(document, ("schema_version", "declaration", "atlas", "receipts", "profiles",
                       "boundary", "document_sha256"), "atlas document")
    require(document["schema_version"] == SCHEMA, "atlas document version invalid")
    expected = build_ohm_atlas(document["declaration"])
    require(canonical_json(document) == canonical_json(expected),
            "atlas document does not reconstruct from its bound declarations and current sources")
    return AtlasSnapshot.from_dict(expected["atlas"])


def load_ohm_atlas(source):
    """Decode at most 4 MiB of UTF-8, reject duplicate keys, and replay bindings."""
    require(type(source) in (bytes, str), "atlas wire source must be bytes or text")
    require(len(source) <= MAX_DOCUMENT_BYTES, "atlas wire size exceeded")
    try:
        raw = source if type(source) is bytes else source.encode("utf-8")
        require(len(raw) <= MAX_DOCUMENT_BYTES, "atlas wire byte size exceeded")
        def pairs(rows):
            result = {}
            for key, value in rows:
                require(key not in result, "duplicate JSON object key")
                result[key] = value
            return result
        def bounded_integer(token):
            # Bound decimal text before conversion even if the host disabled
            # Python's integer-string guard; do not change that global policy.
            require(len(token.lstrip("-")) <= 1234, "JSON integer token exceeds 4096-bit budget")
            value = int(Decimal(token))
            require(value.bit_length() <= 4096, "JSON integer exceeds 4096-bit budget")
            return value
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_int=bounded_integer,
            parse_constant=lambda value: (_ for _ in ()).throw(ContractError("nonfinite JSON constant")))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ContractError("invalid bounded atlas JSON: " + str(exc)[:160]) from exc
    validate_ohm_atlas(document)
    return document


def _address(document, atlas, node_id):
    identifier(node_id, "address node")
    require(node_id in atlas.node_map(), "address node missing")
    node = atlas.node_map()[node_id]
    fields = dict(node.fields)
    return {"schema_version": ADDRESS_SCHEMA, "document_sha256": document["document_sha256"],
            "node_id": node_id, "item_id": node.idea_id, "version_id": fields["version_id"],
            "context_sha256": digest(node.context.to_dict())}


def exact_address(document, node_id):
    return _address(document, validate_ohm_atlas(document), node_id)


def address_text(address):
    _fields(address, ("schema_version", "document_sha256", "node_id", "item_id", "version_id",
                      "context_sha256"), "address")
    require(address["schema_version"] == ADDRESS_SCHEMA, "address version invalid")
    for key in ("document_sha256", "context_sha256"):
        require(type(address[key]) is str and len(address[key]) == 64 and
                all(char in "0123456789abcdef" for char in address[key]), "address hash invalid")
    for key in ("node_id", "item_id", "version_id"):
        identifier(address[key], key)
    return ("cas-rpa://" + address["document_sha256"] + "/" + quote(address["node_id"], safe="") +
            "?context=" + address["context_sha256"] + "&version=" + quote(address["version_id"], safe="") +
            "&item=" + quote(address["item_id"], safe=""))


def parse_address(value):
    text(value, "address text", 2048)
    try:
        parts = urlsplit(value)
        query = parse_qs(parts.query, strict_parsing=True)
        require(set(query) == {"context", "version", "item"} and all(len(v) == 1 for v in query.values()),
                "address query invalid")
        from urllib.parse import unquote
        address = {"schema_version": ADDRESS_SCHEMA, "document_sha256": parts.netloc,
                   "node_id": unquote(parts.path[1:]), "context_sha256": query["context"][0],
                   "version_id": query["version"][0], "item_id": query["item"][0]}
        require(address_text(address) == value, "address is not canonical")
        return address
    except ValueError as exc:
        raise ContractError("invalid exact address") from exc


def resolve_address(document, address):
    atlas = validate_ohm_atlas(document)
    address = parse_address(address) if type(address) is str else address
    _bounded(address, 4096)
    require(type(address) is dict and type(address.get("node_id")) is str, "address node required")
    expected = _address(document, atlas, address["node_id"])
    require(canonical_json(expected) == canonical_json(address), "address binding mismatch")
    return atlas.node_map()[address["node_id"]]


def _cursor(document, atlas, cursor):
    _bounded(cursor, 8192)
    _fields(cursor, ("schema_version", "document_sha256", "path", "focus_node_id", "reference_node_id"), "cursor")
    require(cursor["schema_version"] == CURSOR_SCHEMA and cursor["document_sha256"] == document["document_sha256"],
            "navigation document binding mismatch")
    path = cursor["path"]
    require(type(path) is list and 1 <= len(path) <= MAX_PATH and all(type(key) is str for key in path),
            "navigation path invalid")
    require(len(set(path)) == len(path) and path[0] == atlas.current_state_id, "navigation path root/cycle invalid")
    nodes = atlas.node_map()
    require(all(key in nodes for key in path), "navigation path node missing")
    for key in ("focus_node_id", "reference_node_id"):
        require(type(cursor[key]) is str and cursor[key] in nodes, "navigation selection missing")
    edges = {(link.source_id, link.target_id) for link in atlas.links if link.relation is LinkType.CONTAINS_PART}
    require(all((left, right) in edges for left, right in zip(path, path[1:])), "breadcrumb must follow containment")
    require(all(any(left == key for left, _ in edges) for key in path[1:]),
            "leaf has no interior in a breadcrumb path")
    return cursor


def start_navigation(document):
    atlas = validate_ohm_atlas(document)
    return {"schema_version": CURSOR_SCHEMA, "document_sha256": document["document_sha256"],
            "path": [atlas.current_state_id], "focus_node_id": atlas.current_state_id,
            "reference_node_id": atlas.current_state_id}


def inspect_node(document, cursor, node_id):
    atlas = validate_ohm_atlas(document)
    _cursor(document, atlas, cursor)
    return deepcopy(_cursor(document, atlas, {**cursor, "focus_node_id": node_id}))


def select_reference(document, cursor, node_id):
    atlas = validate_ohm_atlas(document)
    _cursor(document, atlas, cursor)
    return deepcopy(_cursor(document, atlas, {**cursor, "reference_node_id": node_id}))


def enter_node(document, cursor, node_id):
    atlas = validate_ohm_atlas(document)
    _cursor(document, atlas, cursor)
    require(any(edge.source_id == cursor["path"][-1] and edge.target_id == node_id and
                edge.relation is LinkType.CONTAINS_PART for edge in atlas.links), "entry requires direct containment")
    require(any(edge.source_id == node_id and edge.relation is LinkType.CONTAINS_PART for edge in atlas.links),
            "leaf has no interior to enter")
    return deepcopy(_cursor(document, atlas, {**cursor, "path": cursor["path"] + [node_id], "focus_node_id": node_id}))


def return_to(document, cursor, index):
    atlas = validate_ohm_atlas(document)
    _cursor(document, atlas, cursor)
    require(type(index) is int and 0 <= index < len(cursor["path"]), "breadcrumb index invalid")
    path = cursor["path"][:index + 1]
    return deepcopy(_cursor(document, atlas, {**cursor, "path": path, "focus_node_id": path[-1]}))


def _inspection(document, atlas, node_id, reference_node_id):
    node = atlas.node_map()[node_id]
    profile, reference = document["profiles"][node_id], document["profiles"][reference_node_id]
    report = {"status": "NOT_ASSIGNED", "values": None, "reference_node_id": reference_node_id,
              "reference_profile_status": "NOT_ASSIGNED" if reference is None else "DECLARED",
              "order": coordinates.CANONICAL_ORDER,
              "labels": list(coordinates.COORDINATE_LABELS),
              "denominator_label": coordinates.DENOMINATOR_LABEL,
              "numerical_policy": deepcopy(coordinates.NUMERICAL_POLICY)}
    if profile is not None and reference is None:
        report["status"] = "REFERENCE_NOT_ASSIGNED"
    if profile is not None and reference is not None:
        if profile["basis"] != reference["basis"]:
            report["status"] = "INCOMPATIBLE_DECLARED_BASIS"
        else:
            report["values"] = list(coordinates.centered_coordinates(tuple(profile["values"]), tuple(reference["values"]),
                profile_order=coordinates.CANONICAL_ORDER, reference_order=coordinates.CANONICAL_ORDER))
            report["status"] = "CALCULATED_FROM_DECLARED_PROFILES"
            try:
                recovered = coordinates.recover_profile(tuple(report["values"]), tuple(reference["values"]),
                    reference_order=coordinates.CANONICAL_ORDER, output_order=coordinates.CANONICAL_ORDER)
                original = tuple(float(value) for value in coordinates.validate_profile(tuple(profile["values"])))
                within = all(math.isclose(a, b, rel_tol=coordinates.ROUND_TRIP_REL_TOL,
                                         abs_tol=coordinates.ROUND_TRIP_ABS_TOL) for a, b in zip(original, recovered))
                report["round_trip"] = {"status": "WITHIN_DECLARED_TOLERANCE" if within else "OUTSIDE_DECLARED_TOLERANCE",
                                        "recovered_values": list(recovered),
                                        "max_absolute_error": max(abs(a - b) for a, b in zip(original, recovered))}
            except ContractError as exc:
                report["round_trip"] = {"status": "INVERSE_NOT_REPRESENTABLE", "reason": str(exc)}
    address = _address(document, atlas, node_id)
    return {"node": node.to_dict(), "address": address, "address_text": address_text(address),
            "full_cas_description": dict(node.fields)["cas_description"],
            "profile_status": "NOT_ASSIGNED" if profile is None else "DECLARED_NOT_MEASURED",
            "profile": deepcopy(profile), "coordinate_report": report,
            "case_receipts": deepcopy([row for row in document["receipts"] if node_id in row["node_ids"]]),
            "authority": "INSPECTION_ONLY"}


def navigation_view(document, cursor):
    atlas = validate_ohm_atlas(document)
    _cursor(document, atlas, cursor)
    scope = cursor["path"][-1]
    edges = [edge for edge in atlas.links if edge.source_id == scope and edge.relation is LinkType.CONTAINS_PART]
    keys = {scope} | {edge.target_id for edge in edges}
    return {"document_sha256": document["document_sha256"], "current_state_id": atlas.current_state_id,
            "scope_id": scope, "breadcrumb": list(cursor["path"]), "focus_node_id": cursor["focus_node_id"],
            "reference_node_id": cursor["reference_node_id"],
            "nodes": [atlas.node_map()[key].to_dict() for key in sorted(keys)],
            "links": [edge.to_dict() for edge in edges],
            "inspection": _inspection(document, atlas, cursor["focus_node_id"], cursor["reference_node_id"]),
            "authority": "INSPECTION_ONLY"}


def view_payload(document):
    """Validate once and expose O(nodes) initial-reference reports for a viewer."""
    atlas = validate_ohm_atlas(document)
    return {"schema_version": "cas.rpa.ohm-view-payload/0.1",
            "document_sha256": document["document_sha256"], "atlas": atlas.to_dict(),
            "current_state_id": atlas.current_state_id, "initial_reference_node_id": atlas.current_state_id,
            "nodes": {node.node_id: _inspection(document, atlas, node.node_id, atlas.current_state_id) for node in atlas.nodes},
            "boundary": deepcopy(document["boundary"]),
            "navigation": {"schema_version": CURSOR_SCHEMA, "document_sha256": document["document_sha256"],
                           "path": [atlas.current_state_id], "focus_node_id": atlas.current_state_id,
                           "reference_node_id": atlas.current_state_id}}


def demo_declaration():
    """Explicit educational fixture: profiles and present are declared, not inferred."""
    scale = {"id": "demo-linear", "drive_unit": "declared_drive", "attention_unit": "declared_attention"}
    drive = {"value": "12", "scale": scale, "origin": "design", "reference": "demo:drive"}
    resistance = {"scale": scale, "origin": "design", "reference": "demo:resistor-scale"}
    profile = {"values": ["1/40"] * 40, "order": coordinates.CANONICAL_ORDER,
               "basis": "declared-demo-noetic-domain-basis-v1", "origin": "declared",
               "reference": "owner-declared-example-profile"}
    def item(node_id, item_id, version, role, description, assigned, status="unknown"):
        return {"node_id": node_id, "item_id": item_id, "version_id": version, "label": node_id,
                "role": role, "cas_description": description, "status": status, "profile": deepcopy(assigned)}
    items = [item("project", "ohm-project", "v1", "project",
                  "Declared CAS-Ohm comparison project. Present design: R=4; R=6 is hypothetical.", profile)]
    links, cases = [], []
    def part(left, right, projection):
        links.append({"source_id": left, "target_id": right, "relation": "contains_part", "projection": projection})
    for literal, suffix, version, status in (("4", "r4", "v1", "unknown"), ("6", "r6", "v2", "hypothetical")):
        source = "board demo { node a: ^8^C|A; resistor r1: Resistor<a,R=" + literal + ">; }"
        expression = _ohm_expression(drive, resistance, literal)
        alternate = deepcopy(profile)
        if suffix == "r6":
            alternate["values"] = ["1/20", "1/80"] + ["1/40"] * 37 + ["1/80"]
            alternate["reference"] = "owner-declared-alternative-example-profile"
        for role, description in (("board", source), ("stage", "Declared single-resistor stage at state ^8^C|A."),
                                  ("resistor", "Resistor<a,R=" + literal + ">"), ("calculation", expression)):
            items.append(item(role + "-" + suffix, "demo-" + role, version, role, description, alternate, status))
        part("project", "board-" + suffix, "declared board version " + version)
        for left, right in (("board", "stage"), ("stage", "resistor"), ("resistor", "calculation")):
            part(left + "-" + suffix, right + "-" + suffix, "declared " + right + " part")
        cases.append({"case_id": "case-" + suffix, "board_node_id": "board-" + suffix,
                      "stage_node_id": "stage-" + suffix, "resistor_node_id": "resistor-" + suffix,
                      "calculation_node_id": "calculation-" + suffix, "source": source,
                      "resistor_name": "r1", "drive": deepcopy(drive), "resistance": deepcopy(resistance)})
    for role in ("board", "stage", "resistor", "calculation"):
        links.append({"source_id": role + "-r4", "target_id": role + "-r6",
                      "relation": "references_same_idea", "projection": None})
    items.append(item("note-unprofiled", "unprofiled-note", "v1", "note",
                      "No profile was supplied for this explanatory note.", None))
    part("project", "note-unprofiled", "declared explanatory note")
    return {"schema_version": INPUT_SCHEMA, "atlas_id": "cas-ohm-demo",
            "context": AtlasContext("ohm-demo", "cas-ohm-atlas/0.1", "declared-fixture",
                                    "logical-fixture:1", 1).to_dict(),
            "present": {"node_id": "project", "reference": "owner-declared-demo-present",
                        "designation": "HOST_DECLARED_FIXTURE"},
            "items": items, "links": links, "cases": cases}


def build_demo():
    return build_ohm_atlas(demo_declaration())
