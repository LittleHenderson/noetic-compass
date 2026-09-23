"""R3 meeting check 1: does Helm 1.0 (one-hop loop) answer VIA (2-hop) reach records? stdlib only."""
import json
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
SEEDS = ['20260917','20260918','20260919']
VER = {'1.0': 'receipt_helm1_certified_%s', '2.0': 'receipt_%s'}
J = lambda p: json.loads(Path(p).read_bytes())
art0 = T/(VER['2.0'] % SEEDS[0])/'collected/results/artifacts'
pm = J(art0/'protocol_material.json')
split = {}
for r in pm['held_back_record_ids']: split[r] = 'held'
for r in pm['trained_record_ids']: split[r] = 'trained'
for r in pm['excluded_record_ids']: split[r] = 'excluded'
def load(v, s, n):
    art = T/(VER[v] % s)/'collected/results/artifacts'
    return {r['record_id']: r for r in J(art/('course_p%02d_scoring.json' % n))['rows']}
base = load('2.0', SEEDS[0], 10)
info = {}
for rid, r in base.items():
    if r['kind'] != 'reach': continue
    ws = r['witnesses']
    path = ws[0]['evidence'].get('path') if ws and isinstance(ws[0].get('evidence'), dict) else None
    hops = (len(path) - 1) if path else None
    info[rid] = dict(hops=hops, rule=r['rule'], n_adm=r['admissible_answer_count'], split=split[rid], nwit=len(ws))
print('reach records', len(info))
print('by (rule, hops):', sorted(Counter((i['rule'], i['hops']) for i in info.values()).items(), key=str))
print('by (split, hops):', sorted(Counter((i['split'], i['hops']) for i in info.values()).items(), key=str))
print('admissible answer counts:', Counter(i['n_adm'] for i in info.values()), 'witness counts', Counter(i['nwit'] for i in info.values()))
for v in VER:
    for s in SEEDS:
        for n in (0, 10):
            sc = load(v, s, n)
            tab = defaultdict(lambda: [0, 0])
            for rid, i in info.items():
                key = (i['split'], i['hops'])
                tab[key][1] += 1; tab[key][0] += int(bool(sc[rid]['correct']))
            print('Helm', v, s, 'p%02d' % n, ' '.join('%s/h%s %d/%d' % (k[0], k[1], c, t) for k, (c, t) in sorted(tab.items(), key=str)))
