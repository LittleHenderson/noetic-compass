"""R3 meeting check 6: 'same wiring, same slot' lookup baseline for held-back reach.
For each held reach record: find TRAINED reach records whose focus world has the identical rank-labelled edge set
and the same (rule, whole rank, part rank); predict their gold. Also an isomorphism-invariant variant is NOT used
(rank labels are what the machine sees). stdlib only."""
import json
from pathlib import Path
from collections import defaultdict, Counter
exec(open('m5_reach_rules.py').read().split("tab = defaultdict")[0])
def key(rid):
    q = reg[rid]['query']; nodes, E = graph(q['focus_world_id'])
    wiring = (len(nodes), tuple(sorted((rk(a), rk(b)) for a, b in E)))
    return wiring, (q['rule'], rk(q['arguments']['whole']), rk(q['arguments']['part']))
train_tab = defaultdict(Counter)
wirings_trained = Counter()
for rid in gold:
    if split[rid] == 'trained':
        w, s = key(rid); train_tab[(w, s)][next(iter(gold[rid]))] += 1; wirings_trained[w] += 1
res = Counter(); per_q = defaultdict(list)
for rid in gold:
    if split[rid] != 'held': continue
    w, s = key(rid); g = next(iter(gold[rid]))
    if (w, s) in train_tab:
        pred = train_tab[(w, s)].most_common(1)[0][0]; res['covered'] += 1; res['correct'] += int(pred == g)
        per_q[reg[rid]['query']['query_id']].append(pred == g)
    else:
        res['not_covered'] += 1; res['wiring_seen' if w in wirings_trained else 'wiring_unseen'] += 1
        per_q[reg[rid]['query']['query_id']].append(None)
print('held reach records 26 ->', dict(res))
for q, v in sorted(per_q.items()):
    if q in POP: print('frozen reach', q.split('-')[-1][:8], 'FLOOR' if q in FLOOR else 'NONFLOOR', v)
held_worlds = {reg[r]['query']['focus_world_id'] for r in gold if split[r] == 'held'}
print('held reach focus worlds', len(held_worlds), '; rank-labelled wiring identical to a trained reach world:', sum(1 for wid in held_worlds if (len(graph(wid)[0]), tuple(sorted((rk(a), rk(b)) for a, b in graph(wid)[1]))) in wirings_trained))
