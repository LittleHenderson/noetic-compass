"""Do the six degree groups equal the six isomorphism classes? Two independent partitions crossed."""
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
heldworlds = list(c.held_worlds(frozen))
heldset = set(heldworlds)

# partition 1: sorted degree multiset
degree = {}
for wid, w in sorted(worlds.items()):
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    degree[wid] = tuple(sorted((ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]))

# partition 2: exact isomorphism class by brute force over labelings
def iso_class(w):
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = {(e["source"], e["target"]) for e in w["contains"]}
    best = None
    for order in permutations(range(len(refs))):
        idx = {r: order[i] for i, r in enumerate(refs)}
        key = tuple(sorted((idx[a], idx[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (len(refs), best)

iso = {wid: iso_class(w) for wid, w in worlds.items()}

gdeg = defaultdict(list)
for wid in sorted(worlds):
    gdeg[degree[wid]].append(wid)
giso = defaultdict(list)
for wid in sorted(worlds):
    giso[iso[wid]].append(wid)

print("degree-multiset partition: %d groups" % len(gdeg))
print("isomorphism partition:     %d groups" % len(giso))
cross = defaultdict(Counter)
for wid in sorted(worlds):
    cross[degree[wid]][iso[wid]] += 1
pure = all(len(v) == 1 for v in cross.values())
print("every degree group is contained in exactly one isomorphism class?", pure)
for dk in sorted(cross, key=lambda k: (-sum(cross[k].values()), str(k))):
    print("   degrees %s  ->  %d isomorphism classes, sizes %s"
          % (dk, len(cross[dk]), sorted(cross[dk].values(), reverse=True)))
print()
print("so: the two partitions are %s" % ("IDENTICAL" if pure and len(gdeg) == len(giso) else "DIFFERENT"))

print()
print("the exact structural fact: for the 64 bank worlds the sorted (in-degree, out-degree)"
      " multiset is a COMPLETE isomorphism invariant.")
for dk in sorted(gdeg, key=lambda k: -len(gdeg[k])):
    keys = gdeg[dk]
    w0 = worlds[keys[0]]
    refs = sorted(n["ref"] for n in w0["nodes"])
    idx = {r: i for i, r in enumerate(refs)}
    edges = sorted((idx[e["source"]], idx[e["target"]]) for e in w0["contains"])
    print("   size %2d held %d  degrees %s  shape edges %s" % (len(keys), sum(1 for k in keys if k in heldset), dk, edges))

print()
print("held worlds and their twin counts (worlds sharing their exact shape):")
for wid in heldworlds:
    twins = [k for k in giso[iso[wid]] if k != wid]
    print("   %s  shape %s  twin worlds %d  of which trained/bank %d"
          % (wid[-12:], iso[wid][1], len(twins), sum(1 for k in twins if k not in heldset)))
