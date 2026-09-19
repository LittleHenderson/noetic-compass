"""Pure public-input reader for the pointer study: one focus world, read as a small directed graph.

WHAT THIS MODULE IS. `read_packet(packet)` turns ONE closed public packet into the pointer machine's
whole input, and nothing else. Every fact in the reading comes from the packet; the only thing that comes
from outside is the token ID of a declaration string, and that comes from a process-wide cache built ONCE
(`label_cache(root)`). The reading is plain data (dict/list/int/str/None) so `input_digest` is stable
across runs, processes and machines.

WHAT IS NEVER READ. `supports`, `cue`, `instruction`, `role_catalog`, and every answer, target or
private sidecar. The reader does not even require those keys to exist on the record, so a caller can hand
it a packet that carries none of them (test P10 asserts the reading cannot contain them). The forbidden
substring check in the test is the guard: if a forbidden field ever reaches the reading, the canonical
bytes contain its name and the test fails.

WHAT IS READ, per record (INTERFACE_SPEC_POINTER.md section 2, which is the pinned surface):

* `focus_world` - the focus world as a graph: its nodes with their own raw flags, plus the directed
  `contains` adjacency (parent -> child), sorted.
* `worlds` - `{world_id: graph}` for the focus world, the correspondence target world, and every world a
  world-choice slot lists (definition/context/analogy slots name all 64 bank worlds, slots.py:85-107).
* `query` - `kind` as an 8-way learned id, `rule` as a learned id, and the argument node ids where the
  question names them (`whole`, `part`, `target_world_id`).
* `node_flags` - per node of the focus world: `is_declared_whole`, `is_participant` with rank 1..3,
  `is_primary_label` with rank 1..3, `is_whole_argument`, `is_part_argument`, and (see below) `rank`.
* `excerpt` - `role_set` only: the focal excerpt as a frozen, position-free bag of token ids, sorted.

NODE IDENTITY IS THE REGISTERED RANK, AND NO WORDS. A node is identified everywhere in the reading by its
`rank`, the 0-based index of its ref in the world's sorted ref list. No node label text and no node-label
token id ever appears (resolved 2026-09-19: "node LABEL words are DROPPED from the input" -
`INTERFACE_SPEC_POINTER.md:86-93`), and no bare node ref appears either: the design excludes "any part of a
node's ref beyond the index the rank is derived from" (`DESIGN_DRAFT_v0.2.md:394-398`). The adjacency, the
argument marks and the per-node flags are therefore all expressed as ranks. `slot_readings` recovers a
rank from a slot's coordinate ref by parsing that same `/n<i>` index, and this module REQUIRES, while
reading, that every node's stored index equals its sorted position (measured 244 of 244 nodes today, and
enforced here rather than assumed).

PER WORLD, THE DECLARATION TEXT IS TOKENISED. The definition and context answers are pointers at one of
the 64 bank worlds' declarations, so a world-choice slot is unanswerable unless the candidate worlds'
declaration text is in the input. Each world graph therefore carries `declaration_ids` for the four
declared fields (domain, function, kind, setting) - exactly the 136 distinct declaration strings of the
frozen course - and those ids come from the once-built `label_cache`.

THE RANK FEATURE IS A BRANCH, AND ITS DECISION IS REOPENED. `pointer_contract.DESIGN["node_rank_feature"]`
is read LIVE on every call, and both branches are implemented: with the feature ON every node dict carries
`"rank"`, and with it OFF no node dict carries it (the node list order still fixes canonical serialisation,
and adjacency still refers to nodes by list position, because a list must have an order). The contract's
recorded status is `DESIGN["node_rank_decision_status"]` ==
`"REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A"`: the interface spec registered the feature as
INCLUDED, and HEAD `6cb0b348` REOPENED the decision because a rank-only single-flag rule solves 4 of the 9
eligible held `reach` questions. The reading records which branch produced it in `node_rank_feature`, so
the two readings can never be confused. Flipping the contract constant is the whole change.

NO TEACHER, NO NUMERIC RUNTIME. This module imports no torch, no numpy, no provider, and never calls the
checker. Pure tests run it under the same numeric-import guard as the rest of the study.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import RLock

from . import answers, pointer_contract as contract, practice_contract as practice, source, tokenization

# `canonical` and `require` are the shared pair, so every failure raises `ValueError("TYPED_MATCHED:" + code)`.
require, digest, canonical = source.require, source.digest, source.canonical

# The CNCM root, four levels up from cas_meta2/typed_teaching/ - the same anchor pointer_contract.py uses.
CNCM = Path(__file__).resolve().parents[4]
DEFAULT_ROOT = CNCM

READING_SCHEMA = "cncm.typed-pointer-input/0.1"
CACHE_SCHEMA = "cncm.typed-pointer-label-cache/0.1"

# The 8-way learned kind id: the index of the kind in the course's own kind order (practice_contract.KINDS).
KIND_IDS = tuple(practice.KINDS)
require(len(KIND_IDS) == 8 and len(set(KIND_IDS)) == 8 and set(KIND_IDS) == set(answers.RULES),
        "POINTER_INPUTS_KIND_IDS")
# The learned rule id: the index of the rule name in the sorted union of every kind's admitted rules. The
# reach kind admits TWO rules (`answers.RULES["reach"]`), which is why the id is not a function of the kind:
# swapping `bfs_immediate_predecessor_lexical_v1` for `first_direct_constituent_lexical_v1` changes answers
# (review DG2), so the rule must be an input.
RULE_IDS = tuple(sorted({rule for rules in answers.RULES.values() for rule in rules}))
require(len(RULE_IDS) == 9 and len(set(RULE_IDS)) == len(RULE_IDS)
        and all(rules and set(rules) <= set(RULE_IDS) for rules in answers.RULES.values()),
        "POINTER_INPUTS_RULE_IDS")

# The kinds whose slot plan offers the whole bank as one slot's symbols (slots.py:88-95), so their reading
# must carry every world the slot lists. Everything else names focus-world nodes only, except correspondence,
# whose `mapping_target` slots are scoped to the query's target world (slots.py:96-101).
WORLD_CHOICE_KINDS = ("definition", "context", "analogy")
CORRESPONDENCE = "correspondence"
ROLE_SET = "role_set"
# The four declared fields of a world (`source._facts`, source.py:207-209), in a fixed, sorted order.
DECLARATION_FIELDS = ("domain", "function", "kind", "setting")
# The query arguments that name a node of the focus world (`answers._ARGUMENTS`).
NODE_ARGUMENT_FIELDS = ("part", "whole")
# Slot field -> how its `coordinates` are spent. Only these three forms exist (slots.py:85-107).
ROLE_FIELD = "role"
NODE_COORDINATE_FIELDS = ("edge", "mapping_target", "node", "participant")

# The pinned digest of the once-built cache. `label_cache` fails closed if the cache it just built does not
# reproduce this value, so a course or tokenizer change can never be read as the registered cache.
# Measured at HEAD 607a3f15 over the frozen course: 136 declaration strings, 36 role_set excerpts,
# tokenizer digest 5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798, 3829-token vocabulary.
LABEL_CACHE_DIGEST_PIN = "720cb915ba3961b3855c1df5be13b4f4e12885bd4ac93b24ea0c25645365e481"

_WORD_START = tokenization.WORD_START
_LOCK = RLock()
# Process-wide cache state. `caches` memoises per resolved root so the volatile work happens ONCE;
# `installed` is the record `read_packet` reads token ids from. `builds` and `roots` are the evidence the
# "built once" test reads.
_CACHE_STATE = {"caches": {}, "installed": None, "builds": 0, "roots": []}


def _unit_lookup(vocabulary):
    """The (unit -> token id) map that `tokenization.encode_text` rebuilds on EVERY call.

    `tokenization.py:151` builds this 3571-entry dict per call, by running `_unword` (a hex decode plus a
    re-encode round trip, tokenization.py:56-67) over the whole word vocabulary, at a measured 0.0111 s per
    call. This module builds it ONCE per process and reuses it for every cached and every uncached string.
    """
    require(type(vocabulary) is tuple and len(vocabulary) > _WORD_START + 1, "POINTER_INPUTS_VOCABULARY")
    return {tokenization._unword(token): index
            for index, token in enumerate(vocabulary[_WORD_START:], _WORD_START)}


def _encode_text(text, lookup, max_tokens):
    """`FrameTokenizer.encode_text` with the caller's reusable lookup: identical ids, no per-call rebuild."""
    require(type(text) is str and bool(text), "POINTER_INPUTS_TEXT")
    try:
        raw = text.encode("utf-8")
    except UnicodeError as error:
        raise ValueError("POINTER_INPUTS_TEXT") from error
    require(len(raw) <= tokenization.MAX_TEXT_BYTES, "POINTER_INPUTS_TEXT")
    result = []
    for match in tokenization._UNIT.finditer(text):
        unit = match.group()
        remaining = max_tokens - len(result) - 2
        if unit in lookup:
            require(remaining >= 1, "POINTER_INPUTS_TOKEN_OVERFLOW")
            result.append(lookup[unit])
        else:
            require(len(unit) <= remaining, "POINTER_INPUTS_TOKEN_OVERFLOW")
            encoded = unit.encode("utf-8")
            require(len(encoded) <= remaining, "POINTER_INPUTS_TOKEN_OVERFLOW")
            result.extend(tokenization.BYTE_START + byte for byte in encoded)
    return result


def _cached_ids(text, *, cache, table):
    """The token ids of `text` from the once-built cache, else encoded with the SAME reusable lookup.

    The cache covers the frozen course's 136 declaration strings and its 36 `role_set` excerpts. A packet
    from outside that course - the development panel, whose ten-node worlds are their own authored worlds -
    is still readable: the miss is encoded with the one process-wide lookup, so no call ever rebuilds the
    3,571-entry unit map that `tokenization.py:151` rebuilds per call.
    """
    ids = cache[table].get(text)
    if ids is None:
        ids = _encode_text(text, cache["lookup"], cache["max_tokens"])
    require(type(ids) is list and ids, "POINTER_INPUTS_CACHE_IDS")
    return list(ids)


def _ref_rank(ref):
    """The rank a node ref carries: its own `/n<i>` index, which IS its sorted position (source.py:214)."""
    require(type(ref) is str, "POINTER_INPUTS_NODE_REF")
    head, separator, tail = ref.rpartition("/n")
    require(bool(head) and separator == "/n" and tail.isdigit() and str(int(tail)) == tail,
            "POINTER_INPUTS_NODE_REF")
    return int(tail)


def _node_index(world):
    """`{ref: rank}` for one world, REQUIRING that every stored index equals the sorted position.

    The rank is the node's position among the world's sorted refs - the same list `checker._nodes` and
    `slots.alias_table` sort by (slots.py:55-60). This function proves that invariant for every node it
    returns instead of assuming it, so a bank where the two disagreed would fail closed rather than quietly
    reading a node's ref as its identity.
    """
    require(type(world) is dict and type(world.get("nodes")) is list and world["nodes"],
            "POINTER_INPUTS_WORLD")
    refs = [node["ref"] for node in world["nodes"]]
    require(len(set(refs)) == len(refs), "POINTER_INPUTS_NODE_REF")
    index = {}
    for rank, ref in enumerate(sorted(refs)):
        require(_ref_rank(ref) == rank, "POINTER_INPUTS_NODE_RANK")
        index[ref] = rank
    return index


def _rank_feature():
    """The rank branch, read live from the contract so the open decision stays a one-line change."""
    value = contract.DESIGN["node_rank_feature"]
    require(type(value) is bool, "POINTER_INPUTS_RANK_FEATURE")
    return value


def _world_reading(world, *, focus_world_id, target_world_id, arguments, use_rank, cache):
    """One world as a graph: nodes with their own raw flags, directed `contains`, declaration token ids."""
    index = _node_index(world)
    node_count = len(world["nodes"])
    declarations = world["declarations"]
    require(type(declarations) is dict, "POINTER_INPUTS_DECLARATIONS")
    whole = world["declared_whole"]
    require(whole in index, "POINTER_INPUTS_DECLARED_WHOLE")
    # `is_participant` / `is_primary_label` carry the 1-based rank inside the world's declared list, 0 when
    # the node is not in it (the same shape the leaks lens measured: lb17_pool_gradient.py:51).
    participant_rank = {}
    for position, ref in enumerate(declarations["participants"]):
        require(ref in index, "POINTER_INPUTS_PARTICIPANT")
        participant_rank[index[ref]] = position + 1
    primary_rank = {}
    for position, ref in enumerate(declarations["primary_labels"]):
        require(ref in index, "POINTER_INPUTS_PRIMARY_LABEL")
        primary_rank[index[ref]] = position + 1
    declaration_ids = {}
    for field in DECLARATION_FIELDS:
        text = declarations[field]
        require(type(text) is str and bool(text), "POINTER_INPUTS_DECLARATION")
        declaration_ids[field] = _cached_ids(text, cache=cache, table="declaration_ids")
    contains = []
    for edge in world["contains"]:
        require(edge["source"] in index and edge["target"] in index, "POINTER_INPUTS_CONTAINS")
        contains.append([index[edge["source"]], index[edge["target"]]])
    contains.sort()
    nodes = []
    for rank in range(node_count):
        body = {
            "is_declared_whole": 1 if rank == index[whole] else 0,
            "is_participant": participant_rank.get(rank, 0),
            "is_primary_label": primary_rank.get(rank, 0),
            "is_whole_argument": 1 if arguments.get("whole") == rank else 0,
            "is_part_argument": 1 if arguments.get("part") == rank else 0,
        }
        nodes.append({**({"rank": rank} if use_rank else {}), **body})
    return {
        "world_id": world["world_id"],
        "is_focus": 1 if world["world_id"] == focus_world_id else 0,
        "is_target": 1 if target_world_id is not None and world["world_id"] == target_world_id else 0,
        "node_count": node_count,
        "contains": contains,
        "declaration_ids": declaration_ids,
        "nodes": nodes,
    }


def _build_cache(root):
    """Read the frozen course once and tokenise every declaration string and every `role_set` excerpt.

    Only public course data is touched: the bank's worlds (source.validate_public's own object) and each
    registry row's PUBLIC QUERY. `row["cue"]`, `row["instruction"]` and `row["supports"]` are never
    accessed, and neither is any answer. The reusable lookup is built here and kept, so no later call
    pays the `tokenization.py:151` rebuild.
    """
    frozen, tokenizer, _development = contract.load_material(root)
    lookup = _unit_lookup(tokenizer.vocabulary)
    worlds = frozen["bank"]["worlds"]
    require(type(worlds) is list and worlds, "POINTER_INPUTS_COURSE_WORLDS")
    declaration_ids, excerpt_ids = {}, {}
    for world in worlds:
        declarations = world["declarations"]
        for field in DECLARATION_FIELDS:
            text = declarations[field]
            require(type(text) is str and bool(text), "POINTER_INPUTS_DECLARATION")
            if text not in declaration_ids:
                declaration_ids[text] = _encode_text(text, lookup, tokenizer.max_tokens)
    for row in frozen["registry"]:
        query = row["query"]
        if query["kind"] != ROLE_SET:
            continue
        text = query["arguments"]["focal_excerpt"]
        require(type(text) is str and bool(text), "POINTER_INPUTS_EXCERPT")
        if text not in excerpt_ids:
            excerpt_ids[text] = _encode_text(text, lookup, tokenizer.max_tokens)
    require(declaration_ids and excerpt_ids, "POINTER_INPUTS_CACHE_EMPTY")
    for mapping in (declaration_ids, excerpt_ids):
        for text, ids in mapping.items():
            require(ids and all(type(value) is int and not isinstance(value, bool) for value in ids),
                    "POINTER_INPUTS_CACHE_IDS")
    body = {
        "schema": CACHE_SCHEMA,
        "tokenizer_digest": tokenizer.digest,
        "vocabulary_size": len(tokenizer.vocabulary),
        "word_start": _WORD_START,
        "max_tokens": tokenizer.max_tokens,
        "declaration_count": len(declaration_ids),
        "excerpt_count": len(excerpt_ids),
        "declaration_ids": {text: list(ids) for text, ids in sorted(declaration_ids.items())},
        "excerpt_ids": {text: list(ids) for text, ids in sorted(excerpt_ids.items())},
    }
    public = {**body, "cache_digest": digest(body)}
    return {"public": public, "lookup": lookup, "max_tokens": tokenizer.max_tokens,
            "declaration_ids": public["declaration_ids"], "excerpt_ids": public["excerpt_ids"]}


def label_cache(root):
    """The declaration-string and `role_set`-excerpt token cache, built ONCE per process and pinned.

    Returns a dict of plain data whose own `cache_digest` is exposed, plus `LABEL_CACHE_DIGEST_PIN` as the
    module constant holding the registered value: `label_cache` fails closed with
    `POINTER_INPUTS_CACHE_DIGEST` if the cache it built does not reproduce the pin, so the once-built cache
    can never silently become a different cache. The returned dict is a deep copy, so a caller cannot
    mutate the cached one (the same reason `slots.compile_slots` copies its cache entry, slots.py:178).
    """
    resolved = Path(root).resolve()
    with _LOCK:
        record = _CACHE_STATE["caches"].get(str(resolved))
        if record is None:
            record = _build_cache(resolved)
            if LABEL_CACHE_DIGEST_PIN is not None:
                require(record["public"]["cache_digest"] == LABEL_CACHE_DIGEST_PIN,
                        "POINTER_INPUTS_CACHE_DIGEST")
            _CACHE_STATE["caches"][str(resolved)] = record
            _CACHE_STATE["builds"] += 1
            _CACHE_STATE["roots"].append(str(resolved))
        _CACHE_STATE["installed"] = record
        return deepcopy(record["public"])


def _installed():
    """The record `read_packet` reads token ids from, built once from the default root when nothing is set."""
    with _LOCK:
        record = _CACHE_STATE["installed"]
    if record is None:
        # A caller that goes straight to `read_packet` gets the same once-built cache, from the CNCM root
        # this module lives in, instead of a per-call rebuild.
        label_cache(DEFAULT_ROOT)
        with _LOCK:
            record = _CACHE_STATE["installed"]
    require(record is not None, "POINTER_INPUTS_CACHE_REQUIRED")
    return record


def read_packet(packet):
    """The whole per-record input, read from the public packet ONLY. No answers, ever.

    The packet must carry `source["focus_world_id"]` and `source["worlds"]` (the frozen bank, as
    `course._public` builds it, course.py:86-87) and `record["query"]`. It is NOT required to carry
    `supports`, `cue`, `instruction`, `role_catalog` or any answer: this reader reads only the keys it
    needs, so a caller can prove the exclusion by handing it a packet that does not have them at all.
    """
    cache = _installed()
    use_rank = _rank_feature()
    require(type(packet) is dict, "POINTER_INPUTS_PACKET")
    public, record = packet.get("source"), packet.get("record")
    require(type(public) is dict and type(record) is dict, "POINTER_INPUTS_PACKET")
    require("focus_world_id" in public and type(public["focus_world_id"]) is str, "POINTER_INPUTS_FOCUS")
    require(type(public.get("worlds")) is list and public["worlds"], "POINTER_INPUTS_WORLDS")
    query = record.get("query")
    require(type(query) is dict, "POINTER_INPUTS_QUERY")
    require(type(record.get("record_id")) is str and type(query.get("query_id")) is str,
            "POINTER_INPUTS_IDENTITY")
    focus_world_id = public["focus_world_id"]
    require(query.get("focus_world_id") == focus_world_id, "POINTER_INPUTS_FOCUS")
    kind, rule = query.get("kind"), query.get("rule")
    require(kind in KIND_IDS, "POINTER_INPUTS_KIND")
    require(rule in answers.RULES[kind], "POINTER_INPUTS_RULE")
    arguments = query.get("arguments")
    require(type(arguments) is dict, "POINTER_INPUTS_ARGUMENTS")

    by_id = {}
    for world in public["worlds"]:
        require(type(world) is dict and type(world.get("world_id")) is str, "POINTER_INPUTS_WORLDS")
        require(world["world_id"] not in by_id, "POINTER_INPUTS_WORLDS")
        by_id[world["world_id"]] = world
    require(focus_world_id in by_id, "POINTER_INPUTS_FOCUS")
    target_world_id = arguments.get("target_world_id") if kind == CORRESPONDENCE else None
    if target_world_id is not None:
        require(type(target_world_id) is str and target_world_id in by_id, "POINTER_INPUTS_TARGET_WORLD")

    focus_index = _node_index(by_id[focus_world_id])
    marks = {}
    for field in NODE_ARGUMENT_FIELDS:
        value = arguments.get(field)
        require(value is None or (type(value) is str and value in focus_index),
                "POINTER_INPUTS_ARGUMENT_NODE")
        marks[field] = None if value is None else focus_index[value]

    if kind in WORLD_CHOICE_KINDS:
        keep = sorted(by_id)
    else:
        keep = sorted({focus_world_id} | ({target_world_id} if target_world_id is not None else set()))
    graphs = {}
    for world_id in keep:
        graphs[world_id] = _world_reading(by_id[world_id], focus_world_id=focus_world_id,
                                          target_world_id=target_world_id, arguments=marks,
                                          use_rank=use_rank, cache=cache)

    excerpt = []
    if kind == ROLE_SET:
        text = arguments.get("focal_excerpt")
        require(type(text) is str and bool(text), "POINTER_INPUTS_EXCERPT")
        # The bag is position-free: sorted, so the same excerpt always gives the same bytes.
        excerpt = sorted(_cached_ids(text, cache=cache, table="excerpt_ids"))

    return {
        "schema": READING_SCHEMA,
        "record_id": record["record_id"],
        "query_id": query["query_id"],
        "focus_world_id": focus_world_id,
        "node_rank_feature": 1 if use_rank else 0,
        "query": {
            "kind": KIND_IDS.index(kind),
            "kind_name": kind,
            "rule": RULE_IDS.index(rule),
            "rule_name": rule,
            "whole": marks["whole"],
            "part": marks["part"],
            "target_world_id": target_world_id,
            "world_count": len(keep),
        },
        "focus_world": deepcopy(graphs[focus_world_id]),
        "worlds": graphs,
        "node_flags": deepcopy(graphs[focus_world_id]["nodes"]),
        "excerpt": excerpt,
    }


def input_digest(reading):
    """SHA-256 over the canonical reading: the same packet gives the same digest in any process."""
    require(type(reading) is dict and reading.get("schema") == READING_SCHEMA, "POINTER_INPUTS_READING")
    return digest(reading)


def slot_readings(reading, slots):
    """One reading per slot of the EXISTING slot plan, in slot order.

    `slots` is the plan's `slots` list (`slots.compile_slots(packet)["slots"]`, slots.py:103-108) or the
    plan dict itself. Each entry names the slot, the world the slot is scoped to
    (`scope_world_id` / `scope_alias`), the node ranks its `coordinates` point at, those nodes' own raw
    flags, and the size of the slot's declared symbol list. The slot's own coordinate REFS are never
    copied into the reading: they are spent to recover ranks, and only ranks come out.
    """
    require(type(reading) is dict and reading.get("schema") == READING_SCHEMA, "POINTER_INPUTS_READING")
    plan_slots = slots.get("slots") if type(slots) is dict else slots
    require(type(plan_slots) is list and plan_slots, "POINTER_INPUTS_SLOTS")
    graphs = reading["worlds"]
    rows = []
    for slot in plan_slots:
        require(type(slot) is dict, "POINTER_INPUTS_SLOT")
        require(all(key in slot for key in ("slot_id", "field", "group", "coordinates", "scope_world_id",
                                            "symbols")), "POINTER_INPUTS_SLOT")
        world_id, coordinates = slot["scope_world_id"], slot["coordinates"]
        graph = graphs.get(world_id)
        require(graph is not None, "POINTER_INPUTS_SLOT_WORLD")
        require(type(coordinates) is list and type(slot["symbols"]) is list and slot["symbols"],
                "POINTER_INPUTS_SLOT_COORDINATES")
        role_ids, node_ranks = [], []
        if slot["field"] == ROLE_FIELD:
            require(len(coordinates) == 1 and type(coordinates[0]) is int
                    and not isinstance(coordinates[0], bool), "POINTER_INPUTS_SLOT_COORDINATES")
            role_ids = [coordinates[0]]
        elif slot["field"] in NODE_COORDINATE_FIELDS:
            require(coordinates, "POINTER_INPUTS_SLOT_COORDINATES")
            node_ranks = [_ref_rank(ref) for ref in coordinates]
            require(all(0 <= rank < graph["node_count"] for rank in node_ranks),
                    "POINTER_INPUTS_SLOT_RANK")
        else:
            require(coordinates == [], "POINTER_INPUTS_SLOT_COORDINATES")
        rows.append({
            "slot_id": slot["slot_id"],
            "field": slot["field"],
            "group": slot["group"],
            "world_id": world_id,
            "is_target_world": graph["is_target"],
            "role_ids": role_ids,
            "node_ranks": node_ranks,
            "nodes": [deepcopy(graph["nodes"][rank]) for rank in node_ranks],
            "symbol_count": len(slot["symbols"]),
        })
    require(len({row["slot_id"] for row in rows}) == len(rows), "POINTER_INPUTS_SLOT_IDENTITY")
    return rows
