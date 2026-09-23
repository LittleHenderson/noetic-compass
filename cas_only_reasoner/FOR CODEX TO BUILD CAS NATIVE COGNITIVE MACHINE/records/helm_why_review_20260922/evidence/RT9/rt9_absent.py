"""RT9 post-verdict, descriptive: can the ABSENT reach records be decided by one edge?
ONE_EDGE_ABSENT = whole has no child OR part has no parent (no path possible, visible from one edge set).
Otherwise deciding ABSENT needs the whole reachable set. Read-only, stdlib only, no torch."""
import io, contextlib
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
    import rt9_count as R
runs = [R.KEY((v, s)) for v, s, d in R.RUNS]
for panel, ids in (('course', R.course_ids), ('dev', R.dev_ids)):
    groups = {}
    for rid in ids:
        g = R.GOLD[(panel, rid)]
        if g['ans'][0] != 'ABSENT':
            continue
        E = g['E']
        outd = sum(1 for a, b in E if a == g['whole'])
        ind = sum(1 for a, b in E if b == g['part'])
        k = 'ONE_EDGE_ABSENT' if (outd == 0 or ind == 0) else 'NEEDS_REACHABILITY'
        groups.setdefault((k, 'whole_out=%d' % outd, 'part_in=%d' % ind), []).append(rid)
    for k, sel in sorted(groups.items()):
        print(panel, k, 'n=%d' % len(sel), ' | ' + '  '.join('%s %d' % (r, sum(R.CORR[(r, panel)][x] for x in sel)) for r in runs))
