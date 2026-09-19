"""LEAKS LENS lk6: the RELATIONAL-tier gate population after every required removal, and the arithmetic.

Counts, per kind and per held world, exactly which questions must leave the gate population
before a LEARNS_NEW_WORLDS label can mean anything, then states the minimum passing b for
c = 0 at p <= 0.01. Pure Python, no torch, no network, read-only on every existing file.

    python lk6_gate_population.py
"""
import json
import sys
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for  # noqa: E402

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
SAMPLED = ("analogy", "correspondence")


def relabel_world(w, pi):
    new = deepcopy(w)
    new["nodes"] = [{**n, "ref": pi[n["ref"]]} for n in w["nodes"]]
    new["contains"] = [{**e, "source": pi[e["source"]], "target": pi[e["target"]]} for e in w["contains"]]
    new["declared_whole"] = pi[w["declared_whole"]]
    new["declarations"] = {**w["declarations"],
                           "participants": [pi[p] for p in w["declarations"]["participants"]],
                           "primary_labels": [pi[p] for p in w["declarations"]["primary_labels"]]}
    return new


def relabel_public(public, focus_id, pi):
    return {**public, "worlds": [relabel_world(w, pi) if w["world_id"] == focus_id else w
                                 for w in public["worlds"]]}


def apply_pi(value, pi):
    if type(value) is dict:
        return {k: apply_pi(v, pi) for k, v in value.items()}
    if type(value) is list:
        return [apply_pi(v, pi) for v in value]
    if type(value) is str and value in pi:
        return pi[value]
    return value


def comparable(kind, value):
    if kind == "role_set":
        return ("roles", tuple(value["roles"]), value["status"])
    if kind == "definition":
        return ("definition", value["whole"], value["kind_ref"], value["function_ref"])
    if kind == "context":
        return ("context", value["setting_ref"], tuple(sorted(value["participants"])))
    if kind == "parts":
        return ("parts", tuple(sorted(value["nodes"])))
    if kind == "edge_account":
        return ("edges", tuple(sorted((e["source"], e["target"]) for e in value["edges"])))
    if kind == "reach":
        return ("reach", value["state"], value["via"])
    if kind == "analogy":
        return ("analogy", value["world_id"])
    return ("corr", value["status"], tuple(sorted((p["source"], p["target"]) for p in value["pairs"])))


dep_questions = set()
for row in frozen["registry"]:
    kind, rid = row["query"]["kind"], row["record_id"]
    if side[rid] == "excluded":
        continue
    q = row["query"]
    focus = q["focus_world_id"]
    public = packets[rid]["source"]
    refs = sorted(n["ref"] for n in worlds[focus]["nodes"])
    base = [a["value"] for a in checker.derive_target(public, q)["admissible_answers"]]
    orders = ([tuple(reversed(refs))] if kind in SAMPLED else list(permutations(refs)))
    for order in orders:
        pi = dict(zip(refs, order))
        if all(pi[r] == r for r in refs):
            continue
        new_public = relabel_public(public, focus, pi)
        new_query = answers.compile_query(new_public, kind=kind, rule=q["rule"],
                                         arguments={**deepcopy(q["arguments"]),
                                                    **{f: pi[q["arguments"][f]] for f in ("whole", "part")
                                                       if f in q["arguments"]}},
                                         focus_world_id=focus)
        fresh = {canonical(comparable(kind, a["value"]))
                 for a in checker.derive_target(new_public, new_query)["admissible_answers"]}
        expected = {canonical(comparable(kind, apply_pi(v, pi))) for v in base}
        if fresh != expected:
            dep_questions.update(qq for qq, records in m.held_questions.items() if rid in records)
            break
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


r_rank0 = show("point at the alphabetically first node (rank 0) in every node slot", solved_questions(rank0_policy))
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
removals = (set(m.shortcut_hit) | r_fp2 | r_reach_flag | r_edge_flag | r_order | r_rank0 | r_present
            | r_argument | r_constant)
oracle = o_parts | o_edge | o_reach
rel_removed = {q for q in removals if q in rel}
strict_removed = rel_removed | {q for q in oracle if q in rel}
pop = sorted(set(rel) - rel_removed)
pop_strict = sorted(set(rel) - strict_removed)
print("  RELATIONAL tier as designed                                  %d" % len(rel))
print("  minus removals (flags, order dependence, pointing, constant)  %d" % len(rel_removed))
print("  PRIMARY RELATIONAL POPULATION                                 %d" % len(pop),
      dict(sorted(Counter(kind_of[q] for q in pop).items())))
print("  its spread over the held worlds", dict(sorted(Counter(world_of[q][:14] for q in pop).items())))
print("  minus the one-hop adjacency/oracle-solved questions as well   %d" % len(strict_removed - rel_removed))
print("  STRICT POPULATION                                             %d" % len(pop_strict),
      dict(sorted(Counter(kind_of[q] for q in pop_strict).items())))
print("  strict spread over the held worlds", dict(sorted(Counter(world_of[q][:14] for q in pop_strict).items())))
for name, population in (("PRIMARY", pop), ("STRICT", pop_strict)):
    n = len(population)
    minimum = next(b for b in range(0, n + 1) if eg.binomial_upper_tail(b, b) <= Fraction(1, 100))
    print("  %s: n = %d; minimum passing b with c = 0 at p <= 0.01 is b = %d" % (name, n, minimum))
    print("      check: 2**-%d = %s = %.7f <= 0.01 ; 2**-%d = %s = %.7f > 0.01"
          % (minimum, Fraction(1, 2 ** minimum), float(Fraction(1, 2 ** minimum)),
             minimum - 1, Fraction(1, 2 ** (minimum - 1)), float(Fraction(1, 2 ** (minimum - 1)))))
    print("      required share of the population: %d/%d = %.4f" % (minimum, n, minimum / n if n else 0.0))
    print("      gate also needs gains in >= 2 kinds and >= 2 held worlds: kinds available %s, worlds %d"
          % (sorted({kind_of[q] for q in population}), len({world_of[q] for q in population})))
print()
print("  ALL-EIGHT-KINDS population for reference:")
pop_all = sorted(set(m.eligible) - (removals & set(q for q in m.eligible)))
print("    eligible %d minus removals %d = %d" % (len(m.eligible), len(set(m.eligible) & removals), len(pop_all)))
print()
print("  removal ids by rule (eligible questions only, for the frozen removal list):")
for label, group in (("registered shortcut", set(m.shortcut_hit)), ("FP2 parts", r_fp2), ("reach flag", r_reach_flag),
                     ("edge flag", r_edge_flag), ("order dependence", r_order), ("rank-0 pointing", r_rank0),
                     ("PRESENT-for-all", r_present), ("argument-node pointing", r_argument),
                     ("best constant", r_constant), ("oracle one-hop (STRICT only)", oracle)):
    g = sorted(q for q in group if q in m.eligible_set)
    print("    %-28s %2d %s" % (label, len(g), g))
