"""LEAKS LENS lk6: the RELATIONAL-tier gate population after every required removal, and the arithmetic.

Counts, per kind and per held world, exactly which questions must leave the gate population
before a LEARNS_NEW_WORLDS label can mean anything, then states the minimum passing b for
c = 0 at p <= 0.01. Pure Python, no torch, no network, read-only on every existing file.

    python lk6_gate_population.py
"""
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for, order_dependent  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, checker, answers, slots, eg = m.frozen, m.checker, m.answers, m.slots, m.eg
packets, worlds, side, by_id = m.packets, m.worlds, m.side, m.by_id
flags = flags_for(m)
ok, canonical = m.ok, m.canonical
kind_of, world_of = m.kind_of, m.world_of
RELATIONAL = ("parts", "edge_account", "reach", "correspondence", "analogy")
DIRECT_READ = ("definition", "context")
TEXT = ("role_set",)

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  held-back questions", len(m.held_questions), "| registered input-blind removals", len(m.shortcut_hit))
print("  eligible population", len(m.eligible))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))
rel = sorted(q for q in m.eligible if kind_of[q] in RELATIONAL)
print("  RELATIONAL tier (as the draft defines it)", len(rel), dict(sorted(Counter(kind_of[q] for q in rel).items())))
print("  DIRECT_READ tier", len([q for q in m.eligible if kind_of[q] in DIRECT_READ]),
      dict(sorted(Counter(kind_of[q] for q in m.eligible if kind_of[q] in DIRECT_READ).items())))
print("  TEXT tier", len([q for q in m.eligible if kind_of[q] in TEXT]),
      dict(sorted(Counter(kind_of[q] for q in m.eligible if kind_of[q] in TEXT).items())))
print("  RELATIONAL by held world", dict(sorted(Counter(world_of[q][:14] for q in rel).items())))


def solved_questions(rule_of_kind, kinds=KINDS):
    rec_ok = {row["record_id"]: bool(v is not None and ok(row["record_id"], v))
              for row in frozen["registry"] for v in [rule_of_kind(row["query"]["kind"], row)]}
    return {q for q, records in m.held_questions.items() if all(rec_ok.get(r, False) for r in records)}


def show(label, questions, kinds=KINDS):
    hits = sorted(q for q in questions if q in m.eligible_set)
    print("  %-64s removes %2d eligible: %s" % (label, len(hits),
          dict(sorted(Counter(kind_of[q] for q in hits).items()))))
    return set(hits)


print()
print("REMOVAL 1 -- the registered input-blind shortcut (already applied before the gate)")
show("registered most-common-trained-answer removal", set(m.shortcut_hit))

print()
print("REMOVAL 2 -- flag-solved RELATIONAL questions (FP2 and its analogues; no relation is read)")

def fp2(k, r):
    if k != "parts":
        return None
    f = flags(r)
    if f["WA"] != f["DW"]:
        return {"nodes": []}
    return {"nodes": [p for p in f["Psorted"] if p != f["DW"]]}


def reach_flag(k, r):
    if k != "reach":
        return None
    f = flags(r)
    if f["WA"] == f["DW"] and f["PA"] in f["Psorted"]:
        return {"state": "DIRECT", "via": None}
    return {"state": "ABSENT", "via": None}


def edge_flag(k, r):
    if k != "edge_account":
        return None
    f = flags(r)
    return {"edges": [{"source": f["DW"], "target": p} for p in f["Psorted"] if p != f["DW"]]}


r_fp2 = show("FP2: parts(declared_whole) = participants - declared_whole", solved_questions(fp2))
r_reach_flag = show("reach flag rule: DIRECT if whole==declared_whole and part is a participant", solved_questions(reach_flag))
r_edge_flag = show("edge flag rule: edges = declared_whole -> participants - whole", solved_questions(edge_flag))

print()
print("REMOVAL 3 -- DG3 node-order-dependent questions (a name-blind machine cannot know the answer)")
dep_by_record = order_dependent(m)
dep_questions = {q for q, records in m.held_questions.items() if any(dep_by_record.get(r, False) for r in records)}
r_order = show("private answer not invariant under renaming the focus world's node refs", dep_questions)
print("     all held-back questions affected (eligible or not):", len(dep_questions), "of", len(m.held_questions))

print()
print("REMOVAL 4 -- zero-learning POINTING policies that a machine can learn to imitate")


def rank0_policy(k, r):
    f = flags(r)
    if k == "parts":
        return {"nodes": [f["rank0"]]}
    if k == "reach":
        return {"state": "VIA", "via": f["rank0"]}
    if k == "edge_account":
        return {"edges": []}
    if k == "correspondence":
        src = sorted(n["ref"] for n in worlds[f["F"]]["nodes"])
        tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
        if len(src) != len(tgt):
            return {"status": "NO_MATCH", "pairs": []}
        return {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(src, tgt)]}
    if k == "analogy":
        return {"world_id": None}
    return None


def present_all_policy(k, r):
    f = flags(r)
    if k == "parts":
        return {"nodes": list(f["refs"])}
    if k == "edge_account":
        return {"edges": [{"source": a, "target": b} for a in f["refs"] for b in f["refs"]]}
    if k == "reach":
        return {"state": "ABSENT", "via": None}
    if k == "correspondence":
        return {"status": "NO_MATCH", "pairs": []}
    if k == "analogy":
        return {"world_id": None}
    return None


def argument_node_policy(k, r):
    f = flags(r)
    target = f["WA"] or f["DW"]
    if k == "parts":
        return {"nodes": [target]}
    if k == "reach":
        return {"state": "VIA", "via": target}
    if k == "edge_account":
        return {"edges": []}
    if k == "correspondence":
        return rank0_policy(k, r)
    if k == "analogy":
        return {"world_id": f["F"]}
    return None


def rank_first_policy(k, r):
    f = flags(r)
    ref = f["rank0"]
    if k == "parts":
        return {"nodes": [ref]}
    if k == "reach":
        return {"state": "VIA", "via": ref}
    if k == "edge_account":
        return {"edges": []}
    if k == "correspondence":
        return rank0_policy(k, r)
    if k == "analogy":
        return {"world_id": None}
    return None


def rank_last_policy(k, r):
    """Point at the node with the HIGHEST rank, i.e. the alphabetically last node ref."""
    f = flags(r)
    ref = f["refs"][-1]
    if k == "parts":
        return {"nodes": [ref]}
    if k == "reach":
        return {"state": "VIA", "via": ref}
    if k == "edge_account":
        return {"edges": []}
    if k == "correspondence":
        return rank0_policy(k, r)
    if k == "analogy":
        return {"world_id": None}
    return None


r_rankfirst = show("point at the alphabetically FIRST node (rank 0) in every node slot",
                   solved_questions(rank_first_policy))
r_ranklast = show("point at the alphabetically LAST node (highest rank) in every node slot",
                  solved_questions(rank_last_policy))
r_present = show("PRESENT for every node / every edge slot; ABSENT for reach; NO_MATCH for the rest",
                 solved_questions(present_all_policy))
r_argument = show("point at the query's argument node (the declared whole when the question names none)",
                  solved_questions(argument_node_policy))
bank_order = eg._bank_order(frozen)
best_any = {}
counts_any = {}
for row in frozen["registry"]:
    if side[row["record_id"]] != "trained":
        continue
    k = row["query"]["kind"]
    counts_any.setdefault(k, Counter())
    for value in m.admissible[row["record_id"]]:
        counts_any[k][eg.alias_form(json.loads(value), bank_order)] += 1
for k, c in counts_any.items():
    best_any[k] = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def constant_policy(k, r):
    """The best single trained alias-form constant per kind, mapped back to this world's refs.

    The gate's alias form writes every node reference as its own stored index N<k> (evaluate_gates.py:89-96),
    so the constant is a per-world pointer list; it is valid only when it fits this world's shape.
    """
    symbol = best_any.get(k)
    if symbol is None:
        return None
    try:
        value = json.loads(symbol)
    except ValueError:
        return None
    f = flags(r)
    bank = sorted(worlds)
    src = list(f["refs"])
    tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"]) if f["T"] else []
    if k == "correspondence":
        if value["status"] == "NO_MATCH":
            return {"status": "NO_MATCH", "pairs": []}
        pairs = []
        for pair in value["pairs"]:
            i, j = int(pair["source"][1:]), int(pair["target"][1:])
            if i >= len(src) or j >= len(tgt):
                return {"status": "NO_MATCH", "pairs": []}
            pairs.append({"source": src[i], "target": tgt[j]})
        if sorted(p["source"] for p in pairs) != sorted(src):
            return {"status": "NO_MATCH", "pairs": []}
        return {"status": "MAPPING", "pairs": pairs}

    def sub(v):
        if type(v) is dict:
            return {kk: sub(vv) for kk, vv in v.items()}
        if type(v) is list:
            return [sub(vv) for vv in v]
        if type(v) is str:
            if v in set("N%d" % i for i in range(len(src))):
                return src[int(v[1:])]
            if "/decl/" in v and v.startswith("W") and v[1:].split("/")[0].isdigit():
                return answers.declaration_ref(bank[int(v[1:].split("/")[0])], v.rsplit("/decl/", 1)[1])
            if v.startswith("W") and v[1:].isdigit() and int(v[1:]) < len(bank):
                return bank[int(v[1:])]
        return v
    return sub(value)


r_constant = show("the best single trained alias-form CONSTANT answer per kind (input-blind, learnable)",
                  solved_questions(constant_policy))

print()
print("ORACLE RULES (reported, NOT removed by default: applying the checker's own rule to the input IS the")
print("skill under test; these are the ceiling baselines the label must be compared against)")


def parts_oracle(k, r):
    if k != "parts":
        return None
    f = flags(r)
    return {"nodes": sorted(checker._adjacency(f["w"])[f["WA"]])}


def edge_oracle(k, r):
    if k != "edge_account":
        return None
    return checker._derive_values(packets[r["record_id"]]["source"], r["query"])[0][0]


def reach_onehop(k, r):
    if k != "reach":
        return None
    f = flags(r)
    if f["PA"] in checker._adjacency(f["w"])[f["WA"]]:
        return {"state": "DIRECT", "via": None}
    return {"state": "ABSENT", "via": None}


o_parts = show("parts = children of the whole argument (one adjacency hop)", solved_questions(parts_oracle))
o_edge = show("edge_account = the full adjacency of the focus world (one-hop copy)", solved_questions(edge_oracle))
o_reach = show("reach = DIRECT iff part is a child, else ABSENT (one adjacency hop)", solved_questions(reach_onehop))

print()
print("GATE ARITHMETIC")
removals = (set(m.shortcut_hit) | r_fp2 | r_reach_flag | r_edge_flag | r_order | r_rankfirst | r_ranklast
            | r_present | r_argument | r_constant)
removals_with_rank = removals
removals_no_rank = removals - r_ranklast
oracle = o_parts | o_edge | o_reach
for name, group in (("WITHOUT the optional rank feature (section 2.1 as written)", removals_no_rank),
                    ("WITH the optional rank feature (DG3 option A)", removals_with_rank)):
    rel_removed = {q for q in group if q in rel}
    pop = sorted(set(rel) - rel_removed)
    print("  %s" % name)
    print("    RELATIONAL tier 29 minus %d = %d %s" % (len(rel_removed), len(pop),
          dict(sorted(Counter(kind_of[q] for q in pop).items()))))
    print("    spread over held worlds", dict(sorted(Counter(world_of[q][:14] for q in pop).items())))
    n = len(pop)
    minimum = next(b for b in range(0, n + 1) if eg.binomial_upper_tail(b, b) <= Fraction(1, 100))
    print("    n = %d; minimum passing b with c = 0 at p <= 0.01 is b = %d = 2**-%d = %s = %.7f"
          % (n, minimum, minimum, Fraction(1, 2 ** minimum), float(Fraction(1, 2 ** minimum))))
    print("    required share of the population %d/%d = %.4f" % (minimum, n, minimum / n if n else 0.0))
    strict_removed = rel_removed | {q for q in oracle if q in rel}
    pop_strict = sorted(set(rel) - strict_removed)
    ns = len(pop_strict)
    minimum_strict = next(b for b in range(0, ns + 1) if eg.binomial_upper_tail(b, b) <= Fraction(1, 100))
    print("    STRICT (also removing the one-hop adjacency questions) n = %d %s -> minimum b = %d (share %d/%d = %.4f)"
          % (ns, dict(sorted(Counter(kind_of[q] for q in pop_strict).items())), minimum_strict, minimum_strict, ns,
             minimum_strict / ns if ns else 0.0))
    print("    kinds with gains available %s | held worlds %d"
          % (sorted({kind_of[q] for q in pop}), len({world_of[q] for q in pop})))
print()
print("  ALL-EIGHT-KINDS population for reference:")
pop_all = sorted(set(m.eligible) - (removals & set(q for q in m.eligible)))
print("    eligible %d minus removals %d = %d" % (len(m.eligible), len(set(m.eligible) & removals), len(pop_all)))
print()
print("  removal ids by rule (eligible questions only, for the frozen removal list):")
for label, group in (("registered shortcut", set(m.shortcut_hit)), ("FP2 parts", r_fp2), ("reach flag", r_reach_flag),
                     ("edge flag", r_edge_flag), ("order dependence", r_order), ("rank-0 pointing", r_rankfirst),
                     ("rank-last pointing (needs the rank feature)", r_ranklast), ("PRESENT-for-all", r_present),
                     ("argument-node pointing", r_argument),
                     ("best constant", r_constant), ("oracle one-hop (STRICT only)", oracle)):
    g = sorted(q for q in group if q in m.eligible_set)
    print("    %-28s %2d %s" % (label, len(g), g))
