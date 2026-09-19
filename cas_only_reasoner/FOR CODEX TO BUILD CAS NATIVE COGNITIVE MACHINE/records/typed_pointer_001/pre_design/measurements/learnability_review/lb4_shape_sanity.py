"""Sanity check on the bank's shape structure before any colour-refinement claim is made."""
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
print("worlds in bank:", len(worlds))
print("held worlds present in bank:", sum(1 for w in heldworlds if w in worlds))


def shape_key(w):
    """Relabeling-invariant exact shape: min over all labelings of the sorted edge set,
    keeping the node position assignment explicit."""
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = {(e["source"], e["target"]) for e in w["contains"]}
    best = None
    best_order = None
    for order in permutations(range(len(refs))):
        idx = {r: order[i] for i, r in enumerate(refs)}
        key = tuple(sorted((idx[a], idx[b]) for a, b in edges))
        if best is None or key < best:
            best, best_order = key, order
    return (len(refs), best), best_order


classes = defaultdict(list)
keys = {}
for wid in sorted(worlds):
    k, _ = shape_key(worlds[wid])
    keys[wid] = k
    classes[k].append(wid)
print("distinct shapes:", len(classes))
for k, v in sorted(classes.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    print("  shape nodes=%d edges=%s  count=%d  held-in-class=%d" % (k[0], k[1], len(v), sum(1 for w in v if w in heldworlds)))

print()
print("exact degrees per world (histogram of (in,out) pairs, multiset):")
degclasses = defaultdict(list)
for wid in sorted(worlds):
    w = worlds[wid]
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    sig = tuple(sorted((ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]))
    degclasses[sig].append(wid)
print("distinct degree multisets:", len(degclasses))
for sig, v in sorted(degclasses.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
    print("  ", sig, "count", len(v))

print()
print("distinct (nodes, edges) pairs:", Counter((len(worlds[w]["nodes"]), len(worlds[w]["contains"])) for w in worlds))
print("distinct node labels in whole bank:", len({n["label"] for w in worlds.values() for n in w["nodes"]}))
print("distinct declarations.domain:", Counter(w["declarations"]["domain"] for w in worlds.values()))
print("worlds sharing the same (nodes,edges) but different shape:",
      len([1 for i, a in enumerate(sorted(worlds)) for b in sorted(worlds)[i + 1:]
           if keys[a][0] == keys[b][0] and keys[a] != keys[b]]))
print()
print("held world shapes:", [keys[w] for w in heldworlds])
bank = sorted(set(worlds) - set(heldworlds))
print("bank world shapes:", Counter(keys[w] for w in bank))
print("a held world shares its exact shape with a bank world?",
      {w: sum(1 for b in bank if keys[b] == keys[w]) for w in heldworlds})
