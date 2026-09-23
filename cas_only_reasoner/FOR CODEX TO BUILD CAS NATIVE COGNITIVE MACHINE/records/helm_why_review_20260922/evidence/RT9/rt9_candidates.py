"""RT9 post-verdict, descriptive: how much path information does a multi-hop reach answer actually need?
Under the checker's rules the gold VIA node is always one edge from an argument:
  first_direct_constituent_lexical_v1 -> a child of the whole (checker.py:136-141)
  bfs_immediate_predecessor_lexical_v1 -> path[-2], a parent of the part (checker.py:143-149)
So the candidates are: children of the whole (first_dir) or parents of the part (bfs), minus argument nodes.
For each multi-hop course/dev reach record: candidate count, and how many candidates lie on SOME whole->part path.
  ONE_CANDIDATE     : a one-edge rule ('the only child of the whole' / 'the only parent of the part') gives the gold.
  PATH_DECIDES      : >= 2 candidates, exactly one lies on a whole->part path -> path information is needed.
  TIE_BY_LABEL      : >= 2 candidates on a path -> gold chosen by sorted reference (label/rank order).
Then correctness of each run per class. Read-only, stdlib only, no torch."""
import io
import contextlib
from collections import Counter, defaultdict
with contextlib.redirect_stdout(io.StringIO()):
    import rt9_count as R

runs = [R.KEY((v, s)) for v, s, d in R.RUNS]


def reach_set(E, start):
    adj = defaultdict(list)
    for a, b in E:
        adj[a].append(b)
    seen, st = {start}, [start]
    while st:
        x = st.pop()
        for y in adj[x]:
            if y not in seen:
                seen.add(y)
                st.append(y)
    return seen


def klass(g):
    E = g['E']
    wh, pa = g['whole'], g['part']
    if g['rule'].startswith('first_direct'):
        cands = [x for (a, x) in E if a == wh and x not in (wh, pa)]
        on_path = [x for x in cands if pa in reach_set(E, x)]
    else:
        cands = [x for (x, b) in E if b == pa and x not in (wh, pa)]
        from_whole = reach_set(E, wh)
        on_path = [x for x in cands if x in from_whole]
    if len(cands) == 1:
        return 'ONE_CANDIDATE', len(cands), len(on_path)
    if len(on_path) == 1:
        return 'PATH_DECIDES', len(cands), len(on_path)
    return 'TIE_BY_LABEL', len(cands), len(on_path)


for panel, ids, flt, lab in (('course', R.course_ids, lambda g: g['split'] in ('trained', 'held'), 'course trained+held'),
                              ('course', R.course_ids, lambda g: g['split'] == 'excluded', 'course excluded'),
                              ('dev', R.dev_ids, lambda g: True, 'dev panel')):
    print('== %s: multi-hop VIA records by (hop, class, n_candidates, n_on_path)' % lab)
    groups = defaultdict(list)
    for rid in ids:
        g = R.GOLD[(panel, rid)]
        if not flt(g) or g['ans'][0] != 'VIA':
            continue
        k, nc, npth = klass(g)
        groups[(g['hop'], k)].append(rid)
        groups[('detail', g['hop'], k, nc, npth)].append(rid)
    for key in sorted((k for k in groups if k[0] != 'detail'), key=str):
        sel = groups[key]
        qs = sorted(set(R.GOLD[(panel, r)]['qid'][12:20] for r in sel))
        print('  hop%s %-13s n=%2d questions=%d | ' % (key[0], key[1], len(sel), len(qs)) +
              '  '.join('%s %d' % (k, sum(R.CORR[(k, panel)][r] for r in sel)) for k in runs))
    for key in sorted((k for k in groups if k[0] == 'detail'), key=str):
        print('     detail', key[1:], len(groups[key]))
