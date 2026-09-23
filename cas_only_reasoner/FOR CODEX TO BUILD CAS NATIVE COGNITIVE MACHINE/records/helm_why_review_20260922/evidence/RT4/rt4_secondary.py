"""RT4 secondary (NOT the pre-registered verdict): split the disagreement sets by whether the common neighbour is
unique (n_cn == 1) or tied (n_cn == 2, a 'diamond'), and look at how ties are broken."""
from collections import Counter, defaultdict
from rt4_common import *
from rt4_cues import LOCAL, analyse, summarize, verdict

rows = analyse('course_p10', RUNS)
# (a) the checker gold equals the lexfirst common neighbour on every CN-defined record?
PRED = {(v, s, ph): preds(d, ph) for v, s, d in RUNS for ph in ('course_p00', 'course_p01', 'course_p10')}
SCO = {(v, s, ph): scoring(d, ph) for v, s, d in RUNS for ph in ('course_p00', 'course_p01', 'course_p10')}
gold = defaultdict(set)
for key, S in SCO.items():
    for rid, r in S.items():
        if r['kind'] == 'reach' and r['correct']:
            v = PRED[key][rid]['answer']['value']
            gold[rid].add((v['state'], None if v.get('via') is None else rk(v['via'])))
recs = [rid for rid, r in REG.items() if r['query']['kind'] == 'reach']
agree = Counter()
for rid in recs:
    c, m = cues(rid)
    if c['CN'] is None:
        continue
    g = next(iter(gold[rid]))
    agree[(m['n_cn'], g == ('VIA', c['CN']))] += 1
print('(a) CN-defined records: (number of common neighbours, gold == VIA/lexfirst-CN) ->', dict(agree))

# (b) the pre-registered D_k analysis restricted to records with a UNIQUE common neighbour, and to TIED ones
uni = [r for r in rows if r[4]['n_cn'] == 1]
tie = [r for r in rows if r[4]['n_cn'] == 2]
res, un = summarize(uni, LOCAL, '(b1) POOLED p10, records with ONE common neighbour only')
print('   rule applied to this subset (secondary):', verdict(res, un))
for run in RUNS:
    rr = [r for r in uni if r[0] == run[:2]]
    d = [r for r in rr if any(r[3][k] is not None and r[3][k] != r[3]['CN'] for k in LOCAL)]
    print('   run %s/%s unique-CN records disagreeing with >=1 node-local cue: VIA==CN %d/%d' % (
        run[0], run[1], sum(r[2] == r[3]['CN'] for r in d), len(d)))
res, un = summarize(tie, LOCAL, '(b2) POOLED p10, records with TWO common neighbours (diamond ties) only')
print('   rule applied to this subset (secondary):', verdict(res, un))

# (c) diamond ties: which of the two common neighbours is picked, versus participant rank, per run and rule
print('\n(c) diamond records: the two common neighbours, their input flags, and each run\'s pick at p10')
tq = sorted({(r[4]['qid'], r[1]) for r in tie})
seen_q = set()
for qid, rid in tq:
    if qid in seen_q:
        continue
    seen_q.add(qid)
    c, m = cues(rid)
    w = W[m['world']]
    wholedecl = rk(w['declared_whole'])
    E = m['E']
    cn = [x for x in m['C'] if (m['whole'], x) in E and (x, m['part']) in E]
    feats = {x: dict(prank=m['prank'].get(x, 0), declared_whole=int(x == wholedecl),
                     indeg=sum(1 for s, t in E if t == x), outdeg=sum(1 for s, t in E if s == x)) for x in cn}
    nrec = sum(1 for q, r in tq if q == qid)
    picks = []
    for ver, seed, d in RUNS:
        v = via_rank(PRED[(ver, seed, 'course_p10')][rid])
        hi = max(cn, key=lambda x: m['prank'].get(x, 0))
        picks.append('%s/%s:n%s(%s)' % (ver, seed[-2:], v, 'hiPR' if v == hi else ('loPR' if v in cn else 'other')))
    print(' q %s %s records=%d split=%s whole=n%d part=n%d CNs=%s feats=%s gold=%s | %s' % (
        qid[12:20], m['rule'][:9], nrec, m['split'], m['whole'], m['part'], cn, feats, sorted(gold[rid]), ' '.join(picks)))

# (d) are the two tied common neighbours ever identical in every input flag (so only float noise could separate them)?
same = 0
for qid, rid in tq:
    c, m = cues(rid)
    cn = [x for x in m['C'] if (m['whole'], x) in m['E'] and (x, m['part']) in m['E']]
    if len({m['prank'].get(x, 0) for x in cn}) == 1:
        same += 1
print('\n(d) diamond records whose two common neighbours carry the SAME participant rank:', same, 'of', len(tq))
print('    VIA==CN misses at p10 (all runs) split by tie status: unique-CN %d, diamond %d' % (
    sum(1 for r in uni if r[3]['CN'] is not None and r[2] != r[3]['CN']),
    sum(1 for r in tie if r[2] != r[3]['CN'])))
