"""LEAKS LENS lk2: single-flag no-learning baselines, per kind, held and trained.

Every rule reads ONE proposed input field (plus the query arguments, which the design
also supplies) and produces a complete answer scored by the private checker. The FP2
rule is kept as its own line as instructed. Pure Python, no torch, no network.

    python lk2_single_flag.py
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, answers, side = m.frozen, m.answers, m.side
worlds, packets = m.worlds, m.packets
flags = flags_for(m)
ok, score, recount = m.ok, m.score, m.recount
kind_of = m.kind_of

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  held questions", len(m.held_questions), "trained questions", len(m.trained_questions))
print("  eligible", len(m.eligible), "shortcut-removed", len(m.shortcut_hit))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))

FIRST_WORLD = sorted(worlds)[0]


def A(world_id, field):
    return answers.declaration_ref(world_id, field)


def first_ref(field):
    return A(FIRST_WORLD, field)


# ------------------------------------------------------------------ rules
def r_DW(kind, row):
    """is_declared_whole alone: one node identity, nothing else."""
    f = flags(row)
    if kind == "parts":
        return {"nodes": [f["DW"]] if f["DW"] != f["WA"] else []}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": [f["DW"]]}
    if kind == "edge_account":
        return {"edges": [{"source": f["DW"], "target": f["DW"]}]}
    if kind == "reach":
        return {"state": "VIA", "via": f["DW"]}
    if kind == "definition":
        return {"whole": f["DW"], "kind_ref": first_ref("kind"), "function_ref": first_ref("function")}
    if kind == "analogy":
        return {"world_id": None}
    if kind == "correspondence":
        return {"status": "NO_MATCH", "pairs": []}
    return {"roles": [], "status": "INSUFFICIENT"}


def r_P(kind, row):
    """is_participant alone: the participant SET (sorted)."""
    f = flags(row)
    P = f["Psorted"]
    if not P:
        return None
    if kind == "parts":
        return {"nodes": P}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": P}
    if kind == "edge_account":
        return {"edges": [{"source": P[0], "target": P[-1]}]}
    if kind == "reach":
        return {"state": "DIRECT", "via": None} if f["PA"] in P else {"state": "ABSENT", "via": None}
    if kind == "definition":
        return {"whole": P[0], "kind_ref": first_ref("kind"), "function_ref": first_ref("function")}
    if kind == "analogy":
        return {"world_id": None}
    if kind == "correspondence":
        return {"status": "NO_MATCH", "pairs": []}
    return {"roles": [], "status": "INSUFFICIENT"}


def r_Prank(kind, row):
    """is_participant + participant rank: only the rank-1 (first authored) participant."""
    f = flags(row)
    if not f["P"]:
        return None
    first = f["P"][0]
    if kind == "parts":
        return {"nodes": [first]}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": [first]}
    if kind == "reach":
        return {"state": "DIRECT", "via": None} if f["PA"] == first else {"state": "ABSENT", "via": None}
    return r_P(kind, row)


def r_L(kind, row):
    """is_primary_label alone: the primary-label SET."""
    f = flags(row)
    L = sorted(f["L"])
    if not L:
        return None
    if kind == "parts":
        return {"nodes": L}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": L}
    if kind == "reach":
        return {"state": "DIRECT", "via": None} if f["PA"] in L else {"state": "ABSENT", "via": None}
    if kind == "definition":
        return {"whole": L[0], "kind_ref": first_ref("kind"), "function_ref": first_ref("function")}
    return None


def r_Lrank(kind, row):
    """is_primary_label + primary rank: the rank-1 primary label only."""
    f = flags(row)
    if not f["L"]:
        return None
    first = f["L"][0]
    if kind == "parts":
        return {"nodes": [first]}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": [first]}
    if kind == "reach":
        return {"state": "DIRECT", "via": None} if f["PA"] == first else {"state": "ABSENT", "via": None}
    return None


def r_F(kind, row):
    """is_focus_world alone."""
    f = flags(row)
    if kind == "definition":
        return {"whole": f["rank0"], "kind_ref": A(f["F"], "kind"), "function_ref": A(f["F"], "function")}
    if kind == "context":
        return {"setting_ref": A(f["F"], "setting"), "participants": []}
    if kind == "analogy":
        return {"world_id": f["F"]}
    if kind == "correspondence":
        return r_T(kind, row)
    return None


def r_T(kind, row):
    """is_correspondence_target alone: pair source and target nodes by sorted position."""
    if kind != "correspondence":
        return None
    f = flags(row)
    src = sorted(n["ref"] for n in worlds[f["F"]]["nodes"])
    tgt = sorted(n["ref"] for n in worlds[f["T"]]["nodes"])
    if len(src) != len(tgt):
        return {"status": "NO_MATCH", "pairs": []}
    return {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(src, tgt)]}


def r_rank0(kind, row):
    """the node whose rank among the world's sorted refs is 0."""
    f = flags(row)
    if kind == "definition":
        return {"whole": f["rank0"], "kind_ref": first_ref("kind"), "function_ref": first_ref("function")}
    if kind == "parts":
        return {"nodes": [f["rank0"]]}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": [f["rank0"]]}
    if kind == "reach":
        return {"state": "VIA", "via": f["rank0"]}
    if kind == "correspondence":
        return r_T(kind, row)
    return None


def r_rankgt0(kind, row):
    """every node whose rank among the world's sorted refs is >= 1."""
    f = flags(row)
    if kind == "parts":
        return {"nodes": f["rankgt0"]}
    if kind == "context":
        return {"setting_ref": first_ref("setting"), "participants": f["rankgt0"]}
    return None


def r_rankN(kind, row):
    """the node with the highest rank among the world's sorted refs."""
    f = flags(row)
    if kind == "definition":
        return {"whole": f["rankN"], "kind_ref": first_ref("kind"), "function_ref": first_ref("function")}
    if kind == "parts":
        return {"nodes": [f["rankN"]]}
    if kind == "reach":
        return {"state": "VIA", "via": f["rankN"]}
    return None


def r_domain(kind, row):
    """the focus world's domain word: the different-domain subset."""
    f = flags(row)
    different = sorted(k for k, w in worlds.items()
                       if w["declarations"]["domain"] != f["w"]["declarations"]["domain"])
    if kind == "analogy":
        return {"world_id": different[0] if len(different) == 1 else None}
    if kind == "definition":
        return {"whole": f["rank0"], "kind_ref": A(different[0], "kind"), "function_ref": A(different[0], "function")}
    if kind == "context":
        return {"setting_ref": A(different[0], "setting"), "participants": []}
    return None


def r_FP2(kind, row):
    """FP2, its own line: parts(declared_whole) = participants - declared_whole."""
    if kind != "parts":
        return None
    f = flags(row)
    if f["WA"] != f["DW"]:
        return {"nodes": []}
    return {"nodes": [p for p in f["Psorted"] if p != f["DW"]]}


def r_copier(kind, row):
    """every flag of section 2.1, never the adjacency."""
    f = flags(row)
    if kind == "definition":
        return {"whole": f["DW"], "kind_ref": A(f["F"], "kind"), "function_ref": A(f["F"], "function")}
    if kind == "context":
        return {"setting_ref": A(f["F"], "setting"), "participants": f["Psorted"]}
    if kind == "parts":
        return r_FP2(kind, row)
    if kind == "reach":
        return {"state": "DIRECT", "via": None} if f["WA"] == f["DW"] and f["PA"] in f["Psorted"] else {"state": "ABSENT", "via": None}
    if kind == "edge_account":
        return {"edges": [{"source": f["DW"], "target": p} for p in f["Psorted"] if p != f["DW"]]}
    if kind == "analogy":
        return {"world_id": None}
    if kind == "correspondence":
        return r_T(kind, row)
    return None


RULES = (
    ("R1 is_declared_whole ALONE (1 flag)", "is_declared_whole", r_DW, KINDS),
    ("R2 is_participant ALONE (1 flag)", "is_participant", r_P, KINDS),
    ("R3 is_participant + participant rank, rank-1 participant only (2 fields)", "is_participant, participant rank", r_Prank,
     ("parts", "context", "reach")),
    ("R4 is_primary_label ALONE (1 flag)", "is_primary_label", r_L, ("parts", "context", "reach", "definition")),
    ("R5 is_primary_label + primary rank, rank-1 label only (2 fields)", "is_primary_label, primary rank", r_Lrank,
     ("parts", "context", "reach")),
    ("R6 is_focus_world ALONE (1 flag)", "is_focus_world", r_F, ("definition", "context", "analogy", "correspondence")),
    ("R7 is_correspondence_target ALONE (1 flag, + sorted position)", "is_correspondence_target", r_T, ("correspondence",)),
    ("R8 node rank == 0 (the alphabetically first ref) (1 flag)", "node rank among sorted refs", r_rank0,
     ("definition", "parts", "context", "reach", "correspondence")),
    ("R9 node rank >= 1 (all but the alphabetically first ref) (1 flag)", "node rank among sorted refs", r_rankgt0,
     ("parts", "context")),
    ("R10 node rank == highest (the alphabetically last ref) (1 flag)", "node rank among sorted refs", r_rankN,
     ("definition", "parts", "reach")),
    ("R11 the focus world's domain word (1 flag)", "domain word", r_domain, ("analogy", "definition", "context")),
    ("R12 FP2 LINE: parts(declared_whole) = participants - declared_whole", "is_declared_whole + is_participant + query whole",
     r_FP2, ("parts",)),
    ("R13 ALL FLAGS, NO ADJACENCY (FP1's flag copier)", "every flag of section 2.1", r_copier, KINDS),
)

print()
print("SINGLE-FLAG AND FLAG-COPY BASELINES (pure no-learning rules, scored by the private checker)")
print("HE = held-back ELIGIBLE questions solved | HA = all held-back questions | TR = trained questions")
summary = {}
all_eligible = len(m.eligible)
for label, fields, fn, kinds in RULES:
    rec_ok = score(lambda k, r, fn=fn, kinds=kinds: fn(k, r) if k in kinds else None)
    rec, rec_tot, q, q_tot = recount(rec_ok)
    print()
    print("  RULE: %s" % label)
    print("    fields read: %s" % fields)
    for k in kinds:
        print("    %-14s HE %d/%d | HA %d/%d | TR %d/%d | records %s"
              % (k, q["held_eligible"][k], q_tot["held_eligible"][k], q["held_all"][k], q_tot["held_all"][k],
                 q["trained"][k], q_tot["trained"][k],
                 " ".join("%s %d/%d" % (s, rec[s][k], rec_tot[s][k]) for s in SIDES)))
        summary.setdefault(k, []).append((label.split()[0], q["held_eligible"][k], q_tot["held_eligible"][k]))
    print("    ALL EIGHT KINDS: %d/%d held-back eligible questions"
          % (sum(q["held_eligible"][k] for k in KINDS), all_eligible))

print()
print("BEST SINGLE-FLAG RULE PER KIND (held-back eligible questions)")
for k in KINDS:
    best = sorted(summary[k], key=lambda row: (-row[1], row[2], row[0]))[0]
    print("  %-14s best %d/%d by rule %s" % (k, best[1], best[2], best[0]))

print()
print("REFERENCE: the registered input-blind shortcut removal (evaluate_gates.eligible_questions)")
print("  shortcut answers per kind", m.shortcut)
print("  removed questions", len(m.shortcut_hit), dict(sorted(Counter(kind_of[q] for q in m.shortcut_hit).items())))
print("  removed question ids", sorted(m.shortcut_hit))
print("  shortcut source:", m.shortcut_source)
