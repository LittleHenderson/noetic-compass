"""LB14 — what the reference order and the label text can and cannot buy, measured.

Three orderings of the SOURCE nodes, applied as a rank permutation onto the TARGET nodes
sorted by the same rule, and graded against the checker's admissible set:
  ref-rank   : sort by node ref string (the hidden hash order; DG3's rank feature)
  label-rank : sort by the node's label text
  deg-rank   : sort by (in-degree, out-degree), tie-broken by ref
Also measured: is a world's isomorphism to another world ever label-preserving, i.e. does a
node always map to the node with the SAME label? If yes, label text is a complete answer
channel for correspondence. If no, labels are not an answer channel.
"""
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


def degrees(w):
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    return {n["ref"]: (ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]}


def order_by(w, rule):
    if rule == "ref-rank":
        return sorted(n["ref"] for n in w["nodes"])
    if rule == "label-rank":
        return [n["ref"] for n in sorted(w["nodes"], key=lambda n: (n["label"], n["ref"]))]
    if rule == "deg-rank":
        d = degrees(w)
        return sorted((n["ref"] for n in w["nodes"]), key=lambda r: (d[r][0], d[r][1], r))
    raise ValueError(rule)


rows = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    wmap = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = wmap[q["focus_world_id"]]
    target = wmap[q["arguments"]["target_world_id"]]
    adm = {checker._canonical(a["value"]) for a in checker.derive_target(p["source"], q)["admissible_answers"]}
    line = {"rid": rid, "side": side(rid)}
    for rule in ("ref-rank", "label-rank", "deg-rank"):
        src, tgt = order_by(focus, rule), order_by(target, rule)
        cand = {"status": "MAPPING", "pairs": [{"source": a, "target": b} for a, b in zip(src, tgt)]}
        line[rule] = checker._canonical(cand) in adm
    # label-preserving test: does an isomorphism exist that maps each ref to same label?
    fw, tw = next(w for w in frozen["bank"]["worlds"] if w["world_id"] == focus["world_id"]), \
             next(w for w in frozen["bank"]["worlds"] if w["world_id"] == target["world_id"])
    lf = {n["ref"]: n["label"] for n in fw["nodes"]}
    lt = {n["ref"]: n["label"] for n in tw["nodes"]}
    bylabel = {v: k for k, v in lt.items()}
    plain = {v: k for k, v in lf.items()}
    line["label_preserving_candidate_exists"] = (set(lf.values()) == set(lt.values()))
    if line["label_preserving_candidate_exists"]:
        cand = {"status": "MAPPING", "pairs": [{"source": r, "target": bylabel[lf[r]]} for r in sorted(lf)]}
        line["label_preserving_is_admissible"] = checker._canonical(cand) in adm
    else:
        line["label_preserving_is_admissible"] = False
    rows.append(line)

print("correspondence records %d" % len(rows))
for s in ("held", "trained", "excluded"):
    sub = [r for r in rows if r["side"] == s]
    if not sub:
        continue
    print("  %-9s records %-3d  ref-rank rule %d  label-rank rule %d  degree-rank rule %d  label-preserving admissible %d  label sets equal %d"
          % (s, len(sub), sum(r["ref-rank"] for r in sub), sum(r["label-rank"] for r in sub),
             sum(r["deg-rank"] for r in sub), sum(r["label_preserving_is_admissible"] for r in sub),
             sum(r["label_preserving_candidate_exists"] for r in sub)))

# Do the two worlds of a correspondence pair share any label at all?
print()
print("do the paired worlds of a correspondence question share any node label?")
shared = Counter()
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    wmap = {w["world_id"]: w for w in p["source"]["worlds"]}
    a = {n["label"] for n in wmap[q["focus_world_id"]]["nodes"]}
    b = {n["label"] for n in wmap[q["arguments"]["target_world_id"]]["nodes"]}
    shared[(side(rid), len(a & b))] += 1
for s in ("held", "trained", "excluded"):
    print("  %-9s shared-label counts %s" % (s, dict(sorted((k[1], v) for k, v in shared.items() if k[0] == s))))

# Analogy: is the correct partner ever identifiable by label overlap?
print()
print("analogy: label overlap between the focus world and each candidate, split by whether")
print("the candidate is a correct answer")
from cas_meta2.typed_teaching import checker as ch
for s in ("held", "trained"):
    corr, wrong = [], []
    for rid in sorted(packets):
        p = packets[rid]
        q = p["record"]["query"]
        if q["kind"] != "analogy" or side(rid) != s:
            continue
        wmap = {w["world_id"]: w for w in p["source"]["worlds"]}
        focus = wmap[q["focus_world_id"]]
        lf = {n["label"] for n in focus["nodes"]}
        good = {a["value"]["world_id"] for a in checker.derive_target(p["source"], q)["admissible_answers"]}
        for wid, w in wmap.items():
            if wid == q["focus_world_id"]:
                continue
            ov = len(lf & {n["label"] for n in w["nodes"]})
            (corr if wid in good else wrong).append(ov)
    print("  %-9s correct candidates %d overlap histogram %s ; wrong candidates %d histogram %s"
          % (s, len(corr), dict(sorted(Counter(corr).items())), len(wrong), dict(sorted(Counter(wrong).items()))))
