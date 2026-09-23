"""R3 meeting check 2: ten-node development panel, reach by hop count, Helm 1.0 vs 2.0. stdlib only."""
import json
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
T = ROOT/'records/typed_pointer_001'
SEEDS = ['20260917','20260918','20260919']
VER = {'1.0': 'receipt_helm1_certified_%s', '2.0': 'receipt_%s'}
J = lambda p: json.loads(Path(p).read_bytes())
for v in VER:
    for s in SEEDS:
        art = T/(VER[v] % s)/'collected/results/artifacts'
        for n in (0, 10):
            rows = J(art/('development_p%02d_scoring.json' % n))['rows']
            tab = defaultdict(lambda: [0, 0])
            for r in rows:
                ws = r['witnesses']
                path = ws[0]['evidence'].get('path') if ws and isinstance(ws[0].get('evidence'), dict) else None
                key = (r['kind'], (len(path) - 1) if path else None)
                tab[key][1] += 1; tab[key][0] += int(bool(r['correct']))
            print('Helm', v, s, 'dev p%02d' % n, 'total %d/%d' % (sum(c for c, t in tab.values()), sum(t for c, t in tab.values())),
                  ' '.join('%s/h%s %d/%d' % (k[0], k[1], c, t) for k, (c, t) in sorted(tab.items(), key=str)))
