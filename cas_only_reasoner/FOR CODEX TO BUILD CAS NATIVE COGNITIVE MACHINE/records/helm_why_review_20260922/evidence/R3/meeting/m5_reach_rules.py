"""R3 meeting check 5: zero-learning rules on reach, scored against the checker-verified gold signature
(taken from correct predictions in the six receipts). Graphs from the public course bank. stdlib only."""
import json, re
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
J = lambda p: json.loads(Path(p).read_bytes())
exec(open('m4_const_reach.py').read().split("print('reach records with a known")[0])   # builds gold{}
course = J(ROOT/'records/typed_course_001/checks_002/public_course.json')
W = {w['world_id']: w for w in course['bank']['worlds']}
reg = {r['record_id']: r for r in course['registry']}
g2 = J(T/'admission_001/gate_reading.json')
POP = set(g2['population']['question_ids'])
FLOOR = set(g2['oracle_ceilings']['population_ids_the_rule_solves']) | set(g2['oracle_ceilings']['rank_last_ids_the_rule_solves'])
art0 = T/'receipt_20260917/collected/results/artifacts'
pm = J(art0/'protocol_material.json'); split = {**{r: 'held' for r in pm['held_back_record_ids']}, **{r: 'trained' for r in pm['trained_record_ids']}, **{r: 'excluded' for r in pm['excluded_record_ids']}}
rk = lambda ref: int(ref.split('/')[-1][1:])
def graph(wid):
    w = W[wid]; E = set((e['source'], e['target']) for e in w['contains'])
    nodes = sorted({x for e in E for x in e} | set(w.get('nodes', []) if isinstance(w.get('nodes'), list) and w.get('nodes') and isinstance(w['nodes'][0], str) else []), key=rk)
    return nodes, E
def rules(r):
    q = r['query']; wh, pa = q['arguments']['whole'], q['arguments']['part']
    nodes, E = graph(q['focus_world_id'])
    others = [n for n in nodes if n not in (wh, pa)]
    direct = (wh, pa) in E
    common = [m for m in others if (wh, m) in E and (m, pa) in E]
    out = {}
    out['const_VIA_n1'] = 'VIA/n1'
    out['VIA_lexfirst_other'] = 'VIA/n%d' % rk(others[0])
    out['VIA_lexlast_other'] = 'VIA/n%d' % rk(others[-1])
    out['DIRECT_if_edge_else_VIA_lexfirst'] = 'DIRECT/-' if direct else out['VIA_lexfirst_other']
    out['DIRECT_if_edge_else_VIA_lexlast'] = 'DIRECT/-' if direct else out['VIA_lexlast_other']
    out['DIRECT_if_edge_else_VIA_common_neighbour_lexfirst'] = 'DIRECT/-' if direct else ('VIA/n%d' % rk(common[0]) if common else '?')
    return out, len(nodes)
tab = defaultdict(lambda: defaultdict(lambda: [0, 0])); qtab = defaultdict(dict); nn = Counter()
for rid, g in gold.items():
    gs = next(iter(g)); r = reg[rid]; out, n = rules(r); nn[n] += 1
    for name, pred in out.items():
        for grp in ('all', split[rid]):
            tab[name][grp][0] += int(pred == gs); tab[name][grp][1] += 1
        if r['query']['query_id'] in POP:
            qtab[name].setdefault(r['query']['query_id'], []).append(pred == gs)
print('node counts of reach focus worlds:', dict(nn))
frozen_reach = sorted({reg[rid]['query']['query_id'] for rid in gold if reg[rid]['query']['query_id'] in POP})
print('frozen-18 reach questions:', [(q.split('-')[-1][:8], 'FLOOR' if q in FLOOR else 'NONFLOOR') for q in frozen_reach])
for name in tab:
    solved = [q.split('-')[-1][:8] for q, v in sorted(qtab[name].items()) if all(v)]
    nonfloor_solved = [q.split('-')[-1][:8] for q, v in sorted(qtab[name].items()) if all(v) and q not in FLOOR]
    print('%-50s' % name, ' '.join('%s %d/%d' % (k, c, t) for k, (c, t) in sorted(tab[name].items())), '| frozen reach solved', solved, '| of them non-floor', nonfloor_solved)
for rid in gold:
    q = reg[rid]['query']
    if q['query_id'].split('-')[-1][:8] in ('7a391350', 'a3e70de9', '36988555', '404166e8'):
        nodes, E = graph(q['focus_world_id'])
        print(q['query_id'].split('-')[-1][:8], q['rule'], 'whole', q['arguments']['whole'][-2:], 'part', q['arguments']['part'][-2:], 'gold', next(iter(gold[rid])), 'edges', sorted((a[-2:], b[-2:]) for a, b in E), 'nodes', [x[-2:] for x in nodes])
