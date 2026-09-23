"""RT4 secondary: (1) VIA answers on records with no common neighbour (3-hop): whole's child vs part's parent, by rule;
(2) the five ablation prediction files of each run (26 held reach records); (3) p00 cue agreement."""
from collections import Counter, defaultdict
from rt4_common import *
from rt4_cues import LOCAL, analyse, summarize, verdict

def hops_of(rid, S):
    r = S[rid]
    if r['witnesses'] and (r['witnesses'][0].get('evidence') or {}).get('path'):
        return len(r['witnesses'][0]['evidence']['path']) - 1
    return None
SCO10 = {(v, s): scoring(d, 'course_p10') for v, s, d in RUNS}
# (1)
print('(1) p10 VIA answers on records with NO common neighbour, by rule and whether VIA = whole\'s child (WC) / part\'s parent (PP)')
tab = Counter()
for ver, seed, d in RUNS:
    P = preds(d, 'course_p10')
    for rid, p in P.items():
        if p['answer']['kind'] != 'reach':
            continue
        v = via_rank(p)
        if v is None:
            continue
        c, m = cues(rid)
        if c['CN'] is not None:
            continue
        E = m['E']
        wc = [x for x in m['C'] if (m['whole'], x) in E]
        pp = [x for x in m['C'] if (x, m['part']) in E]
        h = hops_of(rid, SCO10[(ver, seed)])
        tab[(m['rule'][:9], 'hops', h, 'VIA==WC' if v in wc else '-', 'VIA==PP' if v in pp else '-',
             'correct' if SCO10[(ver, seed)][rid]['correct'] else 'WRONG')] += 1
for k, v in sorted(tab.items(), key=str):
    print('  ', k, v)

# (2) ablations
print('\n(2) ablation files: 26 held reach records per run; pooled over six runs')
ABL = ['ablation_baseline', 'ablation_round_mix', 'ablation_core_block', 'ablation_query_and_readout', 'ablation_heads']
for ab in ABL:
    rows = analyse(ab, RUNS)
    st = Counter()
    for ver, seed, d in RUNS:
        for rid, p in preds(d, ab).items():
            if p['answer']['kind'] == 'reach':
                st[p['answer']['value']['state']] += 1
    print('  %s reach answer states pooled: %s' % (ab, dict(st)))
    res, un = summarize(rows, LOCAL, '%s pooled six runs (held reach only)' % ab)
    print('   rule applied (secondary, ablated model):', verdict(res, un))
    uni = [r for r in rows if r[4]['n_cn'] == 1]
    print('   unique-CN records: VIA==CN %d/%d' % (sum(r[2] == r[3]['CN'] for r in uni), len(uni)))
# baseline == p10 on held records?
same = Counter()
for ver, seed, d in RUNS:
    a = preds(d, 'ablation_baseline'); b = preds(d, 'course_p10')
    for rid in a:
        same[a[rid]['answer']['value'] == b[rid]['answer']['value']] += 1
print('  ablation_baseline answer == course_p10 answer on the same record (all kinds, 6 runs):', dict(same))

# (3) p00
print('\n(3) p00 (untrained start) cue agreement, pooled and per run')
rows = analyse('course_p00', RUNS)
res, un = summarize(rows, LOCAL, 'course_p00 pooled six runs')
for run in RUNS:
    rr = [r for r in rows if r[0] == run[:2]]
    print('   run %s/%s VIA-answered reach records at p00: %d of 107' % (run[0], run[1], len(rr)))
