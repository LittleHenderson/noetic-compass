"""RT4 detail: which records drive each disagreement set; bank-level cue coincidence; the no-CN VIA records."""
from collections import Counter, defaultdict
from rt4_common import *
from rt4_cues import LOCAL

# 1. Bank-level: over ALL 107 reach records (not only VIA-answered), how often each node-local cue can differ from CN
recs = [rid for rid, r in REG.items() if r['query']['kind'] == 'reach']
print('reach records in registry:', len(recs), '| distinct questions:', len({REG[r]['query']['query_id'] for r in recs}))
cnt = Counter()
for rid in recs:
    c, m = cues(rid)
    cnt[('CN defined', c['CN'] is not None, 'direct edge', m['direct'])] += 1
    if c['CN'] is not None:
        cnt[('n nodes', m['n'], 'n_cn', m['n_cn'], 'n_part_parents_in_C', m['n_pp'], 'n_parent&child_in_C', m['n_pc'])] += 1
        for k in LOCAL:
            cnt[('cue', k, 'defined', c[k] is not None, 'differs from CN', c[k] is not None and c[k] != c['CN'])] += 1
for k, v in sorted(cnt.items(), key=str):
    print('  ', k, v)

# 2. Gold per record, from any correct scoring row with a witness (checker evidence), over all six runs, p00..p10 course files
gold = {}
for ver, seed, d in RUNS:
    for ph in ('course_p00', 'course_p01', 'course_p10'):
        for rid, r in scoring(d, ph).items():
            if r['kind'] != 'reach' or not r['correct']:
                continue
            p = preds(d, ph)[rid] if False else None
            gold.setdefault(rid, set())
PRED = {(ver, seed, ph): preds(d, ph) for ver, seed, d in RUNS for ph in ('course_p00', 'course_p01', 'course_p10')}
SCO = {(ver, seed, ph): scoring(d, ph) for ver, seed, d in RUNS for ph in ('course_p00', 'course_p01', 'course_p10')}
gold = defaultdict(set)
for key, S in SCO.items():
    for rid, r in S.items():
        if r['kind'] == 'reach' and r['correct']:
            v = PRED[key][rid]['answer']['value']
            gold[rid].add((v['state'], None if v.get('via') is None else rk(v['via'])))
print('reach records with a known correct answer (from any correct prediction in 18 course files):', len(gold), 'of', len(recs),
      '| any record with 2 different correct answers:', sum(len(g) > 1 for g in gold.values()))

# 3. Disagreement records in detail (p10)
def show(k):
    print('\n--- D_%s records (CN defined, %s defined, differ) ---' % (k, k))
    for rid in sorted(recs, key=lambda r: (REG[r]['query']['query_id'], r)):
        c, m = cues(rid)
        if c['CN'] is None or c[k] is None or c['CN'] == c[k]:
            continue
        vias = []
        for ver, seed, d in RUNS:
            p = PRED[(ver, seed, 'course_p10')][rid]
            v = p['answer']['value']
            vias.append('%s:%s' % (ver + '/' + seed[-2:], v['state'][0] + ('' if v.get('via') is None else str(rk(v['via'])))))
        g = sorted(gold.get(rid, []))
        print(' q %s rec %s %-8s %s n=%d whole=%d part=%d edges=%s prank=%s | CN=%d %s=%d direct=%s | gold=%s | p10 %s' % (
            m['qid'][12:20], rid[12:20], m['split'], m['rule'][:9], m['n'], m['whole'], m['part'], sorted(m['E']),
            dict(sorted(m['prank'].items())), c['CN'], k, c[k], m['direct'], g, ' '.join(vias)))
for k in ('HPR', 'RF', 'RL'):
    show(k)

# 4. VIA answers on records where CN is undefined (3-hop, direct, absent): compare with gold and cues
print('\n--- p10 VIA answers where CN is undefined ---')
tab = Counter()
for ver, seed, d in RUNS:
    for rid, p in PRED[(ver, seed, 'course_p10')].items():
        if p['answer']['kind'] != 'reach':
            continue
        v = via_rank(p)
        if v is None:
            continue
        c, m = cues(rid)
        if c['CN'] is not None:
            continue
        g = gold.get(rid)
        gs = sorted(g)[0] if g else None
        tab[('correct' if SCO[(ver, seed, 'course_p10')][rid]['correct'] else 'wrong', 'gold', gs[0] if gs else None,
             'VIA==RL' if v == c['RL'] else '', 'VIA==PP' if v == c['PP'] else '', 'VIA==PC' if v == c['PC'] else '')] += 1
for k, v in sorted(tab.items(), key=str):
    print('  ', k, v)
