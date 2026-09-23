"""RT6 M3: in the ladder's VIA questions, how often does the gold 'via' depend on LABEL order (a tie among
shortest-route first constituents), and how often does the frozen checker's rule (first child in index
order with ANY path) give a different answer? No adapter feeds the ladder to Helm yet, so this sizes an exposure only."""
import collections, json, pathlib
ROOT = pathlib.Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
d = json.loads((ROOT / "records/typed_pointer_001/ladder/ladder_v0_1.json").read_text(encoding="utf-8"))
def bfs(ch, s):
    dist, fr = {s: 0}, [s]
    while fr:
        nx = []
        for n in fr:
            for c in sorted(ch[n]):
                if c not in dist: dist[c] = dist[n] + 1; nx.append(c)
        fr = nx
    return dist
c = collections.Counter()
for q in d["questions"]:
    if q["kind"] != "reach" or q["answer"]["state"] != "VIA": continue
    w = d["worlds"][q["world_id"]]; L = w["labels"]; ch = collections.defaultdict(set)
    for a, b in w["edges"]: ch[a].add(b)
    wh, p = L.index(q["arguments"]["whole"]), L.index(q["arguments"]["part"])
    dp = bfs(ch, wh)[p]
    short = [x for x in ch[wh] if bfs(ch, x).get(p) == dp - 1]
    by_label = L[min(short, key=lambda x: L[x])]
    by_index = L[min(short)]
    frozen_rule = L[min(x for x in ch[wh] if p in bfs(ch, x))]
    frozen_rule_label = min(L[x] for x in ch[wh] if p in bfs(ch, x))
    c["frozen_rule_label_order_differs_from_gold"] += frozen_rule_label != q["answer"]["via"]
    c["via_questions"] += 1
    c["tie_among_shortest"] += len(short) > 1
    c["label_order_differs_from_index_order"] += by_label != by_index
    c["frozen_checker_rule_differs_from_gold"] += frozen_rule != q["answer"]["via"]
    assert by_label == q["answer"]["via"]
print(dict(c))
