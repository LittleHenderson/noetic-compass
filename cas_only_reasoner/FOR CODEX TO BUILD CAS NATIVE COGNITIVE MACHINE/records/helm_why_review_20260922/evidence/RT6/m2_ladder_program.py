"""RT6 M2: recompute every gold answer of the Helm difficulty ladder (Q1 T06/T08 instrument) with my OWN
short graph program, reading only the world (edges + labels) and the question arguments. No build code imported."""
import collections, json, pathlib
ROOT = pathlib.Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
d = json.loads((ROOT / "records/typed_pointer_001/ladder/ladder_v0_1.json").read_text(encoding="utf-8"))
def bfs(children, start):
    dist, frontier = {start: 0}, [start]
    while frontier:
        nxt = []
        for n in frontier:
            for c in children[n]:
                if c not in dist:
                    dist[c] = dist[n] + 1; nxt.append(c)
        frontier = nxt
    return dist
def solve(world, q):
    L, n = world["labels"], world["size"]
    ch = collections.defaultdict(set)
    for a, b in world["edges"]:
        ch[a].add(b)
    if q["kind"] == "parts":
        w = L.index(q["arguments"]["whole"])
        return {"nodes": sorted(L[c] for c in ch[w])}
    if q["kind"] == "edge_account":
        return {"edges": sorted([L[a], L[b]] for a, b in world["edges"])}
    w, p = L.index(q["arguments"]["whole"]), L.index(q["arguments"]["part"])
    dw = bfs(ch, w)
    if p not in dw:
        return {"state": "ABSENT", "via": None}
    if dw[p] == 1:
        return {"state": "DIRECT", "via": None}
    cands = [c for c in ch[w] if bfs(ch, c).get(p) == dw[p] - 1]
    return {"state": "VIA", "via": min(L[c] for c in cands)}
tally = collections.Counter(); miss = []
for q in d["questions"]:
    ok = solve(d["worlds"][q["world_id"]], q) == q["answer"]
    tally[(q["kind"], q["hop_distance"], ok)] += 1
    if not ok: miss.append(q)
print("questions", len(d["questions"]), "worlds", len(d["worlds"]))
for k in sorted(tally): print(k, tally[k])
print("exact from visible world + arguments: %d/%d" % (len(d["questions"]) - len(miss), len(d["questions"])))
