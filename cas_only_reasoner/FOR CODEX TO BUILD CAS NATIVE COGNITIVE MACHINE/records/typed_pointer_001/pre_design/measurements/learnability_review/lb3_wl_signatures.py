"""LB3 (corrected) — 1-WL colour refinement over the real node colouring of section 2.1.

This replaces an earlier version whose refinement routine silently never ran: it compared
colour-class COUNTS for the fixed-point test, so two non-isomorphic shapes with the same
degree profile were reported as indistinguishable. The routine here uses the PARTITION test
("do a and b have the same colour for every pair?"), which is the definition of a fixed
point, and it was validated against six synthetic shapes with known colour structure
(lb5_refine_debug) before any count was taken.

Colourings:
  A  flags only        : (in-deg, out-deg, is_declared_whole, participant rank, primary rank)
  B  A + label text    : the node's label string is part of its colour
  C  A + ref rank      : the node's rank among the world's sorted refs
  D  B + C
Groups: the 5 held worlds, the 59 remaining bank worlds, and every (held, bank) pair.
"""
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
heldworlds = sorted(c.held_worlds(frozen))
bankonly = sorted(set(worlds) - set(heldworlds))
print("bank %d ; held %d ; bank-minus-held %d" % (len(worlds), len(heldworlds), len(bankonly)))


def graph(w):
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = sorted((e["source"], e["target"]) for e in w["contains"])
    return refs, edges


def iso_class(w):
    refs, edges = graph(w)
    n = len(refs)
    best = None
    for order in permutations(range(n)):
        idx = {r: order[i] for i, r in enumerate(refs)}
        key = tuple(sorted((idx[a], idx[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (n, best)


CANON = {wid: iso_class(w) for wid, w in worlds.items()}
CLASSOF = defaultdict(list)
for wid in sorted(worlds):
    CLASSOF[CANON[wid]].append(wid)
print("isomorphism classes: %d ; sized %s" % (len(CLASSOF), sorted(Counter(len(v) for v in CLASSOF.values()).items())))


def initial(w, *, text, refrank):
    refs, edges = graph(w)
    decl = w["declarations"]
    ind, outd = Counter(), Counter()
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    part = sorted(decl["participants"])
    prim = list(decl["primary_labels"])
    rk = {r: i + 1 for i, r in enumerate(refs)}
    out = {}
    for node in w["nodes"]:
        r = node["ref"]
        bits = [ind.get(r, 0), outd.get(r, 0), int(r == w["declared_whole"]),
                part.index(r) + 1 if r in part else 0,
                prim.index(r) + 1 if r in prim else 0]
        if refrank:
            bits.append(rk[r])
        if text:
            bits.append(node["label"])
        out[r] = tuple(str(b) for b in bits)
    return out, refs, edges


def refine(colour, refs, edges, max_rounds=10):
    """1-WL with distinct parent/child messages. Fixed point tested on the PARTITION."""
    parent, child = defaultdict(list), defaultdict(list)
    for a, b in edges:
        child[a].append(b)
        parent[b].append(a)
    cur = dict(colour)
    rounds = 0
    for _ in range(max_rounds):
        rounds += 1
        key = {r: (cur[r], tuple(sorted(cur[p] for p in parent[r])), tuple(sorted(cur[ch] for ch in child[r])))
               for r in refs}
        table = {k: i for i, k in enumerate(sorted(set(key.values())))}
        nxt = {r: table[key[r]] for r in refs}
        same_partition = all((nxt[a] == nxt[b]) == (cur[a] == cur[b]) for a in refs for b in refs)
        cur = nxt
        if same_partition:
            break
    return cur, rounds


def signature(col, refs, edges):
    """The multiset signature a mean-pooled, colour-conditioned readout can see.

    Sorted (in-degree, out-degree) multiset, then the size of the colour class each
    (in,out) degree foot sits in, compared as a sorted multiset. Two worlds are
    indistinguishable at this level exactly when these agree. NOTE: counting only the
    sizes of the colour classes is NOT enough -- two worlds can have the same class-size
    pattern and different classes, which merges non-isomorphic shapes. That was the bug
    in the first version of this script.
    """
    ind, outd = Counter(), Counter()
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    cls = Counter(col[r] for r in refs)
    deg_hist = Counter((ind.get(r, 0), outd.get(r, 0)) for r in refs)
    return (tuple(sorted(deg_hist.items())),
            tuple(sorted((col[r], cls[col[r]]) for r in refs)))


for label, kw in (("A flags only", dict(text=False, refrank=False)),
                  ("B flags + label text", dict(text=True, refrank=False)),
                  ("C flags + ref rank", dict(text=False, refrank=True)),
                  ("D flags + text + rank", dict(text=True, refrank=True))):
    sig, rounds, classes = {}, {}, {}
    for wid, w in worlds.items():
        col0, refs, edges = initial(w, **kw)
        col, r = refine(col0, refs, edges)
        sig[wid] = signature(col, refs, edges)
        classes[wid] = len(set(col.values()))
        rounds[wid] = r
    groups = [("held-internal", heldworlds), ("bank-minus-held-internal", bankonly)]
    cross = [(a, b) for a in heldworlds for b in bankonly]
    print()
    print("=== colouring %s ===" % label)
    print("   rounds to fixed point: max %d, distribution %s"
          % (max(rounds.values()), dict(sorted(Counter(rounds.values()).items()))))
    print("   colour classes per world: min %d max %d" % (min(classes.values()), max(classes.values())))
    print("   distinct signatures over the 64 bank worlds: %d ; group-size histogram %s"
          % (len(set(sig.values())), dict(sorted(Counter(Counter(sig.values()).values()).items()))))
    for name, group in groups:
        pairs = [(a, b) for i, a in enumerate(group) for b in group[i + 1:]]
        ind = sum(1 for a, b in pairs if sig[a] == sig[b])
        noniso = sum(1 for a, b in pairs if sig[a] == sig[b] and CANON[a] != CANON[b])
        print("   %-24s %d/%d indistinguishable ; of those NON-isomorphic %d"
              % (name, ind, len(pairs), noniso))
    ind = sum(1 for a, b in cross if sig[a] == sig[b])
    noniso = sum(1 for a, b in cross if sig[a] == sig[b] and CANON[a] != CANON[b])
    print("   %-24s %d/%d indistinguishable ; of those NON-isomorphic %d"
          % ("cross held vs bank", ind, len(cross), noniso))
    # the collapse a graph-blind pooled vector would cause
    collapse = Counter(sig.values())
    big = max(collapse.values())
    print("   largest signature group: %d worlds ; worlds in signature groups of size > 1: %d"
          % (big, sum(v for v in collapse.values() if v > 1)))
    # pairing detail: which world pairs share a signature AND are isomorphic
    share_iso = sum(1 for a, b in [(x, y) for i, x in enumerate(sorted(worlds)) for y in sorted(worlds)[i + 1:]]
                    if sig[a] == sig[b] and CANON[a] == CANON[b])
    share_non = sum(1 for a, b in [(x, y) for i, x in enumerate(sorted(worlds)) for y in sorted(worlds)[i + 1:]]
                    if sig[a] == sig[b] and CANON[a] != CANON[b])
    print("   over all 2016 bank pairs: same signature and isomorphic %d ; same signature and NOT %d"
          % (share_iso, share_non))

print()
print("=== the shape identity of the corpus, for the record ===")
for cls, members in sorted(CLASSOF.items(), key=lambda kv: -len(kv[1])):
    refs, edges = graph(worlds[members[0]])
    print("   class of %2d worlds ; shape %s ; held in class %d" % (len(members), cls[1], sum(1 for m in members if m in set(heldworlds))))
print("held worlds and their twin counts inside the bank:")
for wid in heldworlds:
    print("   %s : class size %d, bank twins %d"
          % (wid[-12:], len(CLASSOF[CANON[wid]]), sum(1 for m in CLASSOF[CANON[wid]] if m != wid and m in set(bankonly))))
