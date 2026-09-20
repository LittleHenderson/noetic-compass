"""Pure exact scoped token-binding recipes; no numerical runtime is imported.

Every token of the reversible frame text, each LF separator, and both sequence
markers belongs to exactly one row. Scope, row ordinal, and token position are
inside each signed-permutation hash domain. Unequal binding maps remove forced
symmetries; they do not prove collision-free finite-dimensional projections.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

from . import input_frames, slots, source, tokenization

SCHEMA = "cas.typed-teaching-scoped-binding/0.1"
PROFILE_SCHEMA = "cas.typed-teaching-scoped-binding-profile/0.1"
ALGORITHM = "sha256-stream-fisher-yates-signed-scope-position/1"
ROW_ALGORITHM = "sha256-rademacher-float32le-64/1"
DIMENSION = 64
MAX_ROWS = 142
MAX_INSPECTION_TOKENS = 128
_PLAN_FIELDS = {"schema", "profile", "packet_digest", "frame_digest", "tokenizer_digest",
                "sequence_digest", "seed", "d_model", "rows", "plan_digest"}
_ROW_FIELDS = {"ordinal", "scope", "start", "count", "token_ids"}


class BindingError(ValueError):
    pass


def _require(value, reason):
    if not value:
        raise BindingError(reason)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise BindingError("TYPED_BINDING_JSON") from exc


def _digest(value):
    return sha256(_canonical(value).encode()).hexdigest()


def validate_config(seed, d_model):
    _require(type(seed) is int and 0 <= seed < 2**63, "TYPED_BINDING_SEED")
    _require(type(d_model) is int and d_model == DIMENSION, "TYPED_BINDING_DIMENSION")


def profile():
    raw = Path(__file__).read_bytes()
    body = {"schema": PROFILE_SCHEMA, "algorithm": ALGORITHM, "row_algorithm": ROW_ALGORITHM,
            "source": {"path": "cas_meta2/typed_teaching/binding.py", "bytes": len(raw), "sha256": sha256(raw).hexdigest()},
            "tokenizer_profile": tokenization.profile(), "slot_profile": slots.profile(),
            "d_model": DIMENSION, "max_rows": MAX_ROWS,
            "scope": "START; each complete JSON line with following LF; END",
            "permutation_domain": ["algorithm", "seed", "scope", "ordinal", "position", "d_model"],
            "row_scaling": "sum(bound token rows)/sqrt(token count); unit L2; reject zero/nonfinite",
            "packet_scaling": "sum(unit row vectors)/sqrt(row count); unit L2; reject zero/nonfinite",
            "slot_scaling": "(unit packet + unit public slot query)/sqrt(2); unit L2; reject zero/nonfinite",
            "frozen_row_values": "64 float32LE entries, each -1/8 or +1/8",
            "row_domains": ["token with exact vocabulary entry", "readout with exact symbol", "query with exact public field scope"],
            "numeric_acceptance": False, "collision_free_claim": False}
    return {**body, "profile_digest": _digest(body)}


def _scope(scope):
    _require(type(scope) in (list, tuple) and 1 <= len(scope) <= 2
             and all(type(v) is str for v in scope), "TYPED_BINDING_SCOPE")
    if len(scope) == 1:
        _require(scope[0] in {"START", "END", "FORMAT", "BINDINGS", "ALIASES", "SOURCE", "RECORD", "QUERY"},
                 "TYPED_BINDING_SCOPE")
    else:
        tag, local = scope
        pattern = {"POLICY": r"P(?:[0-9]|[1-5][0-9]|6[0-4])", "WORLD": r"W(?:[0-9]|[1-5][0-9]|6[0-4])",
                   "SUPPORT": r"S[0-2]"}.get(tag)
        _require(pattern is not None and re.fullmatch(pattern, local) is not None, "TYPED_BINDING_SCOPE")
    return tuple(scope)


def _coordinates(seed, scope, ordinal, position, d_model):
    validate_config(seed, d_model)
    result = _scope(scope)
    _require(type(ordinal) is int and 0 <= ordinal < MAX_ROWS, "TYPED_BINDING_ORDINAL")
    _require(type(position) is int and 0 <= position < tokenization.HARD_MAX_TOKENS, "TYPED_BINDING_POSITION")
    return result


def _stream(domain):
    prefix = _canonical(domain).encode()
    counter = 0
    while True:
        block = sha256(prefix + b"\x00" + counter.to_bytes(8, "little")).digest()
        yield from struct.unpack("<8I", block)
        counter += 1


@lru_cache(maxsize=131072)
def _permutation(seed, scope, ordinal, position, d_model):
    numbers = _stream([ALGORITHM, seed, list(scope), ordinal, position, d_model])
    order = list(range(d_model))
    for at in range(d_model - 1, 0, -1):
        limit = at + 1
        ceiling = 2**32 - (2**32 % limit)
        value = next(numbers)
        while value >= ceiling:
            value = next(numbers)
        selected = value % limit
        order[at], order[selected] = order[selected], order[at]
    bits = next(numbers) | (next(numbers) << 32)
    return tuple(order), tuple(1 if (bits >> i) & 1 else -1 for i in range(d_model))


def signed_permutation(*, seed, scope, ordinal, position, d_model=DIMENSION):
    scope = _coordinates(seed, scope, ordinal, position, d_model)
    return _permutation(seed, scope, ordinal, position, d_model)


def _validate_row(row):
    _require(type(row) is dict and set(row) == _ROW_FIELDS, "TYPED_BINDING_ROW_FIELDS")
    _coordinates(0, row["scope"], row["ordinal"], 0, DIMENSION)
    _require(type(row["start"]) is int and row["start"] >= 0 and type(row["count"]) is int
             and 0 < row["count"] <= tokenization.HARD_MAX_TOKENS, "TYPED_BINDING_ROW_BOUND")
    _require(type(row["token_ids"]) is list and len(row["token_ids"]) == row["count"]
             and all(type(v) is int and 0 <= v < tokenization.WORD_START + tokenization.MAX_UNITS
                     for v in row["token_ids"]), "TYPED_BINDING_TOKEN_IDS")


def compile_packet(packet, tokenizer, *, seed, d_model=DIMENSION):
    validate_config(seed, d_model)
    _require(type(tokenizer) is tokenization.FrameTokenizer, "TYPED_BINDING_TOKENIZER_TYPE")
    frame = input_frames.compile_packet(packet)
    sequence = tokenizer.encode_frame(frame)
    ids = sequence["ids"]
    vocabulary = {bytes.fromhex(v[6:-1]).decode("utf-8") for v in tokenizer.vocabulary[tokenization.WORD_START:]}
    rows, cursor = [], 0
    def append(scope, count):
        nonlocal cursor
        rows.append({"ordinal": len(rows), "scope": list(scope), "start": cursor,
                     "count": count, "token_ids": ids[cursor:cursor + count]})
        cursor += count
    append(["START"], 1)
    lines = frame["text"].split("\n")
    pattern = re.compile(tokenization.UNIT_RULE, re.UNICODE)
    for at, line in enumerate(lines):
        parsed = json.loads(line)
        scope = parsed[:2] if parsed[0] in {"POLICY", "WORLD", "SUPPORT"} else parsed[:1]
        _scope(scope)
        fragment = line + ("\n" if at + 1 < len(lines) else "")
        count = sum(1 if match.group() in vocabulary else len(match.group().encode("utf-8"))
                    for match in pattern.finditer(fragment))
        append(scope, count)
        _require(tokenizer.decode_text(rows[-1]["token_ids"]) == fragment, "TYPED_BINDING_ROW_TEXT")
    append(["END"], 1)
    _require(len(rows) <= MAX_ROWS and cursor == len(ids)
             and [token for row in rows for token in row["token_ids"]] == ids,
             "TYPED_BINDING_COMPLETE_SEQUENCE")
    _require(rows[0]["token_ids"] == [tokenization.START] and rows[-1]["token_ids"] == [tokenization.END],
             "TYPED_BINDING_MARKERS")
    for row in rows:
        _validate_row(row)
    body = {"schema": SCHEMA, "profile": profile(), "packet_digest": _digest(packet),
            "frame_digest": _digest(frame), "tokenizer_digest": tokenizer.digest,
            "sequence_digest": sequence["sequence_digest"], "seed": seed, "d_model": d_model, "rows": rows}
    return {**body, "plan_digest": _digest(body)}


def validate_plan(packet, tokenizer, plan):
    _require(type(plan) is dict and set(plan) == _PLAN_FIELDS, "TYPED_BINDING_PLAN_FIELDS")
    expected = compile_packet(packet, tokenizer, seed=plan["seed"], d_model=plan["d_model"])
    _require(_canonical(plan) == _canonical(expected), "TYPED_BINDING_PLAN_RECONSTRUCTION")
    return deepcopy(expected)


def linear_terms(row, *, seed, d_model=DIMENSION):
    """Bounded exact integer diagnostic, before floating scaling/normalization."""
    validate_config(seed, d_model)
    _validate_row(row)
    _require(row["count"] <= MAX_INSPECTION_TOKENS, "TYPED_BINDING_INSPECTION_BOUND")
    result = [dict() for _ in range(d_model)]
    for position, token in enumerate(row["token_ids"]):
        order, signs = signed_permutation(seed=seed, scope=row["scope"], ordinal=row["ordinal"],
                                          position=position, d_model=d_model)
        for dest, (origin, sign) in enumerate(zip(order, signs)):
            key = (token, origin)
            result[dest][key] = result[dest].get(key, 0) + sign
    return tuple(tuple((token, origin, weight) for (token, origin), weight in sorted(r.items()) if weight)
                 for r in result)


def row_bytes(domain, *, seed, d_model=DIMENSION):
    validate_config(seed, d_model)
    _require(type(domain) is list and bool(domain), "TYPED_BINDING_ROW_DOMAIN")
    bits = int.from_bytes(sha256(_canonical([ROW_ALGORITHM, seed, d_model, domain]).encode()).digest()[:8], "little")
    return struct.pack("<64f", *(0.125 if (bits >> i) & 1 else -0.125 for i in range(d_model)))


def projection_bytes(tokenizer, *, seed, d_model=DIMENSION):
    _require(type(tokenizer) is tokenization.FrameTokenizer, "TYPED_BINDING_TOKENIZER_TYPE")
    tokenizer.to_dict()
    values = [row_bytes(["token", token], seed=seed, d_model=d_model) for token in tokenizer.vocabulary]
    _require(len(set(values)) == len(values), "TYPED_BINDING_DUPLICATE_TOKEN_ROWS")
    return b"".join(values)


def readout_bytes(*, seed, d_model=DIMENSION):
    values = [row_bytes(["readout", symbol], seed=seed, d_model=d_model) for symbol in slots.SYMBOLS]
    _require(len(values) == len(set(values)) == 90, "TYPED_BINDING_READOUT_ROWS")
    return b"".join(values)


def slot_query_spec(packet, slotplan, slot):
    validated = slots.validate_plan(packet, slotplan)
    _require(type(slot) is dict and any(_canonical(slot) == _canonical(value) for value in validated["slots"]),
             "TYPED_BINDING_SLOT_MEMBERSHIP")
    return _query_spec(validated, slot)


def _query_spec(validated, slot):
    """Internal path for a caller that already checked exact plan membership."""
    aliases = validated["aliases"]["worlds"]
    nodes = {node["ref"]: world["alias"] + "/" + node["alias"] for world in aliases for node in world["nodes"]}
    coordinates = [nodes.get(value, value) if type(value) is str else value for value in slot["coordinates"]]
    return {"kind": validated["kind"], "field": slot["field"], "group": slot["group"],
            "scope": slot["scope_alias"], "coordinates": coordinates, "symbols": list(slot["symbols"])}


def query_bytes(packet, slotplan, slot, *, seed, d_model=DIMENSION):
    return row_bytes(["query", slot_query_spec(packet, slotplan, slot)], seed=seed, d_model=d_model)
