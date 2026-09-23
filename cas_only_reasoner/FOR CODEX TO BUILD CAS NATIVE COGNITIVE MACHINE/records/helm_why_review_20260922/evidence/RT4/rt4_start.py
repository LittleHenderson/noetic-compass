"""RT4 start-point question. Definitions fixed in PRE_RUN_DEFINITIONS.txt before this was run.
(A) at p00, share of pointed reach/parts nodes that are rank-last vs chance, per run.
(B) which frozen floor questions each untrained start already answers (validated by rebuilding b/c)."""
from fractions import Fraction
from collections import Counter, defaultdict
from rt4_common import *

GATES = {'2.0': J(T / 'admission_001/gate_reading.json'), '1.0': J(T / 'admission_helm1_certified/gate_reading.json')}


def pointers(run_dir, phase, only_split=None):
    """yield (kind, n, pointed_rank, args) for reach VIA pointers and each parts node pointer."""
    for rid, p in preds(run_dir, phase).items():
        k = p['answer']['kind']
        if only_split and SPLIT.get(rid) != only_split:
            continue
        q = REG[rid]['query']
        if k == 'reach':
            v = via_rank(p)
            if v is None:
                continue
            n = len(W[q['focus_world_id']]['nodes'])
            yield ('reach', n, v, (rk(q['arguments']['whole']), rk(q['arguments']['part'])), rid)
        elif k == 'parts':
            n = len(W[q['focus_world_id']]['nodes'])
            for ref in p['answer']['value']['nodes']:
                yield ('parts', n, rk(ref), (rk(q['arguments']['whole']),), rid)


def measure(ptrs):
    out = {}
    for kinds in (('reach', 'parts'), ('reach',), ('parts',)):
        P = [x for x in ptrs if x[0] in kinds]
        # pre-registered primary: rank-last NON-argument; chance reach 1/(n-2), parts 1/(n-1); argument pointers count as not rank-last
        obs = sum(1 for k, n, v, a, r in P if v == max(x for x in range(n) if x not in a))
        exp = sum((Fraction(1, n - 2) if k == 'reach' else Fraction(1, n - 1)) for k, n, v, a, r in P)
        # chair-literal: 1/(n-2) for every pointer
        exp_lit = sum(Fraction(1, n - 2) for k, n, v, a, r in P)
        # among pointers that are NOT at an argument only
        Pn = [x for x in P if x[2] not in x[3]]
        obs_n = sum(1 for k, n, v, a, r in Pn if v == max(x for x in range(n) if x not in a))
        exp_n = sum((Fraction(1, n - 2) if k == 'reach' else Fraction(1, n - 1)) for k, n, v, a, r in Pn)
        # registered-floor variant: rank-last OVERALL (refs[-1]); chance 1/n
        obs_o = sum(1 for k, n, v, a, r in P if v == n - 1)
        exp_o = sum(Fraction(1, n) for k, n, v, a, r in P)
        out['+'.join(kinds)] = dict(pointers=len(P), obs=obs, exp=exp, ratio=(obs / exp if exp else None),
                                    exp_lit=exp_lit, ratio_lit=(obs / exp_lit if exp_lit else None),
                                    nonarg=len(Pn), obs_n=obs_n, exp_n=exp_n, ratio_n=(obs_n / exp_n if exp_n else None),
                                    obs_o=obs_o, exp_o=exp_o, ratio_o=(obs_o / exp_o if exp_o else None))
    return out


def f(x):
    return 'None' if x is None else '%s (=%s)' % (x, repr(float(x)))


print('(A) p00 rank-last pointing, all 564 course records')
verdict_rows = []
for ver, seed, d in RUNS:
    m = measure(list(pointers(d, 'course_p00')))
    print('== Helm %s seed %s' % (ver, seed))
    for key, v in m.items():
        print('   %-12s pointers %4d | rank-last non-arg %4d vs expected %s -> ratio %s | chair-literal 1/(n-2): ratio %s' % (
            key, v['pointers'], v['obs'], f(v['exp']), f(v['ratio']), f(v['ratio_lit'])))
        print('   %-12s   non-argument pointers only %4d: rank-last %4d vs expected %s -> ratio %s | rank-last OVERALL %4d vs 1/n expected %s -> ratio %s' % (
            '', v['nonarg'], v['obs_n'], f(v['exp_n']), f(v['ratio_n']), v['obs_o'], f(v['exp_o']), f(v['ratio_o'])))
    verdict_rows.append((ver, seed, m['reach+parts']))
print('\nPre-registered verdict (primary = reach+parts, per-pointer chance, argument pointers not rank-last):')
for name, key in (('primary', 'ratio'), ('chair-literal 1/(n-2)', 'ratio_lit'), ('non-argument pointers only', 'ratio_n'),
                  ('rank-last overall vs 1/n', 'ratio_o')):
    rs = [v[key] for _, _, v in verdict_rows]
    ge2 = sum(1 for r in rs if r >= 2)
    within = all(Fraction(2, 3) <= r <= Fraction(3, 2) for r in rs)
    lab = ('LOTTERY' if ge2 >= 4 else ('NO_SYSTEMATIC_BIAS' if within else 'NEITHER_RULE'))
    print('   %-28s ratios %s | runs >= 2x: %d | all within [2/3, 3/2]: %s -> %s' % (
        name, [round(float(r), 6) for r in rs], ge2, within, lab))

# secondary: parts inclusion rate of rank-last non-arg vs other non-arg nodes
print('\n(A2) secondary, parts only: P(node included | rank-last non-arg) vs P(included | other non-arg), p00')
for ver, seed, d in RUNS:
    inc = Counter()
    for rid, p in preds(d, 'course_p00').items():
        if p['answer']['kind'] != 'parts':
            continue
        q = REG[rid]['query']
        n = len(W[q['focus_world_id']]['nodes'])
        wh = rk(q['arguments']['whole'])
        chosen = {rk(x) for x in p['answer']['value']['nodes']}
        rl = max(x for x in range(n) if x != wh)
        for x in range(n):
            if x == wh:
                inc[('whole', x in chosen)] += 1
            else:
                inc[('RL' if x == rl else 'other', x in chosen)] += 1
    rl_rate = Fraction(inc[('RL', True)], inc[('RL', True)] + inc[('RL', False)])
    ot_rate = Fraction(inc[('other', True)], inc[('other', True)] + inc[('other', False)])
    wh_rate = Fraction(inc[('whole', True)], inc[('whole', True)] + inc[('whole', False)])
    print('   Helm %s %s: rank-last included %s | other non-arg included %s | whole arg included %s' % (
        ver, seed, f(rl_rate), f(ot_rate), f(wh_rate)))

# (B) floor questions at p00
print('\n(B) frozen floor questions answered by each untrained start (p00); question right = all its held records right')
for ver, seed, d in RUNS:
    g = GATES[ver]
    pop = g['population']['question_ids']
    oc = g['oracle_ceilings']
    oracle = set(oc['population_ids_the_rule_solves'])
    rlast = set(oc['rank_last_ids_the_rule_solves'])
    floor = oracle | rlast
    held = [rid for rid in SPLIT if SPLIT[rid] == 'held']
    qrec = defaultdict(list)
    for rid in held:
        qid = REG[rid]['query']['query_id']
        if qid in pop:
            qrec[qid].append(rid)
    s0 = scoring(d, 'course_p00')
    s10 = scoring(d, 'course_p10')
    q0 = {q: all(s0[r]['correct'] for r in rs) for q, rs in qrec.items()}
    q10 = {q: all(s10[r]['correct'] for r in rs) for q, rs in qrec.items()}
    b = sum(1 for q in pop if not q0[q] and q10[q])
    c = sum(1 for q in pop if q0[q] and not q10[q])
    rec = g['seeds'][seed]['G_LEARN_population']
    ok = (b == rec['wrong_to_right'] and c == rec['right_to_wrong'])
    sh = lambda q: q[12:20] + ('(R)' if q in rlast and q not in oracle else ('(O+R)' if q in rlast else '(O)'))
    right0 = sorted(sh(q) for q in floor if q0[q])
    print('== Helm %s seed %s: questions mapped %d (records %d) | rebuilt b=%d c=%d, recorded b=%d c=%d, match=%s' % (
        ver, seed, len(qrec), sum(len(v) for v in qrec.values()), b, c, rec['wrong_to_right'], rec['right_to_wrong'], ok))
    print('   p00 right on floor (11): %d -> %s' % (len(right0), right0))
    print('   p00 right on rank-last-only floor (4, excl. 786bbcba which the oracle also solves): %d -> %s' % (
        sum(1 for q in rlast - oracle if q0[q]), sorted(q[12:20] for q in rlast - oracle if q0[q])))
    print('   p00 right on all 18: %d | non-floor right at p00: %s' % (
        sum(q0.values()), sorted(q[12:20] for q in pop if q0[q] and q not in floor)))
