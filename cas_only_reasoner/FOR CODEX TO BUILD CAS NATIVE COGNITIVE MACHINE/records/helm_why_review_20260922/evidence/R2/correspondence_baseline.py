# Mechanism-free matchers vs Helm 2.0's saved, checker-scored-correct correspondence answers (held-back 20).
# Reads only saved records + the PUBLIC bank. No model, no torch, no private target file.
import json, itertools, collections
from pathlib import Path
CN = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
R = CN / "records/typed_pointer_001"
bank = json.loads((CN / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
W = {w["world_id"]: w for w in bank}
print("public bank worlds:", len(W))
ex = next(iter(W.values()))
print("declaration keys:", sorted(ex["declarations"].keys()))

# observed correct answers, per query, from Helm 2.0 seeds (every one scored correct by the frozen checker)
obs = collections.defaultdict(set); status = collections.Counter(); qworld = {}
for s in (7, 8, 9):
    d = R / ("receipt_2026091%d" % s) / "checkpoints"
    preds = json.loads((d / "ablation_baseline_predictions.json").read_text(encoding="utf-8"))["predictions"]
    sc = {r["record_id"]: r for r in json.loads((d / "ablation_baseline_scoring.json").read_text(encoding="utf-8"))["rows"]}
    for p in preds:
        row = sc[p["record_id"]]
        if row["kind"] != "correspondence":
            continue
        assert row["correct"], "all Helm 2.0 correspondence answers are expected correct"
        v = p["answer"]["value"]; status[v["status"]] += 1
        pairs = tuple(sorted((x["source"], x["target"]) for x in v.get("pairs", [])))
        obs[row["query_id"]].add(pairs)
print("held correspondence questions:", len(obs), "answer statuses over 3 seeds:", dict(status))
print("questions where the 3 seeds gave >1 distinct correct mapping:", sum(len(v) > 1 for v in obs.values()))

def world_of(ref): return ref.rsplit("/n", 1)[0]

def structure(w):
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = {(e["source"], e["target"]) for e in w["contains"]}
    return refs, edges

def participant_order(src, tgt):
    """whole -> whole, i-th declared participant -> i-th declared participant. Reads NO edge."""
    m = {src["declared_whole"]: tgt["declared_whole"]}
    for a, b in zip(src["declarations"]["participants"], tgt["declarations"]["participants"]):
        m[a] = b
    rs, _ = structure(src); rt, _ = structure(tgt)
    left = [r for r in rs if r not in m]; free = [r for r in rt if r not in m.values()]
    for a, b in zip(left, free):   # any node outside whole+participants: pair by sorted position
        m[a] = b
    return tuple(sorted(m.items()))

def positional(src, tgt):
    rs, _ = structure(src); rt, _ = structure(tgt)
    return tuple(sorted(zip(rs, rt)))

def iso_lexical_first(src, tgt):
    """Brute-force isomorphism over all permutations (4 nodes -> 24), first in lexical order of target refs."""
    rs, es = structure(src); rt, et = structure(tgt)
    if len(rs) != len(rt): return None
    for perm in itertools.permutations(rt):
        m = dict(zip(rs, perm))
        if {(m[a], m[b]) for a, b in es} == et:
            return tuple(sorted(m.items()))
    return None

def iso_all(src, tgt):
    rs, es = structure(src); rt, et = structure(tgt)
    out = set()
    for perm in itertools.permutations(rt):
        m = dict(zip(rs, perm))
        if {(m[a], m[b]) for a, b in es} == et:
            out.add(tuple(sorted(m.items())))
    return out

score = collections.Counter(); iso_counts = collections.Counter(); part_in_iso = 0
for q, answers in obs.items():
    ans = next(iter(answers))
    src, tgt = W[world_of(ans[0][0])], W[world_of(ans[0][1])]
    allm = iso_all(src, tgt)
    iso_counts[len(allm)] += 1
    for name, f in (("participant_order (no edges read)", participant_order), ("positional n_i->n_i", positional),
                    ("brute_force_isomorphism_lexical_first", iso_lexical_first)):
        score[name] += f(src, tgt) in answers
    part_in_iso += participant_order(src, tgt) in allm
    score["observed answer is a contains-isomorphism"] += ans in allm
for k, v in score.items():
    print("  %-45s %d / %d" % (k, v, len(obs)))
print("  participant_order mapping is itself a contains-isomorphism: %d / %d" % (part_in_iso, len(obs)))
print("  number of contains-isomorphisms per question (count: questions):", dict(sorted(iso_counts.items())))
