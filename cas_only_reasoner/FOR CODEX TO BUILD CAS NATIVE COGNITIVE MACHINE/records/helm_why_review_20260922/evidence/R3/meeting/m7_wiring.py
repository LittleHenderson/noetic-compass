"""R3 meeting check 7: are the held reach worlds' RANK-LABELLED edge sets identical to any trained world (any kind)?
And are they isomorphic (unlabelled) to one? stdlib only."""
import json
from itertools import permutations
from pathlib import Path
exec(open('m5_reach_rules.py').read().split("tab = defaultdict")[0])
held_worlds = sorted({reg[r]['query']['focus_world_id'] for r in gold if split[r] == 'held'})
trained_worlds = sorted({reg[r]['query']['focus_world_id'] for r in reg if split.get(r) == 'trained'})
print('held reach worlds', len(held_worlds), '| worlds focused by any trained record', len(trained_worlds), '| overlap', len(set(held_worlds) & set(trained_worlds)))
def labelled(wid):
    nodes, E = graph(wid); return (len(nodes), frozenset((rk(a), rk(b)) for a, b in E))
def iso(a, b):
    (na, Ea), (nb, Eb) = labelled(a), labelled(b)
    if na != nb or len(Ea) != len(Eb): return False
    return any(frozenset((p[x], p[y]) for x, y in Ea) == Eb for p in permutations(range(na)))
for h in held_worlds:
    same_label = [t for t in trained_worlds if labelled(t) == labelled(h)]
    same_iso = [t for t in trained_worlds if iso(t, h)]
    print(h[6:14], 'nodes/edges', labelled(h)[0], sorted(labelled(h)[1]), '| trained worlds with IDENTICAL rank-labelled edges:', len(same_label), '| isomorphic trained worlds:', len(same_iso))
