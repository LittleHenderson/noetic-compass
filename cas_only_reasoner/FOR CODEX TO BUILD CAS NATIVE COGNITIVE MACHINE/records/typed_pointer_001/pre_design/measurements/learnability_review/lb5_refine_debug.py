"""Debug the colour-refinement routine on known shapes before any count is trusted."""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}

# synthetic shapes with known colour structure
S = {
    "3-path": (["a", "b", "c"], [("a", "b"), ("b", "c")]),
    "4-star": (["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("a", "d")]),
    "4-path": (["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")]),
    "2+2": (["a", "b", "c", "d"], [("a", "b"), ("c", "d")]),
    "fork": (["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d")]),
    "V": (["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]),
}


def refine_shape(refs, edges, init):
    parent, child = defaultdict(list), defaultdict(list)
    for x, y in edges:
        child[x].append(y)
        parent[y].append(x)
    cur = dict(init)
    hist = [cur]
    for _ in range(6):
        key = {r: (cur[r], tuple(sorted(cur[p] for p in parent[r])), tuple(sorted(cur[c] for c in child[r]))) for r in refs}
        table = {k: i for i, k in enumerate(sorted(set(key.values())))}
        nxt = {r: table[key[r]] for r in refs}
        hist.append(nxt)
        if all((nxt[a] == nxt[b]) == (cur[a] == cur[b]) for a in refs for b in refs):
            cur = nxt
            hist.append(nxt)
            break
        cur = nxt
    return hist


def structural_colour(refs, edges):
    ind = Counter(), Counter()
    i_, o_ = Counter(), Counter()
    for a, b in edges:
        o_[a] += 1
        i_[b] += 1
    return {r: "ind=%d|outd=%d" % (i_.get(r, 0), o_.get(r, 0)) for r in refs}


print("synthetic shapes, structural colouring (degree only), no text:")
for name, (refs, edges) in S.items():
    hist = refine_shape(refs, edges, structural_colour(refs, edges))
    print("  %-8s rounds %d  final colour classes %d  signature %s  hist %s"
          % (name, len(hist) - 1, len(set(hist[-1].values())),
             tuple(sorted(Counter(hist[-1].values()).values())),
             [len(set(h.values())) for h in hist]))

print()
print("with a unique text colour per node (what reading label words does):")
for name, (refs, edges) in S.items():
    init = {r: structural_colour(refs, edges)[r] + "|text=" + r for r in refs}
    hist = refine_shape(refs, edges, init)
    print("  %-8s final colour classes %d signature %s" % (name, len(set(hist[-1].values())),
          tuple(sorted(Counter(hist[-1].values()).values()))))

print()
print("real bank worlds: structural colouring, showing the transition each round")
shown = set()
for wid in sorted(worlds):
    w = worlds[wid]
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = sorted((e["source"], e["target"]) for e in w["contains"])
    key = (len(refs), tuple(sorted((o_.get(r, 0) for o_ in [Counter(a for a, _ in edges)]) for r in refs)) if False else len(edges))
    init = structural_colour(refs, edges)
    hist = refine_shape(refs, edges, init)
    sig = tuple(sorted(Counter(hist[-1].values()).values()))
    tag = (len(refs), len(edges), sig)
    if tag not in shown:
        shown.add(tag)
        print("  nodes=%d edges=%d  initial classes %d  per-round classes %s  final signature %s"
              % (len(refs), len(edges), len(set(init.values())), [len(set(h.values())) for h in hist], sig))
print()
sigs = Counter()
for wid in sorted(worlds):
    w = worlds[wid]
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = sorted((e["source"], e["target"]) for e in w["contains"])
    init = structural_colour(refs, edges)
    hist = refine_shape(refs, edges, init)
    sigs[tuple(sorted(Counter(hist[-1].values()).values()))] += 1
print("real bank worlds by structural-colouring signature:", dict(sigs))

full = Counter()
for wid in sorted(worlds):
    w = worlds[wid]
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = sorted((e["source"], e["target"]) for e in w["contains"])
    decl = w["declarations"]
    part = sorted(decl["participants"])
    prim = list(decl["primary_labels"])
    init = {}
    for n in w["nodes"]:
        r = n["ref"]
        init[r] = "%s|whole=%d|parank=%d|prirank=%d|text=%s" % (
            structural_colour(refs, edges)[r], int(r == w["declared_whole"]),
            part.index(r) + 1 if r in part else 0, prim.index(r) + 1 if r in prim else 0, n["label"])
    hist = refine_shape(refs, edges, init)
    full[tuple(sorted(Counter(hist[-1].values()).values()))] += 1
print("real bank worlds, FULL colouring including flags + label text:", dict(full))

nofull = Counter()
for wid in sorted(worlds):
    w = worlds[wid]
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = sorted((e["source"], e["target"]) for e in w["contains"])
    decl = w["declarations"]
    part = sorted(decl["participants"])
    prim = list(decl["primary_labels"])
    init = {}
    for n in w["nodes"]:
        r = n["ref"]
        init[r] = "%s|whole=%d|parank=%d|prirank=%d" % (
            structural_colour(refs, edges)[r], int(r == w["declared_whole"]),
            part.index(r) + 1 if r in part else 0, prim.index(r) + 1 if r in prim else 0)
    hist = refine_shape(refs, edges, init)
    nofull[tuple(sorted(Counter(hist[-1].values()).values()))] += 1
print("real bank worlds, flags but NO label text:", dict(nofull))
