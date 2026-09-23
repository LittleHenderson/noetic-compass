"""RT9: does Helm 2.0 seed 20260918 (the one open loop) answer multi-hop reach better than 2.0 seeds 20260917/20260919
and than its own Helm 1.0 run?  Read-only, stdlib only, NO torch, NO model load. Public bank only.
Definitions fixed in 00_PRE_RUN_DEFINITIONS.txt (sha256 995e6b6a...) before this script was run."""
import json
import io
import contextlib
from pathlib import Path
from collections import deque, Counter

ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT / 'records/typed_pointer_001'
J = lambda p: json.loads(Path(p).read_bytes())
RUNS = [('2.0', '20260917', 'receipt_20260917'), ('2.0', '20260918', 'receipt_20260918'), ('2.0', '20260919', 'receipt_20260919'),
        ('1.0', '20260917', 'receipt_helm1_certified_20260917'), ('1.0', '20260918', 'receipt_helm1_certified_20260918'),
        ('1.0', '20260919', 'receipt_helm1_certified_20260919')]
KEY = lambda r: '%s/%s' % (r[0], r[1][-2:])


# ---------- re-implementation of the frozen checker's reach rule (checker.py:72-153) ----------
def c_nodes(world):
    return sorted(n['ref'] for n in world['nodes'])


def c_edges(world):
    return frozenset((e['source'], e['target']) for e in world['contains'])


def c_adj(world):
    res = {n: [] for n in c_nodes(world)}
    for a, b in sorted(c_edges(world)):
        res[a].append(b)
    return res


def c_bfs(adj, start, goal):
    q, seen = deque([[start]]), {start}
    while q:
        path = q.popleft()
        if path[-1] == goal:
            return path, sorted(seen)
        for ch in adj[path[-1]]:
            if ch not in seen:
                seen.add(ch)
                q.append(path + [ch])
    return None, sorted(seen)


def c_reach(world, query):
    whole, part = query['arguments']['whole'], query['arguments']['part']
    adj = c_adj(world)
    if part in adj[whole]:
        return ('DIRECT', None), [whole, part], None
    if query['rule'] == 'first_direct_constituent_lexical_v1':
        for first in adj[whole]:
            suf, _ = c_bfs(adj, first, part)
            if suf is not None:
                return ('VIA', first), [whole] + suf, None
        _, visited = c_bfs(adj, whole, part)
    else:
        assert query['rule'] == 'bfs_immediate_predecessor_lexical_v1', query['rule']
        path, visited = c_bfs(adj, whole, part)
        if path is not None:
            return ('VIA', path[-2]), path, None
    return ('ABSENT', None), None, visited


# ---------- public inputs ----------
course = J(ROOT / 'records/typed_course_001/checks_002/public_course.json')
W = {w['world_id']: w for w in course['bank']['worlds']}
REG = {r['record_id']: r for r in course['registry']}
pm = J(T / 'receipt_20260917/collected/results/artifacts/protocol_material.json')
SPLIT = {**{r: 'held' for r in pm['held_back_record_ids']}, **{r: 'trained' for r in pm['trained_record_ids']},
         **{r: 'excluded' for r in pm['excluded_record_ids']}}
DEVP = {p['record']['record_id']: p for p in pm['development']['packets']}
for v, s, d in RUNS:
    pmx = J(T / d / 'collected/results/artifacts/protocol_material.json')
    assert pmx['held_back_record_ids'] == pm['held_back_record_ids'] and pmx['trained_record_ids'] == pm['trained_record_ids'] \
        and pmx['excluded_record_ids'] == pm['excluded_record_ids'], d
    assert json.dumps(pmx['development']['packets'], sort_keys=True) == json.dumps(pm['development']['packets'], sort_keys=True), d
print('protocol_material split ids and development packets identical in all six receipts: True')

GOLD = {}


def gold_for(panel, rid):
    if (panel, rid) in GOLD:
        return GOLD[(panel, rid)]
    if panel == 'course':
        q = REG[rid]['query']
        world = W[q['focus_world_id']]
    else:
        q = DEVP[rid]['record']['query']
        worlds = {w['world_id']: w for w in DEVP[rid]['source']['worlds']}
        world = worlds[q['focus_world_id']]
    ans, path, visited = c_reach(world, q)
    g = dict(ans=ans, path=path, visited=visited, hop=(len(path) - 1) if path else 'none', rule=q['rule'],
             n=len(world['nodes']), whole=q['arguments']['whole'], part=q['arguments']['part'], qid=q['query_id'],
             split=SPLIT.get(rid, '?') if panel == 'course' else 'dev', E=c_edges(world))
    GOLD[(panel, rid)] = g
    return g


def pred_val(p):
    v = p['answer']['value']
    return (v.get('state'), v.get('via'))


# ---------- load and validate ----------
CORR = {}
PRED = {}
v1 = Counter()
v2 = Counter()
v1_bad = []
v2_bad = []
for v, s, d in RUNS:
    for panel, fname in (('course', 'course_p10'), ('dev', 'development_p10')):
        sc = J(T / d / 'checkpoints' / (fname + '_scoring.json'))
        pr = {p['record_id']: p for p in J(T / d / 'checkpoints' / (fname + '_predictions.json'))['predictions']}
        cmap = {}
        pmap = {}
        for r in sc['rows']:
            if r['kind'] != 'reach':
                continue
            rid = r['record_id']
            g = gold_for(panel, rid)
            ok = bool(r['correct'])
            cmap[rid] = ok
            pv = pred_val(pr[rid])
            pmap[rid] = pv
            mine = (pv == g['ans'])
            v2[mine == ok] += 1
            if mine != ok:
                v2_bad.append((KEY((v, s)), panel, rid, pv, g['ans'], ok))
            if r['witnesses']:
                ev = r['witnesses'][0].get('evidence') or {}
                if 'path' in ev:
                    same = ev['path'] == g['path']
                else:
                    same = (g['path'] is None and ev.get('reachable_nodes_including_start') == g['visited'])
                v1[same] += 1
                if not same:
                    v1_bad.append((KEY((v, s)), panel, rid, ev, g['path']))
        CORR[(KEY((v, s)), panel)] = cmap
        PRED[(KEY((v, s)), panel)] = pmap
print('(v1) written witnesses equal to my recomputed gold path/closure: %s ; first mismatches: %s' % (dict(v1), v1_bad[:5]))
print('(v2) my gold answer reproduces the scoring correct bit (reach rows, 6 runs x course+dev): %s ; first mismatches: %s' % (dict(v2), v2_bad[:5]))
VALID = (not v1_bad) and (not v2_bad)
print('VALIDATION PASSED:', VALID)

# ---------- population summary ----------
course_ids = sorted(CORR[('2.0/17', 'course')])
dev_ids = sorted(CORR[('2.0/17', 'dev')])
for k in CORR:
    assert sorted(CORR[k]) == (course_ids if k[1] == 'course' else dev_ids), k
print('\ncourse reach records: %d ; dev panel reach records: %d (same record set in all six runs: True)' % (len(course_ids), len(dev_ids)))
print('course reach by (split, hop):', sorted(Counter((GOLD[('course', r)]['split'], GOLD[('course', r)]['hop']) for r in course_ids).items(), key=str))
print('course reach by (rule, hop):', sorted(Counter((GOLD[('course', r)]['rule'][:9], GOLD[('course', r)]['hop']) for r in course_ids).items(), key=str))
print('course reach gold state by hop:', sorted(Counter((GOLD[('course', r)]['hop'], GOLD[('course', r)]['ans'][0]) for r in course_ids).items(), key=str))
print('dev panel reach by (hop):', sorted(Counter(GOLD[('dev', r)]['hop'] for r in dev_ids).items(), key=str))
print('dev panel reach by (rule, hop, n_nodes):', sorted(Counter((GOLD[('dev', r)]['rule'][:9], GOLD[('dev', r)]['hop'], GOLD[('dev', r)]['n']) for r in dev_ids).items(), key=str))
print('dev panel reach gold state:', dict(Counter(GOLD[('dev', r)]['ans'][0] for r in dev_ids)))


def table(pop_filter, panel, label):
    print('\n== %s' % label)
    out = {}
    ids = course_ids if panel == 'course' else dev_ids
    hops_here = sorted(set(GOLD[(panel, r)]['hop'] for r in ids if pop_filter(GOLD[(panel, r)])), key=str)
    for v, s, d in RUNS:
        k = KEY((v, s))
        cm = CORR[(k, panel)]
        row = {}
        for h in hops_here:
            sel = [r for r in ids if pop_filter(GOLD[(panel, r)]) and GOLD[(panel, r)]['hop'] == h]
            row[h] = (sum(cm[r] for r in sel), len(sel))
        out[k] = row
        print('  Helm %s seed 202609%s  ' % (v, s[-2:]) + '  '.join('hop%s %d/%d' % (h, c, t) for h, (c, t) in row.items())
              + '   total %d/%d' % (sum(c for c, t in row.values()), sum(t for c, t in row.values())))
    return out


PRIMARY = table(lambda g: g['split'] in ('trained', 'held'), 'course', 'PRIMARY: course p10 reach, trained + held-back combined')
table(lambda g: g['split'] == 'trained', 'course', 'course p10 reach, trained only')
HELD = table(lambda g: g['split'] == 'held', 'course', 'course p10 reach, held-back only')
EXC = table(lambda g: g['split'] == 'excluded', 'course', 'course p10 reach, excluded only (not in verdict)')
DEV = table(lambda g: True, 'dev', 'dev panel p10 reach (ten-node panel; not in verdict)')


# ---------- outcome rules ----------
def H(tab, k, h):
    return tab[k].get(h, (0, 0))[0]


def apply_rules(tab, label):
    h3 = {k: H(tab, k, 3) for k in tab}
    h2 = {k: H(tab, k, 2) for k in tab}
    r1 = (h3['2.0/18'] - h3['2.0/17'] >= 2) and (h3['2.0/18'] - h3['2.0/19'] >= 2) and (h3['2.0/18'] - h3['1.0/18'] >= 2)
    r2 = all(abs(h2['2.0/18'] - h2[o]) <= 1 for o in ('2.0/17', '2.0/19')) and all(abs(h3['2.0/18'] - h3[o]) <= 1 for o in ('2.0/17', '2.0/19'))
    verdict = 'LOOP_SIGNAL_POSSIBLY_USED' if r1 else ('NO_EVIDENCE_THAT_THE_OPEN_LOOP_IS_USED_FOR_MULTI_HOP' if r2 else 'MIXED')
    print('\n-- rule reading: %s' % label)
    print('   H2 (correct 2-hop):', h2)
    print('   H3 (correct 3-hop):', h3)
    print('   3-hop gaps 2.0/18 minus: 2.0/17 %+d, 2.0/19 %+d, 1.0/18 %+d' % (h3['2.0/18'] - h3['2.0/17'], h3['2.0/18'] - h3['2.0/19'], h3['2.0/18'] - h3['1.0/18']))
    print('   2-hop gaps 2.0/18 minus: 2.0/17 %+d, 2.0/19 %+d, 1.0/18 %+d' % (h2['2.0/18'] - h2['2.0/17'], h2['2.0/18'] - h2['2.0/19'], h2['2.0/18'] - h2['1.0/18']))
    print('   rule1 (LOOP_SIGNAL) fires:', r1, '| rule2 (NO_EVIDENCE) fires:', r2, '| =>', verdict)
    return verdict


V = apply_rules(PRIMARY, 'PRIMARY (trained + held-back combined) -- THE VERDICT')


def merged(*tabs):
    out = {}
    for k in tabs[0]:
        out[k] = {}
        for t in tabs:
            for h, (c, n) in t[k].items():
                a, b = out[k].get(h, (0, 0))
                out[k][h] = (a + c, b + n)
    return out


apply_rules(merged(PRIMARY, DEV), 'SECONDARY: trained + held + dev panel')
apply_rules(merged(PRIMARY, EXC), 'SECONDARY: trained + held + excluded (all 107 course reach)')
apply_rules(HELD, 'SECONDARY: held-back only')
apply_rules(DEV, 'SECONDARY: dev panel only')

# ---------- paired record-level differences ----------
print('\n== paired differences on multi-hop (hop 2 and 3) records: 2.0/18 vs each other run')
for panel, ids, flt in (('course', course_ids, lambda g: g['split'] in ('trained', 'held')), ('dev', dev_ids, lambda g: True)):
    for h in (2, 3, 4, 5):
        sel = [r for r in ids if flt(GOLD[(panel, r)]) and GOLD[(panel, r)]['hop'] == h]
        if not sel:
            continue
        a = CORR[('2.0/18', panel)]
        for other in ('2.0/17', '2.0/19', '1.0/18', '1.0/17', '1.0/19'):
            b = CORR[(other, panel)]
            only18 = [r for r in sel if a[r] and not b[r]]
            onlyo = [r for r in sel if b[r] and not a[r]]
            print('  %s hop%d (n=%d): 2.0/18 right & %s wrong: %d ; %s right & 2.0/18 wrong: %d' % (panel, h, len(sel), other, len(only18), other, len(onlyo)))
    for s in ('17', '18', '19'):
        for h in (2, 3, 4, 5):
            sel = [r for r in ids if flt(GOLD[(panel, r)]) and GOLD[(panel, r)]['hop'] == h]
            if not sel:
                continue
            a = CORR[('2.0/' + s, panel)]
            b = CORR[('1.0/' + s, panel)]
            print('  %s hop%d same seed %s: 2.0 right & 1.0 wrong %d ; 1.0 right & 2.0 wrong %d' % (panel, h, s,
                  sum(a[r] and not b[r] for r in sel), sum(b[r] and not a[r] for r in sel)))

# ---------- list of wrong multi-hop records per run ----------
short = lambda x: x.split('/')[-1] if x else ''
print('\n== wrong records by run (hop>=2), as (query id chars 12-20, split, hop, gold, prediction)')
for panel, ids in (('course', course_ids), ('dev', dev_ids)):
    for v, s, d in RUNS:
        k = KEY((v, s))
        wr = [r for r in ids if GOLD[(panel, r)]['hop'] not in (1, 'none') and not CORR[(k, panel)][r]]
        print('  %s %s: %d wrong: %s' % (panel, k, len(wr), [(GOLD[(panel, r)]['qid'][12:20], GOLD[(panel, r)]['split'][:4], GOLD[(panel, r)]['hop'],
              GOLD[(panel, r)]['ans'][0][0] + short(GOLD[(panel, r)]['ans'][1]), (PRED[(k, panel)][r][0] or '?')[0] + short(PRED[(k, panel)][r][1])) for r in wr]))

# ---------- caveat check (RT4-F4) ----------
print('\n== caveat check on recomputed gold paths, hop-3 VIA records')
for panel, ids in (('course', course_ids), ('dev', dev_ids)):
    c = Counter()
    for r in ids:
        g = GOLD[(panel, r)]
        if g['hop'] != 3 or g['ans'][0] != 'VIA':
            continue
        via = g['ans'][1]
        E = g['E']
        c[(g['rule'][:9], 'via=child_of_whole' if (g['whole'], via) in E else '-', 'via=parent_of_part' if (via, g['part']) in E else '-')] += 1
    print('  %s:' % panel, dict(c))
print('\nVERDICT (primary, pre-registered):', V)
