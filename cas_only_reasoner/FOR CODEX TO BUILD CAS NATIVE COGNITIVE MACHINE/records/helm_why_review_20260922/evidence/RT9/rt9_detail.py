"""RT9 detail (after the verdict; descriptive only, not used for the verdict).
(a) For every multi-hop course reach record where the six runs do not all agree on correctness: question, split, hop,
    number of common neighbours of whole and part (2 = 'diamond', RT4 C24), gold, each run's prediction.
(b) Whole-answer identity (state + via) between runs on reach records, by hop.
Read-only, stdlib only, no torch."""
import io
import contextlib
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
    import rt9_count as R

short = lambda x: x.split('/')[-1] if x else ''
runs = [R.KEY((v, s)) for v, s, d in R.RUNS]


def n_cn(g):
    E = g['E']
    nodes = set(a for a, b in E) | set(b for a, b in E)
    return sorted(short(x) for x in nodes if x not in (g['whole'], g['part']) and (g['whole'], x) in E and (x, g['part']) in E)


print('(a) course multi-hop reach records where the six runs disagree on correctness')
print('    cols: qid[12:20] split hop rule CN-set gold | ' + ' '.join(runs))
rows = []
for rid in R.course_ids:
    g = R.GOLD[('course', rid)]
    if g['hop'] not in (2, 3):
        continue
    bits = [R.CORR[(k, 'course')][rid] for k in runs]
    if all(bits) or not any(bits):
        if not any(bits):
            rows.append(rid)
        continue
    rows.append(rid)
for rid in sorted(rows, key=lambda r: (R.GOLD[('course', r)]['qid'], r)):
    g = R.GOLD[('course', rid)]
    preds = []
    for k in runs:
        st, via = R.PRED[(k, 'course')][rid]
        preds.append(('ok ' if R.CORR[(k, 'course')][rid] else 'XX ') + (st or '?')[0] + short(via))
    print('   %s %-8s hop%s %s CN=%s gold=%s | %s' % (g['qid'][12:20], g['split'], g['hop'], g['rule'][:9], n_cn(g),
          g['ans'][0][0] + short(g['ans'][1]), '  '.join(preds)))

print('\n    summary: by question, the number of records and CN-set size')
byq = {}
for rid in rows:
    g = R.GOLD[('course', rid)]
    byq.setdefault(g['qid'][12:20], []).append((g['split'], len(n_cn(g))))
for q, v in sorted(byq.items()):
    print('     ', q, 'records', len(v), 'splits', dict(Counter(s for s, _ in v)), 'CN-set sizes', dict(Counter(n for _, n in v)))

print('\n(b) whole-answer identity (state+via) on reach records between run pairs, by hop (course all 107; dev 53)')
for panel, ids in (('course', R.course_ids), ('dev', R.dev_ids)):
    for a, b in (('2.0/18', '1.0/18'), ('2.0/18', '1.0/17'), ('2.0/18', '1.0/19'), ('2.0/18', '2.0/17'), ('2.0/18', '2.0/19'),
                 ('1.0/17', '1.0/18'), ('2.0/17', '1.0/19')):
        c = Counter()
        for rid in ids:
            h = R.GOLD[(panel, rid)]['hop']
            c[(h, R.PRED[(a, panel)][rid] == R.PRED[(b, panel)][rid])] += 1
        hops = sorted(set(h for h, _ in c), key=str)
        print('   %s %s vs %s: ' % (panel, a, b) + '  '.join('hop%s same %d/%d' % (h, c[(h, True)], c[(h, True)] + c[(h, False)]) for h in hops))

print('\n(c) diamond reach records (CN-set size 2) among all 107 course reach: by question and split')
dq = Counter()
for rid in R.course_ids:
    g = R.GOLD[('course', rid)]
    if len(n_cn(g)) >= 2:
        dq[(g['qid'][12:20], g['split'])] += 1
print('   ', sorted(dq.items()), 'total records', sum(dq.values()), 'questions', len(set(q for q, _ in dq)))
print('   primary-population diamond records (trained+held):', sum(v for (q, s), v in dq.items() if s in ('trained', 'held')))

print('\n(d) primary 2-hop counts with diamond records removed (descriptive, post-verdict)')
for k in runs:
    sel = [r for r in R.course_ids if R.GOLD[('course', r)]['split'] in ('trained', 'held') and R.GOLD[('course', r)]['hop'] == 2
           and len(n_cn(R.GOLD[('course', r)])) < 2]
    print('   %s: %d/%d' % (k, sum(R.CORR[(k, 'course')][r] for r in sel), len(sel)))
