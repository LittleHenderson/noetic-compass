"""R3 meeting check 4: what do UNTRAINED models answer on reach, and how far does a constant answer go?
Answers are compared by (state, rank of the via node); rank = the /nK suffix of the node ref. stdlib only."""
import json, re
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
SEEDS = ['20260917','20260918','20260919']
VER = {'1.0': 'receipt_helm1_certified_%s', '2.0': 'receipt_%s'}
J = lambda p: json.loads(Path(p).read_bytes())
def sig(val):
    if not isinstance(val, dict): return str(val)
    via = val.get('via')
    return '%s/%s' % (val.get('state'), via.split('/')[-1] if via else '-')
# gold signature per reach record = signature of any CORRECT prediction in any run/checkpoint
SC = re.compile(r'^(course|heldback)_p(\d\d)_(scoring|predictions)\.json$')
gold = defaultdict(set)
for v in VER:
    for s in SEEDS:
        art = T/(VER[v] % s)/'collected/results/artifacts'
        for f in sorted(art.iterdir()):
            m = SC.match(f.name)
            if not m or m.group(3) != 'scoring': continue
            sc = {r['record_id']: r for r in J(f)['rows']}
            pr = J(art/f.name.replace('scoring', 'predictions'))['predictions']
            for p in pr:
                r = sc[p['record_id']]
                if r['kind'] == 'reach' and r['correct']:
                    gold[p['record_id']].add(sig(p['answer']['value']))
print('reach records with a known gold signature', len(gold), '; with >1 signature', sum(1 for g in gold.values() if len(g) > 1))
gs = Counter(next(iter(g)) for g in gold.values())
print('gold signature distribution (all 107 reach records that were ever answered right):', gs.most_common())
art0 = T/(VER['2.0'] % SEEDS[0])/'collected/results/artifacts'
pm = J(art0/'protocol_material.json'); held = set(pm['held_back_record_ids'])
gh = Counter(next(iter(g)) for r, g in gold.items() if r in held)
print('gold signature distribution, held-back reach records:', gh.most_common())
for v in VER:
    for s in SEEDS:
        art = T/(VER[v] % s)/'collected/results/artifacts'
        for n in (0, 10):
            sc = {r['record_id']: r for r in J(art/('course_p%02d_scoring.json' % n))['rows']}
            pr = [p for p in J(art/('course_p%02d_predictions.json' % n))['predictions'] if sc[p['record_id']]['kind'] == 'reach']
            c = Counter(sig(p['answer']['value']) for p in pr)
            print('Helm', v, s, 'p%02d' % n, 'reach answer signatures:', c.most_common(5), '| correct', sum(int(sc[p['record_id']]['correct']) for p in pr), 'of', len(pr))
