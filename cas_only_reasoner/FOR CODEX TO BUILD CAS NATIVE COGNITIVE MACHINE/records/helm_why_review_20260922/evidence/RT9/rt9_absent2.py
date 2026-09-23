"""RT9 post-verdict: predicted answer states on the 29 dev ABSENT records that need reachability. stdlib only, no torch."""
import io, contextlib
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
    import rt9_count as R
runs = [R.KEY((v, s)) for v, s, d in R.RUNS]
sel = []
for rid in R.dev_ids:
    g = R.GOLD[('dev', rid)]
    if g['ans'][0] != 'ABSENT':
        continue
    E = g['E']
    if sum(1 for a, b in E if a == g['whole']) > 0 and sum(1 for a, b in E if b == g['part']) > 0:
        sel.append(rid)
print('dev ABSENT records needing reachability:', len(sel), 'questions:', len(set(R.GOLD[('dev', r)]['qid'] for r in sel)))
for k in runs:
    print(' ', k, dict(Counter(R.PRED[(k, 'dev')][r][0] for r in sel)))
