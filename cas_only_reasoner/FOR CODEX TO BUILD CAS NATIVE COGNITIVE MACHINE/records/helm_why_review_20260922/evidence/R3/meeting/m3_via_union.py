"""R3 meeting check 3: reach accuracy by hop count, with hop counts taken from the checker's witness path
UNIONED over every scoring file of all six runs (a witness is only written when a prediction is correct).
stdlib only; read-only."""
import json, re
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
SEEDS = ['20260917','20260918','20260919']
VER = {'1.0': 'receipt_helm1_certified_%s', '2.0': 'receipt_%s'}
J = lambda p: json.loads(Path(p).read_bytes())
SC = re.compile(r'^(course|heldback)_p(\d\d)_scoring\.json$')
paths = defaultdict(set); wit_vs_correct = Counter()
for v in VER:
    for s in SEEDS:
        art = T/(VER[v] % s)/'collected/results/artifacts'
        for f in art.iterdir():
            if not SC.match(f.name): continue
            for r in J(f)['rows']:
                wit_vs_correct[(bool(r['correct']), len(r['witnesses']) > 0)] += 1
                if r['kind'] != 'reach' or not r['witnesses']: continue
                ev = r['witnesses'][0].get('evidence') or {}
                if ev.get('path'): paths[r['record_id']].add(tuple(ev['path']))
print('(correct, has_witness) counts over all course/heldback scoring files:', dict(wit_vs_correct))
print('records with >1 distinct witness path:', sum(1 for p in paths.values() if len(p) > 1))
art0 = T/(VER['2.0'] % SEEDS[0])/'collected/results/artifacts'
pm = J(art0/'protocol_material.json')
split = {**{r: 'held' for r in pm['held_back_record_ids']}, **{r: 'trained' for r in pm['trained_record_ids']}, **{r: 'excluded' for r in pm['excluded_record_ids']}}
reach = [r['record_id'] for r in J(art0/'course_p10_scoring.json')['rows'] if r['kind'] == 'reach']
hops = {rid: (len(next(iter(paths[rid]))) - 1 if paths.get(rid) else None) for rid in reach}
print('reach records', len(reach), 'hop counts:', sorted(Counter(hops.values()).items(), key=str))
print('by split/hops:', sorted(Counter((split[r], hops[r]) for r in reach).items(), key=str))
for v in VER:
    for s in SEEDS:
        art = T/(VER[v] % s)/'collected/results/artifacts'
        for n in (0, 10):
            sc = {r['record_id']: r for r in J(art/('course_p%02d_scoring.json' % n))['rows']}
            tab = defaultdict(lambda: [0, 0]); allh = defaultdict(lambda: [0, 0])
            for rid in reach:
                k = (split[rid], hops[rid]); ok = int(bool(sc[rid]['correct']))
                tab[k][0] += ok; tab[k][1] += 1; allh[hops[rid]][0] += ok; allh[hops[rid]][1] += 1
            print('Helm', v, s, 'p%02d' % n, '| all:', ' '.join('h%s %d/%d' % (h, c, t) for h, (c, t) in sorted(allh.items(), key=str)),
                  '| held:', ' '.join('h%s %d/%d' % (k[1], c, t) for k, (c, t) in sorted(tab.items(), key=str) if k[0] == 'held'))
