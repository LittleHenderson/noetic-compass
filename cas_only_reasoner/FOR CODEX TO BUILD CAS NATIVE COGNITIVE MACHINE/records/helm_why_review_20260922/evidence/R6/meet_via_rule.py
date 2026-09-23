# R6 meeting: in the held worlds of the frozen reach questions, which (whole, part) pairs have a VIA answer,
# and does a ONE-HOP REVERSE read ("the part's own parent") name the via node? Public bank only. No model.
import json, collections
from pathlib import Path
CN = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
bank = json.loads((CN / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
s = lambda r: r.split("/")[-1]
def analyse(w):
    nodes = [s(n["ref"]) for n in w["nodes"]]
    ch = collections.defaultdict(set); par = collections.defaultdict(set)
    for e in w["contains"]:
        ch[s(e["source"])].add(s(e["target"])); par[s(e["target"])].add(s(e["source"]))
    out = []
    for a in nodes:
        # BFS distances from a
        dist = {a: 0}; q = [a]
        while q:
            x = q.pop(0)
            for y in sorted(ch[x]):
                if y not in dist: dist[y] = dist[x] + 1; q.append(y)
        for b in nodes:
            if b != a and dist.get(b, 0) >= 2:
                vias = sorted(m for m in nodes if m not in (a, b) and m in dist
                              and b in _reach(ch, m))
                out.append((a, b, dist[b], vias, sorted(par[b])))
    return nodes, {k: sorted(v) for k, v in ch.items()}, out
def _reach(ch, m):
    seen = set(); q = [m]
    while q:
        x = q.pop()
        for y in ch[x]:
            if y not in seen: seen.add(y); q.append(y)
    return seen
for prefix in ("world-6e1fcbda", "world-28f61f2d", "world-4090ec49"):
    w = [w for w in bank if w["world_id"].startswith(prefix)][0]
    nodes, ch, out = analyse(w)
    print(prefix, "whole", s(w["declared_whole"]), "children", ch)
    for a, b, d, vias, parents in out:
        print("   reach(%s -> %s) distance %d  intermediates %s  parent-of-part %s  rank-last-node %s" % (a, b, d, vias, parents, max(nodes)))
# bank-wide: over all VIA pairs at distance exactly 2 in every world, is the part's parent unique and an intermediate?
tot = ok = 0
for w in bank:
    nodes, ch, out = analyse(w)
    for a, b, d, vias, parents in out:
        if d == 2:
            tot += 1; ok += (len(parents) == 1 and parents[0] in vias)
print("bank: distance-2 reach pairs", tot, "where the part has exactly one parent and it is an intermediate", ok)
