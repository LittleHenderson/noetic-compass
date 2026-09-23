"""Stage 2 fixed-slot syntax with the original complete-assignment decoder.

Existing supported packets delegate to slots.py and preserve exact plan bytes.
Only larger correspondence packets use the new explicit slot profile.

This defines syntax, aliases and scalar score assembly only. Numerical rows,
core execution, loss, CUDA behavior and learned competence remain unverified.
Incorrect but well-formed answers stay available in every public universe.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from threading import RLock

from . import answers_v2 as answers
from . import course, source, slots as previous

PLAN_SCHEMA = "cas.typed-teaching-slot-plan/0.2"
DECISION_SCHEMA = "cas.typed-teaching-slot-decisions/0.1"
PROFILE_SCHEMA = "cas.typed-teaching-slot-profile/0.2"
SYMBOLS = ("PRESENT", "ABSENT", "DIRECT", "NO_MATCH", "MAPPING") + tuple(
    "N%d" % i for i in range(10)) + tuple("VIA_N%d" % i for i in range(10)) + tuple(
    "W%d" % i for i in range(65))
MAX_ABS_SCORE = 1000000
MAX_CACHE_ENTRIES = 32
MAX_CACHE_SERIALIZED_BYTES = 16 * 1024 ** 2
DECISION_CONTRACT = {
    "independent": "argmax over each slot's declared symbol order; first wins exact ties",
    "correspondence": "NO_MATCH log probability = logsoftmax(mode)[NO_MATCH]; mapping log probability = logsoftmax(mode)[MAPPING] + sum(assigned node logits) - logsumexp(sum(assigned node logits) over ALL syntactic bijections)",
    "correspondence_forced": "No syntactic bijections: NO_MATCH log probability 0; report forced decision",
    "candidate_order": "NO_MATCH first; then all target-ref permutations in lexical order against lexical source refs",
    "candidate_ties": "first candidate wins exact scalar ties",
    "score_scalar": "finite exact Python int or float, excluding bool; absolute value <= 1000000",
    "loss_contract": "field mean, then task mean, then batch mean; correspondence is ONE whole-candidate valid-set field, not node marginals; membership binary loss and private valid-set loss are worker work, not implemented here",
    "semantic_repair": False,
}
require, digest, canonical = source.require, source.digest, source.canonical


def profile():
    """On-disk syntax contract, not worker/readout/checkpoint attestation."""
    raw = Path(__file__).read_bytes()
    body = {"schema": PROFILE_SCHEMA, "symbols": list(SYMBOLS), "symbol_count": len(SYMBOLS),
        "world_alias": "W0..W64 by sorted exact public world_id",
        "node_alias": "N0..N9 by sorted exact node.ref within each world; node aliases are always scoped",
        "maximum_slots": 100, "correspondence_max_nodes": 6, "readout_width_proposed": 64,
        "decision_contract": deepcopy(DECISION_CONTRACT),
        "source_files": [{"path": "cas_meta2/typed_teaching/slots_v2.py", "bytes": len(raw), "sha256": sha256(raw).hexdigest()},
            {"path": "cas_meta2/typed_teaching/answers_v2.py", "bytes": len(Path(answers.__file__).read_bytes()),
             "sha256": sha256(Path(answers.__file__).read_bytes()).hexdigest()}],
        "compatibility_dispatch": "ORIGINAL_PLAN_FOR_NON_CORRESPONDENCE_OR_AT_MOST_FOUR_NODES",
        "previous_slot_profile": previous.profile(),
        "course_profile": course.profile(),
        "status": "PURE_SLOT_CONTRACT_NO_NUMERIC_OR_LEARNING_ACCEPTANCE"}
    return {**body, "profile_digest": digest(body)}


def alias_table(public):
    source.validate_public(public)
    return {"worlds": [{"alias": "W%d" % i, "world_id": world["world_id"],
        "nodes": [{"alias": "N%d" % j, "ref": ref}
                  for j, ref in enumerate(sorted(node["ref"] for node in world["nodes"]))]}
        for i, world in enumerate(sorted(public["worlds"], key=lambda row: row["world_id"]))]}


def _compile_slots_uncached(packet):
    """Compile all syntactic slots from the closed learner-visible packet."""
    checked = course.validate_model_packet(packet)
    public, record = checked["source"], checked["record"]
    query = record["query"]
    inv = answers.answer_space(public, query)["inventory"]
    aliases = alias_table(public)
    world_by_id = {row["world_id"]: row for row in aliases["worlds"]}
    world_alias = {key: row["alias"] for key, row in world_by_id.items()}
    node_alias = {node["ref"]: node["alias"] for row in aliases["worlds"] for node in row["nodes"]}
    focus, kind = query["focus_world_id"], query["kind"]
    target = query["arguments"].get("target_world_id") if kind == "correspondence" else None
    packet_digest = digest(checked)
    slots = []
    def add(field, group, coordinates, symbols, *, scope_world=None):
        scope = focus if scope_world is None else scope_world
        body = {"field": field, "group": group, "coordinates": coordinates,
                "scope_world_id": scope, "scope_alias": world_alias[scope],
                "symbols": list(symbols)}
        require(body["symbols"] and len(set(body["symbols"])) == len(body["symbols"])
                and set(body["symbols"]) <= set(SYMBOLS), "TYPED_SLOT_SYMBOLS")
        slots.append({"slot_id": "typed-slot-" + digest({"packet_digest": packet_digest, **body}), **body})
    if kind == "role_set":
        for role in inv["role_ids"]: add("role", "roles", [role], ("ABSENT", "PRESENT"))
    elif kind == "definition":
        add("whole", "whole", [], [node_alias[ref] for ref in inv["whole_refs"]])
        for field in ("kind_ref", "function_ref"):
            add(field, field, [], [row["alias"] for row in aliases["worlds"]])
    elif kind == "context":
        add("setting_ref", "setting_ref", [], [row["alias"] for row in aliases["worlds"]])
        for ref in inv["participant_refs"]: add("participant", "participants", [ref], ("ABSENT", "PRESENT"))
    elif kind == "analogy":
        add("world_id", "world_id", [], ["NO_MATCH", *(world_alias[ref] for ref in inv["world_ids"])])
    elif kind == "correspondence":
        # Public grammar alone bounds enumeration; no graph edge is examined.
        candidates = answers.correspondence_candidates(public, query)
        add("mode", "correspondence", [], ("NO_MATCH", "MAPPING"))
        for ref in sorted(inv["source_nodes"]):
            add("mapping_target", "correspondence", [ref], [node_alias[v] for v in sorted(inv["target_nodes"])], scope_world=target)
    elif kind == "parts":
        for ref in inv["node_refs"]: add("node", "nodes", [ref], ("ABSENT", "PRESENT"))
    elif kind == "edge_account":
        for pair in inv["edge_pairs"]: add("edge", "edges", list(pair), ("ABSENT", "PRESENT"))
    elif kind == "reach":
        add("reach", "reach", [], ["ABSENT", "DIRECT", *("VIA_" + node_alias[ref] for ref in inv["via_refs"])])
    require(0 < len(slots) <= 100 and len({row["slot_id"] for row in slots}) == len(slots), "TYPED_SLOT_BOUND")
    candidate_rows = []
    if kind == "correspondence":
        for value in candidates:
            candidate_rows.append({"candidate_id": "typed-candidate-" + digest({"query_id": query["query_id"], "value": value}),
                                   "value": value})
    body = {"schema": PLAN_SCHEMA, "record_id": record["record_id"], "query_id": query["query_id"],
        "source_digest": record["source_digest"], "packet_digest": packet_digest, "kind": kind,
        "profile": profile(), "aliases": aliases, "slots": slots, "correspondence_candidates": candidate_rows,
        "decision_contract": deepcopy(DECISION_CONTRACT),
        "forced_candidate_count": 1 if kind == "correspondence" and len(candidate_rows) == 1 else 0}
    return {**body, "plan_digest": digest(body)}


def _packet_bytes(packet):
    # Match the public input-frame envelope, without imposing source-declaration
    # text limits on role excerpts (which may contain up to 16384 UTF-8 bytes).
    # The uncached compiler still applies every field-specific syntax check.
    count, active = 0, set()
    def walk(value, depth):
        nonlocal count
        count += 1
        require(count <= 250000 and depth <= 32, "TYPED_SLOT_CACHE_TREE_BOUND")
        require(type(value) in (dict, list, str, int, bool, type(None)), "TYPED_SLOT_CACHE_JSON_TYPE")
        if type(value) in (dict, list):
            require(id(value) not in active, "TYPED_SLOT_CACHE_CYCLE")
            active.add(id(value))
            if type(value) is dict:
                require(all(type(key) is str for key in value), "TYPED_SLOT_CACHE_JSON_KEY")
            for item in (value.values() if type(value) is dict else value):
                walk(item, depth + 1)
            active.remove(id(value))
        elif type(value) is str:
            require(len(value.encode("utf-8")) <= 8 * 1024 ** 2, "TYPED_SLOT_CACHE_STRING_BOUND")
    walk(packet, 0)
    raw = canonical(packet).encode()
    require(len(raw) <= 8 * 1024 ** 2, "TYPED_SLOT_CACHE_PACKET_BOUND")
    return raw


class _SlotCache:
    """Bound complete admitted plans, with no semantic/private dependency.

    The byte bound counts retained canonical packet/profile/plan bytes. It is
    not a Python heap/RSS cap. An oversized entry compiles without retention.
    All profile identities remain on-disk metadata; loaded-source attestation
    is still the worker's responsibility.
    """
    def __init__(self, *, max_entries=MAX_CACHE_ENTRIES, max_serialized_bytes=MAX_CACHE_SERIALIZED_BYTES):
        require(type(max_entries) is int and 1 <= max_entries <= MAX_CACHE_ENTRIES,
                "TYPED_SLOT_CACHE_ENTRY_BOUND")
        require(type(max_serialized_bytes) is int and 1 <= max_serialized_bytes <= MAX_CACHE_SERIALIZED_BYTES,
                "TYPED_SLOT_CACHE_BYTE_BOUND")
        self.max_entries, self.max_bytes = max_entries, max_serialized_bytes
        self.entries, self.serialized_bytes = OrderedDict(), 0
        self.hits = self.misses = self.compiles = self.evictions = self.bypasses = 0
        self.lock = RLock()

    def compile(self, packet):
        # Reject tuples/custom types/cycles/deep/oversize trees before JSON key
        # construction; e.g. a tuple must not alias an already admitted list.
        raw = _packet_bytes(packet)
        profile_raw = canonical(profile()).encode()
        key = (sha256(raw).digest(), sha256(profile_raw).digest())
        with self.lock:
            if key in self.entries:
                saved_raw, saved_profile, plan, _ = self.entries[key]
                require(saved_raw == raw and saved_profile == profile_raw, "TYPED_SLOT_CACHE_COLLISION")
                self.hits += 1
                self.entries.move_to_end(key)
                return deepcopy(plan)
            self.misses += 1
            self.compiles += 1
        # The admitted snapshot cannot later be mutated by the caller. Failed
        # compilation is never cached. Neither record_id nor a subset is a key.
        plan = _compile_slots_uncached(json.loads(raw))
        require(canonical(plan["profile"]).encode() == profile_raw
                and canonical(profile()).encode() == profile_raw
                and plan["packet_digest"] == sha256(raw).hexdigest(), "TYPED_SLOT_CACHE_CONTEXT_CHANGED")
        size = len(raw) + len(profile_raw) + len(canonical(plan).encode())
        with self.lock:
            if size > self.max_bytes:
                self.bypasses += 1
                return deepcopy(plan)
            if key in self.entries:
                self.serialized_bytes -= self.entries.pop(key)[3]
            while self.entries and (len(self.entries) >= self.max_entries or self.serialized_bytes + size > self.max_bytes):
                self.serialized_bytes -= self.entries.popitem(last=False)[1][3]
                self.evictions += 1
            self.entries[key] = (raw, profile_raw, deepcopy(plan), size)
            self.serialized_bytes += size
            return deepcopy(plan)

    def info(self):
        with self.lock:
            return {"hits": self.hits, "misses": self.misses, "compiles": self.compiles,
                "evictions": self.evictions, "oversize_bypasses": self.bypasses,
                "entries": len(self.entries), "retained_serialized_bytes": self.serialized_bytes,
                "max_entries": self.max_entries, "max_retained_serialized_bytes": self.max_bytes}

    def clear(self):
        with self.lock:
            self.entries.clear()
            self.serialized_bytes = 0
            self.hits = self.misses = self.compiles = self.evictions = self.bypasses = 0


_SLOT_CACHE = _SlotCache()


def compile_slots(packet):
    """Preserve old plan bytes; explicitly version larger correspondence plans."""
    # Validate the full packet before inspecting it. No semantic checker is called.
    checked = course.validate_model_packet(packet)
    query = checked["record"]["query"]
    if query["kind"] != "correspondence":
        return previous.compile_slots(checked)
    inventory = answers.answer_space(checked["source"], query)["inventory"]
    if max(len(inventory["source_nodes"]), len(inventory["target_nodes"])) <= 4:
        return previous.compile_slots(checked)
    return _SLOT_CACHE.compile(checked)


def slot_cache_info():
    return _SLOT_CACHE.info()


def clear_slot_cache():
    _SLOT_CACHE.clear()


def validate_plan(packet, plan):
    source._bounded(plan)
    expected = compile_slots(packet)
    require(canonical(plan) == canonical(expected), "TYPED_SLOT_PLAN_RECONSTRUCTION")
    return deepcopy(expected)


def _decision(plan, selected, candidate=None):
    return {"schema": DECISION_SCHEMA, "record_id": plan["record_id"], "query_id": plan["query_id"],
            "plan_digest": plan["plan_digest"], "selected": selected, "correspondence_candidate_id": candidate}


def _check_scores(plan, scores):
    require(type(scores) is dict and set(scores) == {slot["slot_id"] for slot in plan["slots"]}, "TYPED_SLOT_SCORE_FIELDS")
    for slot in plan["slots"]:
        row = scores[slot["slot_id"]]
        require(type(row) is dict and set(row) == set(slot["symbols"]), "TYPED_SLOT_SCORE_SYMBOLS")
        require(all(type(value) in (int, float) and abs(value) <= MAX_ABS_SCORE and math.isfinite(value)
                    for value in row.values()), "TYPED_SLOT_SCORE_SCALAR")


def _logsumexp(values):
    maximum = max(values)
    result = maximum + math.log(sum(math.exp(value - maximum) for value in values))
    require(math.isfinite(result), "TYPED_SLOT_NONFINITE_SCORE_RESULT")
    return result


def _candidate_scores(plan, scores):
    require(plan["kind"] == "correspondence", "TYPED_SLOT_CANDIDATE_SCORE_KIND")
    mode = scores[plan["slots"][0]["slot_id"]]
    by_ref = {slot["coordinates"][0]: slot for slot in plan["slots"][1:]}
    alias = {node["ref"]: node["alias"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    candidates = plan["correspondence_candidates"]
    if len(candidates) == 1:
        return [{"candidate_id": candidates[0]["candidate_id"], "log_probability": 0.0}]
    raw = [sum(scores[by_ref[pair["source"]]["slot_id"]][alias[pair["target"]]] for pair in row["value"]["pairs"])
           for row in candidates[1:]]
    require(all(math.isfinite(value) for value in raw), "TYPED_SLOT_NONFINITE_SCORE_RESULT")
    mode_normalizer, mapping_normalizer = _logsumexp(list(mode.values())), _logsumexp(raw)
    values = [mode["NO_MATCH"] - mode_normalizer] + [mode["MAPPING"] - mode_normalizer + value - mapping_normalizer for value in raw]
    require(all(math.isfinite(value) for value in values), "TYPED_SLOT_NONFINITE_SCORE_RESULT")
    return [{"candidate_id": row["candidate_id"], "log_probability": value} for row, value in zip(candidates, values)]


def candidate_scores(packet, scores):
    """Normalized public correspondence distribution; never a correct-set mask."""
    plan = compile_slots(packet)
    _check_scores(plan, scores)
    return _candidate_scores(plan, scores)


def score_decisions(packet, scores):
    """Deterministic scalar reference decoder, with no numeric package or teacher.

    Scores cover every slot/symbol exactly. Hierarchical correspondence scoring
    normalizes over ALL syntactic bijections. Joint MAP includes the declared
    mapping-cardinality prior; it is not a mode-first decoder or a truth check.
    """
    plan = compile_slots(packet)
    _check_scores(plan, scores)
    if plan["kind"] != "correspondence":
        return _decision(plan, {slot["slot_id"]: max(slot["symbols"], key=lambda symbol: scores[slot["slot_id"]][symbol])
                                for slot in plan["slots"]})
    winner = max(_candidate_scores(plan, scores), key=lambda row: row["log_probability"])
    return _decision(plan, {}, winner["candidate_id"])


def assemble_answer(packet, decisions):
    """Assemble caller decisions, validating syntax without graph repair."""
    plan = compile_slots(packet)
    source._bounded(decisions)
    fields = {"schema", "record_id", "query_id", "plan_digest", "selected", "correspondence_candidate_id"}
    require(type(decisions) is dict and set(decisions) == fields, "TYPED_SLOT_DECISION_FIELDS")
    require(decisions["schema"] == DECISION_SCHEMA and decisions["record_id"] == plan["record_id"]
            and decisions["query_id"] == plan["query_id"] and decisions["plan_digest"] == plan["plan_digest"],
            "TYPED_SLOT_DECISION_BINDING")
    selected = decisions["selected"]
    require(type(selected) is dict, "TYPED_SLOT_SELECTION_TYPE")
    if plan["kind"] == "correspondence":
        require(selected == {} and type(decisions["correspondence_candidate_id"]) is str, "TYPED_SLOT_MAPPING_SELECTION")
        row = next((row for row in plan["correspondence_candidates"]
                    if row["candidate_id"] == decisions["correspondence_candidate_id"]), None)
        require(row is not None, "TYPED_SLOT_UNKNOWN_CANDIDATE")
        value = deepcopy(row["value"])
    else:
        require(decisions["correspondence_candidate_id"] is None
                and set(selected) == {slot["slot_id"] for slot in plan["slots"]}, "TYPED_SLOT_SELECTION_COVERAGE")
        require(all(type(selected[slot["slot_id"]]) is str and selected[slot["slot_id"]] in slot["symbols"]
                    for slot in plan["slots"]), "TYPED_SLOT_SELECTION_SYMBOL")
        worlds = {world["alias"]: world for world in plan["aliases"]["worlds"]}
        focus = next(world for world in worlds.values() if world["world_id"] == packet["record"]["source_world_id"])
        nodes = {node["alias"]: node["ref"] for node in focus["nodes"]}
        picked = [(slot, selected[slot["slot_id"]]) for slot in plan["slots"]]
        fields = {slot["field"]: symbol for slot, symbol in picked}
        kind = plan["kind"]
        if kind == "role_set":
            roles = sorted(slot["coordinates"][0] for slot, symbol in picked if symbol == "PRESENT")
            value = {"roles": roles, "status": "INSUFFICIENT" if not roles else "UNIQUE" if len(roles) == 1 else "AMBIGUOUS"}
        elif kind == "definition":
            value = {"whole": nodes[fields["whole"]], **{field: answers.declaration_ref(worlds[fields[field]]["world_id"], declaration)
                      for field, declaration in (("kind_ref", "kind"), ("function_ref", "function"))}}
        elif kind == "context":
            value = {"setting_ref": answers.declaration_ref(worlds[fields["setting_ref"]]["world_id"], "setting"),
                     "participants": sorted(slot["coordinates"][0] for slot, symbol in picked
                                            if slot["field"] == "participant" and symbol == "PRESENT")}
        elif kind == "analogy":
            value = {"world_id": None if fields["world_id"] == "NO_MATCH" else worlds[fields["world_id"]]["world_id"]}
        elif kind == "parts":
            value = {"nodes": sorted(slot["coordinates"][0] for slot, symbol in picked if symbol == "PRESENT")}
        elif kind == "edge_account":
            pairs = sorted(slot["coordinates"] for slot, symbol in picked if symbol == "PRESENT")
            value = {"edges": [{"source": a, "target": b} for a, b in pairs]}
        elif kind == "reach":
            symbol = fields["reach"]
            value = {"state": "VIA" if symbol.startswith("VIA_") else symbol,
                     "via": nodes[symbol[4:]] if symbol.startswith("VIA_") else None}
    return answers.make_answer(packet["source"], packet["record"]["query"], value)
