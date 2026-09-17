"""Reversible full-public frames, with no answer computation or pruning.

The learner-visible text contains every alias, factored policy, source fact,
query and worked support needed to reconstruct the input packet. It is a
declared JSON-line language, not legacy Facts prose. W aliases follow sorted
world IDs; N aliases follow sorted node refs *within* each world. E aliases
similarly identify supplied edges. References embedded in opaque public text
are escaped and compacted reversibly, never parsed for semantic meaning.

Admission here is closed public syntax plus internal digest/reference joins.
Instructions and catalog strings are preserved, not certified as an authorized
course. A caller must separately pin the approved course registry. Integrity
of self-contained frames is not authentication, numerical readiness or learning.
Only the existing pure source/answer syntax contracts and stdlib are imported;
no course, focal, semantic checker, numerical or provider module is imported.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from . import answers, source

SCHEMA = "cas.typed-teaching-input-frame/0.1"
TEXT_SCHEMA = "cas.typed-teaching-input-text/0.1"
PROFILE_SCHEMA = "cas.typed-teaching-input-frame-profile/0.1"
MAX_PACKET_BYTES = 8 * 1024 * 1024
MAX_FRAME_BYTES = 16 * 1024 * 1024
_FRAME_FIELDS = {"schema", "profile_digest", "bindings", "aliases", "text", "frame_digest"}
_RECORD_FIELDS = {"record_id", "schema", "source_digest", "source_world_id", "query",
                  "cue", "instruction", "role_catalog", "supports"}
_SUPPORT_FIELDS = {"query", "cue", "instruction", "worked_answer", "selection_rule"}
_KIND_FACE = {"definition": 1, "context": 2, "analogy": 3, "correspondence": 4,
              "parts": 5, "reach": 5, "edge_account": 6}
_WORLD_FIELDS = {"nodes", "declared_whole", "declarations", "contains", "source_order",
                 "canonical_account_order", "policy"}
_POLICY_FIELDS = {"participants_basis", "contains_inventory_complete", "inventory_scope",
                  "source_status", "process_order", "order_basis"}


class InputFrameError(ValueError):
    """Malformed public syntax, ambiguous aliases, or a changed byte binding."""


def _require(value, reason):
    if not value:
        raise InputFrameError(reason)


def _closed(value, fields, reason):
    _require(type(value) is dict and set(value) == set(fields), reason)


def _canonical(value):
    # Match course/source canonical bytes, including ASCII Unicode escapes.
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise InputFrameError("INPUT_FRAME_JSON") from exc


def _digest(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _bounded(value, maximum):
    count, active = 0, set()
    def walk(item, depth):
        nonlocal count
        count += 1
        _require(count <= 250000 and depth <= 32, "INPUT_FRAME_TREE_BOUND")
        _require(type(item) in (dict, list, str, int, bool, type(None)), "INPUT_FRAME_JSON_TYPE")
        if type(item) in (dict, list):
            _require(id(item) not in active, "INPUT_FRAME_CYCLE")
            active.add(id(item))
            if type(item) is dict:
                _require(all(type(k) is str for k in item), "INPUT_FRAME_JSON_KEY")
                children = item.values()
            else:
                children = item
            for child in children:
                walk(child, depth + 1)
            active.remove(id(item))
        elif type(item) is str:
            try:
                size = len(item.encode("utf-8"))
            except UnicodeError as exc:
                raise InputFrameError("INPUT_FRAME_UTF8") from exc
            _require(size <= maximum, "INPUT_FRAME_STRING_BOUND")
    walk(value, 0)
    _require(len(_canonical(value).encode()) <= maximum, "INPUT_FRAME_BYTE_BOUND")


def profile():
    """Current on-disk codec/syntax pins, not a loaded-worker attestation."""
    directory = Path(__file__).resolve().parent
    files = []
    for name in ("__init__.py", "answers.py", "input_frames.py", "source.py"):
        raw = (directory / name).read_bytes()
        files.append({"path": "cas_meta2/typed_teaching/" + name,
                      "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema": PROFILE_SCHEMA, "frame_schema": SCHEMA, "text_schema": TEXT_SCHEMA,
            "files": files, "canonicalization": "SORT_KEYS_COMPACT_ASCII_JSON_UTF8_NO_NEWLINE",
            "aliases": "SORTED_WORLD_ID_W0_W64_SORTED_SCOPED_NODE_REF_N0_N9_SORTED_EDGE_REF_E0_E89",
            "escape": "AT_AT_IS_LITERAL_AT_AT_BRACE_ALIAS_IS_EXACT_REFERENCE",
            "line_order": ["FORMAT", "BINDINGS", "ALIASES", "POLICY*", "SOURCE",
                           "WORLD*", "RECORD", "QUERY", "SUPPORT*"],
            "world_node_columns": ["local_node_alias", "label", "kind"],
            "world_edge_columns": ["local_edge_alias", "local_source_node_alias", "local_target_node_alias"],
            "all_model_information_in_text": True,
            "semantic_checker_used": False, "target_conditioned_pruning": False,
            "admission": "CLOSED_PUBLIC_SYNTAX_AND_INTERNAL_BINDINGS_NOT_AUTHORIZED_COURSE_MEMBERSHIP",
            "max_packet_bytes": MAX_PACKET_BYTES, "max_frame_bytes": MAX_FRAME_BYTES,
            "numeric_readiness": False}
    return {**body, "profile_digest": _digest(body)}


def _text(value, reason):
    _require(type(value) is str and 0 < len(value.encode("utf-8")) <= 16384, reason)


def _packet(packet):
    _bounded(packet, MAX_PACKET_BYTES)
    _closed(packet, {"source", "record"}, "INPUT_PACKET_FIELDS")
    public, row = packet["source"], packet["record"]
    source.validate_public(public)
    _closed(row, _RECORD_FIELDS, "INPUT_RECORD_FIELDS")
    _require(row["schema"] == "cas.typed-teaching-model-packet/0.1"
             and row["record_id"] == "typed-input-" + _digest({k: v for k, v in row.items() if k != "record_id"}),
             "INPUT_RECORD_ID")
    query = answers.validate_query(public, row["query"])
    _require(row["source_digest"] == _digest(public)
             and row["source_world_id"] == public["focus_world_id"] == query["focus_world_id"],
             "INPUT_SOURCE_JOIN")
    _closed(row["role_catalog"], set("123456"), "INPUT_ROLE_CATALOG_FIELDS")
    for value in row["role_catalog"].values():
        _text(value, "INPUT_ROLE_CATALOG_TEXT")
    _text(row["instruction"], "INPUT_INSTRUCTION")
    _require(type(row["supports"]) is list and len(row["supports"]) in (0, 3), "INPUT_SUPPORT_COUNT")
    if query["kind"] == "role_set":
        _require(row["cue"] is None and row["supports"] == [], "INPUT_ROLE_PRIVACY")
    elif row["cue"] is not None:
        _require(row["cue"] == "CUBE_FACE_%d" % _KIND_FACE[query["kind"]], "INPUT_CUE_KIND")
    for support in row["supports"]:
        _closed(support, _SUPPORT_FIELDS, "INPUT_SUPPORT_FIELDS")
        sq = answers.validate_query(public, support["query"])
        _require(sq["kind"] in _KIND_FACE and support["cue"] == "CUBE_FACE_%d" % _KIND_FACE[sq["kind"]],
                 "INPUT_SUPPORT_CUE")
        _require(sq["focus_world_id"] != query["focus_world_id"], "INPUT_SUPPORT_SELF")
        answers.validate_answer(public, sq, support["worked_answer"])
        _text(support["instruction"], "INPUT_SUPPORT_INSTRUCTION")
        _text(support["selection_rule"], "INPUT_SUPPORT_SELECTION")


def _aliases(public):
    rows, references = [], {}
    for index, world in enumerate(sorted(public["worlds"], key=lambda w: w["world_id"])):
        alias, wid = "W%d" % index, world["world_id"]
        references[wid] = alias
        row = {"alias": alias, "world_id": wid, "nodes": [], "edges": []}
        for field, prefix in (("nodes", "N"), ("edges", "E")):
            items = world["nodes"] if field == "nodes" else world["contains"]
            for at, ref in enumerate(sorted(item["ref"] for item in items)):
                local = prefix + str(at)
                _require(ref.startswith(wid + "/"), "INPUT_ALIAS_SCOPE")
                row[field].append([local, ref[len(wid):]])
                references[ref] = alias + "/" + local
        for field in ("kind", "function", "setting"):
            references[answers.declaration_ref(wid, field)] = alias + "/decl/" + field
        rows.append(row)
    return rows, references


def _transform(value, string_function):
    if type(value) is str:
        return string_function(value)
    if type(value) is list:
        return [_transform(item, string_function) for item in value]
    if type(value) is dict:
        return {key: _transform(child, string_function) for key, child in value.items()}
    return value


def _encoder(references):
    matcher = re.compile("|".join(re.escape(ref) for ref in sorted(references, key=lambda r: (-len(r), r))))
    def encode(value):
        # Escape literal marker characters first; alias replacements introduce
        # new markers only after escaping, so alias-looking prose stays literal.
        return matcher.sub(lambda m: "@{" + references[m.group()] + "}", value.replace("@", "@@"))
    return lambda value: _transform(value, encode)


def _decoding_tables(aliases):
    _require(type(aliases) is list and 0 < len(aliases) <= 65, "INPUT_ALIAS_WORLD_BOUND")
    refs, scopes, ids = {}, {}, []
    for index, row in enumerate(aliases):
        _closed(row, {"alias", "world_id", "nodes", "edges"}, "INPUT_ALIAS_FIELDS")
        alias, wid = row["alias"], row["world_id"]
        _require(alias == "W%d" % index and type(wid) is str and re.fullmatch(r"world-[0-9a-f]{64}", wid),
                 "INPUT_ALIAS_WORLD")
        ids.append(wid)
        refs[alias] = wid
        scopes[alias] = {"world_id": wid, "nodes": {}, "edges": {}}
        for field, prefix, maximum in (("nodes", "N", 10), ("edges", "E", 90)):
            values = row[field]
            _require(type(values) is list and 0 < len(values) <= maximum, "INPUT_ALIAS_LOCAL_BOUND")
            suffixes = []
            for at, pair in enumerate(values):
                _require(type(pair) is list and len(pair) == 2 and pair[0] == prefix + str(at)
                         and type(pair[1]) is str and re.fullmatch(r"/" + prefix.lower() + r"[0-9]+", pair[1]),
                         "INPUT_ALIAS_LOCAL")
                local, suffix = pair
                suffixes.append(suffix)
                refs[alias + "/" + local] = wid + suffix
                scopes[alias][field][local] = wid + suffix
            _require(suffixes == sorted(set(suffixes)), "INPUT_ALIAS_LOCAL_ORDER")
        for field in ("kind", "function", "setting"):
            refs[alias + "/decl/" + field] = wid + "/decl/" + field
    _require(ids == sorted(set(ids)), "INPUT_ALIAS_WORLD_ORDER")
    def decode(value):
        parts, at = [], 0
        while at < len(value):
            if value[at] != "@":
                parts.append(value[at]); at += 1
            elif value.startswith("@@", at):
                parts.append("@"); at += 2
            else:
                _require(value.startswith("@{", at), "INPUT_ESCAPE")
                end = value.find("}", at + 2)
                _require(end != -1 and value[at + 2:end] in refs, "INPUT_ALIAS_UNKNOWN")
                parts.append(refs[value[at + 2:end]]); at = end + 1
        return "".join(parts)
    return scopes, lambda value: _transform(value, decode)


def _bindings(packet):
    result = {"canonicalization": "SORT_KEYS_COMPACT_ASCII_JSON_UTF8_NO_NEWLINE"}
    for key, value in (("source", packet["source"]), ("record", packet["record"]), ("packet", packet)):
        raw = _canonical(value).encode()
        result[key] = {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    return result


def _policy(world):
    return {"participants_basis": world["declarations"]["participants_basis"],
            "contains_inventory_complete": world["contains_inventory_complete"],
            "inventory_scope": world["inventory_scope"], "source_status": world["source_status"],
            "process_order": world["branch_order"]["process_order"],
            "order_basis": world["branch_order"]["order_basis"]}


def _build(packet, codec_profile):
    public, record = packet["source"], packet["record"]
    aliases, refs = _aliases(public)
    encode = _encoder(refs)
    policies = sorted({_canonical(_policy(w)) for w in public["worlds"]})
    policy_ids = {text: "P%d" % i for i, text in enumerate(policies)}
    binding = _bindings(packet)
    rows = [["FORMAT", TEXT_SCHEMA, codec_profile["profile_digest"]], ["BINDINGS", binding], ["ALIASES", aliases]]
    rows.extend(["POLICY", policy_ids[text], encode(json.loads(text))] for text in policies)
    rows.append(["SOURCE", encode({k: v for k, v in public.items() if k != "worlds"})])
    for world, alias in zip(public["worlds"], aliases):
        wid = world["world_id"]
        local = lambda ref: refs[ref].split("/", 1)[1]
        material = {"nodes": [[local(n["ref"]), n["label"], n["kind"]] for n in world["nodes"]],
                    "declared_whole": local(world["declared_whole"]),
                    "declarations": {k: v for k, v in world["declarations"].items() if k != "participants_basis"},
                    "contains": [[local(e["ref"]), local(e["source"]), local(e["target"])] for e in world["contains"]],
                    "source_order": [local(ref) for ref in world["branch_order"]["source_order"]],
                    "canonical_account_order": [local(ref) for ref in world["branch_order"]["canonical_account_order"]],
                    "policy": policy_ids[_canonical(_policy(world))]}
        rows.append(["WORLD", alias["alias"], encode(material)])
    rows.append(["RECORD", encode({k: v for k, v in record.items() if k not in ("query", "supports")})])
    rows.append(["QUERY", encode(record["query"])])
    rows.extend(["SUPPORT", "S%d" % i, encode(support)] for i, support in enumerate(record["supports"]))
    text = "\n".join(_canonical(row) for row in rows)
    body = {"schema": SCHEMA, "profile_digest": codec_profile["profile_digest"],
            "bindings": binding, "aliases": aliases, "text": text}
    result = {**body, "frame_digest": _digest(body)}
    _bounded(result, MAX_FRAME_BYTES)
    return result


def compile_packet(packet):
    """Encode every public field; no main target or semantic checker is read."""
    _packet(packet)
    return _build(packet, profile())


def _rows(text):
    _require(type(text) is str and 0 < len(text.encode("utf-8")) <= MAX_FRAME_BYTES, "INPUT_FRAME_TEXT_BOUND")
    lines = text.split("\n")
    _require(7 <= len(lines) <= 140 and all(lines), "INPUT_FRAME_LINE_BOUND")
    rows = []
    def pairs(items):
        value = {}
        for key, child in items:
            _require(key not in value, "INPUT_FRAME_DUPLICATE_KEY")
            value[key] = child
        return value
    for line in lines:
        try:
            value = json.loads(line, object_pairs_hook=pairs)
        except (ValueError, RecursionError) as exc:
            raise InputFrameError("INPUT_FRAME_LINE_JSON") from exc
        _require(type(value) is list and 2 <= len(value) <= 3 and _canonical(value) == line, "INPUT_FRAME_LINE_CANONICAL")
        rows.append(value)
    return rows


def _restore_text(text):
    rows = _rows(text)
    _require(rows[0][:2] == ["FORMAT", TEXT_SCHEMA] and len(rows[0]) == 3,
             "INPUT_FRAME_FORMAT")
    _require(rows[1][0] == "BINDINGS" and len(rows[1]) == 2
             and rows[2][0] == "ALIASES" and len(rows[2]) == 2, "INPUT_FRAME_PREAMBLE")
    aliases = rows[2][1]
    scopes, decode = _decoding_tables(aliases)
    at, policies = 3, {}
    while at < len(rows) and rows[at][0] == "POLICY":
        row = rows[at]
        _require(len(row) == 3 and row[1] == "P%d" % len(policies), "INPUT_POLICY_ORDER")
        policy = decode(row[2])
        _closed(policy, _POLICY_FIELDS, "INPUT_POLICY_FIELDS")
        policies[row[1]] = policy; at += 1
    _require(bool(policies) and at < len(rows) and rows[at][0] == "SOURCE" and len(rows[at]) == 2,
             "INPUT_SOURCE_SCOPE")
    public = decode(rows[at][1]); at += 1
    _closed(public, {"focus_world_id", "bank"}, "INPUT_SOURCE_HEADER")
    public["worlds"] = []
    for alias in aliases:
        _require(at < len(rows) and len(rows[at]) == 3 and rows[at][:2] == ["WORLD", alias["alias"]],
                 "INPUT_WORLD_SCOPE")
        data = decode(rows[at][2]); at += 1
        _closed(data, _WORLD_FIELDS, "INPUT_WORLD_FIELDS")
        scope = scopes[alias["alias"]]
        _require(type(data["policy"]) is str and data["policy"] in policies, "INPUT_WORLD_POLICY")
        policy = deepcopy(policies[data["policy"]])
        def local(ref, field):
            _require(type(ref) is str and ref in scope[field], "INPUT_LOCAL_SCOPE")
            return scope[field][ref]
        _require(type(data["nodes"]) is list and type(data["contains"]) is list, "INPUT_WORLD_ROWS")
        nodes, edges = [], []
        for row in data["nodes"]:
            _require(type(row) is list and len(row) == 3, "INPUT_NODE_COLUMNS")
            nodes.append({"ref": local(row[0], "nodes"), "label": row[1], "kind": row[2]})
        for row in data["contains"]:
            _require(type(row) is list and len(row) == 3, "INPUT_EDGE_COLUMNS")
            edges.append({"ref": local(row[0], "edges"), "source": local(row[1], "nodes"), "target": local(row[2], "nodes")})
        _closed(data["declarations"], {"domain", "kind", "function", "setting", "primary_labels", "participants"},
                "INPUT_DECLARATION_FIELDS")
        declarations = {**data["declarations"], "participants_basis": policy["participants_basis"]}
        _require(type(data["source_order"]) is list and type(data["canonical_account_order"]) is list, "INPUT_ORDER_ROWS")
        public["worlds"].append({"world_id": scope["world_id"], "nodes": nodes,
            "declared_whole": local(data["declared_whole"], "nodes"), "declarations": declarations, "contains": edges,
            "contains_inventory_complete": policy["contains_inventory_complete"], "inventory_scope": policy["inventory_scope"],
            "branch_order": {"source_order": [local(v, "edges") for v in data["source_order"]],
                "canonical_account_order": [local(v, "edges") for v in data["canonical_account_order"]],
                "process_order": policy["process_order"], "order_basis": policy["order_basis"]},
            "source_status": policy["source_status"]})
    _require(at + 1 < len(rows) and len(rows[at]) == len(rows[at + 1]) == 2
             and rows[at][0] == "RECORD" and rows[at + 1][0] == "QUERY", "INPUT_QUERY_SCOPE")
    record = decode(rows[at][1])
    _closed(record, _RECORD_FIELDS - {"query", "supports"}, "INPUT_RECORD_HEADER")
    record["query"], record["supports"] = decode(rows[at + 1][1]), []
    at += 2
    for i, row in enumerate(rows[at:]):
        _require(len(row) == 3 and row[:2] == ["SUPPORT", "S%d" % i], "INPUT_SUPPORT_SCOPE")
        record["supports"].append(decode(row[2]))
    return {"source": public, "record": record}


def _verified(frame):
    _bounded(frame, MAX_FRAME_BYTES)
    _closed(frame, _FRAME_FIELDS, "INPUT_FRAME_FIELDS")
    current = profile()
    _require(frame["schema"] == SCHEMA and frame["profile_digest"] == current["profile_digest"], "INPUT_FRAME_PROFILE")
    _require(frame["frame_digest"] == _digest({k: v for k, v in frame.items() if k != "frame_digest"}),
             "INPUT_FRAME_IDENTITY")
    packet = _restore_text(frame["text"])
    _packet(packet)
    expected = _build(packet, current)
    _require(_canonical(frame) == _canonical(expected), "INPUT_FRAME_RECONSTRUCTION")
    return packet


def restore_packet(frame):
    """Restore the exact canonical source and record bytes or refuse."""
    return deepcopy(_verified(frame))


def validate_frame(frame):
    """Closed syntax and exact reconstruction; no semantic answer checks."""
    _verified(frame)
    return deepcopy(frame)
