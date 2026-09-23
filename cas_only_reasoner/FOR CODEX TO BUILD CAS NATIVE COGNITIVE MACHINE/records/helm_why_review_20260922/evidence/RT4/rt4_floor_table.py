"""RT4: what each untrained start (p00) answered on the five rank-last floor questions (held records only)."""
from collections import Counter
from rt4_common import *
g = J(T / 'admission_001/gate_reading.json')
rlast = g['oracle_ceilings']['rank_last_ids_the_rule_solves']
for q in rlast:
    rids = sorted(r for r in SPLIT if SPLIT[r] == 'held' and REG[r]['query']['query_id'] == q)
    Q = REG[rids[0]]['query']
    n = len(W[Q['focus_world_id']]['nodes'])
    args = {k: rk(v) for k, v in Q['arguments'].items()}
    print('q %s kind=%s rule=%s n=%d args=%s held records=%d' % (q[12:20], Q['kind'], Q['rule'][:12], n, args, len(rids)))
    for ver, seed, d in RUNS:
        P = preds(d, 'course_p00')
        S = scoring(d, 'course_p00')
        ans = Counter()
        for r in rids:
            v = P[r]['answer']['value']
            if Q['kind'] == 'reach':
                ans['%s%s' % (v['state'], '' if v.get('via') is None else '/n%d' % rk(v['via']))] += 1
            else:
                ans['nodes=%s' % sorted(rk(x) for x in v['nodes'])] += 1
        print('   p00 Helm %s %s: %s | all right: %s' % (ver, seed, dict(ans), all(S[r]['correct'] for r in rids)))
