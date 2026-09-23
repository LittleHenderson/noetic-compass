"""R3 gate forensics: deterministic, stdlib only, read-only on the repo."""
import json, re
from fractions import Fraction
from math import comb
from pathlib import Path
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
SEEDS = ['20260917','20260918','20260919']
VER = {'1.0': 'receipt_helm1_certified_%s', '2.0': 'receipt_%s'}
GATE = {'1.0': T/'admission_helm1_certified/gate_reading.json', '2.0': T/'admission_001/gate_reading.json'}
def J(p): return json.loads(Path(p).read_bytes())
def tail(b, n):
    if n == 0: return Fraction(1)
    return Fraction(sum(comb(n,k) for k in range(b, n+1)), 2**n)
g2 = J(GATE['2.0']); g1 = J(GATE['1.0'])
assert g1['population']['question_ids'] == g2['population']['question_ids']
POP = list(g2['population']['question_ids'])
FLOOR = set(g2['oracle_ceilings']['population_ids_the_rule_solves']) | set(g2['oracle_ceilings']['rank_last_ids_the_rule_solves'])
ORACLE = set(g2['oracle_ceilings']['population_ids_the_rule_solves']); RANK = set(g2['oracle_ceilings']['rank_last_ids_the_rule_solves'])
anc = J(T/'trust_anchor_helm2_experimental_20208c92.json')
kind_of = anc['population']['kind_of']; world_of = anc['population']['world_of']
short = lambda q: q.split('-')[-1][:8]
SCORE = re.compile(r'^(course|heldback)_p(\d\d)_scoring\.json$')
data = {}
for v, pat in VER.items():
    for s in SEEDS:
        art = T/(pat % s)/'collected/results/artifacts'
        at = {}
        rows_by_ck = {}
        for f in sorted(art.iterdir()):
            m = SCORE.match(f.name)
            if not m: continue
            n = int(m.group(2)); sc = J(f)
            for r in sc['rows']:
                at.setdefault(n, {})[r['record_id']] = bool(r['correct'])
                rows_by_ck.setdefault(n, {})[r['record_id']] = r
        pm = J(art/'protocol_material.json')
        wr = J(art/'worker_report.json')
        data[(v,s)] = dict(at=at, rows=rows_by_ck, pm=pm, wr=wr, art=art)
# question -> records from course_p00 rows (all 564)
r00 = data[('2.0','20260917')]['rows'][0]
q_records = {}; rec_kind = {}; rec_q = {}
for rid, r in r00.items():
    q_records.setdefault(r['query_id'], []).append(rid); rec_kind[rid] = r['kind']; rec_q[rid] = r['query_id']
pm = data[('2.0','20260917')]['pm']
HELD = pm['held_back_record_ids']; TRAINED = pm['trained_record_ids']; EXCL = pm['excluded_record_ids']
# consistency across versions of the split
for key,d in data.items():
    assert d['pm']['held_back_record_ids']==HELD and d['pm']['trained_record_ids']==TRAINED, key
held_q = sorted({rec_q[r] for r in HELD})
print('records total', len(r00), 'held', len(HELD), 'trained', len(TRAINED), 'excluded', len(EXCL), 'held questions', len(held_q))
def qok(at, q): return all(at[r] for r in q_records[q])
out = {}
print('\n=== (1) PRIMARY TEST ON THE FROZEN 18, recomputed from raw correct flags, both rules ===')
for v in VER:
    for s in SEEDS:
        at = data[(v,s)]['at']; cks = sorted(at); st, fi = cks[0], cks[-1]
        before = {q: qok(at[st], q) for q in POP}; after = {q: qok(at[fi], q) for q in POP}
        b = sum(1 for q in POP if not before[q] and after[q]); c = sum(1 for q in POP if before[q] and not after[q])
        p = tail(b, b+c)
        kinds = sorted({kind_of[q] for q in POP if not before[q] and after[q]})
        worlds = sorted({world_of[q] for q in POP if not before[q] and after[q]})
        frozen_rule = b > c and p <= Fraction(1,100) and len(kinds) >= 2 and len(worlds) >= 2
        strict_rule = b >= 7 and c == 0 and len(kinds) >= 2 and len(worlds) >= 2
        fin_correct = [q for q in POP if after[q]]
        above = [q for q in fin_correct if q not in FLOOR]
        floor_missed = [q for q in FLOOR if not after[q]]
        # gate against floor rule: machine-only vs rule-only
        bf = len(above); cf = len(floor_missed); pf = tail(bf, bf+cf)
        g = (g1 if v=='1.0' else g2)['seeds'][s]['G_LEARN_population']
        print(f"Helm {v} seed {s}: ck {st}->{fi} before {sum(before.values())} after {sum(after.values())} b={b} c={c} p={p} ({float(p)}) kinds={kinds} worlds={len(worlds)} | evaluate_gates rule pass={frozen_rule} (frozen reading says {g['passed']}, b/c {g['wrong_to_right']}/{g['right_to_wrong']}, p {g['p_one_sided']}) | broken==0 rule pass={strict_rule}")
        print(f"     above floor at final: {bf} {[ (short(q), kind_of[q]) for q in above]}; floor questions wrong at final: {cf} {[ (short(q), kind_of[q], 'RANK' if q in RANK else 'ORACLE') for q in floor_missed]}; machine-vs-floor p={pf} ({float(pf)})")
        broken = [q for q in POP if before[q] and not after[q]]
        startright = [q for q in POP if before[q]]
        print(f"     right at START: {[(short(q), kind_of[q], 'RANK' if q in RANK else ('ORACLE' if q in ORACLE else 'NONFLOOR')) for q in startright]}")
        print(f"     BROKEN: {[(short(q), kind_of[q], short(world_of[q]), 'RANK' if q in RANK else ('ORACLE' if q in ORACLE else 'NONFLOOR'), len(q_records[q])) for q in broken]}")
        out[(v,s)] = dict(before=before, after=after, b=b, c=c)
# counterfactual: what b would 19 need
print('\nmin b passing with c=0:', min(b for b in range(1,40) if tail(b,b)<=Fraction(1,100)), ' with c=1:', min(b for b in range(2,40) if tail(b,b+1)<=Fraction(1,100)), ' with c=2:', min(b for b in range(3,40) if tail(b,b+2)<=Fraction(1,100)))
print('tail(7,8)=', tail(7,8), float(tail(7,8)), ' tail(7,7)=', tail(7,7), float(tail(7,7)), ' tail(11,12)=', tail(11,12), float(tail(11,12)), ' tail(8,9)=', tail(8,9), float(tail(8,9)))
json.dump({'POP':POP,'FLOOR':sorted(FLOOR),'RANK':sorted(RANK),'ORACLE':sorted(ORACLE)}, open('ids.json','w'), indent=1)
