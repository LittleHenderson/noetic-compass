"""Shared loader + pure-Python frozen-encoder rebuild (float64). Run with python -B (no .pyc in repo)."""
import sys
sys.dont_write_bytecode = True
import hashlib, math, struct, pathlib, json, pickle, os

CNCM = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
COMP = CNCM / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(CNCM)); sys.path.insert(0, str(COMP))
from cas_meta2.typed_teaching import practice_contract as c, binding, slots, checker  # noqa

SCRATCH = pathlib.Path(__file__).resolve().parent
SEED = 20260916
D = 64
FROZEN = {"projection": "4481b1d23e1f30e21e735efe337b8f2404ac53daea51510cf0106b2359fefdd9",
          "readout": "14da2c58e7c8f271968d99c251fc6eafd510d724982f15b86a3ded604f0ac667"}


def floats(raw):
    return list(struct.unpack(f"<{len(raw)//4}f", raw))


def rows_of(raw):
    f = floats(raw); return [f[i:i + D] for i in range(0, len(f), D)]


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    assert n > 0 and math.isfinite(n)
    return [x / n for x in v]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cos(a, b):
    return dot(a, b) / (norm(a) * norm(b))


def load():
    frozen, tokenizer, development = c.load_material(CNCM)
    held, trained, excluded = c.split(frozen)
    packets = dict(c.public_packets(frozen))
    return frozen, tokenizer, development, held, trained, excluded, packets


def gate(tokenizer):
    p = binding.projection_bytes(tokenizer, seed=SEED)
    r = binding.readout_bytes(seed=SEED)
    hp, hr = hashlib.sha256(p).hexdigest(), hashlib.sha256(r).hexdigest()
    ok = hp == FROZEN["projection"] and hr == FROZEN["readout"]
    return ok, (hp, len(p) // 4 // D), (hr, len(r) // 4 // D), rows_of(p), rows_of(r)


_ROWCACHE = {}


def row_vector(row, ids, projection):
    """encoder.py:159-163 for one row: sum_t signedperm_t(proj[token_t]) / sqrt(count), unit."""
    key = (row["ordinal"], tuple(row["scope"]), tuple(row["token_ids"]))
    if key in _ROWCACHE:
        return _ROWCACHE[key]
    span = ids[row["start"]:row["start"] + row["count"]]
    assert span == row["token_ids"]
    acc = [0.0] * D
    for at, tok in enumerate(span):
        order, signs = binding.signed_permutation(seed=SEED, scope=row["scope"], ordinal=row["ordinal"], position=at, d_model=D)
        base = projection[tok]
        for dest in range(D):
            acc[dest] += signs[dest] * base[order[dest]]
    v = unit([x / math.sqrt(row["count"]) for x in acc])
    _ROWCACHE[key] = v
    return v


def packet_rows(packet, tokenizer, projection):
    plan = binding.compile_packet(packet, tokenizer, seed=SEED)
    ids = [t for row in plan["rows"] for t in row["token_ids"]]
    out = []
    for row in plan["rows"]:
        out.append((row, row_vector(row, ids, projection)))
    return plan, out


def packet_vector_from_rows(rowvecs):
    """encoder.py:164: unit(sum(unit rows)/sqrt(n))."""
    total = [0.0] * D
    for v in rowvecs:
        for i in range(D):
            total[i] += v[i]
    return unit([x / math.sqrt(len(rowvecs)) for x in total])


def query_vector(validated, slot):
    spec = binding._query_spec(validated, slot)
    return spec, floats(binding.row_bytes(["query", spec], seed=SEED))
