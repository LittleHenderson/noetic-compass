"""Can node-LOCAL structural features alone (declared-whole flag, in-degree, out-degree) pick a correct
correspondence on the 5 held questions? Helm 2.0 still scores 20/20 with message passing switched off,
so its matching head sees only per-node raw features. Pure JSON, public bank + saved predictions only."""
import json, itertools, collections
from pathlib import Path
CN = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
R = CN / "records/typed_pointer_001"
bank = json.loads((CN / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
W = {w["world_id"]: w for w in bank}
def world_of(ref): return ref.rsplit("/n", 1)[0]
def struct(w):
    refs = sorted(n["ref"] for n in w["nodes"]); edges = {(e["source"], e["target"]) for e in w["contains"]}
    return refs, edges
def sig(w, r):
    _, es = struct(w)
    return (1 if r == w["declared_whole"] else 0, sum(1 for a, b in es if b == r), sum(1 for a, b in es if a == r))
def part_rank(w, r):
    p = w["declarations"]["participants"]
    return p.index(r) + 1 if r in p else 0
qs = {}
for s in (7, 8, 9):
    d = R / ("receipt_2026091%d" % s) / "checkpoints"
    for tag in ("ablation_baseline", "ablation_round_mix"):
        preds = json.loads((d / (tag + "_predictions.json")).read_text(encoding="utf-8"))["predictions"]
        sc = {r["record_id"]: r for r in json.loads((d / (tag + "_scoring.json")).read_text(encoding="utf-8"))["rows"]}
        for p in preds:
            row = sc[p["record_id"]]
            if row["kind"] != "correspondence": continue
            pairs = tuple(sorted((x["source"], x["target"]) for x in p["answer"]["value"]["pairs"]))
            qs.setdefault(row["query_id"], {"pairs": pairs, "correct": collections.Counter()})
            qs[row["query_id"]]["correct"][(s, tag, row["correct"])] += 1
print("held correspondence questions:", len(qs))
for q, info in sorted(qs.items()):
    pairs = info["pairs"]; src, tgt = W[world_of(pairs[0][0])], W[world_of(pairs[0][1])]
    rs, es = struct(src); rt, et = struct(tgt)
    bij = [dict(zip(rs, perm)) for perm in itertools.permutations(rt)]
    iso = [m for m in bij if {(m[a], m[b]) for a, b in es} == et]
    local = [m for m in bij if all(sig(src, a) == sig(tgt, m[a]) for a in rs)]
    local_not_iso = [m for m in local if m not in iso]
    local_plus_rank = [m for m in local if all(part_rank(src, a) == part_rank(tgt, m[a]) for a in rs)]
    lpr_not_iso = [m for m in local_plus_rank if m not in iso]
    ok = {k: v for k, v in info["correct"].items()}
    print("%s nodes %d | isomorphisms %d | bijections matching (whole, in-deg, out-deg) %d, of which NOT isomorphisms %d | "
          "same + participant rank %d, NOT iso %d | correct counts %s"
          % (q[12:24], len(rs), len(iso), len(local), len(local_not_iso), len(local_plus_rank), len(lpr_not_iso),
             sorted((f"s{k[0]}-{k[1][9:]}", k[2], v) for k, v in ok.items())))
